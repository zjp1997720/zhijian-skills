#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = SKILL_ROOT / "references" / "audit-schema.json"
MAX_CREATION_ATTEMPTS = 8
MAX_IN_FLIGHT = 6


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate deterministic invariants in a Codex model-routing team ledger."
    )
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
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


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main() -> int:
    args = parse_args()
    result: dict[str, Any] = {
        "ledger": str(args.ledger),
        "status": "fail",
        "ledger_valid": False,
        "record_count": 0,
        "in_flight_count": 0,
        "errors": [],
        "warnings": [],
    }
    try:
        payload = load_json(args.ledger)
        schema = load_json(args.schema)
        root, records = records_from(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result["errors"].append(f"JSON load failed: {exc}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    result["record_count"] = len(records)
    required = schema.get("required", []) if isinstance(schema, dict) else []
    states = set(
        schema.get("properties", {})
        .get("control_state", {})
        .get("enum", [])
    )

    if len(records) > MAX_CREATION_ATTEMPTS:
        result["errors"].append("worker records exceed the root creation-attempt cap")

    attempts: list[int] = []
    task_ids: set[str] = set()
    thread_ids: set[str] = set()
    pending_ids: set[str] = set()
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

        missing = [field for field in required if field not in record]
        if missing:
            result["errors"].append(f"{prefix} is missing required fields: {', '.join(missing)}")

        attempt = record.get("creation_attempt")
        if not isinstance(attempt, int) or isinstance(attempt, bool) or not 1 <= attempt <= 8:
            result["errors"].append(f"{prefix} has invalid creation_attempt")
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
        result["errors"].append("creation_attempt values must be unique")
    if attempts and sorted(attempts) != list(range(1, len(attempts) + 1)):
        result["errors"].append("creation_attempt values must be contiguous from 1")
    if result["in_flight_count"] > MAX_IN_FLIGHT:
        result["errors"].append("in-flight records exceed the concurrency cap")

    if root is not None and "creation_attempts" in root:
        root_attempts = root["creation_attempts"]
        if (
            not isinstance(root_attempts, int)
            or isinstance(root_attempts, bool)
            or root_attempts != len(records)
        ):
            result["errors"].append(
                "root creation_attempts must equal the number of Worker records"
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
