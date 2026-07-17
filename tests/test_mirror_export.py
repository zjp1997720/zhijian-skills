from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/skill-open-sourcer/scripts/export_mirror.py"


class MirrorExportTests(unittest.TestCase):
    def make_repo(self, root: Path) -> None:
        (root / "skills/demo/references").mkdir(parents=True)
        (root / "docs/skills/demo").mkdir(parents=True)
        (root / "docs/changelogs").mkdir(parents=True)
        (root / "skills/demo/SKILL.md").write_text(
            "---\nname: demo\ndescription: Demo Skill\n---\n\n"
            "Read [policy](references/policy.md).\n",
            encoding="utf-8",
        )
        (root / "skills/demo/references/policy.md").write_text("policy\n", encoding="utf-8")
        (root / "docs/skills/demo/README.md").write_text("# Demo\n", encoding="utf-8")
        (root / "docs/skills/demo/README.zh-CN.md").write_text("# 演示\n", encoding="utf-8")
        (root / "docs/changelogs/demo.md").write_text("# Changelog\n", encoding="utf-8")
        (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
        (root / "CONTRIBUTING.md").write_text("Contribute upstream.\n", encoding="utf-8")

    def run_export(self, source: Path, destination: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(source),
                "--skill",
                "demo",
                "--destination",
                str(destination),
                "--source-commit",
                "abc123",
                "--version",
                "1.0.0",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_export_is_complete_and_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            destination = base / "mirror"
            self.make_repo(source)

            first = self.run_export(source, destination)
            self.assertEqual(first.returncode, 0, first.stderr)
            metadata = json.loads((destination / "SOURCE.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["skill"], "demo")
            self.assertTrue((destination / "skills/demo/references/policy.md").is_file())
            self.assertTrue((destination / ".github/workflows/redirect-contributions.yml").is_file())
            first_digest = metadata["export_digest"]

            second = self.run_export(source, destination)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(
                first_digest,
                json.loads((destination / "SOURCE.json").read_text(encoding="utf-8"))["export_digest"],
            )

    def test_unknown_mirror_drift_blocks_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            destination = base / "mirror"
            self.make_repo(source)
            self.assertEqual(self.run_export(source, destination).returncode, 0)
            (destination / "README.md").write_text("manual edit\n", encoding="utf-8")

            result = self.run_export(source, destination)
            self.assertEqual(result.returncode, 2)
            self.assertIn("mirror.drift", result.stderr)


if __name__ == "__main__":
    unittest.main()
