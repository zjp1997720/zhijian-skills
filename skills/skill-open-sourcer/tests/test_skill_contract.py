from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_readme_audit_uses_explicit_portfolio_boundary(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        design = (ROOT / "references" / "readme-design.md").read_text(encoding="utf-8")
        self.assertIn("--repository-root <zhijian-skills>", skill)
        self.assertIn("--repository-root <zhijian-skills>", design)

    def test_cli_help_probe_cannot_be_mistaken_for_install(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        package = (ROOT / "references" / "release-package.md").read_text(encoding="utf-8")
        for text in (skill, package):
            self.assertIn("npx --no-install skills --help", text)
            self.assertIn("npx skills add <source> --help", text)
            self.assertIn("may perform a real installation", text)


if __name__ == "__main__":
    unittest.main()
