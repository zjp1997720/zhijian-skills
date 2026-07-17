#!/usr/bin/env python3
"""Audit, apply, and roll back canonical public-Skill symlinks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IGNORED_PARTS = {".git", "node_modules", "__pycache__", "coverage", "dist", "reports"}


class LinkError(RuntimeError):
    pass


def manifest(root: Path) -> dict[str, str]:
    if not root.is_dir():
        return {}
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        if path.name == ".DS_Store" or path.suffix == ".pyc":
            continue
        result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def parse_roots(values: list[str]) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    for value in values:
        if "=" not in value:
            raise LinkError(f"link.root_invalid: expected harness=/absolute/path, got {value}")
        harness, raw_path = value.split("=", 1)
        path = Path(raw_path).expanduser().resolve()
        if harness not in {"codex", "claude-code", "agents"} or not path.is_absolute():
            raise LinkError(f"link.root_invalid: {value}")
        roots.append((harness, path))
    return roots


def load_registry(repo: Path) -> list[dict[str, Any]]:
    payload = json.loads((repo / "registry/skills.json").read_text(encoding="utf-8"))
    return [record for record in payload["skills"] if record.get("lifecycle") == "active"]


def plan_links(repo: Path, roots: list[tuple[str, Path]]) -> dict[str, Any]:
    repo = repo.resolve()
    records = load_registry(repo)
    actions: list[dict[str, Any]] = []
    for harness, root in roots:
        root = Path(os.path.realpath(root))
        for record in records:
            canonical = (repo / record["path"]).resolve()
            entry = root / record["name"]
            supported = harness in record["harnesses"]
            if not supported and not entry.exists() and not entry.is_symlink():
                continue
            action: dict[str, Any] = {
                "harness": harness,
                "root": str(root),
                "skill": record["name"],
                "entry": str(entry),
                "canonical": str(canonical),
            }
            if not supported:
                action.update(status="remove-unsupported", different=True)
            elif entry.is_symlink() and entry.resolve() == canonical:
                action.update(status="healthy", different=False)
            elif not entry.exists() and not entry.is_symlink():
                action.update(status="create", different=False)
            else:
                different = True
                if entry.is_dir() and not entry.is_symlink():
                    different = manifest(entry) != manifest(canonical)
                action.update(status="replace", different=different)
            actions.append(action)
    return {"schema_version": "1.0.0", "repo": str(repo), "actions": actions}


def backup_root() -> Path:
    state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return state / "zhijian-skills/link-backups"


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def apply_links(plan: dict[str, Any], *, accept_differences: bool) -> dict[str, Any]:
    conflicts = [
        action
        for action in plan["actions"]
        if action["status"] == "replace" and action["different"]
    ]
    if conflicts and not accept_differences:
        names = ", ".join(f"{item['harness']}:{item['skill']}" for item in conflicts)
        raise LinkError(f"link.differences: review and rerun with --accept-differences: {names}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    root = backup_root() / run_id
    manifest_path = root / "manifest.json"
    completed: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "schema_version": "1.0.0",
        "repo": plan["repo"],
        "state": "running",
        "completed": completed,
        "in_progress": None,
        "manifest": str(manifest_path),
    }
    write_json_atomic(manifest_path, result)
    try:
        for index, action in enumerate(plan["actions"]):
            if action["status"] == "healthy":
                continue
            entry = Path(action["entry"])
            canonical = Path(action["canonical"])
            entry.parent.mkdir(parents=True, exist_ok=True)
            completed_action = dict(action)
            if entry.exists() or entry.is_symlink():
                backup = root / f"{index:03d}-{action['harness']}-{action['skill']}"
                completed_action["backup"] = str(backup)
            result["in_progress"] = completed_action
            write_json_atomic(manifest_path, result)
            if entry.exists() or entry.is_symlink():
                backup = Path(completed_action["backup"])
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(entry), str(backup))
            if action["status"] == "remove-unsupported":
                completed.append(completed_action)
                result["in_progress"] = None
                write_json_atomic(manifest_path, result)
                continue
            relative = os.path.relpath(canonical, entry.parent)
            entry.symlink_to(relative, target_is_directory=True)
            if not entry.is_symlink() or entry.resolve() != canonical:
                raise LinkError(f"link.verification: failed to link {entry}")
            completed.append(completed_action)
            result["in_progress"] = None
            write_json_atomic(manifest_path, result)
    except Exception as exc:
        rollback_actions(completed, in_progress=result["in_progress"])
        result["state"] = "rolled-back"
        result["in_progress"] = None
        result["error"] = str(exc)
        write_json_atomic(manifest_path, result)
        raise
    result["state"] = "complete"
    write_json_atomic(manifest_path, result)
    return result


def canonical_link_is_intact(action: dict[str, Any]) -> bool:
    entry = Path(action["entry"])
    return entry.is_symlink() and entry.resolve() == Path(action["canonical"])


def validate_rollback_state(action: dict[str, Any], *, in_progress: bool) -> None:
    entry = Path(action["entry"])
    backup = action.get("backup")
    backup_exists = bool(backup and Path(backup).exists())
    status = action["status"]

    if in_progress and not backup_exists and status != "create":
        return
    if status == "remove-unsupported":
        if entry.exists() or entry.is_symlink():
            raise LinkError(f"link.rollback_conflict: {entry} was recreated after migration")
        return
    if entry.exists() or entry.is_symlink():
        if not canonical_link_is_intact(action):
            raise LinkError(f"link.rollback_conflict: {entry} changed after migration")
    elif not in_progress:
        raise LinkError(f"link.rollback_conflict: expected canonical link is missing: {entry}")


def rollback_actions(
    actions: list[dict[str, Any]], *, in_progress: dict[str, Any] | None = None
) -> None:
    journal = [(action, False) for action in actions]
    if in_progress:
        journal.append((in_progress, True))
    for action, is_in_progress in journal:
        validate_rollback_state(action, in_progress=is_in_progress)
    for action, _ in reversed(journal):
        entry = Path(action["entry"])
        backup = action.get("backup")
        backup_exists = bool(backup and Path(backup).exists())
        if canonical_link_is_intact(action):
            entry.unlink()
        if backup_exists:
            entry.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(backup, entry)


def rollback_manifest(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    try:
        relative = path.relative_to(backup_root().resolve())
    except ValueError as exc:
        raise LinkError(f"link.rollback_manifest_unsafe: {path}") from exc
    if len(relative.parts) != 2 or relative.name != "manifest.json":
        raise LinkError(f"link.rollback_manifest_unsafe: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if Path(payload.get("manifest", "")).expanduser().resolve() != path:
        raise LinkError(f"link.rollback_manifest_mismatch: {path}")
    if payload.get("state") == "rolled-back":
        return payload
    rollback_actions(
        list(payload.get("completed", [])), in_progress=payload.get("in_progress")
    )
    payload["state"] = "rolled-back"
    payload["in_progress"] = None
    payload["rolled_back"] = True
    write_json_atomic(path, payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo")
    parser.add_argument("--root", action="append", default=[])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback")
    parser.add_argument("--accept-differences", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.rollback:
            result = rollback_manifest(Path(args.rollback))
        else:
            if not args.repo or not args.root:
                raise LinkError("link.arguments: --repo and at least one --root are required")
            result = plan_links(Path(args.repo), parse_roots(args.root))
            if args.apply:
                result = apply_links(result, accept_differences=args.accept_differences)
    except (LinkError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        actions = result.get("actions", result.get("completed", []))
        for action in actions:
            print(f"{action.get('status', 'linked'):8} {action['harness']:11} {action['skill']} -> {action['canonical']}")
        if result.get("manifest"):
            print(f"Rollback manifest: {result['manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
