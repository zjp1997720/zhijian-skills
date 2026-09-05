from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
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
        registry = json.loads(
            (SKILL_ROOT / "references/model-registry.json").read_text(encoding="utf-8")
        )
        for model in (item["id"] for item in registry["models"]):
            self.assertIn(model, package)
        self.assertIn("spawn_agent", package)
        for surface in contract["execution_surfaces"]:
            self.assertIn(surface, package)
        self.assertIn("禁止", package)
        self.assertIn("projectless", package)
        self.assertIn("reserved slots", package)
        for tool in contract["required_tools"]:
            self.assertIn(tool, package)
        for field in contract["required_thread_audit_fields"]:
            self.assertIn(field, package)

    def test_registry_preserves_automatic_and_manual_boundaries(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        registry = json.loads(
            (SKILL_ROOT / "references/model-registry.json").read_text(encoding="utf-8")
        )
        models = {item["id"]: item for item in registry["models"]}
        self.assertTrue(models["gpt-5.6-luna"]["automatic"])
        self.assertTrue(models["gpt-5.6-sol"]["automatic"])
        self.assertEqual(
            registry["policy"]["fast_routing_models"],
            ["gpt-5.6-luna", "gpt-5.6-sol", "gpt-5.6-terra"],
        )
        self.assertEqual(registry["policy"]["default_fast_models"], [])
        self.assertEqual(
            registry["policy"]["fast_requires_explicit_models"],
            ["gpt-5.6-sol", "gpt-5.6-terra"],
        )
        self.assertEqual(registry["policy"]["app_thread_only_models"], [])
        self.assertEqual(registry["policy"]["default_surface"], "native_subagent")
        self.assertEqual(
            registry["policy"]["default_openai_route"],
            {
                "surface": "native_subagent",
                "model": "gpt-5.6-sol",
                "thinking": "medium",
                "speed": "standard",
                "fork_turns": "none",
            },
        )
        self.assertEqual(
            registry["policy"]["high_risk_openai_route"]["thinking"],
            "high",
        )
        self.assertEqual(
            registry["policy"]["openai_route_profiles"]["critical"]["minimum_thinking"],
            "xhigh",
        )
        self.assertEqual(
            registry["policy"]["route_selection"]["workload_profiles"]["mechanical"],
            "mechanical",
        )
        self.assertEqual(
            registry["policy"]["team_limit_profiles"]["expanded"],
            {
                "max_planned_workers": 12,
                "max_worker_attempts": 16,
                "max_new_workers_per_wave": 6,
                "min_reserved_slots": 2,
            },
        )
        self.assertEqual(
            models["gpt-5.6-luna"]["surface_thinking"]["native_subagent"],
            ["xhigh", "max"],
        )
        self.assertEqual(models["gpt-5.6-luna"]["multi_agent_version"], "v1")
        self.assertEqual(models["gpt-5.6-luna"]["native_role"], "leaf")
        self.assertEqual(models["gpt-5.6-luna"]["thinking"], ["xhigh", "max"])
        self.assertEqual(
            models["gpt-5.6-sol"]["thinking"], ["medium", "high", "xhigh", "max"]
        )
        self.assertEqual(models["gpt-5.6-terra"]["status"], "opt_in")
        self.assertFalse(models["gpt-5.6-terra"]["automatic"])
        self.assertEqual(models["antigravity/gemini-3.6-flash"]["status"], "manual_only")
        self.assertFalse(models["antigravity/gemini-3.6-flash"]["automatic"])
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
        native_schema = json.loads(
            (SKILL_ROOT / "references/native-audit-schema.json").read_text(
                encoding="utf-8"
            )
        )
        for field in contract["speed_audit_fields"]:
            self.assertIn(field, audit_schema["properties"])
            self.assertIn(field, native_schema["properties"])
        for field in contract["team_plan_audit_fields"]:
            self.assertIn(field, audit_schema["properties"])
            self.assertIn(field, native_schema["properties"])
        for field in contract["required_native_audit_fields"]:
            self.assertIn(field, native_schema["properties"])
            self.assertIn(field, native_schema["allOf"][0]["then"]["required"])

    def test_dual_surface_support_files_are_self_contained(self) -> None:
        required = (
            "references/native-audit-schema.json",
            "references/native-subagent-lifecycle.md",
            "references/surface-selection-policy.md",
            "references/team-plan.md",
            "references/route-compiler.md",
            "scripts/route_policy.py",
            "scripts/validate_team_plan.py",
            "scripts/compile_route_plan.py",
        )
        for relative in required:
            with self.subTest(relative=relative):
                self.assertTrue((SKILL_ROOT / relative).is_file())

    def test_initial_skill_body_preserves_router_contract_after_slimming(self) -> None:
        body = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for marker in (
            "native_subagent",
            "App Thread",
            'schema_version: "3.0"',
            "surface_intent",
            "fork_turns",
            "runtime_evidence",
            "service_tier=priority",
            "Luna",
            "Sol",
            "Terra",
            "Grok",
            "Gemini",
            "Ultra",
            "UNKNOWN",
            "task_id",
            "TeamPlan",
            "scripts/validate_team_plan.py",
            "reserved slots",
            "同波写冲突",
            "RELEASED",
            "scripts/validate_route_plan.py",
            "scripts/validate_team_ledger.py",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)
        self.assertLessEqual(len(body), 3_000)

    def test_orchestrator_does_not_pin_itself_to_luna(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = skill.split("---", 2)[1]
        self.assertNotRegex(frontmatter, r"(?m)^model\s*:")
        self.assertNotIn("model: luna", (SKILL_ROOT / "agents/openai.yaml").read_text())

    def test_validation_cases_cover_slimming_replay_set(self) -> None:
        cases = (SKILL_ROOT / "references/validation-cases.md").read_text(
            encoding="utf-8"
        )
        for case in (
            "默认 Native Sol",
            "Native Luna Fast 缺少 schema",
            "Sol thinking 与 Fast",
            "Durable App",
            "上游 Skill",
            "TeamPlan write collision",
            "Expanded capacity",
        ):
            self.assertIn(case, cases)

    def run_team_plan_validator(
        self, plan: dict[str, object], *, stdin: bool = False
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(SKILL_ROOT / "scripts/validate_team_plan.py"),
        ]
        if stdin:
            return subprocess.run(
                [*command, "-"],
                cwd=ROOT,
                input=json.dumps(plan),
                text=True,
                capture_output=True,
                check=False,
            )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "team-plan.json"
            path.write_text(json.dumps(plan), encoding="utf-8")
            return subprocess.run(
                [*command, str(path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

    def team_plan(
        self,
        *,
        unit_count: int = 2,
        revision: int = 1,
        supersedes_revision: int | None = None,
        scale_profile: str | None = None,
        scale_reason: str | None = None,
    ) -> dict[str, object]:
        units = []
        for index in range(1, unit_count + 1):
            units.append(
                {
                    "unit_id": f"U{index}",
                    "role": "researcher" if index < unit_count else "verifier",
                    "goal": f"Complete bounded unit {index}",
                    "output": f"reports/u{index}.md",
                    "depends_on": [],
                    "ownership": {
                        "write": [f"reports/u{index}.md"],
                        "forbidden": [],
                    },
                    "done_when": f"Unit {index} evidence is reviewable",
                }
            )
        plan: dict[str, object] = {
            "schema_version": "1.0",
            "revision": revision,
            "supersedes_revision": supersedes_revision,
            "planning_source": "ad_hoc",
            "source_refs": [],
            "root_goal": "Deliver an integrated result",
            "units": units,
            "reserved_slots": 8 - unit_count,
            "integration_owner": "lead",
            "integration_order": [unit["unit_id"] for unit in units],
            "final_verification": "Lead verifies the integrated result",
            "revision_reason": "initial" if revision == 1 else "new dependency evidence",
        }
        if scale_profile is not None:
            plan["scale_profile"] = scale_profile
        if scale_reason is not None:
            plan["scale_reason"] = scale_reason
        return plan

    def capacity_evidence(
        self,
        *,
        total: int = 6,
        coordinator: int = 1,
        active: int = 0,
        available: int = 5,
        captured_at: str | None = None,
    ) -> dict[str, object]:
        return {
            "kind": "live_tool_contract",
            "host": "test-host",
            "captured_at": captured_at or datetime.now(timezone.utc).isoformat(),
            "total_concurrency_slots": total,
            "coordinator_slots": coordinator,
            "active_worker_slots": active,
            "available_child_slots": available,
        }

    def test_team_plan_validator_accepts_stdin_and_computes_waves(self) -> None:
        plan = self.team_plan(unit_count=4)
        plan["reserved_slots"] = 4
        result = self.run_team_plan_validator(plan, stdin=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["team_plan_valid"])
        self.assertEqual(payload["dispatch_waves"], [["U1", "U2", "U3"], ["U4"]])

    def test_team_plan_validator_respects_dependency_layers(self) -> None:
        plan = self.team_plan(unit_count=3)
        plan["reserved_slots"] = 5
        plan["units"][2]["depends_on"] = ["U1", "U2"]
        result = self.run_team_plan_validator(plan)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(
            json.loads(result.stdout)["dispatch_waves"],
            [["U1", "U2"], ["U3"]],
        )

    def test_team_plan_validator_rejects_cycle_and_same_wave_write_overlap(self) -> None:
        cyclic = self.team_plan()
        cyclic["units"][0]["depends_on"] = ["U2"]
        cyclic["units"][1]["depends_on"] = ["U1"]
        cycle_result = self.run_team_plan_validator(cyclic)
        self.assertEqual(cycle_result.returncode, 2, cycle_result.stdout)
        self.assertIn("contains a cycle", cycle_result.stdout)

        overlap = self.team_plan()
        overlap["units"][0]["ownership"]["write"] = ["scripts"]
        overlap["units"][1]["ownership"]["write"] = ["scripts/router.py"]
        overlap_result = self.run_team_plan_validator(overlap)
        self.assertEqual(overlap_result.returncode, 2, overlap_result.stdout)
        self.assertIn("overlapping write scope", overlap_result.stdout)

    def test_team_plan_validator_rejects_budget_and_lead_ownership_drift(self) -> None:
        plan = self.team_plan(unit_count=6)
        plan["reserved_slots"] = 3
        plan["integration_owner"] = "worker"
        result = self.run_team_plan_validator(plan)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("exceed the attempt cap", result.stdout)
        self.assertIn("integration_owner must remain lead", result.stdout)

    def test_team_plan_validator_requires_upstream_source_refs(self) -> None:
        plan = self.team_plan()
        plan["planning_source"] = "ce_plan"
        result = self.run_team_plan_validator(plan)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("requires source_refs", result.stdout)

    def test_team_plan_validator_uses_expanded_profile_only_with_reason_and_reserve(self) -> None:
        standard = self.team_plan(unit_count=7)
        standard["reserved_slots"] = 1
        rejected = self.run_team_plan_validator(standard)
        self.assertEqual(rejected.returncode, 2, rejected.stdout)
        self.assertIn("between 2 and 6", rejected.stdout)

        expanded = self.team_plan(
            unit_count=12,
            scale_profile="expanded",
            scale_reason="Twelve independent read-only reviews have isolated outputs.",
        )
        expanded["reserved_slots"] = 2
        expanded["runtime_worker_capacity"] = 5
        expanded["runtime_capacity_evidence"] = self.capacity_evidence()
        accepted = self.run_team_plan_validator(expanded)
        self.assertEqual(accepted.returncode, 0, accepted.stdout)
        payload = json.loads(accepted.stdout)
        self.assertEqual(payload["scale_profile"], "expanded")
        self.assertEqual(payload["dispatch_waves"], [
            ["U1", "U2", "U3", "U4", "U5"],
            ["U6", "U7", "U8", "U9", "U10"],
            ["U11", "U12"],
        ])
        self.assertEqual(payload["effective_worker_capacity"], 5)

        no_capacity = self.team_plan(
            unit_count=7,
            scale_profile="expanded",
            scale_reason="Capacity must be live-confirmed.",
        )
        no_capacity["reserved_slots"] = 2
        missing_capacity = self.run_team_plan_validator(no_capacity)
        self.assertEqual(missing_capacity.returncode, 2, missing_capacity.stdout)
        self.assertIn(
            "requires runtime_worker_capacity",
            missing_capacity.stdout,
        )

        no_evidence = self.team_plan(
            unit_count=7,
            scale_profile="expanded",
            scale_reason="Capacity must include current live evidence.",
        )
        no_evidence["reserved_slots"] = 2
        no_evidence["runtime_worker_capacity"] = 5
        missing_evidence = self.run_team_plan_validator(no_evidence)
        self.assertEqual(missing_evidence.returncode, 2, missing_evidence.stdout)
        self.assertIn("requires runtime_capacity_evidence", missing_evidence.stdout)

        forged_capacity = json.loads(json.dumps(expanded))
        forged_capacity["runtime_capacity_evidence"]["active_worker_slots"] = 2
        forged = self.run_team_plan_validator(forged_capacity)
        self.assertEqual(forged.returncode, 2, forged.stdout)
        self.assertIn("slot arithmetic does not balance", forged.stdout)

        stale_capacity = json.loads(json.dumps(expanded))
        stale_capacity["runtime_capacity_evidence"]["captured_at"] = (
            datetime.now(timezone.utc) - timedelta(minutes=11)
        ).isoformat()
        stale = self.run_team_plan_validator(stale_capacity)
        self.assertEqual(stale.returncode, 2, stale.stdout)
        self.assertIn("is stale or from the future", stale.stdout)

        expanded.pop("scale_reason")
        expanded["reserved_slots"] = 1
        invalid = self.run_team_plan_validator(expanded)
        self.assertEqual(invalid.returncode, 2, invalid.stdout)
        self.assertIn("requires scale_reason", invalid.stdout)
        self.assertIn("at least 2 reserved_slots", invalid.stdout)

        too_large = self.team_plan(
            unit_count=13,
            scale_profile="expanded",
            scale_reason="Independent outputs still remain policy-bounded.",
        )
        too_large["reserved_slots"] = 2
        too_large["runtime_worker_capacity"] = 5
        too_large["runtime_capacity_evidence"] = self.capacity_evidence()
        oversized = self.run_team_plan_validator(too_large)
        self.assertEqual(oversized.returncode, 2, oversized.stdout)
        self.assertIn("between 2 and 12", oversized.stdout)

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
            "--host",
            "test-host",
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
            "--host",
            "test-host",
            "--provider-status",
            "allowed",
            "--data-allowed",
        )
        self.assertEqual(explicit.returncode, 2, explicit.stderr or explicit.stdout)
        payload = json.loads(explicit.stdout)
        self.assertFalse(payload["route_eligible"])
        self.assertIn("cannot be overridden", " ".join(payload["errors"]))

    def test_preflight_enforces_surface_thinking_and_terra_opt_in(self) -> None:
        thread_low = self.run_preflight(
            "--surface",
            "app_thread",
            "--model",
            "gpt-5.6-sol",
            "--thinking",
            "low",
        )
        self.assertEqual(thread_low.returncode, 2, thread_low.stderr or thread_low.stdout)
        self.assertIn("not declared for this model", thread_low.stdout)

        native_low = self.run_preflight(
            "--surface",
            "native_subagent",
            "--model",
            "gpt-5.6-sol",
            "--thinking",
            "low",
            "--runtime-confirmed",
            "--host",
            "test-host",
            "--provider-status",
            "allowed",
            "--data-allowed",
        )
        self.assertEqual(native_low.returncode, 2, native_low.stderr or native_low.stdout)
        self.assertIn("not declared for this model", native_low.stdout)

        native_high = self.run_preflight(
            "--surface",
            "native_subagent",
            "--model",
            "gpt-5.6-sol",
            "--thinking",
            "high",
            "--runtime-confirmed",
            "--host",
            "test-host",
            "--provider-status",
            "allowed",
            "--data-allowed",
        )
        self.assertEqual(native_high.returncode, 0, native_high.stderr or native_high.stdout)
        self.assertEqual(json.loads(native_high.stdout)["surface"], "native_subagent")

        missing_host = self.run_preflight(
            "--surface",
            "native_subagent",
            "--model",
            "gpt-5.6-sol",
            "--thinking",
            "high",
            "--runtime-confirmed",
            "--provider-status",
            "allowed",
            "--data-allowed",
        )
        self.assertEqual(missing_host.returncode, 2, missing_host.stdout)
        self.assertIn("requires --host", missing_host.stdout)

        terra_implicit = self.run_preflight(
            "--surface",
            "native_subagent",
            "--model",
            "gpt-5.6-terra",
            "--thinking",
            "low",
            "--runtime-confirmed",
            "--host",
            "test-host",
            "--provider-status",
            "allowed",
            "--data-allowed",
        )
        self.assertEqual(terra_implicit.returncode, 3, terra_implicit.stderr or terra_implicit.stdout)
        self.assertFalse(json.loads(terra_implicit.stdout)["route_eligible"])

        terra_explicit = self.run_preflight(
            "--surface",
            "native_subagent",
            "--model",
            "gpt-5.6-terra",
            "--thinking",
            "low",
            "--explicit-user-request",
            "--runtime-confirmed",
            "--host",
            "test-host",
            "--provider-status",
            "allowed",
            "--data-allowed",
        )
        self.assertEqual(terra_explicit.returncode, 0, terra_explicit.stderr or terra_explicit.stdout)
        self.assertTrue(json.loads(terra_explicit.stdout)["route_eligible"])

        terra_fast = self.run_preflight(
            "--surface",
            "native_subagent",
            "--model",
            "gpt-5.6-terra",
            "--thinking",
            "low",
            "--speed",
            "fast",
            "--explicit-user-request",
            "--runtime-confirmed",
            "--service-tier-confirmed",
            "--host",
            "test-host",
            "--provider-status",
            "allowed",
            "--data-allowed",
        )
        self.assertEqual(terra_fast.returncode, 0, terra_fast.stdout)
        self.assertEqual(
            json.loads(terra_fast.stdout)["runtime_evidence"]["service_tier"],
            "priority",
        )

    def test_preflight_allows_native_luna_leaf_and_requires_explicit_sol_fast(self) -> None:
        native_luna = self.run_preflight(
            "--surface",
            "native_subagent",
            "--model",
            "gpt-5.6-luna",
            "--thinking",
            "xhigh",
            "--runtime-confirmed",
            "--host",
            "test-host",
            "--provider-status",
            "allowed",
            "--data-allowed",
        )
        self.assertEqual(native_luna.returncode, 0, native_luna.stdout)
        native_payload = json.loads(native_luna.stdout)
        self.assertEqual(native_payload["fork_turns"], "none")
        self.assertEqual(native_payload["checks"]["registry"]["native_role"], "leaf")
        self.assertNotIn("service_tier", native_payload["runtime_evidence"])

        sol_fast = self.run_preflight(
            "--surface",
            "native_subagent",
            "--model",
            "gpt-5.6-sol",
            "--thinking",
            "high",
            "--speed",
            "fast",
            "--runtime-confirmed",
            "--service-tier-confirmed",
            "--host",
            "test-host",
            "--provider-status",
            "allowed",
            "--data-allowed",
        )
        self.assertEqual(sol_fast.returncode, 2, sol_fast.stdout)
        self.assertIn("requires an explicit user request", sol_fast.stdout)

        sol_fast_explicit = self.run_preflight(
            "--surface",
            "native_subagent",
            "--model",
            "gpt-5.6-sol",
            "--thinking",
            "high",
            "--speed",
            "fast",
            "--explicit-user-request",
            "--runtime-confirmed",
            "--service-tier-confirmed",
            "--host",
            "test-host",
            "--provider-status",
            "allowed",
            "--data-allowed",
        )
        self.assertEqual(sol_fast_explicit.returncode, 0, sol_fast_explicit.stdout)
        self.assertEqual(
            json.loads(sol_fast_explicit.stdout)["runtime_evidence"]["service_tier"],
            "priority",
        )

    def test_preflight_emits_app_speed_evidence_only_when_live_schema_accepts_it(self) -> None:
        confirmed = self.run_preflight(
            "--surface",
            "app_thread",
            "--model",
            "gpt-5.6-luna",
            "--thinking",
            "xhigh",
            "--speed",
            "fast",
            "--runtime-confirmed",
            "--service-tier-confirmed",
            "--host",
            "test-host",
            "--provider-status",
            "allowed",
            "--data-allowed",
        )
        self.assertEqual(confirmed.returncode, 0, confirmed.stdout)
        evidence = json.loads(confirmed.stdout)["speed_evidence"]
        self.assertEqual(evidence["kind"], "live_create_schema")
        self.assertEqual(evidence["service_tier"], "priority")

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

    def test_preflight_catalog_capability_does_not_invent_fast_support(self) -> None:
        catalog = {
            "models": [
                {
                    "slug": "gpt-5.6-luna",
                    "supported_reasoning_levels": [{"effort": "xhigh"}],
                    "service_tiers": [],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            missing = self.run_preflight(
                "--model",
                "gpt-5.6-luna",
                "--thinking",
                "xhigh",
                "--speed",
                "fast",
                "--catalog",
                str(path),
                "--provider-status",
                "allowed",
                "--data-allowed",
            )
        self.assertEqual(missing.returncode, 2, missing.stdout)
        self.assertIn("lacks the requested Fast service tier", missing.stdout)

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
            native_without_spawn_evidence = self.run_preflight(
                "--surface",
                "native_subagent",
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
        self.assertEqual(
            native_without_spawn_evidence.returncode,
            3,
            native_without_spawn_evidence.stderr or native_without_spawn_evidence.stdout,
        )
        self.assertFalse(json.loads(native_without_spawn_evidence.stdout)["route_eligible"])

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

    def run_route_validator_stdin(
        self, plan: dict[str, object]
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts/validate_route_plan.py"),
                "-",
            ],
            cwd=ROOT,
            input=json.dumps(plan),
            text=True,
            capture_output=True,
            check=False,
        )

    def run_route_compiler(
        self, request: dict[str, object]
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts/compile_route_plan.py"),
                "-",
            ],
            cwd=ROOT,
            input=json.dumps(request),
            text=True,
            capture_output=True,
            check=False,
        )

    def live_spawn_evidence(
        self,
        model: str = "gpt-5.6-sol",
        thinking: str = "high",
        speed: str | None = None,
        **overrides: object,
    ) -> dict[str, object]:
        evidence: dict[str, object] = {
            "kind": "live_spawn_schema",
            "surface": "native_subagent",
            "model": model,
            "thinking": thinking,
            "fork_turns": "none",
            "accepted": True,
            "host": "test-host",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        if speed is not None:
            evidence["speed"] = speed
            evidence["service_tier"] = "priority" if speed == "fast" else None
        evidence.update(overrides)
        return evidence

    def live_app_speed_evidence(
        self,
        model: str = "gpt-5.6-luna",
        thinking: str = "xhigh",
        **overrides: object,
    ) -> dict[str, object]:
        evidence: dict[str, object] = {
            "kind": "live_create_schema",
            "surface": "app_thread",
            "model": model,
            "thinking": thinking,
            "speed": "fast",
            "service_tier": "priority",
            "accepted": True,
            "host": "test-host",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        evidence.update(overrides)
        return evidence

    def live_app_evidence(
        self,
        model: str = "gpt-5.6-sol",
        thinking: str = "medium",
        **overrides: object,
    ) -> dict[str, object]:
        evidence: dict[str, object] = {
            "kind": "live_create_schema",
            "surface": "app_thread",
            "model": model,
            "thinking": thinking,
            "accepted": True,
            "host": "test-host",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        evidence.update(overrides)
        return evidence

    def native_candidate(
        self,
        model: str = "gpt-5.6-sol",
        thinking: str = "high",
        **overrides: object,
    ) -> dict[str, object]:
        candidate: dict[str, object] = {
            "surface": "native_subagent",
            "model": model,
            "thinking": thinking,
            "speed": "standard",
            "fork_turns": "none",
            "runtime_evidence": self.live_spawn_evidence(model, thinking),
        }
        candidate.update(overrides)
        return candidate

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

    def test_route_plan_validator_accepts_one_declared_worker(self) -> None:
        plan = {
            "task_class": "DEEP_AGENTIC_CODE",
            "minimum_thinking": "high",
            "provider_allowlist": ["xai"],
            "provider_status": {"xai": "allowed"},
            "data_allowed_providers": ["xai"],
            "explicit_user_request": True,
            "risk_acknowledged": True,
            "candidates": [{"model": "xai/grok-4.5", "thinking": "high"}],
            "max_worker_threads": 1,
            "max_followups_per_thread": 1,
        }
        valid = self.run_route_validator(plan)
        self.assertEqual(valid.returncode, 0, valid.stderr or valid.stdout)

        plan["max_worker_threads"] = 2
        mismatch = self.run_route_validator(plan)
        self.assertEqual(mismatch.returncode, 2, mismatch.stderr or mismatch.stdout)
        self.assertIn("must match the declared candidate count", mismatch.stdout)

    def test_route_plan_validator_accepts_explicit_sol_medium(self) -> None:
        plan = {
            "task_class": "EXPLICIT_DURABLE_GENERAL",
            "minimum_thinking": "medium",
            "provider_allowlist": ["openai"],
            "provider_status": {"openai": "allowed"},
            "data_allowed_providers": ["openai"],
            "explicit_user_request": True,
            "risk_acknowledged": True,
            "candidates": [{"model": "gpt-5.6-sol", "thinking": "medium"}],
            "max_worker_threads": 1,
            "max_followups_per_thread": 1,
        }
        valid = self.run_route_validator(plan)
        self.assertEqual(valid.returncode, 0, valid.stderr or valid.stdout)

    def test_route_plan_validator_live_gates_luna_fast_and_requires_explicit_sol(self) -> None:
        plan = {
            "schema_version": "2.1",
            "task_class": "DEFAULT_GENERAL",
            "minimum_thinking": "high",
            "provider_allowlist": ["openai"],
            "provider_status": {"openai": "allowed"},
            "data_allowed_providers": ["openai"],
            "explicit_user_request": False,
            "risk_acknowledged": False,
            "candidates": [
                {
                    "surface": "app_thread",
                    "model": "gpt-5.6-luna",
                    "thinking": "xhigh",
                    "speed": "fast",
                    "speed_evidence": self.live_app_speed_evidence(),
                }
            ],
            "max_worker_threads": 1,
            "max_followups_per_thread": 1,
        }
        luna_fast = self.run_route_validator(plan)
        self.assertEqual(luna_fast.returncode, 0, luna_fast.stderr or luna_fast.stdout)

        plan["candidates"][0]["model"] = "gpt-5.6-sol"
        plan["candidates"][0]["speed_evidence"]["model"] = "gpt-5.6-sol"
        sol_fast = self.run_route_validator(plan)
        self.assertEqual(sol_fast.returncode, 2, sol_fast.stderr or sol_fast.stdout)
        self.assertIn("model requires explicit_user_request for Fast", sol_fast.stdout)

        plan["explicit_user_request"] = True
        sol_fast_explicit = self.run_route_validator(plan)
        self.assertEqual(
            sol_fast_explicit.returncode,
            0,
            sol_fast_explicit.stderr or sol_fast_explicit.stdout,
        )

    def test_route_plan_validator_accepts_native_luna_with_v3_context_evidence(self) -> None:
        plan = {
            "schema_version": "3.0",
            "surface_intent": "parent_integrated",
            "task_class": "DEFAULT_GENERAL",
            "minimum_thinking": "high",
            "provider_allowlist": ["openai"],
            "provider_status": {"openai": "allowed"},
            "data_allowed_providers": ["openai"],
            "explicit_user_request": False,
            "risk_acknowledged": False,
            "candidates": [
                {
                    "surface": "native_subagent",
                    "model": "gpt-5.6-luna",
                    "thinking": "xhigh",
                    "speed": "standard",
                    "fork_turns": "none",
                    "runtime_evidence": self.live_spawn_evidence(
                        model="gpt-5.6-luna", thinking="xhigh"
                    ),
                }
            ],
            "max_worker_threads": 1,
            "max_followups_per_thread": 1,
        }
        valid = self.run_route_validator(plan)
        self.assertEqual(valid.returncode, 0, valid.stdout)

        plan["candidates"][0]["runtime_evidence"]["speed"] = "fast"
        plan["candidates"][0]["runtime_evidence"]["service_tier"] = "priority"
        mismatched_speed = self.run_route_validator(plan)
        self.assertEqual(mismatched_speed.returncode, 2, mismatched_speed.stdout)
        self.assertIn("contains mismatched Fast fields", mismatched_speed.stdout)
        plan["candidates"][0]["runtime_evidence"].pop("speed")
        plan["candidates"][0]["runtime_evidence"].pop("service_tier")

        plan["candidates"][0]["fork_turns"] = "all"
        invalid = self.run_route_validator(plan)
        self.assertEqual(invalid.returncode, 2, invalid.stdout)
        self.assertIn("requires fork_turns='none' or a positive turn count", invalid.stdout)

        legacy = json.loads(json.dumps(plan))
        legacy["schema_version"] = "2.1"
        legacy["candidates"][0]["fork_turns"] = "none"
        legacy["candidates"][0]["runtime_evidence"]["fork_turns"] = "none"
        rejected_legacy_native_luna = self.run_route_validator(legacy)
        self.assertEqual(
            rejected_legacy_native_luna.returncode,
            2,
            rejected_legacy_native_luna.stdout,
        )
        self.assertIn("v2.1 cannot authorize native Luna", rejected_legacy_native_luna.stdout)

    def test_route_plan_validator_rejects_app_fast_without_live_speed_evidence(self) -> None:
        plan = {
            "schema_version": "2.1",
            "task_class": "DEFAULT_GENERAL",
            "minimum_thinking": "high",
            "provider_allowlist": ["openai"],
            "provider_status": {"openai": "allowed"},
            "data_allowed_providers": ["openai"],
            "explicit_user_request": False,
            "risk_acknowledged": False,
            "candidates": [
                {
                    "surface": "app_thread",
                    "model": "gpt-5.6-luna",
                    "thinking": "xhigh",
                    "speed": "fast",
                }
            ],
            "max_worker_threads": 1,
            "max_followups_per_thread": 1,
        }
        invalid = self.run_route_validator(plan)
        self.assertEqual(invalid.returncode, 2, invalid.stdout)
        self.assertIn("requires tuple-bound live speed evidence", invalid.stdout)

    def test_route_plan_schema_21_requires_explicit_surface_and_speed(self) -> None:
        plan = {
            "schema_version": "2.1",
            "task_class": "DEFAULT_GENERAL",
            "minimum_thinking": "high",
            "provider_allowlist": ["openai"],
            "provider_status": {"openai": "allowed"},
            "data_allowed_providers": ["openai"],
            "explicit_user_request": False,
            "risk_acknowledged": False,
            "candidates": [{"model": "gpt-5.6-sol", "thinking": "high"}],
            "max_worker_threads": 1,
            "max_followups_per_thread": 1,
        }
        invalid = self.run_route_validator(plan)
        self.assertEqual(invalid.returncode, 2, invalid.stdout)
        self.assertIn("must declare surface", invalid.stdout)
        self.assertIn("must declare speed", invalid.stdout)

    def test_route_plan_validator_accepts_native_sol_high_with_live_evidence(self) -> None:
        plan = {
            "schema_version": "3.0",
            "surface_intent": "parent_integrated",
            "task_class": "NATIVE_WORKER_EXPLICIT",
            "minimum_thinking": "high",
            "provider_allowlist": ["openai"],
            "provider_status": {"openai": "allowed"},
            "data_allowed_providers": ["openai"],
            "explicit_user_request": False,
            "risk_acknowledged": False,
            "candidates": [self.native_candidate()],
            "max_worker_threads": 1,
            "max_followups_per_thread": 1,
        }
        automatic_native = self.run_route_validator(plan)
        self.assertEqual(automatic_native.returncode, 0, automatic_native.stdout)

        plan["explicit_user_request"] = True
        valid = self.run_route_validator(plan)
        self.assertEqual(valid.returncode, 0, valid.stderr or valid.stdout)

        plan["candidates"][0].pop("runtime_evidence")
        missing_live_evidence = self.run_route_validator(plan)
        self.assertEqual(
            missing_live_evidence.returncode,
            2,
            missing_live_evidence.stderr or missing_live_evidence.stdout,
        )
        self.assertIn("requires tuple-bound live runtime evidence", missing_live_evidence.stdout)

    def compact_request(
        self,
        *,
        workload: str = "routine",
        risk: str = "normal",
        surface_intent: str = "parent_integrated",
        evidence: list[dict[str, object]] | dict[str, object] | None = None,
        **overrides: object,
    ) -> dict[str, object]:
        if evidence is None:
            evidence = [
                self.live_spawn_evidence("gpt-5.6-sol", "medium"),
                self.live_spawn_evidence("gpt-5.6-sol", "high"),
            ]
        request: dict[str, object] = {
            "workload": workload,
            "risk": risk,
            "surface_intent": surface_intent,
            "provider_allowlist": ["openai"],
            "provider_status": {"openai": "allowed"},
            "data_allowed_providers": ["openai"],
            "explicit_user_request": False,
            "risk_acknowledged": False,
            "live_evidence": evidence,
        }
        request.update(overrides)
        return request

    def test_route_compiler_builds_registry_default_without_dispatching(self) -> None:
        result = self.run_route_compiler(self.compact_request())
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["selected_profile"], "default")
        plan = payload["route_plan"]
        self.assertEqual(plan["schema_version"], "3.0")
        self.assertEqual(
            [(item["model"], item["thinking"]) for item in plan["candidates"]],
            [("gpt-5.6-sol", "medium"), ("gpt-5.6-sol", "high")],
        )
        self.assertEqual(payload["validation"]["status"], "pass")
        self.assertTrue(payload["dispatch"]["ready"])
        self.assertFalse(payload["dispatch"]["auto_dispatch"])
        self.assertNotIn("spawn_agent", json.dumps(payload))

    def test_route_compiler_selects_mechanical_and_high_risk_registry_profiles(self) -> None:
        mechanical = self.run_route_compiler(
            self.compact_request(
                workload="mechanical",
                evidence=[
                    self.live_spawn_evidence("gpt-5.6-luna", "xhigh"),
                    self.live_spawn_evidence("gpt-5.6-sol", "medium"),
                ],
            )
        )
        self.assertEqual(mechanical.returncode, 0, mechanical.stdout)
        mechanical_payload = json.loads(mechanical.stdout)
        self.assertEqual(mechanical_payload["selected_profile"], "mechanical")
        self.assertEqual(
            mechanical_payload["route_plan"]["candidates"][0]["model"],
            "gpt-5.6-luna",
        )
        high_risk = self.run_route_compiler(
            self.compact_request(
                risk="high",
                evidence=[
                    self.live_spawn_evidence("gpt-5.6-sol", "high"),
                    self.live_spawn_evidence("gpt-5.6-sol", "xhigh"),
                ],
            )
        )
        self.assertEqual(high_risk.returncode, 0, high_risk.stdout)
        high_risk_payload = json.loads(high_risk.stdout)
        self.assertEqual(high_risk_payload["selected_profile"], "high_risk")
        self.assertEqual(
            high_risk_payload["route_plan"]["candidates"][0]["thinking"],
            "high",
        )

    def test_route_compiler_cannot_bypass_registry_risk_floor_with_override(self) -> None:
        result = self.run_route_compiler(
            self.compact_request(
                risk="high",
                route_profile="default",
                include_fallback=False,
                evidence=self.live_spawn_evidence("gpt-5.6-sol", "medium"),
            )
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("risk 'high' minimum_thinking high", result.stdout)

    def test_route_compiler_downgrades_fast_without_live_priority_evidence(self) -> None:
        result = self.run_route_compiler(
            self.compact_request(
                speed="fast",
                explicit_user_request=True,
                evidence=[
                    self.live_spawn_evidence("gpt-5.6-sol", "medium"),
                    self.live_spawn_evidence("gpt-5.6-sol", "high"),
                ],
            )
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["warnings"])
        candidates = payload["route_plan"]["candidates"]
        self.assertEqual([item["speed"] for item in candidates], ["standard", "standard"])
        self.assertNotIn("service_tier", json.dumps(payload["dispatch"]))

    def test_route_compiler_keeps_fast_only_with_exact_live_priority_evidence(self) -> None:
        result = self.run_route_compiler(
            self.compact_request(
                speed="fast",
                explicit_user_request=True,
                evidence=[
                    self.live_spawn_evidence("gpt-5.6-sol", "medium", speed="fast"),
                    self.live_spawn_evidence("gpt-5.6-sol", "high", speed="fast"),
                ],
            )
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(
            [item["speed"] for item in payload["route_plan"]["candidates"]],
            ["fast", "fast"],
        )
        self.assertEqual(
            [item.get("service_tier") for item in payload["dispatch"]["candidates"]],
            ["priority", "priority"],
        )

    def test_route_compiler_rejects_incomplete_fast_evidence(self) -> None:
        evidence = self.live_spawn_evidence(
            "gpt-5.6-sol", "medium", speed="fast"
        )
        evidence.pop("service_tier")
        result = self.run_route_compiler(
            self.compact_request(
                speed="fast",
                explicit_user_request=True,
                include_fallback=False,
                evidence=evidence,
            )
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("runtime evidence does not match", result.stdout)

    def test_route_compiler_reports_unaccepted_evidence_and_provider_block(self) -> None:
        evidence = self.live_spawn_evidence("gpt-5.6-sol", "medium")
        evidence.pop("accepted")
        missing_acceptance = self.run_route_compiler(
            self.compact_request(evidence=evidence, include_fallback=False)
        )
        self.assertEqual(missing_acceptance.returncode, 2, missing_acceptance.stdout)
        missing_payload = json.loads(missing_acceptance.stdout)
        self.assertIn("accepted", " ".join(missing_payload["errors"]))
        self.assertNotIn(
            "accepted",
            missing_payload["route_plan"]["candidates"][0]["runtime_evidence"],
        )

        blocked = self.run_route_compiler(
            self.compact_request(
                include_fallback=False,
                provider_status={"openai": "blocked"},
                evidence=self.live_spawn_evidence("gpt-5.6-sol", "medium"),
            )
        )
        self.assertEqual(blocked.returncode, 2, blocked.stdout)
        self.assertIn("provider policy is blocked", blocked.stdout)

    def test_route_compiler_requires_app_live_authorization_and_preserves_surface(self) -> None:
        no_app_evidence = self.run_route_compiler(
            self.compact_request(
                include_fallback=False,
                surface_intent="durable_app",
                evidence=[],
            )
        )
        self.assertEqual(no_app_evidence.returncode, 2, no_app_evidence.stdout)
        self.assertIn("host_authorization", no_app_evidence.stdout)

        app_evidence = [
            self.live_app_evidence("gpt-5.6-sol", "medium"),
            self.live_app_evidence("gpt-5.6-sol", "high"),
        ]
        app = self.run_route_compiler(
            self.compact_request(
                surface_intent="durable_app",
                evidence=app_evidence,
                host_authorization={
                    "surface": "app_thread",
                    "authorized": True,
                    "host": "test-host",
                    "source": "test-live-host",
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        )
        self.assertEqual(app.returncode, 0, app.stdout)
        app_payload = json.loads(app.stdout)
        self.assertEqual(
            {item["surface"] for item in app_payload["route_plan"]["candidates"]},
            {"app_thread"},
        )
        self.assertFalse(app_payload["dispatch"]["auto_dispatch"])
        self.assertNotIn("create_thread", json.dumps(app_payload["dispatch"]))

    def test_route_plan_validator_accepts_stdin_without_persisting_a_plan(self) -> None:
        plan = {
            "task_class": "NATIVE_WORKER_EXPLICIT",
            "minimum_thinking": "high",
            "provider_allowlist": ["openai"],
            "provider_status": {"openai": "allowed"},
            "data_allowed_providers": ["openai"],
            "explicit_user_request": True,
            "risk_acknowledged": False,
            "candidates": [self.native_candidate()],
            "max_worker_threads": 1,
            "max_followups_per_thread": 1,
        }
        from_file = self.run_route_validator(plan)
        from_stdin = self.run_route_validator_stdin(plan)
        self.assertEqual(from_stdin.returncode, 0, from_stdin.stderr or from_stdin.stdout)
        self.assertEqual(
            json.loads(from_stdin.stdout)["candidates"],
            json.loads(from_file.stdout)["candidates"],
        )

    def test_route_plan_validator_supports_predeclared_cross_surface_fallback(self) -> None:
        plan = {
            "task_class": "DEFAULT_GENERAL",
            "minimum_thinking": "high",
            "provider_allowlist": ["openai"],
            "provider_status": {"openai": "allowed"},
            "data_allowed_providers": ["openai"],
            "explicit_user_request": False,
            "risk_acknowledged": False,
            "candidates": [
                {
                    "surface": "app_thread",
                    "model": "gpt-5.6-luna",
                    "thinking": "xhigh",
                },
                {
                    "surface": "native_subagent",
                    "model": "gpt-5.6-sol",
                    "thinking": "high",
                    "runtime_evidence": self.live_spawn_evidence(),
                },
            ],
            "max_worker_threads": 2,
            "max_followups_per_thread": 1,
        }
        valid = self.run_route_validator(plan)
        self.assertEqual(valid.returncode, 0, valid.stderr or valid.stdout)

        plan["candidates"][0]["surface"] = "unknown_surface"
        invalid_surface = self.run_route_validator(plan)
        self.assertEqual(invalid_surface.returncode, 2, invalid_surface.stderr or invalid_surface.stdout)
        self.assertIn("unknown execution surface", invalid_surface.stdout)

    def test_route_plan_validator_defaults_legacy_candidates_to_app_thread(self) -> None:
        plan = {
            "task_class": "DEFAULT_GENERAL",
            "minimum_thinking": "high",
            "provider_allowlist": ["openai"],
            "provider_status": {"openai": "allowed"},
            "data_allowed_providers": ["openai"],
            "explicit_user_request": False,
            "risk_acknowledged": False,
            "candidates": [{"model": "gpt-5.6-sol", "thinking": "high"}],
            "max_worker_threads": 1,
            "max_followups_per_thread": 1,
        }
        valid = self.run_route_validator(plan)
        self.assertEqual(valid.returncode, 0, valid.stderr or valid.stdout)
        self.assertIn('"surface": "app_thread"', valid.stdout)

    def test_route_plan_validator_keeps_terra_explicit_and_first(self) -> None:
        plan = {
            "task_class": "TERRA_EXPLICIT",
            "minimum_thinking": "low",
            "provider_allowlist": ["openai"],
            "provider_status": {"openai": "allowed"},
            "data_allowed_providers": ["openai"],
            "explicit_user_request": True,
            "risk_acknowledged": False,
            "candidates": [
                self.native_candidate(model="gpt-5.6-terra"),
                self.native_candidate(),
            ],
            "max_worker_threads": 2,
            "max_followups_per_thread": 1,
        }
        valid = self.run_route_validator(plan)
        self.assertEqual(valid.returncode, 0, valid.stderr or valid.stdout)

        plan["explicit_user_request"] = False
        implicit = self.run_route_validator(plan)
        self.assertEqual(implicit.returncode, 2, implicit.stderr or implicit.stdout)
        self.assertIn("requires explicit_user_request", implicit.stdout)

        plan["explicit_user_request"] = True
        plan["candidates"].reverse()
        fallback = self.run_route_validator(plan)
        self.assertEqual(fallback.returncode, 2, fallback.stderr or fallback.stdout)
        self.assertIn("cannot be a fallback candidate", fallback.stdout)

    def test_route_plan_rejects_non_boolean_authorization_and_bad_runtime_evidence(self) -> None:
        plan = {
            "task_class": "TERRA_EXPLICIT",
            "minimum_thinking": "low",
            "provider_allowlist": ["openai"],
            "provider_status": {"openai": "allowed"},
            "data_allowed_providers": ["openai"],
            "explicit_user_request": "false",
            "risk_acknowledged": False,
            "candidates": [self.native_candidate(model="gpt-5.6-terra")],
            "max_worker_threads": 1,
            "max_followups_per_thread": 1,
        }
        invalid_boolean = self.run_route_validator(plan)
        self.assertEqual(invalid_boolean.returncode, 2, invalid_boolean.stdout)
        self.assertIn("explicit_user_request must be a boolean", invalid_boolean.stdout)

        plan["explicit_user_request"] = True
        plan["candidates"] = [
            self.native_candidate(
                model="gpt-5.6-terra",
                runtime_evidence=self.live_spawn_evidence(model="gpt-5.6-sol"),
            )
        ]
        mismatched = self.run_route_validator(plan)
        self.assertEqual(mismatched.returncode, 2, mismatched.stdout)
        self.assertIn("runtime evidence does not match", mismatched.stdout)

        stale_at = (datetime.now(timezone.utc) - timedelta(minutes=11)).isoformat()
        plan["candidates"] = [
            self.native_candidate(
                model="gpt-5.6-terra",
                runtime_evidence=self.live_spawn_evidence(
                    model="gpt-5.6-terra", checked_at=stale_at
                ),
            )
        ]
        stale = self.run_route_validator(plan)
        self.assertEqual(stale.returncode, 2, stale.stdout)
        self.assertIn("runtime evidence is stale", stale.stdout)

    def test_lifecycle_defines_data_ready_without_claiming_model_identity(self) -> None:
        lifecycle = (SKILL_ROOT / "references/thread-lifecycle.md").read_text(encoding="utf-8")
        self.assertIn("assistant-originated", lifecycle)
        self.assertIn("observed_runtime_model", lifecycle)
        self.assertIn("list_threads", lifecycle)

    def test_supervision_protocol_handles_pending_unknown_and_resume(self) -> None:
        protocol = (SKILL_ROOT / "references/thread-supervision-protocol.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("pendingWorktreeId", protocol)
        self.assertIn("list_threads(query=task_id)", protocol)
        self.assertIn("两次连续官方观察", protocol)
        self.assertIn("UNKNOWN` 禁止 follow-up、归档、fallback 和重复创建", protocol)
        self.assertIn("最新成功", protocol)
        self.assertLess(protocol.index("读取上游账本"), protocol.index("才沿原 RoutePlan"))

    def run_ledger_validator(self, payload: object) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "team-ledger.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [
                    sys.executable,
                    str(SKILL_ROOT / "scripts/validate_team_ledger.py"),
                    str(path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

    def run_ledger_validator_stdin(self, payload: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts/validate_team_ledger.py"),
                "-",
            ],
            cwd=ROOT,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )

    def ledger_record(self, **overrides: object) -> dict[str, object]:
        record: dict[str, object] = {
            "creation_attempt": 1,
            "subtask_attempt": 1,
            "task_id": "task-alpha-a1",
            "thread_id": "thread-alpha",
            "pending_worktree_id": None,
            "control_state": "COMPLETED",
            "thread_status": "idle",
            "turn_status": "completed",
            "last_observed_at": "2026-07-25T00:00:00+08:00",
            "role": "reviewer",
            "model": "gpt-5.6-sol",
            "requested_model": "gpt-5.6-sol",
            "platform_accepted_model": "gpt-5.6-sol",
            "observed_runtime_model": "unknown",
            "thinking": "xhigh",
            "route_plan": {},
            "provider_policy": {},
            "materialized": True,
            "data_ready": True,
            "status": "completed",
            "output": "reports/review.md",
            "adopted": True,
            "fallback_reason": None,
            "archived": True,
        }
        record.update(overrides)
        return record

    def native_ledger_record(self, **overrides: object) -> dict[str, object]:
        record: dict[str, object] = {
            "worker_attempt": 2,
            "subtask_attempt": 1,
            "task_id": "task-native-a1",
            "surface": "native_subagent",
            "agent_id": "agent-native",
            "control_state": "CLOSED",
            "agent_status": "completed",
            "last_observed_at": "2026-07-27T00:00:00+08:00",
            "fork_mode": "fresh",
            "role": "scout",
            "model": "gpt-5.6-sol",
            "requested_model": "gpt-5.6-sol",
            "platform_accepted_model": "gpt-5.6-sol",
            "observed_runtime_model": "unknown",
            "thinking": "high",
            "route_plan": {},
            "provider_policy": {},
            "status": "completed",
            "output": "CODEX_SOL_CHILD_OK",
            "adopted": True,
            "fallback_reason": None,
            "closed": True,
        }
        record.update(overrides)
        return record

    def route_plan_21(
        self,
        *,
        surface: str,
        model: str,
        thinking: str,
        speed: str,
        explicit_user_request: bool = False,
    ) -> dict[str, object]:
        return {
            "schema_version": "2.1",
            "explicit_user_request": explicit_user_request,
            "candidates": [
                {
                    "surface": surface,
                    "model": model,
                    "thinking": thinking,
                    "speed": speed,
                }
            ],
        }

    def test_ledger_validator_accepts_completed_and_pending_records(self) -> None:
        completed = self.ledger_record()
        pending = self.ledger_record(
            creation_attempt=2,
            task_id="task-beta-a1",
            thread_id=None,
            pending_worktree_id="pending-beta",
            control_state="CREATION_PENDING",
            thread_status=None,
            turn_status=None,
            last_observed_at=None,
            materialized=False,
            data_ready=False,
            status="creation_pending",
            output=None,
            adopted=False,
            archived=False,
        )
        result = self.run_ledger_validator(
            {"creation_attempts": 2, "workers": [completed, pending]}
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ledger_valid"])
        self.assertEqual(payload["in_flight_count"], 1)

    def test_ledger_validator_maps_workers_to_team_plan_units(self) -> None:
        plan = self.team_plan()
        first = self.ledger_record(unit_id="U1", team_plan_revision=1)
        second = self.ledger_record(
            creation_attempt=2,
            task_id="task-beta-a1",
            thread_id="thread-beta",
            unit_id="U2",
            team_plan_revision=1,
        )
        result = self.run_ledger_validator(
            {
                "team_plans": [plan],
                "active_team_plan_revision": 1,
                "creation_attempts": 2,
                "worker_attempts": 2,
                "workers": [first, second],
            }
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ledger_valid"])
        self.assertEqual(payload["warnings"], [])

    def test_ledger_validator_rejects_worker_outside_team_plan(self) -> None:
        result = self.run_ledger_validator(
            {
                "team_plans": [self.team_plan()],
                "active_team_plan_revision": 1,
                "workers": [
                    self.ledger_record(unit_id="U9", team_plan_revision=1)
                ],
            }
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("outside its TeamPlan revision", result.stdout)

    def test_ledger_validator_blocks_new_revision_while_old_wave_is_active(self) -> None:
        revision_one = self.team_plan()
        revision_two = self.team_plan(revision=2, supersedes_revision=1)
        old_active = self.ledger_record(
            unit_id="U1",
            team_plan_revision=1,
            control_state="DATA_READY",
            thread_status="active",
            turn_status="inProgress",
            output=None,
            adopted=False,
            archived=False,
        )
        new_planned = self.ledger_record(
            creation_attempt=2,
            task_id="task-new-revision-a1",
            unit_id="U1",
            team_plan_revision=2,
            thread_id=None,
            control_state="PLANNED",
            thread_status=None,
            turn_status=None,
            last_observed_at=None,
            materialized=False,
            data_ready=False,
            status="planned",
            output=None,
            adopted=False,
            archived=False,
        )
        result = self.run_ledger_validator(
            {
                "team_plans": [revision_one, revision_two],
                "active_team_plan_revision": 2,
                "workers": [old_active, new_planned],
            }
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("older revision is still in flight", result.stdout)

    def test_ledger_validator_blocks_activating_revision_before_old_wave_closes(self) -> None:
        result = self.run_ledger_validator(
            {
                "team_plans": [
                    self.team_plan(),
                    self.team_plan(revision=2, supersedes_revision=1),
                ],
                "active_team_plan_revision": 2,
                "workers": [
                    self.ledger_record(
                        unit_id="U1",
                        team_plan_revision=1,
                        control_state="DATA_READY",
                        thread_status="active",
                        turn_status="inProgress",
                        output=None,
                        adopted=False,
                        archived=False,
                    )
                ],
            }
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("older revision is still in flight", result.stdout)

    def test_ledger_validator_enforces_two_contiguous_attempts_per_unit(self) -> None:
        first = self.ledger_record(unit_id="U1", team_plan_revision=1)
        duplicate = self.ledger_record(
            creation_attempt=2,
            task_id="task-alpha-a2",
            thread_id="thread-alpha-a2",
            unit_id="U1",
            team_plan_revision=1,
            subtask_attempt=1,
        )
        result = self.run_ledger_validator(
            {
                "team_plans": [self.team_plan()],
                "active_team_plan_revision": 1,
                "workers": [first, duplicate],
            }
        )
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("attempts must be unique and contiguous", result.stdout)

    def test_ledger_validator_warns_for_undispatched_team_plan_unit(self) -> None:
        result = self.run_ledger_validator(
            {
                "team_plans": [self.team_plan()],
                "active_team_plan_revision": 1,
                "workers": [
                    self.ledger_record(unit_id="U1", team_plan_revision=1)
                ],
            }
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        warnings = json.loads(result.stdout)["warnings"]
        self.assertTrue(any("unit U2 has no Worker record" in item for item in warnings))

    def test_ledger_validator_rejects_unknown_archive_and_pending_as_thread(self) -> None:
        invalid = self.ledger_record(
            thread_id="pending-same",
            pending_worktree_id="pending-same",
            control_state="UNKNOWN",
        )
        result = self.run_ledger_validator([invalid])
        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        self.assertIn("pending id as a formal thread id", result.stdout)
        self.assertIn("cannot archive UNKNOWN", result.stdout)

    def test_ledger_validator_uses_official_state_not_legacy_status(self) -> None:
        active = self.ledger_record(
            control_state="DATA_READY",
            thread_status="active",
            turn_status="inProgress",
            status="done",
            output=None,
            adopted=False,
            archived=False,
        )
        result = self.run_ledger_validator([active])
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_ledger_validator_applies_expanded_team_plan_limits(self) -> None:
        plan = self.team_plan(
            unit_count=7,
            scale_profile="expanded",
            scale_reason="Seven isolated outputs can be reviewed independently.",
        )
        plan["reserved_slots"] = 2
        plan["runtime_worker_capacity"] = 7
        plan["runtime_capacity_evidence"] = self.capacity_evidence(
            total=8,
            coordinator=1,
            active=0,
            available=7,
        )
        workers = []
        for index in range(1, 7):
            workers.append(
                self.ledger_record(
                    creation_attempt=index,
                    task_id=f"task-expanded-{index}",
                    thread_id=None,
                    pending_worktree_id=None,
                    control_state="PLANNED",
                    thread_status=None,
                    turn_status=None,
                    last_observed_at=None,
                    materialized=False,
                    data_ready=False,
                    status="planned",
                    output=None,
                    adopted=False,
                    archived=False,
                    unit_id=f"U{index}",
                    team_plan_revision=1,
                )
            )
        result = self.run_ledger_validator(
            {
                "creation_attempts": 6,
                "worker_attempts": 6,
                "team_plans": [plan],
                "active_team_plan_revision": 1,
                "workers": workers,
            }
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["scale_profile"], "expanded")
        self.assertEqual(payload["in_flight_count"], 6)

    def test_ledger_validator_rejects_inspect_source_mutation(self) -> None:
        inspect = self.ledger_record(
            task_intent="inspect",
            mutation_authority="declared-workspace",
        )
        result = self.run_ledger_validator([inspect])
        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        self.assertIn("grants source mutation to inspect", result.stdout)

    def test_ledger_validator_accepts_mixed_thread_and_native_records(self) -> None:
        thread_record = self.ledger_record(archived=False)
        native_record = self.native_ledger_record()
        result = self.run_ledger_validator(
            {
                "worker_attempts": 2,
                "creation_attempts": 1,
                "workers": [thread_record, native_record],
            }
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ledger_valid"])

    def test_ledger_validator_requires_speed_identity_for_schema_21(self) -> None:
        route_plan = self.route_plan_21(
            surface="app_thread",
            model="gpt-5.6-luna",
            thinking="high",
            speed="standard",
        )
        valid_record = self.ledger_record(
            model="gpt-5.6-luna",
            requested_model="gpt-5.6-luna",
            platform_accepted_model="gpt-5.6-luna",
            thinking="high",
            requested_speed="standard",
            platform_accepted_speed="standard",
            observed_runtime_speed="unknown",
            route_plan=route_plan,
        )
        valid = self.run_ledger_validator([valid_record])
        self.assertEqual(valid.returncode, 0, valid.stdout)

        missing = dict(valid_record)
        missing.pop("observed_runtime_speed")
        invalid = self.run_ledger_validator([missing])
        self.assertEqual(invalid.returncode, 2, invalid.stdout)
        self.assertIn("missing speed audit fields", invalid.stdout)

    def test_ledger_validator_distinguishes_default_and_explicit_fast(self) -> None:
        route_plan = self.route_plan_21(
            surface="app_thread",
            model="gpt-5.6-luna",
            thinking="xhigh",
            speed="fast",
        )
        luna_fast = self.ledger_record(
            model="gpt-5.6-luna",
            requested_model="gpt-5.6-luna",
            platform_accepted_model="gpt-5.6-luna",
            thinking="xhigh",
            requested_speed="fast",
            platform_accepted_speed="fast",
            observed_runtime_speed="unknown",
            route_plan=route_plan,
        )
        valid = self.run_ledger_validator([luna_fast])
        self.assertEqual(valid.returncode, 0, valid.stdout)

        sol_fast = dict(luna_fast)
        sol_fast["model"] = "gpt-5.6-sol"
        sol_fast["requested_model"] = "gpt-5.6-sol"
        sol_fast["platform_accepted_model"] = "gpt-5.6-sol"
        sol_fast["route_plan"] = self.route_plan_21(
            surface="app_thread",
            model="gpt-5.6-sol",
            thinking="xhigh",
            speed="fast",
        )
        invalid = self.run_ledger_validator([sol_fast])
        self.assertEqual(invalid.returncode, 2, invalid.stdout)
        self.assertIn("model requires explicit_user_request for Fast", invalid.stdout)

        sol_fast["route_plan"] = self.route_plan_21(
            surface="app_thread",
            model="gpt-5.6-sol",
            thinking="xhigh",
            speed="fast",
            explicit_user_request=True,
        )
        explicit = self.run_ledger_validator([sol_fast])
        self.assertEqual(explicit.returncode, 0, explicit.stdout)

    def test_ledger_validator_accepts_native_light_ledger_from_stdin(self) -> None:
        payload = [self.native_ledger_record(worker_attempt=1)]
        from_file = self.run_ledger_validator(payload)
        from_stdin = self.run_ledger_validator_stdin(payload)
        self.assertEqual(from_stdin.returncode, 0, from_stdin.stderr or from_stdin.stdout)
        self.assertEqual(
            json.loads(from_stdin.stdout)["record_count"],
            json.loads(from_file.stdout)["record_count"],
        )

    def test_thread_ledger_requires_compatible_attempt_fields_to_match(self) -> None:
        matching = self.ledger_record(worker_attempt=1)
        valid = self.run_ledger_validator([matching])
        self.assertEqual(valid.returncode, 0, valid.stderr or valid.stdout)

        mismatched = self.ledger_record(worker_attempt=2)
        invalid = self.run_ledger_validator([mismatched])
        self.assertEqual(invalid.returncode, 2, invalid.stderr or invalid.stdout)
        self.assertIn("worker_attempt must equal creation_attempt", invalid.stdout)

    def test_native_ledger_requires_close_gate_for_adopted_output(self) -> None:
        native_record = self.native_ledger_record(control_state="COMPLETED", closed=False)
        result = self.run_ledger_validator([native_record])
        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        self.assertIn("adopted native output must be closed", result.stdout)

    def test_native_v3_ledger_accepts_completed_idle_release(self) -> None:
        route_plan = {
            "schema_version": "3.0",
            "surface_intent": "parent_integrated",
            "explicit_user_request": False,
            "candidates": [
                {
                    "surface": "native_subagent",
                    "model": "gpt-5.6-sol",
                    "thinking": "high",
                    "speed": "standard",
                    "fork_turns": "none",
                    "runtime_evidence": self.live_spawn_evidence(),
                }
            ],
        }
        released = self.native_ledger_record(
            worker_attempt=1,
            control_state="RELEASED",
            fork_turns="none",
            requested_speed="standard",
            platform_accepted_speed="standard",
            observed_runtime_speed="unknown",
            route_plan=route_plan,
            closed=False,
            released=True,
            release_method="completed_idle",
        )
        valid = self.run_ledger_validator([released])
        self.assertEqual(valid.returncode, 0, valid.stderr or valid.stdout)

        running_release = dict(released)
        running_release["agent_status"] = "running"
        still_running = self.run_ledger_validator([running_release])
        self.assertEqual(still_running.returncode, 2, still_running.stdout)
        self.assertIn(
            "completed_idle release requires completed or idle agent_status",
            still_running.stdout,
        )

        no_evidence = json.loads(json.dumps(released))
        no_evidence["route_plan"]["candidates"][0].pop("runtime_evidence")
        missing_evidence = self.run_ledger_validator([no_evidence])
        self.assertEqual(
            missing_evidence.returncode,
            2,
            missing_evidence.stderr or missing_evidence.stdout,
        )
        self.assertIn("lacks matching native runtime evidence", missing_evidence.stdout)

        unreleased = dict(released)
        unreleased.update(
            control_state="COMPLETED",
            released=False,
            release_method=None,
        )
        invalid = self.run_ledger_validator([unreleased])
        self.assertEqual(invalid.returncode, 2, invalid.stderr or invalid.stdout)
        self.assertIn("adopted native output must be released", invalid.stdout)

    def test_native_ledger_rejects_inherited_or_mismatched_route_identity(self) -> None:
        for override, message in (
            ({"fork_mode": "inherited"}, "must use fresh context"),
            ({"platform_accepted_model": "gpt-5.6-terra"}, "accepted model mismatch"),
            ({"observed_runtime_model": "gpt-5.6-terra"}, "observed model mismatch"),
        ):
            with self.subTest(override=override):
                result = self.run_ledger_validator(
                    [self.native_ledger_record(**override)]
                )
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn(message, result.stdout)

    def test_completed_unclosed_native_agents_still_consume_concurrency(self) -> None:
        records = []
        for attempt in range(1, 8):
            records.append(
                self.native_ledger_record(
                    worker_attempt=attempt,
                    task_id=f"native-{attempt}",
                    agent_id=f"agent-{attempt}",
                    control_state="COMPLETED" if attempt < 7 else "RUNNING",
                    closed=False,
                    adopted=False,
                    output=None,
                )
            )
        result = self.run_ledger_validator(records)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("in-flight records exceed the concurrency cap", result.stdout)

    def test_native_policy_requires_v3_context_and_release_without_silent_inheritance(self) -> None:
        policy = (SKILL_ROOT / "references/native-subagent-lifecycle.md").read_text(
            encoding="utf-8"
        )
        self.assertIn('fork_turns="none"', policy)
        self.assertIn('fork_turns="all"', policy)
        self.assertIn("RELEASED", policy)
        self.assertIn("completed_idle", policy)
        self.assertIn("禁止静默继承父模型", policy)
        self.assertIn("observed_runtime_model", policy)

    def test_adapter_keeps_verifier_before_reviewer(self) -> None:
        adapter = (SKILL_ROOT / "references/upstream-skill-adapter.md").read_text(encoding="utf-8")
        self.assertLess(adapter.index("verifier：1 个"), adapter.index("reviewer：1 个"))
        self.assertIn("每次调用 `create_thread` 前", adapter)
        self.assertIn("返回正式 id 或 pending id 后写入对应字段", adapter)


if __name__ == "__main__":
    unittest.main()
