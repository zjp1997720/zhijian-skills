from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/codex-skill-admin/scripts/codex_skill_admin.py"
SPEC = importlib.util.spec_from_file_location("codex_skill_admin_under_test", SCRIPT)
assert SPEC and SPEC.loader
admin = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(admin)


NOW = dt.datetime(2026, 9, 5, tzinfo=dt.timezone.utc).timestamp()


def stamp(offset_seconds: int = 0) -> str:
    return dt.datetime.fromtimestamp(NOW + offset_seconds, tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")


def call(
    path: str,
    *,
    timestamp: str = stamp(),
    kind: str = "function_call",
    name: str = "functions.exec",
    call_id: str = "call-1",
) -> dict[str, object]:
    if kind == "function_call":
        arguments: object = json.dumps({"cmd": f"cat {path}"})
        payload = {"type": kind, "name": name, "arguments": arguments, "call_id": call_id}
    else:
        payload = {"type": kind, "name": name, "input": {"path": path}, "call_id": call_id}
    return {"type": "response_item", "timestamp": timestamp, "payload": payload}


def result(
    call_id: str,
    *,
    timestamp: str = stamp(1),
    payload: dict[str, object] | None = None,
    kind: str = "function_call_output",
) -> dict[str, object]:
    return {
        "type": "response_item",
        "timestamp": timestamp,
        "payload": {"type": kind, "call_id": call_id, **(payload or {"output": "skill body"})},
    }


class SkillAdminUsageFixtureTests(unittest.TestCase):
    def run_events(self, events: list[dict[str, object]], *, aliases: str = "") -> dict[str, object]:
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / "session.jsonl"
            session.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
            with mock.patch.object(admin, "recent_session_files", return_value=[session]), mock.patch.dict(
                os.environ, {admin.PATH_ALIASES_ENV: aliases}, clear=False
            ):
                return admin.collect_skill_usage(30, now=NOW)

    def test_output_targets_are_not_reads_and_legacy_exit_errors_are_failed(self) -> None:
        self.assertEqual(admin._shell_read_paths("cat > /skills/out/SKILL.md"), [])
        self.assertEqual(admin._shell_read_paths("cat /skills/in/SKILL.md >/skills/out/SKILL.md"), ["/skills/in/SKILL.md"])
        for text in ['Script completed\nOutput: {"exit_code": 1, "output": ""}', 'Chunk ID: abc\nProcess exited with code 1\nFinal output:']:
            self.assertEqual(admin._result_status({"payload": {"output": text}}), "failed")

    def test_function_and_custom_tool_calls_require_success_result(self) -> None:
        function_path = "/skills/function/SKILL.md"
        custom_path = "/skills/custom/SKILL.md"
        usage = self.run_events(
            [
                call(function_path, call_id="function"),
                result("function"),
                {
                    "type": "response_item",
                    "timestamp": stamp(),
                    "payload": {
                        "type": "custom_tool_call",
                        "name": "functions.exec",
                        "input": f'text(await tools.exec_command({{cmd:"cat {custom_path}"}}))',
                        "call_id": "custom",
                    },
                },
                result("custom", kind="custom_tool_call_output", payload={"isError": False, "output": "body"}),
            ]
        )
        self.assertEqual({function_path, custom_path}, set(usage["successful"]))
        self.assertEqual(1, admin.usage_count(usage["successful"][function_path]))
        self.assertEqual(1, admin.usage_count(usage["successful"][custom_path]))

    def test_event_time_window_and_duplicate_reads_are_session_aggregated(self) -> None:
        path = "/skills/repeated/SKILL.md"
        usage = self.run_events(
            [
                call(path, timestamp=stamp(-31 * 86400), call_id="old"),
                result("old", timestamp=stamp(-31 * 86400 + 1)),
                call(path, call_id="one"),
                result("one"),
                call(path, call_id="two"),
                result("two"),
            ]
        )
        self.assertEqual(2, len(usage["successful"][path]))
        self.assertEqual(1, usage["outside_window_count"])
        self.assertEqual(1, admin.usage_count(usage["successful"][path]))

    def test_failed_and_unmatched_results_are_not_successful(self) -> None:
        failed_path = "/skills/failed/SKILL.md"
        unknown_path = "/skills/unknown/SKILL.md"
        usage = self.run_events(
            [
                call(failed_path, call_id="failed"),
                result("failed", payload={"isError": True, "error": "permission denied"}),
                call(unknown_path, kind="custom_tool_call", name="read_file", call_id="unknown"),
            ]
        )
        self.assertNotIn(failed_path, usage["successful"])
        self.assertNotIn(unknown_path, usage["successful"])
        self.assertIn(failed_path, usage["failed"])
        self.assertIn(unknown_path, usage["unknown"])

    def test_aliases_apply_only_to_real_reads_and_mentions_are_ignored(self) -> None:
        old_path = "/old/root/alias/SKILL.md"
        new_path = "/new/root/alias/SKILL.md"
        usage = self.run_events(
            [
                {
                    "type": "response_item",
                    "timestamp": stamp(),
                    "payload": {
                        "type": "function_call",
                        "name": "functions.exec",
                        "arguments": json.dumps({"cmd": f'echo "{old_path}"'}),
                        "call_id": "mention",
                    },
                },
                result("mention"),
                call(old_path, name="read_file", kind="custom_tool_call", call_id="alias"),
                result("alias", kind="custom_tool_call_output", payload={"status": "completed", "output": "body"}),
            ],
            aliases="/old/root=/new/root",
        )
        self.assertEqual({new_path}, set(usage["successful"]))

    def test_self_audit_call_is_excluded_but_real_read_in_same_session_remains(self) -> None:
        path = "/skills/audited/SKILL.md"
        self_audit = {
            "type": "response_item",
            "timestamp": stamp(),
            "payload": {
                "type": "custom_tool_call",
                "name": "functions.exec",
                "input": {"cmd": f"cat {path}; python3 codex_skill_admin.py audit-unused --days 30"},
                "call_id": "audit",
            },
        }
        usage = self.run_events([self_audit, result("audit", kind="custom_tool_call_output")])
        self.assertNotIn(path, usage["successful"])
        usage = self.run_events([call(path, call_id="real"), result("real"), self_audit, result("audit")])
        self.assertEqual(1, len(usage["successful"][path]))

    def test_explicit_session_exclusion_removes_all_evidence_from_that_session(self) -> None:
        path = "/skills/excluded/SKILL.md"
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / "session.jsonl"
            session.write_text(
                json.dumps(call(path, call_id="excluded")) + "\n" + json.dumps(result("excluded")) + "\n",
                encoding="utf-8",
            )
            with mock.patch.object(admin, "recent_session_files", return_value=[session]):
                usage = admin.collect_skill_usage(30, now=NOW, exclude_sessions=[str(session)])
        self.assertEqual({}, usage["successful"])
        self.assertEqual(1, usage["excluded_session_count"])

    def test_unknown_result_and_unknown_tool_are_exposed_separately(self) -> None:
        unknown_result_path = "/skills/empty-result/SKILL.md"
        unsupported_path = "/skills/unsupported/SKILL.md"
        opaque_js_path = "/skills/opaque-js/SKILL.md"
        usage = self.run_events(
            [
                call(unknown_result_path, call_id="empty"),
                result("empty", payload={"output": ""}),
                call(unsupported_path, kind="custom_tool_call", name="mystery_tool", call_id="unsupported"),
                result("unsupported", kind="custom_tool_call_output", payload={"output": "body"}),
                {
                    "type": "response_item",
                    "timestamp": stamp(),
                    "payload": {
                        "type": "custom_tool_call",
                        "name": "functions.exec",
                        "input": f"text(await tools.exec_command({{cmd: makeCommand('{opaque_js_path}')}}))",
                        "call_id": "opaque-js",
                    },
                },
                result("opaque-js", kind="custom_tool_call_output", payload={"output": "body"}),
            ]
        )
        self.assertIn(unknown_result_path, usage["unknown"])
        self.assertIn(unsupported_path, usage["unknown"])
        self.assertIn(opaque_js_path, usage["unknown"])
        self.assertEqual(2, len(usage["unsupported"]))

    def test_nested_exec_results_are_error_first_and_pending_is_unknown(self) -> None:
        nested_failure = "/skills/nested-failure/SKILL.md"
        yielded = "/skills/yielded/SKILL.md"
        mixed = "/skills/mixed/SKILL.md"
        missing = "/skills/missing/SKILL.md"
        usage = self.run_events(
            [
                call(nested_failure, call_id="nested"),
                result(
                    "nested",
                    payload={
                        "output": 'Script completed with result {"exit_code":1,"output":"cat: no such file"}',
                    },
                ),
                call(yielded, call_id="yield"),
                result("yield", payload={"output": "Script running with cell ID 42"}),
                call(mixed, call_id="mixed"),
                result(
                    "mixed",
                    payload={
                        "output": [
                            {"status": "completed", "output": "body"},
                            {"status": "failed", "error": "inner call failed"},
                        ]
                    },
                ),
                call(missing, call_id="missing"),
                result("missing", payload={"output": "cat: /skills/missing/SKILL.md: No such file or directory"}),
            ]
        )
        self.assertIn(nested_failure, usage["failed"])
        self.assertIn(yielded, usage["unknown"])
        self.assertIn(mixed, usage["failed"])
        self.assertIn(missing, usage["failed"])
        self.assertEqual({}, usage["successful"])

    def test_audit_does_not_disable_skill_with_uncertain_evidence(self) -> None:
        uncertain_path = "/skills/uncertain/SKILL.md"
        untouched_path = "/skills/untouched/SKILL.md"
        skills = [
            {"name": "uncertain", "scope": "user", "path": uncertain_path, "enabled": True},
            {"name": "untouched", "scope": "user", "path": untouched_path, "enabled": True},
        ]
        fake_usage = {
            "successful": {},
            "read_intents": {uncertain_path: [{"source": "s", "session": "s", "status": "unknown"}]},
            "unknown": {uncertain_path: [{"source": "s", "session": "s", "status": "unknown"}]},
            "failed": {},
            "unsupported": [],
            "outside_window_count": 0,
            "missing_timestamp_count": 0,
            "excluded_session_count": 0,
        }
        with mock.patch.object(admin, "collect_skill_usage", return_value=fake_usage):
            audit = admin.audit_unused(skills, 30, 0, False, [])
        self.assertEqual([untouched_path], [item["path"] for item in audit["disableCandidates"]])
        self.assertEqual([uncertain_path], [item["path"] for item in audit["uncertainEnabled"]])


if __name__ == "__main__":
    unittest.main()
