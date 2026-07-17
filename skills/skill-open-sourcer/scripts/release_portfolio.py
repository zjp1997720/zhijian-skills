#!/usr/bin/env python3
"""Prepare and verify immutable Portfolio release plans."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from export_mirror import file_manifest, manifest_digest  # noqa: E402


SENSITIVE_ENV_FRAGMENTS = (
    "TOKEN",
    "PASSWORD",
    "SECRET",
    "API_KEY",
    "APIKEY",
    "GITHUB_",
    "GH_",
    "SSH_AUTH_SOCK",
    "GIT_ASKPASS",
)


class ReleaseError(RuntimeError):
    pass


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_json(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=check
    )


def repository_head(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def worktree_is_clean(repo: Path) -> bool:
    return not git(repo, "status", "--porcelain").stdout.strip()


def path_digest(path: Path) -> str:
    return manifest_digest(file_manifest(path, exclude_source=False))


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"


def pinned_skills_version(repo: Path) -> str:
    lock = json.loads((repo / "package-lock.json").read_text(encoding="utf-8"))
    return lock.get("packages", {}).get("node_modules/skills", {}).get("version", "missing")


def executor_identity(repo: Path) -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "node": subprocess.run(
            ["node", "--version"], text=True, capture_output=True, check=False
        ).stdout.strip()
        or "missing",
        "skills_cli": pinned_skills_version(repo),
        "registry_schema_digest": file_digest(repo / "registry/skills.schema.json"),
        "registry_digest": file_digest(repo / "registry/skills.json"),
        "release_engine_digest": file_digest(Path(__file__).resolve()),
        "mirror_exporter_digest": file_digest(SCRIPT_DIR / "export_mirror.py"),
        "portfolio_validator_digest": file_digest(SCRIPT_DIR / "portfolio.py"),
    }


def sanitized_environment(environment: dict[str, str] | None = None) -> dict[str, str]:
    source = dict(os.environ if environment is None else environment)
    return {
        key: value
        for key, value in source.items()
        if not any(fragment in key.upper() for fragment in SENSITIVE_ENV_FRAGMENTS)
    }


def load_registry(repo: Path) -> list[dict[str, Any]]:
    payload = json.loads((repo / "registry/skills.json").read_text(encoding="utf-8"))
    return [item for item in payload["skills"] if item.get("lifecycle") == "active"]


def tag_exists(repo: Path, tag: str) -> bool:
    return git(repo, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}", check=False).returncode == 0


def record_changed(repo: Path, record: dict[str, Any]) -> tuple[bool, str]:
    tag = record["canonical_tag"]
    if not tag_exists(repo, tag):
        previous = git(
            repo,
            "tag",
            "--list",
            f"{record['name']}/v*",
            "--sort=-v:refname",
        ).stdout.splitlines()
        if not previous:
            return True, "initial_baseline"
        paths = [
            record["path"],
            record["documentation"],
            record["documentation_zh"],
            record["changelog"],
        ]
        changed = git(repo, "diff", "--quiet", previous[0], "--", *paths, check=False).returncode != 0
        return changed, "content_change" if changed else "version_declaration"
    paths = [
        record["path"],
        record["documentation"],
        record["documentation_zh"],
        record["changelog"],
    ]
    changed = git(repo, "diff", "--quiet", tag, "--", *paths, check=False).returncode != 0
    return changed, "content_change" if changed else "unchanged"


def build_release_plan(repo: Path, *, excluded: set[str] | None = None) -> dict[str, Any]:
    repo = repo.resolve()
    excluded = excluded or set()
    if not worktree_is_clean(repo):
        raise ReleaseError("plan.dirty: commit or stash canonical changes before planning")
    head = repository_head(repo)
    identity = executor_identity(repo)
    releases: list[dict[str, Any]] = []
    for record in sorted(load_registry(repo), key=lambda item: item["name"]):
        if record["name"] in excluded:
            continue
        changed, reason = record_changed(repo, record)
        if not changed:
            continue
        payload = {
            "skill": record["name"],
            "version": record["version"],
            "canonical_tag": record["canonical_tag"],
            "mirror_tag": record["mirror_tag"],
            "mirror": record["mirror"],
            "source_commit": head,
            "content_digest": path_digest(repo / record["path"]),
            "documentation_digest": digest_json(
                {
                    "en": file_digest(repo / record["documentation"]),
                    "zh": file_digest(repo / record["documentation_zh"]),
                    "changelog": file_digest(repo / record["changelog"]),
                }
            ),
            "semver_reason": reason,
            "validation_commands": record.get("validation", {}).get("commands", []),
            "status": "prepared",
        }
        releases.append(payload)

    seed = {
        "schema_version": "1.0.0",
        "repository": str(repo),
        "base_commit": head,
        "executor_identity": identity,
        "releases": releases,
    }
    plan_id = digest_json(seed)[:20]
    for release in releases:
        release["candidate_commit"] = head
        release["candidate_ref"] = f"refs/zhijian-candidates/{plan_id}/{release['skill']}"
    plan = dict(seed, plan_id=plan_id, releases=releases)
    for release in releases:
        git(repo, "update-ref", release["candidate_ref"], head)
    return plan


def verify_plan(plan: dict[str, Any]) -> None:
    repo = Path(plan["repository"]).resolve()
    if repository_head(repo) != plan["base_commit"] or not worktree_is_clean(repo):
        raise ReleaseError("plan.stale: canonical source changed after Dry Run")
    if executor_identity(repo) != plan["executor_identity"]:
        raise ReleaseError("plan.stale: execution identity changed after Dry Run")
    records = {item["name"]: item for item in load_registry(repo)}
    for release in plan["releases"]:
        record = records.get(release["skill"])
        if not record or path_digest(repo / record["path"]) != release["content_digest"]:
            raise ReleaseError(f"plan.stale: payload changed for {release['skill']}")
        current_docs = digest_json(
            {
                "en": file_digest(repo / record["documentation"]),
                "zh": file_digest(repo / record["documentation_zh"]),
                "changelog": file_digest(repo / record["changelog"]),
            }
        )
        if current_docs != release["documentation_digest"]:
            raise ReleaseError(f"plan.stale: documentation changed for {release['skill']}")


def state_root() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return base / "zhijian-skills/releases"


def update_ledger(plan: dict[str, Any], skill: str, step: str) -> dict[str, Any]:
    if skill not in {item["skill"] for item in plan["releases"]}:
        raise ReleaseError(f"ledger.skill_unknown: {skill}")
    root = state_root()
    root.mkdir(parents=True, exist_ok=True)
    ledger_path = root / f"{plan['plan_id']}.json"
    lock_path = root / f"{plan['plan_id']}.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if ledger_path.is_file():
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        else:
            ledger = {"plan_id": plan["plan_id"], "skills": {}}
        ledger["skills"].setdefault(skill, {})[step] = "verified"
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=root, delete=False
        ) as handle:
            json.dump(ledger, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            temporary = Path(handle.name)
        temporary.replace(ledger_path)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return ledger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan")
    plan.add_argument("--repo", required=True)
    plan.add_argument("--all", action="store_true", required=True)
    plan.add_argument("--dry-run", action="store_true", required=True)
    plan.add_argument("--exclude", action="append", default=[])
    plan.add_argument("--plan-out", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--plan", required=True)
    record = subparsers.add_parser("record-step")
    record.add_argument("--plan", required=True)
    record.add_argument("--skill", required=True)
    record.add_argument("--step", required=True)
    return parser


def read_plan(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "plan":
            plan = build_release_plan(Path(args.repo), excluded=set(args.exclude))
            Path(args.plan_out).write_text(
                json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        elif args.command == "verify":
            verify_plan(read_plan(args.plan))
            print("Release plan is current and executable.")
        else:
            plan = read_plan(args.plan)
            verify_plan(plan)
            print(json.dumps(update_ledger(plan, args.skill, args.step), ensure_ascii=False, sort_keys=True))
    except (ReleaseError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
