from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/skill-open-sourcer/scripts/release_portfolio.py"


class ReleasePlanTests(unittest.TestCase):
    def git(self, repo: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=repo, text=True, capture_output=True, check=True
        )
        return result.stdout.strip()

    def make_repo(self, root: Path) -> None:
        (root / "skills/demo").mkdir(parents=True)
        (root / "docs/skills/demo").mkdir(parents=True)
        (root / "docs/changelogs").mkdir(parents=True)
        (root / "registry").mkdir(parents=True)
        (root / "skills/demo/SKILL.md").write_text(
            "---\nname: demo\ndescription: Demo\n---\n", encoding="utf-8"
        )
        (root / "docs/skills/demo/README.md").write_text("# Demo\n", encoding="utf-8")
        (root / "docs/skills/demo/README.zh-CN.md").write_text("# 演示\n", encoding="utf-8")
        (root / "docs/changelogs/demo.md").write_text("# Changelog\n", encoding="utf-8")
        (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
        (root / "CONTRIBUTING.md").write_text("Contribute\n", encoding="utf-8")
        registry = {
            "schema_version": "1.0.0",
            "skills": [
                {
                    "name": "demo",
                    "lifecycle": "active",
                    "version": "1.0.0",
                    "path": "skills/demo",
                    "mirror": "owner/demo",
                    "documentation": "docs/skills/demo/README.md",
                    "documentation_zh": "docs/skills/demo/README.zh-CN.md",
                    "changelog": "docs/changelogs/demo.md",
                    "canonical_tag": "demo/v1.0.0",
                    "mirror_tag": "v1.0.0",
                    "validation": {"commands": [], "live_smoke": None},
                    "capabilities": {
                        "network": "none",
                        "subprocess": "none",
                        "filesystem": "read",
                        "credentials": "none",
                    },
                    "harnesses": ["codex"],
                }
            ],
        }
        (root / "registry/skills.json").write_text(
            json.dumps(registry), encoding="utf-8"
        )
        (root / "registry/skills.schema.json").write_text("{}\n", encoding="utf-8")
        (root / "package-lock.json").write_text(
            json.dumps({"packages": {"node_modules/skills": {"version": "1.5.18"}}}),
            encoding="utf-8",
        )
        self.git(root, "init", "-b", "main")
        self.git(root, "config", "user.name", "Test")
        self.git(root, "config", "user.email", "test@example.com")
        self.git(root, "add", ".")
        self.git(root, "commit", "-m", "baseline")

    def plan(self, repo: Path, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "plan",
                "--repo",
                str(repo),
                "--all",
                "--dry-run",
                "--plan-out",
                str(path),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_plan_is_deterministic_and_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self.make_repo(repo)
            first_path = Path(tmp) / "first.json"
            second_path = Path(tmp) / "second.json"
            first = self.plan(repo, first_path)
            second = self.plan(repo, second_path)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            first_data = json.loads(first_path.read_text(encoding="utf-8"))
            second_data = json.loads(second_path.read_text(encoding="utf-8"))
            self.assertEqual(first_data, second_data)
            self.assertEqual(first_data["releases"][0]["semver_reason"], "initial_baseline")
            self.assertTrue(first_data["releases"][0]["candidate_ref"].startswith("refs/zhijian-candidates/"))

            (repo / "skills/demo/SKILL.md").write_text("changed\n", encoding="utf-8")
            verify = subprocess.run(
                [sys.executable, str(SCRIPT), "verify", "--plan", str(first_path)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(verify.returncode, 2)
            self.assertIn("plan.stale", verify.stderr)

    def test_ledger_updates_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self.make_repo(repo)
            plan_path = Path(tmp) / "plan.json"
            self.assertEqual(self.plan(repo, plan_path).returncode, 0)
            env = dict(os.environ, XDG_STATE_HOME=str(Path(tmp) / "state"))
            command = [
                sys.executable,
                str(SCRIPT),
                "record-step",
                "--plan",
                str(plan_path),
                "--skill",
                "demo",
                "--step",
                "mirror-pushed",
            ]
            first = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
            second = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(json.loads(first.stdout), json.loads(second.stdout))


if __name__ == "__main__":
    unittest.main()
