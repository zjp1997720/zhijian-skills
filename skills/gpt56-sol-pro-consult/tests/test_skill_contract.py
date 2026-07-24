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

    def test_chrome_workflow_has_atomic_upload_and_verified_composer_recovery(self) -> None:
        workflow = (SKILL_DIR / "references/chrome-workflow.md").read_text(encoding="utf-8")
        for required in (
            "one `node_repl js` invocation",
            'waitForEvent("filechooser")',
            "chooser.setFiles",
            "innerText()",
            "在文本字段中显示",
            "Show in text field",
            "Never click Send with an empty or unverified packet",
        ):
            self.assertIn(required, workflow)

    def test_chrome_workflow_blocks_duplicate_send_after_ambiguous_reset(self) -> None:
        workflow = (SKILL_DIR / "references/chrome-workflow.md").read_text(encoding="utf-8")
        for state in ("NOT_SENT", "SENT", "UNKNOWN"):
            self.assertIn(f"`{state}`", workflow)
        self.assertIn("Never create a fresh consultation or click Send again", workflow)
        self.assertIn("mark the consultation incomplete instead of risking a duplicate", workflow)


if __name__ == "__main__":
    unittest.main()
