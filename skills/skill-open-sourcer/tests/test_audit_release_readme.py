from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_release_readme.py"


class AuditReleaseReadmeTests(unittest.TestCase):
    def run_audit(self, root: Path, strict: bool = True) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPT), str(root)]
        if strict:
            command.append("--strict")
        return subprocess.run(command, text=True, capture_output=True, check=False)

    def write_valid_release(self, root: Path) -> None:
        assets = root / "assets" / "readme"
        assets.mkdir(parents=True)
        (assets / "hero.svg").write_text(
            """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 320" role="img" aria-labelledby="title desc" data-composition="input-to-output">
<title>Demo Skill</title><desc>A concrete demo workflow</desc>
<rect width="1200" height="320" fill="#111"/>
</svg>
""",
            encoding="utf-8",
        )
        (root / "README.md").write_text(
            """# Demo Skill

Turn one local input into a verified public result.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Agent Install

`npx skills add owner/demo-skill`

<p align="center"><img src="./assets/readme/hero.svg" width="100%" alt="Demo Skill workflow"></p>

## License

MIT
""",
            encoding="utf-8",
        )
        (root / "README.zh-CN.md").write_text(
            """# Demo Skill

把一个本地输入转换为经过验证的公开结果。

## Agent 安装

`npx skills add owner/demo-skill`

## 许可证

MIT
""",
            encoding="utf-8",
        )
        (root / "LICENSE").write_text("MIT\n", encoding="utf-8")

    def test_valid_release_passes_strict_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_valid_release(root)
            result = self.run_audit(root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("README files audited: 2", result.stdout)

    def test_missing_install_and_image_alt_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "# Broken Skill\n\n## Details\n\n<img src=\"./missing.svg\">\n",
                encoding="utf-8",
            )
            result = self.run_audit(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("npx skills add", result.stdout)
            self.assertIn("empty or missing alt", result.stdout)
            self.assertIn("missing local image", result.stdout)

    def test_unsafe_svg_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_valid_release(root)
            svg = root / "assets" / "readme" / "hero.svg"
            svg.write_text(
                """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 320" role="img" aria-labelledby="title desc" data-composition="input-to-output">
<title>Demo</title><desc>A concrete demo workflow</desc><script>alert(1)</script>
</svg>
""",
                encoding="utf-8",
            )
            result = self.run_audit(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("unsupported <script>", result.stdout)

    def test_generic_alt_and_missing_composition_fail_strict_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_valid_release(root)
            readme = root / "README.md"
            readme.write_text(readme.read_text(encoding="utf-8").replace("Demo Skill workflow", "hero"), encoding="utf-8")
            svg = root / "assets" / "readme" / "hero.svg"
            svg.write_text(svg.read_text(encoding="utf-8").replace(' data-composition="input-to-output"', ""), encoding="utf-8")
            result = self.run_audit(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("alt text is too generic", result.stdout)
            self.assertIn("missing a stable data-composition", result.stdout)

    def test_root_skill_with_support_files_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_valid_release(root)
            (root / "SKILL.md").write_text(
                "# Demo\n\nRead [policy](references/policy.md).\n",
                encoding="utf-8",
            )
            references = root / "references"
            references.mkdir()
            (references / "policy.md").write_text("# Policy\n", encoding="utf-8")
            result = self.run_audit(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("root-level remote npx installs copy only SKILL.md", result.stdout)

    def test_nested_skill_with_support_files_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_valid_release(root)
            skill_root = root / "skills" / "demo-skill"
            references = skill_root / "references"
            references.mkdir(parents=True)
            (skill_root / "SKILL.md").write_text(
                "# Demo\n\nRead [policy](references/policy.md).\n",
                encoding="utf-8",
            )
            (references / "policy.md").write_text("# Policy\n", encoding="utf-8")
            result = self.run_audit(root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
