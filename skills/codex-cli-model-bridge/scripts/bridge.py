#!/usr/bin/env python3
"""Codex ↔ CLIProxyAPI model bridge.

The script deliberately keeps secrets out of stdout. It manages only the Codex
provider block, its model catalog, and bridge ownership state.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import difflib
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request


SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CODEX_HOME = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()
DEFAULT_STATE_DIR = Path("~/.config/codex-cli-model-bridge").expanduser()
DEFAULT_PROXY_URL = "http://127.0.0.1:8317/v1"
DEFAULT_TRANSPARENT_PROXY_URL = "http://127.0.0.1:8318/v1"
DEFAULT_PROFILE_NAME = "cli-proxy"
DEFAULT_PROFILE_CONFIG = DEFAULT_CODEX_HOME / f"{DEFAULT_PROFILE_NAME}.config.toml"
DEFAULT_STATE_DB = DEFAULT_CODEX_HOME / "state_5.sqlite"
DEFAULT_AUTH_FILE = DEFAULT_CODEX_HOME / "auth.json"
DEFAULT_TRANSPARENT_RUNTIME = DEFAULT_STATE_DIR / "transparent_proxy.mjs"
DEFAULT_CATALOG_POLICY = SKILL_DIR / "policies" / "catalog.json"
DEFAULT_LAUNCH_AGENT = Path(
    "~/Library/LaunchAgents/com.zhijian.codex-cli-model-bridge-transparent-proxy.plist"
).expanduser()
TRANSPARENT_LAUNCH_LABEL = "com.zhijian.codex-cli-model-bridge-transparent-proxy"
PROVIDER_ID = "cli_proxy"
SCHEMA_VERSION = 1
MIN_TOOL_SAFE_PROXY_VERSION = (7, 2, 130)


def is_windows() -> bool:
    return os.name == "nt" or platform.system() == "Windows"


def python_executable() -> str:
    return sys.executable or shutil.which("python3") or shutil.which("python") or "python3"


def ruby_executable() -> str:
    found = shutil.which("ruby")
    if found:
        return found
    return "ruby" if is_windows() else "/usr/bin/ruby"


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        expanded = path.expanduser()
        if expanded.exists():
            return expanded
    return None


def discover_executable(names: list[str], extra: list[Path] | None = None) -> Path | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)
    return first_existing(extra or [])


def default_proxy_binary() -> Path:
    extra: list[Path] = []
    if platform.system() == "Darwin":
        extra = [
            Path("/opt/homebrew/opt/cliproxyapi/bin/cliproxyapi"),
            Path("/usr/local/opt/cliproxyapi/bin/cliproxyapi"),
        ]
    found = discover_executable(["cliproxyapi", "cli-proxy-api", "CLIProxyAPI"], extra)
    return found or Path("cliproxyapi")


def default_brew() -> Path:
    found = discover_executable(
        ["brew"],
        [Path("/opt/homebrew/bin/brew"), Path("/usr/local/bin/brew")],
    )
    return found or Path("brew")


def default_node() -> Path:
    found = discover_executable(
        ["node"],
        [Path("/opt/homebrew/bin/node"), Path("/usr/local/bin/node")],
    )
    return found or Path("node")


def default_proxy_config() -> Path:
    env = os.environ.get("CLIPROXYAPI_CONFIG")
    if env:
        return Path(env).expanduser()
    home = Path.home()
    candidates = [
        home / ".cli-proxy-api" / "config.yaml",
        home / ".cliproxyapi" / "config.yaml",
        Path("/opt/homebrew/etc/cliproxyapi.conf"),
        Path("/usr/local/etc/cliproxyapi.conf"),
    ]
    if is_windows():
        local = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
        roaming = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
        candidates = [
            home / ".cli-proxy-api" / "config.yaml",
            local / "CLIProxyAPI" / "config.yaml",
            roaming / "CLIProxyAPI" / "config.yaml",
            local / "EasyCLIProxyAPI" / "cpa-core" / "config.yaml",
        ] + candidates
    return first_existing(candidates) or candidates[0]


def default_helper_path() -> Path:
    base = Path("~/.config/codex-cli-proxy").expanduser()
    python_helper = base / "read-client-key.py"
    ruby_helper = base / "read-client-key.rb"
    if python_helper.exists():
        return python_helper
    if ruby_helper.exists():
        return ruby_helper
    return python_helper


def helper_invocation(helper_path: Path) -> tuple[str, list[str]]:
    if helper_path.suffix.lower() == ".rb":
        return ruby_executable(), [str(helper_path)]
    python = python_executable()
    if Path(python).name.lower() in {"py", "py.exe"}:
        return python, ["-3", str(helper_path)]
    return python, [str(helper_path)]


DEFAULT_PROXY_CONFIG = default_proxy_config()
DEFAULT_BREW = default_brew()
DEFAULT_PROXY_BINARY = default_proxy_binary()
DEFAULT_HELPER = default_helper_path()


def emit(value: object, exit_code: int = 0) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(exit_code)


def mode(path: Path) -> str | None:
    try:
        return oct(stat.S_IMODE(path.stat().st_mode))
    except FileNotFoundError:
        return None


def owner_mode_ok(path: Path, expected: int) -> bool:
    if is_windows():
        return True
    return mode(path) == oct(expected)


def timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def parse_proxy_version(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"CLIProxyAPI Version:\s*(\d+)\.(\d+)\.(\d+)", text)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def proxy_version(path: Path) -> tuple[str | None, tuple[int, int, int] | None]:
    try:
        proc = subprocess.run(
            [str(path), "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    parsed = parse_proxy_version(proc.stdout)
    rendered = ".".join(str(part) for part in parsed) if parsed else None
    return rendered, parsed


def backup(path: Path) -> Path:
    target = path.with_name(f"{path.name}.backup-{timestamp()}")
    shutil.copy2(path, target)
    os.chmod(target, 0o600)
    return target


def atomic_write(path: Path, data: str, file_mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, file_mode)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def read_json(path: Path, default: object | None = None) -> object:
    if not path.exists():
        if default is not None:
            return copy.deepcopy(default)
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def is_loopback(url: str) -> bool:
    try:
        host = urllib.parse.urlparse(url).hostname
        return host in {"127.0.0.1", "localhost", "::1"}
    except ValueError:
        return False


def provider_from_config(config: dict, provider_id: str = PROVIDER_ID) -> dict:
    return dict(config.get("model_providers", {}).get(provider_id, {}))


def load_config(path: Path) -> tuple[dict, str | None]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return {}, "missing"
    except (tomllib.TOMLDecodeError, OSError) as exc:
        return {}, f"{type(exc).__name__}: {exc}"


def token_from_provider(provider: dict) -> tuple[str | None, str | None]:
    auth = provider.get("auth")
    if not isinstance(auth, dict):
        return None, "command-backed auth is not configured"
    command = auth.get("command")
    args = auth.get("args", [])
    if not isinstance(command, str) or not command:
        return None, "auth.command is missing"
    if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        return None, "auth.args must be a string array"
    timeout = max(1, int(auth.get("timeout_ms", 5000)) / 1000)
    try:
        proc = subprocess.run(
            [command, *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"credential helper failed: {type(exc).__name__}"
    token = proc.stdout.strip()
    if proc.returncode != 0 or not token:
        return None, "credential helper returned no usable token"
    return token, None


def required_live_routes(catalog_entries: list[dict], managed_ids: list[str], default_model: str | None) -> list[str]:
    required: set[str] = {item for item in managed_ids if item}
    if default_model:
        required.add(default_model)
    for entry in catalog_entries:
        slug = entry.get("slug")
        if not isinstance(slug, str) or not slug:
            continue
        if entry.get("visibility") == "hide":
            continue
        if entry.get("supported_in_api") is False:
            continue
        required.add(slug)
    return sorted(required)


def live_model_ids(base_url: str, token: str, fixture: Path | None = None) -> set[str]:
    if fixture:
        payload = read_json(fixture)
    else:
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.load(response)
    data = payload.get("data", []) if isinstance(payload, dict) else []
    return {item["id"] for item in data if isinstance(item, dict) and isinstance(item.get("id"), str)}


def catalog_models(path: Path) -> list[dict]:
    payload = read_json(path)
    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise ValueError("catalog must contain a models array")
    slugs: set[str] = set()
    for entry in models:
        if not isinstance(entry, dict) or not isinstance(entry.get("slug"), str):
            raise ValueError("every catalog entry needs a string slug")
        if entry["slug"] in slugs:
            raise ValueError(f"duplicate catalog slug: {entry['slug']}")
        slugs.add(entry["slug"])
    return models


def catalog_policy(path: Path) -> dict:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("catalog policy root must be an object")
    if payload.get("schema_version") != 1:
        raise ValueError("catalog policy schema_version must be 1")
    hidden = payload.get("hidden_native_model_ids", [])
    if not isinstance(hidden, list) or not all(isinstance(item, str) and item.strip() for item in hidden):
        raise ValueError("hidden_native_model_ids must be an array of non-empty strings")
    if len(hidden) != len(set(hidden)):
        raise ValueError("hidden_native_model_ids must not contain duplicates")
    protected = payload.get("protected_native_model_ids", [])
    if not isinstance(protected, list) or not all(
        isinstance(item, str) and item.strip() for item in protected
    ):
        raise ValueError("protected_native_model_ids must be an array of non-empty strings")
    if len(protected) != len(set(protected)):
        raise ValueError("protected_native_model_ids must not contain duplicates")
    return {
        "schema_version": 1,
        "hidden_native_model_ids": hidden,
        "protected_native_model_ids": protected,
    }


def protected_supersede_conflicts(manifests: list[dict], policy: dict) -> list[str]:
    protected = set(policy.get("protected_native_model_ids", []))
    superseded = {
        route
        for manifest in manifests
        for route in manifest.get("supersedes", [])
        if isinstance(route, str)
    }
    return sorted(protected & superseded)


def manifest_paths(selected: set[str] | None = None) -> list[Path]:
    paths = sorted((SKILL_DIR / "models").glob("*.json"))
    local = DEFAULT_STATE_DIR / "models.d"
    if local.exists():
        paths.extend(sorted(local.glob("*.json")))
    if selected is None:
        return paths
    return [path for path in paths if path.stem in selected]


def validate_manifest(data: dict) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version": int,
        "slug": str,
        "display_name": str,
        "description": str,
        "template_slug": str,
        "context_window": int,
        "effective_context_window_percent": int,
        "default_reasoning_level": str,
        "reasoning_efforts": list,
        "input_modalities": list,
        "priority": int,
    }
    for key, expected in required.items():
        if not isinstance(data.get(key), expected):
            errors.append(f"{key} must be {expected.__name__}")
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if isinstance(data.get("slug"), str) and not re.fullmatch(r"[a-zA-Z0-9._:-]+", data["slug"]):
        errors.append("slug contains unsupported characters")
    efforts = data.get("reasoning_efforts", [])
    allowed_efforts = {"minimal", "low", "medium", "high", "xhigh", "max", "ultra"}
    if not efforts or any(not isinstance(item, str) or item not in allowed_efforts for item in efforts):
        errors.append("reasoning_efforts contains an invalid value")
    modalities = data.get("input_modalities", [])
    if not modalities or any(item not in {"text", "image"} for item in modalities):
        errors.append("input_modalities must contain only text/image")
    if data.get("default_reasoning_level") not in efforts:
        errors.append("default_reasoning_level must be in reasoning_efforts")
    supersedes = data.get("supersedes", [])
    if not isinstance(supersedes, list) or any(not isinstance(item, str) or not item for item in supersedes):
        errors.append("supersedes must be a string array")
    return errors


def reasoning_levels(efforts: list[str]) -> list[dict]:
    descriptions = {
        "minimal": "Minimal reasoning for the fastest response",
        "low": "Fast responses with lighter reasoning",
        "medium": "Balanced speed and reasoning depth",
        "high": "Greater reasoning depth for complex work",
        "xhigh": "Extra-high reasoning depth",
        "max": "Maximum reasoning depth",
        "ultra": "Maximum reasoning with automatic task delegation",
    }
    return [{"effort": effort, "description": descriptions[effort]} for effort in efforts]


def build_entry(manifest: dict, templates: dict[str, dict]) -> dict:
    template_slug = manifest["template_slug"]
    if template_slug not in templates:
        raise ValueError(f"template model is missing: {template_slug}")
    entry = copy.deepcopy(templates[template_slug])
    entry.update(
        {
            "slug": manifest["slug"],
            "display_name": manifest["display_name"],
            "description": manifest["description"],
            "default_reasoning_level": manifest["default_reasoning_level"],
            "supported_reasoning_levels": reasoning_levels(manifest["reasoning_efforts"]),
            "visibility": "list",
            "supported_in_api": True,
            "priority": manifest["priority"],
            "additional_speed_tiers": manifest.get("additional_speed_tiers", []),
            "service_tiers": manifest.get("service_tiers", []),
            "context_window": manifest["context_window"],
            "max_context_window": manifest["context_window"],
            "effective_context_window_percent": manifest["effective_context_window_percent"],
            "input_modalities": manifest["input_modalities"],
            "supports_search_tool": bool(manifest.get("supports_search_tool", False)),
            "supports_image_detail_original": bool(
                manifest.get("supports_image_detail_original", "image" in manifest["input_modalities"])
            ),
            "prefer_websockets": bool(manifest.get("prefer_websockets", False)),
        }
    )
    # Tool mode is a model-specific calling protocol, not a generic capability.
    # Third-party models copied from an OpenAI template must be able to opt out
    # of `code_mode_only`, whose freeform `exec` payload cannot be represented
    # by a normal JSON function schema through compatibility bridges.
    if "tool_mode" in manifest:
        tool_mode = manifest["tool_mode"]
        if tool_mode is None:
            entry.pop("tool_mode", None)
        else:
            entry["tool_mode"] = tool_mode
    return entry


def replace_top_scalar(text: str, key: str, value: str) -> str:
    lines = text.splitlines(keepends=True)
    first_table = next((i for i, line in enumerate(lines) if line.lstrip().startswith("[")), len(lines))
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    for index in range(first_table):
        if pattern.match(lines[index]):
            lines[index] = f"{key} = {json.dumps(value)}\n"
            return "".join(lines)
    lines.insert(first_table, f"{key} = {json.dumps(value)}\n")
    return "".join(lines)


def remove_top_scalar(text: str, key: str) -> str:
    lines = text.splitlines(keepends=True)
    first_table = next((i for i, line in enumerate(lines) if line.lstrip().startswith("[")), len(lines))
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    return "".join(line for index, line in enumerate(lines) if not (index < first_table and pattern.match(line)))


def thread_inventory(path: Path) -> tuple[dict[str, int], dict[str, object] | None, str | None]:
    if not path.exists():
        return {}, None, "state database is missing"
    try:
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        connection.execute("PRAGMA query_only = ON")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        rows = connection.execute(
            "SELECT id, model_provider, archived FROM threads ORDER BY id"
        ).fetchall()
        connection.close()
    except sqlite3.Error as exc:
        return {}, None, f"{type(exc).__name__}: {exc}"
    counts: dict[str, int] = {}
    digest = hashlib.sha256()
    for thread_id, provider, archived in rows:
        counts[str(provider)] = counts.get(str(provider), 0) + 1
        digest.update(f"{thread_id}\0{provider}\0{archived}\n".encode())
    return counts, {"total": len(rows), "sha256": digest.hexdigest(), "integrity": integrity}, None


def dominant_provider(counts: dict[str, int]) -> str | None:
    if not counts:
        return None
    return max(counts, key=lambda item: (counts[item], item))


def config_diff(path: Path, before: str, after: str, context: int = 3) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
            n=context,
        )
    )


def replace_yaml_section_bool(text: str, section: str, key: str, value: bool) -> str:
    lines = text.splitlines(keepends=True)
    section_pattern = re.compile(rf"^{re.escape(section)}:\s*(?:#.*)?$")
    key_pattern = re.compile(rf"^(\s+){re.escape(key)}:\s*(?:true|false)\s*(?:#.*)?$", re.IGNORECASE)
    section_start = next((index for index, line in enumerate(lines) if section_pattern.match(line.rstrip("\n"))), None)
    rendered = "true" if value else "false"
    if section_start is None:
        suffix = "" if not text or text.endswith("\n") else "\n"
        return f"{text}{suffix}{section}:\n  {key}: {rendered}\n"
    section_end = next(
        (
            index
            for index in range(section_start + 1, len(lines))
            if lines[index].strip()
            and not lines[index].lstrip().startswith("#")
            and not lines[index][0].isspace()
        ),
        len(lines),
    )
    for index in range(section_start + 1, section_end):
        match = key_pattern.match(lines[index].rstrip("\n"))
        if match:
            lines[index] = f"{match.group(1)}{key}: {rendered}\n"
            return "".join(lines)
    lines.insert(section_start + 1, f"  {key}: {rendered}\n")
    return "".join(lines)


def yaml_section_bool(text: str, section: str, key: str) -> bool | None:
    lines = text.splitlines()
    section_pattern = re.compile(rf"^{re.escape(section)}:\s*(?:#.*)?$")
    key_pattern = re.compile(rf"^\s+{re.escape(key)}:\s*(true|false)\s*(?:#.*)?$", re.IGNORECASE)
    section_start = next((index for index, line in enumerate(lines) if section_pattern.match(line)), None)
    if section_start is None:
        return None
    for line in lines[section_start + 1 :]:
        if line.strip() and not line.lstrip().startswith("#") and not line[0].isspace():
            break
        match = key_pattern.match(line)
        if match:
            return match.group(1).lower() == "true"
    return None


def replace_provider_block(text: str, provider_id: str, block: str) -> str:
    lines = text.splitlines(keepends=True)
    root = f"model_providers.{provider_id}"
    start = None
    end = None
    for index, line in enumerate(lines):
        match = re.match(r"^\s*\[([^]]+)\]\s*$", line)
        if match and match.group(1) == root:
            start = index
            continue
        if start is not None and match:
            section = match.group(1)
            if section != root and not section.startswith(root + "."):
                end = index
                break
    if start is None:
        prefix = text.rstrip() + ("\n\n" if text.strip() else "")
        return prefix + block.rstrip() + "\n"
    if end is None:
        end = len(lines)
    replacement = [line + "\n" for line in block.rstrip().splitlines()]
    if end < len(lines):
        replacement.append("\n")
    return "".join(lines[:start] + replacement + lines[end:])


def ruby_helper_source(proxy_config: Path) -> str:
    return f'''#!/usr/bin/ruby
require "yaml"

config = YAML.safe_load(File.read({json.dumps(str(proxy_config))}), aliases: true)
keys = Array(config["api-keys"]).map(&:to_s).reject(&:empty?)
abort "CLIProxyAPI client key is missing" if keys.empty?
STDOUT.write(keys.first)
'''


def python_helper_source(proxy_config: Path) -> str:
    return f'''#!/usr/bin/env python3
from pathlib import Path
import sys

text = Path({json.dumps(str(proxy_config))}).read_text(encoding="utf-8")
keys = []
in_keys = False
quotes = chr(39) + chr(34)
for raw in text.splitlines():
    stripped = raw.strip()
    if stripped.startswith("api-keys:"):
        in_keys = True
        rest = stripped.split(":", 1)[1].strip()
        if rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            if inner:
                keys.append(inner.strip(quotes))
            break
        if rest:
            keys.append(rest.strip(quotes))
            break
        continue
    if in_keys:
        if stripped.startswith("-"):
            item = stripped[1:].strip().strip(quotes)
            if item:
                keys.append(item)
            continue
        if stripped and not stripped.startswith("#"):
            break
if not keys:
    sys.exit("CLIProxyAPI client key is missing")
sys.stdout.write(keys[0])
'''


def helper_source(proxy_config: Path, helper_path: Path) -> str:
    if helper_path.suffix.lower() == ".rb":
        return ruby_helper_source(proxy_config)
    return python_helper_source(proxy_config)


def chatgpt_auth_state(path: Path) -> tuple[dict[str, object], str | None]:
    try:
        payload = read_json(path)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        return {}, f"{type(exc).__name__}"
    if not isinstance(payload, dict):
        return {}, "auth root is not an object"
    tokens = payload.get("tokens")
    token_fields = ("id_token", "access_token", "refresh_token")
    has_tokens = isinstance(tokens, dict) and all(
        isinstance(tokens.get(field), str) and bool(tokens.get(field)) for field in token_fields
    )
    return {
        "mode": payload.get("auth_mode"),
        "chatgpt_tokens_present": has_tokens,
        "mode_on_disk": mode(path),
    }, None


def transparent_health_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/__codex_bridge_health", "", "", ""))


def wait_for_transparent_proxy(base_url: str, attempts: int = 20) -> bool:
    request = urllib.request.Request(transparent_health_url(base_url))
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                payload = json.load(response)
            if response.status == 200 and payload.get("status") == "ok":
                return True
        except (OSError, ValueError, urllib.error.URLError):
            time.sleep(0.2)
    return False


def launch_agent_source(node: Path, runtime: Path, helper: Path, transparent_url: str, upstream_url: str) -> str:
    transparent = urllib.parse.urlparse(transparent_url)
    upstream = urllib.parse.urlparse(upstream_url)
    command, helper_args = helper_invocation(helper)
    payload = {
        "Label": TRANSPARENT_LAUNCH_LABEL,
        "ProgramArguments": [str(node), str(runtime)],
        "EnvironmentVariables": {
            "CODEX_BRIDGE_HELPER": str(helper),
            "CODEX_BRIDGE_HELPER_CMD": command,
            "CODEX_BRIDGE_HELPER_ARGS": json.dumps(helper_args[:-1]),
            "CODEX_BRIDGE_LISTEN_PORT": str(transparent.port or 8318),
            "CODEX_BRIDGE_UPSTREAM_PORT": str(upstream.port or 8317),
        },
        "RunAtLoad": True,
        "KeepAlive": True,
        "ProcessType": "Background",
        "ThrottleInterval": 5,
    }
    return plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True).decode("utf-8")


def start_detached_proxy(
    node: Path,
    runtime: Path,
    helper: Path,
    transparent_url: str,
    upstream_url: str,
) -> str | None:
    transparent = urllib.parse.urlparse(transparent_url)
    upstream = urllib.parse.urlparse(upstream_url)
    command, helper_args = helper_invocation(helper)
    env = os.environ.copy()
    env["CODEX_BRIDGE_HELPER"] = str(helper)
    env["CODEX_BRIDGE_HELPER_CMD"] = command
    env["CODEX_BRIDGE_HELPER_ARGS"] = json.dumps(helper_args[:-1])
    env["CODEX_BRIDGE_LISTEN_PORT"] = str(transparent.port or 8318)
    env["CODEX_BRIDGE_UPSTREAM_PORT"] = str(upstream.port or 8317)
    kwargs: dict[str, object] = {
        "args": [str(node), str(runtime)],
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "env": env,
        "close_fds": True,
    }
    if is_windows():
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    else:
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen(**kwargs)
    except OSError as exc:
        return f"failed to start transparent proxy: {type(exc).__name__}"
    return None


def start_transparent_proxy(
    node: Path,
    runtime: Path,
    helper: Path,
    transparent_url: str,
    upstream_url: str,
    launch_agent_path: Path,
) -> str | None:
    if platform.system() == "Darwin":
        launch_agent_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        atomic_write(
            launch_agent_path,
            launch_agent_source(node, runtime, helper, transparent_url, upstream_url),
            0o600,
        )
        return start_launch_agent(launch_agent_path)
    return start_detached_proxy(node, runtime, helper, transparent_url, upstream_url)


def start_launch_agent(path: Path) -> str | None:
    domain = f"gui/{os.getuid()}"
    target = f"{domain}/{TRANSPARENT_LAUNCH_LABEL}"
    loaded = subprocess.run(
        ["/bin/launchctl", "print", target],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0
    command = ["/bin/launchctl", "kickstart", "-k", target] if loaded else [
        "/bin/launchctl",
        "bootstrap",
        domain,
        str(path),
    ]
    proc = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return None if proc.returncode == 0 else "launchctl failed to start the transparent proxy"


def restart_cliproxyapi(brew: Path) -> str | None:
    try:
        proc = subprocess.run(
            [str(brew), "services", "restart", "cliproxyapi"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"CLIProxyAPI restart failed: {type(exc).__name__}"
    return None if proc.returncode == 0 else "CLIProxyAPI restart failed"


def wait_for_models(base_url: str, attempts: int = 30) -> bool:
    request = urllib.request.Request(f"{base_url.rstrip('/')}/models", headers={"Authorization": "Bearer probe"})
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                payload = json.load(response)
            if response.status == 200 and isinstance(payload.get("data"), list):
                return True
        except (OSError, ValueError, urllib.error.URLError):
            time.sleep(0.2)
    return False


def cmd_configure_multi_agent(args: argparse.Namespace) -> None:
    proxy_config = Path(args.proxy_config).expanduser()
    brew = Path(args.brew).expanduser()
    if not is_loopback(args.transparent_url):
        emit({"status": "blocked", "error": "transparent URL must be loopback-only"}, 2)
    try:
        current = proxy_config.read_text(encoding="utf-8")
    except OSError as exc:
        emit({"status": "blocked", "error": f"CLIProxyAPI config is unavailable: {type(exc).__name__}"}, 2)
    current_sha = hashlib.sha256(current.encode()).hexdigest()
    if args.expected_sha256 and current_sha != args.expected_sha256:
        emit(
            {
                "status": "blocked",
                "error": "CLIProxyAPI config changed after approval",
                "expected_sha256": args.expected_sha256,
                "actual_sha256": current_sha,
            },
            2,
        )
    updated = replace_yaml_section_bool(current, "codex", "optimize-multi-agent-v2", True)
    changed = updated != current
    result = {
        "status": "planned" if not args.apply else "unchanged",
        "finding_id": "models.codex_multi_agent_v2_compat_disabled",
        "proxy_config": str(proxy_config),
        "config_sha256": current_sha,
        "diff": config_diff(proxy_config, current, updated, context=0),
        "multi_agent_v2_compat": True,
        "backup": None,
        "restarted": False,
        "secrets_redacted": True,
    }
    if not args.apply:
        emit(result)
    if changed:
        result["backup"] = str(backup(proxy_config))
        atomic_write(proxy_config, updated, 0o600)
        result["status"] = "applied"
    verified = proxy_config.read_text(encoding="utf-8")
    if yaml_section_bool(verified, "codex", "optimize-multi-agent-v2") is not True:
        emit({"status": "blocked", "error": "post-write multi-agent compatibility verification failed"}, 2)
    if not args.skip_restart:
        restart_error = None
        if changed:
            if platform.system() == "Darwin" and brew.exists():
                restart_error = restart_cliproxyapi(brew)
                result["restarted"] = restart_error is None
            else:
                result["restarted"] = False
                result["restart_hint"] = "restart the local CLIProxyAPI process, then rerun audit"
        if restart_error:
            emit({"status": "blocked", "error": restart_error}, 2)
        if not wait_for_models(args.transparent_url):
            emit(
                {
                    "status": "blocked",
                    "error": "CLIProxyAPI did not become healthy",
                    "restart_hint": result.get("restart_hint"),
                },
                2,
            )
    emit(result)


def cmd_probe_multi_agent(args: argparse.Namespace) -> None:
    if not is_loopback(args.transparent_url):
        emit({"status": "blocked", "error": "transparent URL must be loopback-only"}, 2)
    models = [item.strip() for item in args.models.split(",") if item.strip()]
    if not models:
        emit({"status": "blocked", "error": "--models is required"}, 2)
    results: dict[str, dict] = {}
    for model in models:
        payload = {
            "model": model,
            "input": [
                {
                    "type": "agent_message",
                    "id": "amsg_00000000-0000-4000-8000-000000000001",
                    "author": "/root",
                    "recipient": "/root/compat_probe",
                    "content": [
                        {"type": "input_text", "text": "Message Type: NEW_TASK\nPayload:\n"},
                        {"type": "encrypted_content", "encrypted_content": "Reply exactly: CODEX_MULTI_AGENT_OK"},
                    ],
                    "internal_chat_message_metadata_passthrough": {
                        "turn_id": "00000000-0000-4000-8000-000000000002"
                    },
                }
            ],
            "stream": False,
        }
        request = urllib.request.Request(
            f"{args.transparent_url.rstrip('/')}/responses",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": "Bearer codex-bridge-probe",
                "Content-Type": "application/json",
                "User-Agent": "Codex Desktop/0.147.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                response.read()
            results[model] = {"ok": response.status == 200, "status": response.status, "error": None}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            results[model] = {
                "ok": False,
                "status": exc.code,
                "error": "unsupported Codex agent_message input" if "ModelInput" in body else "upstream rejected the probe",
            }
        except (OSError, TimeoutError) as exc:
            results[model] = {"ok": False, "status": None, "error": type(exc).__name__}
    passed = all(item["ok"] for item in results.values())
    emit({"status": "passed" if passed else "failed", "results": results, "secrets_redacted": True}, 0 if passed else 2)


def cmd_configure_desktop(args: argparse.Namespace) -> None:
    config_path = Path(args.config).expanduser()
    state_db = Path(args.state_db).expanduser()
    catalog_path = Path(args.catalog).expanduser()
    auth_path = Path(args.auth_file).expanduser()
    helper_path = Path(args.helper).expanduser()
    runtime_path = Path(args.runtime_script).expanduser()
    launch_agent_path = Path(args.launch_agent).expanduser()
    node_path = Path(args.node).expanduser()

    if not is_loopback(args.proxy_url) or not is_loopback(args.transparent_url):
        emit({"status": "blocked", "error": "both proxy URLs must be loopback-only"}, 2)
    if urllib.parse.urlparse(args.proxy_url).netloc == urllib.parse.urlparse(args.transparent_url).netloc:
        emit({"status": "blocked", "error": "transparent and authenticated proxy endpoints must differ"}, 2)
    config, config_error = load_config(config_path)
    if config_error:
        emit({"status": "blocked", "error": f"Codex config is invalid: {config_error}"}, 2)
    counts, inventory_before, inventory_error = thread_inventory(state_db)
    if inventory_error or not inventory_before:
        emit({"status": "blocked", "error": inventory_error or "thread inventory is empty"}, 2)
    history_provider = dominant_provider(counts)
    if history_provider != "openai":
        emit(
            {
                "status": "blocked",
                "error": "desktop-transparent mode requires openai to own the majority of task history",
                "provider_counts": counts,
            },
            2,
        )
    auth, auth_error = chatgpt_auth_state(auth_path)
    if auth_error or auth.get("mode") != "chatgpt" or not auth.get("chatgpt_tokens_present"):
        emit(
            {
                "status": "blocked",
                "error": "a healthy ChatGPT login is required before desktop-transparent mode",
                "auth": auth,
            },
            2,
        )
    if not helper_path.exists() or not node_path.exists():
        emit({"status": "blocked", "error": "Node.js or the CLIProxyAPI credential helper is missing"}, 2)
    try:
        catalog_ids = {entry["slug"] for entry in catalog_models(catalog_path)}
    except Exception as exc:
        emit({"status": "blocked", "error": f"model catalog is invalid: {type(exc).__name__}"}, 2)
    if args.default_model and args.default_model not in catalog_ids:
        emit({"status": "blocked", "error": "default model is absent from the proxy catalog"}, 2)

    current = config_path.read_text(encoding="utf-8")
    current_sha = hashlib.sha256(current.encode()).hexdigest()
    if args.expected_sha256 and current_sha != args.expected_sha256:
        emit(
            {
                "status": "blocked",
                "error": "config changed after approval",
                "expected_sha256": args.expected_sha256,
                "actual_sha256": current_sha,
            },
            2,
        )
    updated = replace_top_scalar(current, "model_provider", "openai")
    updated = replace_top_scalar(updated, "openai_base_url", args.transparent_url)
    updated = replace_top_scalar(updated, "model_catalog_json", str(catalog_path))
    if args.default_model:
        updated = replace_top_scalar(updated, "model", args.default_model)
    diff = config_diff(config_path, current, updated)
    result = {
        "status": "planned" if not args.apply else "unchanged",
        "finding_id": "models.desktop_transparent_proxy_missing",
        "config": str(config_path),
        "config_sha256": current_sha,
        "diff": diff,
        "provider_counts": counts,
        "thread_inventory_before": inventory_before,
        "auth": auth,
        "catalog": str(catalog_path),
        "catalog_model_count": len(catalog_ids),
        "transparent_url": args.transparent_url,
        "authenticated_upstream": args.proxy_url,
        "runtime_script": str(runtime_path),
        "launch_agent": str(launch_agent_path),
        "backup": None,
        "secrets_redacted": True,
    }
    if not args.apply:
        emit(result)

    runtime_source = (SKILL_DIR / "scripts" / "transparent_proxy.mjs").read_text(encoding="utf-8")
    runtime_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    atomic_write(runtime_path, runtime_source, 0o700)
    launch_error = start_transparent_proxy(
        node_path,
        runtime_path,
        helper_path,
        args.transparent_url,
        args.proxy_url,
        launch_agent_path,
    )
    if launch_error or not wait_for_transparent_proxy(args.transparent_url):
        emit({"status": "blocked", "error": launch_error or "transparent proxy health check failed"}, 2)

    if updated != current:
        result["backup"] = str(backup(config_path))
        atomic_write(config_path, updated, 0o600)
        result["status"] = "applied"
    verified, verify_error = load_config(config_path)
    if (
        verify_error
        or verified.get("model_provider", "openai") != "openai"
        or verified.get("openai_base_url") != args.transparent_url
        or verified.get("model_catalog_json") != str(catalog_path)
    ):
        emit({"status": "blocked", "error": "post-write config verification failed"}, 2)
    _, inventory_after, after_error = thread_inventory(state_db)
    if after_error or inventory_after != inventory_before:
        emit({"status": "blocked", "error": "thread inventory changed during desktop configuration"}, 2)
    result["thread_inventory_after"] = inventory_after
    result["transparent_proxy_healthy"] = True
    emit(result)


def cmd_audit(args: argparse.Namespace) -> None:
    config_path = Path(args.config).expanduser()
    profile_path = Path(args.profile_config).expanduser()
    state_db = Path(args.state_db).expanduser()
    config, config_error = load_config(config_path)
    profile, profile_error = load_config(profile_path)
    default_provider = config.get("model_provider", "openai")
    root_base_url = config.get("openai_base_url")
    transparent_mode = (
        default_provider == "openai" and isinstance(root_base_url, str) and bool(root_base_url)
    )
    provider = provider_from_config(profile)
    base_url = root_base_url if transparent_mode else provider.get("base_url")
    base_url = base_url if isinstance(base_url, str) else None
    catalog_raw = config.get("model_catalog_json") if transparent_mode else profile.get("model_catalog_json")
    catalog_path = Path(catalog_raw).expanduser() if isinstance(catalog_raw, str) else None
    provider_counts, inventory, inventory_error = thread_inventory(state_db)
    history_provider = dominant_provider(provider_counts)
    auth, auth_error = chatgpt_auth_state(Path(args.auth_file).expanduser())
    proxy_config_path = Path(args.proxy_config).expanduser()
    try:
        proxy_multi_agent_compat = yaml_section_bool(
            proxy_config_path.read_text(encoding="utf-8"), "codex", "optimize-multi-agent-v2"
        )
    except OSError:
        proxy_multi_agent_compat = None
    findings: list[str] = []
    if config_error:
        findings.append(f"config: {config_error}")
    if profile_error and not transparent_mode:
        findings.append(f"profile: {profile_error}")
    if inventory_error:
        findings.append(f"thread inventory: {inventory_error}")
    if config_path.exists() and not owner_mode_ok(config_path, 0o600):
        findings.append("config.toml is not mode 0600")
    if profile_path.exists() and not owner_mode_ok(profile_path, 0o600):
        findings.append(f"{profile_path.name} is not mode 0600")
    if history_provider and default_provider != history_provider:
        findings.append("default Provider hides the majority of indexed thread history")
    if transparent_mode:
        if auth_error or auth.get("mode") != "chatgpt" or not auth.get("chatgpt_tokens_present"):
            findings.append("desktop-transparent mode is missing a healthy ChatGPT login")
        if not base_url or not is_loopback(base_url):
            findings.append("transparent OpenAI base URL is missing or not loopback-only")
        if proxy_multi_agent_compat is not True:
            findings.append("CLIProxyAPI Codex multi-agent v2 compatibility is disabled")
        token, token_error = ("codex-bridge-audit", None)
    else:
        if profile.get("model_provider") != PROVIDER_ID:
            findings.append(f"bridge profile model_provider is not {PROVIDER_ID}")
        if not base_url or not is_loopback(base_url):
            findings.append("custom Provider is missing or not loopback-only")
        if provider.get("wire_api", "responses") != "responses":
            findings.append("custom Provider wire_api is not responses")
        token, token_error = token_from_provider(provider) if provider else (None, "Provider missing")
    live_ids: set[str] = set()
    live_error = token_error
    if token and base_url:
        try:
            live_ids = live_model_ids(base_url, token, Path(args.models_file) if args.models_file else None)
            live_error = None
        except Exception as exc:  # errors are redacted to type/status only
            live_error = f"{type(exc).__name__}"
            if isinstance(exc, urllib.error.HTTPError):
                live_error += f" status={exc.code}"
    catalog_ids: list[str] = []
    catalog_error = None
    if catalog_path:
        try:
            catalog_ids = [entry["slug"] for entry in catalog_models(catalog_path)]
        except Exception as exc:
            catalog_error = f"{type(exc).__name__}: {exc}"
            findings.append("model catalog is invalid")
    else:
        findings.append("model_catalog_json is not configured")
    state_path = Path(args.state_dir).expanduser() / "state.json"
    state = read_json(state_path, {"managed_model_ids": []})
    managed = sorted(set(state.get("managed_model_ids", []))) if isinstance(state, dict) else []
    catalog_entries = catalog_models(catalog_path) if catalog_path and not catalog_error else []
    required_routes = required_live_routes(catalog_entries, managed, config.get("model") if isinstance(config.get("model"), str) else None)
    missing_routes = sorted(model for model in required_routes if live_ids and model not in live_ids)
    if missing_routes:
        findings.append("visible or default catalog models are missing from the live proxy")
    codex_version = None
    try:
        codex_version = subprocess.run(
            [args.codex, "--version"], capture_output=True, text=True, timeout=5, check=False
        ).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        findings.append("Codex CLI is unavailable")
    proxy_version_text, proxy_version_tuple = proxy_version(Path(args.proxy_binary).expanduser())
    if proxy_version_tuple is None:
        findings.append("CLIProxyAPI version is unavailable")
    elif "grok-4.6" in managed and proxy_version_tuple < MIN_TOOL_SAFE_PROXY_VERSION:
        findings.append(
            "CLIProxyAPI is older than 7.2.130; Grok Responses tool and multi-agent probes are required"
        )
    emit(
        {
            "status": "ready" if not findings and not live_error else "attention",
            "codex": {
                "version": codex_version,
                "config": str(config_path),
                "config_mode": mode(config_path),
                "model": config.get("model"),
                "model_provider": default_provider,
                "bridge_mode": "desktop-transparent" if transparent_mode else "isolated-profile",
                "openai_base_url": root_base_url if transparent_mode else None,
                "service_tier": config.get("service_tier"),
            },
            "auth": auth,
            "history": {
                "state_db": str(state_db),
                "provider_counts": provider_counts,
                "dominant_provider": history_provider,
                "inventory": inventory,
                "error": inventory_error,
            },
            "profile": {
                "name": args.profile,
                "config": str(profile_path),
                "config_mode": mode(profile_path),
                "model": profile.get("model"),
                "model_provider": profile.get("model_provider"),
            },
            "provider": {
                "id": "openai" if transparent_mode else PROVIDER_ID,
                "base_url": base_url,
                "loopback_only": bool(base_url and is_loopback(base_url)),
                "wire_api": "responses" if transparent_mode else provider.get("wire_api", "responses") if provider else None,
                "command_auth": False if transparent_mode else isinstance(provider.get("auth"), dict) if provider else False,
                "live_model_count": len(live_ids),
                "live_error": live_error,
                "multi_agent_v2_compat": proxy_multi_agent_compat,
                "version": proxy_version_text,
                "minimum_tool_safe_version": ".".join(
                    str(part) for part in MIN_TOOL_SAFE_PROXY_VERSION
                ),
            },
            "catalog": {
                "path": str(catalog_path) if catalog_path else None,
                "mode": mode(catalog_path) if catalog_path else None,
                "model_count": len(catalog_ids),
                "managed_model_ids": managed,
                "missing_live_routes": missing_routes,
                "error": catalog_error,
            },
            "findings": findings,
            "secrets_redacted": True,
        },
        0 if not findings and not live_error else 2,
    )


def cmd_configure(args: argparse.Namespace) -> None:
    profile_path = Path(args.profile_config).expanduser()
    catalog_path = Path(args.catalog).expanduser()
    helper_path = Path(args.helper).expanduser()
    proxy_config = Path(args.proxy_config).expanduser()
    if not is_loopback(args.proxy_url):
        emit({"status": "blocked", "error": "proxy URL must be loopback-only"}, 2)
    current = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
    updated = replace_top_scalar(current, "model_provider", PROVIDER_ID)
    updated = replace_top_scalar(updated, "model_catalog_json", str(catalog_path))
    if args.default_model:
        updated = replace_top_scalar(updated, "model", args.default_model)
    command, helper_args = helper_invocation(helper_path)
    block = f'''[model_providers.{PROVIDER_ID}]
name = "CLI Proxy API"
base_url = {json.dumps(args.proxy_url)}
wire_api = "responses"
request_max_retries = 4
stream_max_retries = 5
stream_idle_timeout_ms = 300000

[model_providers.{PROVIDER_ID}.auth]
command = {json.dumps(command)}
args = {json.dumps(helper_args)}
timeout_ms = 5000
refresh_interval_ms = 300000'''
    updated = replace_provider_block(updated, PROVIDER_ID, block)
    changed = updated != current or not helper_path.exists()
    result = {
        "status": "planned" if not args.apply else "unchanged",
        "changes": {"config": updated != current, "credential_helper": not helper_path.exists()},
        "backup": None,
        "profile": {"name": args.profile, "config": str(profile_path)},
        "default_config_unchanged": True,
        "provider": {"id": PROVIDER_ID, "base_url": args.proxy_url, "wire_api": "responses"},
        "secrets_redacted": True,
    }
    if args.apply and changed:
        if profile_path.exists() and updated != current:
            result["backup"] = str(backup(profile_path))
        atomic_write(profile_path, updated, 0o600)
        helper_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        atomic_write(helper_path, helper_source(proxy_config, helper_path), 0o700)
        result["status"] = "applied"
    emit(result)


def cmd_restore_default(args: argparse.Namespace) -> None:
    config_path = Path(args.config).expanduser()
    state_db = Path(args.state_db).expanduser()
    native_path = Path(args.native_catalog).expanduser()
    config, config_error = load_config(config_path)
    if config_error:
        emit({"status": "blocked", "error": f"Codex config is invalid: {config_error}"}, 2)
    counts, inventory_before, inventory_error = thread_inventory(state_db)
    if inventory_error or not inventory_before:
        emit({"status": "blocked", "error": inventory_error or "thread inventory is empty"}, 2)
    target_provider = args.provider or dominant_provider(counts)
    if not target_provider:
        emit({"status": "blocked", "error": "cannot determine the history Provider"}, 2)
    largest = max(counts.values()) if counts else 0
    if counts.get(target_provider, 0) < largest and not args.allow_minority_provider:
        emit(
            {
                "status": "blocked",
                "error": "target Provider is not the dominant thread-history Provider",
                "provider_counts": counts,
            },
            2,
        )
    native_models = catalog_models(native_path)
    native_ids = {entry["slug"] for entry in native_models}
    target_model = args.model or config.get("model")
    if target_model not in native_ids:
        target_model = "gpt-5.6-sol" if "gpt-5.6-sol" in native_ids else native_models[0]["slug"]
    current = config_path.read_text(encoding="utf-8")
    current_sha = hashlib.sha256(current.encode()).hexdigest()
    if args.expected_sha256 and current_sha != args.expected_sha256:
        emit(
            {
                "status": "blocked",
                "error": "config changed after approval",
                "expected_sha256": args.expected_sha256,
                "actual_sha256": current_sha,
            },
            2,
        )
    updated = replace_top_scalar(current, "model_provider", target_provider)
    updated = replace_top_scalar(updated, "model", target_model)
    updated = remove_top_scalar(updated, "model_catalog_json")
    updated = remove_top_scalar(updated, "openai_base_url")
    diff = config_diff(config_path, current, updated)
    result = {
        "status": "planned" if not args.apply else "unchanged",
        "finding_id": "threads.default_provider_history_scope_mismatch",
        "config": str(config_path),
        "config_sha256": current_sha,
        "diff": diff,
        "provider_counts": counts,
        "target_provider": target_provider,
        "target_model": target_model,
        "thread_inventory_before": inventory_before,
        "backup": None,
        "secrets_redacted": True,
    }
    if args.apply and updated != current:
        result["backup"] = str(backup(config_path))
        atomic_write(config_path, updated, 0o600)
        verified, verify_error = load_config(config_path)
        if verify_error or verified.get("model_provider", "openai") != target_provider:
            emit({"status": "blocked", "error": "post-write config verification failed"}, 2)
        _, inventory_after, after_error = thread_inventory(state_db)
        if after_error or inventory_after != inventory_before:
            emit({"status": "blocked", "error": "thread inventory changed during config repair"}, 2)
        result["thread_inventory_after"] = inventory_after
        result["status"] = "applied"
    emit(result)


def cmd_sync(args: argparse.Namespace) -> None:
    config, config_error = load_config(Path(args.config).expanduser())
    if config_error:
        emit({"status": "blocked", "error": f"Codex config is invalid: {config_error}"}, 2)
    provider = provider_from_config(config)
    base_url = provider.get("base_url", DEFAULT_PROXY_URL)
    if not is_loopback(base_url):
        emit({"status": "blocked", "error": "active Provider is not loopback-only"}, 2)
    selected = {item.strip() for item in args.models.split(",") if item.strip()} if args.models else None
    paths = manifest_paths(selected)
    manifests: list[dict] = []
    manifest_errors: dict[str, list[str]] = {}
    for path in paths:
        data = read_json(path)
        errors = validate_manifest(data) if isinstance(data, dict) else ["manifest root must be an object"]
        if errors:
            manifest_errors[str(path)] = errors
        else:
            manifests.append(data)
    if selected:
        found = {item["slug"] for item in manifests}
        for missing in sorted(selected - found):
            manifest_errors[missing] = ["no manifest found"]
    if manifest_errors:
        emit({"status": "blocked", "manifest_errors": manifest_errors}, 2)
    live_ids: set[str] = set()
    if not args.skip_live_check:
        token, error = token_from_provider(provider)
        if error or not token:
            emit({"status": "blocked", "error": error or "credential helper failed"}, 2)
        try:
            live_ids = live_model_ids(base_url, token, Path(args.models_file) if args.models_file else None)
        except Exception as exc:
            emit({"status": "blocked", "error": f"live model discovery failed: {type(exc).__name__}"}, 2)
    unavailable = sorted(item["slug"] for item in manifests if live_ids and item["slug"] not in live_ids)
    if unavailable:
        emit({"status": "blocked", "missing_live_routes": unavailable, "secrets_redacted": True}, 2)
    native_path = Path(args.native_catalog).expanduser()
    target_path = Path(args.catalog).expanduser()
    policy_path = Path(args.catalog_policy).expanduser()
    try:
        policy = catalog_policy(policy_path)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        emit({"status": "blocked", "error": f"catalog policy is invalid: {exc}", "policy": str(policy_path)}, 2)
    hidden_native_ids = set(policy["hidden_native_model_ids"])
    protected_native_ids = set(policy["protected_native_model_ids"])
    native = catalog_models(native_path)
    current = catalog_models(target_path) if target_path.exists() else copy.deepcopy(native)
    native_map = {entry["slug"]: entry for entry in native}
    current_map = {entry["slug"]: entry for entry in current}
    state_path = Path(args.state_dir).expanduser() / "state.json"
    state = read_json(state_path, {"schema_version": 1, "managed_model_ids": []})
    managed_before = set(state.get("managed_model_ids", [])) if isinstance(state, dict) else set()
    desired: dict[str, dict] = {}
    superseded: set[str] = set()
    for manifest in manifests:
        desired[manifest["slug"]] = build_entry(manifest, native_map)
        superseded.update(manifest.get("supersedes", []))
    protected_conflicts = protected_supersede_conflicts(manifests, policy)
    if protected_conflicts:
        emit(
            {
                "status": "blocked",
                "error": "managed manifests may not supersede native model IDs required by Codex thread creation",
                "protected_native_conflicts": protected_conflicts,
            },
            2,
        )
    conflicts = sorted(slug for slug in desired if slug in current_map and slug not in managed_before and slug not in native_map)
    if conflicts and not args.adopt:
        emit(
            {
                "status": "blocked",
                "conflicts": conflicts,
                "hint": "rerun with --adopt only if this private Skill should own these exact slugs",
            },
            2,
        )
    kept: list[dict] = []
    desired_ids = set(desired)
    for entry in native:
        if entry["slug"] not in desired_ids and entry["slug"] not in superseded:
            native_entry = copy.deepcopy(entry)
            if native_entry["slug"] in hidden_native_ids:
                native_entry["visibility"] = "hide"
            kept.append(native_entry)
    for entry in current:
        slug = entry["slug"]
        if slug in native_map or slug in desired_ids or slug in superseded:
            continue
        if slug in managed_before and args.prune_managed:
            continue
        kept.append(copy.deepcopy(entry))
    final_models = kept + [desired[manifest["slug"]] for manifest in manifests]
    final_map = {entry["slug"]: entry for entry in final_models}
    final_payload = {"models": final_models}
    current_payload = {"models": current}
    added = sorted(slug for slug in desired if slug not in current_map)
    updated_ids = sorted(slug for slug in desired if slug in current_map and current_map[slug] != desired[slug])
    removed = sorted(
        slug for slug in managed_before if args.prune_managed and slug not in desired_ids and slug in current_map
    )
    unchanged = sorted(slug for slug in desired if slug in current_map and current_map[slug] == desired[slug])
    changed = final_payload != current_payload
    result = {
        "status": "planned" if not args.apply else "unchanged",
        "catalog": str(target_path),
        "changes": {"added": added, "updated": updated_ids, "removed": removed, "unchanged": unchanged},
        "superseded_routes": sorted(superseded),
        "catalog_policy": str(policy_path),
        "protected_native_models": sorted(protected_native_ids & set(native_map)),
        "protected_native_models_not_found": sorted(protected_native_ids - set(native_map)),
        "hidden_native_models": sorted(
            slug for slug in hidden_native_ids if final_map.get(slug, {}).get("visibility") == "hide"
        ),
        "hidden_native_models_not_found": sorted(hidden_native_ids - set(native_map)),
        "managed_after": sorted(desired_ids | (managed_before - set(removed))),
        "backup": None,
        "live_routes_verified": not args.skip_live_check,
        "secrets_redacted": True,
    }
    if args.apply:
        if changed:
            if target_path.exists():
                result["backup"] = str(backup(target_path))
            atomic_write(target_path, json.dumps(final_payload, ensure_ascii=False, indent=2) + "\n", 0o600)
            result["status"] = "applied"
        next_state = {
            "schema_version": 1,
            "managed_model_ids": result["managed_after"],
            "catalog": str(target_path),
            "provider_id": PROVIDER_ID,
            "hidden_native_model_ids": sorted(hidden_native_ids),
            "protected_native_model_ids": sorted(protected_native_ids),
        }
        atomic_write(state_path, json.dumps(next_state, ensure_ascii=False, indent=2) + "\n", 0o600)
    emit(result)


def probe_prompt(shell: bool, tool_sequence: bool) -> str:
    if tool_sequence:
        return (
            "Use the shell tool twice and in this exact order: first run pwd, "
            "then run git --version. Both must succeed. After both succeed, "
            "reply with exactly CODEX_BRIDGE_TOOL_SEQUENCE_OK. "
            "Do not simulate either command and do not call any other tool."
        )
    if shell:
        return (
            "Use the shell tool to run exactly this command: pwd. "
            "After it succeeds, reply with exactly: CODEX_BRIDGE_SHELL_OK. "
            "Do not simulate the command and do not call any other tool."
        )
    return "Reply with exactly: CODEX_BRIDGE_OK"


def probe_catalog_path(args: argparse.Namespace) -> Path:
    if args.catalog:
        return Path(args.catalog).expanduser()
    if not args.desktop:
        return DEFAULT_CODEX_HOME / "model-catalog-cli-proxy.json"
    config_path = Path(args.config).expanduser()
    config, config_error = load_config(config_path)
    if config_error:
        emit(
            {
                "status": "blocked",
                "error": f"cannot read the desktop Codex config: {config_error}",
                "config": str(config_path),
            },
            2,
        )
    catalog = config.get("model_catalog_json")
    if not isinstance(catalog, str) or not catalog.strip():
        emit(
            {
                "status": "blocked",
                "error": "desktop Codex config has no model_catalog_json; pass --catalog to override",
                "config": str(config_path),
            },
            2,
        )
    return Path(catalog).expanduser()


def cmd_probe(args: argparse.Namespace) -> None:
    target_path = probe_catalog_path(args)
    entries = {entry["slug"]: entry for entry in catalog_models(target_path)}
    models = [item.strip() for item in args.models.split(",") if item.strip()]
    if not models:
        emit({"status": "blocked", "error": "--models is required"}, 2)
    results: dict[str, dict] = {}
    for model in models:
        if model not in entries:
            results[model] = {"ok": False, "error": "model is absent from the catalog"}
            continue
        if args.fast and "fast" not in entries[model].get("additional_speed_tiers", []):
            results[model] = {"ok": False, "error": "model does not advertise Fast"}
            continue
        with tempfile.TemporaryDirectory(prefix="codex-model-probe-") as temp_dir:
            output = Path(temp_dir) / "answer.txt"
            command = [
                args.codex,
                "exec",
                "--ephemeral",
                "--skip-git-repo-check",
                "--ignore-rules",
                "--sandbox",
                "read-only",
                "--model",
                model,
                "--output-last-message",
                str(output),
            ]
            if not args.desktop:
                command.extend(["--profile", args.profile])
            if args.fast:
                command.extend(["--config", 'service_tier="fast"'])
            if args.shell or args.tool_sequence:
                command.append("--json")
            prompt = probe_prompt(args.shell, args.tool_sequence)
            command.append(prompt)
            try:
                proc = subprocess.run(
                    command,
                    stdout=subprocess.PIPE if args.shell or args.tool_sequence else subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=args.timeout,
                    check=False,
                    start_new_session=True,
                )
                answer = output.read_text(encoding="utf-8").strip() if output.exists() else ""
                shell_executed = False
                tool_sequence_executed = False
                completed_commands: list[str] = []
                if args.shell or args.tool_sequence:
                    for line in proc.stdout.splitlines():
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        item = event.get("item", {})
                        command_text = item.get("command", "")
                        if (
                            event.get("type") == "item.completed"
                            and item.get("type") == "command_execution"
                            and item.get("status") == "completed"
                            and item.get("exit_code") == 0
                            and re.search(r"(?:^|[ ;])pwd(?:$|[ ;])", command_text)
                        ):
                            shell_executed = True
                        if (
                            event.get("type") == "item.completed"
                            and item.get("type") == "command_execution"
                            and item.get("status") == "completed"
                            and item.get("exit_code") == 0
                        ):
                            completed_commands.append(command_text)
                    tool_sequence_executed = (
                        len(completed_commands) >= 2
                        and re.search(r"(?:^|[ ;])pwd(?:$|[ ;])", completed_commands[0]) is not None
                        and "git --version" in completed_commands[1]
                    )
                expected = (
                    "CODEX_BRIDGE_TOOL_SEQUENCE_OK"
                    if args.tool_sequence
                    else "CODEX_BRIDGE_SHELL_OK"
                    if args.shell
                    else "CODEX_BRIDGE_OK"
                )
                execution_ok = (
                    tool_sequence_executed
                    if args.tool_sequence
                    else shell_executed
                    if args.shell
                    else True
                )
                ok = proc.returncode == 0 and expected in answer and execution_ok
                results[model] = {
                    "ok": ok,
                    "fast": bool(args.fast),
                    "shell": bool(args.shell),
                    "shell_executed": shell_executed if args.shell else None,
                    "tool_sequence": bool(args.tool_sequence),
                    "tool_sequence_executed": tool_sequence_executed if args.tool_sequence else None,
                    "exit_code": proc.returncode,
                    "error": None if ok else (
                        "Codex did not execute the required ordered shell-tool sequence"
                        if args.tool_sequence
                        else "Codex did not execute a successful pwd shell call"
                        if args.shell
                        else "Codex did not complete the expected Responses turn"
                    ),
                }
            except subprocess.TimeoutExpired:
                results[model] = {
                    "ok": False,
                    "fast": bool(args.fast),
                    "shell": bool(args.shell),
                    "error": "probe timed out",
                }
            except OSError as exc:
                results[model] = {
                    "ok": False,
                    "fast": bool(args.fast),
                    "shell": bool(args.shell),
                    "error": type(exc).__name__,
                }
    emit(
        {
            "status": "passed" if all(item["ok"] for item in results.values()) else "failed",
            "catalog": str(target_path),
            "results": results,
        },
        0 if all(item["ok"] for item in results.values()) else 2,
    )


def cmd_validate_manifest(args: argparse.Namespace) -> None:
    path = Path(args.path).expanduser()
    data = read_json(path)
    errors = validate_manifest(data) if isinstance(data, dict) else ["manifest root must be an object"]
    emit({"status": "valid" if not errors else "invalid", "path": str(path), "errors": errors}, 0 if not errors else 2)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Codex CLI model bridge")
    sub = root.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("audit")
    audit.add_argument("--config", default=str(DEFAULT_CODEX_HOME / "config.toml"))
    audit.add_argument("--profile", default=DEFAULT_PROFILE_NAME)
    audit.add_argument("--profile-config", default=str(DEFAULT_PROFILE_CONFIG))
    audit.add_argument("--state-db", default=str(DEFAULT_STATE_DB))
    audit.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR))
    audit.add_argument("--auth-file", default=str(DEFAULT_AUTH_FILE))
    audit.add_argument("--proxy-config", default=str(DEFAULT_PROXY_CONFIG))
    audit.add_argument("--models-file")
    audit.add_argument("--codex", default="codex")
    audit.add_argument("--proxy-binary", default=str(DEFAULT_PROXY_BINARY))
    audit.set_defaults(func=cmd_audit)

    configure = sub.add_parser("configure")
    configure.add_argument("--profile", default=DEFAULT_PROFILE_NAME)
    configure.add_argument("--profile-config", default=str(DEFAULT_PROFILE_CONFIG))
    configure.add_argument("--catalog", default=str(DEFAULT_CODEX_HOME / "model-catalog-cli-proxy.json"))
    configure.add_argument("--helper", default=str(DEFAULT_HELPER))
    configure.add_argument("--proxy-config", default=str(DEFAULT_PROXY_CONFIG))
    configure.add_argument("--proxy-url", default=DEFAULT_PROXY_URL)
    configure.add_argument("--default-model")
    configure.add_argument("--apply", action="store_true")
    configure.set_defaults(func=cmd_configure)

    desktop = sub.add_parser("configure-desktop")
    desktop.add_argument("--config", default=str(DEFAULT_CODEX_HOME / "config.toml"))
    desktop.add_argument("--state-db", default=str(DEFAULT_STATE_DB))
    desktop.add_argument("--catalog", default=str(DEFAULT_CODEX_HOME / "model-catalog-cli-proxy.json"))
    desktop.add_argument("--auth-file", default=str(DEFAULT_AUTH_FILE))
    desktop.add_argument("--helper", default=str(DEFAULT_HELPER))
    desktop.add_argument("--proxy-url", default=DEFAULT_PROXY_URL)
    desktop.add_argument("--transparent-url", default=DEFAULT_TRANSPARENT_PROXY_URL)
    desktop.add_argument("--runtime-script", default=str(DEFAULT_TRANSPARENT_RUNTIME))
    desktop.add_argument("--launch-agent", default=str(DEFAULT_LAUNCH_AGENT))
    desktop.add_argument("--node", default=str(default_node()))
    desktop.add_argument("--default-model", default="gpt-5.6-sol")
    desktop.add_argument("--expected-sha256")
    desktop.add_argument("--apply", action="store_true")
    desktop.set_defaults(func=cmd_configure_desktop)

    multi_agent = sub.add_parser("configure-multi-agent")
    multi_agent.add_argument("--proxy-config", default=str(DEFAULT_PROXY_CONFIG))
    multi_agent.add_argument("--transparent-url", default=DEFAULT_TRANSPARENT_PROXY_URL)
    multi_agent.add_argument("--brew", default=str(DEFAULT_BREW))
    multi_agent.add_argument("--expected-sha256")
    multi_agent.add_argument("--skip-restart", action="store_true", help="Tests only; never use for live repair")
    multi_agent.add_argument("--apply", action="store_true")
    multi_agent.set_defaults(func=cmd_configure_multi_agent)

    restore = sub.add_parser("restore-default")
    restore.add_argument("--config", default=str(DEFAULT_CODEX_HOME / "config.toml"))
    restore.add_argument("--state-db", default=str(DEFAULT_STATE_DB))
    restore.add_argument("--native-catalog", default=str(DEFAULT_CODEX_HOME / "models_cache.json"))
    restore.add_argument("--provider")
    restore.add_argument("--model")
    restore.add_argument("--expected-sha256")
    restore.add_argument("--allow-minority-provider", action="store_true")
    restore.add_argument("--apply", action="store_true")
    restore.set_defaults(func=cmd_restore_default)

    sync = sub.add_parser("sync")
    sync.add_argument("--config", default=str(DEFAULT_CODEX_HOME / "config.toml"))
    sync.add_argument("--catalog", default=str(DEFAULT_CODEX_HOME / "model-catalog-cli-proxy.json"))
    sync.add_argument("--native-catalog", default=str(DEFAULT_CODEX_HOME / "models_cache.json"))
    sync.add_argument("--catalog-policy", default=str(DEFAULT_CATALOG_POLICY))
    sync.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR))
    sync.add_argument("--models")
    sync.add_argument("--models-file")
    sync.add_argument("--adopt", action="store_true")
    sync.add_argument("--prune-managed", action="store_true")
    sync.add_argument("--skip-live-check", action="store_true", help="Tests only; never use for live setup")
    sync.add_argument("--apply", action="store_true")
    sync.set_defaults(func=cmd_sync)

    probe = sub.add_parser("probe")
    probe.add_argument("--catalog")
    probe.add_argument("--config", default=str(DEFAULT_CODEX_HOME / "config.toml"))
    probe.add_argument("--profile", default=DEFAULT_PROFILE_NAME)
    probe.add_argument("--desktop", action="store_true")
    probe.add_argument("--models", required=True)
    probe.add_argument("--fast", action="store_true")
    probe.add_argument("--shell", action="store_true", help="Require a real read-only pwd tool execution")
    probe.add_argument(
        "--tool-sequence",
        action="store_true",
        help="Require ordered successful pwd and git --version shell executions",
    )
    probe.add_argument("--timeout", type=int, default=180)
    probe.add_argument("--codex", default="codex")
    probe.set_defaults(func=cmd_probe)

    probe_multi_agent = sub.add_parser("probe-multi-agent")
    probe_multi_agent.add_argument("--transparent-url", default=DEFAULT_TRANSPARENT_PROXY_URL)
    probe_multi_agent.add_argument("--models", required=True)
    probe_multi_agent.add_argument("--timeout", type=int, default=120)
    probe_multi_agent.set_defaults(func=cmd_probe_multi_agent)

    validate = sub.add_parser("validate-manifest")
    validate.add_argument("path")
    validate.set_defaults(func=cmd_validate_manifest)
    return root


def main() -> None:
    args = parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
