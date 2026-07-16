from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "scan_workspace.py"
SPEC = importlib.util.spec_from_file_location("codex_doctor_scan", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ScanWorkspaceTests(unittest.TestCase):
    def make_repo(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / ".git").mkdir()
        return temp, root

    def test_frontmatter_parser_ignores_body_name_examples(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        skill = root / "SKILL.md"
        skill.write_text("---\nname: real-name\ndescription: real description\n---\n\n```yaml\nname: fake-name\n```\n", encoding="utf-8")
        data, error = MODULE.parse_frontmatter(skill)
        self.assertIsNone(error)
        self.assertEqual(data["name"], "real-name")

    def test_instruction_chain_flags_byte_limit(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        (root / "AGENTS.md").write_text("# Rules\n" + ("critical rule\n" * 20), encoding="utf-8")
        findings = []
        inventory = {}
        MODULE.scan_instructions(root, root, root / ".codex-home", {"project_doc_max_bytes": 80}, findings, inventory)
        self.assertTrue(any(x["id"].startswith("instructions.effective_chain_truncated") for x in findings))

    def test_cross_host_parity_is_inventory_not_deletion_finding(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        content = "# Safety\n\n- Never delete user work without approval.\n"
        (root / "AGENTS.md").write_text(content, encoding="utf-8")
        (root / "CLAUDE.md").write_text(content, encoding="utf-8")
        findings = []
        inventory = {}
        MODULE.scan_instructions(root, root, root / ".codex-home", {}, findings, inventory)
        self.assertEqual(inventory["instructions"]["cross_host_parity"]["classification"], "parity_inventory_not_deletion_finding")
        self.assertFalse(any("claude" in x["summary"].lower() and x["severity"] != "S4" for x in findings))

    def test_disabled_mcp_with_missing_command_is_not_failure(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        findings = []
        inventory = {}
        user = {"mcp_servers": {"off": {"command": "definitely-missing-command", "enabled": False}}}
        MODULE.scan_config_mcp_hooks(root, root / ".codex-home", user, {}, findings, inventory)
        self.assertFalse(any(x["domain"] == "mcp" for x in findings))

    def test_project_secret_values_are_redacted(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        (root / ".codex").mkdir()
        findings = []
        inventory = {}
        project = {"service": {"api_key": "super-secret-value"}}
        MODULE.scan_config_mcp_hooks(root, root / ".codex-home", {}, project, findings, inventory)
        report = json.dumps(findings)
        self.assertIn("project_secret_shaped_values", report)
        self.assertNotIn("super-secret-value", report)
        finding = next(x for x in findings if "project_secret_shaped_values" in x["id"])
        self.assertEqual(finding["severity"], "S4")
        self.assertEqual(finding["confidence"], "medium")

    def test_enabled_mcp_without_transport_is_failure(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        findings = []
        inventory = {}
        user = {"mcp_servers": {"broken": {"enabled": True}}}
        MODULE.scan_config_mcp_hooks(root, root / ".codex-home", user, {}, findings, inventory, root)
        hit = next(x for x in findings if "enabled_transport_missing" in x["id"])
        self.assertEqual(hit["severity"], "S1")

    def test_interpreter_with_missing_static_script_is_failure(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        with mock.patch.object(MODULE.shutil, "which", return_value="/usr/bin/python3"):
            self.assertFalse(MODULE.command_exists("python3 scripts/missing.py", root))

    def test_untracked_sensitive_name_is_advisory_not_proven_exposure(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        completed = mock.Mock(returncode=0, stdout="# branch.head main\n? auth.json\n", stderr="")
        findings = []
        inventory = {}
        with mock.patch.object(MODULE, "run", return_value=completed):
            MODULE.scan_git_root(root, findings, inventory)
        hit = next(x for x in findings if "untracked_sensitive_names" in x["id"])
        self.assertEqual(hit["severity"], "S4")

    def test_explicit_root_docs_prohibition_is_enforced(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        (root / "AGENTS.md").write_text("- 禁止在根目录重建 `docs/`。\n", encoding="utf-8")
        (root / "docs").mkdir()
        completed = mock.Mock(returncode=0, stdout="# branch.head main\n? docs/spec.md\n", stderr="")

        def fake_run(cmd: list[str], cwd: Path, timeout: int = 30):
            if cmd[1:3] == ["status", "--porcelain=v2"]:
                return completed
            if cmd[1:3] == ["check-ignore", "-q"]:
                return mock.Mock(returncode=1, stdout="", stderr="")
            raise AssertionError(f"unexpected command: {cmd}")

        findings = []
        inventory = {}
        with mock.patch.object(MODULE, "run", side_effect=fake_run):
            MODULE.scan_git_root(root, findings, inventory)
        hit = next(x for x in findings if "explicitly_forbidden_root_docs" in x["id"])
        self.assertEqual(hit["evidence"]["rule"]["line"], 1)

    def test_root_docs_is_not_flagged_without_explicit_rule(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        (root / "docs").mkdir()
        completed = mock.Mock(returncode=0, stdout="# branch.head main\n? docs/spec.md\n", stderr="")
        findings = []
        inventory = {}
        with mock.patch.object(MODULE, "run", return_value=completed):
            MODULE.scan_git_root(root, findings, inventory)
        self.assertFalse(any("explicitly_forbidden_root_docs" in x["id"] for x in findings))

    def test_generated_output_inside_protected_root_is_flagged(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        (root / ".codex" / "visualizations").mkdir(parents=True)
        completed = mock.Mock(returncode=0, stdout="# branch.head main\n? .codex/visualizations/report.html\n", stderr="")

        def fake_run(cmd: list[str], cwd: Path, timeout: int = 30):
            if cmd[1:3] == ["status", "--porcelain=v2"]:
                return completed
            if cmd[1:3] == ["check-ignore", "-q"]:
                return mock.Mock(returncode=1, stdout="", stderr="")
            raise AssertionError(f"unexpected command: {cmd}")

        findings = []
        inventory = {}
        with mock.patch.object(MODULE, "run", side_effect=fake_run):
            MODULE.scan_git_root(root, findings, inventory)
        hit = next(x for x in findings if "generated_paths_inside_protected_root_not_ignored" in x["id"])
        self.assertEqual(hit["evidence"]["paths"], [".codex/visualizations"])

    def test_inline_toml_hook_missing_command_is_reported(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        findings = []
        inventory = {}
        user = {
            "hooks": {
                "PreToolUse": [
                    {"hooks": [{"type": "command", "command": "definitely-missing-hook-command"}]}
                ]
            }
        }
        MODULE.scan_config_mcp_hooks(root, root / ".codex-home", user, {}, findings, inventory, root)
        hit = next(x for x in findings if x["domain"] == "hooks" and "command_missing" in x["id"])
        self.assertEqual(hit["source"], str(root / ".codex-home" / "config.toml"))
        self.assertEqual(hit["evidence"]["source_kind"], "inline_toml")

    def test_duplicate_missing_hooks_have_unique_finding_ids(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        codex_home = root / ".codex-home"
        codex_home.mkdir()
        (codex_home / "hooks.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {
                                "hooks": [
                                    {"type": "command", "command": "missing-repeat-command"},
                                    {"type": "command", "command": "missing-repeat-command"},
                                ]
                            }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        findings = []
        inventory = {}
        MODULE.scan_config_mcp_hooks(root, codex_home, {}, {}, findings, inventory, root)
        ids = [x["id"] for x in findings if x["domain"] == "hooks" and "command_missing" in x["id"]]
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 2)

    def test_invalid_inline_hook_shape_is_reported(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        findings = []
        inventory = {}
        user = {"hooks": {"PreToolUse": {"hooks": []}}}
        MODULE.scan_config_mcp_hooks(root, root / ".codex-home", user, {}, findings, inventory, root)
        hit = next(x for x in findings if "inline_toml_schema_error" in x["id"])
        self.assertEqual(hit["severity"], "S1")

    def test_hook_trust_state_is_not_treated_as_inline_hook_definition(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        codex_home = root / ".codex-home"
        codex_home.mkdir()
        (codex_home / "hooks.json").write_text('{"hooks": {}}', encoding="utf-8")
        findings = []
        inventory = {}
        user = {"hooks": {"state": {"source:stop:0:0": {"trusted_hash": "abc"}}}}
        MODULE.scan_config_mcp_hooks(root, codex_home, user, {}, findings, inventory, root)
        self.assertFalse(any("inline_toml" in x["id"] or "merged_sources" in x["id"] for x in findings))
        self.assertFalse(any(x["type"] == "inline_toml" for x in inventory["hooks"]))

    def test_project_mcp_override_is_scanned_as_effective_config(self) -> None:
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        findings = []
        inventory = {}
        user = {"mcp_servers": {"shared": {"command": "missing-user-command"}}}
        project = {"mcp_servers": {"shared": {"enabled": False}}}
        MODULE.scan_config_mcp_hooks(root, root / ".codex-home", user, project, findings, inventory, root)
        self.assertFalse(any(x["domain"] == "mcp" for x in findings))
        item = next(x for x in inventory["mcp"] if x["name"] == "shared")
        self.assertFalse(item["enabled"])
        self.assertTrue(item["overrides_user_definition"])

    def test_markdown_targets_ignore_fenced_examples(self) -> None:
        text = "[real](references/real.md)\n```markdown\n[placeholder](url)\n```\n"
        self.assertEqual(MODULE.markdown_targets_outside_fences(text), ["references/real.md"])

    def test_built_in_findings_remain_separate(self) -> None:
        payload = {
            "schemaVersion": 1,
            "checks": {
                "network.http": {"status": "fail", "summary": "HTTP failed", "details": {}},
                "network.websocket": {"status": "ok", "summary": "WebSocket passed", "details": {}},
            },
        }
        completed = mock.Mock(returncode=1, stdout=json.dumps(payload), stderr="")
        findings = []
        inventory = {}
        with mock.patch.object(MODULE.shutil, "which", return_value="/usr/bin/codex"), mock.patch.object(MODULE, "run", return_value=completed):
            MODULE.built_in_doctor(Path.cwd(), findings, inventory, False)
        self.assertEqual(len([x for x in findings if x["domain"] == "built_in"]), 1)
        self.assertEqual(inventory["built_in_doctor"]["checks"]["network.websocket"]["status"], "ok")

    def test_compact_report_preserves_findings_and_check_rows(self) -> None:
        report = {
            "schemaVersion": 1,
            "scanner": "codex-doctor-workspace",
            "overallStatus": "warn",
            "summary": {"S0": 0, "S1": 0, "S2": 1, "S3": 0, "S4": 0, "total": 1},
            "findings": [{"id": "root_hygiene.example", "severity": "S2"}],
            "inventory": {
                "built_in_doctor": {
                    "schemaVersion": 1,
                    "codexVersion": "1.2.3",
                    "overallStatus": "fail",
                    "checks": {
                        "network.http": {"status": "fail", "summary": "HTTP failed", "details": {"large": "payload"}},
                        "network.websocket": {"status": "ok", "summary": "WebSocket passed", "details": {"large": "payload"}},
                    },
                },
                "skills": {"count": 1, "roots": ["/skills"], "items": [{"path": "/skills/a/SKILL.md", "body": "large"}]},
            },
            "safety": {"read_only": True},
        }
        compact = MODULE.compact_report(report)
        self.assertEqual(compact["findings"], report["findings"])
        self.assertEqual(compact["inventory"]["skills"]["itemsOmitted"], 1)
        self.assertNotIn("items", compact["inventory"]["skills"])
        self.assertEqual(compact["inventory"]["built_in_doctor"]["checks"]["network.http"]["status"], "fail")
        self.assertEqual(compact["inventory"]["built_in_doctor"]["checks"]["network.websocket"]["status"], "ok")
        self.assertNotIn("details", compact["inventory"]["built_in_doctor"]["checks"]["network.http"])


if __name__ == "__main__":
    unittest.main()
