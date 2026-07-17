#!/usr/bin/env python3
"""Export one canonical Skill into its standalone compatibility mirror."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any


MANIFEST_NAME = "SOURCE.json"
IGNORED_PARTS = {
    ".git",
    "__pycache__",
    "node_modules",
    "coverage",
    "dist",
    "reports",
    "_preview_frames",
    "_preview_magazine",
}
EXPORT_IGNORES = shutil.ignore_patterns(
    ".DS_Store",
    ".git",
    "__pycache__",
    "*.pyc",
    "node_modules",
    "coverage",
    "dist",
    "reports",
    "preview.html",
    "_preview_frames",
    "_preview_magazine",
)
WORKFLOW = """name: Redirect contributions

on:
  pull_request_target:
    types: [opened]

permissions:
  contents: read
  pull-requests: write

jobs:
  redirect:
    runs-on: ubuntu-latest
    steps:
      - name: Point contributors to the canonical repository
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: 'This repository is a generated compatibility mirror. Please reopen this contribution in https://github.com/zjp1997720/zhijian-skills.'
            });
            await github.rest.pulls.update({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: context.issue.number,
              state: 'closed'
            });
"""


class ExportError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_manifest(root: Path, *, exclude_source: bool = True) -> dict[str, str]:
    result: dict[str, str] = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if path.name in {".DS_Store", "preview.html"} or path.suffix == ".pyc":
            continue
        if exclude_source and relative == MANIFEST_NAME:
            continue
        result[relative] = sha256_bytes(path.read_bytes())
    return result


def manifest_digest(manifest: dict[str, str]) -> str:
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def payload_digest(skill_dir: Path) -> str:
    return manifest_digest(file_manifest(skill_dir, exclude_source=False))


def ensure_existing_mirror_is_known(destination: Path, *, adopt: bool) -> list[str]:
    if adopt:
        return sorted(
            path.relative_to(destination).as_posix()
            for path in destination.rglob("*")
            if path.is_file() and ".git" not in path.parts
        )
    current = file_manifest(destination)
    if not current:
        return []
    metadata_path = destination / MANIFEST_NAME
    if not metadata_path.is_file():
        raise ExportError(
            "mirror.drift: destination contains files without SOURCE.json; review and rerun with --adopt"
        )
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExportError(f"mirror.drift: invalid SOURCE.json: {exc}") from exc
    expected = metadata.get("files")
    if not isinstance(expected, dict) or current != expected:
        raise ExportError("mirror.drift: destination differs from the last generated manifest")
    return sorted(current)


def remove_generated_files(destination: Path, old_files: list[str]) -> None:
    for relative in sorted(old_files, reverse=True):
        path = destination / relative
        if path.is_file() or path.is_symlink():
            path.unlink()
    for path in sorted(destination.rglob("*"), reverse=True):
        if path.is_dir() and ".git" not in path.parts:
            try:
                path.rmdir()
            except OSError:
                pass


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def export_mirror(
    repo: Path,
    skill: str,
    destination: Path,
    *,
    source_commit: str,
    version: str,
    adopt: bool = False,
) -> dict[str, Any]:
    repo = repo.resolve()
    destination = destination.resolve()
    skill_dir = repo / "skills" / skill
    required = [
        skill_dir / "SKILL.md",
        repo / f"docs/skills/{skill}/README.md",
        repo / f"docs/skills/{skill}/README.zh-CN.md",
        repo / f"docs/changelogs/{skill}.md",
        repo / "LICENSE",
        repo / "CONTRIBUTING.md",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ExportError(f"mirror.source_missing: {', '.join(missing)}")

    destination.mkdir(parents=True, exist_ok=True)
    old_files = ensure_existing_mirror_is_known(destination, adopt=adopt)
    remove_generated_files(destination, old_files)
    (destination / MANIFEST_NAME).unlink(missing_ok=True)

    banner = (
        "> [!IMPORTANT]\n"
        "> This repository is a generated compatibility mirror. "
        "The editable source, Issues, and contributions live in "
        f"[zjp1997720/zhijian-skills](https://github.com/zjp1997720/zhijian-skills/tree/main/skills/{skill}).\n\n"
    )
    readme = (repo / f"docs/skills/{skill}/README.md").read_text(encoding="utf-8")
    readme_zh = (repo / f"docs/skills/{skill}/README.zh-CN.md").read_text(encoding="utf-8")
    (destination / "README.md").write_text(banner + readme, encoding="utf-8")
    (destination / "README.zh-CN.md").write_text(banner + readme_zh, encoding="utf-8")
    copy_file(repo / f"docs/changelogs/{skill}.md", destination / "CHANGELOG.md")
    copy_file(repo / "LICENSE", destination / "LICENSE")
    copy_file(repo / "CONTRIBUTING.md", destination / "CONTRIBUTING.md")
    shutil.copytree(
        skill_dir,
        destination / "skills" / skill,
        copy_function=shutil.copy2,
        ignore=EXPORT_IGNORES,
    )
    readme_assets = repo / f"docs/skills/{skill}/assets/readme"
    if readme_assets.is_dir():
        shutil.copytree(
            readme_assets,
            destination / "assets/readme",
            copy_function=shutil.copy2,
            ignore=EXPORT_IGNORES,
        )
    workflow = destination / ".github/workflows/redirect-contributions.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(WORKFLOW, encoding="utf-8")

    files = file_manifest(destination)
    metadata: dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated": True,
        "canonical_repository": "zjp1997720/zhijian-skills",
        "skill": skill,
        "version": version,
        "source_commit": source_commit,
        "payload_digest": payload_digest(skill_dir),
        "export_digest": manifest_digest(files),
        "files": files,
    }
    (destination / MANIFEST_NAME).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--adopt", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = export_mirror(
            Path(args.repo),
            args.skill,
            Path(args.destination),
            source_commit=args.source_commit,
            version=args.version,
            adopt=args.adopt,
        )
    except ExportError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
