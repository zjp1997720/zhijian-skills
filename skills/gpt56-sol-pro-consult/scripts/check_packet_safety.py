#!/usr/bin/env python3
"""Heuristic packet scanner for GPT 5.6 Sol Pro consultation packets.

This script is intentionally light-touch. The skill is meant to solve hard
problems with rich context, so ordinary user-owned project or business details
should not block consultation. Only credential-like material blocks by default.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


HIGH_PATTERNS = [
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PRIVATE )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("authorization_header", re.compile(r"(?i)\bAuthorization\s*:\s*(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{12,}")),
    ("cookie_header", re.compile(r"(?i)\bCookie\s*:\s*[^\\n]{20,}")),
    ("password_assignment", re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*['\"]?[^\\s'\"]{8,}")),
]

WARN_PATTERNS = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone_cn", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("id_card_cn", re.compile(r"\b\d{17}[\dXx]\b")),
    ("absolute_user_path", re.compile(r"/Users/[^\\s`'\"<>]+")),
    ("private_url", re.compile(r"https?://(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[0-1])\.\d+\.\d+)[^\\s`'\"<>]*")),
]


def compact_excerpt(text: str, start: int, end: int) -> str:
    left = max(0, start - 12)
    right = min(len(text), end + 12)
    snippet = text[left:right].replace("\n", "\\n")
    if len(snippet) > 80:
        snippet = snippet[:77] + "..."
    return snippet


def scan(text: str) -> dict:
    findings = []
    for severity, patterns in (("high", HIGH_PATTERNS), ("warn", WARN_PATTERNS)):
        for name, pattern in patterns:
            for match in pattern.finditer(text):
                findings.append(
                    {
                        "severity": severity,
                        "type": name,
                        "start": match.start(),
                        "end": match.end(),
                        "excerpt": compact_excerpt(text, match.start(), match.end()),
                    }
                )

    high_count = sum(1 for item in findings if item["severity"] == "high")
    warn_count = sum(1 for item in findings if item["severity"] == "warn")
    return {
        "ok": high_count == 0,
        "high_count": high_count,
        "warn_count": warn_count,
        "char_count": len(text),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan a GPT 5.6 Sol Pro context packet for credential-like material.")
    parser.add_argument("packet", help="Path to packet markdown, or '-' for stdin")
    parser.add_argument("--max-chars", type=int, default=15000, help="Warn when packet exceeds this many characters")
    parser.add_argument("--fail-on-length", action="store_true", help="Exit non-zero when packet exceeds --max-chars")
    parser.add_argument("--allow-credentials", action="store_true", help="Warn but do not fail on credential-like findings")
    args = parser.parse_args()

    if args.packet == "-":
        text = sys.stdin.read()
    else:
        text = Path(args.packet).read_text(encoding="utf-8")

    result = scan(text)
    if len(text) > args.max_chars:
        result["findings"].append(
            {
                "severity": "warn",
                "type": "packet_too_long",
                "start": args.max_chars,
                "end": len(text),
                "excerpt": f"{len(text)} chars exceeds max {args.max_chars}",
            }
        )
        result["warn_count"] += 1
        if args.fail_on_length:
            result["ok"] = False
            result["findings"][-1]["severity"] = "high"
            result["high_count"] += 1
            result["warn_count"] -= 1

    if args.allow_credentials:
        result["ok"] = True

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
