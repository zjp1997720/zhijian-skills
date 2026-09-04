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

    def test_single_skill_release_selector_is_the_documented_default(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "release-contract.md").read_text(encoding="utf-8")
        for text in (skill, contract):
            self.assertIn("--skill <name>", text)
            self.assertIn("mutually exclusive", text)
            self.assertIn("--exclude", text)

    def test_isolated_install_uses_one_fail_fast_verifier(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        package = (ROOT / "references" / "release-package.md").read_text(encoding="utf-8")
        for text in (skill, package):
            self.assertIn("scripts/verify_isolated_install.py", text)
            self.assertIn("--install-source", text)
            self.assertIn("returns non-zero", text)

    def test_release_contract_blocks_stale_source_checkouts(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "release-contract.md").read_text(
            encoding="utf-8"
        )
        guard = (ROOT / "scripts" / "git_sync_guard.py").read_text(encoding="utf-8")
        for text in (skill, contract):
            self.assertIn("--source-checkout", text)
            self.assertIn("needs-sync", text)
            self.assertIn("short-lived branch", text)
            self.assertIn("PR", text)
        self.assertIn("base_remote_sha", guard)
        self.assertIn("ls-remote", guard)
        self.assertIn("pre-commit", guard)

    def test_release_plan_requires_committed_governance_baselines(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "release-contract.md").read_text(
            encoding="utf-8"
        )
        for text in (skill, contract):
            self.assertIn("trust_report", text)
            self.assertIn("output_quality_scorecard", text)
            self.assertIn("tracked at `HEAD`", text)


if __name__ == "__main__":
    unittest.main()
