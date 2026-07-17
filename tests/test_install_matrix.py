from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "node_modules/skills/bin/cli.mjs"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_manifest(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): digest(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not any(part in {"node_modules", "__pycache__", ".git"} for part in path.parts)
    }


class InstallMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not CLI.is_file():
            raise unittest.SkipTest("run npm ci at the repository root before the install matrix")
        cls.node = subprocess.run(
            ["node", "-p", "process.execPath"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        registry = json.loads((ROOT / "registry/skills.json").read_text(encoding="utf-8"))
        cls.records = [item for item in registry["skills"] if item["lifecycle"] == "active"]

    def test_every_active_skill_copies_complete_payload(self) -> None:
        with tempfile.TemporaryDirectory() as source_tmp:
            clean_source = Path(source_tmp) / "source"
            shutil.copytree(
                ROOT,
                clean_source,
                ignore=shutil.ignore_patterns(
                    ".git",
                    ".agents",
                    "node_modules",
                    "__pycache__",
                    "*.pyc",
                    "reports",
                    "preview.html",
                ),
            )
            for record in self.records:
                with self.subTest(skill=record["name"]), tempfile.TemporaryDirectory() as tmp:
                    workspace = Path(tmp) / "workspace"
                    home = Path(tmp) / "home"
                    workspace.mkdir()
                    home.mkdir()
                    environment = {
                        "HOME": str(home),
                        "PATH": os.environ.get("PATH", ""),
                        "NO_COLOR": "1",
                        "CI": "1",
                    }
                    result = subprocess.run(
                        [
                            self.node,
                            str(CLI),
                            "add",
                            str(clean_source),
                            "--skill",
                            record["name"],
                            "--agent",
                            "codex",
                            "--copy",
                            "--yes",
                        ],
                        cwd=workspace,
                        env=environment,
                        text=True,
                        capture_output=True,
                        timeout=30,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
                    installed = workspace / ".agents/skills" / record["name"]
                    self.assertTrue(installed.is_dir(), result.stdout)
                    self.assertEqual(
                        package_manifest(clean_source / record["path"]),
                        package_manifest(installed),
                        "copied installation must retain every payload file byte-for-byte",
                    )
                    self.assertFalse((installed / "node_modules").exists())


if __name__ == "__main__":
    unittest.main()
