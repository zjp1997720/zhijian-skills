from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release_portfolio.py"


class ReleaseSelectionTests(unittest.TestCase):
    def git(self, repo: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=repo, text=True, capture_output=True, check=True
        )
        return result.stdout.strip()

    def make_repo(self, repo: Path) -> None:
        records = []
        for name in ("demo-one", "demo-two"):
            (repo / "skills" / name).mkdir(parents=True)
            (repo / "docs" / "skills" / name).mkdir(parents=True)
            (repo / "docs" / "changelogs").mkdir(parents=True, exist_ok=True)
            (repo / "skills" / name / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Demo\n---\n", encoding="utf-8"
            )
            (repo / "docs" / "skills" / name / "README.md").write_text(
                f"# {name}\n", encoding="utf-8"
            )
            (repo / "docs" / "skills" / name / "README.zh-CN.md").write_text(
                f"# {name}\n", encoding="utf-8"
            )
            (repo / "docs" / "changelogs" / f"{name}.md").write_text(
                "# Changelog\n", encoding="utf-8"
            )
            records.append(
                {
                    "name": name,
                    "lifecycle": "active",
                    "version": "1.0.0",
                    "path": f"skills/{name}",
                    "documentation": f"docs/skills/{name}/README.md",
                    "documentation_zh": f"docs/skills/{name}/README.zh-CN.md",
                    "changelog": f"docs/changelogs/{name}.md",
                    "canonical_tag": f"{name}/v1.0.0",
                    "validation": {"commands": [], "live_smoke": None},
                }
            )
        (repo / "registry").mkdir()
        (repo / "registry" / "skills.json").write_text(
            json.dumps({"schema_version": "1.0.0", "skills": records}),
            encoding="utf-8",
        )
        (repo / "registry" / "skills.schema.json").write_text("{}\n", encoding="utf-8")
        (repo / "package-lock.json").write_text(
            json.dumps({"packages": {"node_modules/skills": {"version": "1.5.18"}}}),
            encoding="utf-8",
        )
        self.git(repo, "init", "-b", "main")
        self.git(repo, "config", "user.name", "Test")
        self.git(repo, "config", "user.email", "test@example.com")
        self.git(repo, "add", ".")
        self.git(repo, "commit", "-m", "baseline")
        remote = repo.parent / "remote.git"
        subprocess.run(
            ["git", "init", "--bare", str(remote)],
            text=True,
            capture_output=True,
            check=True,
        )
        self.git(repo, "remote", "add", "origin", str(remote))
        self.git(repo, "push", "-u", "origin", "main")

    def run_plan(self, repo: Path, plan_path: Path, *selector: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "plan",
                "--repo",
                str(repo),
                "--source-checkout",
                str(repo),
                *selector,
                "--dry-run",
                "--plan-out",
                str(plan_path),
            ],
            text=True,
            capture_output=True,
            check=False,
            env=dict(os.environ, ZHIJIAN_ALLOW_TEST_REMOTE="1"),
        )

    def test_skill_selector_plans_only_the_named_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self.make_repo(repo)
            plan_path = Path(tmp) / "plan.json"
            result = self.run_plan(repo, plan_path, "--skill", "demo-two")
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertEqual([release["skill"] for release in plan["releases"]], ["demo-two"])

    def test_unknown_skill_fails_before_candidate_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self.make_repo(repo)
            plan_path = Path(tmp) / "plan.json"
            result = self.run_plan(repo, plan_path, "--skill", "missing")
            self.assertEqual(result.returncode, 2)
            self.assertIn("plan.skill_unknown: missing", result.stderr)
            self.assertFalse(plan_path.exists())
            refs = self.git(repo, "for-each-ref", "--format=%(refname)", "refs/zhijian-candidates")
            self.assertEqual(refs, "")

    def test_all_and_skill_are_mutually_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self.make_repo(repo)
            plan_path = Path(tmp) / "plan.json"
            result = self.run_plan(repo, plan_path, "--all", "--skill", "demo-one")
            self.assertEqual(result.returncode, 2)
            self.assertIn("not allowed with argument", result.stderr)

    def test_skill_rejects_exclude(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self.make_repo(repo)
            plan_path = Path(tmp) / "plan.json"
            result = self.run_plan(
                repo,
                plan_path,
                "--skill",
                "demo-one",
                "--exclude",
                "demo-two",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("plan.selector_conflict", result.stderr)

    def test_governed_skill_rejects_existing_but_untracked_baselines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self.make_repo(repo)
            skill = repo / "skills" / "demo-one"
            (repo / ".gitignore").write_text("reports/\n", encoding="utf-8")
            (skill / "manifest.json").write_text(
                json.dumps(
                    {
                        "maturity_tier": "governed",
                        "lifecycle_stage": "governed",
                        "trust_report": "reports/trust-report.md",
                        "output_quality_scorecard": "reports/output_quality_scorecard.md",
                    }
                ),
                encoding="utf-8",
            )
            self.git(repo, "add", ".gitignore", "skills/demo-one/manifest.json")
            self.git(repo, "commit", "-m", "declare ignored baselines")
            self.git(repo, "push", "origin", "main")
            reports = skill / "reports"
            reports.mkdir()
            (reports / "trust-report.md").write_text("trusted\n", encoding="utf-8")
            (reports / "output_quality_scorecard.md").write_text("passed\n", encoding="utf-8")

            plan_path = Path(tmp) / "plan.json"
            result = self.run_plan(repo, plan_path, "--skill", "demo-one")

            self.assertEqual(result.returncode, 2)
            self.assertIn("plan.baseline_untracked", result.stderr)
            self.assertIn("reports/trust-report.md", result.stderr)
            self.assertFalse(plan_path.exists())
            refs = self.git(
                repo,
                "for-each-ref",
                "--format=%(refname)",
                "refs/zhijian-candidates",
            )
            self.assertEqual(refs, "")

    def test_governed_skill_freezes_tracked_baseline_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self.make_repo(repo)
            skill = repo / "skills" / "demo-one"
            (skill / "security").mkdir()
            (skill / "references").mkdir()
            (skill / "security" / "trust-baseline.md").write_text("trusted\n", encoding="utf-8")
            (skill / "references" / "output-eval-baseline.md").write_text(
                "passed\n", encoding="utf-8"
            )
            (skill / "manifest.json").write_text(
                json.dumps(
                    {
                        "maturity_tier": "governed",
                        "lifecycle_stage": "governed",
                        "trust_report": "security/trust-baseline.md",
                        "output_quality_scorecard": "references/output-eval-baseline.md",
                    }
                ),
                encoding="utf-8",
            )
            self.git(repo, "add", "skills/demo-one")
            self.git(repo, "commit", "-m", "track governed baselines")
            self.git(repo, "push", "origin", "main")

            plan_path = Path(tmp) / "plan.json"
            result = self.run_plan(repo, plan_path, "--skill", "demo-one")

            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            baselines = plan["releases"][0]["governance_baselines"]
            self.assertEqual(
                baselines["trust_report"]["path"],
                "skills/demo-one/security/trust-baseline.md",
            )
            self.assertEqual(len(baselines["trust_report"]["sha256"]), 64)
            self.assertEqual(
                baselines["output_quality_scorecard"]["path"],
                "skills/demo-one/references/output-eval-baseline.md",
            )

    def test_governed_skill_requires_both_baseline_declarations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self.make_repo(repo)
            skill = repo / "skills" / "demo-one"
            (skill / "manifest.json").write_text(
                json.dumps(
                    {
                        "maturity_tier": "governed",
                        "lifecycle_stage": "governed",
                    }
                ),
                encoding="utf-8",
            )
            self.git(repo, "add", "skills/demo-one/manifest.json")
            self.git(repo, "commit", "-m", "declare governed skill")
            self.git(repo, "push", "origin", "main")

            result = self.run_plan(repo, Path(tmp) / "plan.json", "--skill", "demo-one")

            self.assertEqual(result.returncode, 2)
            self.assertIn("plan.baseline_undeclared", result.stderr)
            self.assertIn("manifest.trust_report", result.stderr)


if __name__ == "__main__":
    unittest.main()
