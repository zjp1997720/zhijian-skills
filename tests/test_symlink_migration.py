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
                persisted = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
                self.assertEqual(persisted["state"], "complete")
                self.assertIsNone(persisted["in_progress"])
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

    def test_unsupported_harness_copy_is_backed_up_and_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            root = base / "claude"
            self.make_repo(repo)
            (root / "demo").mkdir(parents=True)
            (root / "demo/SKILL.md").write_text("demo\n", encoding="utf-8")
            with patch.dict(os.environ, {"XDG_STATE_HOME": str(base / "state")}):
                plan = plan_links(repo, [("claude-code", root)])
                self.assertEqual(plan["actions"][0]["status"], "remove-unsupported")
                result = apply_links(plan, accept_differences=False)
                self.assertFalse((root / "demo").exists())
                self.assertTrue(Path(result["completed"][0]["backup"]).is_dir())

    def test_failed_link_is_rolled_back_and_journaled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            root = base / "codex"
            self.make_repo(repo)
            (root / "demo").mkdir(parents=True)
            (root / "demo/SKILL.md").write_text("demo\n", encoding="utf-8")
            with patch.dict(os.environ, {"XDG_STATE_HOME": str(base / "state")}):
                plan = plan_links(repo, [("codex", root)])
                with patch.object(Path, "symlink_to", side_effect=OSError("simulated crash")):
                    with self.assertRaisesRegex(OSError, "simulated crash"):
                        apply_links(plan, accept_differences=False)
                self.assertFalse((root / "demo").is_symlink())
                self.assertEqual(
                    (root / "demo/SKILL.md").read_text(encoding="utf-8"), "demo\n"
                )
                manifests = list((base / "state/zhijian-skills/link-backups").glob("*/manifest.json"))
                self.assertEqual(len(manifests), 1)
                payload = json.loads(manifests[0].read_text(encoding="utf-8"))
                self.assertEqual(payload["state"], "rolled-back")
                self.assertIsNone(payload["in_progress"])

    def test_rollback_refuses_to_delete_user_content_created_after_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / "repo"
            root = base / "codex"
            self.make_repo(repo)
            with patch.dict(os.environ, {"XDG_STATE_HOME": str(base / "state")}):
                result = apply_links(
                    plan_links(repo, [("codex", root)]), accept_differences=False
                )
                entry = root / "demo"
                entry.unlink()
                entry.mkdir()
                (entry / "user-file.md").write_text("keep me\n", encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "link.rollback_conflict"):
                    rollback_manifest(Path(result["manifest"]))
                self.assertEqual(
                    (entry / "user-file.md").read_text(encoding="utf-8"), "keep me\n"
                )

    def test_rollback_rejects_manifest_outside_managed_backup_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            manifest = base / "untrusted.json"
            manifest.write_text(
                json.dumps({"manifest": str(manifest), "completed": []}),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"XDG_STATE_HOME": str(base / "state")}):
                with self.assertRaisesRegex(RuntimeError, "link.rollback_manifest_unsafe"):
                    rollback_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
