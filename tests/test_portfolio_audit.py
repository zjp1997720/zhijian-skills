from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "skill-open-sourcer" / "scripts" / "portfolio.py"


class PortfolioAuditTest(unittest.TestCase):
    def run_tool(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def write_skill(
        self,
        root: Path,
        *,
        name: str = "demo-skill",
        body: str = "# Demo\n",
    ) -> Path:
        skill = root / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Demo skill used by tests.\n---\n\n{body}",
            encoding="utf-8",
        )
        return skill

    def write_repo(
        self,
        root: Path,
        *,
        body: str = "# Demo\n",
        capabilities: dict[str, str] | None = None,
        retired: bool = False,
    ) -> Path:
        skill = self.write_skill(root, body=body)
        docs = root / "docs" / "skills" / "demo-skill"
        docs.mkdir(parents=True)
        (docs / "README.md").write_text("# Demo\n", encoding="utf-8")
        (docs / "README.zh-CN.md").write_text("# Demo\n", encoding="utf-8")
        changelogs = root / "docs" / "changelogs"
        changelogs.mkdir(parents=True)
        (changelogs / "demo-skill.md").write_text("# Changelog\n", encoding="utf-8")
        registry = root / "registry"
        registry.mkdir()
        record = {
            "name": "demo-skill",
            "lifecycle": "retired" if retired else "active",
            "version": "1.0.0",
            "path": "skills/demo-skill",
            "mirror": "owner/demo-skill",
            "documentation": "docs/skills/demo-skill/README.md",
            "documentation_zh": "docs/skills/demo-skill/README.zh-CN.md",
            "changelog": "docs/changelogs/demo-skill.md",
            "canonical_tag": "demo-skill/v1.0.0",
            "mirror_tag": "v1.0.0",
            "validation": {"commands": [], "live_smoke": None},
            "capabilities": capabilities
            or {
                "network": "none",
                "subprocess": "none",
                "filesystem": "none",
                "credentials": "none",
            },
            "harnesses": ["codex"],
        }
        (registry / "skills.json").write_text(
            json.dumps({"schema_version": "1.0.0", "skills": [record]}),
            encoding="utf-8",
        )
        return skill

    def test_validate_skill_preserves_single_skill_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = self.write_skill(Path(tmp))
            result = self.run_tool("validate-skill", str(skill), "--json")
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("clear", payload["status"])
            self.assertEqual("demo-skill", payload["name"])

    def test_valid_portfolio_audits_active_and_ignores_retired(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_repo(root)
            retired = self.write_skill(root, name="retired-skill")
            self.assertTrue(retired.exists())
            result = self.run_tool("audit", "--repo", str(root), "--strict", "--json")
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(["demo-skill"], payload["audited_skills"])

    def test_root_level_skill_blocks_portfolio_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_repo(root)
            (root / "SKILL.md").write_text("# Wrong root\n", encoding="utf-8")
            result = self.run_tool("audit", "--repo", str(root), "--strict", "--json")
            self.assertEqual(2, result.returncode)
            self.assertIn("portfolio.root_skill", result.stdout)

    def test_missing_markdown_reference_blocks_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = self.write_skill(
                root,
                body="Read [the policy](references/missing.md).\n",
            )
            result = self.run_tool("validate-skill", str(skill), "--json")
            self.assertEqual(2, result.returncode)
            self.assertIn("skill.missing_reference", result.stdout)

    def test_private_absolute_path_blocks_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = self.write_skill(root, body="Use /Users/example/private/file.md.\n")
            result = self.run_tool("validate-skill", str(skill), "--json")
            self.assertEqual(2, result.returncode)
            self.assertIn("private_path", result.stdout)

    def test_generated_python_cache_does_not_block_local_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = self.write_repo(root)
            cache = skill / "scripts" / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "worker.cpython-314.pyc").write_bytes(b"generated")
            result = self.run_tool("audit", "--repo", str(root), "--strict", "--json")
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertNotIn("suspicious_directory", result.stdout)

    def test_undeclared_executable_capability_blocks_portfolio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = self.write_repo(root)
            scripts = skill / "scripts"
            scripts.mkdir()
            (scripts / "fetch.py").write_text(
                "from urllib.request import urlopen\nurlopen('https://example.com')\n",
                encoding="utf-8",
            )
            result = self.run_tool("audit", "--repo", str(root), "--strict", "--json")
            self.assertEqual(2, result.returncode)
            self.assertIn("capability.network_undeclared", result.stdout)

    def test_malformed_registry_blocks_entire_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "registry"
            registry.mkdir()
            fixture = (
                ROOT
                / "tests"
                / "fixtures"
                / "portfolio"
                / "malformed-registry.json"
            )
            (registry / "skills.json").write_text(
                fixture.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            result = self.run_tool("audit", "--repo", str(root), "--strict", "--json")
            self.assertEqual(2, result.returncode)
            self.assertIn("registry.", result.stdout)


if __name__ == "__main__":
    unittest.main()
