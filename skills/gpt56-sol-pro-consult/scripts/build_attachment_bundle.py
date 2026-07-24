#!/usr/bin/env python3
"""Build a text attachment bundle for GPT 5.6 Sol Pro uploads.

Use this when ChatGPT Web rejects a zip/archive, when a directory has many
small source files, or when preserving file names matters more than preserving
the exact filesystem package.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable


DEFAULT_EXTENSIONS = {
    ".c",
    ".cc",
    ".cfg",
    ".conf",
    ".css",
    ".csv",
    ".go",
    ".h",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".cache",
}

SKIP_FILES = {".DS_Store"}


def iter_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
            continue
        if not path.is_dir():
            continue
        for item in path.rglob("*"):
            if not item.is_file():
                continue
            if item.name in SKIP_FILES:
                continue
            if any(part in SKIP_DIRS for part in item.parts):
                continue
            files.append(item)
    return sorted(set(files), key=lambda p: str(p))


def is_probably_text(path: Path, allowed_extensions: set[str]) -> bool:
    if path.suffix.lower() not in allowed_extensions:
        return False
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\x00" not in chunk


def relative_label(path: Path, roots: list[Path]) -> str:
    for root in roots:
        try:
            return str(path.relative_to(root))
        except ValueError:
            pass
    return str(path)


def fence_for(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    return {
        "md": "markdown",
        "py": "python",
        "js": "javascript",
        "mjs": "javascript",
        "ts": "typescript",
        "tsx": "tsx",
        "json": "json",
        "yaml": "yaml",
        "yml": "yaml",
        "sh": "bash",
        "html": "html",
        "css": "css",
    }.get(ext, ext or "text")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Files or directories to bundle")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output .md/.txt bundle path")
    parser.add_argument("--max-file-bytes", type=int, default=250_000)
    parser.add_argument("--max-total-bytes", type=int, default=2_000_000)
    parser.add_argument(
        "--include-extension",
        action="append",
        default=[],
        help="Additional extension to include, such as .lock",
    )
    args = parser.parse_args()

    roots = [p.resolve() for p in args.paths if p.exists()]
    allowed_extensions = set(DEFAULT_EXTENSIONS)
    allowed_extensions.update(ext if ext.startswith(".") else f".{ext}" for ext in args.include_extension)

    candidates = iter_files(roots)
    selected: list[tuple[Path, str, int, bool]] = []
    skipped: list[str] = []
    total = 0

    for path in candidates:
        resolved = path.resolve()
        label = relative_label(resolved, roots)
        if not is_probably_text(resolved, allowed_extensions):
            skipped.append(f"{label} (unsupported or binary)")
            continue
        try:
            raw = resolved.read_bytes()
        except OSError as exc:
            skipped.append(f"{label} (read error: {exc})")
            continue
        truncated = len(raw) > args.max_file_bytes
        raw = raw[: args.max_file_bytes]
        if total + len(raw) > args.max_total_bytes:
            skipped.append(f"{label} (total bundle limit reached)")
            continue
        total += len(raw)
        text = raw.decode("utf-8", errors="replace")
        selected.append((resolved, text, len(raw), truncated))

    lines: list[str] = [
        "# GPT 5.6 Sol Pro Attachment Bundle",
        "",
        "The attached bundle contains local files for review. Local paths are provenance labels only.",
        "",
        "## Manifest",
    ]
    for path, _text, size, truncated in selected:
        label = relative_label(path, roots)
        note = " truncated" if truncated else ""
        lines.append(f"- `{label}` ({size} bytes{note})")
    if skipped:
        lines.extend(["", "## Skipped"])
        lines.extend(f"- {item}" for item in skipped)

    lines.extend(["", "## Files"])
    for path, text, _size, truncated in selected:
        label = relative_label(path, roots)
        lang = fence_for(path)
        lines.extend(["", f"### `{label}`", "", f"````{lang}", text.rstrip(), "````"])
        if truncated:
            lines.append("")
            lines.append("[TRUNCATED: file exceeded max-file-bytes]")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output)
    print(f"files={len(selected)} skipped={len(skipped)} bytes={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
