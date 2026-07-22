from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = ROOT / "skills/codex-model-routing-team"
CONTRACT = Path(__file__).with_name("codex-model-routing-team-expected.json")


class SkillContractTests(unittest.TestCase):
    def test_worker_budget_fits_total_cap(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        budget = contract["deep_research_budget"]
        self.assertLessEqual(sum(budget.values()), contract["max_total_workers"])

    def test_skill_preserves_routing_and_fallback_contract(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        package = "\n".join(
            path.read_text(encoding="utf-8") for path in sorted(SKILL_ROOT.rglob("*.md"))
        )
        for model in contract["known_models"]:
            self.assertIn(model, package)
        self.assertIn("spawn_agent", package)
        self.assertIn("禁止", package)
        self.assertIn("projectless", package)
        self.assertIn("reserved slots", package)
        for field in contract["required_thread_audit_fields"]:
            self.assertIn(field, package)

    def test_registry_preserves_automatic_and_manual_boundaries(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        registry = json.loads(
            (SKILL_ROOT / "references/model-registry.json").read_text(encoding="utf-8")
        )
        models = {item["id"]: item for item in registry["models"]}
        self.assertEqual(set(contract["known_models"]), set(models))
        self.assertEqual(
            set(contract["automatic_models"]),
            {model_id for model_id, item in models.items() if item["automatic"]},
        )
        self.assertEqual(
            set(contract["manual_only_models"]),
            {model_id for model_id, item in models.items() if item["status"] == "manual_only"},
        )
        self.assertTrue(
            set(contract["forbidden_worker_thinking"])
            <= set(registry["policy"]["forbidden_thinking"])
        )
        audit_schema = json.loads(
            (SKILL_ROOT / "references/audit-schema.json").read_text(encoding="utf-8")
        )
        self.assertTrue(
            set(contract["required_thread_audit_fields"])
            <= set(audit_schema["required"])
        )

    def run_preflight(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts/model_preflight.py"),
                *args,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_preflight_allows_grok_high_and_rejects_ultra(self) -> None:
        incomplete = self.run_preflight("--model", "xai/grok-4.5", "--thinking", "high")
        self.assertEqual(incomplete.returncode, 3, incomplete.stderr or incomplete.stdout)
        self.assertTrue(json.loads(incomplete.stdout)["registry_eligible"])
        self.assertFalse(json.loads(incomplete.stdout)["route_eligible"])

        allowed = self.run_preflight(
            "--model",
            "xai/grok-4.5",
            "--thinking",
            "high",
            "--runtime-confirmed",
            "--provider-status",
            "allowed",
            "--data-allowed",
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr or allowed.stdout)
        self.assertTrue(json.loads(allowed.stdout)["route_eligible"])

        forbidden = self.run_preflight("--model", "xai/grok-4.5", "--thinking", "ultra")
        self.assertEqual(forbidden.returncode, 2, forbidden.stderr or forbidden.stdout)
        self.assertFalse(json.loads(forbidden.stdout)["route_eligible"])

    def test_preflight_keeps_blocked_gemini_closed_even_when_explicit(self) -> None:
        implicit = self.run_preflight(
            "--model", "antigravity/gemini-3.6-flash", "--thinking", "medium"
        )
        self.assertEqual(implicit.returncode, 2, implicit.stderr or implicit.stdout)

        explicit = self.run_preflight(
            "--model",
            "antigravity/gemini-3.6-flash",
            "--thinking",
            "medium",
            "--explicit-user-request",
            "--risk-acknowledged",
            "--runtime-confirmed",
            "--provider-status",
            "allowed",
            "--data-allowed",
        )
        self.assertEqual(explicit.returncode, 2, explicit.stderr or explicit.stdout)
        payload = json.loads(explicit.stdout)
        self.assertFalse(payload["route_eligible"])
        self.assertIn("cannot be overridden", " ".join(payload["errors"]))

    def test_preflight_validates_runtime_catalog(self) -> None:
        catalog = {
            "models": [
                {
                    "slug": "xai/grok-4.5",
                    "supported_reasoning_levels": [{"effort": "medium"}],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            result = self.run_preflight(
                "--model",
                "xai/grok-4.5",
                "--thinking",
                "high",
                "--catalog",
                str(path),
                "--provider-status",
                "allowed",
                "--data-allowed",
            )
        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        self.assertIn("runtime catalog rejects", result.stdout)

    def test_preflight_semantic_probe_matches_nonce_without_leaking_body(self) -> None:
        class ProbeHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                match = re.search(r"ROUTE-CANARY-[0-9A-F]+", payload["input"])
                response = {
                    "output": [
                        {
                            "content": [
                                {"type": "output_text", "text": match.group(0) if match else ""}
                            ]
                        }
                    ]
                }
                body = json.dumps(response).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), ProbeHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = self.run_preflight(
                "--model",
                "xai/grok-4.5",
                "--thinking",
                "high",
                "--probe-url",
                f"http://127.0.0.1:{server.server_port}/v1/responses",
                "--provider-status",
                "allowed",
                "--data-allowed",
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["checks"]["semantic_probe"]["semantic_match"])
        self.assertNotIn("ROUTE-CANARY-", result.stdout)

    def test_preflight_rejects_remote_probe_url_before_credential_lookup(self) -> None:
        result = self.run_preflight(
            "--model",
            "xai/grok-4.5",
            "--thinking",
            "high",
            "--provider-status",
            "allowed",
            "--data-allowed",
            "--probe-url",
            "https://example.com/v1/responses",
            "--auth-env",
            "UNSET_TEST_CREDENTIAL",
        )
        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertIn("loopback", payload["checks"]["semantic_probe"]["error"])
        self.assertNotIn("UNSET_TEST_CREDENTIAL", payload["checks"]["semantic_probe"]["error"])

    def test_semantic_probe_blocks_redirects_and_oversized_responses(self) -> None:
        class UnsafeHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/oversized")
                    self.end_headers()
                    return
                body = json.dumps({"output_text": "x" * 70_000}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), UnsafeHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        common = (
            "--model",
            "xai/grok-4.5",
            "--thinking",
            "high",
            "--provider-status",
            "allowed",
            "--data-allowed",
        )
        try:
            redirected = self.run_preflight(
                *common,
                "--probe-url",
                f"http://127.0.0.1:{server.server_port}/redirect",
            )
            oversized = self.run_preflight(
                *common,
                "--probe-url",
                f"http://127.0.0.1:{server.server_port}/oversized",
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(redirected.returncode, 2, redirected.stderr or redirected.stdout)
        self.assertIn("redirect", redirected.stdout)
        self.assertEqual(oversized.returncode, 2, oversized.stderr or oversized.stdout)
        self.assertIn("exceeded 65536 bytes", oversized.stdout)

    def run_route_validator(self, plan: dict[str, object]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "route-plan.json"
            path.write_text(json.dumps(plan), encoding="utf-8")
            return subprocess.run(
                [
                    sys.executable,
                    str(SKILL_ROOT / "scripts/validate_route_plan.py"),
                    str(path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_route_plan_validator_enforces_order_provider_and_thinking(self) -> None:
        plan = {
            "task_class": "DEEP_AGENTIC_CODE",
            "minimum_thinking": "high",
            "provider_allowlist": ["xai", "openai"],
            "provider_status": {"xai": "allowed", "openai": "allowed"},
            "data_allowed_providers": ["xai", "openai"],
            "explicit_user_request": False,
            "risk_acknowledged": False,
            "candidates": [
                {"model": "xai/grok-4.5", "thinking": "high"},
                {"model": "gpt-5.6-sol", "thinking": "high"},
            ],
            "max_worker_threads": 2,
            "max_followups_per_thread": 1,
        }
        valid = self.run_route_validator(plan)
        self.assertEqual(valid.returncode, 0, valid.stderr or valid.stdout)

        plan["minimum_thinking"] = "xhigh"
        invalid = self.run_route_validator(plan)
        self.assertEqual(invalid.returncode, 2, invalid.stderr or invalid.stdout)
        self.assertIn("falls below minimum_thinking", invalid.stdout)

    def test_lifecycle_defines_data_ready_without_claiming_model_identity(self) -> None:
        lifecycle = (SKILL_ROOT / "references/thread-lifecycle.md").read_text(encoding="utf-8")
        self.assertIn("assistant-originated", lifecycle)
        self.assertIn("items 暂时为空", lifecycle)
        self.assertIn("先工具调用可以计入", lifecycle)
        self.assertIn("observed_runtime_model` 保持 `unknown", lifecycle)

    def test_adapter_keeps_verifier_before_reviewer(self) -> None:
        adapter = (SKILL_ROOT / "references/upstream-skill-adapter.md").read_text(encoding="utf-8")
        self.assertLess(adapter.index("verifier：1 个"), adapter.index("reviewer：1 个"))
        self.assertIn("每次调用 `create_thread` 前", adapter)
        self.assertIn("返回 ID 后立即补 `thread_id`", adapter)


if __name__ == "__main__":
    unittest.main()
