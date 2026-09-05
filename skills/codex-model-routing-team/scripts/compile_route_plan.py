#!/usr/bin/env python3
"""Compile a compact routing request into a validated RoutePlan.

The compiler is deliberately a pure planning helper.  It reads JSON, copies
caller supplied live evidence, invokes the existing RoutePlan validator, and
returns dispatch arguments for inspection.  It never creates a Worker or an
App Thread.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = SKILL_ROOT / "references" / "model-registry.json"
DEFAULT_VALIDATOR = SKILL_ROOT / "scripts" / "validate_route_plan.py"
EVIDENCE_TTL = timedelta(minutes=10)
KNOWN_SURFACES = {"native_subagent", "app_thread"}


def load_json(source: str) -> Any:
    if source == "-":
        return json.load(sys.stdin)
    return json.loads(Path(source).read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compile compact routing JSON into a validated RoutePlan; "
            "the command never dispatches a Worker."
        )
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="compact routing JSON path, or - (the default) for stdin",
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--validator", type=Path, default=DEFAULT_VALIDATOR)
    return parser.parse_args()


def result_template() -> dict[str, Any]:
    return {
        "status": "fail",
        "compiled": False,
        "selected_profile": None,
        "warnings": [],
        "errors": [],
        "route_plan": None,
        "dispatch": {
            "auto_dispatch": False,
            "ready": False,
            "candidates": [],
        },
        "validation": None,
    }


def add_error(result: dict[str, Any], message: str) -> None:
    result["errors"].append(message)


def add_warning(result: dict[str, Any], message: str) -> None:
    result["warnings"].append(message)


def route_selection(
    policy: dict[str, Any], request: dict[str, Any], result: dict[str, Any]
) -> str | None:
    selection = policy.get("route_selection")
    if not isinstance(selection, dict):
        selection = {}

    explicit = request.get("route_profile")
    if explicit is not None:
        if not isinstance(explicit, str) or not explicit.strip():
            add_error(result, "route_profile must be a non-empty string")
            return None
        return explicit

    workload = request.get("workload", request.get("task_shape", "routine"))
    risk = request.get("risk", "normal")
    if not isinstance(workload, str) or not workload.strip():
        add_error(result, "workload must be a non-empty string")
        return None
    if not isinstance(risk, str) or not risk.strip():
        add_error(result, "risk must be a non-empty string")
        return None

    risk_overrides = selection.get("risk_overrides", {})
    workload_profiles = selection.get("workload_profiles", {})
    if not isinstance(risk_overrides, dict):
        risk_overrides = {}
    if not isinstance(workload_profiles, dict):
        workload_profiles = {}

    if risk in risk_overrides:
        profile = risk_overrides[risk]
    elif workload in workload_profiles:
        profile = workload_profiles[workload]
    else:
        profile = selection.get("default_profile", "default")
        if workload not in {"routine", "default"}:
            add_error(
                result,
                f"workload {workload!r} has no registry route profile",
            )
            return None

    if not isinstance(profile, str) or not profile.strip():
        add_error(result, "registry route selection returned an invalid profile")
        return None
    return profile


def profile_routes(
    policy: dict[str, Any], profile: str, result: dict[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    """Resolve a registry profile without naming a model in code."""
    profiles = policy.get("openai_route_profiles")
    profile_spec = profiles.get(profile) if isinstance(profiles, dict) else None
    if profiles is not None and not isinstance(profiles, dict):
        add_error(result, "registry openai_route_profiles must be an object")
        return None, None, None

    if isinstance(profile_spec, dict):
        route_ref = profile_spec.get("route_ref")
        if not isinstance(route_ref, str):
            add_error(result, f"registry profile {profile!r} lacks route_ref")
            return None, None, None
        primary = policy.get(route_ref)
        if not isinstance(primary, dict):
            add_error(result, f"registry route {route_ref!r} is missing")
            return None, None, None
        fallback_ref = profile_spec.get("fallback_ref")
        fallback: dict[str, Any] | None = None
        if fallback_ref is not None:
            if not isinstance(fallback_ref, str):
                add_error(result, f"registry profile {profile!r} has invalid fallback_ref")
                return None, None, None
            fallback_value = policy.get(fallback_ref)
            if not isinstance(fallback_value, dict):
                add_error(result, f"registry fallback route {fallback_ref!r} is missing")
                return None, None, None
            fallback = fallback_value
        minimum = profile_spec.get("minimum_thinking")
        if not isinstance(minimum, str):
            add_error(result, f"registry profile {profile!r} lacks minimum_thinking")
            return None, None, None
        return copy.deepcopy(primary), copy.deepcopy(fallback), minimum

    # Compatibility for a registry that predates route profiles.  The route
    # objects still come from the registry; this fallback never names a model.
    if profiles is None:
        if profile in {"high_risk", "critical"}:
            primary = policy.get("high_risk_openai_route")
        else:
            primary = policy.get("default_openai_route")
        if isinstance(primary, dict):
            minimum = primary.get("thinking")
            if isinstance(minimum, str):
                return copy.deepcopy(primary), None, minimum
        add_error(result, f"registry has no route for profile {profile!r}")
        return None, None, None

    add_error(result, f"unknown registry route profile {profile!r}")
    return None, None, None


def route_from_request(
    value: Any,
    *,
    policy: dict[str, Any],
    result: dict[str, Any],
    label: str,
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        add_error(result, f"{label} must be an object")
        return None
    nested = value.get("route")
    if nested is not None:
        if not isinstance(nested, dict):
            add_error(result, f"{label}.route must be an object")
            return None
        route = copy.deepcopy(nested)
        for key in ("surface", "model", "thinking", "speed", "fork_turns"):
            if key in value:
                route[key] = copy.deepcopy(value[key])
    else:
        route = {
            key: copy.deepcopy(value[key])
            for key in ("surface", "model", "thinking", "speed", "fork_turns")
            if key in value
        }
    for key in ("runtime_evidence", "speed_evidence", "live_evidence", "surface_evidence"):
        if key in value:
            route[key] = copy.deepcopy(value[key])
    if not route:
        add_error(result, f"{label} must declare at least one route field")
        return None
    return route


def candidate_evidence(
    request: dict[str, Any], route: dict[str, Any], index: int, surface: str
) -> Any:
    for key in (
        "runtime_evidence" if surface == "native_subagent" else "speed_evidence",
        "live_evidence",
        "surface_evidence",
    ):
        if key in route:
            value = route[key]
            if isinstance(value, dict) and key == "live_evidence":
                for nested_key in (
                    "runtime_evidence",
                    "speed_evidence",
                    "surface_evidence",
                ):
                    if nested_key in value:
                        return copy.deepcopy(value[nested_key])
            return copy.deepcopy(value)

    source: Any = None
    for key in ("live_evidence", "runtime_evidence", "speed_evidence"):
        if key in request:
            source = request[key]
            break
    if isinstance(source, list):
        if index < len(source):
            source = source[index]
        else:
            return None
    elif isinstance(source, dict):
        if str(index) in source:
            source = source[str(index)]
        elif index == 0 and "primary" in source:
            source = source["primary"]
        elif index == 1 and "fallback" in source:
            source = source["fallback"]
        elif "candidates" in source and isinstance(source["candidates"], list):
            values = source["candidates"]
            source = values[index] if index < len(values) else None
        elif "kind" not in source:
            return None

    if isinstance(source, dict):
        for nested_key in (
            "runtime_evidence",
            "speed_evidence",
            "surface_evidence",
        ):
            if nested_key in source:
                source = source[nested_key]
                break
    return copy.deepcopy(source)


def explicit_surface(request: dict[str, Any], route: dict[str, Any]) -> Any:
    if "surface" in route:
        return route["surface"]
    if isinstance(request.get("surface"), str):
        return request["surface"]
    return None


def apply_request_overrides(
    route: dict[str, Any], request: dict[str, Any], *, from_explicit_routes: bool
) -> dict[str, Any]:
    route = copy.deepcopy(route)
    if from_explicit_routes:
        return route
    for key in ("surface", "model", "thinking", "speed", "fork_turns"):
        if key in request:
            route[key] = copy.deepcopy(request[key])
    context = request.get("context")
    if isinstance(context, dict) and "fork_turns" in context:
        route["fork_turns"] = copy.deepcopy(context["fork_turns"])
    return route


def fast_fields_present(evidence: Any) -> bool:
    return isinstance(evidence, dict) and (
        evidence.get("speed") == "fast"
        or evidence.get("service_tier") == "priority"
    )


def fast_evidence_complete(evidence: Any) -> bool:
    return isinstance(evidence, dict) and (
        evidence.get("speed") == "fast"
        and evidence.get("service_tier") == "priority"
    )


def prepare_candidate(
    route: dict[str, Any],
    *,
    request: dict[str, Any],
    policy: dict[str, Any],
    index: int,
    result: dict[str, Any],
) -> dict[str, Any] | None:
    candidate = copy.deepcopy(route)
    surface = candidate.get("surface", policy.get("default_surface"))
    model = candidate.get("model")
    thinking = candidate.get("thinking")
    speed = candidate.get("speed", policy.get("default_speed", "standard"))
    if surface not in KNOWN_SURFACES:
        add_error(result, f"candidate {index} uses an unknown execution surface")
        return None
    if not isinstance(model, str) or not model:
        add_error(result, f"candidate {index} lacks model")
        return None
    if not isinstance(thinking, str) or not thinking:
        add_error(result, f"candidate {index} lacks thinking")
        return None
    if not isinstance(speed, str):
        add_error(result, f"candidate {index} speed must be a string")
        return None
    candidate["surface"] = surface
    candidate["model"] = model
    candidate["thinking"] = thinking
    candidate["speed"] = speed

    evidence = candidate_evidence(request, candidate, index, surface)
    if speed == "fast":
        fast_models = set(policy.get("fast_routing_models", []))
        explicit_required = set(policy.get("fast_requires_explicit_models", []))
        can_request_fast = model in fast_models and not (
            model in explicit_required
            and request.get("explicit_user_request") is not True
        )
        if not can_request_fast and not fast_fields_present(evidence):
            candidate["speed"] = "standard"
            speed = "standard"
            add_warning(
                result,
                f"candidate {index} Fast request downgraded to Standard by registry authorization policy",
            )
        elif not fast_evidence_complete(evidence):
            candidate["speed"] = "standard"
            speed = "standard"
            if fast_fields_present(evidence):
                # Keep the incomplete Fast request visible so the existing
                # validator rejects the exact tuple instead of silently
                # rewriting caller supplied evidence.
                candidate["speed"] = "fast"
            else:
                add_warning(
                    result,
                    f"candidate {index} Fast request downgraded to Standard because live priority evidence is absent",
                )

    if surface == "native_subagent":
        if "fork_turns" not in candidate:
            candidate["fork_turns"] = "none"
        candidate["runtime_evidence"] = evidence
        for key in ("speed_evidence", "live_evidence", "surface_evidence"):
            candidate.pop(key, None)
    else:
        if "fork_turns" in candidate:
            add_error(result, f"candidate {index} App Thread route must not declare fork_turns")
        candidate.pop("fork_turns", None)
        for key in ("runtime_evidence", "live_evidence"):
            candidate.pop(key, None)
        candidate["surface_evidence"] = evidence
        if speed == "fast":
            candidate["speed_evidence"] = evidence
        else:
            candidate.pop("speed_evidence", None)

    return candidate


def parse_checked_at(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def validate_app_evidence(
    candidate: dict[str, Any], index: int, result: dict[str, Any]
) -> None:
    evidence = candidate.get("surface_evidence")
    if not isinstance(evidence, dict):
        add_error(
            result,
            f"candidate {index} app_thread requires live_evidence with accepted=true",
        )
        return
    expected = {
        "kind": "live_create_schema",
        "surface": "app_thread",
        "model": candidate.get("model"),
        "thinking": candidate.get("thinking"),
    }
    for key, value in expected.items():
        if evidence.get(key) != value:
            add_error(result, f"candidate {index} App live evidence does not match {key}")
    if evidence.get("accepted") is not True:
        add_error(result, f"candidate {index} App live evidence is not accepted by the host")
    if not isinstance(evidence.get("host"), str) or not evidence["host"].strip():
        add_error(result, f"candidate {index} App live evidence lacks a host identity")
    checked = parse_checked_at(evidence.get("checked_at"))
    if checked is None:
        add_error(result, f"candidate {index} App live evidence has an invalid checked_at")
    else:
        age = datetime.now(timezone.utc) - checked
        if age > EVIDENCE_TTL:
            add_error(result, f"candidate {index} App live evidence is stale")
        elif age < -timedelta(minutes=1):
            add_error(result, f"candidate {index} App live evidence is dated in the future")
    if candidate.get("speed") == "standard" and fast_fields_present(evidence):
        add_error(
            result,
            f"candidate {index} Standard App live evidence contains mismatched Fast fields",
        )


def validate_native_evidence(
    candidate: dict[str, Any], index: int, result: dict[str, Any]
) -> None:
    evidence = candidate.get("runtime_evidence")
    if isinstance(evidence, dict) and evidence.get("accepted") is not True:
        add_error(
            result,
            f"candidate {index} native live evidence must explicitly contain accepted=true",
        )


def validate_host_authorization(
    candidates: list[dict[str, Any]], request: dict[str, Any], result: dict[str, Any]
) -> None:
    """Require authorization separately from the App create schema."""
    app_candidates = [
        candidate for candidate in candidates if candidate.get("surface") == "app_thread"
    ]
    if not app_candidates:
        return
    authorization = request.get("host_authorization")
    if not isinstance(authorization, dict):
        add_error(
            result,
            "app_thread requires host_authorization in addition to live schema evidence",
        )
        return
    if authorization.get("surface") != "app_thread":
        add_error(result, "host_authorization must target app_thread")
    if authorization.get("authorized") is not True:
        add_error(result, "host_authorization is not explicitly authorized")
    auth_host = authorization.get("host")
    if not isinstance(auth_host, str) or not auth_host.strip():
        add_error(result, "host_authorization lacks a host identity")
    auth_source = authorization.get("source")
    if not isinstance(auth_source, str) or not auth_source.strip():
        add_error(result, "host_authorization lacks an authorization source")
    auth_checked = parse_checked_at(authorization.get("checked_at"))
    if auth_checked is None:
        add_error(result, "host_authorization has an invalid checked_at")
    else:
        age = datetime.now(timezone.utc) - auth_checked
        if age > EVIDENCE_TTL:
            add_error(result, "host_authorization is stale")
        elif age < -timedelta(minutes=1):
            add_error(result, "host_authorization is dated in the future")
    if isinstance(auth_host, str) and auth_host.strip():
        for index, candidate in enumerate(app_candidates):
            evidence = candidate.get("surface_evidence")
            if isinstance(evidence, dict) and evidence.get("host") != auth_host:
                add_error(result, f"candidate {index} App evidence host differs from host_authorization")


def build_routes(
    request: dict[str, Any],
    *,
    policy: dict[str, Any],
    profile: str,
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    explicit_routes = request.get("routes")
    routes: list[dict[str, Any]] = []
    if explicit_routes is not None:
        if not isinstance(explicit_routes, list) or not 1 <= len(explicit_routes) <= 2:
            add_error(result, "routes must contain one or two ordered entries")
            return routes
        for index, value in enumerate(explicit_routes):
            route = route_from_request(
                value,
                policy=policy,
                result=result,
                label=f"routes[{index}]",
            )
            if route is not None:
                routes.append(route)
        return routes

    primary, registry_fallback, _minimum = profile_routes(policy, profile, result)
    if primary is None:
        return routes
    routes.append(apply_request_overrides(primary, request, from_explicit_routes=False))

    include_fallback = request.get("include_fallback", True)
    if not isinstance(include_fallback, bool):
        add_error(result, "include_fallback must be a boolean")
        return routes

    fallback_value: Any = request.get("fallback_route")
    if fallback_value is None and "fallback" in request:
        fallback_value = request["fallback"]
    if fallback_value is False:
        include_fallback = False
    elif fallback_value not in (None, True):
        if isinstance(fallback_value, str):
            fallback_profile = fallback_value
            fallback_primary, _unused, _minimum = profile_routes(
                policy, fallback_profile, result
            )
            if fallback_primary is not None:
                routes.append(
                    apply_request_overrides(
                        fallback_primary, request, from_explicit_routes=False
                    )
                )
            include_fallback = False
        elif isinstance(fallback_value, list):
            for index, value in enumerate(fallback_value):
                route = route_from_request(
                    value,
                    policy=policy,
                    result=result,
                    label=f"fallback[{index}]",
                )
                if route is not None:
                    routes.append(route)
            include_fallback = False
        else:
            route = route_from_request(
                fallback_value,
                policy=policy,
                result=result,
                label="fallback",
            )
            if route is not None:
                routes.append(route)
            include_fallback = False

    if include_fallback and registry_fallback is not None:
        routes.append(
            apply_request_overrides(registry_fallback, request, from_explicit_routes=False)
        )
    # A durable intent is an explicit Surface choice.  Adapt registry route
    # objects that were authored for native execution while preserving their
    # model, thinking, speed, and candidate order.  The live App evidence gate
    # below still decides whether the route is usable.
    if request.get("surface_intent") == "durable_app":
        for route in routes:
            route["surface"] = "app_thread"
            route.pop("fork_turns", None)
    if len(routes) > 2:
        add_error(result, "candidate chain must contain at most two entries")
        return routes[:2]
    return routes


def provider_fields(request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key in ("provider_allowlist", "provider_status", "data_allowed_providers"):
        if key in request:
            fields[key] = copy.deepcopy(request[key])
        else:
            # Leave the field empty so the existing validator reports the
            # precise contract failure.  The compiler never widens a data
            # boundary from registry metadata.
            fields[key] = [] if key != "provider_status" else {}
            add_error(result, f"{key} must be supplied by the caller")
    return fields


def profile_minimum(policy: dict[str, Any], profile: str) -> str | None:
    profiles = policy.get("openai_route_profiles")
    if isinstance(profiles, dict):
        spec = profiles.get(profile)
        if isinstance(spec, dict) and isinstance(spec.get("minimum_thinking"), str):
            return spec["minimum_thinking"]
    return None


def build_plan(
    request: dict[str, Any],
    *,
    registry: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any] | None:
    policy = registry.get("policy")
    if not isinstance(policy, dict):
        add_error(result, "registry policy must be an object")
        return None

    profile = route_selection(policy, request, result)
    result["selected_profile"] = profile
    if profile is None:
        return None
    routes = build_routes(request, policy=policy, profile=profile, result=result)
    if not routes:
        return None

    candidates: list[dict[str, Any]] = []
    for index, route in enumerate(routes):
        candidate = prepare_candidate(
            route,
            request=request,
            policy=policy,
            index=index,
            result=result,
        )
        if candidate is not None:
            if candidate["surface"] == "app_thread":
                validate_app_evidence(candidate, index, result)
            else:
                validate_native_evidence(candidate, index, result)
            candidates.append(candidate)

    if not candidates:
        return None

    profiles = policy.get("openai_route_profiles")
    spec = profiles.get(profile) if isinstance(profiles, dict) else None
    minimum = spec.get("minimum_thinking") if isinstance(spec, dict) else None
    if not isinstance(minimum, str):
        minimum = request.get("minimum_thinking")
    if not isinstance(minimum, str):
        minimum = candidates[0].get("thinking")

    risk = request.get("risk", "normal")
    selection = policy.get("route_selection")
    risk_overrides = selection.get("risk_overrides", {}) if isinstance(selection, dict) else {}
    risk_profile = risk_overrides.get(risk) if isinstance(risk_overrides, dict) else None
    risk_minimum = (
        profile_minimum(policy, risk_profile)
        if isinstance(risk_profile, str)
        else None
    )
    thinking_order = policy.get("thinking_order", [])
    rank = {value: index for index, value in enumerate(thinking_order)}
    if isinstance(risk_minimum, str) and risk_minimum in rank:
        for index, candidate in enumerate(candidates):
            thinking = candidate.get("thinking")
            if thinking not in rank or rank[thinking] < rank[risk_minimum]:
                add_error(
                    result,
                    f"candidate {index} falls below risk {risk!r} minimum_thinking {risk_minimum}",
                )
        if isinstance(minimum, str) and (
            minimum not in rank or rank[minimum] < rank[risk_minimum]
        ):
            add_error(
                result,
                f"risk {risk!r} requires minimum_thinking {risk_minimum}",
            )

    schema_version = request.get(
        "schema_version",
        policy.get("current_route_plan_schema_version", "3.0"),
    )
    surface_intent = request.get("surface_intent")
    if surface_intent is None:
        surface_intent = (
            "durable_app"
            if all(c.get("surface") == "app_thread" for c in candidates)
            else "parent_integrated"
        )

    plan: dict[str, Any] = {
        "schema_version": schema_version,
        "surface_intent": surface_intent,
        "task_class": request.get("task_class", profile),
        "workload": request.get("workload", request.get("task_shape", "routine")),
        "risk": request.get("risk", "normal"),
        "route_profile": profile,
        "minimum_thinking": minimum,
        **provider_fields(request, result),
        "explicit_user_request": request.get("explicit_user_request", False),
        "risk_acknowledged": request.get("risk_acknowledged", False),
        "candidates": candidates,
        "max_worker_threads": len(candidates),
        "max_followups_per_thread": request.get("max_followups_per_thread", 1),
    }
    if "host_authorization" in request:
        plan["host_authorization"] = copy.deepcopy(request["host_authorization"])
    validate_host_authorization(candidates, request, result)
    return plan


def validate_plan(
    plan: dict[str, Any], *, validator: Path, registry: Path
) -> tuple[int, dict[str, Any] | None, str | None]:
    try:
        completed = subprocess.run(
            [sys.executable, str(validator), "-", "--registry", str(registry)],
            input=json.dumps(plan, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return 2, None, f"RoutePlan validator could not run: {exc}"
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        detail = completed.stderr.strip() or completed.stdout.strip()
        return (
            2,
            None,
            f"RoutePlan validator returned invalid JSON{': ' + detail if detail else ''}",
        )
    return completed.returncode, payload, None


def dispatch_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    surface = candidate.get("surface")
    args: dict[str, Any] = {
        "surface": surface,
        "model": candidate.get("model"),
        "speed": candidate.get("speed"),
    }
    if surface == "native_subagent":
        args["reasoning_effort"] = candidate.get("thinking")
        args["fork_turns"] = candidate.get("fork_turns")
        evidence = candidate.get("runtime_evidence")
    else:
        args["thinking"] = candidate.get("thinking")
        evidence = candidate.get("speed_evidence")
    if candidate.get("speed") == "fast" and isinstance(evidence, dict):
        service_tier = evidence.get("service_tier")
        if isinstance(service_tier, str) and service_tier:
            args["service_tier"] = service_tier
    return args


def compile_request(
    request: Any, *, registry_path: Path, validator_path: Path
) -> tuple[int, dict[str, Any]]:
    result = result_template()
    if not isinstance(request, dict):
        add_error(result, "compact routing input must be a JSON object")
        return 2, result
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        add_error(result, f"registry load failed: {exc}")
        return 2, result
    if not isinstance(registry, dict):
        add_error(result, "registry must be a JSON object")
        return 2, result

    plan = build_plan(request, registry=registry, result=result)
    if plan is None:
        return 2, result
    result["route_plan"] = plan
    result["compiled"] = True
    result["dispatch"]["candidates"] = [
        dispatch_candidate(candidate) for candidate in plan["candidates"]
    ]

    validator_code, validation, validator_error = validate_plan(
        plan, validator=validator_path, registry=registry_path
    )
    if validator_error is not None:
        add_error(result, validator_error)
        return 2, result
    result["validation"] = validation
    if validation is not None:
        result["errors"].extend(validation.get("errors", []))
        result["warnings"].extend(validation.get("warnings", []))
    if result["errors"]:
        result["status"] = "fail"
        return 2, result
    if validator_code == 3:
        result["status"] = "manual_review"
        return 3, result
    if validator_code != 0:
        result["status"] = "fail"
        return 2, result
    result["status"] = "pass"
    result["dispatch"]["ready"] = bool(
        isinstance(validation, dict) and validation.get("route_ready") is True
    )
    return 0, result


def main() -> int:
    args = parse_args()
    result = result_template()
    try:
        request = load_json(args.input)
    except (OSError, json.JSONDecodeError) as exc:
        add_error(result, f"compact input load failed: {exc}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    code, result = compile_request(
        request,
        registry_path=args.registry,
        validator_path=args.validator,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
