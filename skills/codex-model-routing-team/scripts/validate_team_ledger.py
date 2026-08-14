#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from validate_team_plan import validate_team_plan_payload
from route_policy import runtime_model_id


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = SKILL_ROOT / "references" / "audit-schema.json"
DEFAULT_NATIVE_SCHEMA = SKILL_ROOT / "references" / "native-audit-schema.json"
DEFAULT_REGISTRY = SKILL_ROOT / "references" / "model-registry.json"
FALLBACK_MAX_CREATION_ATTEMPTS = 8
FALLBACK_MAX_IN_FLIGHT = 6
CURRENT_ROUTE_PLAN_SCHEMA_VERSION = "2.1"
SPEED_MODES = {"standard", "fast"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_input(source: str) -> Any:
    if source == "-":
        return json.load(sys.stdin)
    return load_json(Path(source))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate deterministic invariants in a Codex model-routing team ledger."
    )
    parser.add_argument("ledger", help="ledger JSON path, or - to read JSON from stdin")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--native-schema", type=Path, default=DEFAULT_NATIVE_SCHEMA)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    return parser.parse_args()


def records_from(payload: Any) -> tuple[dict[str, Any] | None, list[Any]]:
    if isinstance(payload, list):
        return None, payload
    if isinstance(payload, dict) and isinstance(payload.get("workers"), list):
        return payload, payload["workers"]
    raise ValueError("ledger must be an array or an object with a workers array")


def valid_timestamp(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str) or not value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def record_is_in_flight(record: dict[str, Any]) -> bool:
    state = record.get("control_state")
    if record.get("surface", "app_thread") == "native_subagent":
        return state in {
            "PLANNED",
            "SPAWN_PENDING",
            "RUNNING",
            "COMPLETED",
            "UNKNOWN",
            "FAILED",
        }
    return state in {
        "PLANNED",
        "CREATION_PENDING",
        "CONTROL_READY",
        "DATA_READY",
        "UNKNOWN",
    }


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_speed_identity(
    record: dict[str, Any],
    *,
    prefix: str,
    accepted_states: set[str],
    fast_routing_models: set[str],
    default_fast_models: set[str],
    errors: list[str],
) -> None:
    route_plan = record.get("route_plan")
    route_plan_schema_version = (
        route_plan.get("schema_version") if isinstance(route_plan, dict) else None
    )
    if (
        route_plan_schema_version is not None
        and route_plan_schema_version != CURRENT_ROUTE_PLAN_SCHEMA_VERSION
    ):
        errors.append(f"{prefix} uses an unsupported RoutePlan schema_version")
    strict = (
        isinstance(route_plan, dict)
        and route_plan_schema_version == CURRENT_ROUTE_PLAN_SCHEMA_VERSION
    )
    fields = (
        "requested_speed",
        "platform_accepted_speed",
        "observed_runtime_speed",
    )
    if not strict and not any(field in record for field in fields):
        return
    if strict:
        missing = [field for field in fields if field not in record]
        if missing:
            errors.append(
                f"{prefix} is missing speed audit fields: {', '.join(missing)}"
            )

    requested = record.get("requested_speed")
    accepted = record.get("platform_accepted_speed")
    observed = record.get("observed_runtime_speed")
    if requested not in SPEED_MODES:
        errors.append(f"{prefix} has invalid requested_speed")
        return
    requested_model = record.get("requested_model")
    if requested == "fast" and requested_model not in fast_routing_models:
        errors.append(f"{prefix} requests Fast for a registry-ineligible model")
    if (
        requested == "fast"
        and requested_model not in default_fast_models
        and not (
            isinstance(route_plan, dict)
            and route_plan.get("explicit_user_request") is True
        )
    ):
        errors.append(f"{prefix} non-default Fast lacks explicit_user_request")
    if accepted is not None and accepted not in SPEED_MODES:
        errors.append(f"{prefix} has invalid platform_accepted_speed")
    if observed not in {None, "unknown", *SPEED_MODES}:
        errors.append(f"{prefix} has invalid observed_runtime_speed")
    if record.get("control_state") in accepted_states and accepted != requested:
        errors.append(f"{prefix} accepted speed mismatch")
    if observed not in {None, "unknown", requested}:
        errors.append(f"{prefix} observed speed mismatch")

    if strict and isinstance(route_plan, dict):
        candidates = route_plan.get("candidates")
        selected = (
            isinstance(candidates, list)
            and any(
                isinstance(candidate, dict)
                and candidate.get("surface", "app_thread")
                == record.get("surface", "app_thread")
                and candidate.get("model") == record.get("requested_model")
                and candidate.get("thinking") == record.get("thinking")
                and candidate.get("speed") == requested
                for candidate in candidates
            )
        )
        if not selected:
            errors.append(f"{prefix} speed identity does not match RoutePlan")


def main() -> int:
    args = parse_args()
    result: dict[str, Any] = {
        "ledger": str(args.ledger),
        "status": "fail",
        "ledger_valid": False,
        "record_count": 0,
        "in_flight_count": 0,
        "scale_profile": "standard",
        "limits": {},
        "errors": [],
        "warnings": [],
    }
    try:
        payload = load_input(args.ledger)
        root, records = records_from(payload)
        registry = load_json(args.registry)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result["errors"].append(f"JSON load failed: {exc}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    policy = registry.get("policy", {}) if isinstance(registry, dict) else {}
    registry_models = {
        item["id"]: item
        for item in registry.get("models", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    default_profile = policy.get("default_team_limit_profile", "standard")
    profiles = policy.get("team_limit_profiles", {})
    default_limits = (
        profiles.get(default_profile, {}) if isinstance(profiles, dict) else {}
    )
    max_creation_attempts = default_limits.get(
        "max_worker_attempts", FALLBACK_MAX_CREATION_ATTEMPTS
    )
    max_in_flight = default_limits.get(
        "max_planned_workers", FALLBACK_MAX_IN_FLIGHT
    )
    if (
        not isinstance(max_creation_attempts, int)
        or isinstance(max_creation_attempts, bool)
        or max_creation_attempts < 1
    ):
        max_creation_attempts = FALLBACK_MAX_CREATION_ATTEMPTS
    if (
        not isinstance(max_in_flight, int)
        or isinstance(max_in_flight, bool)
        or max_in_flight < 1
    ):
        max_in_flight = FALLBACK_MAX_IN_FLIGHT
    fast_routing_models = set(policy.get("fast_routing_models", []))
    default_fast_models = set(policy.get("default_fast_models", []))
    result["scale_profile"] = default_profile
    result["limits"] = {
        "max_worker_attempts": max_creation_attempts,
        "max_planned_workers": max_in_flight,
    }
    result["record_count"] = len(records)
    team_plan_units: dict[int, set[str]] = {}
    team_plan_limits: dict[int, dict[str, int]] = {}
    team_plan_profiles: dict[int, str] = {}
    active_team_plan_revision: int | None = None
    if root is not None and (
        "team_plans" in root or "active_team_plan_revision" in root
    ):
        team_plans = root.get("team_plans")
        active_team_plan_revision = root.get("active_team_plan_revision")
        if not isinstance(team_plans, list) or not team_plans:
            result["errors"].append("root team_plans must be a non-empty array")
        else:
            revisions: list[int] = []
            for index, team_plan in enumerate(team_plans):
                validation = validate_team_plan_payload(team_plan, registry)
                if not validation["team_plan_valid"]:
                    for error in validation["errors"]:
                        result["errors"].append(
                            f"team_plans[{index}] is invalid: {error}"
                        )
                    continue
                revision = team_plan["revision"]
                revisions.append(revision)
                team_plan_units[revision] = {
                    unit["unit_id"] for unit in team_plan["units"]
                }
                team_plan_limits[revision] = validation["limits"]
                team_plan_profiles[revision] = validation["scale_profile"]
            if revisions and revisions != list(range(1, len(revisions) + 1)):
                result["errors"].append(
                    "TeamPlan revisions must be ordered and contiguous from 1"
                )
            if (
                not isinstance(active_team_plan_revision, int)
                or isinstance(active_team_plan_revision, bool)
                or active_team_plan_revision not in team_plan_units
            ):
                result["errors"].append(
                    "active_team_plan_revision must name an available revision"
                )
            elif revisions and active_team_plan_revision != revisions[-1]:
                result["errors"].append(
                    "active_team_plan_revision must name the latest revision"
                )
            elif active_team_plan_revision in team_plan_limits:
                active_limits = team_plan_limits[active_team_plan_revision]
                max_creation_attempts = active_limits["max_worker_attempts"]
                max_in_flight = active_limits["max_planned_workers"]
                result["scale_profile"] = team_plan_profiles[active_team_plan_revision]
                result["limits"] = active_limits
    surfaces = {
        record.get("surface", "app_thread")
        for record in records
        if isinstance(record, dict)
    }
    try:
        schema = load_json(args.schema) if "app_thread" in surfaces else {}
        native_schema = (
            load_json(args.native_schema) if "native_subagent" in surfaces else {}
        )
    except (OSError, json.JSONDecodeError) as exc:
        result["errors"].append(f"JSON load failed: {exc}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    required = schema.get("required", []) if isinstance(schema, dict) else []
    states = set(
        schema.get("properties", {})
        .get("control_state", {})
        .get("enum", [])
    )
    native_required = (
        native_schema.get("required", []) if isinstance(native_schema, dict) else []
    )
    native_states = set(
        native_schema.get("properties", {})
        .get("control_state", {})
        .get("enum", [])
    )

    if len(records) > max_creation_attempts:
        result["errors"].append("worker records exceed the root worker-attempt cap")

    attempts: list[int] = []
    task_ids: set[str] = set()
    thread_ids: set[str] = set()
    pending_ids: set[str] = set()
    agent_ids: set[str] = set()
    recorded_team_units: set[tuple[int, str]] = set()
    in_flight_team_revisions: set[int] = set()
    team_unit_attempts: dict[tuple[int, str], list[int]] = {}
    in_flight_states = {
        "PLANNED",
        "CREATION_PENDING",
        "CONTROL_READY",
        "DATA_READY",
        "UNKNOWN",
    }

    for index, record in enumerate(records):
        prefix = f"record {index}"
        if not isinstance(record, dict):
            result["errors"].append(f"{prefix} must be an object")
            continue

        surface = record.get("surface", "app_thread")
        if team_plan_units:
            unit_id = record.get("unit_id")
            team_plan_revision = record.get("team_plan_revision")
            if not nonempty_string(unit_id):
                result["errors"].append(f"{prefix} lacks a TeamPlan unit_id")
            if (
                not isinstance(team_plan_revision, int)
                or isinstance(team_plan_revision, bool)
                or team_plan_revision < 1
            ):
                result["errors"].append(
                    f"{prefix} has invalid team_plan_revision"
                )
            elif team_plan_revision not in team_plan_units:
                result["errors"].append(
                    f"{prefix} references an unknown TeamPlan revision"
                )
            elif nonempty_string(unit_id):
                if unit_id not in team_plan_units[team_plan_revision]:
                    result["errors"].append(
                        f"{prefix} references a unit outside its TeamPlan revision"
                    )
                else:
                    pair = (team_plan_revision, unit_id)
                    recorded_team_units.add(pair)
                    subtask_attempt = record.get("subtask_attempt")
                    if (
                        isinstance(subtask_attempt, int)
                        and not isinstance(subtask_attempt, bool)
                        and 1 <= subtask_attempt <= 2
                    ):
                        team_unit_attempts.setdefault(pair, []).append(
                            subtask_attempt
                        )
                    if record_is_in_flight(record):
                        in_flight_team_revisions.add(team_plan_revision)
        if surface == "native_subagent":
            missing = [field for field in native_required if field not in record]
            if missing:
                result["errors"].append(
                    f"{prefix} is missing required fields: {', '.join(missing)}"
                )

            attempt = record.get("worker_attempt")
            if (
                not isinstance(attempt, int)
                or isinstance(attempt, bool)
                or not 1 <= attempt <= max_creation_attempts
            ):
                result["errors"].append(f"{prefix} has invalid worker_attempt")
            else:
                attempts.append(attempt)

            subtask_attempt = record.get("subtask_attempt")
            if (
                not isinstance(subtask_attempt, int)
                or isinstance(subtask_attempt, bool)
                or not 1 <= subtask_attempt <= 2
            ):
                result["errors"].append(f"{prefix} has invalid subtask_attempt")

            task_id = record.get("task_id")
            if not nonempty_string(task_id):
                result["errors"].append(f"{prefix} has invalid task_id")
            elif task_id in task_ids:
                result["errors"].append(f"{prefix} duplicates task_id {task_id}")
            else:
                task_ids.add(task_id)

            agent_id = record.get("agent_id")
            if agent_id is not None and not nonempty_string(agent_id):
                result["errors"].append(f"{prefix} has invalid agent_id")
            if nonempty_string(agent_id):
                if agent_id in agent_ids:
                    result["errors"].append(f"{prefix} duplicates agent_id {agent_id}")
                agent_ids.add(agent_id)

            state = record.get("control_state")
            if state not in native_states:
                result["errors"].append(f"{prefix} has unknown native control_state")
            if state in {
                "PLANNED",
                "SPAWN_PENDING",
                "RUNNING",
                "COMPLETED",
                "UNKNOWN",
                "FAILED",
            }:
                result["in_flight_count"] += 1

            adopted = record.get("adopted")
            closed = record.get("closed")
            if not isinstance(adopted, bool):
                result["errors"].append(f"{prefix} has non-boolean adopted")
            if not isinstance(closed, bool):
                result["errors"].append(f"{prefix} has non-boolean closed")

            if state == "PLANNED" and (agent_id is not None or closed is True):
                result["errors"].append(f"{prefix} PLANNED native state contains runtime evidence")
            elif state == "SPAWN_PENDING" and closed is True:
                result["errors"].append(f"{prefix} SPAWN_PENDING native state is closed")
            elif state in {"RUNNING", "COMPLETED", "CLOSED"} and not nonempty_string(agent_id):
                result["errors"].append(f"{prefix} native state lacks an agent_id")
            if state == "CLOSED" and closed is not True:
                result["errors"].append(f"{prefix} violates the native close gate")
            if closed is True and state != "CLOSED":
                result["errors"].append(f"{prefix} closes a non-CLOSED native state")

            if record.get("fork_mode") != "fresh":
                result["errors"].append(f"{prefix} native worker must use fresh context")
            requested_model = record.get("requested_model")
            if not nonempty_string(requested_model) or record.get("model") != requested_model:
                result["errors"].append(f"{prefix} requested model mismatch")
            entry = registry_models.get(requested_model, {})
            expected_runtime_model = runtime_model_id(
                entry,
                "native_subagent",
                record.get("requested_speed", "standard"),
            )
            if record.get("runtime_model") != expected_runtime_model:
                result["errors"].append(f"{prefix} runtime model mismatch")
            accepted_model = record.get("platform_accepted_model")
            if state in {"RUNNING", "COMPLETED", "FAILED", "CLOSED"}:
                if not nonempty_string(accepted_model) or accepted_model != expected_runtime_model:
                    result["errors"].append(f"{prefix} accepted model mismatch")
            observed_model = record.get("observed_runtime_model")
            if (
                observed_model is not None
                and observed_model != "unknown"
                and observed_model not in {requested_model, expected_runtime_model}
            ):
                result["errors"].append(f"{prefix} observed model mismatch")
            validate_speed_identity(
                record,
                prefix=prefix,
                accepted_states={"RUNNING", "COMPLETED", "CLOSED"},
                fast_routing_models=fast_routing_models,
                default_fast_models=default_fast_models,
                errors=result["errors"],
            )

            if not valid_timestamp(record.get("last_observed_at")):
                result["errors"].append(f"{prefix} has invalid last_observed_at")
            if state in {"RUNNING", "COMPLETED", "UNKNOWN", "FAILED", "CLOSED"}:
                if record.get("last_observed_at") is None:
                    result["errors"].append(
                        f"{prefix} lacks an official native observation timestamp"
                    )

            output = record.get("output")
            if adopted is True and not nonempty_string(output):
                result["errors"].append(f"{prefix} is adopted without a recorded output")
            if adopted is True and (state != "CLOSED" or closed is not True):
                result["errors"].append(
                    f"{prefix} adopted native output must be closed"
                )

            task_intent = record.get("task_intent")
            mutation_authority = record.get("mutation_authority")
            if task_intent is not None and task_intent not in {"mutate", "inspect", "verify"}:
                result["errors"].append(f"{prefix} has invalid task_intent")
            if mutation_authority is not None and mutation_authority not in {
                "none",
                "declared-output-only",
                "declared-workspace",
                "isolated-worktree",
            }:
                result["errors"].append(f"{prefix} has invalid mutation_authority")
            if task_intent in {"inspect", "verify"} and mutation_authority in {
                "declared-workspace",
                "isolated-worktree",
            }:
                result["errors"].append(
                    f"{prefix} grants source mutation to {task_intent} intent"
                )
            continue

        if surface != "app_thread":
            result["errors"].append(f"{prefix} has unknown execution surface")
            continue

        missing = [field for field in required if field not in record]
        if missing:
            result["errors"].append(f"{prefix} is missing required fields: {', '.join(missing)}")

        attempt = record.get("creation_attempt")
        if (
            not isinstance(attempt, int)
            or isinstance(attempt, bool)
            or not 1 <= attempt <= max_creation_attempts
        ):
            result["errors"].append(f"{prefix} has invalid creation_attempt")
        else:
            attempts.append(attempt)
        worker_attempt = record.get("worker_attempt")
        if worker_attempt is not None:
            if (
                not isinstance(worker_attempt, int)
                or isinstance(worker_attempt, bool)
                or not 1 <= worker_attempt <= max_creation_attempts
            ):
                result["errors"].append(f"{prefix} has invalid worker_attempt")
            elif worker_attempt != attempt:
                result["errors"].append(
                    f"{prefix} worker_attempt must equal creation_attempt"
                )

        subtask_attempt = record.get("subtask_attempt")
        if (
            not isinstance(subtask_attempt, int)
            or isinstance(subtask_attempt, bool)
            or not 1 <= subtask_attempt <= 2
        ):
            result["errors"].append(f"{prefix} has invalid subtask_attempt")

        task_id = record.get("task_id")
        if not nonempty_string(task_id):
            result["errors"].append(f"{prefix} has invalid task_id")
        elif task_id in task_ids:
            result["errors"].append(f"{prefix} duplicates task_id {task_id}")
        else:
            task_ids.add(task_id)

        thread_id = record.get("thread_id")
        pending_id = record.get("pending_worktree_id")
        if thread_id is not None and not nonempty_string(thread_id):
            result["errors"].append(f"{prefix} has invalid thread_id")
        if pending_id is not None and not nonempty_string(pending_id):
            result["errors"].append(f"{prefix} has invalid pending_worktree_id")
        if nonempty_string(thread_id):
            if thread_id in thread_ids:
                result["errors"].append(f"{prefix} duplicates thread_id {thread_id}")
            thread_ids.add(thread_id)
        if nonempty_string(pending_id):
            if pending_id in pending_ids:
                result["errors"].append(
                    f"{prefix} duplicates pending_worktree_id {pending_id}"
                )
            pending_ids.add(pending_id)
        if nonempty_string(thread_id) and thread_id == pending_id:
            result["errors"].append(f"{prefix} treats a pending id as a formal thread id")

        state = record.get("control_state")
        if state not in states:
            result["errors"].append(f"{prefix} has unknown control_state")
        if state in in_flight_states:
            result["in_flight_count"] += 1

        materialized = record.get("materialized")
        data_ready = record.get("data_ready")
        adopted = record.get("adopted")
        archived = record.get("archived")
        for name, value in (
            ("materialized", materialized),
            ("data_ready", data_ready),
            ("adopted", adopted),
            ("archived", archived),
        ):
            if not isinstance(value, bool):
                result["errors"].append(f"{prefix} has non-boolean {name}")

        if materialized is True and not nonempty_string(thread_id):
            result["errors"].append(f"{prefix} is materialized without a formal thread_id")
        if data_ready is True and materialized is not True:
            result["errors"].append(f"{prefix} is data_ready without materialization")

        if state == "PLANNED":
            if (
                thread_id is not None
                or pending_id is not None
                or materialized is True
                or data_ready is True
            ):
                result["errors"].append(f"{prefix} PLANNED state contains runtime evidence")
        elif state == "CREATION_PENDING":
            if materialized is True or data_ready is True:
                result["errors"].append(f"{prefix} CREATION_PENDING cannot be ready")
        elif state == "CONTROL_READY":
            if materialized is not True or not nonempty_string(thread_id) or data_ready is True:
                result["errors"].append(f"{prefix} violates CONTROL_READY invariants")
        elif state == "DATA_READY":
            if materialized is not True or data_ready is not True or not nonempty_string(thread_id):
                result["errors"].append(f"{prefix} violates DATA_READY invariants")
        elif state == "COMPLETED":
            if (
                materialized is not True
                or data_ready is not True
                or not nonempty_string(thread_id)
                or record.get("turn_status") != "completed"
            ):
                result["errors"].append(f"{prefix} violates COMPLETED invariants")
        elif state in {"UNKNOWN", "FAILED"} and archived is True:
            result["errors"].append(f"{prefix} cannot archive {state} state")

        if not valid_timestamp(record.get("last_observed_at")):
            result["errors"].append(f"{prefix} has invalid last_observed_at")
        if state in {"CONTROL_READY", "DATA_READY", "COMPLETED", "UNKNOWN", "FAILED"}:
            if record.get("last_observed_at") is None:
                result["errors"].append(f"{prefix} lacks an official observation timestamp")
        if state in {"CONTROL_READY", "DATA_READY", "COMPLETED"}:
            if not nonempty_string(record.get("thread_status")):
                result["errors"].append(f"{prefix} lacks an official thread_status")
        validate_speed_identity(
            record,
            prefix=prefix,
            accepted_states={"CONTROL_READY", "DATA_READY", "COMPLETED"},
            fast_routing_models=fast_routing_models,
            default_fast_models=default_fast_models,
            errors=result["errors"],
        )

        output = record.get("output")
        if adopted is True and not nonempty_string(output):
            result["errors"].append(f"{prefix} is adopted without a recorded output")
        if archived is True:
            if (
                state != "COMPLETED"
                or record.get("turn_status") != "completed"
                or materialized is not True
                or adopted is not True
                or not nonempty_string(thread_id)
                or not nonempty_string(output)
            ):
                result["errors"].append(f"{prefix} violates the archive gate")

        task_intent = record.get("task_intent")
        mutation_authority = record.get("mutation_authority")
        if task_intent is not None and task_intent not in {"mutate", "inspect", "verify"}:
            result["errors"].append(f"{prefix} has invalid task_intent")
        if mutation_authority is not None and mutation_authority not in {
            "none",
            "declared-output-only",
            "declared-workspace",
            "isolated-worktree",
        }:
            result["errors"].append(f"{prefix} has invalid mutation_authority")
        if task_intent in {"inspect", "verify"} and mutation_authority in {
            "declared-workspace",
            "isolated-worktree",
        }:
            result["errors"].append(
                f"{prefix} grants source mutation to {task_intent} intent"
            )
        correlation_id = record.get("result_correlation_id")
        if correlation_id is not None and not nonempty_string(correlation_id):
            result["errors"].append(f"{prefix} has invalid result_correlation_id")

    if len(attempts) != len(set(attempts)):
        result["errors"].append("Worker attempt values must be unique")
    if attempts and sorted(attempts) != list(range(1, len(attempts) + 1)):
        result["errors"].append("Worker attempt values must be contiguous from 1")
    if result["in_flight_count"] > max_in_flight:
        result["errors"].append("in-flight records exceed the concurrency cap")

    if active_team_plan_revision is not None:
        stale_in_flight = sorted(
            revision
            for revision in in_flight_team_revisions
            if revision < active_team_plan_revision
        )
        if stale_in_flight:
            result["errors"].append(
                "a newer TeamPlan revision is active while an older revision is still in flight"
            )

    for (revision, unit_id), attempts_for_unit in sorted(team_unit_attempts.items()):
        expected = list(range(1, len(attempts_for_unit) + 1))
        if sorted(attempts_for_unit) != expected:
            result["errors"].append(
                f"TeamPlan revision {revision} unit {unit_id} attempts must be unique and contiguous from 1"
            )

    for revision, unit_ids in sorted(team_plan_units.items()):
        for unit_id in sorted(unit_ids):
            if (revision, unit_id) not in recorded_team_units:
                result["warnings"].append(
                    f"TeamPlan revision {revision} unit {unit_id} has no Worker record; report its disposition"
                )

    if root is not None:
        expected_attempt_counts = {
            "creation_attempts": sum(
                1
                for record in records
                if isinstance(record, dict)
                and record.get("surface", "app_thread") == "app_thread"
            ),
            "worker_attempts": len(records),
        }
        for field, expected_count in expected_attempt_counts.items():
            if field not in root:
                continue
            root_attempts = root[field]
            if (
                not isinstance(root_attempts, int)
                or isinstance(root_attempts, bool)
                or root_attempts != expected_count
            ):
                result["errors"].append(
                    f"root {field} must equal {expected_count} for this ledger"
                )

    if result["errors"]:
        exit_code = 2
    else:
        result["status"] = "pass"
        result["ledger_valid"] = True
        exit_code = 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
