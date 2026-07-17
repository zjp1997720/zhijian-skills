from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = ROOT / "skills/codex-model-routing-team"
CONTRACT = Path(__file__).with_name("codex-model-routing-team-expected.json")


class SkillContractTests(unittest.TestCase):
    def test_worker_budget_fits_total_cap(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        budget = contract["deep_research_budget"]
        self.assertLessEqual(sum(budget.values()), contract["max_total_workers"])

    def test_skill_preserves_routing_and_fallback_contract(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        package = "\n".join(
            path.read_text(encoding="utf-8") for path in sorted(SKILL_ROOT.rglob("*.md"))
        )
        for model in contract["default_models"]:
            self.assertIn(model, package)
        self.assertIn("spawn_agent", package)
        self.assertIn("禁止", package)
        self.assertIn("projectless", package)
        self.assertIn("reserved slots", package)

    def test_adapter_keeps_verifier_before_reviewer(self) -> None:
        adapter = (SKILL_ROOT / "references/upstream-skill-adapter.md").read_text(encoding="utf-8")
        self.assertLess(adapter.index("verifier：1 个"), adapter.index("reviewer：1 个"))
        self.assertIn("每次 `create_thread` 成功后", adapter)


if __name__ == "__main__":
    unittest.main()
