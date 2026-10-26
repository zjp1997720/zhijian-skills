#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""复用本机 Codex OAuth 登录态进行文生图 / 图像编辑。

设计目标：
1. 纯 Python 标准库，无第三方依赖
2. 从 ~/.codex/auth.json 读取并按需刷新 token
3. 调用 chatgpt.com 的 codex responses SSE 接口
4. 从 SSE 事件中提取图片 base64，保存为本地 PNG
"""

from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import hashlib
import json
import mimetypes
import pathlib
import secrets
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request
import zlib
from fractions import Fraction
from typing import Any, Dict, Iterable, List, Optional, Tuple

AUTH_PATH = pathlib.Path("~/.codex/auth.json").expanduser()
RESPONSES_ENDPOINT = "https://chatgpt.com/backend-api/codex/responses"
REFRESH_ENDPOINT = "https://auth.openai.com/oauth/token"
REFRESH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
DEFAULT_RESPONSE_MODEL = "gpt-6-astra"
REQUEST_TIMEOUT = 300
TOKEN_EXPIRY_SKEW_SECONDS = 60
INSTRUCTIONS = (
    "You are an assistant that must fulfill image generation and image editing "
    "requests by using the image_generation tool when provided."
)
ASPECT_TO_SIZE = {
    "square": "1024x1024",
    "landscape": "1536x1024",
    "portrait": "1024x1536",
}
QUALITY_CHOICES = {"low", "medium", "high"}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


class CodexImageError(Exception):
    """可预期错误，适合直接反馈给用户。"""


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def print_json(payload: Dict[str, Any], *, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
    stream.flush()


def fail(message: str, *, details: Optional[str] = None, exit_code: int = 1) -> None:
    payload: Dict[str, Any] = {"success": False, "error": message}
    if details:
        payload["details"] = details
    print_json(payload, stream=sys.stderr)
    raise SystemExit(exit_code)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用本机 Codex OAuth 登录态调用 gpt-image-2 生图。",
    )
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt", help="直接传入 prompt 文本")
    prompt_group.add_argument("--prompt-file", help="从文件读取 prompt 文本")
    parser.add_argument(
        "--quality",
        choices=sorted(QUALITY_CHOICES),
        default="medium",
        help="图片质量，默认 medium",
    )
    parser.add_argument(
        "--aspect",
        choices=sorted(ASPECT_TO_SIZE.keys()),
        default="square",
        help="后端母版方向：landscape / square / portrait，默认 square",
    )
    parser.add_argument(
        "--out-dir",
        default=".",
        help="输出目录，默认当前目录",
    )
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        help="输入图，可传本地路径、http(s) URL 或 data URL；可重复传入",
    )
    parser.add_argument(
        "--reference-image",
        action="append",
        default=[],
        help="参考图，可传本地路径、http(s) URL 或 data URL；可重复传入",
    )
    parser.add_argument(
        "--model",
        default="gpt-image-2",
        help="image_generation tool 的模型名，默认 gpt-image-2",
    )
    parser.add_argument(
        "--response-model",
        default=DEFAULT_RESPONSE_MODEL,
        help="负责理解 prompt、参考图角色并调度生图工具的外层模型，默认 gpt-6-astra",
    )
    parser.add_argument(
        "--continue-from",
        help="从上一次运行 manifest 继续编辑：自动带入上一张成图与可复用参考图",
    )
    parser.add_argument(
        "--manifest-out",
        help="运行 manifest 的输出路径；默认与最终图片同目录、同名并追加 .manifest.json",
    )
    parser.add_argument(
        "--name",
        help="输出文件基础名（不含目录）：生成 <name>.png 与 <name>.png.manifest.json；同名已存在时不覆盖，自动追加 -2、-3",
    )
    return parser.parse_args(argv)


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt is not None:
        prompt = args.prompt
    else:
        prompt_path = pathlib.Path(args.prompt_file).expanduser()
        try:
            prompt = prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise CodexImageError(f"prompt 文件不存在：{prompt_path}") from exc
    prompt = prompt.strip()
    if not prompt:
        raise CodexImageError("prompt 为空，请提供 --prompt 或 --prompt-file。")
    return prompt


def load_auth_data() -> Dict[str, Any]:
    if not AUTH_PATH.exists():
        raise CodexImageError(
            f"未找到 {AUTH_PATH}。请先安装并登录 Codex CLI：codex auth login"
        )
    try:
        return json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CodexImageError(f"无法解析 {AUTH_PATH}：{exc}") from exc


def save_auth_data(auth_data: Dict[str, Any]) -> None:
    """写回 Codex auth.json。

    refresh_token 可能是单次使用的，刷新成功后必须持久化新 token。
    用临时文件 + replace 避免进程中断时写坏 auth.json。
    """
    AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(auth_data, ensure_ascii=False, indent=2) + "\n"
    tmp_path = AUTH_PATH.with_suffix(AUTH_PATH.suffix + ".tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    try:
        tmp_path.chmod(0o600)
    except OSError:
        pass
    tmp_path.replace(AUTH_PATH)


def pad_base64url(value: str) -> str:
    return value + "=" * (-len(value) % 4)


def decode_jwt_payload(token: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        raise CodexImageError("access_token 不是合法 JWT，无法解析 payload。")
    try:
        payload_bytes = base64.urlsafe_b64decode(pad_base64url(parts[1]))
        return json.loads(payload_bytes.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CodexImageError(f"无法解析 access_token JWT payload：{exc}") from exc


def token_expired(access_token: str) -> bool:
    payload = decode_jwt_payload(access_token)
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        return False
    now_ts = dt.datetime.now(dt.timezone.utc).timestamp()
    return now_ts >= (float(exp) - TOKEN_EXPIRY_SKEW_SECONDS)


def http_json_request(
    url: str,
    *,
    method: str = "POST",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[bytes] = None,
    timeout: int = REQUEST_TIMEOUT,
) -> Tuple[int, Dict[str, Any]]:
    request = urllib.request.Request(url=url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read().decode(charset, errors="replace")
            return response.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        details = raw.strip() or str(exc)
        raise CodexImageError(f"HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise CodexImageError(f"网络请求失败：{exc}") from exc
    except json.JSONDecodeError as exc:
        raise CodexImageError(f"服务端返回了非 JSON 数据：{exc}") from exc


def refresh_tokens_if_needed(auth_data: Dict[str, Any]) -> Dict[str, Any]:
    tokens = dict(auth_data.get("tokens") or {})
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    if not access_token:
        raise CodexImageError("auth.json 缺少 tokens.access_token。")

    try:
        expired = token_expired(access_token)
    except CodexImageError:
        # 如果 token 结构异常，仍然尝试直接刷新一次，避免因本地缓存格式差异误判。
        expired = True

    if not expired:
        return auth_data

    if not refresh_token:
        raise CodexImageError("access_token 已过期，且 auth.json 缺少 refresh_token。请重新运行 codex auth login")

    form = urllib.parse.urlencode(
        {
            "client_id": REFRESH_CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "User-Agent": "codex_cli_rs/0.0.0 (codex-image-gen)",
    }

    try:
        _, refresh_payload = http_json_request(
            REFRESH_ENDPOINT,
            method="POST",
            headers=headers,
            body=form,
        )
    except CodexImageError as exc:
        raise CodexImageError(
            "刷新 Codex access token 失败，请重新运行 codex auth login",
            ) from exc

    updated_tokens = dict(tokens)
    for key, value in refresh_payload.items():
        if key in {"access_token", "refresh_token", "id_token"} and value:
            updated_tokens[key] = value

    auth_data = dict(auth_data)
    auth_data["tokens"] = updated_tokens
    auth_data["last_refresh"] = utc_now_iso()
    save_auth_data(auth_data)
    return auth_data


def extract_account_id(auth_data: Dict[str, Any]) -> str:
    tokens = dict(auth_data.get("tokens") or {})
    access_token = tokens.get("access_token")
    if not access_token:
        raise CodexImageError("auth.json 缺少 tokens.access_token。")
    payload = decode_jwt_payload(access_token)

    # Codex CLI / ChatGPT token 的常见位置：
    # {"https://api.openai.com/auth": {"chatgpt_account_id": "..."}}
    openai_auth = payload.get("https://api.openai.com/auth")
    account_id = None
    if isinstance(openai_auth, dict):
        account_id = openai_auth.get("chatgpt_account_id")
    account_id = (
        account_id
        or payload.get("chatgpt_account_id")
        or payload.get("account_id")
        or tokens.get("account_id")
    )
    if not account_id:
        raise CodexImageError("无法从 access_token 或 auth.json 中提取 ChatGPT-Account-ID。")
    return str(account_id)


def encode_local_image(path_text: str) -> str:
    path = pathlib.Path(path_text).expanduser()
    if not path.exists():
        raise CodexImageError(f"图片不存在：{path}")
    mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{data}"


def normalize_image_source(value: str) -> str:
    value = value.strip()
    if not value:
        raise CodexImageError("收到空图片路径。")
    lowered = value.lower()
    if lowered.startswith("http://") or lowered.startswith("https://") or lowered.startswith("data:"):
        return value
    return encode_local_image(value)


def unique_sources(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def relocate_local_path(path: pathlib.Path, *, manifest_dir: pathlib.Path) -> pathlib.Path:
    """manifest 里存的是绝对路径；文件随 manifest 整体挪动后，回落到 manifest 所在目录找同名文件。"""
    if path.exists():
        return path
    sibling = manifest_dir / path.name
    if sibling.exists():
        return sibling
    return path


def reusable_manifest_source(entry: Any, *, manifest_dir: pathlib.Path) -> Optional[str]:
    if not isinstance(entry, dict) or entry.get("reusable") is False:
        return None
    source = entry.get("source")
    if not isinstance(source, str) or not source.strip():
        return None
    source = source.strip()
    lowered = source.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return source
    path = pathlib.Path(source).expanduser()
    if not path.is_absolute():
        path = manifest_dir / path
    return str(relocate_local_path(path, manifest_dir=manifest_dir).resolve())


def apply_continuation(args: argparse.Namespace) -> Optional[Dict[str, Any]]:
    if not args.continue_from:
        args.image = unique_sources(args.image)
        args.reference_image = unique_sources(args.reference_image)
        return None

    manifest_path = pathlib.Path(args.continue_from).expanduser().resolve()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CodexImageError(f"continuation manifest 不存在：{manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise CodexImageError(f"无法解析 continuation manifest：{exc}") from exc
    if not isinstance(manifest, dict):
        raise CodexImageError("continuation manifest 顶层必须是 JSON object。")

    output = manifest.get("output")
    previous_image: Optional[str] = None
    if isinstance(output, dict):
        final_entry = output.get("image")
        if isinstance(final_entry, dict):
            previous_image = reusable_manifest_source(
                final_entry,
                manifest_dir=manifest_path.parent,
            )
        elif isinstance(final_entry, str):
            previous_image = final_entry
    if not previous_image and isinstance(manifest.get("image"), str):
        previous_image = str(manifest["image"])
    if not previous_image:
        raise CodexImageError("continuation manifest 缺少可复用的上一张成图路径。")
    if not previous_image.lower().startswith(("http://", "https://")):
        previous_path = pathlib.Path(previous_image).expanduser()
        if not previous_path.is_absolute():
            previous_path = manifest_path.parent / previous_path
        previous_path = relocate_local_path(previous_path, manifest_dir=manifest_path.parent)
        previous_image = str(previous_path.resolve())
        if not pathlib.Path(previous_image).exists():
            raise CodexImageError(f"continuation manifest 指向的成图不存在：{previous_image}")

    carried_references: List[str] = []
    for entry in manifest.get("reference_images") or []:
        source = reusable_manifest_source(entry, manifest_dir=manifest_path.parent)
        if source:
            carried_references.append(source)

    args.image = unique_sources([previous_image, *args.image])
    args.reference_image = unique_sources([*carried_references, *args.reference_image])
    return {"path": str(manifest_path), "sha256": sha256_file(manifest_path)}


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def describe_image_source(value: str) -> Dict[str, Any]:
    source = value.strip()
    lowered = source.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return {"kind": "url", "source": source, "reusable": True}
    if lowered.startswith("data:"):
        return {
            "kind": "data_url",
            "reusable": False,
            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "note": "data URL 未写入 manifest；继续编辑时需重新传入原图",
        }
    path = pathlib.Path(source).expanduser().resolve()
    return {
        "kind": "local_file",
        "source": str(path),
        "reusable": True,
        "sha256": sha256_file(path),
    }


def aspect_ratio(aspect: str) -> Fraction:
    width_text, height_text = ASPECT_TO_SIZE[aspect].split("x", maxsplit=1)
    return Fraction(int(width_text), int(height_text))


def build_request_body(args: argparse.Namespace, prompt: str) -> Dict[str, Any]:
    content: List[Dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    for index, source in enumerate(args.image, start=1):
        content.append(
            {
                "type": "input_text",
                "text": (
                    f"Target/input image {index}: this is an image to edit or preserve as the primary canvas. "
                    "Apply the requested changes to it and preserve unspecified content."
                ),
            }
        )
        content.append(
            {
                "type": "input_image",
                "image_url": normalize_image_source(source),
            }
        )
    for index, source in enumerate(args.reference_image, start=1):
        content.append(
            {
                "type": "input_text",
                "text": (
                    f"Reference image {index}: use it only for identity, style, material, or constraint guidance. "
                    "Do not treat it as the target canvas and do not copy its layout unless the user explicitly asks."
                ),
            }
        )
        content.append(
            {
                "type": "input_image",
                "image_url": normalize_image_source(source),
            }
        )

    return {
        "model": args.response_model,
        "store": False,
        "instructions": INSTRUCTIONS,
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": content,
            }
        ],
        "tools": [
            {
                "type": "image_generation",
                "model": args.model,
                "size": ASPECT_TO_SIZE[args.aspect],
                "quality": args.quality,
                "output_format": "png",
                "background": "opaque",
                "partial_images": 1,
            }
        ],
        "tool_choice": {
            "type": "allowed_tools",
            "mode": "required",
            "tools": [{"type": "image_generation"}],
        },
        "stream": True,
    }


def extract_image_candidates(event_payload: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    finals: List[str] = []
    partials: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            node_type = node.get("type")
            result = node.get("result")
            if node_type == "image_generation_call" and isinstance(result, str) and result.strip():
                finals.append(result.strip())
            partial = node.get("partial_image_b64")
            if isinstance(partial, str) and partial.strip():
                partials.append(partial.strip())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(event_payload)
    return finals, partials


def stream_image_b64(
    access_token: str,
    account_id: str,
    request_body: Dict[str, Any],
) -> str:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "User-Agent": "codex_cli_rs/0.0.0",
        "originator": "codex_cli_rs",
        "ChatGPT-Account-ID": account_id,
    }
    body = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url=RESPONSES_ENDPOINT,
        data=body,
        headers=headers,
        method="POST",
    )

    final_images: List[str] = []
    partial_images: List[str] = []
    event_lines: List[str] = []

    def consume_event(lines: Iterable[str]) -> Optional[bool]:
        data_parts: List[str] = []
        for item in lines:
            if item.startswith("data:"):
                data_parts.append(item[5:].lstrip())
        if not data_parts:
            return None
        payload_text = "\n".join(data_parts).strip()
        if not payload_text:
            return None
        if payload_text == "[DONE]":
            return True
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError:
            return None
        finals, partials = extract_image_candidates(payload)
        final_images.extend(finals)
        partial_images.extend(partials)
        return None

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            while True:
                raw_line = response.readline()
                if not raw_line:
                    if event_lines:
                        done = consume_event(event_lines)
                        if done:
                            break
                    break
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                if line == "":
                    done = consume_event(event_lines)
                    event_lines = []
                    if done:
                        break
                    continue
                if line.startswith(":"):
                    continue
                event_lines.append(line)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace").strip()
        if exc.code == 401:
            raise CodexImageError("收到 401 Unauthorized。请重新运行 codex auth login。") from exc
        if exc.code == 403:
            raise CodexImageError(
                "收到 403 Forbidden。大概率是 Cloudflare / 请求头 / 账号态问题，请检查 User-Agent、originator、ChatGPT-Account-ID。",
            ) from exc
        if exc.code in (400, 404) and "model" in error_body.lower():
            raise CodexImageError(
                f"请求 Responses API 失败（HTTP {exc.code}）：{error_body}。"
                "若当前账号不支持默认调度模型，请用 --response-model 换成你的 Codex 可用模型。",
            ) from exc
        raise CodexImageError(f"请求 Responses API 失败（HTTP {exc.code}）：{error_body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise CodexImageError(f"无法连接 Responses API：{exc}") from exc

    if final_images:
        return final_images[-1]
    if partial_images:
        return partial_images[-1]
    raise CodexImageError("SSE 流结束，但没有提取到图片数据。请检查上游响应结构是否变更。")


def decode_image_bytes(image_b64: str) -> bytes:
    try:
        return base64.b64decode(image_b64, validate=False)
    except binascii.Error as exc:
        raise CodexImageError(f"返回的图片 base64 无法解码：{exc}") from exc


def png_dimensions(image_bytes: bytes) -> Tuple[int, int]:
    """Read PNG dimensions without restoring the removed ratio-fitting pipeline."""
    if len(image_bytes) < 24 or not image_bytes.startswith(PNG_SIGNATURE):
        raise CodexImageError("生图后端返回的文件不是合法 PNG。")
    if image_bytes[12:16] != b"IHDR":
        raise CodexImageError("PNG 缺少首个 IHDR chunk，无法读取尺寸。")
    width, height = struct.unpack(">II", image_bytes[16:24])
    if width <= 0 or height <= 0:
        raise CodexImageError(f"PNG 尺寸异常：{width}x{height}")
    return width, height


def normalize_output_name(name: str) -> str:
    """校验 --name：只接受文件基础名，传了 .png 后缀就去掉，避免生成 x.png.png。"""
    base = name.strip()
    if base.lower().endswith(".png"):
        base = base[: -len(".png")]
    if not base or base in {".", ".."} or "/" in base or "\\" in base:
        raise CodexImageError(f"--name 只能是文件基础名，不能为空或包含目录分隔符：{name!r}")
    return base


def path_taken(path: pathlib.Path, *, check_manifest: bool) -> bool:
    if path.exists():
        return True
    return check_manifest and path.with_suffix(path.suffix + ".manifest.json").exists()


def output_path_for(
    prompt: str,
    out_dir: str,
    name: Optional[str] = None,
    *,
    check_manifest: bool = True,
) -> pathlib.Path:
    directory = pathlib.Path(out_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    if name is not None:
        base = normalize_output_name(name)
        index = 1
        while True:
            suffix = "" if index == 1 else f"-{index}"
            path = directory / f"{base}{suffix}.png"
            if not path_taken(path, check_manifest=check_manifest):
                return path
            index += 1
    digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:12]
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    # 并行运行同一提示词时，时间戳与提示词哈希可能完全相同；加随机串避免互相覆盖。
    while True:
        path = directory / f"codex-image-{stamp}-{digest}-{secrets.token_hex(3)}.png"
        if not path_taken(path, check_manifest=check_manifest):
            return path


def save_new_image(
    image_bytes: bytes,
    prompt: str,
    out_dir: str,
    name: Optional[str] = None,
    *,
    check_manifest: bool = True,
) -> pathlib.Path:
    """以独占方式创建图片文件；并行同名运行抢到同一路径时，换下一个后缀重试。"""
    while True:
        path = output_path_for(prompt, out_dir, name, check_manifest=check_manifest)
        try:
            with path.open("xb") as handle:
                handle.write(image_bytes)
        except FileExistsError:
            continue
        return path


def manifest_path_for(args: argparse.Namespace, output_path: pathlib.Path) -> pathlib.Path:
    if args.manifest_out:
        path = pathlib.Path(args.manifest_out).expanduser().resolve()
    else:
        path = output_path.with_suffix(output_path.suffix + ".manifest.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def output_descriptor(path: pathlib.Path, size: Tuple[int, int]) -> Dict[str, Any]:
    return {
        "kind": "local_file",
        "source": str(path.resolve()),
        "path": str(path.resolve()),
        "reusable": True,
        "sha256": sha256_file(path),
        "size": f"{size[0]}x{size[1]}",
    }


def write_run_manifest(
    args: argparse.Namespace,
    *,
    prompt: str,
    continued_from: Optional[Dict[str, Any]],
    source_path: pathlib.Path,
    output_path: pathlib.Path,
    source_size: Tuple[int, int],
    output_size: Tuple[int, int],
) -> pathlib.Path:
    manifest_path = manifest_path_for(args, output_path)
    manifest: Dict[str, Any] = {
        "schema_version": 1,
        "created_at": utc_now_iso(),
        "prompt": prompt,
        "response_model": args.response_model,
        "image_model": args.model,
        "quality": args.quality,
        "aspect": args.aspect,
        "requested_source_size": ASPECT_TO_SIZE[args.aspect],
        "continued_from": continued_from,
        "target_images": [describe_image_source(value) for value in args.image],
        "reference_images": [describe_image_source(value) for value in args.reference_image],
        "input_contract": {
            "target_images": "primary canvases to edit; preserve unspecified content",
            "reference_images": "identity/style/material guidance only; do not copy layout by default",
        },
        "output": {
            "image": output_descriptor(output_path, output_size),
            "source_image": output_descriptor(source_path, source_size),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    prompt = read_prompt(args)
    if args.name is not None:
        normalize_output_name(args.name)  # 先校验，避免生图后才因文件名报错
    continued_from = apply_continuation(args)
    auth_data = load_auth_data()
    auth_data = refresh_tokens_if_needed(auth_data)
    tokens = dict(auth_data.get("tokens") or {})
    access_token = tokens.get("access_token")
    if not access_token:
        raise CodexImageError("auth.json 缺少有效 access_token。")
    account_id = extract_account_id(auth_data)
    request_body = build_request_body(args, prompt)
    image_b64 = stream_image_b64(access_token, account_id, request_body)
    image_bytes = decode_image_bytes(image_b64)
    source_path = save_new_image(
        image_bytes,
        prompt,
        args.out_dir,
        args.name,
        check_manifest=not args.manifest_out,
    )

    source_size = png_dimensions(image_bytes)
    output_path = source_path
    output_size = source_size

    manifest_path = write_run_manifest(
        args,
        prompt=prompt,
        continued_from=continued_from,
        source_path=source_path,
        output_path=output_path,
        source_size=source_size,
        output_size=output_size,
    )

    payload: Dict[str, Any] = {
        "success": True,
        "image": str(output_path),
        "source_size": f"{source_size[0]}x{source_size[1]}",
        "output_size": f"{output_size[0]}x{output_size[1]}",
        "manifest": str(manifest_path),
        "response_model": args.response_model,
        "image_model": args.model,
        "quality": args.quality,
    }
    if args.name is not None:
        payload["requested_name"] = args.name
    print_json(payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CodexImageError as exc:
        fail(str(exc))
