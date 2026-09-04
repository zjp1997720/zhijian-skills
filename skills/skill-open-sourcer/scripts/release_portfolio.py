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
from git_sync_guard import (  # noqa: E402
    SyncGuardError,
    ensure_checkout_ready,
    mark_needs_sync,
    remote_head,
    verify_canonical_origin,
)

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


IGNORED_PARTS = {
    ".git",
    "__pycache__",
    "node_modules",
    "coverage",
    "dist",
    "reports",
}

GOVERNANCE_BASELINE_FIELDS = (
    "trust_report",
    "output_quality_scorecard",
)


def file_manifest(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if path.name == ".DS_Store" or path.suffix == ".pyc":
            continue
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def manifest_digest(manifest: dict[str, str]) -> str:
    return hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest()


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
    return manifest_digest(file_manifest(path))


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"


def governance_baselines(repo: Path, record: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Resolve and freeze committed governance evidence declared by a Skill."""
    skill_root = (repo / record["path"]).resolve()
    manifest_path = skill_root / "manifest.json"
    if not manifest_path.exists():
        return {}
    if not manifest_path.is_file():
        raise ReleaseError(f"plan.manifest_invalid: {record['name']}: manifest.json is not a file")

    manifest_relative = manifest_path.relative_to(repo).as_posix()
    tracked_manifest = git(
        repo,
        "cat-file",
        "-e",
        f"HEAD:{manifest_relative}",
        check=False,
    )
    if tracked_manifest.returncode != 0:
        raise ReleaseError(
            f"plan.manifest_untracked: {record['name']}: {manifest_relative} is not tracked at HEAD"
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseError(
            f"plan.manifest_invalid: {record['name']}: cannot read manifest.json"
        ) from exc
    if not isinstance(manifest, dict):
        raise ReleaseError(
            f"plan.manifest_invalid: {record['name']}: manifest.json must contain an object"
        )
    governed = (
        manifest.get("maturity_tier") == "governed"
        or manifest.get("lifecycle_stage") == "governed"
    )
    baselines: dict[str, dict[str, str]] = {}
    for field in GOVERNANCE_BASELINE_FIELDS:
        declared = manifest.get(field)
        if declared is None:
            if governed:
                raise ReleaseError(
                    f"plan.baseline_undeclared: {record['name']}: manifest.{field} is required"
                )
            continue
        if not isinstance(declared, str) or not declared.strip():
            raise ReleaseError(
                f"plan.baseline_invalid: {record['name']}: manifest.{field} must be a relative file path"
            )

        baseline_path = (skill_root / declared).resolve()
        try:
            baseline_path.relative_to(skill_root)
            baseline_relative = baseline_path.relative_to(repo).as_posix()
        except ValueError as exc:
            raise ReleaseError(
                f"plan.baseline_unsafe: {record['name']}: manifest.{field} escapes the Skill payload"
            ) from exc
        if not baseline_path.is_file():
            raise ReleaseError(
                f"plan.baseline_missing: {record['name']}: manifest.{field} -> {baseline_relative}"
            )
        tracked = git(
            repo,
            "cat-file",
            "-e",
            f"HEAD:{baseline_relative}",
            check=False,
        )
        if tracked.returncode != 0:
            raise ReleaseError(
                f"plan.baseline_untracked: {record['name']}: manifest.{field} -> "
                f"{baseline_relative} is not tracked at HEAD"
            )
        baselines[field] = {
            "path": baseline_relative,
            "sha256": file_digest(baseline_path),
        }
    return baselines


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
        "portfolio_validator_digest": file_digest(SCRIPT_DIR / "portfolio.py"),
    }


def create_candidate_commit(
    repo: Path, *, head: str, plan_id: str, skill: str, version: str
) -> str:
    """Create one deterministic detached commit for a Skill release candidate."""
    tree = git(repo, "rev-parse", f"{head}^{{tree}}").stdout.strip()
    source_date = git(repo, "show", "-s", "--format=%aI", head).stdout.strip()
    environment = sanitized_environment()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Zhijian Skills Release Planner",
            "GIT_AUTHOR_EMAIL": "releases@zhijian-skills.local",
            "GIT_AUTHOR_DATE": source_date,
            "GIT_COMMITTER_NAME": "Zhijian Skills Release Planner",
            "GIT_COMMITTER_EMAIL": "releases@zhijian-skills.local",
            "GIT_COMMITTER_DATE": source_date,
        }
    )
    message = f"release candidate: {skill} v{version}\n\nPlan: {plan_id}\n"
    result = subprocess.run(
        ["git", "commit-tree", tree, "-p", head],
        cwd=repo,
        input=message,
        text=True,
        capture_output=True,
        check=True,
        env=environment,
    )
    return result.stdout.strip()


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


def build_release_plan(
    repo: Path,
    *,
    source_checkout: Path,
    selected: set[str] | None = None,
    excluded: set[str] | None = None,
) -> dict[str, Any]:
    repo = repo.resolve()
    source_checkout = source_checkout.resolve()
    selected = selected or set()
    excluded = excluded or set()
    if selected and excluded:
        raise ReleaseError("plan.selector_conflict: --exclude cannot be used with --skill")
    verify_canonical_origin(repo)
    verify_canonical_origin(source_checkout)
    ensure_checkout_ready(repo)
    if not worktree_is_clean(repo):
        raise ReleaseError("plan.dirty: commit or stash canonical changes before planning")
    head = repository_head(repo)
    base_remote_sha = remote_head(repo)
    identity = executor_identity(repo)
    records = sorted(load_registry(repo), key=lambda item: item["name"])
    active_names = {record["name"] for record in records}
    unknown = sorted(selected - active_names)
    if unknown:
        raise ReleaseError(f"plan.skill_unknown: {', '.join(unknown)}")
    releases: list[dict[str, Any]] = []
    for record in records:
        if selected and record["name"] not in selected:
            continue
        if record["name"] in excluded:
            continue
        changed, reason = record_changed(repo, record)
        if not changed:
            continue
        baselines = governance_baselines(repo, record)
        payload = {
            "skill": record["name"],
            "version": record["version"],
            "canonical_tag": record["canonical_tag"],
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
            "governance_baselines": baselines,
            "status": "prepared",
        }
        releases.append(payload)

    seed = {
        "schema_version": "1.0.0",
        "repository": str(repo),
        "source_checkout": str(source_checkout),
        "base_commit": head,
        "base_remote_sha": base_remote_sha,
        "remote": "origin",
        "remote_branch": "main",
        "executor_identity": identity,
        "releases": releases,
    }
    plan_id = digest_json(seed)[:20]
    for release in releases:
        release["candidate_ref"] = f"refs/zhijian-candidates/{plan_id}/{release['skill']}"
        release["candidate_commit"] = create_candidate_commit(
            repo,
            head=head,
            plan_id=plan_id,
            skill=release["skill"],
            version=release["version"],
        )
    plan = dict(seed, plan_id=plan_id, releases=releases)
    if source_checkout != repo:
        mark_needs_sync(
            source_checkout,
            status="release-in-progress",
            base_remote_sha=base_remote_sha,
            integration_repo=repo,
            plan_id=plan_id,
        )
    for release in releases:
        git(repo, "update-ref", release["candidate_ref"], release["candidate_commit"])
    return plan


def verify_plan(plan: dict[str, Any], *, check_remote: bool = True) -> None:
    repo = Path(plan["repository"]).resolve()
    ensure_checkout_ready(repo)
    if repository_head(repo) != plan["base_commit"] or not worktree_is_clean(repo):
        raise ReleaseError("plan.stale: canonical source changed after Dry Run")
    if check_remote and remote_head(repo) != plan.get("base_remote_sha"):
        raise ReleaseError("plan.remote_changed: origin/main changed after planning")
    if executor_identity(repo) != plan["executor_identity"]:
        raise ReleaseError("plan.stale: execution identity changed after Dry Run")
    records = {item["name"]: item for item in load_registry(repo)}
    for release in plan["releases"]:
        record = records.get(release["skill"])
        if not record or path_digest(repo / record["path"]) != release["content_digest"]:
            raise ReleaseError(f"plan.stale: payload changed for {release['skill']}")
        if governance_baselines(repo, record) != release.get("governance_baselines", {}):
            raise ReleaseError(f"plan.stale: governance baselines changed for {release['skill']}")
        current_docs = digest_json(
            {
                "en": file_digest(repo / record["documentation"]),
                "zh": file_digest(repo / record["documentation_zh"]),
                "changelog": file_digest(repo / record["changelog"]),
            }
        )
        if current_docs != release["documentation_digest"]:
            raise ReleaseError(f"plan.stale: documentation changed for {release['skill']}")
        candidate = git(
            repo, "rev-parse", "--verify", "--quiet", release["candidate_ref"], check=False
        ).stdout.strip()
        if candidate != release["candidate_commit"]:
            raise ReleaseError(f"plan.stale: candidate ref changed for {release['skill']}")
        parent = git(repo, "rev-parse", f"{candidate}^1").stdout.strip()
        candidate_tree = git(repo, "rev-parse", f"{candidate}^{{tree}}").stdout.strip()
        base_tree = git(repo, "rev-parse", f"{plan['base_commit']}^{{tree}}").stdout.strip()
        if parent != plan["base_commit"] or candidate_tree != base_tree:
            raise ReleaseError(f"plan.stale: candidate commit changed for {release['skill']}")


def verify_frozen_source(plan: dict[str, Any]) -> None:
    """Verify immutable plan objects after a PR merge changes the checked-out HEAD."""
    repo = Path(plan["repository"]).resolve()
    ensure_checkout_ready(repo)
    base = git(
        repo,
        "rev-parse",
        "--verify",
        f"{plan['base_commit']}^{{commit}}",
        check=False,
    ).stdout.strip()
    if base != plan["base_commit"]:
        raise ReleaseError("plan.stale: frozen source commit is unavailable")
    base_tree = git(repo, "rev-parse", f"{base}^{{tree}}").stdout.strip()
    for release in plan["releases"]:
        candidate = git(
            repo,
            "rev-parse",
            "--verify",
            "--quiet",
            release["candidate_ref"],
            check=False,
        ).stdout.strip()
        if candidate != release["candidate_commit"]:
            raise ReleaseError(f"plan.stale: candidate ref changed for {release['skill']}")
        parent = git(repo, "rev-parse", f"{candidate}^1").stdout.strip()
        candidate_tree = git(repo, "rev-parse", f"{candidate}^{{tree}}").stdout.strip()
        if parent != base or candidate_tree != base_tree:
            raise ReleaseError(f"plan.stale: candidate commit changed for {release['skill']}")


def verify_remote_release(plan: dict[str, Any], expected_remote_sha: str) -> str:
    repo = Path(plan["repository"]).resolve()
    actual = remote_head(repo)
    if actual != expected_remote_sha:
        raise ReleaseError(
            f"release.remote_mismatch: expected {expected_remote_sha}, observed {actual}"
        )
    git(repo, "fetch", "--no-tags", "origin", actual)
    ancestor = git(
        repo,
        "merge-base",
        "--is-ancestor",
        plan["base_commit"],
        actual,
        check=False,
    )
    if ancestor.returncode != 0:
        raise ReleaseError("release.source_missing: remote main does not contain the planned source")
    return actual


def cleanup_candidates(plan: dict[str, Any]) -> list[str]:
    """Delete only candidate refs that still point to the plan's frozen commits."""
    repo = Path(plan["repository"]).resolve()
    expected_prefix = f"refs/zhijian-candidates/{plan['plan_id']}/"
    removed: list[str] = []
    for release in plan["releases"]:
        reference = release["candidate_ref"]
        if not reference.startswith(expected_prefix):
            raise ReleaseError(f"cleanup.ref_unsafe: refusing to delete {reference}")
        current = git(repo, "rev-parse", "--verify", "--quiet", reference, check=False)
        if current.returncode != 0:
            continue
        if current.stdout.strip() != release["candidate_commit"]:
            raise ReleaseError(f"cleanup.ref_changed: refusing to delete {reference}")
        git(repo, "update-ref", "-d", reference, release["candidate_commit"])
        removed.append(reference)
    return removed


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
    selector = plan.add_mutually_exclusive_group(required=True)
    selector.add_argument("--all", action="store_true")
    selector.add_argument(
        "--skill",
        action="append",
        default=[],
        metavar="NAME",
        help="plan only the named active Skill; repeat to select multiple Skills",
    )
    plan.add_argument("--dry-run", action="store_true", required=True)
    plan.add_argument(
        "--source-checkout",
        required=True,
        help="original canonical checkout; use the same path as --repo unless a clean integration clone is publishing",
    )
    plan.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="exclude a Skill from --all planning; cannot be combined with --skill",
    )
    plan.add_argument("--plan-out", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--plan", required=True)
    record = subparsers.add_parser("record-step")
    record.add_argument("--plan", required=True)
    record.add_argument("--skill", required=True)
    record.add_argument("--step", required=True)
    record.add_argument(
        "--remote-sha",
        help="required for canonical-pushed; must equal the live origin/main SHA",
    )
    cleanup = subparsers.add_parser("cleanup")
    cleanup.add_argument("--plan", required=True)
    return parser


def read_plan(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "plan":
            plan = build_release_plan(
                Path(args.repo),
                source_checkout=Path(args.source_checkout),
                selected=set(args.skill),
                excluded=set(args.exclude),
            )
            Path(args.plan_out).write_text(
                json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        elif args.command == "verify":
            verify_plan(read_plan(args.plan))
            print("Release plan is current and executable.")
        elif args.command == "record-step":
            plan = read_plan(args.plan)
            if args.step == "canonical-pushed":
                if not args.remote_sha:
                    raise ReleaseError("release.remote_sha_required: canonical-pushed needs --remote-sha")
                verify_frozen_source(plan)
                actual_remote = verify_remote_release(plan, args.remote_sha)
                source_checkout = Path(plan["source_checkout"]).resolve()
                repository = Path(plan["repository"]).resolve()
                if source_checkout != repository:
                    mark_needs_sync(
                        source_checkout,
                        status="needs-sync",
                        base_remote_sha=plan["base_remote_sha"],
                        integration_repo=repository,
                        plan_id=plan["plan_id"],
                        observed_remote_head=actual_remote,
                    )
            else:
                verify_plan(plan)
            print(json.dumps(update_ledger(plan, args.skill, args.step), ensure_ascii=False, sort_keys=True))
        else:
            removed = cleanup_candidates(read_plan(args.plan))
            print(json.dumps({"removed": removed}, ensure_ascii=False, sort_keys=True))
    except (
        ReleaseError,
        SyncGuardError,
        OSError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
