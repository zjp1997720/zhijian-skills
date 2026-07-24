#!/usr/bin/env python3
"""Audit release README structure, local assets, and basic SVG safety.

The checks are deterministic. They complement, rather than replace, rendered
visual inspection. The README/SVG quality model is informed by the MIT-licensed
oil-oil/beautify-github-readme project; see references/third-party-notices.md.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote


MARKDOWN_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[^)]*)?\)")
MARKDOWN_LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)(?:\s+[^)]*)?\)")
HTML_IMAGE_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
HTML_SRC = re.compile(r"\bsrc=[\"']([^\"']+)[\"']", re.IGNORECASE)
HTML_ALT = re.compile(r"\balt=[\"']([^\"']*)[\"']", re.IGNORECASE)
INSTALL_COMMAND = re.compile(r"\bnpx\s+(?:--yes\s+)?skills\s+add\b", re.IGNORECASE)
UNSAFE_SVG_TAGS = {"script", "foreignObject"}
ANIMATION_SVG_TAGS = {"animate", "animateMotion", "animateTransform", "set"}
REMOTE_PREFIXES = ("http://", "https://", "//")
SKIP_LINK_PREFIXES = REMOTE_PREFIXES + ("#", "mailto:", "tel:", "data:")
FIRST_SCREEN_LINES = 80
MAX_ASSET_BYTES = 2_000_000
ROOT_SUPPORT_DIRS = ("agents", "references", "scripts")


@dataclass(frozen=True)
class Finding:
    severity: str
    path: Path
    message: str


def add(findings: list[Finding], severity: str, path: Path, message: str) -> None:
    findings.append(Finding(severity, path, message))


def normalized_target(raw: str) -> str:
    return unquote(raw.strip().strip("<>").split("#", 1)[0].split("?", 1)[0])


def allowed_remote_badge(src: str) -> bool:
    return "img.shields.io/" in src or ("/actions/workflows/" in src and "/badge.svg" in src)


def inside_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def repository_boundary(release_root: Path) -> Path:
    """Allow Portfolio docs to resolve canonical repository links safely."""
    for candidate in (release_root, *release_root.parents):
        if (candidate / "registry" / "skills.json").is_file() and (candidate / "skills").is_dir():
            return candidate.resolve()
    return release_root.resolve()


def prose_before_second_heading(lines: list[str]) -> str | None:
    seen_h1 = False
    in_fence = False
    for raw in lines[:FIRST_SCREEN_LINES]:
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if re.match(r"^#\s+\S", line):
            seen_h1 = True
            continue
        if seen_h1 and re.match(r"^##\s+\S", line):
            return None
        if not seen_h1 or not line:
            continue
        if line.startswith(("<", "![", "[", "#", "|", "-", "*", ">", "`")):
            continue
        plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        plain = re.sub(r"[*_~`]", "", plain).strip()
        if len(plain) >= 12:
            return plain
    return None


def audit_svg(path: Path, display_path: Path, findings: list[Finding]) -> None:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        add(findings, "error", display_path, f"invalid SVG XML: {exc}")
        return

    if "viewBox" not in root.attrib:
        add(findings, "error", display_path, "SVG is missing viewBox")
    if root.attrib.get("role") != "img":
        add(findings, "error", display_path, 'SVG root must declare role="img"')
    aria_labels = set(root.attrib.get("aria-labelledby", "").split())
    if not {"title", "desc"} <= aria_labels:
        add(findings, "error", display_path, "SVG root must reference title and desc with aria-labelledby")
    if path.name == "hero.svg" and not root.attrib.get("data-composition", "").strip():
        add(findings, "warning", display_path, "proof-led Hero is missing a stable data-composition id")

    found_title = False
    found_desc = False
    title_text = ""
    desc_text = ""
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        found_title = found_title or tag == "title"
        found_desc = found_desc or tag == "desc"
        if tag == "title":
            title_text = "".join(node.itertext()).strip()
        if tag == "desc":
            desc_text = "".join(node.itertext()).strip()
        if tag in UNSAFE_SVG_TAGS:
            add(findings, "error", display_path, f"SVG contains unsupported <{tag}>")
        if tag in ANIMATION_SVG_TAGS:
            add(findings, "warning", display_path, f"SVG animation <{tag}> may not work on GitHub")

        for attr_name, value in node.attrib.items():
            local_attr = attr_name.rsplit("}", 1)[-1]
            if local_attr == "href" and value.strip().startswith(REMOTE_PREFIXES):
                add(findings, "error", display_path, f"SVG contains remote href: {value[:100]}")
            if local_attr == "style" and re.search(r"url\s*\(\s*(?:https?:)?//", value, re.IGNORECASE):
                add(findings, "error", display_path, "SVG inline style loads a remote resource")

        if tag == "style":
            style_text = "".join(node.itertext())
            if re.search(r"@import|@font-face|url\s*\(\s*(?:https?:)?//", style_text, re.IGNORECASE):
                add(findings, "error", display_path, "SVG style loads a remote font, stylesheet, or asset")

    if not found_title:
        add(findings, "error", display_path, "SVG is missing <title>")
    elif len(title_text) < 3:
        add(findings, "error", display_path, "SVG <title> is empty or not meaningful")
    if not found_desc:
        add(findings, "error", display_path, "SVG is missing <desc>")
    elif len(desc_text) < 12:
        add(findings, "error", display_path, "SVG <desc> is empty or not meaningful")


def meaningful_alt(value: str) -> bool:
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value.lower()).strip()
    return len(normalized) >= 12 and normalized not in {"image", "hero", "banner", "logo", "readme hero"}


def check_local_target(
    src: str,
    readme: Path,
    release_root: Path,
    findings: list[Finding],
    kind: str,
) -> Path | None:
    if src.startswith(REMOTE_PREFIXES):
        if kind == "image" and allowed_remote_badge(src):
            return None
        add(findings, "warning", readme.relative_to(release_root), f"remote {kind} is fragile: {src[:120]}")
        return None
    if src.startswith(("data:", "#")):
        return None

    clean = normalized_target(src)
    if not clean:
        return None
    target = (readme.parent / clean).resolve()
    shown = readme.relative_to(release_root)
    boundary = repository_boundary(release_root)
    if not inside_root(target, boundary):
        add(findings, "error", shown, f"{kind} escapes the release repository: {src}")
        return None
    if not target.exists():
        add(findings, "error", shown, f"missing local {kind}: {src}")
        return None
    if target.is_file() and target.stat().st_size > MAX_ASSET_BYTES:
        add(findings, "warning", target.relative_to(boundary), f"asset exceeds {MAX_ASSET_BYTES} bytes")
    return target


def audit_readme(readme: Path, release_root: Path, findings: list[Finding]) -> None:
    shown = readme.relative_to(release_root)
    try:
        text = readme.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        add(findings, "error", shown, f"cannot read UTF-8 README: {exc}")
        return

    lines = text.splitlines()
    first_screen = "\n".join(lines[:FIRST_SCREEN_LINES])
    if not re.search(r"^#\s+\S", first_screen, re.MULTILINE):
        add(findings, "error", shown, f"first {FIRST_SCREEN_LINES} lines have no accessible H1 title")
    if prose_before_second_heading(lines) is None:
        add(findings, "warning", shown, "no plain-language value sentence appears between H1 and the first H2")
    if not INSTALL_COMMAND.search(first_screen):
        add(findings, "error", shown, f"first {FIRST_SCREEN_LINES} lines do not contain an npx skills add command")

    badge_count = len(re.findall(r"img\.shields\.io|badge", first_screen, re.IGNORECASE))
    if badge_count > 3:
        add(findings, "warning", shown, f"first screen contains {badge_count} badge references; keep at most 3")

    image_sources: list[tuple[str, str]] = []
    for alt, src in MARKDOWN_IMAGE.findall(text):
        if not alt.strip():
            add(findings, "error", shown, f"Markdown image has empty alt text: {src}")
        elif not allowed_remote_badge(src) and not meaningful_alt(alt):
            add(findings, "warning", shown, f"Markdown image alt text is too generic: {src}")
        image_sources.append((src, "image"))

    for tag in HTML_IMAGE_TAG.findall(text):
        src_match = HTML_SRC.search(tag)
        alt_match = HTML_ALT.search(tag)
        if not src_match:
            add(findings, "error", shown, f"HTML img has no src: {tag[:120]}")
            continue
        src = src_match.group(1)
        if not alt_match or not alt_match.group(1).strip():
            add(findings, "error", shown, f"HTML image has empty or missing alt text: {src}")
        elif not allowed_remote_badge(src) and not meaningful_alt(alt_match.group(1)):
            add(findings, "warning", shown, f"HTML image alt text is too generic: {src}")
        image_sources.append((src, "image"))

    audited_svgs: set[Path] = set()
    for src, kind in image_sources:
        target = check_local_target(src, readme, release_root, findings, kind)
        if target and target.is_file() and target.suffix.lower() == ".svg" and target not in audited_svgs:
            audited_svgs.add(target)
            audit_svg(target, target.relative_to(release_root), findings)

    for _label, href in MARKDOWN_LINK.findall(text):
        if href.startswith(SKIP_LINK_PREFIXES):
            continue
        check_local_target(href, readme, release_root, findings, "link")


def audit_package_layout(release_root: Path, findings: list[Finding]) -> None:
    root_skill = release_root / "SKILL.md"
    if not root_skill.is_file():
        return

    support_dirs = [name for name in ROOT_SUPPORT_DIRS if (release_root / name).is_dir()]
    try:
        skill_text = root_skill.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        skill_text = ""
    if (release_root / "assets").is_dir() and re.search(r"(?:^|[(`'\"/])assets/", skill_text):
        support_dirs.append("assets")

    if support_dirs:
        listed = ", ".join(f"{name}/" for name in support_dirs)
        add(
            findings,
            "error",
            Path("SKILL.md"),
            "root-level remote npx installs copy only SKILL.md; move the complete "
            f"payload under skills/<skill-name>/ so these files are installed: {listed}",
        )


def discover_readmes(inputs: list[str]) -> tuple[Path, list[Path]]:
    paths = [Path(raw).expanduser().resolve() for raw in inputs]
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise ValueError(f"path does not exist: {missing[0]}")

    if len(paths) == 1 and paths[0].is_dir():
        release_root = paths[0]
        readmes = sorted(path for path in release_root.glob("README*.md") if path.is_file())
    else:
        readmes = paths
        if any(not path.is_file() for path in readmes):
            raise ValueError("when passing multiple inputs, every input must be a README file")
        release_root = Path(os.path.commonpath([str(path.parent) for path in readmes])).resolve()

    if not readmes:
        raise ValueError("no README*.md files found")
    if not any(path.name == "README.md" for path in readmes):
        raise ValueError("release repository is missing README.md")
    return release_root, readmes


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit release README files and local visual assets.")
    parser.add_argument("paths", nargs="+", help="Release repository directory or one or more README files")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    args = parser.parse_args()

    try:
        release_root, readmes = discover_readmes(args.paths)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    audit_package_layout(release_root, findings)
    for readme in readmes:
        audit_readme(readme, release_root, findings)

    errors = [item for item in findings if item.severity == "error"]
    warnings = [item for item in findings if item.severity == "warning"]
    print(f"Release root: {release_root}")
    print(f"README files audited: {len(readmes)}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    for item in findings:
        print(f"[{item.severity}] {item.path}: {item.message}")

    if errors or (args.strict and warnings):
        return 1
    print("OK: deterministic README and SVG checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
