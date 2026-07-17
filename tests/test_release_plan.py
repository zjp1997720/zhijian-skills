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
            release = first_data["releases"][0]
            self.assertNotEqual(release["candidate_commit"], first_data["base_commit"])
            self.assertEqual(
                self.git(repo, "rev-parse", f"{release['candidate_commit']}^1"),
                first_data["base_commit"],
            )
            self.assertEqual(
                self.git(repo, "rev-parse", f"{release['candidate_commit']}^{{tree}}"),
                self.git(repo, "rev-parse", f"{first_data['base_commit']}^{{tree}}"),
            )
            self.assertRegex(release["mirror_export_digest"], r"^[0-9a-f]{64}$")

            (repo / "skills/demo/SKILL.md").write_text("changed\n", encoding="utf-8")
            verify = subprocess.run(
                [sys.executable, str(SCRIPT), "verify", "--plan", str(first_path)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(verify.returncode, 2)
            self.assertIn("plan.stale", verify.stderr)

    def test_each_skill_gets_a_distinct_detached_candidate_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self.make_repo(repo)
            registry_path = repo / "registry/skills.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            second = json.loads(json.dumps(registry["skills"][0]))
            replacements = {
                "name": "demo-two",
                "path": "skills/demo-two",
                "mirror": "owner/demo-two",
                "documentation": "docs/skills/demo-two/README.md",
                "documentation_zh": "docs/skills/demo-two/README.zh-CN.md",
                "changelog": "docs/changelogs/demo-two.md",
                "canonical_tag": "demo-two/v1.0.0",
            }
            second.update(replacements)
            registry["skills"].append(second)
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            (repo / "skills/demo-two").mkdir()
            (repo / "skills/demo-two/SKILL.md").write_text(
                "---\nname: demo-two\ndescription: Demo two\n---\n", encoding="utf-8"
            )
            (repo / "docs/skills/demo-two").mkdir()
            (repo / "docs/skills/demo-two/README.md").write_text("# Demo two\n", encoding="utf-8")
            (repo / "docs/skills/demo-two/README.zh-CN.md").write_text("# 演示二\n", encoding="utf-8")
            (repo / "docs/changelogs/demo-two.md").write_text("# Changelog\n", encoding="utf-8")
            self.git(repo, "add", ".")
            self.git(repo, "commit", "-m", "add second skill")
            plan_path = Path(tmp) / "plan.json"
            self.assertEqual(self.plan(repo, plan_path).returncode, 0)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            candidates = {release["candidate_commit"] for release in plan["releases"]}
            self.assertEqual(len(candidates), 2)
            self.assertNotIn(plan["base_commit"], candidates)

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

    def test_cleanup_deletes_only_the_planned_candidate_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self.make_repo(repo)
            plan_path = Path(tmp) / "plan.json"
            self.assertEqual(self.plan(repo, plan_path).returncode, 0)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            reference = plan["releases"][0]["candidate_ref"]
            cleanup = subprocess.run(
                [sys.executable, str(SCRIPT), "cleanup", "--plan", str(plan_path)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cleanup.returncode, 0, cleanup.stderr)
            self.assertIn(reference, json.loads(cleanup.stdout)["removed"])
            self.assertNotEqual(
                subprocess.run(
                    ["git", "rev-parse", "--verify", reference],
                    cwd=repo,
                    capture_output=True,
                    check=False,
                ).returncode,
                0,
            )

    def test_cleanup_rejects_refs_outside_candidate_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self.make_repo(repo)
            plan_path = Path(tmp) / "plan.json"
            self.assertEqual(self.plan(repo, plan_path).returncode, 0)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["releases"][0]["candidate_ref"] = "refs/heads/main"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            cleanup = subprocess.run(
                [sys.executable, str(SCRIPT), "cleanup", "--plan", str(plan_path)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cleanup.returncode, 2)
            self.assertIn("cleanup.ref_unsafe", cleanup.stderr)
            self.assertEqual(self.git(repo, "rev-parse", "refs/heads/main"), self.git(repo, "rev-parse", "HEAD"))


if __name__ == "__main__":
    unittest.main()
