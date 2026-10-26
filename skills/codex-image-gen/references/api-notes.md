# Codex OAuth 生图 API 备注

本文档记录 `codex-image-gen` 依赖的最小协议面，方便在 Claude Code、Codex、OpenCode 等 Agent 里排错和二次封装。

## 1. 认证来源

认证文件：

```text
~/.codex/auth.json
```

典型格式：

```json
{
  "auth_mode": "chatgpt",
  "tokens": {
    "id_token": "...",
    "access_token": "...",
    "refresh_token": "...",
    "account_id": "..."
  },
  "last_refresh": "2026-07-03T07:05:56.768466Z"
}
```

脚本需要做 3 件事：

1. 读取 `tokens.access_token`
2. 解 JWT payload，检查 `exp`
3. 过期时用 `tokens.refresh_token` 刷新，并写回原文件

## 2. 刷新 token

刷新端点：

```text
POST https://auth.openai.com/oauth/token
```

最小表单字段：

```text
client_id=app_EMoamEEZ73f0CkXaXp7hrann
grant_type=refresh_token
refresh_token=<auth.json 中的 refresh_token>
```

实现建议：

- 用 `application/x-www-form-urlencoded`
- 刷新成功后保留原有 `auth.json` 字段，只更新 `tokens` 中返回的新值
- `last_refresh` 用 UTC ISO8601，末尾带 `Z`

## 3. Responses API

请求端点：

```text
POST https://chatgpt.com/backend-api/codex/responses
```

### 必备请求头

以下请求头缺一不可，否则常见结果是 403：

```text
User-Agent: codex_cli_rs/0.0.0
originator: codex_cli_rs
ChatGPT-Account-ID: <从 access_token JWT claim 取 chatgpt_account_id>
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: text/event-stream
```

其中 `ChatGPT-Account-ID` 优先从 access token 的 JWT payload 提取；若提取失败，可退回 `auth.json.tokens.account_id` 作为兜底。

## 4. 请求体结构

外层模型默认使用 GPT-6 Astra，并可通过 `--response-model` 显式覆盖：

```json
{"model": "gpt-6-astra"}
```

外层模型负责理解用户意图、区分主编辑图与参考图、组织工具调用；真正负责像素生成的仍是 `gpt-image-2`。因此 `--response-model` 与 `--quality` 控制的是两个不同层面。

真正负责出图的是 tools 中的 `image_generation`：

```json
{
  "type": "image_generation",
  "model": "gpt-image-2",
  "size": "1024x1024",
  "quality": "medium",
  "output_format": "png",
  "background": "opaque",
  "partial_images": 1
}
```

**服务端会改写工具配置**（2026-10-09 实测，`response.completed` 回显的 `tools`）：无论请求 `gpt-image-2`、`gpt-image-2.5-flare`、`gpt-image-2.5-sunburst`、带日期快照还是不存在的名字，都返回成功，回显的生图模型一律是 `gpt-image-2-codex`，`quality` 与 `size` 都是 `auto`。PNG 内的 C2PA 只写 `gpt-image`，不带版本。Codex 源码 `codex-rs/ext/image-generation/src/tool.rs` 也写死了 `IMAGE_MODEL = "gpt-image-2"`，`quality` 和 `size` 固定为 `auto`。因此经 Codex OAuth 通道用不上 GPT Image 2.5，`--model` 改了也不生效。要用 2.5，只能走 OpenAI 平台 API Key（Image API 或 Responses 的 `image_generation` 工具，按量计费）。`--quality` 是否真正生效尚未验证。

### 文生图 content

```json
[
  {"type": "input_text", "text": "<prompt>"}
]
```

### image-to-image / 编辑 content

在上面的 prompt 后，先为每张图添加角色说明，再追加对应图片：

```json
[
  {"type": "input_text", "text": "Target/input image 1: ... primary canvas ..."},
  {"type": "input_image", "image_url": "data:image/png;base64,..."},
  {"type": "input_text", "text": "Reference image 1: ... guidance only ..."},
  {"type": "input_image", "image_url": "data:image/png;base64,..."}
]
```

`--image` 对应主编辑画布，`--reference-image` 对应身份、风格、材质或规则参考。后端协议没有单独的图片角色字段，因此用紧邻图片的 `input_text` 明示语义，不能再把两类图片无差别拼接。

### 运行 manifest 与连续编辑

每次成功运行都会在最终图片旁写入 `.manifest.json`，记录：

- prompt、外层调度模型、生图模型、quality 和比例参数
- 主编辑图与参考图的原始来源及本地 SHA-256
- 母版、最终图片、尺寸与 SHA-256
- 上游 manifest 路径和哈希（如果通过 `--continue-from` 续跑）

`--continue-from` 读取上一轮 manifest，把上一张最终图作为第一张 `--image`，并复用可重建的参考图。data URL 不写入 manifest，避免旁路复制大块图像数据；这类输入在下一轮必须重新传入。

## 5. 母版尺寸与交付比例

Responses API 当前只暴露 3 个后端母版尺寸：

- `square` -> `1024x1024`
- `landscape` -> `1536x1024`
- `portrait` -> `1024x1536`

这些母版分别是 1:1、3:2、2:3，不等于 16:9、2.35:1 或 3:4。脚本不做生成后比例适配：不扩边、不裁切、不缩放，保存上游返回的原始 PNG。若最终页面必须有特定比例，应由排版层等比显示，或明确重新生成可承载该比例的内容图。

上游可能忽略 `size` 并返回其他比例。脚本会在 manifest 中记录实际尺寸；比例不满足需求时直接返修或重生成，不做本地强制比例处理。

quality：

- `low`
- `medium`
- `high`

## 6. SSE 响应解析

图片数据可能出现在两类位置：

### A. 最终图片

```json
{"type": "image_generation_call", "result": "<base64>"}
```

### B. 流式中间图

任意嵌套层中的：

```json
{"partial_image_b64": "<base64>"}
```

解析策略建议：

1. 按 SSE 标准逐行读 `data:`
2. 遇到空行就把当前 event 合并并解析 JSON
3. 优先取最后一个 `image_generation_call.result`
4. 如果没有最终图，再回退到最后一个 `partial_image_b64`

## 7. 常见故障

### 401 Unauthorized

通常表示：

- access token 失效
- refresh token 也失效
- 本地登录态已经不可用

处理：让用户重新执行：

```bash
codex auth login
```

### 403 Forbidden

通常表示：

- 缺少 `User-Agent: codex_cli_rs/0.0.0`
- 缺少 `originator: codex_cli_rs`
- 缺少或错误的 `ChatGPT-Account-ID`
- 账号态 / Cloudflare 风控拦截

### 返回成功但没有图片字段

说明上游事件结构变了。应保留原始事件样本，扩展解析逻辑，而不是盲猜字段。

## 8. 这个 skill 的边界

它只解决：

- 已登录 Codex CLI 的本机 OAuth 态复用
- 文生图 / 图像编辑
- 本地 PNG 落地
- 基于 manifest 的本地连续返修

它不解决：

- 各宿主 Agent 自带的专有生图工具
- 云端任务队列
- 多图批量调度
- 高级后处理
- 自动读取只存在于聊天上下文、尚未落盘的最近图片

如果未来要做批量生图，可以在当前脚本外层再包一层 shell / Python 调度器。
