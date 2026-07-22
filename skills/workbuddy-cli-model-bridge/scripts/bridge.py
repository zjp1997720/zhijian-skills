#!/usr/bin/env python3
"""Deterministic macOS bridge between CLIProxyAPI and WorkBuddy.

The script deliberately separates discovery, installation, OAuth, probing, and
WorkBuddy mutation. OAuth is always delegated to CLIProxyAPI's native login
commands; this script never reads or copies token contents.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
SKILL_DIR = Path(__file__).resolve().parents[1]
BUNDLED_PROVIDER_DIR = SKILL_DIR / "providers"
DEFAULT_STATE_RELATIVE = Path(".config/workbuddy-cli-model-bridge")
DEFAULT_WORKBUDDY_RELATIVE = Path(".workbuddy/models.json")
DEFAULT_PROXY_URL = "http://127.0.0.1:8317"


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", zlib.crc32(chunk_type + data))


def vision_probe_png(width: int = 256, height: int = 192) -> str:
    """Return a deterministic, semantically distinct image for vision probes."""
    signature = b"\x89PNG\r\n\x1a\n"
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            color = (255, 255, 255)
            if 24 <= x < 104 and 56 <= y < 136:
                color = (224, 48, 48)
            elif (x - 192) ** 2 + (y - 96) ** 2 <= 40**2:
                color = (45, 88, 220)
            rows.extend(color)
    png = signature + png_chunk(b"IHDR", header) + png_chunk(b"IDAT", zlib.compress(rows, 9)) + png_chunk(b"IEND", b"")
    return base64.b64encode(png).decode("ascii")


PROBE_IMAGE_PNG = vision_probe_png()
VISION_PROBE_EXPECTED = "LEFT=RED_SQUARE;RIGHT=BLUE_CIRCLE"


class BridgeError(RuntimeError):
    """A user-actionable bridge failure with a stable code."""

    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def redact_text(value: str) -> str:
    value = re.sub(r"(?i)(authorization:\s*bearer\s+)[^\s]+", r"\1[REDACTED]", value)
    value = re.sub(r"\bsk-[A-Za-z0-9_-]{12,}\b", "[REDACTED]", value)
    value = re.sub(r"\b[a-fA-F0-9]{48,}\b", "[REDACTED]", value)
    return value[:1200]


def emit(payload: dict[str, Any], *, pretty: bool = True) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=True))


def home_path(value: str | Path, home: Path) -> Path:
    text = os.path.expandvars(str(value))
    if text == "~":
        return home
    if text.startswith("~/"):
        return home / text[2:]
    path = Path(text)
    return path if path.is_absolute() else home / path


def atomic_write(path: Path, content: str, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def backup_file(path: Path) -> Path | None:
    if not path.is_file():
        return None
    destination = path.with_name(f"{path.name}.backup-{now_stamp()}")
    shutil.copy2(path, destination)
    os.chmod(destination, 0o600)
    return destination


def run_command(
    command: list[str],
    *,
    timeout: int = 120,
    capture: bool = True,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=capture,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BridgeError("command_failed", f"Command could not run: {command[0]}", details={"error": str(exc)}) from exc
    if check and completed.returncode != 0:
        raise BridgeError(
            "command_failed",
            f"Command failed: {command[0]}",
            details={"returncode": completed.returncode, "stderr": redact_text(completed.stderr or "")},
        )
    return completed


def command_path(candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    return None


def top_level_scalar(text: str, key: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.*?)\s*$")
    for line in text.splitlines():
        if line.startswith((" ", "\t", "#")):
            continue
        match = pattern.match(line)
        if match:
            value = match.group(1).split(" #", 1)[0].strip()
            if not value:
                return None
            if value[:1] in {'"', "'"} and value[-1:] == value[:1]:
                value = value[1:-1]
            return value
    return None


def replace_top_level_scalar(text: str, key: str, value: str) -> str:
    line_value = json.dumps(value)
    pattern = re.compile(rf"^{re.escape(key)}:\s*.*$", re.MULTILINE)
    replacement = f"{key}: {line_value}"
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    suffix = "" if text.endswith("\n") else "\n"
    return f"{text}{suffix}{replacement}\n"


def yaml_list_values(text: str, key: str) -> list[str]:
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line.startswith(f"{key}:")), None)
    if start is None:
        return []
    inline = lines[start].split(":", 1)[1].strip()
    if inline.startswith("[") and inline.endswith("]"):
        return [item.strip().strip("\"'") for item in inline[1:-1].split(",") if item.strip()]
    values: list[str] = []
    for line in lines[start + 1 :]:
        if line and not line.startswith((" ", "\t")):
            break
        match = re.match(r"^\s+-\s+(.+?)\s*$", line)
        if match:
            values.append(match.group(1).split(" #", 1)[0].strip().strip("\"'"))
    return values


def ensure_yaml_list_value(text: str, key: str, value: str) -> tuple[str, bool]:
    if value in yaml_list_values(text, key):
        return text, False
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if line.startswith(f"{key}:")), None)
    quoted = json.dumps(value)
    if start is None:
        suffix = [] if not lines or lines[-1] == "" else [""]
        return "\n".join(lines + suffix + [f"{key}:", f"  - {quoted}", ""]), True
    inline = lines[start].split(":", 1)[1].strip()
    if inline == "[]":
        lines[start] = f"{key}:"
        lines.insert(start + 1, f"  - {quoted}")
        return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), True
    if inline:
        existing = yaml_list_values(text, key)
        lines[start] = f"{key}:"
        for offset, item in enumerate(existing + [value], 1):
            lines.insert(start + offset, f"  - {json.dumps(item)}")
        return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), True
    insert_at = start + 1
    while insert_at < len(lines) and (not lines[insert_at] or lines[insert_at].startswith((" ", "\t"))):
        insert_at += 1
    lines.insert(insert_at, f"  - {quoted}")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), True


def load_json(path: Path, *, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (OSError, json.JSONDecodeError) as exc:
        raise BridgeError("invalid_json", f"Invalid JSON: {path}", details={"error": str(exc)}) from exc


def save_json(path: Path, value: Any, *, mode: int = 0o600) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n", mode=mode)


def state_paths(home: Path) -> dict[str, Path]:
    root = home / DEFAULT_STATE_RELATIVE
    return {
        "root": root,
        "state": root / "state.json",
        "secret": root / "secret.json",
        "providers": root / "providers.d",
    }


def client_secret(home: Path, *, create: bool = False) -> str | None:
    from_env = os.environ.get("WORKBUDDY_BRIDGE_API_KEY")
    if from_env:
        return from_env
    path = state_paths(home)["secret"]
    payload = load_json(path, default={}) or {}
    current = payload.get("proxy_api_key")
    if isinstance(current, str) and len(current) >= 24:
        return current
    if not create:
        return None
    current = secrets.token_hex(32)
    save_json(path, {"schema_version": SCHEMA_VERSION, "proxy_api_key": current}, mode=0o600)
    return current


def validate_provider(provider: Any, *, source: str = "provider") -> list[str]:
    errors: list[str] = []
    if not isinstance(provider, dict):
        return [f"{source}: provider must be an object"]
    if provider.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{source}: schema_version must be {SCHEMA_VERSION}")
    provider_id = provider.get("id")
    if not isinstance(provider_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", provider_id):
        errors.append(f"{source}: id must be kebab-case")
    if not isinstance(provider.get("display_name"), str):
        errors.append(f"{source}: display_name is required")
    cli = provider.get("cli")
    if not isinstance(cli, dict) or not isinstance(cli.get("commands"), list):
        errors.append(f"{source}: cli.commands must be an array")
    else:
        commands = cli["commands"]
        if not commands or any(
            not isinstance(command, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", command)
            for command in commands
        ):
            errors.append(f"{source}: cli.commands must contain safe executable basenames")
        auth_hints = cli.get("auth_hints", [])
        if not isinstance(auth_hints, list) or any(
            not isinstance(hint, str)
            or not hint
            or Path(hint).is_absolute()
            or ".." in Path(hint).parts
            for hint in auth_hints
        ):
            errors.append(f"{source}: cli.auth_hints must contain relative paths without traversal")
    cliproxy = provider.get("cliproxy")
    if not isinstance(cliproxy, dict):
        errors.append(f"{source}: cliproxy is required")
    else:
        if not isinstance(cliproxy.get("provider"), str):
            errors.append(f"{source}: cliproxy.provider is required")
        flag = cliproxy.get("login_flag")
        if flag is not None and (
            not isinstance(flag, str) or not re.fullmatch(r"--[a-z0-9][a-z0-9-]*", flag)
        ):
            errors.append(f"{source}: cliproxy.login_flag must be one literal --kebab-case flag")
        prefixes = cliproxy.get("auth_file_prefixes", [])
        if not isinstance(prefixes, list) or any(not isinstance(prefix, str) or not prefix for prefix in prefixes):
            errors.append(f"{source}: cliproxy.auth_file_prefixes must be an array of strings")
    models = provider.get("models")
    if not isinstance(models, list) or not models:
        errors.append(f"{source}: models must be a non-empty array")
    else:
        seen: set[str] = set()
        for index, model in enumerate(models):
            prefix = f"{source}: models[{index}]"
            if not isinstance(model, dict):
                errors.append(f"{prefix} must be an object")
                continue
            key = model.get("key")
            if not isinstance(key, str) or not key:
                errors.append(f"{prefix}.key is required")
            elif key in seen:
                errors.append(f"{prefix}.key is duplicated")
            else:
                seen.add(key)
            candidates = model.get("candidates")
            patterns = model.get("patterns", [])
            if (
                not isinstance(candidates, list)
                or not candidates
                or any(not isinstance(candidate, str) or not candidate for candidate in candidates)
            ):
                errors.append(f"{prefix}.candidates must be a non-empty string array")
            if not isinstance(patterns, list):
                errors.append(f"{prefix}.patterns must be an array")
            for pattern in patterns if isinstance(patterns, list) else []:
                try:
                    re.compile(pattern)
                except (TypeError, re.error):
                    errors.append(f"{prefix}.patterns contains an invalid regex")
            workbuddy = model.get("workbuddy")
            if not isinstance(workbuddy, dict):
                errors.append(f"{prefix}.workbuddy is required")
            else:
                allowed = {
                    "supportsToolCall",
                    "supportsImages",
                    "supportsReasoning",
                    "useCustomProtocol",
                    "onlyReasoning",
                    "reasoning",
                    "maxInputTokens",
                    "maxOutputTokens",
                }
                unknown = set(workbuddy) - allowed
                if unknown:
                    errors.append(f"{prefix}.workbuddy has unknown keys: {sorted(unknown)}")
                for flag_key in (
                    "supportsToolCall",
                    "supportsImages",
                    "supportsReasoning",
                    "useCustomProtocol",
                    "onlyReasoning",
                ):
                    if flag_key in workbuddy and not isinstance(workbuddy[flag_key], bool):
                        errors.append(f"{prefix}.workbuddy.{flag_key} must be boolean")
                for limit_key in ("maxInputTokens", "maxOutputTokens"):
                    if limit_key in workbuddy and (
                        not isinstance(workbuddy[limit_key], int) or isinstance(workbuddy[limit_key], bool) or workbuddy[limit_key] <= 0
                    ):
                        errors.append(f"{prefix}.workbuddy.{limit_key} must be a positive integer")
                if "reasoning" in workbuddy and not isinstance(workbuddy["reasoning"], dict):
                    errors.append(f"{prefix}.workbuddy.reasoning must be an object")
    return errors


def load_providers(home: Path) -> dict[str, dict[str, Any]]:
    providers: dict[str, dict[str, Any]] = {}
    paths = sorted(BUNDLED_PROVIDER_DIR.glob("*.json"))
    local_dir = state_paths(home)["providers"]
    paths.extend(sorted(local_dir.glob("*.json")) if local_dir.is_dir() else [])
    for path in paths:
        payload = load_json(path)
        errors = validate_provider(payload, source=str(path))
        if errors:
            raise BridgeError("invalid_provider", "Provider validation failed", details={"errors": errors})
        providers[payload["id"]] = payload
    return providers


def detect_proxy_binary(home: Path) -> str | None:
    found = command_path(("cli-proxy-api", "cliproxyapi"))
    if found:
        return found
    candidates = [
        home / "Library/Application Support/CLIProxyAPI/cli-proxy-api",
        home / "cliproxyapi/cli-proxy-api",
    ]
    return str(next((path for path in candidates if path.is_file() and os.access(path, os.X_OK)), "")) or None


def proxy_binary_version(binary: str | None) -> str | None:
    if not binary:
        return None
    try:
        completed = run_command([binary, "--version"], timeout=15)
    except BridgeError:
        return None
    rendered = (completed.stdout or completed.stderr or "").strip().splitlines()
    return redact_text(rendered[0]) if rendered else None


def process_config_path() -> Path | None:
    if platform.system() != "Darwin":
        return None
    completed = run_command(["ps", "-axo", "command="], timeout=10)
    for line in completed.stdout.splitlines():
        if "cli-proxy-api" not in line.lower():
            continue
        match = re.search(r"(?:--config|-config)\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))", line)
        if match:
            return Path(next(group for group in match.groups() if group))
    return None


def brew_prefix() -> Path | None:
    brew = shutil.which("brew")
    if not brew:
        return None
    completed = run_command([brew, "--prefix"], timeout=20)
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return Path(value) if value else None


def brew_formula_installed(brew: str) -> bool:
    completed = run_command([brew, "list", "--versions", "cliproxyapi"], timeout=30)
    return completed.returncode == 0 and bool(completed.stdout.strip())


def proxy_process_running() -> bool:
    if platform.system() != "Darwin":
        return False
    completed = run_command(["ps", "-axo", "command="], timeout=10)
    return any("cli-proxy-api" in line.lower() for line in completed.stdout.splitlines())


def detect_config(home: Path, explicit: str | None = None) -> Path | None:
    if explicit:
        return home_path(explicit, home)
    process_path = process_config_path()
    if process_path and process_path.exists():
        return process_path
    prefix = brew_prefix()
    candidates = [home / ".cli-proxy-api/config.yaml"]
    if prefix:
        candidates.insert(0, prefix / "etc/cliproxyapi.conf")
    candidates.extend((Path("/opt/homebrew/etc/cliproxyapi.conf"), Path("/usr/local/etc/cliproxyapi.conf")))
    return next((path for path in candidates if path.exists()), None)


def config_facts(path: Path | None, home: Path) -> dict[str, Any]:
    if not path or not path.is_file():
        return {"path": str(path) if path else None, "exists": False}
    text = path.read_text(encoding="utf-8")
    host = top_level_scalar(text, "host")
    port_raw = top_level_scalar(text, "port") or "8317"
    auth_dir_raw = top_level_scalar(text, "auth-dir") or "~/.cli-proxy-api"
    try:
        port = int(port_raw)
    except ValueError:
        port = 8317
    unsafe = host in {None, "", "0.0.0.0", "::", "[::]"}
    return {
        "path": str(path),
        "exists": True,
        "host": host,
        "port": port,
        "loopback_only": not unsafe and host in {"127.0.0.1", "localhost", "::1"},
        "auth_dir": str(home_path(auth_dir_raw, home)),
        "api_key_count": len(yaml_list_values(text, "api-keys")),
        "mode": oct(stat.S_IMODE(path.stat().st_mode)),
    }


def normalized_endpoint(proxy_url: str) -> str:
    return proxy_url.rstrip("/") + "/v1/chat/completions"


def http_json(
    url: str,
    api_key: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: int = 45,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        try:
            body = redact_text(exc.read().decode("utf-8", errors="replace").replace(api_key, "[REDACTED]"))
        finally:
            exc.close()
        raise BridgeError("http_error", f"HTTP {exc.code} from local proxy", details={"body": body}) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise BridgeError("proxy_unreachable", "Local proxy request failed", details={"error": str(exc.reason if hasattr(exc, "reason") else exc)}) from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise BridgeError("invalid_proxy_response", "Local proxy returned invalid JSON") from exc


def list_proxy_models(proxy_url: str, api_key: str) -> list[dict[str, Any]]:
    payload = http_json(proxy_url.rstrip("/") + "/v1/models", api_key)
    models = payload.get("data")
    if not isinstance(models, list):
        raise BridgeError("invalid_models_response", "Local proxy did not return a model list")
    return [item for item in models if isinstance(item, dict) and isinstance(item.get("id"), str)]


def provider_auth_counts(auth_dir: Path, providers: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {provider_id: 0 for provider_id in providers}
    if not auth_dir.is_dir():
        return counts
    for path in auth_dir.glob("*.json"):
        lowered = path.name.lower()
        for provider_id, provider in providers.items():
            prefixes = provider.get("cliproxy", {}).get("auth_file_prefixes", [provider_id])
            if any(lowered.startswith(str(prefix).lower()) for prefix in prefixes):
                counts[provider_id] += 1
                break
    return counts


def detect_cli(provider: dict[str, Any], home: Path) -> dict[str, Any]:
    commands = provider.get("cli", {}).get("commands", [])
    executable = command_path(commands)
    hints = [home_path(value, home) for value in provider.get("cli", {}).get("auth_hints", [])]
    return {
        "installed": bool(executable),
        "command": Path(executable).name if executable else None,
        "login_signal": any(path.exists() for path in hints),
    }


def probe_stream(endpoint: str, api_key: str, model: str) -> tuple[bool, str | None]:
    payload = {"model": model, "messages": [{"role": "user", "content": "Reply with OK."}], "stream": True, "max_tokens": 16}
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            chunk = response.read(8192)
        return (b"data:" in chunk or b"choices" in chunk), None
    except urllib.error.HTTPError as exc:
        try:
            message = f"HTTP {exc.code} from local proxy"
        finally:
            exc.close()
        return False, message
    except Exception as exc:  # urllib exposes several platform-specific timeout types
        return False, redact_text(str(exc))


def probe_json(endpoint: str, api_key: str, payload: dict[str, Any], validator) -> tuple[bool, str | None]:
    try:
        response = http_json(endpoint, api_key, payload=payload)
        if response.get("error"):
            return False, redact_text(json.dumps(response["error"], ensure_ascii=False))
        return bool(validator(response)), None
    except BridgeError as exc:
        return False, f"{exc.code}: {exc.message}"


def message_text(response: dict[str, Any]) -> str:
    try:
        content = response["choices"][0]["message"].get("content")
        return content if isinstance(content, str) else ""
    except (KeyError, IndexError, TypeError):
        return ""


def message_exists(response: dict[str, Any]) -> bool:
    return bool(message_text(response).strip())


def tool_call_exists(response: dict[str, Any]) -> bool:
    try:
        calls = response["choices"][0]["message"].get("tool_calls")
        return (
            isinstance(calls, list)
            and bool(calls)
            and calls[0].get("function", {}).get("name") == "bridge_probe"
        )
    except (KeyError, IndexError, TypeError):
        return False


def probe_model(endpoint: str, api_key: str, model: str, workbuddy: dict[str, Any]) -> dict[str, Any]:
    base = {"model": model, "max_tokens": 32, "stream": False}
    results: dict[str, Any] = {}
    ok, error = probe_json(
        endpoint,
        api_key,
        {**base, "messages": [{"role": "user", "content": "Reply with OK."}]},
        message_exists,
    )
    results["text"] = {"ok": ok, "error": error}
    stream_ok, stream_error = probe_stream(endpoint, api_key, model)
    results["stream"] = {"ok": stream_ok, "error": stream_error}
    if workbuddy.get("supportsToolCall"):
        tool_payload = {
            **base,
            "messages": [{"role": "user", "content": "Call bridge_probe with value ok."}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "bridge_probe",
                        "description": "Return the bridge probe value",
                        "parameters": {
                            "type": "object",
                            "properties": {"value": {"type": "string"}},
                            "required": ["value"],
                        },
                    },
                }
            ],
            "tool_choice": {"type": "function", "function": {"name": "bridge_probe"}},
        }
        tool_ok, tool_error = probe_json(endpoint, api_key, tool_payload, tool_call_exists)
        results["tools"] = {"ok": tool_ok, "error": tool_error}
    if workbuddy.get("supportsImages"):
        image_payload = {
            **base,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Inspect the image and answer exactly in this template: "
                                "LEFT=<COLOR>_<SHAPE>;RIGHT=<COLOR>_<SHAPE>. "
                                "Use RED or BLUE for COLOR and SQUARE or CIRCLE for SHAPE."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{PROBE_IMAGE_PNG}"}},
                    ],
                }
            ],
        }
        image_ok, image_error = probe_json(
            endpoint,
            api_key,
            image_payload,
            lambda response: re.sub(r"[`\s.]", "", message_text(response).upper()) == VISION_PROBE_EXPECTED,
        )
        results["images"] = {"ok": image_ok, "error": image_error}
    if workbuddy.get("supportsReasoning"):
        effort = workbuddy.get("reasoning", {}).get("defaultEffort", "medium")
        reasoning_payload = {
            **base,
            "messages": [{"role": "user", "content": "Reply with OK."}],
            "reasoning_effort": effort,
        }
        reasoning_ok, reasoning_error = probe_json(endpoint, api_key, reasoning_payload, message_exists)
        results["reasoning"] = {"ok": reasoning_ok, "error": reasoning_error}
    return results


def select_recommended_models(
    available: list[dict[str, Any]], providers: Iterable[dict[str, Any]]
) -> tuple[list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]], list[dict[str, Any]]]:
    by_id = {model["id"]: model for model in available}
    selected: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    missing: list[dict[str, Any]] = []
    used: set[str] = set()
    for provider in providers:
        expected_owner = provider.get("cliproxy", {}).get("provider")
        for recommendation in provider["models"]:
            match = next((by_id[item] for item in recommendation["candidates"] if item in by_id), None)
            if match is None:
                for pattern in recommendation.get("patterns", []):
                    match = next(
                        (
                            model
                            for model in available
                            if re.search(pattern, model["id"])
                            and (not expected_owner or model.get("owned_by") in {None, expected_owner})
                        ),
                        None,
                    )
                    if match:
                        break
            if match and match["id"] not in used:
                selected.append((provider, recommendation, match))
                used.add(match["id"])
            elif not recommendation.get("optional", False):
                missing.append({"provider": provider["id"], "recommendation": recommendation["key"]})
    return selected, missing


def workbuddy_entry(model_id: str, endpoint: str, api_key: str, settings: dict[str, Any]) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": model_id,
        "name": model_id,
        "vendor": "Custom",
        "url": endpoint,
        "apiKey": api_key,
        "supportsToolCall": bool(settings.get("supportsToolCall", False)),
        "supportsImages": bool(settings.get("supportsImages", False)),
        "supportsReasoning": bool(settings.get("supportsReasoning", False)),
        "useCustomProtocol": bool(settings.get("useCustomProtocol", True)),
        "onlyReasoning": bool(settings.get("onlyReasoning", False)),
    }
    for key in ("reasoning", "maxInputTokens", "maxOutputTokens"):
        if key in settings:
            entry[key] = settings[key]
    return entry


def merge_workbuddy_models(
    existing: list[dict[str, Any]],
    incoming: list[tuple[str, dict[str, Any]]],
    managed_before: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any], set[str]]:
    result = [dict(item) for item in existing]
    positions = {item.get("id"): index for index, item in enumerate(result) if isinstance(item, dict)}
    added: list[str] = []
    updated: list[str] = []
    unchanged: list[str] = []
    conflicts: list[str] = []
    managed_after = set(managed_before)
    for provider_id, entry in incoming:
        model_id = entry["id"]
        if model_id in positions and model_id not in managed_before:
            conflicts.append(model_id)
            continue
        if model_id in positions:
            if result[positions[model_id]] == entry:
                unchanged.append(model_id)
            else:
                result[positions[model_id]] = entry
                updated.append(model_id)
        else:
            positions[model_id] = len(result)
            result.append(entry)
            added.append(model_id)
        managed_after.add(model_id)
    stale = sorted(managed_before - {entry[1]["id"] for entry in incoming})
    return result, {
        "added": added,
        "updated": updated,
        "unchanged": unchanged,
        "conflicts": conflicts,
        "stale_preserved": stale,
    }, managed_after


def cmd_validate_provider(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser()
    payload = load_json(path)
    errors = validate_provider(payload, source=str(path))
    emit({"status": "pass" if not errors else "fail", "provider": payload.get("id") if isinstance(payload, dict) else None, "errors": errors})
    return 0 if not errors else 2


def cmd_audit(args: argparse.Namespace) -> int:
    home = Path(args.home).expanduser().resolve()
    providers = load_providers(home)
    binary = detect_proxy_binary(home)
    config = detect_config(home, args.config)
    facts = config_facts(config, home)
    proxy_url = args.proxy_url or (
        f"http://127.0.0.1:{facts.get('port', 8317)}" if facts.get("exists") else DEFAULT_PROXY_URL
    )
    client_key = client_secret(home)
    model_count: int | None = None
    owners: dict[str, int] = {}
    proxy_error: str | None = None
    if client_key:
        try:
            models = list_proxy_models(proxy_url, client_key)
            model_count = len(models)
            for model in models:
                owner = str(model.get("owned_by") or "unknown")
                owners[owner] = owners.get(owner, 0) + 1
        except BridgeError as exc:
            proxy_error = f"{exc.code}: {exc.message}"
    auth_dir = Path(facts.get("auth_dir") or home / ".cli-proxy-api")
    workbuddy = home / DEFAULT_WORKBUDDY_RELATIVE
    workbuddy_payload = load_json(workbuddy, default=[])
    if not isinstance(workbuddy_payload, list):
        workbuddy_payload = []
    state = load_json(state_paths(home)["state"], default={}) or {}
    findings: list[dict[str, str]] = []
    if platform.system() != "Darwin":
        findings.append({"code": "unsupported_os", "severity": "error", "message": "Version 1 supports macOS only."})
    if not shutil.which("brew"):
        findings.append({"code": "homebrew_missing", "severity": "action", "message": "Homebrew must be installed interactively."})
    if not binary:
        findings.append({"code": "cliproxy_missing", "severity": "action", "message": "CLIProxyAPI is not installed."})
    if binary and not facts.get("exists"):
        findings.append({"code": "cliproxy_config_missing", "severity": "action", "message": "CLIProxyAPI config was not found."})
    if facts.get("exists") and not facts.get("loopback_only"):
        findings.append({"code": "proxy_not_loopback", "severity": "error", "message": "CLIProxyAPI is not explicitly bound to loopback."})
    if facts.get("exists") and facts.get("mode") != "0o600":
        findings.append({"code": "proxy_config_permissions", "severity": "action", "message": "CLIProxyAPI config should use mode 0600."})
    if not workbuddy.is_file():
        findings.append({"code": "workbuddy_uninitialized", "severity": "action", "message": "Open WorkBuddy once before syncing models."})
    elif oct(stat.S_IMODE(workbuddy.stat().st_mode)) != "0o600":
        findings.append({"code": "workbuddy_config_permissions", "severity": "action", "message": "WorkBuddy models.json should use mode 0600."})
    if client_key is None:
        findings.append({"code": "bridge_secret_missing", "severity": "action", "message": "Bootstrap must create a dedicated proxy client key."})
    if proxy_error:
        findings.append({"code": "proxy_request_failed", "severity": "action", "message": "The authenticated local proxy request failed."})
    emit(
        {
            "schema_version": SCHEMA_VERSION,
            "status": "ready" if not findings and model_count is not None else "attention",
            "platform": {"system": platform.system(), "machine": platform.machine()},
            "cliproxy": {
                "binary": binary,
                "version": proxy_binary_version(binary),
                "config": facts,
                "proxy_url": proxy_url,
                "model_count": model_count,
                "model_owners": owners,
                "error": proxy_error,
                "auth_counts": provider_auth_counts(auth_dir, providers),
            },
            "providers": {provider_id: detect_cli(provider, home) for provider_id, provider in providers.items()},
            "workbuddy": {
                "path": str(workbuddy),
                "exists": workbuddy.is_file(),
                "model_count": len(workbuddy_payload),
                "managed_model_ids": state.get("managed_model_ids", []),
            },
            "findings": findings,
            "safety": {"read_only": True, "secrets_redacted": True},
        }
    )
    return 0 if not any(item["severity"] == "error" for item in findings) else 2


def minimal_config(api_key: str) -> str:
    return (
        'host: "127.0.0.1"\n'
        "port: 8317\n\n"
        "remote-management:\n"
        "  allow-remote: false\n"
        '  secret-key: ""\n'
        "  disable-control-panel: true\n\n"
        'auth-dir: "~/.cli-proxy-api"\n\n'
        "api-keys:\n"
        f"  - {json.dumps(api_key)}\n\n"
        "debug: false\n"
        "request-log: false\n"
        "logging-to-file: true\n"
        "usage-statistics-enabled: false\n"
        "request-retry: 3\n"
    )


def bootstrap_config_preflight(config: Path | None, *, allow_rebind_local: bool) -> str | None:
    if not config or not config.is_file():
        return None
    text = config.read_text(encoding="utf-8")
    host = top_level_scalar(text, "host")
    if host in {None, "", "0.0.0.0", "::", "[::]"} and not allow_rebind_local:
        raise BridgeError(
            "public_bind_requires_approval",
            "Existing CLIProxyAPI config is not explicitly loopback-only; rerun with --allow-rebind-local after confirming remote clients are not required",
            details={"config": str(config)},
        )
    return text


def cmd_bootstrap(args: argparse.Namespace) -> int:
    home = Path(args.home).expanduser().resolve()
    if platform.system() != "Darwin":
        raise BridgeError("unsupported_os", "Version 1 supports macOS only")
    brew = shutil.which("brew")
    if not brew:
        raise BridgeError("homebrew_missing", "Install Homebrew interactively, then rerun bootstrap")
    config = detect_config(home, args.config)
    existing_text = bootstrap_config_preflight(config, allow_rebind_local=args.allow_rebind_local)
    binary = detect_proxy_binary(home)
    formula_installed = brew_formula_installed(brew)
    install_planned = not binary
    actions: list[str] = []
    if not binary:
        actions.append("brew install cliproxyapi")
        if args.apply:
            run_command([brew, "install", "cliproxyapi"], timeout=900, check=True)
            formula_installed = True
            binary = detect_proxy_binary(home)
            if not binary:
                raise BridgeError("install_failed", "Homebrew completed but CLIProxyAPI binary was not found")
    active_config = detect_config(home, args.config)
    if active_config != config:
        config = active_config
        existing_text = bootstrap_config_preflight(config, allow_rebind_local=args.allow_rebind_local)
    config = config or home / ".cli-proxy-api/config.yaml"
    client_key = client_secret(home, create=args.apply)
    if not client_key:
        actions.append("create dedicated proxy client key")
    backup: Path | None = None
    if config.is_file():
        assert existing_text is not None
        text = existing_text
        text_changed = False
        host = top_level_scalar(text, "host")
        if host in {None, "", "0.0.0.0", "::", "[::]"}:
            actions.append("bind CLIProxyAPI to 127.0.0.1")
            if args.apply:
                backup = backup_file(config)
                text = replace_top_level_scalar(text, "host", "127.0.0.1")
                text_changed = True
        if client_key:
            updated, changed = ensure_yaml_list_value(text, "api-keys", client_key)
            if changed:
                actions.append("add dedicated WorkBuddy proxy key")
                if args.apply:
                    backup = backup or backup_file(config)
                    text = updated
                    text_changed = True
        if stat.S_IMODE(config.stat().st_mode) != 0o600:
            actions.append("secure CLIProxyAPI config permissions")
        if args.apply and text_changed:
            atomic_write(config, text, mode=0o600)
        elif args.apply and stat.S_IMODE(config.stat().st_mode) != 0o600:
            os.chmod(config, 0o600)
    else:
        actions.append("create loopback-only CLIProxyAPI config")
        if args.apply:
            assert client_key
            atomic_write(config, minimal_config(client_key), mode=0o600)
    if formula_installed or install_planned:
        actions.append("start CLIProxyAPI with brew services")
        if args.apply:
            completed = run_command([brew, "services", "start", "cliproxyapi"], timeout=180)
            if completed.returncode != 0 and "already started" not in (completed.stdout + completed.stderr).lower():
                raise BridgeError("service_start_failed", "brew services could not start CLIProxyAPI", details={"stderr": redact_text(completed.stderr)})
    elif proxy_process_running():
        actions.append("keep healthy non-Homebrew CLIProxyAPI process in place")
    else:
        raise BridgeError(
            "manual_install_not_running",
            "A non-Homebrew CLIProxyAPI binary exists but no process is running; start its existing service or migrate it explicitly",
            details={"binary": binary},
        )
    emit(
        {
            "status": "applied" if args.apply else "planned",
            "actions": actions,
            "binary": binary,
            "config": str(config),
            "backup": str(backup) if backup else None,
            "proxy_url": DEFAULT_PROXY_URL,
            "client_key_available": bool(client_key),
            "secrets_redacted": True,
        }
    )
    return 0


def cmd_authorize(args: argparse.Namespace) -> int:
    home = Path(args.home).expanduser().resolve()
    providers = load_providers(home)
    provider = providers.get(args.provider)
    if not provider:
        raise BridgeError("unknown_provider", f"Unknown provider: {args.provider}")
    login_flag = provider.get("cliproxy", {}).get("login_flag")
    if not login_flag:
        raise BridgeError("oauth_not_supported", f"Provider {args.provider} has no native CLIProxyAPI login flag")
    binary = detect_proxy_binary(home)
    if not binary:
        raise BridgeError("cliproxy_missing", "Run bootstrap before authorization")
    config = detect_config(home, args.config)
    command = [binary]
    if config:
        command.extend(["--config", str(config)])
    command.append(login_flag)
    if args.no_browser:
        command.append("--no-browser")
    if args.dry_run:
        emit({"status": "planned", "provider": args.provider, "command": [Path(binary).name, "--config", "<config>", login_flag]})
        return 0
    completed = run_command(command, timeout=args.timeout, capture=False)
    if completed.returncode != 0:
        raise BridgeError("oauth_failed", f"OAuth failed for {args.provider}", details={"returncode": completed.returncode})
    facts = config_facts(config, home)
    auth_dir = Path(facts.get("auth_dir") or home / ".cli-proxy-api")
    for auth_file in auth_dir.glob("*.json") if auth_dir.is_dir() else []:
        try:
            os.chmod(auth_file, 0o600)
        except OSError:
            pass
    emit({"status": "authorized", "provider": args.provider, "auth_files_secured": True})
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    home = Path(args.home).expanduser().resolve()
    providers_by_id = load_providers(home)
    requested = [item.strip() for item in args.providers.split(",") if item.strip()]
    unknown = sorted(set(requested) - set(providers_by_id))
    if unknown:
        raise BridgeError("unknown_provider", "Unknown provider ids", details={"providers": unknown})
    providers = [providers_by_id[item] for item in requested]
    proxy_url = args.proxy_url.rstrip("/")
    endpoint = normalized_endpoint(proxy_url)
    client_key = client_secret(home)
    if not client_key:
        raise BridgeError("bridge_secret_missing", "Run bootstrap or set WORKBUDDY_BRIDGE_API_KEY")
    if args.models_file:
        available_payload = load_json(Path(args.models_file))
        available = available_payload.get("data", available_payload) if isinstance(available_payload, dict) else available_payload
        if not isinstance(available, list):
            raise BridgeError("invalid_models_response", "Models fixture must be an array or {data: [...]} object")
    else:
        available = list_proxy_models(proxy_url, client_key)
    selected, missing = select_recommended_models(available, providers)
    if not selected:
        raise BridgeError("no_recommended_models", "No recommended models are available", details={"missing": missing})
    incoming: list[tuple[str, dict[str, Any]]] = []
    probes: dict[str, Any] = {}
    skipped: list[dict[str, str]] = []
    for provider, recommendation, available_model in selected:
        model_id = available_model["id"]
        settings = dict(recommendation["workbuddy"])
        if not args.skip_probes:
            result = probe_model(endpoint, client_key, model_id, settings)
            probes[model_id] = result
            if not result["text"]["ok"] or not result["stream"]["ok"]:
                skipped.append({"model": model_id, "reason": "text_or_stream_probe_failed"})
                continue
            if "tools" in result and not result["tools"]["ok"]:
                settings["supportsToolCall"] = False
            if "images" in result and not result["images"]["ok"]:
                settings["supportsImages"] = False
            if "reasoning" in result and not result["reasoning"]["ok"]:
                settings["supportsReasoning"] = False
                settings.pop("reasoning", None)
                settings["onlyReasoning"] = False
        incoming.append((provider["id"], workbuddy_entry(model_id, endpoint, client_key, settings)))
    if not incoming:
        raise BridgeError("all_probes_failed", "All recommended models failed required probes", details={"probes": probes})
    workbuddy_path = home_path(args.workbuddy, home)
    if not workbuddy_path.is_file():
        raise BridgeError("workbuddy_uninitialized", "Open WorkBuddy once before syncing models", details={"path": str(workbuddy_path)})
    existing = load_json(workbuddy_path)
    if not isinstance(existing, list) or not all(isinstance(item, dict) for item in existing):
        raise BridgeError("invalid_workbuddy_config", "WorkBuddy models.json must contain an array of model objects")
    state_file = state_paths(home)["state"]
    state = load_json(state_file, default={}) or {}
    managed_before = set(state.get("managed_model_ids", []))
    merged, changes, managed_after = merge_workbuddy_models(existing, incoming, managed_before)
    backup: Path | None = None
    permissions_hardened: list[str] = []
    if args.apply and (changes["added"] or changes["updated"]):
        backup = backup_file(workbuddy_path)
        save_json(workbuddy_path, merged, mode=0o600)
        save_json(
            state_file,
            {
                "schema_version": SCHEMA_VERSION,
                "updated_at": iso_now(),
                "managed_model_ids": sorted(managed_after),
                "providers": requested,
                "workbuddy_path": str(workbuddy_path),
                "endpoint": endpoint,
                "proxy_key_sha256": hashlib.sha256(client_key.encode("utf-8")).hexdigest(),
            },
            mode=0o600,
        )
    if args.apply:
        for path, label in (
            (workbuddy_path, "workbuddy"),
            (state_file, "bridge_state"),
            (state_paths(home)["secret"], "bridge_secret"),
        ):
            if path.is_file() and stat.S_IMODE(path.stat().st_mode) != 0o600:
                os.chmod(path, 0o600)
                permissions_hardened.append(label)
    emit(
        {
            "status": "applied" if args.apply else "planned",
            "providers": requested,
            "endpoint": endpoint,
            "changes": changes,
            "missing_recommendations": missing,
            "skipped": skipped,
            "probes": probes,
            "backup": str(backup) if backup else None,
            "permissions_hardened": permissions_hardened,
            "secrets_redacted": True,
        }
    )
    return 0 if not changes["conflicts"] else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge CLI subscription models into WorkBuddy on macOS")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Read-only discovery of CLIProxyAPI, CLIs, OAuth signals, and WorkBuddy")
    audit.add_argument("--home", default=str(Path.home()))
    audit.add_argument("--config")
    audit.add_argument("--proxy-url")
    audit.set_defaults(func=cmd_audit)

    bootstrap = subparsers.add_parser("bootstrap", help="Install and safely initialize CLIProxyAPI")
    bootstrap.add_argument("--home", default=str(Path.home()))
    bootstrap.add_argument("--config")
    bootstrap.add_argument("--apply", action="store_true")
    bootstrap.add_argument("--allow-rebind-local", action="store_true")
    bootstrap.set_defaults(func=cmd_bootstrap)

    authorize = subparsers.add_parser("authorize", help="Run a provider's native CLIProxyAPI OAuth flow")
    authorize.add_argument("provider")
    authorize.add_argument("--home", default=str(Path.home()))
    authorize.add_argument("--config")
    authorize.add_argument("--no-browser", action="store_true")
    authorize.add_argument("--dry-run", action="store_true")
    authorize.add_argument("--timeout", type=int, default=1800)
    authorize.set_defaults(func=cmd_authorize)

    sync = subparsers.add_parser("sync", help="Probe recommended models and merge them into WorkBuddy")
    sync.add_argument("--providers", default="codex,xai-grok,antigravity")
    sync.add_argument("--home", default=str(Path.home()))
    sync.add_argument("--proxy-url", default=DEFAULT_PROXY_URL)
    sync.add_argument("--workbuddy", default=str(DEFAULT_WORKBUDDY_RELATIVE))
    sync.add_argument("--models-file", help="Offline /v1/models fixture for deterministic testing")
    sync.add_argument("--skip-probes", action="store_true")
    sync.add_argument("--apply", action="store_true")
    sync.set_defaults(func=cmd_sync)

    validate = subparsers.add_parser("validate-provider", help="Validate a bundled or local Provider manifest")
    validate.add_argument("path")
    validate.set_defaults(func=cmd_validate_provider)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except BridgeError as exc:
        emit({"status": "error", "code": exc.code, "message": exc.message, "details": exc.details, "secrets_redacted": True})
        return 2
    except KeyboardInterrupt:
        emit({"status": "cancelled", "message": "Operation cancelled by user"})
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
