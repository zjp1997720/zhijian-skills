#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from route_policy import KNOWN_SURFACES, runtime_model_id, supported_thinking, version_tuple


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = SKILL_ROOT / "references" / "model-registry.json"
RUNTIME_EVIDENCE_TTL = timedelta(minutes=10)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_input(source: str) -> Any:
    if source == "-":
        return json.load(sys.stdin)
    return load_json(Path(source))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a concrete RoutePlan against model, thinking, speed, provider, and retry policies."
    )
    parser.add_argument("plan", help="RoutePlan JSON path, or - to read JSON from stdin")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    return parser.parse_args()


def valid_runtime_evidence(
    evidence: Any,
    *,
    model: str,
    thinking: str,
    speed: str,
    strict_speed: bool,
    runtime_model: str,
    tool_probe_required: bool,
    minimum_proxy_version: str | None,
    now: datetime,
) -> tuple[bool, str | None]:
    if not isinstance(evidence, dict):
        return False, "native route requires tuple-bound live runtime evidence"
    expected = {
        "kind": "live_spawn_schema",
        "surface": "native_subagent",
        "model": model,
        "runtime_model": runtime_model,
        "thinking": thinking,
    }
    if strict_speed or speed == "fast":
        expected["speed"] = speed
        expected["service_tier"] = None if runtime_model != model else (
            "priority" if speed == "fast" else None
        )
    if (
        any(evidence.get(key) != value for key, value in expected.items())
        or evidence.get("accepted") is not True
    ):
        return False, "native runtime evidence does not match the candidate tuple"
    host = evidence.get("host")
    if not isinstance(host, str) or not host.strip():
        return False, "native runtime evidence lacks a host identity"
    checked_at = evidence.get("checked_at")
    if not isinstance(checked_at, str):
        return False, "native runtime evidence has an invalid checked_at"
    try:
        checked = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
    except ValueError:
        return False, "native runtime evidence has an invalid checked_at"
    if checked.tzinfo is None:
        return False, "native runtime evidence has an invalid checked_at"
    age = now - checked.astimezone(timezone.utc)
    if age > RUNTIME_EVIDENCE_TTL:
        return False, "native runtime evidence is stale"
    if age < -timedelta(minutes=1):
        return False, "native runtime evidence is dated in the future"
    if tool_probe_required:
        tool_probe = evidence.get("tool_probe")
        if not isinstance(tool_probe, dict) or tool_probe.get("kind") != "codex_tool_sequence":
            return False, "native runtime evidence lacks the required Codex tool-sequence probe"
        if tool_probe.get("accepted") is not True:
            return False, "required Codex tool-sequence probe did not pass"
        if tool_probe.get("minimum_proxy_version") != minimum_proxy_version:
            return False, "Codex tool-sequence probe uses the wrong proxy compatibility floor"
        actual_version = version_tuple(tool_probe.get("proxy_version"))
        minimum_version = version_tuple(minimum_proxy_version)
        if actual_version is None or minimum_version is None or actual_version < minimum_version:
            return False, "Codex tool-sequence probe uses an incompatible proxy version"
    return True, None


def valid_app_speed_evidence(
    evidence: Any,
    *,
    model: str,
    thinking: str,
    now: datetime,
) -> tuple[bool, str | None]:
    if not isinstance(evidence, dict):
        return False, "App Fast route requires tuple-bound live speed evidence"
    expected = {
        "kind": "live_create_schema",
        "surface": "app_thread",
        "model": model,
        "thinking": thinking,
        "speed": "fast",
        "service_tier": "priority",
    }
    if (
        any(evidence.get(key) != value for key, value in expected.items())
        or evidence.get("accepted") is not True
    ):
        return False, "App Fast evidence does not match the candidate tuple"
    host = evidence.get("host")
    if not isinstance(host, str) or not host.strip():
        return False, "App Fast evidence lacks a host identity"
    checked_at = evidence.get("checked_at")
    if not isinstance(checked_at, str):
        return False, "App Fast evidence has an invalid checked_at"
    try:
        checked = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
    except ValueError:
        return False, "App Fast evidence has an invalid checked_at"
    if checked.tzinfo is None:
        return False, "App Fast evidence has an invalid checked_at"
    age = now - checked.astimezone(timezone.utc)
    if age > RUNTIME_EVIDENCE_TTL:
        return False, "App Fast evidence is stale"
    if age < -timedelta(minutes=1):
        return False, "App Fast evidence is dated in the future"
    return True, None


def main() -> int:
    args = parse_args()
    result: dict[str, Any] = {
        "plan": str(args.plan),
        "status": "fail",
        "route_ready": False,
        "errors": [],
        "warnings": [],
        "candidates": [],
    }
    try:
        plan = load_input(args.plan)
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
    speed_modes = set(registry.get("policy", {}).get("speed_modes", []))
    default_speed = registry.get("policy", {}).get("default_speed", "standard")
    fast_routing_models = set(registry.get("policy", {}).get("fast_routing_models", []))
    default_fast_models = set(
        registry.get("policy", {}).get("default_fast_models", [])
    )
    app_thread_only_models = set(
        registry.get("policy", {}).get("app_thread_only_models", [])
    )
    native_first_requires_explicit = registry.get("policy", {}).get(
        "native_first_candidate_requires_explicit_request", True
    )
    current_schema_version = registry.get("policy", {}).get(
        "current_route_plan_schema_version", "2.1"
    )
    plan_schema_version = plan.get("schema_version")
    strict_route_plan = plan_schema_version == current_schema_version
    if plan_schema_version is not None and not strict_route_plan:
        result["errors"].append("schema_version is unsupported")
    result["schema_version"] = plan_schema_version or "legacy"

    for field in ("explicit_user_request", "risk_acknowledged"):
        if not isinstance(plan.get(field), bool):
            result["errors"].append(f"{field} must be a boolean")

    minimum = plan.get("minimum_thinking")
    if minimum not in rank:
        result["errors"].append("minimum_thinking is missing or unknown")
    candidates = plan.get("candidates")
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 2:
        result["errors"].append("candidates must contain one or two ordered entries")
        candidates = []
    max_worker_threads = plan.get("max_worker_threads")
    if not isinstance(max_worker_threads, int) or isinstance(max_worker_threads, bool) or not 1 <= max_worker_threads <= 2:
        result["errors"].append("max_worker_threads must be 1 or 2")
    elif candidates and max_worker_threads != len(candidates):
        result["errors"].append("max_worker_threads must match the declared candidate count")
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

    seen: set[tuple[str, str, str, str]] = set()
    now = datetime.now(timezone.utc)
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            result["errors"].append(f"candidate {index} must be an object")
            continue
        model_id = candidate.get("model")
        thinking = candidate.get("thinking")
        speed = candidate.get("speed", default_speed)
        surface = candidate.get("surface", "app_thread")
        if strict_route_plan and "surface" not in candidate:
            result["errors"].append(f"candidate {index} must declare surface")
        if strict_route_plan and "speed" not in candidate:
            result["errors"].append(f"candidate {index} must declare speed")
        if surface not in KNOWN_SURFACES:
            result["errors"].append(f"candidate {index} uses an unknown execution surface")
            continue
        if not isinstance(model_id, str) or model_id not in models:
            result["errors"].append(f"candidate {index} uses an unknown model")
            continue
        if not isinstance(speed, str) or speed not in speed_modes:
            result["errors"].append(f"candidate {index} uses an unknown speed")
            continue
        if speed == "fast" and model_id not in fast_routing_models:
            result["errors"].append(
                f"candidate {index} requests Fast for a registry-ineligible model"
            )
        if (
            speed == "fast"
            and model_id not in default_fast_models
            and plan.get("explicit_user_request") is not True
        ):
            result["errors"].append(
                f"candidate {index} non-default Fast requires explicit_user_request"
            )
        if surface == "native_subagent" and model_id in app_thread_only_models:
            result["errors"].append(
                f"candidate {index} model is App Thread only in the current routing policy"
            )
        if (
            surface == "native_subagent"
            and index == 0
            and native_first_requires_explicit
            and plan.get("explicit_user_request") is not True
        ):
            result["errors"].append(
                "native first candidate requires explicit_user_request; automatic routes default to App Thread"
            )
        entry = models[model_id]
        runtime_model = runtime_model_id(entry, surface, speed)
        if runtime_model is None:
            result["errors"].append(
                f"candidate {index} has no runtime model for this Surface and speed"
            )
            continue
        if "runtime_model" in candidate and candidate.get("runtime_model") != runtime_model:
            result["errors"].append(f"candidate {index} declares the wrong runtime model")
        surface_thinking = supported_thinking(entry, surface)
        if not isinstance(thinking, str) or thinking not in surface_thinking:
            result["errors"].append(f"candidate {index} uses unsupported thinking")
            continue
        runtime_evidence = candidate.get("runtime_evidence")
        speed_evidence = candidate.get("speed_evidence")
        if surface == "native_subagent":
            evidence_valid, evidence_error = valid_runtime_evidence(
                runtime_evidence,
                model=model_id,
                thinking=thinking,
                speed=speed,
                strict_speed=strict_route_plan,
                runtime_model=runtime_model,
                tool_probe_required=entry.get("tool_probe_required") is True,
                minimum_proxy_version=entry.get("minimum_proxy_version"),
                now=now,
            )
            if not evidence_valid:
                result["errors"].append(f"candidate {index} {evidence_error}")
        elif speed == "fast":
            evidence_valid, evidence_error = valid_app_speed_evidence(
                speed_evidence,
                model=model_id,
                thinking=thinking,
                now=now,
            )
            if not evidence_valid:
                result["errors"].append(f"candidate {index} {evidence_error}")
        if thinking in forbidden:
            result["errors"].append(f"candidate {index} uses forbidden thinking")
        if minimum in rank and rank.get(thinking, -1) < rank[minimum]:
            result["errors"].append(f"candidate {index} falls below minimum_thinking")
        key = (surface, model_id, thinking, speed)
        if key in seen:
            result["errors"].append("candidate chain contains a duplicate or loop")
        seen.add(key)
        result["candidates"].append(
            {
                "surface": surface,
                "model": model_id,
                "runtime_model": runtime_model,
                "thinking": thinking,
                "speed": speed,
                "runtime_evidence": runtime_evidence,
                "speed_evidence": speed_evidence,
            }
        )

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
            if plan.get("explicit_user_request") is not True:
                result["errors"].append("manual-only model requires explicit_user_request")
            if plan.get("risk_acknowledged") is not True:
                result["errors"].append("manual-only model requires risk_acknowledged")
        elif entry.get("status") == "opt_in":
            if index != 0:
                result["errors"].append("opt-in model cannot be a fallback candidate")
            if plan.get("explicit_user_request") is not True:
                result["errors"].append("opt-in model requires explicit_user_request")
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
