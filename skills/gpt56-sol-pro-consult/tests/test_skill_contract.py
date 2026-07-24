#!/usr/bin/env python3

from __future__ import annotations

import json
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_chrome_is_default_and_opencli_is_optional(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Use the Codex Chrome plugin by default", skill)
        self.assertIn("OpenCLI is optional and is not an installation prerequisite", skill)
        self.assertNotIn("For text-only consultations, default to the wrapper", skill)

    def test_required_public_files_exist(self) -> None:
        for relative in (
            "agents/openai.yaml",
            "references/chrome-workflow.md",
            "references/opencli-fallback.md",
            "references/context-packet-template.md",
        ):
            self.assertTrue((SKILL_DIR / relative).is_file(), relative)

    def test_no_personal_absolute_paths(self) -> None:
        for path in SKILL_DIR.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                text = path.read_text(encoding="utf-8", errors="ignore")
                for forbidden in ("/Users/" + "me/", "zhu" + "jinpeng", "deepsight_" + "vault"):
                    self.assertNotIn(forbidden, text, str(path))

    def test_evals_route_normal_requests_to_chrome(self) -> None:
        payload = json.loads((SKILL_DIR / "evals/evals.json").read_text(encoding="utf-8"))
        for case in payload["evals"]:
            self.assertIn("Chrome", case["expected_output"])


if __name__ == "__main__":
    unittest.main()
