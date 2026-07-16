#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import datetime as dt
import glob
import json
import os
import pathlib
import re
import socket
import struct
import subprocess
import sys
import time
import urllib.request
from typing import Any


HOME = pathlib.Path.home()
CODEX_HOME = pathlib.Path(os.environ.get("CODEX_HOME", HOME / ".codex"))
DEFAULT_BACKUP_ROOT = CODEX_HOME / "backup"
SESSION_PATH_RE = re.compile(r"((?:~|/)[^\"'\n\r]*?SKILL\.md)")
PATH_ALIASES_ENV = "CODEX_SKILL_ADMIN_PATH_ALIASES"


def normalize_path(path: str) -> str:
    normalized = os.path.expanduser(path)
    for mapping in os.environ.get(PATH_ALIASES_ENV, "").split(os.pathsep):
        if not mapping or "=" not in mapping:
            continue
        source, target = mapping.split("=", 1)
        source = os.path.expanduser(source)
        target = os.path.expanduser(target)
        if normalized.startswith(source):
            normalized = target + normalized[len(source) :]
    return normalized


def json_print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class TempAppServer:
    def __init__(self) -> None:
        self.port = free_port()
        self.process: subprocess.Popen[str] | None = None

    def __enter__(self) -> int:
        cmd = ["codex", "app-server", "--listen", f"ws://127.0.0.1:{self.port}"]
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        ready_url = f"http://127.0.0.1:{self.port}/readyz"
        deadline = time.time() + 15
        last_error = ""
        while time.time() < deadline:
            if self.process.poll() is not None:
                output = ""
                if self.process.stdout:
                    output = self.process.stdout.read()
                raise RuntimeError(f"codex app-server exited early:\n{output}")
            try:
                with urllib.request.urlopen(ready_url, timeout=1) as response:
                    if response.status == 200:
                        return self.port
            except Exception as exc:
                last_error = str(exc)
                time.sleep(0.15)
        raise RuntimeError(f"codex app-server did not become ready: {last_error}")

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if not self.process:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)


class WebSocketJsonRpc:
    def __init__(self, port: int) -> None:
        self.port = port
        self.sock: socket.socket | None = None
        self.next_id = 1

    def __enter__(self) -> "WebSocketJsonRpc":
        self.connect()
        init = self.request(
            "initialize",
            {
                "clientInfo": {"name": "codex-skill-admin", "version": "1.0.0"},
                "capabilities": {"experimentalApi": True},
            },
        )
        if "error" in init:
            raise RuntimeError(f"initialize failed: {init['error']}")
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass

    def connect(self) -> None:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET / HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=10)
        sock.settimeout(30)
        sock.sendall(request.encode("ascii"))
        headers = self._read_until(sock, b"\r\n\r\n")
        if b"101 Switching Protocols" not in headers:
            raise RuntimeError(headers.decode("utf-8", "replace"))
        self.sock = sock

    @staticmethod
    def _read_until(sock: socket.socket, marker: bytes) -> bytes:
        data = b""
        while marker not in data:
            chunk = sock.recv(4096)
            if not chunk:
                raise RuntimeError("socket closed during handshake")
            data += chunk
        return data

    def request(self, method: str, params: Any = None) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        payload: dict[str, Any] = {"id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        self._send_json(payload)
        while True:
            response = self._recv_json()
            if response.get("id") == request_id:
                return response

    def _send_json(self, payload: dict[str, Any]) -> None:
        if not self.sock:
            raise RuntimeError("websocket is not connected")
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        mask = os.urandom(4)
        header = bytearray([0x81])
        if len(body) < 126:
            header.append(0x80 | len(body))
        elif len(body) < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", len(body)))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", len(body)))
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(body))
        self.sock.sendall(bytes(header) + mask + masked)

    def _recv_exact(self, length: int) -> bytes:
        if not self.sock:
            raise RuntimeError("websocket is not connected")
        chunks: list[bytes] = []
        remaining = length
        while remaining:
            chunk = self.sock.recv(remaining)
            if not chunk:
                raise RuntimeError("socket closed while reading frame")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _recv_json(self) -> dict[str, Any]:
        while True:
            first, second = self._recv_exact(2)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._recv_exact(8))[0]
            mask = self._recv_exact(4) if masked else b""
            payload = self._recv_exact(length)
            if masked:
                payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
            if opcode == 8:
                raise RuntimeError("websocket closed")
            if opcode == 9:
                continue
            if opcode not in (1, 0):
                continue
            return json.loads(payload.decode("utf-8"))


def with_client(func):
    def wrapper(args: argparse.Namespace) -> int:
        with TempAppServer() as port:
            with WebSocketJsonRpc(port) as client:
                return func(args, client)

    return wrapper


def call_or_raise(client: WebSocketJsonRpc, method: str, params: Any = None) -> Any:
    response = client.request(method, params)
    if "error" in response:
        raise RuntimeError(f"{method} failed: {response['error']}")
    return response.get("result")


def skill_list(client: WebSocketJsonRpc, cwd: str, force_reload: bool) -> list[dict[str, Any]]:
    result = call_or_raise(client, "skills/list", {"cwds": [cwd], "forceReload": force_reload})
    return result["data"][0]["skills"]


def summarize(skills: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "skillCount": len(skills),
        "enabledCount": sum(1 for item in skills if item.get("enabled")),
        "disabledCount": sum(1 for item in skills if not item.get("enabled")),
    }


def recent_session_files(days: int) -> list[pathlib.Path]:
    cutoff = time.time() - days * 86400
    files: set[pathlib.Path] = set()
    for pattern in (
        CODEX_HOME / "archived_sessions" / "*.jsonl",
        CODEX_HOME / "sessions" / "**" / "*.jsonl",
    ):
        for raw in glob.glob(str(pattern), recursive=True):
            path = pathlib.Path(raw)
            try:
                if path.stat().st_mtime >= cutoff:
                    files.add(path)
            except OSError:
                continue
    return sorted(files)


def collect_used_skill_paths(days: int) -> dict[str, list[dict[str, str]]]:
    used: dict[str, list[dict[str, str]]] = {}

    def add(path: str, source: str, timestamp: str) -> None:
        path = normalize_path(path)
        used.setdefault(path, []).append({"source": source, "timestamp": timestamp})

    for session in recent_session_files(days):
        try:
            with session.open("r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    payload = event.get("payload") or {}
                    if event.get("type") != "response_item":
                        continue
                    if payload.get("type") != "function_call":
                        continue
                    arguments = payload.get("arguments") or ""
                    if "SKILL.md" not in arguments:
                        continue
                    for match in SESSION_PATH_RE.finditer(arguments):
                        add(match.group(1), str(session), event.get("timestamp", ""))
        except OSError:
            continue

    omo_dir = CODEX_HOME / "plugins" / "data" / "omo-sisyphuslabs" / "sessions"
    cutoff = time.time() - days * 86400
    for raw in glob.glob(str(omo_dir / "*.json")):
        path = pathlib.Path(raw)
        try:
            stat = path.stat()
            if stat.st_mtime < cutoff:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        timestamp = dt.datetime.fromtimestamp(stat.st_mtime).isoformat()
        for match in SESSION_PATH_RE.finditer(text):
            add(match.group(1), str(path), timestamp)

    return used


def map_used_to_current(
    skills: list[dict[str, Any]],
    used_paths: dict[str, list[dict[str, str]]],
) -> tuple[set[str], dict[str, list[dict[str, str]]]]:
    by_path = {normalize_path(item["path"]): item for item in skills}
    by_dir: dict[str, list[dict[str, Any]]] = {}
    for item in skills:
        dirname = pathlib.Path(item["path"]).parent.name
        by_dir.setdefault(dirname, []).append(item)

    used_current_paths: set[str] = set()
    evidence_by_current_path: dict[str, list[dict[str, str]]] = {}
    for path, evidence in used_paths.items():
        normalized = normalize_path(path)
        current = by_path.get(normalized)
        if current:
            used_current_paths.add(current["path"])
            evidence_by_current_path.setdefault(current["path"], []).extend(evidence)
            continue
        dirname = pathlib.Path(normalized).parent.name
        matches = [
            item
            for item in by_dir.get(dirname, [])
            if item["name"] == dirname
            or item["name"].endswith(f":{dirname}")
            or item["path"].endswith(f"/{dirname}/SKILL.md")
        ]
        if len(matches) == 1:
            used_current_paths.add(matches[0]["path"])
            evidence_by_current_path.setdefault(matches[0]["path"], []).extend(evidence)
    return used_current_paths, evidence_by_current_path


def usage_count(evidence: list[dict[str, str]]) -> int:
    sources = {item.get("source", "") for item in evidence if item.get("source")}
    return len(sources) if sources else len(evidence)


def audit_unused(
    skills: list[dict[str, Any]],
    days: int,
    max_uses: int,
    include_system: bool,
    keep_names: list[str],
) -> dict[str, Any]:
    used_raw = collect_used_skill_paths(days)
    used_current, evidence = map_used_to_current(skills, used_raw)
    keep_set = set(keep_names)
    enabled = [item for item in skills if item.get("enabled")]
    candidates = []
    used_enabled = []
    for item in enabled:
        item_evidence = evidence.get(item["path"], [])
        item_usage_count = usage_count(item_evidence)
        if item["path"] in used_current and item_usage_count > max_uses:
            used_enabled.append(
                {
                    "name": item["name"],
                    "scope": item["scope"],
                    "path": item["path"],
                    "usageCount": item_usage_count,
                    "evidenceCount": len(item_evidence),
                }
            )
            continue
        if item.get("scope") == "system" and not include_system:
            continue
        if item["name"] in keep_set:
            continue
        candidates.append(
            {
                "name": item["name"],
                "scope": item["scope"],
                "path": item["path"],
                "usageCount": item_usage_count,
                "evidenceCount": len(item_evidence),
            }
        )

    return {
        "days": days,
        "maxUses": max_uses,
        "summary": summarize(skills),
        "usedEnabledCount": len(used_enabled),
        "disableCandidateCount": len(candidates),
        "usedEnabled": sorted(used_enabled, key=lambda item: (item["name"], item["path"])),
        "disableCandidates": sorted(candidates, key=lambda item: (item["scope"], item["name"], item["path"])),
        "rawUsedSkillPathCount": len(used_raw),
    }


def backup_dir(prefix: str) -> pathlib.Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = DEFAULT_BACKUP_ROOT / f"{prefix}-{stamp}"
    path.mkdir(parents=True, exist_ok=False)
    return path


@with_client
def cmd_list(args: argparse.Namespace, client: WebSocketJsonRpc) -> int:
    skills = skill_list(client, args.cwd, args.force_reload)
    output = {"summary": summarize(skills), "skills": skills if args.full else None}
    if args.json:
        json_print(output)
    else:
        print(json.dumps(output["summary"], ensure_ascii=False))
        for item in sorted(skills, key=lambda entry: (not entry["enabled"], entry["scope"], entry["name"], entry["path"])):
            if args.enabled and not item["enabled"]:
                continue
            if args.disabled and item["enabled"]:
                continue
            state = "enabled" if item["enabled"] else "disabled"
            print(f"{state}\t{item['scope']}\t{item['name']}\t{item['path']}")
    return 0


@with_client
def cmd_audit_unused(args: argparse.Namespace, client: WebSocketJsonRpc) -> int:
    skills = skill_list(client, args.cwd, True)
    audit = audit_unused(skills, args.days, args.max_uses, args.include_system, args.keep_name)
    json_print(audit)
    return 0


@with_client
def cmd_disable_unused(args: argparse.Namespace, client: WebSocketJsonRpc) -> int:
    skills = skill_list(client, args.cwd, True)
    audit = audit_unused(skills, args.days, args.max_uses, args.include_system, args.keep_name)
    candidates = audit["disableCandidates"]
    ui_count_note = (
        "The Codex desktop Skills tab count is the total discovered skill count, "
        "not the enabled count. It is expected to stay unchanged after disabling skills."
    )
    if not args.apply:
        json_print({"dryRun": True, "wouldDisable": len(candidates), "uiCountNote": ui_count_note, "audit": audit})
        return 0

    target_dir = pathlib.Path(args.backup_dir) if args.backup_dir else backup_dir("skill-disable-unused")
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "skills-list-before.json").write_text(json.dumps(skills, ensure_ascii=False, indent=2), encoding="utf-8")
    (target_dir / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    (target_dir / "disable-candidates.json").write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")

    results = []
    for item in candidates:
        response = client.request("skills/config/write", {"path": item["path"], "enabled": False})
        results.append({"name": item["name"], "path": item["path"], "ok": "error" not in response, "response": response})
    after = skill_list(client, args.cwd, True)
    result = {
        "backupDir": str(target_dir),
        "attempted": len(results),
        "failed": [item for item in results if not item["ok"]],
        "beforeSummary": summarize(skills),
        "afterSummary": summarize(after),
        "uiCountNote": ui_count_note,
        "nextVerificationCommand": "python3 scripts/codex_skill_admin.py verify --cwd \"$PWD\"",
        "results": results,
    }
    (target_dir / "disable-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    json_print(result)
    return 1 if result["failed"] else 0


@with_client
def cmd_restore(args: argparse.Namespace, client: WebSocketJsonRpc) -> int:
    backup = pathlib.Path(args.backup_dir)
    candidates_file = backup / "disable-candidates.json"
    if not candidates_file.exists():
        raise FileNotFoundError(f"missing {candidates_file}")
    candidates = json.loads(candidates_file.read_text(encoding="utf-8"))
    results = []
    for item in candidates:
        response = client.request("skills/config/write", {"path": item["path"], "enabled": True})
        results.append({"name": item.get("name"), "path": item["path"], "ok": "error" not in response, "response": response})
    result = {"restored": len(results), "failed": [item for item in results if not item["ok"]], "results": results}
    (backup / "restore-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    json_print(result)
    return 1 if result["failed"] else 0


@with_client
def cmd_set(args: argparse.Namespace, client: WebSocketJsonRpc) -> int:
    requested = [{"selector": path, "type": "path"} for path in args.path] + [
        {"selector": name, "type": "name"} for name in args.name
    ]
    if not args.apply:
        json_print({"dryRun": True, "enabled": args.enabled, "wouldSet": len(requested), "selectors": requested})
        return 0
    results = []
    for path in args.path:
        response = client.request("skills/config/write", {"path": path, "enabled": args.enabled})
        results.append({"selector": path, "ok": "error" not in response, "response": response})
    for name in args.name:
        response = client.request("skills/config/write", {"name": name, "enabled": args.enabled})
        results.append({"selector": name, "ok": "error" not in response, "response": response})
    json_print({"attempted": len(results), "failed": [item for item in results if not item["ok"]], "results": results})
    return 1 if any(not item["ok"] for item in results) else 0


def prompt_available_skill_count(prompt: str) -> int:
    proc = subprocess.run(
        ["codex", "debug", "prompt-input", prompt],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "codex debug prompt-input failed")
    strings = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', proc.stdout)
    text = "\n".join(bytes(item, "utf-8").decode("unicode_escape") for item in strings)
    count = 0
    active = False
    for line in text.splitlines():
        if line.startswith("### Available skills"):
            active = True
            continue
        if line.startswith("### How to use skills"):
            active = False
        if active and line.startswith("- "):
            count += 1
    return count


def cmd_prompt_count(args: argparse.Namespace) -> int:
    try:
        count = prompt_available_skill_count(args.prompt)
    except RuntimeError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    json_print({"availableSkillCount": count})
    return 0


@with_client
def cmd_verify(args: argparse.Namespace, client: WebSocketJsonRpc) -> int:
    skills = skill_list(client, args.cwd, True)
    summary = summarize(skills)
    report: dict[str, Any] = {
        "summary": summary,
        "ui": {
            "skillTabCount": summary["skillCount"],
            "countMeaning": "Total discovered skills. This matches the Codex desktop Skills tab count and does not drop when skills are disabled.",
        },
        "effectiveVisibility": {
            "enabledCount": summary["enabledCount"],
            "disabledCount": summary["disabledCount"],
        },
        "successCriteria": [
            "Disabled target skills appear in list --disabled.",
            "enabledCount drops after disabling skills.",
            "availableSkillCount drops after disabling skills that were previously injected into the prompt.",
            "The desktop UI Skills tab count may remain unchanged because it counts total discovered skills.",
        ],
    }
    try:
        report["effectiveVisibility"]["availableSkillCount"] = prompt_available_skill_count(args.prompt)
    except RuntimeError as exc:
        report["effectiveVisibility"]["availableSkillCountError"] = str(exc)
    json_print(report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Codex skills through the official local app-server API.")
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list")
    list_p.add_argument("--cwd", default=os.getcwd())
    list_p.add_argument("--force-reload", action="store_true")
    list_p.add_argument("--json", action="store_true")
    list_p.add_argument("--full", action="store_true")
    list_p.add_argument("--enabled", action="store_true")
    list_p.add_argument("--disabled", action="store_true")
    list_p.set_defaults(func=cmd_list)

    audit_p = sub.add_parser("audit-unused")
    audit_p.add_argument("--cwd", default=os.getcwd())
    audit_p.add_argument("--days", type=int, default=30)
    audit_p.add_argument("--max-uses", type=int, default=0)
    audit_p.add_argument("--include-system", action="store_true")
    audit_p.add_argument("--keep-system", action="store_true", help=argparse.SUPPRESS)
    audit_p.add_argument("--keep-name", action="append", default=[])
    audit_p.set_defaults(func=cmd_audit_unused)

    disable_p = sub.add_parser("disable-unused")
    disable_p.add_argument("--cwd", default=os.getcwd())
    disable_p.add_argument("--days", type=int, default=30)
    disable_p.add_argument("--max-uses", type=int, default=0)
    disable_p.add_argument("--apply", action="store_true")
    disable_p.add_argument("--backup-dir")
    disable_p.add_argument("--include-system", action="store_true")
    disable_p.add_argument("--keep-system", action="store_true", help=argparse.SUPPRESS)
    disable_p.add_argument("--keep-name", action="append", default=[])
    disable_p.set_defaults(func=cmd_disable_unused)

    restore_p = sub.add_parser("restore")
    restore_p.add_argument("--backup-dir", required=True)
    restore_p.set_defaults(func=cmd_restore)

    set_p = sub.add_parser("set")
    set_p.add_argument("--enabled", action=argparse.BooleanOptionalAction, required=True)
    set_p.add_argument("--path", action="append", default=[])
    set_p.add_argument("--name", action="append", default=[])
    set_p.add_argument("--apply", action="store_true")
    set_p.set_defaults(func=cmd_set)

    prompt_p = sub.add_parser("prompt-count")
    prompt_p.add_argument("--prompt", default="skill visibility check")
    prompt_p.set_defaults(func=cmd_prompt_count)

    verify_p = sub.add_parser("verify")
    verify_p.add_argument("--cwd", default=os.getcwd())
    verify_p.add_argument("--prompt", default="skill visibility check")
    verify_p.set_defaults(func=cmd_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "command", "") == "set" and not args.path and not args.name:
        raise SystemExit("set requires at least one --path or --name")
    if hasattr(args, "days") and args.days < 1:
        raise SystemExit("--days must be at least 1")
    if hasattr(args, "max_uses") and args.max_uses < 0:
        raise SystemExit("--max-uses must be at least 0")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
