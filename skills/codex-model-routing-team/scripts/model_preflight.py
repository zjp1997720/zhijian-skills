#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = SKILL_ROOT / "references" / "model-registry.json"
MAX_RESPONSE_BYTES = 65_536


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def reasoning_levels(model: dict[str, Any]) -> set[str]:
    raw = model.get("supported_reasoning_levels")
    if not isinstance(raw, list):
        return set()
    levels: set[str] = set()
    for item in raw:
        if isinstance(item, str):
            levels.add(item)
        elif isinstance(item, dict) and isinstance(item.get("effort"), str):
            levels.add(item["effort"])
    return levels


def catalog_models(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("models"), list):
        return [item for item in payload["models"] if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def find_catalog_model(payload: Any, model_id: str) -> dict[str, Any] | None:
    for item in catalog_models(payload):
        candidate = item.get("slug") or item.get("id") or item.get("model")
        if candidate == model_id:
            return item
    return None


def extract_response_text(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
    chunks: list[str] = []
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                text = part.get("text") or part.get("output_text")
                if isinstance(text, str):
                    chunks.append(text)
    return "\n".join(chunks)


def loopback_probe_url(url: str) -> tuple[bool, str | None]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False, "probe URL must be an absolute HTTP(S) URL"
    if parsed.username or parsed.password:
        return False, "probe URL must not contain credentials"
    if parsed.hostname == "localhost":
        return True, None
    try:
        if ipaddress.ip_address(parsed.hostname).is_loopback:
            return True, None
    except ValueError:
        pass
    return False, "probe URL must use a loopback host"


def semantic_probe(
    *,
    url: str,
    model: str,
    thinking: str,
    auth_env: str | None,
    timeout: float,
) -> dict[str, Any]:
    safe_url, url_error = loopback_probe_url(url)
    if not safe_url:
        return {"status": "fail", "error": url_error}
    nonce = f"ROUTE-CANARY-{secrets.token_hex(4).upper()}"
    body = {
        "model": model,
        "input": f"Do not call tools. Reply with exactly {nonce}",
        "reasoning": {"effort": thinking},
        "max_output_tokens": 32,
        "tools": [],
    }
    headers = {"Content-Type": "application/json"}
    if auth_env:
        authorization_value = os.environ.get(auth_env)
        if not authorization_value:
            return {
                "status": "fail",
                "error": f"credential environment variable is missing: {auth_env}",
            }
        headers["Authorization"] = f"Bearer {authorization_value}"
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    opener = urllib.request.build_opener(NoRedirect())
    started = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            status_code = response.status
    except urllib.error.HTTPError as exc:
        retry_after = exc.headers.get("Retry-After") if exc.headers else None
        return {
            "status": "fail",
            "http_status": exc.code,
            "retry_after": retry_after,
            "error": "probe endpoint returned an HTTP error or redirect",
        }
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"status": "fail", "error": f"probe transport failed: {exc}"}
    elapsed_ms = round((time.monotonic() - started) * 1000)
    if len(raw) > MAX_RESPONSE_BYTES:
        return {
            "status": "fail",
            "http_status": status_code,
            "latency_ms": elapsed_ms,
            "error": "probe response exceeded 65536 bytes",
        }
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "status": "fail",
            "http_status": status_code,
            "latency_ms": elapsed_ms,
            "error": "probe response was not valid JSON",
            "response_sha256": hashlib.sha256(raw).hexdigest(),
        }
    text = extract_response_text(payload)
    matched = text.strip() == nonce
    return {
        "status": "pass" if matched else "fail",
        "http_status": status_code,
        "latency_ms": elapsed_ms,
        "semantic_match": matched,
        "response_chars": len(text),
        "response_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect registry, runtime, provider, and optional semantic evidence for one model route."
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--thinking", required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--runtime-confirmed", action="store_true")
    parser.add_argument(
        "--provider-status",
        choices=("allowed", "manual_review", "blocked", "unknown"),
        default="unknown",
    )
    parser.add_argument("--data-allowed", action="store_true")
    parser.add_argument("--explicit-user-request", action="store_true")
    parser.add_argument("--risk-acknowledged", action="store_true")
    parser.add_argument("--probe-url")
    parser.add_argument("--auth-env")
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result: dict[str, Any] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "thinking": args.thinking,
        "registry_eligible": False,
        "runtime_status": "unknown",
        "provider_status": args.provider_status,
        "data_allowed": args.data_allowed,
        "route_status": "fail",
        "route_eligible": False,
        "checks": {},
        "warnings": [],
        "errors": [],
    }
    try:
        registry = load_json(args.registry)
    except (OSError, json.JSONDecodeError) as exc:
        result["errors"].append(f"registry load failed: {exc}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    models = registry.get("models", []) if isinstance(registry, dict) else []
    entry = next(
        (item for item in models if isinstance(item, dict) and item.get("id") == args.model),
        None,
    )
    if entry is None:
        result["errors"].append("model is not declared in model-registry.json")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    forbidden = set(registry.get("policy", {}).get("forbidden_thinking", []))
    registry_thinking = set(entry.get("thinking", []))
    if args.thinking in forbidden:
        result["errors"].append("thinking is forbidden by registry policy")
    elif args.thinking not in registry_thinking:
        result["errors"].append("thinking is not declared for this model")
    result["registry_eligible"] = not result["errors"]
    result["checks"]["registry"] = {
        "status": entry.get("status"),
        "automatic": bool(entry.get("automatic")),
        "provider": entry.get("provider"),
        "terms_default": entry.get("terms_default", "unknown"),
        "thinking_supported": args.thinking in registry_thinking,
    }

    if entry.get("terms_default") == "blocked":
        result["errors"].append("registry provider policy is blocked and cannot be overridden")

    manual_ready = True
    if entry.get("status") == "manual_only":
        manual_ready = args.explicit_user_request and args.risk_acknowledged
        if not args.explicit_user_request:
            result["warnings"].append("manual-only model requires an explicit user request")
        if not args.risk_acknowledged:
            result["warnings"].append("manual-only model requires separate risk acknowledgement")
    elif not entry.get("automatic"):
        result["errors"].append("model is disabled for automatic routing")

    catalog_declared = False
    if args.catalog and not result["errors"]:
        try:
            catalog_entry = find_catalog_model(load_json(args.catalog), args.model)
        except (OSError, json.JSONDecodeError) as exc:
            result["errors"].append(f"catalog load failed: {exc}")
            catalog_entry = None
        if catalog_entry is None:
            result["checks"]["catalog"] = {"found": False}
            result["errors"].append("model is absent from the supplied runtime catalog")
        else:
            levels = reasoning_levels(catalog_entry)
            supported = not levels or args.thinking in levels
            result["checks"]["catalog"] = {
                "found": True,
                "thinking_supported": supported,
                "declared_levels": sorted(levels),
            }
            if not supported:
                result["errors"].append("runtime catalog rejects the requested thinking level")
            else:
                catalog_declared = True

    if args.runtime_confirmed and not result["errors"]:
        result["runtime_status"] = "pass"
    elif catalog_declared:
        result["runtime_status"] = "declared"

    provider_ready = args.provider_status == "allowed" and args.data_allowed
    if args.provider_status == "blocked":
        result["errors"].append("provider policy is blocked and cannot be manually overridden")
    elif args.provider_status != "allowed":
        result["warnings"].append("provider approval is incomplete")
    if not args.data_allowed:
        result["warnings"].append("task data is not approved for this provider")

    if args.probe_url:
        if result["errors"] or not provider_ready or not manual_ready:
            result["warnings"].append("semantic probe skipped until registry and provider gates pass")
        else:
            probe = semantic_probe(
                url=args.probe_url,
                model=args.model,
                thinking=args.thinking,
                auth_env=args.auth_env,
                timeout=args.timeout,
            )
            result["checks"]["semantic_probe"] = probe
            if probe.get("status") == "pass":
                result["runtime_status"] = "pass"
            else:
                result["runtime_status"] = "fail"
                result["errors"].append("semantic probe failed")

    result["route_eligible"] = (
        not result["errors"]
        and result["registry_eligible"]
        and result["runtime_status"] == "pass"
        and provider_ready
        and manual_ready
    )
    if result["route_eligible"]:
        result["route_status"] = "pass"
        exit_code = 0
    elif result["errors"]:
        result["route_status"] = "fail"
        exit_code = 2
    else:
        result["route_status"] = "manual_review" if entry.get("status") == "manual_only" else "unknown"
        exit_code = 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
