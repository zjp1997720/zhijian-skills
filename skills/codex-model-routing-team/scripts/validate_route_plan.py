#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = SKILL_ROOT / "references" / "model-registry.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a concrete RoutePlan against model, thinking, provider, and retry policies."
    )
    parser.add_argument("plan", type=Path)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result: dict[str, Any] = {
        "plan": str(args.plan),
        "status": "fail",
        "route_ready": False,
        "errors": [],
        "warnings": [],
    }
    try:
        plan = load_json(args.plan)
        registry = load_json(args.registry)
    except (OSError, json.JSONDecodeError) as exc:
        result["errors"].append(f"JSON load failed: {exc}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    if not isinstance(plan, dict) or not isinstance(registry, dict):
        result["errors"].append("plan and registry must be JSON objects")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    models = {
        item["id"]: item
        for item in registry.get("models", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    order = registry.get("policy", {}).get("thinking_order", [])
    rank = {name: index for index, name in enumerate(order)}
    forbidden = set(registry.get("policy", {}).get("forbidden_thinking", []))

    minimum = plan.get("minimum_thinking")
    if minimum not in rank:
        result["errors"].append("minimum_thinking is missing or unknown")
    candidates = plan.get("candidates")
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 2:
        result["errors"].append("candidates must contain one or two ordered entries")
        candidates = []
    if plan.get("max_worker_threads") != 2:
        result["errors"].append("max_worker_threads must equal 2")
    if plan.get("max_followups_per_thread") != 1:
        result["errors"].append("max_followups_per_thread must equal 1")

    allowlist = plan.get("provider_allowlist")
    if not isinstance(allowlist, list) or not all(isinstance(item, str) for item in allowlist):
        result["errors"].append("provider_allowlist must be a string array")
        allowlist = []
    provider_status = plan.get("provider_status")
    if not isinstance(provider_status, dict):
        result["errors"].append("provider_status must be an object")
        provider_status = {}
    data_allowed = plan.get("data_allowed_providers")
    if not isinstance(data_allowed, list) or not all(isinstance(item, str) for item in data_allowed):
        result["errors"].append("data_allowed_providers must be a string array")
        data_allowed = []

    seen: set[tuple[str, str]] = set()
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            result["errors"].append(f"candidate {index} must be an object")
            continue
        model_id = candidate.get("model")
        thinking = candidate.get("thinking")
        if not isinstance(model_id, str) or model_id not in models:
            result["errors"].append(f"candidate {index} uses an unknown model")
            continue
        entry = models[model_id]
        if not isinstance(thinking, str) or thinking not in entry.get("thinking", []):
            result["errors"].append(f"candidate {index} uses unsupported thinking")
            continue
        if thinking in forbidden:
            result["errors"].append(f"candidate {index} uses forbidden thinking")
        if minimum in rank and rank.get(thinking, -1) < rank[minimum]:
            result["errors"].append(f"candidate {index} falls below minimum_thinking")
        key = (model_id, thinking)
        if key in seen:
            result["errors"].append("candidate chain contains a duplicate or loop")
        seen.add(key)

        provider = entry.get("provider")
        if provider not in allowlist:
            result["errors"].append(f"candidate {index} provider is outside provider_allowlist")
        if provider not in data_allowed:
            result["errors"].append(f"candidate {index} provider is not approved for task data")
        terms = provider_status.get(provider, "unknown")
        if entry.get("terms_default") == "blocked":
            result["errors"].append(f"candidate {index} registry provider policy is blocked")
        elif terms == "blocked":
            result["errors"].append(f"candidate {index} provider policy is blocked")
        elif terms != "allowed":
            result["warnings"].append(f"candidate {index} provider requires manual review")

        if entry.get("status") == "manual_only":
            if index != 0:
                result["errors"].append("manual-only model cannot be a fallback candidate")
            if not plan.get("explicit_user_request"):
                result["errors"].append("manual-only model requires explicit_user_request")
            if not plan.get("risk_acknowledged"):
                result["errors"].append("manual-only model requires risk_acknowledged")
        elif not entry.get("automatic"):
            result["errors"].append(f"candidate {index} is disabled for automatic routing")

    if result["errors"]:
        result["status"] = "fail"
        exit_code = 2
    elif result["warnings"]:
        result["status"] = "manual_review"
        exit_code = 3
    else:
        result["status"] = "pass"
        result["route_ready"] = True
        exit_code = 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
