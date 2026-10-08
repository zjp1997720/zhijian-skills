#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import base64
import datetime as dt
import glob
import json
import os
import pathlib
import re
import shlex
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
    normalized = os.path.normpath(os.path.expanduser(path))
    mappings: list[tuple[str, str]] = []
    for mapping in os.environ.get(PATH_ALIASES_ENV, "").split(os.pathsep):
        if not mapping or "=" not in mapping:
            continue
        source, target = mapping.split("=", 1)
        mappings.append(
            (
                os.path.normpath(os.path.expanduser(source)),
                os.path.normpath(os.path.expanduser(target)),
            )
        )
    # Longest roots first avoids a short alias accidentally matching a sibling
    # such as /old/root2.  Apply one pass per mapping; aliases are intentionally
    # treated as path roots, rather than arbitrary string substitutions.
    for source, target in sorted(mappings, key=lambda item: len(item[0]), reverse=True):
        if normalized == source:
            normalized = target
        elif normalized.startswith(source + os.sep):
            normalized = target + normalized[len(source) :]
    return os.path.normpath(normalized)


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


READ_COMMANDS = frozenset(
    {
        "awk",
        "bat",
        "cat",
        "head",
        "less",
        "more",
        "nl",
        "sed",
        "tail",
    }
)
SEARCH_COMMANDS = frozenset({"grep", "rg", "ripgrep"})
READ_TOOL_NAME_RE = re.compile(r"(?:^|[_:.\-])(read|open|cat|head|tail|sed)(?:$|[_:.\-])", re.I)
RESULT_TYPES = frozenset(
    {
        "function_call_output",
        "custom_tool_call_output",
        "tool_result",
        "tool_call_output",
        "exec_command_output",
    }
)
CALL_TYPES = frozenset({"function_call", "custom_tool_call"})
SUCCESS_STATUSES = frozenset({"completed", "complete", "ok", "success", "succeeded", "done"})
FAILED_STATUSES = frozenset({"failed", "failure", "error", "errored", "cancelled", "canceled"})
CURRENT_SESSION_ENV_VARS = (
    "CODEX_SKILL_ADMIN_SESSION",
    "CODEX_SESSION_FILE",
    "CODEX_SESSION_PATH",
    "CODEX_SESSION_ID",
    "CODEX_THREAD_ID",
)


def parse_event_timestamp(value: Any) -> float | None:
    """Return a JSON event timestamp as Unix seconds, or None when unsupported."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        # Millisecond timestamps are common in exported event logs.
        return number / 1000 if number > 100_000_000_000 else number
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        number = None
    if number is not None:
        return number / 1000 if number > 100_000_000_000 else number
    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.timestamp()


def event_timestamp(event: dict[str, Any]) -> str:
    payload = _event_payload(event)
    for candidate in (
        event.get("timestamp"),
        event.get("created_at"),
        event.get("createdAt"),
        payload.get("timestamp"),
        payload.get("created_at"),
        payload.get("createdAt"),
    ):
        if candidate not in (None, ""):
            return str(candidate)
    return ""


def _event_payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    if isinstance(payload, dict):
        if "type" not in payload and event.get("type") in CALL_TYPES | RESULT_TYPES:
            return {**event, **payload}
        return payload
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, dict):
            return parsed
    return event


def _json_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "[{":
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def _tool_call(event: dict[str, Any]) -> dict[str, Any] | None:
    payload = _event_payload(event)
    kind = payload.get("type")
    if kind not in CALL_TYPES:
        return None
    raw_input = payload.get("arguments") if kind == "function_call" else payload.get("input")
    if raw_input is None:
        raw_input = payload.get("arguments", payload.get("params"))
    return {
        "type": kind,
        "name": str(payload.get("name") or payload.get("tool_name") or ""),
        "input": raw_input,
        "call_id": payload.get("call_id") or payload.get("callId") or payload.get("id"),
        "timestamp": event_timestamp(event),
        "raw": payload,
    }


def _tool_result(event: dict[str, Any]) -> dict[str, Any] | None:
    payload = _event_payload(event)
    kind = payload.get("type")
    if kind not in RESULT_TYPES:
        return None
    return {
        "type": kind,
        "call_id": payload.get("call_id") or payload.get("callId") or payload.get("id"),
        "timestamp": event_timestamp(event),
        "payload": payload,
    }


def _skill_path(raw: Any, workdir: str | None = None) -> str | None:
    if not isinstance(raw, str):
        return None
    path = raw.strip().strip("'\"`<>,;()[]{}")
    if path.startswith("file://"):
        path = path[7:]
    if not path.endswith("SKILL.md"):
        return None
    if path in {"SKILL.md", "./SKILL.md"} and not workdir:
        return None
    if not (path.startswith(("/", "~", "./", "../")) or os.sep in path):
        return None
    if not os.path.isabs(os.path.expanduser(path)):
        if not workdir:
            return None
        path = os.path.join(os.path.abspath(os.path.expanduser(workdir)), path)
    return normalize_path(path)


def _direct_paths(value: Any, workdir: str | None = None) -> list[str]:
    """Extract paths from structured file-read arguments, never free text."""
    value = _json_value(value)
    if not isinstance(value, dict):
        return []
    paths: list[str] = []
    for key in ("path", "file", "filename", "file_path", "filePath", "uri"):
        candidate = value.get(key)
        if isinstance(candidate, str):
            path = _skill_path(candidate, workdir)
            if path:
                paths.append(path)
    return sorted(set(paths))


def _shell_read_paths(command: str, workdir: str | None = None) -> list[str]:
    """Find SKILL.md operands of commands that actually read file contents."""
    paths: set[str] = set()
    for segment in re.split(r"(?:&&|\|\||[;|])", command):
        segment = segment.strip()
        if not segment:
            continue
        try:
            tokens = shlex.split(segment, posix=True)
        except ValueError:
            continue
        if not tokens:
            continue
        command_name = os.path.basename(tokens[0]).lower()
        # `bash -lc 'cat /x/SKILL.md'` is a common extra wrapper around exec.
        if command_name in {"bash", "sh", "zsh", "fish"}:
            for index, token in enumerate(tokens[:-1]):
                if token in {"-c", "-lc", "--command"}:
                    paths.update(_shell_read_paths(tokens[index + 1], workdir))
            continue
        if command_name in {"python", "python3", "node", "ruby", "perl"}:
            script_parts = [
                token
                for index, token in enumerate(tokens)
                if index and tokens[index - 1] in {"-c", "-e", "--eval"}
            ]
            script = " ".join(script_parts)
            if re.search(r"(?:open|read_text|readFile|readFileSync|\.read\s*\()", script, re.I):
                for match in SESSION_PATH_RE.finditer(script):
                    path = _skill_path(match.group(1), workdir)
                    if path:
                        paths.add(path)
            continue
        if command_name == "rg" and "--files" in tokens:
            continue
        if command_name not in READ_COMMANDS | SEARCH_COMMANDS:
            # Shell input redirection still proves a read for a known file.
            if "<" in tokens:
                index = tokens.index("<")
                for token in tokens[index + 1 :]:
                    path = _skill_path(token, workdir)
                    if path:
                        paths.add(path)
            continue
        skip_output_target = False
        for token in tokens[1:]:
            if skip_output_target:
                skip_output_target = False
                continue
            if token in {">", ">>", "1>", "2>", "1>>", "2>>"}:
                skip_output_target = True
                continue
            if token.startswith((">", "1>", "2>")):
                continue
            if token.startswith("-"):
                # Support --file=/path/SKILL.md while skipping flags that are
                # merely textual mentions.
                token = token.partition("=")[2] if "=" in token else ""
            path = _skill_path(token, workdir)
            if path:
                paths.add(path)
    return sorted(paths)


def _js_property_string(source: str, property_name: str) -> str | None:
    """Decode one static quoted JS object property without evaluating JS."""
    match = re.search(rf"\b{re.escape(property_name)}\s*:\s*([\"'`])", source)
    if not match:
        return None
    quote = match.group(1)
    start = match.end()
    escaped = False
    end = start
    for index in range(start, len(source)):
        char = source[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == quote:
            end = index
            break
    if end == start and (end >= len(source) or source[end] != quote):
        return None
    literal = source[start:end]
    try:
        if quote == '"':
            return json.loads('"' + literal + '"')
        if quote == "'":
            value = ast.literal_eval("'" + literal + "'")
            return value if isinstance(value, str) else None
        # Backtick strings are accepted only when they contain no interpolation.
        if "${" in literal:
            return None
        return bytes(literal, "utf-8").decode("unicode_escape")
    except (SyntaxError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _js_exec_input(source: str) -> tuple[str | None, str | None]:
    """Read static cmd/workdir properties from a functions.exec JS wrapper."""
    if "exec_command" not in source:
        return None, None
    return _js_property_string(source, "cmd") or _js_property_string(source, "command"), _js_property_string(source, "workdir")


def _js_unknown_paths(source: str, workdir: str | None = None) -> list[str]:
    """Retain explicit SKILL.md paths from unparseable JS as unknown evidence."""
    paths: set[str] = set()
    for match in SESSION_PATH_RE.finditer(source):
        path = _skill_path(match.group(1), workdir)
        if path:
            paths.add(path)
    return sorted(paths)


def _call_read_paths(call: dict[str, Any]) -> tuple[list[str], bool]:
    name = call["name"].lower()
    value = _json_value(call.get("input"))
    workdir = None
    if isinstance(value, dict):
        for key in ("workdir", "cwd", "working_directory", "workingDirectory"):
            if isinstance(value.get(key), str):
                workdir = value[key]
                break
    wrapper = name in {"functions.exec", "functions.exec_command", "exec", "exec_command"}
    if wrapper:
        command: str | None = None
        if isinstance(value, str):
            if "exec_command" in value:
                command, js_workdir = _js_exec_input(value)
                if js_workdir:
                    workdir = js_workdir
                if command is None:
                    # Do not execute or fully parse arbitrary JS.  Explicit
                    # paths remain as low-confidence unknown evidence.
                    return _js_unknown_paths(value, workdir), False
            else:
                command = value
        elif isinstance(value, dict):
            for key in ("cmd", "command", "shell_command", "shellCommand", "script"):
                if isinstance(value.get(key), str):
                    command = value[key]
                    break
        if command:
            return _shell_read_paths(command, workdir), True
        return [], False
    if READ_TOOL_NAME_RE.search(name):
        return _direct_paths(value, workdir), True
    # An unknown custom tool carrying a structured path is an auditable intent,
    # but it cannot be called successful until its result is understood.
    paths = _direct_paths(value, workdir)
    return paths, False


ERROR_PREFIX_RE = re.compile(
    r"^\s*(?:error|failed|failure)\s*[:!]|^\s*(?:permission denied|command not found|"
    r"command failed|command exited with code\s*[1-9]|non[- ]zero exit)\b|"
    r"^\s*(?:tool|exec|command)\s+error\s*[:!]",
    re.I,
)
MISSING_FILE_RE = re.compile(
    r"(?:^\s*no such file(?: or directory)?|\b(?:cat|sed|head|tail|awk|grep|rg):[^\n]*(?:no such file|is a directory))",
    re.I,
)
PENDING_TEXT_RE = re.compile(
    r"(?:^\s*(?:pending|in[_ -]?progress|queued|script running\b|running with cell id)|\bscript running with cell id)",
    re.I,
)
WRAPPED_SUCCESS_RE = re.compile(r"^\s*script completed\b", re.I)
EXIT_CODE_RE = re.compile(r'(?:exit[_ ]code["\']?\s*[:=]?\s*|process exited with code\s+)(-?\d+)', re.I)


def _result_value_statuses(value: Any, depth: int = 0) -> list[str]:
    """Return every status found in a result, preserving failure/unknown evidence."""
    if depth > 8:
        return ["unknown"]
    if value is None:
        return []
    if isinstance(value, bool):
        return ["success" if value else "unknown"]
    if isinstance(value, (int, float)):
        return ["success" if value == 0 else "failed"]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        parsed = _json_value(text)
        if parsed is not value:
            return _result_value_statuses(parsed, depth + 1)
        # App wrappers often prefix JSON with `Script completed`; inspect all
        # embedded signals instead of treating the wrapper as success.
        exit_codes = [int(match.group(1)) for match in EXIT_CODE_RE.finditer(text)]
        if any(code != 0 for code in exit_codes):
            return ["failed"]
        if ERROR_PREFIX_RE.search(text) or MISSING_FILE_RE.search(text):
            return ["failed"]
        if PENDING_TEXT_RE.search(text):
            return ["unknown"]
        if WRAPPED_SUCCESS_RE.search(text):
            return ["success"] if exit_codes else ["unknown"]
        return ["success"]
    if isinstance(value, list):
        statuses: list[str] = []
        for item in value:
            statuses.extend(_result_value_statuses(item, depth + 1))
        return statuses or ["unknown"]
    if not isinstance(value, dict):
        return ["unknown"]

    statuses: list[str] = []
    payload_type = str(value.get("type") or "").lower()
    if payload_type in FAILED_STATUSES or payload_type in {"error", "tool_error"}:
        statuses.append("failed")
    for key in ("is_error", "isError", "failed"):
        if value.get(key) is True:
            statuses.append("failed")
        elif value.get(key) is False:
            statuses.append("success")
    status = str(value.get("status") or "").lower()
    if status in FAILED_STATUSES:
        statuses.append("failed")
    elif status in SUCCESS_STATUSES:
        statuses.append("success")
    elif status in {"pending", "in_progress", "queued", "running"}:
        statuses.append("unknown")
    exit_code = value.get("exit_code", value.get("exitCode"))
    if isinstance(exit_code, (int, float)):
        statuses.append("success" if exit_code == 0 else "failed")
    for key in ("error", "errors"):
        if value.get(key):
            statuses.append("failed")

    found_content = False
    for key in ("output", "result", "content", "data", "text", "stdout", "stderr"):
        if key in value:
            found_content = True
            statuses.extend(_result_value_statuses(value[key], depth + 1))
    if not found_content and not statuses:
        statuses.append("unknown")
    return statuses


def _result_status(result: dict[str, Any]) -> str:
    """Classify a tool result with failure and unknown states taking priority."""
    statuses = _result_value_statuses(result.get("payload") or {})
    if "failed" in statuses:
        return "failed"
    if "unknown" in statuses:
        return "unknown"
    return "success" if statuses and all(status == "success" for status in statuses) else "unknown"


def _excluded_session(session: pathlib.Path, session_keys: set[str]) -> bool:
    if not session_keys:
        return False
    normalized = normalize_path(str(session))
    return (
        normalized in session_keys
        or session.name in session_keys
        or any(key and key in session.stem for key in session_keys if os.sep not in key)
    )


def _self_audit_call(call: dict[str, Any]) -> bool:
    text = json.dumps(call.get("input"), ensure_ascii=False) if not isinstance(call.get("input"), str) else call["input"]
    return "codex_skill_admin.py" in text and re.search(r"\b(?:audit-unused|disable-unused)\b", text) is not None


def _new_usage_report() -> dict[str, Any]:
    return {
        "successful": {},
        "read_intents": {},
        "unknown": {},
        "failed": {},
        "unsupported": [],
        "outside_window_count": 0,
        "missing_timestamp_count": 0,
        "excluded_session_count": 0,
    }


def _append_evidence(bucket: dict[str, list[dict[str, Any]]], path: str, evidence: dict[str, Any]) -> None:
    bucket.setdefault(path, []).append(evidence)


def _collect_events(
    events: list[dict[str, Any]],
    source: pathlib.Path,
    cutoff: float,
    now: float,
    report: dict[str, Any],
    excluded_current_audit: bool,
) -> None:
    calls: list[tuple[int, dict[str, Any]]] = []
    results: list[tuple[int, dict[str, Any]]] = []
    for index, event in enumerate(events):
        call = _tool_call(event)
        if call:
            call["event_index"] = index
            call["session"] = str(source)
            calls.append((index, call))
        result = _tool_result(event)
        if result:
            result["event_index"] = index
            results.append((index, result))

    for index, call in calls:
        paths, recognized = _call_read_paths(call)
        if not paths:
            continue
        if excluded_current_audit and _self_audit_call(call):
            continue
        timestamp_text = call.get("timestamp", "")
        timestamp = parse_event_timestamp(timestamp_text)
        if timestamp is None:
            report["missing_timestamp_count"] += len(paths)
            status = "unknown"
        elif timestamp < cutoff or timestamp > now:
            report["outside_window_count"] += len(paths)
            continue
        else:
            status = "unknown"
            call_id = call.get("call_id")
            matching = [
                candidate
                for result_index, candidate in results
                if result_index > index and call_id is not None and candidate.get("call_id") == call_id
            ]
            if matching:
                status = _result_status(matching[0])
            if not recognized:
                # A result from an unknown tool can be successful for that
                # tool, but it does not prove that the SKILL.md was read.
                status = "unknown"
        for path in paths:
            evidence: dict[str, Any] = {
                "path": path,
                "source": str(source),
                "session": str(source),
                "timestamp": str(timestamp_text),
                "status": status,
                "confidence": "high" if status == "success" else "low",
            }
            _append_evidence(report["read_intents"], path, evidence)
            if status == "success":
                _append_evidence(report["successful"], path, evidence)
            elif status == "failed":
                _append_evidence(report["failed"], path, evidence)
            else:
                _append_evidence(report["unknown"], path, evidence)
            if not recognized:
                report["unsupported"].append({**evidence, "path": path, "tool": call.get("name", "")})


def _session_keys(values: list[str] | None) -> set[str]:
    keys = {normalize_path(value) for value in (values or []) if value}
    for env_name in CURRENT_SESSION_ENV_VARS:
        value = os.environ.get(env_name)
        if value:
            keys.add(normalize_path(value))
            keys.add(pathlib.Path(value).name)
    return keys


def _omo_events(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        events: list[dict[str, Any]] = []
        for item in value:
            events.extend(_omo_events(item))
        return events
    if isinstance(value, dict):
        if _tool_call(value) or _tool_result(value):
            return [value]
        events: list[dict[str, Any]] = []
        for key in ("events", "records", "items", "messages"):
            nested = value.get(key)
            if isinstance(nested, (dict, list)):
                events.extend(_omo_events(nested))
        return events
    return []


def collect_skill_usage(
    days: int,
    *,
    exclude_sessions: list[str] | None = None,
    exclude_current_audit: bool = True,
    now: float | None = None,
) -> dict[str, Any]:
    """Collect proven reads plus separate uncertain/read-intent evidence."""
    now = time.time() if now is None else now
    cutoff = now - days * 86400
    report = _new_usage_report()
    excluded = _session_keys(exclude_sessions)
    for session in recent_session_files(days):
        if _excluded_session(session, excluded):
            report["excluded_session_count"] += 1
            continue
        events: list[dict[str, Any]] = []
        try:
            with session.open("r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(event, dict):
                        events.append(event)
        except OSError:
            continue
        _collect_events(events, session, cutoff, now, report, exclude_current_audit)

    # OMO exports are supported when they retain the same structured tool
    # events.  A bare SKILL.md fingerprint is intentionally unknown and is not
    # promoted to successful usage.
    omo_dir = CODEX_HOME / "plugins" / "data" / "omo-sisyphuslabs" / "sessions"
    for raw in glob.glob(str(omo_dir / "*.json")):
        path = pathlib.Path(raw)
        if _excluded_session(path, excluded):
            report["excluded_session_count"] += 1
            continue
        try:
            stat = path.stat()
            if stat.st_mtime < cutoff:
                continue
            parsed = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, json.JSONDecodeError):
            continue
        events = _omo_events(parsed)
        if events:
            _collect_events(events, path, cutoff, now, report, exclude_current_audit)
    # Keep both spellings available to callers while the CLI uses the clearer
    # camelCase labels below.  The dictionaries are intentionally shared so
    # no evidence can drift between compatibility views.
    report["read_intent"] = report["read_intents"]
    return report


def collect_used_skill_paths(
    days: int,
    *,
    exclude_sessions: list[str] | None = None,
    exclude_current_audit: bool = True,
    now: float | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Backward-compatible view containing only high-confidence successful reads."""
    return collect_skill_usage(
        days,
        exclude_sessions=exclude_sessions,
        exclude_current_audit=exclude_current_audit,
        now=now,
    )["successful"]


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


def usage_count(evidence: list[dict[str, Any]]) -> int:
    sources = {
        item.get("session") or item.get("source", "")
        for item in evidence
        if item.get("session") or item.get("source")
    }
    return len(sources) if sources else len(evidence)


def audit_unused(
    skills: list[dict[str, Any]],
    days: int,
    max_uses: int,
    include_system: bool,
    keep_names: list[str],
    exclude_sessions: list[str] | None = None,
    exclude_current_audit: bool = True,
) -> dict[str, Any]:
    usage = collect_skill_usage(
        days,
        exclude_sessions=exclude_sessions,
        exclude_current_audit=exclude_current_audit,
    )
    used_raw = usage["successful"]
    uncertain_raw: dict[str, list[dict[str, Any]]] = {}
    for bucket_name in ("unknown", "failed"):
        for path, evidence in usage[bucket_name].items():
            uncertain_raw.setdefault(path, []).extend(evidence)
    used_current, evidence = map_used_to_current(skills, used_raw)
    uncertain_current, uncertain_evidence = map_used_to_current(skills, uncertain_raw)
    keep_set = set(keep_names)
    enabled = [item for item in skills if item.get("enabled")]
    candidates = []
    used_enabled = []
    uncertain_enabled = []
    for item in enabled:
        item_evidence = evidence.get(item["path"], [])
        item_uncertain = uncertain_evidence.get(item["path"], [])
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
        # A read intent with an unclassified or failed result is evidence about
        # this skill, but not proof of successful use. Keep it out of the
        # disable set so parser gaps cannot turn into an unsafe zero.
        if item["path"] in uncertain_current:
            uncertain_enabled.append(
                {
                    "name": item["name"],
                    "scope": item["scope"],
                    "path": item["path"],
                    "usageCount": item_usage_count,
                    "evidenceCount": len(item_evidence),
                    "readIntentCount": len(item_uncertain),
                    "reason": "read intent exists but successful result is not proven",
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
        "uncertainEnabledCount": len(uncertain_enabled),
        "disableCandidateCount": len(candidates),
        "usedEnabled": sorted(used_enabled, key=lambda item: (item["name"], item["path"])),
        "uncertainEnabled": sorted(uncertain_enabled, key=lambda item: (item["name"], item["path"])),
        "disableCandidates": sorted(candidates, key=lambda item: (item["scope"], item["name"], item["path"])),
        "rawUsedSkillPathCount": len(used_raw),
        "rawReadIntentSkillPathCount": len(usage["read_intents"]),
        "rawUnknownSkillPathCount": len(usage["unknown"]),
        "rawFailedSkillPathCount": len(usage["failed"]),
        "readIntent": usage["read_intents"],
        "read_intent": usage["read_intents"],
        "unknown": usage["unknown"],
        "failed": usage["failed"],
        "unsupported": usage["unsupported"],
        "unsupportedEvidenceCount": len(usage["unsupported"]),
        "outsideWindowCount": usage["outside_window_count"],
        "missingTimestampCount": usage["missing_timestamp_count"],
        "excludedSessionCount": usage["excluded_session_count"],
        "excludedSessions": sorted(set(exclude_sessions or [])),
        "excludeCurrentAudit": exclude_current_audit,
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
    audit = audit_unused(
        skills,
        args.days,
        args.max_uses,
        args.include_system,
        args.keep_name,
        getattr(args, "exclude_session", []),
        getattr(args, "exclude_current_audit", True),
    )
    json_print(audit)
    return 0


@with_client
def cmd_disable_unused(args: argparse.Namespace, client: WebSocketJsonRpc) -> int:
    skills = skill_list(client, args.cwd, True)
    audit = audit_unused(
        skills,
        args.days,
        args.max_uses,
        args.include_system,
        args.keep_name,
        getattr(args, "exclude_session", []),
        getattr(args, "exclude_current_audit", True),
    )
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
    audit_p.add_argument(
        "--exclude-session",
        action="append",
        default=[],
        help="exclude a session JSONL path (repeatable); current session env vars are excluded too",
    )
    audit_p.add_argument(
        "--exclude-current-audit",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="ignore tool calls that invoke codex_skill_admin audit-unused/disable-unused (default: true)",
    )
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
    disable_p.add_argument(
        "--exclude-session",
        action="append",
        default=[],
        help="exclude a session JSONL path (repeatable); current session env vars are excluded too",
    )
    disable_p.add_argument(
        "--exclude-current-audit",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="ignore tool calls that invoke codex_skill_admin audit-unused/disable-unused (default: true)",
    )
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
