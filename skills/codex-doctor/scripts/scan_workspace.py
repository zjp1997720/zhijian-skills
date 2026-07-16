#!/usr/bin/env python3
"""Read-only Codex workspace health scanner.

The script never edits configuration or repository files and never executes hooks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    tomllib = None


SCHEMA_VERSION = 1
DEFAULT_DOC_LIMIT = 32 * 1024
SEVERITIES = ("S0", "S1", "S2", "S3", "S4")
SECRET_KEY_RE = re.compile(r"(?:token|secret|password|passwd|api[_-]?key|auth(?:orization)?)", re.I)
INFERABLE_HEADING_RE = re.compile(
    r"(?:技术栈|依赖|目录结构|项目结构|文件结构|常用命令|开发命令|tech(?:nology)? stack|dependencies|directory structure|file tree|commands)",
    re.I,
)
PROTECTED_RULE_RE = re.compile(
    r"(?:安全|禁止|不得|授权|隐私|凭据|密钥|Git|分支|提交|push|发布|付款|生产|账户|品牌|人格|业务|客户|目录|路径|同步|generated|security|credential|secret|authorization|production|payment|brand|persona)",
    re.I,
)
SUSPICIOUS_ROOT_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
    "dist",
    "build",
}
PROTECTED_ROOT_DIRS = {".agents", ".claude", ".codex", ".git", ".workbuddy", ".web-clipper"}
KNOWN_GENERATED_ROOT_PATHS = {".codex/visualizations"}


def run(cmd: list[str], cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)


def sha256(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def safe_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def stable_id(domain: str, source: str, code: str) -> str:
    digest = hashlib.sha1(f"{domain}|{source}|{code}".encode()).hexdigest()[:8]
    return f"{domain}.{code}.{digest}"


def add_finding(
    findings: list[dict[str, Any]],
    *,
    domain: str,
    severity: str,
    confidence: str,
    code: str,
    source: str,
    summary: str,
    evidence: Any,
    impact: str,
    recommendation: str,
    fixability: str = "manual_review",
) -> None:
    findings.append(
        {
            "id": stable_id(domain, source, code),
            "domain": domain,
            "severity": severity,
            "confidence": confidence,
            "source": source,
            "summary": summary,
            "evidence": evidence,
            "impact": impact,
            "recommendation": recommendation,
            "fixability": fixability,
        }
    )


def git_root(cwd: Path) -> Path | None:
    try:
        cp = run(["git", "rev-parse", "--show-toplevel"], cwd)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if cp.returncode != 0:
        return None
    return Path(cp.stdout.strip()).resolve()


def load_toml(path: Path, findings: list[dict[str, Any]], domain: str = "config") -> dict[str, Any]:
    if not path.exists():
        return {}
    if tomllib is None:
        add_finding(
            findings,
            domain=domain,
            severity="S1",
            confidence="high",
            code="toml_parser_missing",
            source=str(path),
            summary="Python tomllib is unavailable",
            evidence={"python": sys.version.split()[0]},
            impact="TOML configuration could not be validated.",
            recommendation="Run with Python 3.11 or newer.",
            fixability="environment",
        )
        return {}
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        add_finding(
            findings,
            domain=domain,
            severity="S1",
            confidence="high",
            code="toml_parse_error",
            source=str(path),
            summary="TOML configuration cannot be parsed",
            evidence={"error_type": type(exc).__name__, "error": str(exc)[:300]},
            impact="The effective Codex configuration may not load.",
            recommendation="Inspect and repair the TOML syntax after reviewing a focused diff.",
        )
        return {}


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def first_nonempty(paths: list[Path]) -> Path | None:
    for path in paths:
        text = safe_text(path)
        if text and text.strip():
            return path
    return None


def explicit_root_path_prohibition(root: Path, relative_path: str) -> dict[str, Any] | None:
    """Return an explicit repository-root prohibition from the active root instructions."""
    source = first_nonempty([root / "AGENTS.override.md", root / "AGENTS.md"])
    if not source:
        return None
    text = safe_text(source) or ""
    path_pattern = re.compile(rf"`?{re.escape(relative_path.rstrip('/'))}/?`?", re.I)
    deny_pattern = re.compile(r"(?:禁止|不得|不可|must\s+not|do\s+not|never)", re.I)
    root_pattern = re.compile(r"(?:根目录|仓库根|repository\s+root|repo\s+root)", re.I)
    for line_no, line in enumerate(text.splitlines(), 1):
        if path_pattern.search(line) and deny_pattern.search(line) and root_pattern.search(line):
            return {"source": str(source), "line": line_no, "text": line.strip()[:500]}
    return None


def instruction_chain(
    cwd: Path, root: Path | None, codex_home: Path, config: dict[str, Any]
) -> list[dict[str, Any]]:
    chain: list[Path] = []
    global_file = first_nonempty([codex_home / "AGENTS.override.md", codex_home / "AGENTS.md"])
    if global_file:
        chain.append(global_file)

    if root:
        try:
            relative = cwd.resolve().relative_to(root)
            dirs = [root]
            current = root
            for part in relative.parts:
                current = current / part
                dirs.append(current)
        except ValueError:
            dirs = [cwd]
    else:
        dirs = [cwd]

    fallbacks = config.get("project_doc_fallback_filenames", [])
    if not isinstance(fallbacks, list):
        fallbacks = []
    names = ["AGENTS.override.md", "AGENTS.md"] + [str(x) for x in fallbacks if isinstance(x, str)]
    for directory in dirs:
        selected = first_nonempty([directory / name for name in names])
        if selected:
            chain.append(selected)

    result = []
    for path in chain:
        text = safe_text(path) or ""
        result.append(
            {
                "path": str(path),
                "bytes": len(text.encode("utf-8")),
                "lines": len(text.splitlines()),
                "sha256": sha256(path),
                "text": text,
            }
        )
    return result


def normalized_blocks(text: str) -> list[tuple[int, str, str]]:
    blocks: list[tuple[int, str, str]] = []
    current: list[str] = []
    start = 1
    in_fence = False
    in_frontmatter = text.startswith("---\n")
    for idx, line in enumerate(text.splitlines(), 1):
        if idx == 1 and in_frontmatter:
            continue
        if in_frontmatter:
            if line.strip() == "---":
                in_frontmatter = False
            continue
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line.strip():
            if current:
                raw = "\n".join(current).strip()
                norm = re.sub(r"\s+", " ", raw).strip().lower()
                if len(norm) >= 40:
                    blocks.append((start, norm, raw))
                current = []
            start = idx + 1
        else:
            if not current:
                start = idx
            current.append(line)
    if current:
        raw = "\n".join(current).strip()
        norm = re.sub(r"\s+", " ", raw).strip().lower()
        if len(norm) >= 40:
            blocks.append((start, norm, raw))
    return blocks


def scan_instructions(
    cwd: Path,
    root: Path | None,
    codex_home: Path,
    config: dict[str, Any],
    findings: list[dict[str, Any]],
    inventory: dict[str, Any],
) -> None:
    chain = instruction_chain(cwd, root, codex_home, config)
    limit = config.get("project_doc_max_bytes", DEFAULT_DOC_LIMIT)
    if not isinstance(limit, int) or limit <= 0:
        limit = DEFAULT_DOC_LIMIT
    total = sum(item["bytes"] for item in chain)
    inventory["instructions"] = {
        "effective_chain": [{k: v for k, v in item.items() if k != "text"} for item in chain],
        "combined_bytes": total,
        "project_doc_max_bytes": limit,
        "semantic_candidates": [],
    }

    running = 0
    for item in chain:
        before = running
        running += item["bytes"]
        if before < limit < running or (running > limit and before >= limit):
            add_finding(
                findings,
                domain="instructions",
                severity="S1",
                confidence="high",
                code="effective_chain_truncated",
                source=item["path"],
                summary="The effective AGENTS instruction chain exceeds the configured byte limit",
                evidence={"limit": limit, "bytes_before_file": before, "file_bytes": item["bytes"], "combined_bytes": total},
                impact="Rules at or after this file may be missing from the model-visible prompt.",
                recommendation="Move directory-specific rules closer to their scope or raise the limit after reviewing context cost.",
            )
            break

    block_locations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in chain:
        for line, norm, raw in normalized_blocks(item["text"]):
            block_locations[norm].append(
                {"path": item["path"], "line": line, "sha256": item["sha256"], "protected": bool(PROTECTED_RULE_RE.search(raw))}
            )
        for line_no, line in enumerate(item["text"].splitlines(), 1):
            if line.lstrip().startswith("#") and INFERABLE_HEADING_RE.search(line):
                inventory["instructions"]["semantic_candidates"].append(
                    {"path": item["path"], "line": line_no, "heading": line.strip(), "reason": "heading suggests repo-inferable inventory"}
                )

    for norm, locations in block_locations.items():
        unique = {(x["path"], x["line"]) for x in locations}
        if len(unique) < 2:
            continue
        protected = any(x["protected"] for x in locations)
        duplicate_code = ("exact_duplicate_block_protected_" if protected else "exact_duplicate_block_") + hashlib.sha1(norm.encode()).hexdigest()[:6]
        add_finding(
            findings,
            domain="instructions",
            severity="S4",
            confidence="high",
            code=duplicate_code,
            source=locations[0]["path"],
            summary="An exact normalized instruction block appears more than once",
            evidence={"locations": locations, "normalized_sha1": hashlib.sha1(norm.encode()).hexdigest()},
            impact="Repeated prompt text consumes context; protected rules may repeat intentionally.",
            recommendation="Review scope and intent. Preserve protected rules unless an approved parity contract makes one copy unnecessary.",
            fixability="manual_semantic_review",
        )

    if root:
        agents = root / "AGENTS.md"
        claude = root / "CLAUDE.md"
        if agents.exists() and claude.exists():
            a_lines = {x.strip() for x in (safe_text(agents) or "").splitlines() if x.strip()}
            c_lines = {x.strip() for x in (safe_text(claude) or "").splitlines() if x.strip()}
            overlap = len(a_lines & c_lines)
            inventory["instructions"]["cross_host_parity"] = {
                "agents_path": str(agents),
                "claude_path": str(claude),
                "shared_nonempty_lines": overlap,
                "agents_unique_lines": len(a_lines),
                "claude_unique_lines": len(c_lines),
                "classification": "parity_inventory_not_deletion_finding",
            }


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str | None]:
    text = safe_text(path)
    if text is None:
        return {}, "unreadable"
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "missing_frontmatter"
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, "unterminated_frontmatter"
    data: dict[str, str] = {}
    current_key: str | None = None
    for line in lines[1:end]:
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            current_key = m.group(1)
            data[current_key] = m.group(2).strip().strip('"\'')
        elif current_key and line.startswith((" ", "\t")):
            data[current_key] += " " + line.strip()
    return data, None


def markdown_targets_outside_fences(text: str) -> list[str]:
    targets: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        targets.extend(match.group(1) for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", line))
    return targets


def skill_roots(cwd: Path, root: Path | None, codex_home: Path) -> list[Path]:
    roots: list[Path] = []
    if root:
        try:
            relative = cwd.resolve().relative_to(root)
            current = root
            roots.append(current / ".agents" / "skills")
            for part in relative.parts:
                current = current / part
                roots.append(current / ".agents" / "skills")
        except ValueError:
            roots.append(cwd / ".agents" / "skills")
    else:
        roots.append(cwd / ".agents" / "skills")
    roots.extend([Path.home() / ".agents" / "skills", codex_home / "skills"])
    seen: set[str] = set()
    out: list[Path] = []
    for path in roots:
        key = str(path.resolve()) if path.exists() else str(path)
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def scan_skills(
    cwd: Path,
    root: Path | None,
    codex_home: Path,
    findings: list[dict[str, Any]],
    inventory: dict[str, Any],
) -> None:
    skills: list[dict[str, Any]] = []
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_skill_files: set[str] = set()
    for base in skill_roots(cwd, root, codex_home):
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            skill_file = child / "SKILL.md"
            if not skill_file.exists():
                continue
            real = str(skill_file.resolve())
            if real in seen_skill_files:
                continue
            seen_skill_files.add(real)
            metadata, error = parse_frontmatter(skill_file)
            text = safe_text(skill_file) or ""
            item = {
                "path": str(skill_file),
                "real_path": real,
                "name": metadata.get("name"),
                "description_chars": len(metadata.get("description", "")),
                "lines": len(text.splitlines()),
                "sha256": sha256(skill_file),
            }
            skills.append(item)
            if error or not metadata.get("name") or not metadata.get("description"):
                add_finding(
                    findings,
                    domain="skills",
                    severity="S1",
                    confidence="high",
                    code="invalid_frontmatter",
                    source=str(skill_file),
                    summary="Skill frontmatter is missing or incomplete",
                    evidence={"parse_error": error, "has_name": bool(metadata.get("name")), "has_description": bool(metadata.get("description"))},
                    impact="Codex may not discover or correctly trigger this Skill.",
                    recommendation="Repair only the first YAML frontmatter block and verify discovery.",
                )
            if metadata.get("name"):
                by_name[metadata["name"]].append(item)
            if item["lines"] > 500:
                add_finding(
                    findings,
                    domain="skills",
                    severity="S3",
                    confidence="high",
                    code="long_skill_body",
                    source=str(skill_file),
                    summary="SKILL.md exceeds the recommended progressive-disclosure size",
                    evidence={"lines": item["lines"]},
                    impact="Selected Skill instructions consume more context and are harder to maintain.",
                    recommendation="Move detailed references or deterministic procedures into references/ or scripts/ after review.",
                )
            for raw_target in markdown_targets_outside_fences(text):
                target = raw_target.strip().strip("<>")
                placeholder = target.lower() in {"url", "path", "..."} or bool(re.search(r"[<>{}\[\]*]", target)) or "路径" in target
                if not target or placeholder or target.startswith(("#", "http://", "https://", "mailto:", "skill://")):
                    continue
                target = target.split("#", 1)[0]
                candidate = Path(target) if os.path.isabs(target) else skill_file.parent / target
                if not candidate.exists():
                    code = "broken_markdown_reference_" + hashlib.sha1(target.encode()).hexdigest()[:6]
                    add_finding(
                        findings,
                        domain="skills",
                        severity="S2",
                        confidence="high",
                        code=code,
                        source=str(skill_file),
                        summary="Skill contains a broken local Markdown reference",
                        evidence={"target": target},
                        impact="The Skill may fail when progressive disclosure reaches this resource.",
                        recommendation="Restore the referenced resource or update the link after confirming source ownership.",
                    )

    for name, items in by_name.items():
        if len(items) > 1:
            code = "duplicate_active_name_" + hashlib.sha1(name.encode()).hexdigest()[:6]
            add_finding(
                findings,
                domain="skills",
                severity="S2",
                confidence="high",
                code=code,
                source=items[0]["path"],
                summary=f"Multiple discovered Skills use the name '{name}'",
                evidence={"paths": [x["path"] for x in items]},
                impact="Codex does not merge same-name Skills; selectors and triggering can become ambiguous.",
                recommendation="Confirm intended scope and source ownership before renaming, disabling, or removing anything.",
            )
    inventory["skills"] = {"count": len(skills), "roots": [str(x) for x in skill_roots(cwd, root, codex_home)], "items": skills}


def walk_secret_keys(value: Any, prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if SECRET_KEY_RE.search(str(key)) and isinstance(child, str) and child.strip():
                hits.append(path)
            hits.extend(walk_secret_keys(child, path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            hits.extend(walk_secret_keys(child, f"{prefix}[{idx}]"))
    return hits


def command_exists(command: str, cwd: Path | None = None) -> bool:
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    if not parts:
        return False
    exe = os.path.expanduser(parts[0])
    if os.path.isabs(exe) or "/" in exe:
        path = Path(exe)
        if not path.is_absolute() and cwd is not None:
            path = cwd / path
        executable_exists = path.is_file() and os.access(path, os.X_OK)
    else:
        executable_exists = shutil.which(exe) is not None
    if not executable_exists:
        return False
    interpreter = Path(exe).name.lower()
    if interpreter in {"python", "python3", "node", "bash", "sh", "zsh", "ruby", "perl"} and len(parts) > 1:
        script = parts[1]
        if not script.startswith("-") and "$" not in script and ("/" in script or Path(script).suffix):
            script_path = Path(os.path.expanduser(script))
            if not script_path.is_absolute() and cwd is not None:
                script_path = cwd / script_path
            return script_path.is_file()
    return True


def collect_hook_handlers(hooks: Any, source: Path, source_kind: str) -> list[dict[str, Any]]:
    """Flatten JSON or TOML hook structures without executing or expanding commands."""
    if not isinstance(hooks, dict):
        return []
    root_hooks = hooks.get("hooks", hooks)
    if not isinstance(root_hooks, dict):
        return []
    handlers: list[dict[str, Any]] = []
    for event, groups in root_hooks.items():
        if not isinstance(groups, list):
            continue
        for group_index, group in enumerate(groups):
            if not isinstance(group, dict):
                continue
            group_handlers = group.get("hooks", [])
            if not isinstance(group_handlers, list):
                continue
            for handler_index, handler in enumerate(group_handlers):
                if isinstance(handler, dict):
                    handlers.append(
                        {
                            "event": event,
                            "group_index": group_index,
                            "handler_index": handler_index,
                            "source": str(source),
                            "source_kind": source_kind,
                            **handler,
                        }
                    )
    return handlers


def hook_shape_errors(hooks: Any) -> list[dict[str, str]]:
    """Validate the documented three-level event/group/handler structure."""
    if not isinstance(hooks, dict):
        return [{"path": "hooks", "error": "expected object"}]
    root_hooks = hooks.get("hooks", hooks)
    if not isinstance(root_hooks, dict):
        return [{"path": "hooks", "error": "expected event object"}]
    errors: list[dict[str, str]] = []
    for event, groups in root_hooks.items():
        if event in {"managed_dir", "windows_managed_dir"}:
            continue
        if not isinstance(groups, list):
            errors.append({"path": f"hooks.{event}", "error": "expected matcher-group list"})
            continue
        for group_index, group in enumerate(groups):
            group_path = f"hooks.{event}[{group_index}]"
            if not isinstance(group, dict):
                errors.append({"path": group_path, "error": "expected matcher-group object"})
                continue
            handlers = group.get("hooks")
            if not isinstance(handlers, list):
                errors.append({"path": f"{group_path}.hooks", "error": "expected handler list"})
                continue
            for handler_index, handler in enumerate(handlers):
                handler_path = f"{group_path}.hooks[{handler_index}]"
                if not isinstance(handler, dict):
                    errors.append({"path": handler_path, "error": "expected handler object"})
                    continue
                if handler.get("type") == "command" and not isinstance(handler.get("command"), str):
                    errors.append({"path": f"{handler_path}.command", "error": "expected command string"})
    return errors


def scan_config_mcp_hooks(
    root: Path | None,
    codex_home: Path,
    user_config: dict[str, Any],
    project_config: dict[str, Any],
    findings: list[dict[str, Any]],
    inventory: dict[str, Any],
    command_cwd: Path | None = None,
) -> None:
    config_items = []
    for path, data, scope in [
        (codex_home / "config.toml", user_config, "user"),
        ((root / ".codex" / "config.toml") if root else Path("/__missing__"), project_config, "project"),
    ]:
        if path.exists():
            config_items.append({"path": str(path), "scope": scope, "sha256": sha256(path), "top_level_keys": sorted(data)})
    inventory["config"] = config_items

    if root and project_config:
        secret_keys = walk_secret_keys(project_config)
        if secret_keys:
            add_finding(
                findings,
                domain="config",
                severity="S4",
                confidence="medium",
                code="project_secret_shaped_values",
                source=str(root / ".codex" / "config.toml"),
                summary="Project Codex config contains non-empty secret-shaped keys that require verification",
                evidence={"keys": secret_keys, "values": "redacted"},
                impact="Credentials in a repository-level config can be committed or exposed.",
                recommendation="Verify whether these are credentials, rotate if exposed, and move secrets to an approved secret store.",
                fixability="security_response",
            )

    effective_config = deep_merge(user_config, project_config)
    effective_servers = effective_config.get("mcp_servers", {}) if isinstance(effective_config, dict) else {}
    user_servers = user_config.get("mcp_servers", {}) if isinstance(user_config, dict) else {}
    project_servers = project_config.get("mcp_servers", {}) if isinstance(project_config, dict) else {}
    mcp_inventory = []
    if isinstance(effective_servers, dict):
        for name, cfg in effective_servers.items():
            if not isinstance(cfg, dict):
                continue
            scope = "project" if isinstance(project_servers, dict) and name in project_servers else "user"
            path = (root / ".codex" / "config.toml") if scope == "project" and root else codex_home / "config.toml"
            enabled = cfg.get("enabled", True) is not False
            transport = "http" if isinstance(cfg.get("url"), str) else "stdio" if isinstance(cfg.get("command"), str) else "unknown"
            mcp_inventory.append(
                {
                    "name": name,
                    "scope": scope,
                    "enabled": enabled,
                    "transport": transport,
                    "source": str(path),
                    "overrides_user_definition": scope == "project" and isinstance(user_servers, dict) and name in user_servers,
                }
            )
            if not enabled:
                continue
            if transport == "unknown":
                code = "enabled_transport_missing_" + hashlib.sha1(str(name).encode()).hexdigest()[:6]
                add_finding(
                    findings,
                    domain="mcp",
                    severity="S1",
                    confidence="high",
                    code=code,
                    source=str(path),
                    summary=f"Enabled MCP server '{name}' has no supported transport",
                    evidence={"server": name, "scope": scope, "has_command": False, "has_url": False},
                    impact="The MCP server cannot start.",
                    recommendation="Add the authoritative command or HTTP URL, or disable the entry after explicit approval.",
                )
                continue
            if transport == "stdio" and not command_exists(str(cfg.get("command", "")), command_cwd):
                code = "enabled_command_missing_" + hashlib.sha1(str(name).encode()).hexdigest()[:6]
                add_finding(
                    findings,
                    domain="mcp",
                    severity="S1",
                    confidence="high",
                    code=code,
                    source=str(path),
                    summary=f"Enabled MCP server '{name}' has no resolvable command",
                    evidence={"server": name, "scope": scope, "command": str(cfg.get("command", "")).split()[0] if cfg.get("command") else None},
                    impact="The MCP server cannot start.",
                    recommendation="Verify the intended executable and installation source; do not install automatically.",
                )
            if transport == "http":
                parsed = urlparse(str(cfg.get("url")))
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    code = "invalid_http_url_" + hashlib.sha1(str(name).encode()).hexdigest()[:6]
                    add_finding(
                        findings,
                        domain="mcp",
                        severity="S1",
                        confidence="high",
                        code=code,
                        source=str(path),
                        summary=f"Enabled MCP server '{name}' has an invalid HTTP URL",
                        evidence={"server": name, "scope": scope, "scheme": parsed.scheme, "has_host": bool(parsed.netloc)},
                        impact="The MCP server cannot connect.",
                        recommendation="Correct the URL after confirming the authoritative endpoint.",
                    )
    inventory["mcp"] = mcp_inventory

    plugins = effective_config.get("plugins", {}) if isinstance(effective_config, dict) else {}
    inventory["plugins"] = [
        {"name": str(name), "enabled": cfg.get("enabled", True) is not False}
        for name, cfg in sorted(plugins.items())
        if isinstance(cfg, dict)
    ] if isinstance(plugins, dict) else []

    hook_inventory = []
    for scope, base, data in [
        ("user", codex_home, user_config),
        ("project", (root / ".codex") if root else Path("/__missing__"), project_config),
    ]:
        hooks_json = base / "hooks.json"
        hooks_table = data.get("hooks", {}) if isinstance(data, dict) else {}
        inline_hooks = (
            {k: v for k, v in hooks_table.items() if k not in {"state", "managed_dir", "windows_managed_dir"}}
            if isinstance(hooks_table, dict)
            else {}
        )
        inline = bool(inline_hooks)
        json_data: dict[str, Any] = {}
        if hooks_json.exists():
            try:
                json_data = json.loads(hooks_json.read_text(encoding="utf-8"))
                hook_inventory.append({"scope": scope, "source": str(hooks_json), "type": "json", "sha256": sha256(hooks_json)})
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                add_finding(
                    findings,
                    domain="hooks",
                    severity="S1",
                    confidence="high",
                    code="json_parse_error",
                    source=str(hooks_json),
                    summary="Hook JSON cannot be parsed",
                    evidence={"error_type": type(exc).__name__, "error": str(exc)[:300]},
                    impact="Project or user hooks may not load.",
                    recommendation="Repair JSON syntax without executing the hooks.",
                )
        if json_data:
            shape_errors = hook_shape_errors(json_data)
            if shape_errors:
                add_finding(
                    findings,
                    domain="hooks",
                    severity="S1",
                    confidence="high",
                    code="json_schema_error",
                    source=str(hooks_json),
                    summary="Hook JSON does not match the documented event/group/handler shape",
                    evidence={"errors": shape_errors[:20], "truncated": len(shape_errors) > 20},
                    impact="Handlers can be skipped or interpreted differently from the author's intent.",
                    recommendation="Repair the structure without executing any hook commands.",
                )
        if inline:
            hook_inventory.append({"scope": scope, "source": str(base / "config.toml"), "type": "inline_toml"})
            shape_errors = hook_shape_errors(inline_hooks)
            if shape_errors:
                add_finding(
                    findings,
                    domain="hooks",
                    severity="S1",
                    confidence="high",
                    code="inline_toml_schema_error",
                    source=str(base / "config.toml"),
                    summary="Inline TOML hooks do not match the documented event/group/handler shape",
                    evidence={"errors": shape_errors[:20], "truncated": len(shape_errors) > 20},
                    impact="Handlers can be skipped or interpreted differently from the author's intent.",
                    recommendation="Repair the structure without executing any hook commands.",
                )
        if hooks_json.exists() and inline:
            add_finding(
                findings,
                domain="hooks",
                severity="S2",
                confidence="high",
                code="merged_sources_same_layer",
                source=str(base),
                summary=f"{scope.title()} scope defines both hooks.json and inline TOML hooks",
                evidence={"json": str(hooks_json), "toml": str(base / "config.toml")},
                impact="Codex merges both sources; matching hooks can run concurrently and duplicate effects.",
                recommendation="Prefer one representation per layer after comparing behavior and trust state.",
            )
        handlers = collect_hook_handlers(json_data, hooks_json, "json")
        if inline:
            handlers.extend(collect_hook_handlers(inline_hooks, base / "config.toml", "inline_toml"))
        for handler in handlers:
            if handler.get("type") == "command" and isinstance(handler.get("command"), str) and not command_exists(handler["command"], command_cwd):
                identity = "|".join(
                    str(x)
                    for x in (
                        handler.get("source_kind"),
                        handler.get("event"),
                        handler.get("group_index"),
                        handler.get("handler_index"),
                        handler.get("command"),
                    )
                )
                code = "command_missing_" + hashlib.sha1(identity.encode()).hexdigest()[:6]
                add_finding(
                    findings,
                    domain="hooks",
                    severity="S1",
                    confidence="high",
                    code=code,
                    source=str(handler.get("source")),
                    summary=f"Hook command for {handler.get('event')} has no resolvable executable",
                    evidence={
                        "event": handler.get("event"),
                        "source_kind": handler.get("source_kind"),
                        "group_index": handler.get("group_index"),
                        "handler_index": handler.get("handler_index"),
                        "command": handler["command"].split()[0],
                    },
                    impact="The hook will be skipped or fail when triggered.",
                    recommendation="Verify the executable and script path without running the hook.",
                )
    inventory["hooks"] = hook_inventory


def scan_git_root(root: Path | None, findings: list[dict[str, Any]], inventory: dict[str, Any]) -> None:
    if not root:
        inventory["git"] = {"repository": False}
        return
    try:
        cp = run(["git", "status", "--porcelain=v2", "--branch"], root)
    except (OSError, subprocess.TimeoutExpired) as exc:
        add_finding(
            findings,
            domain="git",
            severity="S1",
            confidence="high",
            code="status_failed",
            source=str(root),
            summary="Git status could not be collected",
            evidence={"error_type": type(exc).__name__},
            impact="Workspace change ownership and safety cannot be assessed.",
            recommendation="Run a read-only Git status manually.",
        )
        return
    lines = cp.stdout.splitlines()
    branch = next((line.removeprefix("# branch.head ") for line in lines if line.startswith("# branch.head ")), None)
    tracked_changes = sum(1 for line in lines if line.startswith(("1 ", "2 ", "u ")))
    untracked = [line[2:] for line in lines if line.startswith("? ")]
    inventory["git"] = {
        "repository": True,
        "root": str(root),
        "branch": branch,
        "tracked_change_count": tracked_changes,
        "untracked_count": len(untracked),
    }
    sensitive = [p for p in untracked if re.search(r"(?:^|/)(?:\.env(?:\.|$)|auth\.json$|credentials?(?:\.|$)|secrets?(?:\.|$))", p, re.I)]
    if sensitive:
        add_finding(
            findings,
            domain="git",
            severity="S4",
            confidence="medium",
            code="untracked_sensitive_names",
            source=str(root),
            summary="Untracked files have credential-shaped names",
            evidence={"paths": sensitive},
            impact="Sensitive local files may be committed accidentally.",
            recommendation="Inspect contents without printing secrets, then verify ignore policy and rotate exposed credentials if necessary.",
            fixability="security_review",
        )

    root_hygiene = []
    for name in sorted(SUSPICIOUS_ROOT_DIRS):
        path = root / name
        if not path.exists() or name in PROTECTED_ROOT_DIRS:
            continue
        ignored = run(["git", "check-ignore", "-q", "--", name], root).returncode == 0
        if not ignored:
            root_hygiene.append(name)
    if root_hygiene:
        add_finding(
            findings,
            domain="root_hygiene",
            severity="S2",
            confidence="high",
            code="generated_dirs_not_ignored",
            source=str(root),
            summary="Known generated or dependency directories exist at repository root and are not ignored",
            evidence={"paths": root_hygiene},
            impact="Generated files can pollute search, context, and commits.",
            recommendation="Confirm project ownership, then add precise ignore rules or move/rebuild assets in the approved location.",
        )

    generated_nested = []
    for relative_path in sorted(KNOWN_GENERATED_ROOT_PATHS):
        path = root / relative_path
        if not path.exists():
            continue
        ignored = run(["git", "check-ignore", "-q", "--", relative_path], root).returncode == 0
        if not ignored:
            generated_nested.append(relative_path)
    if generated_nested:
        add_finding(
            findings,
            domain="root_hygiene",
            severity="S2",
            confidence="high",
            code="generated_paths_inside_protected_root_not_ignored",
            source=str(root),
            summary="Known generated output exists inside a protected root directory and is not ignored",
            evidence={"paths": generated_nested},
            impact="Generated output can pollute search, context, and commits while hiding inside a configuration directory.",
            recommendation="Confirm ownership, then move the output to the approved generated-artifact location or add a precise ignore rule.",
        )

    docs_rule = explicit_root_path_prohibition(root, "docs/")
    docs_path = root / "docs"
    if docs_rule and docs_path.exists():
        add_finding(
            findings,
            domain="root_hygiene",
            severity="S2",
            confidence="high",
            code="explicitly_forbidden_root_docs",
            source=str(root),
            summary="A root docs/ directory violates an explicit repository instruction",
            evidence={"path": "docs/", "rule": docs_rule},
            impact="Plans or specifications are stored outside the repository's declared documentation location.",
            recommendation="Review ownership, then move each file to the approved documentation directory with a finding-level diff.",
        )


def built_in_doctor(cwd: Path, findings: list[dict[str, Any]], inventory: dict[str, Any], skip: bool) -> None:
    if skip:
        inventory["built_in_doctor"] = {"status": "skipped", "reason": "--skip-built-in"}
        return
    if not shutil.which("codex"):
        add_finding(
            findings,
            domain="runtime",
            severity="S1",
            confidence="high",
            code="codex_missing",
            source="PATH",
            summary="Codex executable is not available",
            evidence={"command": "codex"},
            impact="The built-in health report cannot run.",
            recommendation="Verify the intended Codex installation and PATH.",
            fixability="environment",
        )
        return
    try:
        cp = run(["codex", "doctor", "--json"], cwd, timeout=90)
    except (OSError, subprocess.TimeoutExpired) as exc:
        add_finding(
            findings,
            domain="runtime",
            severity="S1",
            confidence="high",
            code="doctor_failed",
            source="codex doctor --json",
            summary="Built-in Codex doctor did not complete",
            evidence={"error_type": type(exc).__name__},
            impact="Installation and runtime health remain unverified.",
            recommendation="Run `codex doctor --summary` interactively and inspect the environment-specific failure.",
            fixability="environment",
        )
        return
    try:
        report = json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        add_finding(
            findings,
            domain="runtime",
            severity="S1",
            confidence="high",
            code="doctor_json_invalid",
            source="codex doctor --json",
            summary="Built-in Codex doctor returned invalid JSON",
            evidence={"returncode": cp.returncode, "error": str(exc)},
            impact="Built-in diagnostic results cannot be safely integrated.",
            recommendation="Inspect `codex doctor --help` and the installed version before changing anything.",
        )
        return
    inventory["built_in_doctor"] = report
    checks = report.get("checks", {}) if isinstance(report, dict) else {}
    if isinstance(checks, dict):
        for check_id, check in checks.items():
            if not isinstance(check, dict) or check.get("status") in {None, "ok", "pass", "skipped"}:
                continue
            status = str(check.get("status"))
            severity = "S1" if status in {"fail", "error"} else "S2" if status == "warning" else "S4"
            add_finding(
                findings,
                domain="built_in",
                severity=severity,
                confidence="high",
                code=re.sub(r"[^a-z0-9_]+", "_", check_id.lower()),
                source="codex doctor --json",
                summary=str(check.get("summary") or check_id),
                evidence={"check_id": check_id, "status": status, "details": check.get("details"), "issues": check.get("issues")},
                impact="Built-in Codex health check is not passing.",
                recommendation=str(check.get("remediation") or "Inspect this check independently; preserve environment-specific sub-checks."),
                fixability="built_in_guidance",
            )


def build_report(cwd: Path, skip_builtin: bool) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    inventory: dict[str, Any] = {}
    cwd = cwd.resolve()
    root = git_root(cwd)
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()
    user_path = codex_home / "config.toml"
    project_path = (root / ".codex" / "config.toml") if root else Path("/__missing__")
    user_config = load_toml(user_path, findings)
    project_config = load_toml(project_path, findings) if root else {}
    effective = deep_merge(user_config, project_config)

    built_in_doctor(cwd, findings, inventory, skip_builtin)
    scan_instructions(cwd, root, codex_home, effective, findings, inventory)
    scan_skills(cwd, root, codex_home, findings, inventory)
    scan_config_mcp_hooks(root, codex_home, user_config, project_config, findings, inventory, cwd)
    scan_git_root(root, findings, inventory)

    counts = Counter(x["severity"] for x in findings)
    overall = "fail" if counts["S0"] or counts["S1"] else "warn" if findings else "pass"
    return {
        "schemaVersion": SCHEMA_VERSION,
        "scanner": "codex-doctor-workspace",
        "cwd": str(cwd),
        "repo_root": str(root) if root else None,
        "overallStatus": overall,
        "summary": {severity: counts[severity] for severity in SEVERITIES} | {"total": len(findings)},
        "findings": sorted(findings, key=lambda x: (SEVERITIES.index(x["severity"]), x["domain"], x["id"])),
        "inventory": inventory,
        "safety": {"read_only": True, "hooks_executed": False, "repairs_available_in_scanner": False},
    }


def print_human(report: dict[str, Any]) -> None:
    print(f"Codex workspace doctor: {report['overallStatus'].upper()}")
    print(" ".join(f"{k}={v}" for k, v in report["summary"].items()))
    for finding in report["findings"]:
        print(f"[{finding['severity']}/{finding['confidence']}] {finding['id']} — {finding['summary']}")
        print(f"  source: {finding['source']}")
        print(f"  recommendation: {finding['recommendation']}")


def compact_report(report: dict[str, Any]) -> dict[str, Any]:
    """Keep decision-relevant evidence while omitting large deterministic inventories."""
    inventory = report.get("inventory", {})
    built_in = inventory.get("built_in_doctor")
    compact_built_in: Any = built_in
    if isinstance(built_in, dict) and isinstance(built_in.get("checks"), dict):
        check_counts: Counter[str] = Counter()
        checks: dict[str, Any] = {}
        for check_id, check in built_in["checks"].items():
            if not isinstance(check, dict):
                continue
            status = str(check.get("status", "unknown"))
            check_counts[status] += 1
            checks[check_id] = {
                "status": status,
                "summary": check.get("summary"),
            }
        compact_built_in = {
            "schemaVersion": built_in.get("schemaVersion"),
            "codexVersion": built_in.get("codexVersion"),
            "overallStatus": built_in.get("overallStatus"),
            "checkStatusCounts": dict(sorted(check_counts.items())),
            "checks": checks,
        }

    skills = inventory.get("skills", {})
    compact_skills: Any = skills
    if isinstance(skills, dict):
        items = skills.get("items", [])
        compact_skills = {
            "count": skills.get("count"),
            "roots": skills.get("roots", []),
            "itemsOmitted": len(items) if isinstance(items, list) else 0,
        }

    compact_inventory = {
        "built_in_doctor": compact_built_in,
        "instructions": inventory.get("instructions"),
        "skills": compact_skills,
        "config": inventory.get("config"),
        "mcp": inventory.get("mcp"),
        "plugins": inventory.get("plugins"),
        "hooks": inventory.get("hooks"),
        "git": inventory.get("git"),
    }
    return {**report, "inventory": compact_inventory}


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Codex workspace health scanner")
    parser.add_argument("--cwd", default=os.getcwd(), help="Working directory whose effective scope should be checked")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="Emit full machine-readable JSON, including complete inventories")
    output.add_argument("--compact-json", action="store_true", help="Emit decision-relevant JSON without large Skill and built-in detail inventories")
    parser.add_argument("--skip-built-in", action="store_true", help="Skip `codex doctor --json` when it already ran")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when S0 or S1 findings exist")
    args = parser.parse_args()
    cwd = Path(args.cwd)
    if not cwd.is_dir():
        parser.error(f"--cwd is not a directory: {cwd}")
    report = build_report(cwd, args.skip_built_in)
    if args.json or args.compact_json:
        payload = compact_report(report) if args.compact_json else report
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print_human(report)
    if args.strict and (report["summary"]["S0"] or report["summary"]["S1"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
