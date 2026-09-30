#!/usr/bin/env python3
"""Prepare a native team with existing validators; never dispatch workers."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from compile_route_plan import DEFAULT_REGISTRY, DEFAULT_VALIDATOR, compile_request, load_json
from validate_team_plan import validate_team_plan_payload


def prepare(payload: dict) -> dict:
    """One shared route is enough when every unit has the same workload/risk."""
    if not isinstance(payload, dict):
        raise ValueError("input must be an object")
    team = payload.get("team_plan")
    registry = json.loads(DEFAULT_REGISTRY.read_text(encoding="utf-8"))
    validation = validate_team_plan_payload(team, registry)
    if not validation["team_plan_valid"]:
        raise ValueError("; ".join(validation["errors"]))
    if team["scale_profile"] != "standard" or team["revision"] != 1:
        raise ValueError("quick path accepts only a new standard team; use the full workflow otherwise")
    prefix = payload.get("task_prefix")
    if not isinstance(prefix, str) or not prefix.strip() or len(prefix) > 110:
        raise ValueError("task_prefix must be a non-empty string of at most 110 characters")
    code, compiled = compile_request(
        payload.get("routing"), registry_path=DEFAULT_REGISTRY, validator_path=DEFAULT_VALIDATOR
    )
    if code or not compiled["dispatch"]["ready"]:
        raise ValueError("; ".join(compiled["errors"]) or "routing requires review")
    route = compiled["route_plan"]
    candidates = route["candidates"]
    if any(c["surface"] != "native_subagent" or c["speed"] != "standard" for c in candidates):
        raise ValueError("quick path accepts only native Standard routes")
    primary = candidates[0]
    workers = []
    for attempt, unit in enumerate(team["units"], 1):
        intent, authority = unit.get("task_intent"), unit.get("mutation_authority")
        allowed = {"inspect": {"none"}, "verify": {"none"}, "mutate": {"declared-output-only", "declared-workspace"}}
        if intent not in allowed or authority not in allowed[intent]:
            raise ValueError(f"{unit['unit_id']}: declare task_intent and matching mutation_authority")
        workers.append({
            "worker_attempt": attempt, "subtask_attempt": 1,
            "task_id": f"{prefix}:{unit['unit_id']}", "unit_id": unit["unit_id"],
            "team_plan_revision": 1, "surface": "native_subagent", "agent_id": None,
            "control_state": "PLANNED", "agent_status": None, "last_observed_at": None,
            "fork_mode": "fresh" if primary["fork_turns"] == "none" else "recent",
            "fork_turns": primary["fork_turns"], "role": unit["role"],
            "model": primary["model"], "requested_model": primary["model"],
            "platform_accepted_model": None, "observed_runtime_model": "unknown",
            "thinking": primary["thinking"], "requested_speed": "standard",
            "platform_accepted_speed": None, "observed_runtime_speed": "unknown",
            "route_plan": copy.deepcopy(route),
            "provider_policy": {k: copy.deepcopy(route[k]) for k in (
                "provider_allowlist", "provider_status", "data_allowed_providers")},
            "task_intent": intent, "mutation_authority": authority,
            "status": "planned", "output": None, "adopted": False,
            "fallback_reason": None, "closed": False, "released": False, "release_method": None,
        })
    return {
        "status": "prepared", "auto_dispatch": False,
        "dispatch_waves": validation["dispatch_waves"],
        "dispatch_candidates": compiled["dispatch"]["candidates"],
        "warnings": compiled["warnings"],
        "ledger": {"team_plans": [team], "active_team_plan_revision": 1, "workers": workers},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="-", help="JSON input path, or - for stdin")
    parser.add_argument("--output", type=Path, help="save prepared data locally and print only a compact receipt")
    args = parser.parse_args()
    try:
        result = prepare(load_json(args.input))
        if args.output:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            result = {"status": "prepared", "auto_dispatch": False, "output": str(args.output),
                      "worker_count": len(result["ledger"]["workers"]), "dispatch_waves": result["dispatch_waves"],
                      "dispatch_candidates": result["dispatch_candidates"], "warnings": result["warnings"]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "fail", "auto_dispatch": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
