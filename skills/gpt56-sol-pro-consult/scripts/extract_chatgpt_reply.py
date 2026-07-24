#!/usr/bin/env python3
"""Extract the latest ChatGPT assistant reply from OpenCLI extract JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ASSISTANT_MARKERS = [
    "#### ChatGPT 说：",
    "#### ChatGPT said:",
    "#### ChatGPT:",
]

USER_MARKERS = [
    "#### 你说：",
    "#### You said:",
]

DISCLAIMER_PATTERNS = [
    r"\n+ChatGPT 也可能会犯错。.*$",
    r"\n+ChatGPT can make mistakes\..*$",
]


def load_content(path: str) -> str:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict) or "content" not in data:
        raise ValueError("OpenCLI extract JSON must contain a top-level 'content' field")
    return str(data["content"])


def split_latest_assistant(content: str) -> str:
    marker_positions = []
    for marker in ASSISTANT_MARKERS:
        index = 0
        while True:
            found = content.find(marker, index)
            if found == -1:
                break
            marker_positions.append((found, marker))
            index = found + len(marker)

    if not marker_positions:
        raise ValueError("No assistant marker found in extracted content")

    start, marker = sorted(marker_positions)[-1]
    reply = content[start + len(marker) :].strip()

    next_positions = []
    for next_marker in ASSISTANT_MARKERS + USER_MARKERS:
        pos = reply.find(next_marker)
        if pos != -1:
            next_positions.append(pos)
    if next_positions:
        reply = reply[: min(next_positions)].strip()

    for pattern in DISCLAIMER_PATTERNS:
        reply = re.sub(pattern, "", reply, flags=re.DOTALL).strip()

    return reply


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract the latest assistant reply from OpenCLI ChatGPT extract JSON.")
    parser.add_argument("extract_json", help="Path to OpenCLI extract JSON, or '-' for stdin")
    parser.add_argument("--sentinel", help="Required sentinel that must appear inside the assistant reply")
    parser.add_argument("--json", action="store_true", help="Print JSON envelope instead of plain text")
    args = parser.parse_args()

    try:
        content = load_content(args.extract_json)
        reply = split_latest_assistant(content)
        sentinel_ok = True if not args.sentinel else args.sentinel.replace("_", "\\_") in reply or args.sentinel in reply
        if args.sentinel and not sentinel_ok:
            raise ValueError(f"Sentinel not found in assistant reply: {args.sentinel}")
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"ok": True, "sentinel_ok": sentinel_ok, "reply": reply}, ensure_ascii=False, indent=2))
    else:
        print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
