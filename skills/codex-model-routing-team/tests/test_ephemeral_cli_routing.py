from __future__ import annotations

import json
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
COMPILER = SKILL_ROOT / "scripts" / "compile_route_plan.py"
VALIDATOR = SKILL_ROOT / "scripts" / "validate_route_plan.py"


class EphemeralCliRoutingTests(unittest.TestCase):
    def evidence(self, model: str, thinking: str = "high") -> dict[str, object]:
        return {
            "kind": "live_codex_cli_help_catalog",
            "surface": "ephemeral_codex_cli",
            "model": model,
            "thinking": thinking,
            "speed": "standard",
            "fresh_context": True,
            "ephemeral": True,
            "sandbox": "read-only",
            "help_verified": True,
            "catalog_verified": True,
            "host": "test-host",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def request(self, model: str, provider: str, provider_state: str) -> dict[str, object]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "surface_intent": "ephemeral_cli",
            "routes": [
                {
                    "surface": "ephemeral_codex_cli",
                    "model": model,
                    "thinking": "high",
                    "speed": "standard",
                    "fresh_context": True,
                    "runtime_evidence": self.evidence(model),
                }
            ],
            "provider_allowlist": [provider],
            "provider_status": {provider: provider_state},
            "data_allowed_providers": [provider],
            "explicit_user_request": True,
            "risk_acknowledged": False,
            "cli_authorization": {
                "surface": "ephemeral_codex_cli",
                "user_authorized": True,
                "host_policy": "allowed",
                "source": "current_user_request",
                "host": "test-host",
                "checked_at": now,
            },
            "include_fallback": False,
        }

    def compile(self, request: dict[str, object]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(COMPILER), "-"],
            input=json.dumps(request),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_exact_flash_models_compile_to_ephemeral_read_only_argv(self) -> None:
        cases = (
            (
                "opencode-go/deepseek-v4.1-flash",
                "opencode-go",
                "manual_authorized",
            ),
            (
                "antigravity/gemini-3.8-flash",
                "google-antigravity",
                "experimental_authorized",
            ),
        )
        for model, provider, provider_state in cases:
            with self.subTest(model=model):
                result = self.compile(self.request(model, provider, provider_state))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                self.assertTrue(payload["dispatch"]["ready"])
                candidate = payload["dispatch"]["candidates"][0]
                self.assertEqual(candidate["surface"], "ephemeral_codex_cli")
                self.assertEqual(candidate["lifecycle"], "process_exit")
                self.assertEqual(
                    candidate["argv"],
                    [
                        "codex",
                        "exec",
                        "--ephemeral",
                        "-s",
                        "read-only",
                        "-m",
                        model,
                        "-c",
                        'model_reasoning_effort="high"',
                        "--json",
                        "-o",
                        "response.md",
                        "-",
                    ],
                )

    def test_cli_route_rejects_native_schema_stale_tuple_and_host_denial(self) -> None:
        model = "opencode-go/deepseek-v4.1-flash"
        request = self.request(model, "opencode-go", "manual_authorized")

        request["routes"][0]["runtime_evidence"]["kind"] = "live_spawn_schema"
        forged = self.compile(request)
        self.assertEqual(forged.returncode, 2, forged.stdout)
        self.assertIn("must not impersonate native schema", forged.stdout)

        request = self.request(model, "opencode-go", "manual_authorized")
        request["routes"][0]["runtime_evidence"]["checked_at"] = (
            datetime.now(timezone.utc) - timedelta(minutes=11)
        ).isoformat()
        stale = self.compile(request)
        self.assertEqual(stale.returncode, 2, stale.stdout)
        self.assertIn("evidence is stale", stale.stdout)

        request = self.request(model, "opencode-go", "manual_authorized")
        request["routes"][0]["runtime_evidence"]["thinking"] = "max"
        mismatched = self.compile(request)
        self.assertEqual(mismatched.returncode, 2, mismatched.stdout)
        self.assertIn("does not match the candidate tuple", mismatched.stdout)

        request = self.request(model, "opencode-go", "manual_authorized")
        request["cli_authorization"]["host_policy"] = "blocked"
        blocked = self.compile(request)
        self.assertEqual(blocked.returncode, 2, blocked.stdout)
        self.assertIn("host_policy", blocked.stdout)

    def test_provider_run_states_do_not_become_automatic_allowed(self) -> None:
        cases = (
            ("opencode-go/deepseek-v4.1-flash", "opencode-go"),
            ("antigravity/gemini-3.8-flash", "google-antigravity"),
        )
        for model, provider in cases:
            with self.subTest(model=model):
                result = self.compile(self.request(model, provider, "allowed"))
                self.assertEqual(result.returncode, 3, result.stdout)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["status"], "manual_review")
                self.assertFalse(payload["dispatch"]["ready"])

    def test_cli_route_rejects_fast_and_missing_explicit_request(self) -> None:
        model = "antigravity/gemini-3.8-flash"
        request = self.request(
            model, "google-antigravity", "experimental_authorized"
        )
        request["routes"][0]["speed"] = "fast"
        fast = self.compile(request)
        self.assertEqual(fast.returncode, 2, fast.stdout)
        self.assertIn("requires Standard speed", fast.stdout)

        request = self.request(
            model, "google-antigravity", "experimental_authorized"
        )
        request["explicit_user_request"] = False
        implicit = self.compile(request)
        self.assertEqual(implicit.returncode, 2, implicit.stdout)
        self.assertIn("requires explicit_user_request", implicit.stdout)

    def test_cli_audit_schema_requires_unknown_capable_observation_fields(self) -> None:
        schema = json.loads(
            (SKILL_ROOT / "references" / "cli-audit-schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            schema["properties"]["surface"]["const"], "ephemeral_codex_cli"
        )
        self.assertIn("observed_runtime_model", schema["required"])
        self.assertIn("observed_runtime_thinking", schema["required"])
        self.assertNotIn("thread_id", schema["properties"])
        self.assertNotIn("agent_id", schema["properties"])


if __name__ == "__main__":
    unittest.main()
