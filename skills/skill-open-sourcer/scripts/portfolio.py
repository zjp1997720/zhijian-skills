#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from scan_skill_release import scan  # noqa: E402


REQUIRED_RECORD_FIELDS = {
    "name",
    "lifecycle",
    "version",
    "path",
    "documentation",
    "documentation_zh",
    "changelog",
    "canonical_tag",
    "validation",
    "capabilities",
    "harnesses",
}
CAPABILITY_KEYS = {"network", "subprocess", "filesystem", "credentials"}
ALLOWED_HARNESSES = {"codex", "claude-code", "agents"}
MARKDOWN_LINK = re.compile(r"\[[^\]]*]\(([^)]+)\)")
FRONTMATTER_NAME = re.compile(r"(?m)^name:\s*[\"']?([^\"'\n]+)")
FRONTMATTER_DESCRIPTION = re.compile(r"(?m)^description:\s*(.*)$")
NETWORK_PATTERNS = (
    re.compile(r"\b(?:urllib\.request|urlopen|requests\.|httpx\.)"),
    re.compile(r"\bfetch\s*\("),
    re.compile(r"\bhttps?\.request\s*\("),
    re.compile(r"\b(?:curl|wget)\s+"),
)
SUBPROCESS_PATTERNS = (
    re.compile(r"\bsubprocess\."),
    re.compile(r"\bos\.system\s*\("),
    re.compile(r"\bPopen\s*\("),
    re.compile(r"\bchild_process\b"),
    re.compile(r"\b(?:exec|spawn)(?:Sync)?\s*\("),
)
FILESYSTEM_WRITE_PATTERNS = (
    re.compile(r"\.(?:write_text|write_bytes)\s*\("),
    re.compile(r"\bopen\s*\([^)]*,\s*[\"'][wax+]"),
    re.compile(r"\b(?:writeFile|appendFile)(?:Sync)?\s*\("),
)
CREDENTIAL_PATTERNS = (
    re.compile(
        r"(?:os\.environ|process\.env).{0,80}"
        r"(?:TOKEN|PASSWORD|SECRET|API[_-]?KEY|COOKIE)",
        re.IGNORECASE,
    ),
)
EXECUTABLE_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".sh", ".bash", ".zsh"}


def finding(
    finding_id: str,
    message: str,
    *,
    severity: str = "blocker",
    skill: str | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": finding_id,
        "severity": severity,
        "message": message,
    }
    if skill:
        result["skill"] = skill
    if path:
        result["path"] = path
    return result


def extract_frontmatter(skill_file: Path) -> tuple[str | None, str | None]:
    text = skill_file.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        return None, None
    end = text.find("\n---", 4)
    if end < 0:
        return None, None
    frontmatter = text[4:end]
    name_match = FRONTMATTER_NAME.search(frontmatter)
    description_match = FRONTMATTER_DESCRIPTION.search(frontmatter)
    name = name_match.group(1).strip() if name_match else None
    description = description_match.group(1).strip() if description_match else None
    if description in {"|", ">", "|-", ">-"}:
        lines = frontmatter[description_match.end() :].splitlines()
        description = " ".join(
            line.strip()
            for line in lines
            if line.startswith((" ", "\t")) and line.strip()
        )
    return name, description


def missing_references(skill_dir: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for markdown in sorted(skill_dir.rglob("*.md")):
        if any(part in {".git", "node_modules"} for part in markdown.parts):
            continue
        text = markdown.read_text(encoding="utf-8", errors="replace")
        for raw in MARKDOWN_LINK.findall(text):
            target = raw.strip().split("#", 1)[0]
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            candidate = (markdown.parent / target).resolve()
            if skill_dir.resolve() not in candidate.parents and candidate != skill_dir.resolve():
                issues.append(
                    finding(
                        "skill.reference_escape",
                        f"Markdown reference escapes the Skill package: {raw}",
                        path=str(markdown.relative_to(skill_dir)),
                    )
                )
            elif not candidate.exists():
                issues.append(
                    finding(
                        "skill.missing_reference",
                        f"Referenced package file does not exist: {raw}",
                        path=str(markdown.relative_to(skill_dir)),
                    )
                )
    return issues


def validate_skill(skill_dir: Path) -> dict[str, Any]:
    skill_dir = skill_dir.expanduser().resolve()
    issues: list[dict[str, Any]] = []
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        issues.append(finding("skill.entrypoint_missing", "Missing SKILL.md"))
        name = skill_dir.name
    else:
        name, description = extract_frontmatter(skill_file)
        if not name:
            issues.append(
                finding("skill.frontmatter_name", "SKILL.md has no valid name")
            )
            name = skill_dir.name
        if not description:
            issues.append(
                finding(
                    "skill.frontmatter_description",
                    "SKILL.md has no non-empty description",
                    skill=name,
                )
            )
        issues.extend(missing_references(skill_dir))

    if skill_file.is_file():
        scan_result = scan(skill_dir)
        for item in scan_result["issues"]:
            issues.append(
                finding(
                    f"safety.{item['reason']}",
                    item["detail"] or item["reason"],
                    severity=item["severity"],
                    skill=name,
                    path=item["path"],
                )
            )

    issues.sort(key=lambda item: (item["severity"] != "blocker", item["id"], item.get("path", "")))
    blockers = sum(item["severity"] == "blocker" for item in issues)
    return {
        "name": name,
        "status": "blocked" if blockers else "clear",
        "blocker_count": blockers,
        "warning_count": sum(item["severity"] == "warning" for item in issues),
        "findings": issues,
    }


def detect_capabilities(skill_dir: Path) -> set[str]:
    detected: set[str] = set()
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or path.suffix not in EXECUTABLE_SUFFIXES:
            continue
        if any(part in {".git", "node_modules", "__pycache__"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(pattern.search(text) for pattern in NETWORK_PATTERNS):
            detected.add("network")
        if any(pattern.search(text) for pattern in SUBPROCESS_PATTERNS):
            detected.add("subprocess")
        if any(pattern.search(text) for pattern in FILESYSTEM_WRITE_PATTERNS):
            detected.add("filesystem")
        if any(pattern.search(text) for pattern in CREDENTIAL_PATTERNS):
            detected.add("credentials")
    return detected


def validate_record_shape(record: Any, index: int) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not isinstance(record, dict):
        return [
            finding(
                "registry.record_type",
                f"Registry record {index} must be an object",
            )
        ]
    missing = sorted(REQUIRED_RECORD_FIELDS - set(record))
    if missing:
        issues.append(
            finding(
                "registry.required_fields",
                f"Registry record {index} is missing: {', '.join(missing)}",
                skill=record.get("name"),
            )
        )
    name = record.get("name")
    path = record.get("path")
    if isinstance(name, str) and path != f"skills/{name}":
        issues.append(
            finding(
                "registry.path",
                "Skill path must equal skills/<name>",
                skill=name,
                path=str(path),
            )
        )
    capabilities = record.get("capabilities")
    if not isinstance(capabilities, dict) or set(capabilities) != CAPABILITY_KEYS:
        issues.append(
            finding(
                "registry.capabilities",
                "Capabilities must declare network, subprocess, filesystem, and credentials",
                skill=name,
            )
        )
    harnesses = record.get("harnesses")
    if (
        not isinstance(harnesses, list)
        or not harnesses
        or not set(harnesses) <= ALLOWED_HARNESSES
    ):
        issues.append(
            finding(
                "registry.harnesses",
                "Harnesses must be a non-empty list of supported identifiers",
                skill=name,
            )
        )
    return issues


def load_registry(repo: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    registry_path = repo / "registry" / "skills.json"
    if not registry_path.is_file():
        return [], [finding("registry.missing", "Missing registry/skills.json")]
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [finding("registry.invalid_json", str(exc))]
    if not isinstance(payload, dict) or not isinstance(payload.get("skills"), list):
        return [], [finding("registry.skills", "Registry must contain a skills array")]
    records = payload["skills"]
    issues: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        issues.extend(validate_record_shape(record, index))
    for key in ("name", "path"):
        values = [
            record.get(key)
            for record in records
            if isinstance(record, dict) and record.get(key)
        ]
        duplicates = sorted({value for value in values if values.count(value) > 1})
        if duplicates:
            issues.append(
                finding(
                    f"registry.duplicate_{key}",
                    f"Duplicate {key}: {', '.join(duplicates)}",
                )
            )
    return records, issues


def audit_repo(repo: Path) -> dict[str, Any]:
    repo = repo.expanduser().resolve()
    findings: list[dict[str, Any]] = []
    if (repo / "SKILL.md").exists():
        findings.append(
            finding(
                "portfolio.root_skill",
                "Portfolio repositories must not expose a root-level SKILL.md",
                path="SKILL.md",
            )
        )

    records, registry_findings = load_registry(repo)
    findings.extend(registry_findings)
    audited: list[str] = []
    for record in records:
        if not isinstance(record, dict) or record.get("lifecycle") != "active":
            continue
        if REQUIRED_RECORD_FIELDS - set(record):
            continue
        name = record["name"]
        audited.append(name)
        skill_dir = (repo / record["path"]).resolve()
        if repo not in skill_dir.parents:
            findings.append(
                finding(
                    "registry.path_escape",
                    "Skill path escapes the Portfolio repository",
                    skill=name,
                    path=record["path"],
                )
            )
            continue
        validation = validate_skill(skill_dir)
        for item in validation["findings"]:
            item = dict(item)
            item.setdefault("skill", name)
            findings.append(item)

        for field in ("documentation", "documentation_zh", "changelog"):
            target = (repo / record[field]).resolve()
            if repo not in target.parents or not target.is_file():
                findings.append(
                    finding(
                        f"registry.{field}",
                        f"Registry {field} does not resolve to a repository file",
                        skill=name,
                        path=record[field],
                    )
                )

        declared = record["capabilities"]
        for capability in sorted(detect_capabilities(skill_dir)):
            value = declared.get(capability, "none")
            if value == "none":
                findings.append(
                    finding(
                        f"capability.{capability}_undeclared",
                        f"Executable files require undeclared {capability} capability",
                        skill=name,
                        path=record["path"],
                    )
                )

    findings.sort(
        key=lambda item: (
            item["severity"] != "blocker",
            item.get("skill", ""),
            item["id"],
            item.get("path", ""),
        )
    )
    blockers = sum(item["severity"] == "blocker" for item in findings)
    return {
        "status": "blocked" if blockers else "clear",
        "audited_skills": sorted(audited),
        "blocker_count": blockers,
        "warning_count": sum(item["severity"] == "warning" for item in findings),
        "findings": findings,
    }


def print_result(result: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"Status: {result['status']}")
    if "audited_skills" in result:
        print(f"Skills audited: {len(result['audited_skills'])}")
    elif "name" in result:
        print(f"Skill: {result['name']}")
    print(f"Blockers: {result['blocker_count']}")
    print(f"Warnings: {result['warning_count']}")
    for item in result["findings"]:
        skill = f" [{item['skill']}]" if item.get("skill") else ""
        path = f" ({item['path']})" if item.get("path") else ""
        print(f"- {item['severity']} {item['id']}{skill}{path}: {item['message']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate one public Skill or audit a Registry-driven Skill Portfolio."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate-skill")
    validate_parser.add_argument("skill")
    validate_parser.add_argument("--json", action="store_true")

    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("--repo", required=True)
    audit_parser.add_argument("--strict", action="store_true")
    audit_parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "validate-skill":
        result = validate_skill(Path(args.skill))
        print_result(result, as_json=args.json)
    else:
        result = audit_repo(Path(args.repo))
        print_result(result, as_json=args.json)
    return 2 if result["blocker_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
