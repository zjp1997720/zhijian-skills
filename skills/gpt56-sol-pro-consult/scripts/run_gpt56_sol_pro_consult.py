#!/usr/bin/env python3
"""Run a text-only GPT 5.6 Sol Pro consultation through ChatGPT Web and OpenCLI."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from extract_chatgpt_reply import split_latest_assistant


SKILL_DIR = Path(__file__).resolve().parents[1]
MODEL_TESTIDS = (
    "data-testid=model-switcher-gpt-5-pro",
    "data-testid=model-switcher-gpt-5-6-pro",
)
MODEL_LABELS = ("Pro", "Sol", "5.6", "极高", "Extra High", "High", "Medium", "Instant")
LEGACY_PRO_HINTS = ("gpt-5-5-pro", "GPT 5.5 Pro", "GPT-5.5 Pro", "Pro Extended", "进阶专业")
PRO_LABEL = re.compile(r"(?<![A-Za-z0-9])Pro(?![A-Za-z0-9])", re.IGNORECASE)
GPT56_FAMILY_HINTS = ("GPT-5.6 Sol", "GPT 5.6 Sol")
SEND_HINTS = (
    "data-testid=send-button",
    "aria-label=发送提示",
    "aria-label=Send prompt",
    "aria-label=Send message",
)
GENERATING_HINTS = (
    "data-testid=stop-button",
    "aria-label=停止回答",
    "aria-label=Stop generating",
    "aria-label=Stop streaming",
    "正在思考",
)


class ConsultError(RuntimeError):
    pass


def run_opencli(args: list[str], *, timeout: int = 60, check: bool = True) -> str:
    result = subprocess.run(
        ["opencli", *args],
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ConsultError(f"opencli {' '.join(args)} failed: {detail}")
    return result.stdout


def find_ref(state: str, predicate) -> str | None:
    for line in state.splitlines():
        if predicate(line):
            match = re.search(r"\[(\d+)\]", line)
            if match:
                return match.group(1)
    return None


def find_ref_by_block(state: str, first_line_predicate, block_predicate, lookahead: int = 8) -> str | None:
    lines = state.splitlines()
    for index, line in enumerate(lines):
        if not first_line_predicate(line):
            continue
        block = "\n".join(lines[index : index + lookahead])
        if not block_predicate(block):
            continue
        match = re.search(r"\[(\d+)\]", line)
        if match:
            return match.group(1)
    return None


def get_state(session: str) -> str:
    return run_opencli(["browser", session, "state"], timeout=30)


def click_ref(session: str, ref: str) -> None:
    run_opencli(["browser", session, "click", ref], timeout=30)


def is_current_pro_block(block: str, *, require_checked: bool) -> bool:
    if any(hint in block for hint in LEGACY_PRO_HINTS):
        return False
    if require_checked and "aria-checked=true" not in block:
        return False
    if any(testid in block for testid in MODEL_TESTIDS):
        return True
    return "role=menuitemradio" in block and bool(PRO_LABEL.search(block))


def has_gpt56_family(state: str) -> bool:
    return any(hint in state for hint in GPT56_FAMILY_HINTS)


def model_is_confirmed(state: str) -> bool:
    lines = state.splitlines()
    for index, line in enumerate(lines):
        if "role=menuitemradio" not in line and not any(testid in line for testid in MODEL_TESTIDS):
            continue
        block = "\n".join(lines[index : index + 6])
        has_current_testid = any(testid in block for testid in MODEL_TESTIDS)
        if is_current_pro_block(block, require_checked=True) and (has_current_testid or has_gpt56_family(state)):
            return True
    return False


def find_model_button(state: str) -> str | None:
    return find_ref_by_block(
        state,
        lambda line: "<button" in line and "aria-haspopup=menu" in line,
        lambda block: any(label in block for label in MODEL_LABELS),
        lookahead=10,
    )


def find_pro_ref(menu_state: str) -> str | None:
    exact_ref = find_ref_by_block(
        menu_state,
        lambda line: any(testid in line for testid in MODEL_TESTIDS),
        lambda block: is_current_pro_block(block, require_checked=False),
        lookahead=6,
    )
    if exact_ref or not has_gpt56_family(menu_state):
        return exact_ref
    return find_ref_by_block(
        menu_state,
        lambda line: "role=menuitemradio" in line,
        lambda block: is_current_pro_block(block, require_checked=False),
        lookahead=6,
    )


def ensure_gpt56_sol_pro(session: str) -> str:
    state = get_state(session)
    if model_is_confirmed(state):
        run_opencli(["browser", session, "keys", "Escape"], timeout=10, check=False)
        return get_state(session)

    model_button = find_model_button(state)
    if not model_button:
        raise ConsultError("Could not find the ChatGPT model switcher button.")

    click_ref(session, model_button)
    menu_state = get_state(session)
    pro_ref = find_pro_ref(menu_state)
    if not pro_ref:
        raise ConsultError("GPT 5.6 Sol Pro was not visible in the model switcher.")

    if not model_is_confirmed(menu_state):
        click_ref(session, pro_ref)
        time.sleep(1)
        state = get_state(session)
        model_button = find_model_button(state)
        if not model_button:
            raise ConsultError("Could not reopen the model switcher for confirmation.")
        click_ref(session, model_button)
        menu_state = get_state(session)

    if not model_is_confirmed(menu_state):
        raise ConsultError("GPT 5.6 Sol Pro could not be confirmed as selected.")

    run_opencli(["browser", session, "keys", "Escape"], timeout=10, check=False)
    return get_state(session)


def read_packet(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    return sys.stdin.read()


def run_safety_check(packet_path: Path, allow_warnings: bool) -> None:
    result = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts" / "check_packet_safety.py"), str(packet_path)],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = result.stdout.strip() or result.stderr.strip()
        raise ConsultError(f"Packet safety check failed: {detail}")
    if not allow_warnings:
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return
        if payload.get("warn_count", 0):
            print(result.stdout.strip(), file=sys.stderr)


def extract_sentinel(packet: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    match = re.search(r"GPT56_SOL_PRO_RESULT_[A-Za-z0-9_:-]+", packet)
    if not match:
        raise ConsultError("Could not infer sentinel. Pass --sentinel or include GPT56_SOL_PRO_RESULT_... in the packet.")
    return match.group(0)


def composer_ref(state: str) -> str | None:
    return find_ref(
        state,
        lambda line: (
            "id=prompt-textarea" in line
            and ("contenteditable=true" in line or "textarea" in line)
        ),
    )


def fill_composer(session: str, state: str, packet: str, sentinel: str) -> str:
    ref = composer_ref(state)
    if not ref:
        raise ConsultError("Could not find ChatGPT composer.")

    raw = run_opencli(["browser", session, "fill", ref, packet], timeout=120, check=False)
    try:
        fill_payload = json.loads(raw)
    except json.JSONDecodeError:
        fill_payload = {}

    if fill_payload and not fill_payload.get("filled"):
        raise ConsultError(f"Composer fill failed: {raw.strip()}")

    state_after_fill = get_state(session)
    actual = str(fill_payload.get("actual", ""))
    if fill_payload and not fill_payload.get("verified", True):
        if sentinel not in state_after_fill and sentinel not in actual:
            raise ConsultError("Composer fill was not verified and sentinel is not visible in state.")
    return state_after_fill


def send_ref(state: str) -> str | None:
    return find_ref(
        state,
        lambda line: "<button" in line and any(hint in line for hint in SEND_HINTS),
    )


def send_packet(session: str, state: str) -> None:
    ref = send_ref(state)
    if not ref:
        raise ConsultError("Could not find ChatGPT send button after filling composer.")
    click_ref(session, ref)


def extract_current(session: str) -> str:
    return run_opencli(
        ["browser", session, "extract", "--selector", "main", "--chunk-size", "40000"],
        timeout=60,
    )


def normalize_sentinel(text: str) -> str:
    return text.replace("\\_", "_")


def page_is_generating(state: str) -> bool:
    return any(hint in state for hint in GENERATING_HINTS)


def wait_for_reply(session: str, sentinel: str, timeout_seconds: int, poll_seconds: int) -> str:
    deadline = time.time() + timeout_seconds
    last_error = "Timed out before extraction started."

    while time.time() < deadline:
        time.sleep(poll_seconds)
        state = get_state(session)
        extract_json = extract_current(session)
        try:
            payload = json.loads(extract_json)
            reply = split_latest_assistant(str(payload.get("content", "")))
            normalized = normalize_sentinel(reply)
            if sentinel in normalized:
                return normalized
            if page_is_generating(state):
                last_error = (
                    "GPT 5.6 Sol Pro is still generating/thinking; partial text is not final yet "
                    f"(sentinel not found: {sentinel})"
                )
            else:
                last_error = f"Sentinel not found in completed assistant reply: {sentinel}"
        except Exception as exc:
            if page_is_generating(state):
                last_error = f"GPT 5.6 Sol Pro is still generating/thinking; extraction not ready: {exc}"
            else:
                last_error = str(exc)

    raise ConsultError(f"Timed out waiting for GPT 5.6 Sol Pro reply: {last_error}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--prompt-file", help="Path to a full context packet.")
    source.add_argument("--stdin", action="store_true", help="Read a full context packet from stdin.")
    parser.add_argument("--sentinel", help="Expected sentinel in the assistant reply.")
    parser.add_argument("--session", help="OpenCLI browser session name.")
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--poll", type=int, default=180)
    parser.add_argument("--skip-doctor", action="store_true")
    parser.add_argument("--skip-safety", action="store_true")
    parser.add_argument("--allow-warning-output", action="store_true")
    parser.add_argument(
        "--attachment",
        action="append",
        default=[],
        help="Not supported by this wrapper; use the Chrome file chooser workflow.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.attachment:
        print(
            "ERROR: This wrapper is text-only. Use the Chrome file chooser workflow for attachments.",
            file=sys.stderr,
        )
        return 2

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session = args.session or f"gpt56-sol-pro-{timestamp}"

    try:
        packet = read_packet(args)
        sentinel = extract_sentinel(packet, args.sentinel)
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as file:
            file.write(packet)
            packet_path = Path(file.name)
        try:
            if not args.skip_safety:
                run_safety_check(packet_path, args.allow_warning_output)

            if not args.skip_doctor:
                run_opencli(["doctor"], timeout=60)

            run_opencli(["browser", session, "open", "https://chatgpt.com/"], timeout=60)
            state = ensure_gpt56_sol_pro(session)
            state = fill_composer(session, state, packet, sentinel)
            send_packet(session, state)
            reply = wait_for_reply(session, sentinel, args.timeout, args.poll)
        finally:
            packet_path.unlink(missing_ok=True)
    except ConsultError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"session={session}", file=sys.stderr)
    print("model=GPT-5.6-Sol-Pro", file=sys.stderr)
    print("model_confirmed=yes", file=sys.stderr)
    print("sentinel_verified=yes", file=sys.stderr)
    sys.stdout.write(reply)
    if not reply.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
