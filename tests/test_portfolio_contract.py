from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "registry" / "skills.json"
EXPECTED_SKILLS = {
    "codex-doctor",
    "codex-model-routing-team",
    "codex-skill-admin",
    "enterprise-clone-builder",
    "html-express",
    "skill-open-sourcer",
    "wechat-article-search",
    "wechat-styler",
}
CAPABILITY_KEYS = {"network", "subprocess", "filesystem", "credentials"}
ALLOWED_CAPABILITY_VALUES = {"none", "read", "write", "required"}
ALLOWED_HARNESSES = {"codex", "claude-code", "agents"}


class PortfolioContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        cls.records = cls.registry["skills"]

    def test_registry_has_exact_first_wave(self) -> None:
        self.assertEqual(EXPECTED_SKILLS, {record["name"] for record in self.records})

    def test_identity_and_paths_are_unique(self) -> None:
        for key in ("name", "path", "mirror"):
            values = [record[key] for record in self.records]
            self.assertEqual(len(values), len(set(values)), key)

    def test_every_record_resolves_to_complete_repository_paths(self) -> None:
        for record in self.records:
            with self.subTest(skill=record["name"]):
                skill_dir = ROOT / record["path"]
                self.assertEqual(ROOT / "skills" / record["name"], skill_dir)
                self.assertTrue((skill_dir / "SKILL.md").is_file())
                self.assertTrue((ROOT / record["documentation"]).is_file())
                self.assertTrue((ROOT / record["documentation_zh"]).is_file())
                self.assertTrue((ROOT / record["changelog"]).is_file())

    def test_versions_and_tags_are_independent(self) -> None:
        for record in self.records:
            with self.subTest(skill=record["name"]):
                self.assertEqual("1.0.0", record["version"])
                self.assertEqual(f"{record['name']}/v1.0.0", record["canonical_tag"])
                self.assertEqual("v1.0.0", record["mirror_tag"])

    def test_capability_and_harness_contract(self) -> None:
        for record in self.records:
            with self.subTest(skill=record["name"]):
                self.assertEqual(CAPABILITY_KEYS, set(record["capabilities"]))
                self.assertTrue(
                    set(record["capabilities"].values())
                    <= ALLOWED_CAPABILITY_VALUES
                )
                self.assertTrue(record["harnesses"])
                self.assertTrue(set(record["harnesses"]) <= ALLOWED_HARNESSES)

    def test_root_has_no_installable_skill(self) -> None:
        self.assertFalse((ROOT / "SKILL.md").exists())

    def test_schema_declares_registry_contract(self) -> None:
        schema = json.loads(
            (ROOT / "registry" / "skills.schema.json").read_text(encoding="utf-8")
        )
        required = set(
            schema["properties"]["skills"]["items"]["required"]
        )
        self.assertTrue(
            {
                "name",
                "version",
                "path",
                "mirror",
                "documentation",
                "changelog",
                "validation",
                "capabilities",
                "harnesses",
            }
            <= required
        )


if __name__ == "__main__":
    unittest.main()
