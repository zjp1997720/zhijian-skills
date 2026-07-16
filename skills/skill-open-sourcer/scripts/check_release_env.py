#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str], cwd: Path | None = None, timeout: int = 15) -> dict:
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except FileNotFoundError:
        return {"ok": False, "exit_code": None, "stdout": "", "stderr": "not found"}
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": f"timeout after {timeout}s",
        }
    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def command_info(name: str, version_args: list[str] | None = None) -> dict:
    path = shutil.which(name)
    info = {"name": name, "path": path, "ok": bool(path)}
    if path and version_args:
        result = run([name, *version_args])
        info["version"] = (result["stdout"] or result["stderr"]).splitlines()[0] if (result["stdout"] or result["stderr"]) else ""
    return info


def detect_git_remote(cwd: Path | None) -> dict:
    if not cwd:
        return {"ok": False, "reason": "no_cwd"}
    inside = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=cwd)
    if not inside["ok"]:
        return {"ok": False, "reason": "not_git_repo"}
    remote = run(["git", "remote", "get-url", "origin"], cwd=cwd)
    if not remote["ok"]:
        return {"ok": False, "reason": "no_origin_remote"}
    return {"ok": True, "remote": remote["stdout"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local environment for open-sourcing a skill.")
    parser.add_argument("--repo-dir", help="Existing release repo path, if one already exists")
    parser.add_argument("--check-npx-skills", action="store_true", help="Run npx skills --help to verify the CLI can execute")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    args = parser.parse_args()

    repo_dir = Path(args.repo_dir).expanduser().resolve() if args.repo_dir else None
    checks = {
        "python3": command_info("python3", ["--version"]),
        "git": command_info("git", ["--version"]),
        "node": command_info("node", ["--version"]),
        "npx": command_info("npx", ["--version"]),
        "gh": command_info("gh", ["--version"]),
    }

    gh_auth = {"ok": False, "reason": "gh_not_installed"}
    if checks["gh"]["ok"]:
        auth = run(["gh", "auth", "status"])
        gh_auth = {"ok": auth["ok"], "stdout": auth["stdout"], "stderr": auth["stderr"]}

    npx_skills = {"ok": None, "reason": "not_checked"}
    if args.check_npx_skills:
        if checks["npx"]["ok"]:
            npx_skills = run(["npx", "--yes", "skills", "--help"], timeout=60)
        else:
            npx_skills = {"ok": False, "reason": "npx_not_installed"}

    remote = detect_git_remote(repo_dir)
    required = ["python3", "git", "node", "npx"]
    missing_required = [name for name in required if not checks[name]["ok"]]
    publish_surfaces = {
        "gh_authenticated": gh_auth["ok"],
        "existing_origin_remote": remote["ok"],
        "github_app_or_mcp": "manual-runtime-check",
    }

    blockers = []
    for name in missing_required:
        blockers.append(f"missing_required_command:{name}")
    if args.check_npx_skills and not npx_skills["ok"]:
        blockers.append("npx_skills_unavailable")

    warnings = []
    if not gh_auth["ok"] and not remote["ok"]:
        warnings.append("no_local_github_publish_surface_detected")

    result = {
        "status": "blocked" if blockers else "ready",
        "checks": checks,
        "gh_auth": gh_auth,
        "npx_skills": npx_skills,
        "git_remote": remote,
        "publish_surfaces": publish_surfaces,
        "blockers": blockers,
        "warnings": warnings,
        "notes": [
            "gh is the default local GitHub publishing surface.",
            "GitHub MCP/app or an existing authenticated remote can replace gh when available in the agent runtime.",
            "Run with --check-npx-skills before final release verification or when network/package access is uncertain.",
        ],
    }

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Status: {result['status']}")
        for name in ["python3", "git", "node", "npx", "gh"]:
            info = checks[name]
            suffix = f" ({info.get('version', '')})" if info.get("version") else ""
            print(f"{name}: {'ok' if info['ok'] else 'missing'} {info.get('path') or ''}{suffix}")
        print(f"gh auth: {'ok' if gh_auth['ok'] else 'not available'}")
        print(f"existing origin remote: {'ok' if remote['ok'] else remote.get('reason', 'not available')}")
        if args.check_npx_skills:
            print(f"npx skills: {'ok' if npx_skills['ok'] else 'failed'}")
        for item in blockers:
            print(f"[blocker] {item}")
        for item in warnings:
            print(f"[warning] {item}")

    return 2 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
