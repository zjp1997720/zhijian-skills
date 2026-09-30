"""Routing decisions and admission gates, without model calls or dispatch."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from compile_route_plan import compile_request, DEFAULT_REGISTRY, DEFAULT_VALIDATOR
from prepare_native_team import prepare


def evidence(model, thinking):
    return {"kind": "live_spawn_schema", "surface": "native_subagent", "model": model,
            "thinking": thinking, "fork_turns": "none", "accepted": True,
            "host": "test-host", "checked_at": datetime.now(timezone.utc).isoformat()}


def request(workload="routine", state="specified", pairs=None, **overrides):
    if pairs is None:
        pairs = [("gpt-6-luna", "xhigh"), ("gpt-6.1-sol", "medium")]
    value = {"workload": workload, "risk": "normal", "surface_intent": "parent_integrated",
             "task_contract": {"decision_state": state, "acceptance": "Run target tests and compare each claim with the supplied sources"},
             "provider_allowlist": ["openai"], "provider_status": {"openai": "allowed"},
             "data_allowed_providers": ["openai"], "explicit_user_request": False,
             "risk_acknowledged": False, "live_evidence": [evidence(*p) for p in pairs]}
    value.update(overrides)
    return value


def compile_route(value):
    return compile_request(value, registry_path=DEFAULT_REGISTRY, validator_path=DEFAULT_VALIDATOR)


class LunaRoutingTests(unittest.TestCase):
    def assert_route(self, value, expected):
        code, result = compile_route(value)
        self.assertEqual(code, 0, result["errors"])
        self.assertTrue(result["dispatch"]["ready"])
        self.assertFalse(result["dispatch"]["auto_dispatch"])
        self.assertEqual([(c["model"], c["thinking"]) for c in result["route_plan"]["candidates"]], expected)
        return result["route_plan"]

    def test_decision_state_and_risk_matrix(self):
        cases = [
            ("routine", "specified", "normal", [("gpt-6-luna", "xhigh"), ("gpt-6.1-sol", "medium")]),
            ("mechanical", "specified", "normal", [("gpt-6-luna", "xhigh"), ("gpt-6.1-sol", "medium")]),
            ("complex", "specified", "normal", [("gpt-6-luna", "max"), ("gpt-6.1-sol", "high")]),
            ("routine", "unresolved", "normal", [("gpt-6.1-sol", "medium"), ("gpt-6.1-sol", "high")]),
            ("complex", "unresolved", "normal", [("gpt-6.1-sol", "high"), ("gpt-6.1-sol", "xhigh")]),
            ("review", "specified", "normal", [("gpt-6.1-sol", "high"), ("gpt-6.1-sol", "xhigh")]),
            ("complex", "specified", "high", [("gpt-6.1-sol", "high"), ("gpt-6.1-sol", "xhigh")]),
            ("routine", "specified", "critical", [("gpt-6.1-sol", "xhigh")]),
            ("critical_review", "specified", "high", [("gpt-6.1-sol", "xhigh")]),
        ]
        for workload, state, risk, pairs in cases:
            with self.subTest(workload=workload, state=state, risk=risk):
                plan = self.assert_route(request(workload, state, pairs, risk=risk), pairs)
                self.assertEqual(plan["task_contract"]["decision_state"], state)

    def test_contract_missing_unknown_or_empty_is_rejected(self):
        for contract in [None, {}, {"decision_state": "unknown", "acceptance": "test"},
                         {"decision_state": "specified", "acceptance": " "},
                         {"decision_state": "specified", "acceptance": []}]:
            with self.subTest(contract=contract):
                code, result = compile_route(request(task_contract=contract))
                self.assertEqual(code, 2)
                self.assertFalse(result["dispatch"]["ready"])
                self.assertIn("task_contract", str(result["errors"]))

    def test_luna_admission_cannot_be_bypassed_by_explicit_routes_or_raw_plan(self):
        plan = self.assert_route(request(), [("gpt-6-luna", "xhigh"), ("gpt-6.1-sol", "medium")])
        variants = [None, {"decision_state": "unresolved", "acceptance": "test"}]
        for contract in variants:
            with self.subTest(contract=contract):
                raw = copy.deepcopy(plan)
                raw["task_contract"] = contract
                result = subprocess.run([sys.executable, str(DEFAULT_VALIDATOR), "-"], input=json.dumps(raw), text=True, capture_output=True)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("Luna requires", result.stdout)
                explicit = request(task_contract=contract, routes=[{"model": "gpt-6-luna", "thinking": "xhigh"}], pairs=[("gpt-6-luna", "xhigh")])
                code, compiled = compile_route(explicit)
                self.assertEqual(code, 2, compiled)
                self.assertIn("Luna requires", str(compiled["errors"]))

    def test_explicit_luna_cannot_claim_critical_review_or_high_risk(self):
        for changes in [{"risk": "high"}, {"workload": "critical_review"}, {"task_class": "CRITICAL_REVIEW"}]:
            with self.subTest(changes=changes):
                code, result = compile_route(request(routes=[{"model": "gpt-6-luna", "thinking": "max"}], pairs=[("gpt-6-luna", "max")], **changes))
                self.assertEqual(code, 2, result)
                self.assertIn("high-risk or critical review", str(result["errors"]))

    def test_explicit_profile_cannot_lower_critical_review_floor(self):
        code, result = compile_route(request(workload="critical_review", route_profile="judgment", pairs=[("gpt-6.1-sol", "medium"), ("gpt-6.1-sol", "high")]))
        self.assertEqual(code, 2)
        self.assertIn("protected task minimum_thinking xhigh", str(result["errors"]))

    def test_two_attempt_depth_fallback_without_sol_third_attempt(self):
        pairs = [("gpt-6-luna", "xhigh"), ("gpt-6-luna", "max")]
        plan = self.assert_route(request(pairs=pairs, fallback="complex"), pairs)
        self.assertEqual(plan["max_worker_threads"], 2)
        self.assertEqual(plan["max_followups_per_thread"], 1)
        code, result = compile_route(request(routes=[{"model": m, "thinking": t} for m, t in pairs + [("gpt-6.1-sol", "high")]]))
        self.assertEqual(code, 2)
        self.assertIn("one or two", str(result["errors"]))

    def test_luna_lower_effort_and_missing_live_tuple_stay_rejected(self):
        for effort in ["low", "medium", "high", "ultra"]:
            with self.subTest(effort=effort):
                code, result = compile_route(request(routes=[{"model": "gpt-6-luna", "thinking": effort}], pairs=[("gpt-6-luna", effort)]))
                self.assertEqual(code, 2)
                self.assertFalse(result["dispatch"]["ready"])
        code, result = compile_route(request(pairs=[("gpt-5.6-luna", "xhigh"), ("gpt-5.6-sol", "medium")]))
        self.assertEqual(code, 2)
        self.assertIn("does not match", str(result["errors"]))

    def test_quick_team_preserves_contract_and_route_without_dispatch(self):
        units = [{"unit_id": f"U{i}", "role": "researcher", "goal": f"Check source {i}",
                  "output": f"Evidence {i}", "depends_on": [], "ownership": {"write": [], "forbidden": []},
                  "done_when": "Every claim has a supplied source", "task_intent": "inspect", "mutation_authority": "none"} for i in (1, 2)]
        team = {"schema_version": "1.0", "revision": 1, "supersedes_revision": None,
                "planning_source": "ad_hoc", "source_refs": [], "root_goal": "Check two independent sources",
                "scale_profile": "standard", "units": units, "reserved_slots": 0,
                "integration_owner": "lead", "integration_order": ["U1", "U2"],
                "final_verification": "Lead checks the cited evidence", "revision_reason": "initial"}
        payload = {"task_prefix": "test-luna", "team_plan": team, "routing": request()}
        result = prepare(payload)
        self.assertFalse(result["auto_dispatch"])
        for worker in result["ledger"]["workers"]:
            self.assertEqual(worker["requested_model"], "gpt-6-luna")
            self.assertEqual(worker["thinking"], "xhigh")
            self.assertEqual(worker["route_plan"]["task_contract"], payload["routing"]["task_contract"])
            self.assertEqual(worker["observed_runtime_model"], "unknown")
        payload["routing"]["task_contract"]["acceptance"] = ""
        with self.assertRaisesRegex(ValueError, "task_contract.acceptance"):
            prepare(payload)


if __name__ == "__main__":
    unittest.main()
