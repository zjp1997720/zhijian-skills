from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills/skill-open-sourcer/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from manage_local_links import apply_links, plan_links, rollback_manifest  # noqa: E402


class SymlinkMigrationTests(unittest.TestCase):
    def make_repo(self, root: Path) -> None:
        (root / "skills/demo").mkdir(parents=True)
        (root / "skills/demo/SKILL.md").write_text("demo\n", encoding="utf-8")
        (root / "registry").mkdir()
        (root / "registry/skills.json").write_text(
            json.dumps(
                {
                    "skills": [
                        {
                            "name": "demo",
                            "lifecycle": "active",
                            "path": "skills/demo",
                            "harnesses": ["codex"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def test_identical_copy_is_backed_up_linked_and_rollbackable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            root = base / "codex"
            self.make_repo(repo)
            (root / "demo").mkdir(parents=True)
            (root / "demo/SKILL.md").write_text("demo\n", encoding="utf-8")
            with patch.dict(os.environ, {"XDG_STATE_HOME": str(base / "state")}):
                plan = plan_links(repo, [("codex", root)])
                self.assertFalse(plan["actions"][0]["different"])
                result = apply_links(plan, accept_differences=False)
                entry = root / "demo"
                self.assertTrue(entry.is_symlink())
                self.assertEqual(entry.resolve(), (repo / "skills/demo").resolve())
                rollback_manifest(Path(result["manifest"]))
                self.assertFalse(entry.is_symlink())
                self.assertEqual((entry / "SKILL.md").read_text(encoding="utf-8"), "demo\n")

    def test_different_copy_blocks_without_explicit_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            root = base / "codex"
            self.make_repo(repo)
            (root / "demo").mkdir(parents=True)
            (root / "demo/SKILL.md").write_text("local change\n", encoding="utf-8")
            plan = plan_links(repo, [("codex", root)])
            self.assertTrue(plan["actions"][0]["different"])
            with self.assertRaisesRegex(RuntimeError, "link.differences"):
                apply_links(plan, accept_differences=False)
            self.assertFalse((root / "demo").is_symlink())

    def test_correct_symlink_is_healthy_and_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            root = base / "codex"
            self.make_repo(repo)
            root.mkdir()
            (root / "demo").symlink_to(repo / "skills/demo", target_is_directory=True)
            plan = plan_links(repo, [("codex", root)])
            self.assertEqual(plan["actions"][0]["status"], "healthy")


if __name__ == "__main__":
    unittest.main()
