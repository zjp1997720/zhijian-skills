---
name: codex-image-gen
description: 给任何已登录 Codex CLI 的 Agent 提供本地生图能力，零私有依赖。只要用户提到生图、画图、生成图片、image
  generation、文生图、配图、插图、封面、海报、根据 prompt 出图，或要把本机 `~/.codex/auth.json` 里的 Codex
  OAuth 登录态复用成可执行脚本，都应优先使用本 skill。适用于 Claude Code、Codex、OpenCode 等任何能运行 bash /
  python3 脚本的 Agent。
disable-model-invocation: false
---

# Codex Image Gen

目标：把“本机已登录的 Codex OAuth 生图能力”封装成一个**零私有依赖**的跨 Agent Skill。

它不依赖任何私有模块；任何能执行 `python3` 的 Agent，只要宿主机已经装好 Codex CLI 并执行过 `codex auth login`，就能直接调用 `scripts/codex_image.py` 生图或做图像编辑。

## 前置条件

必须同时满足：

1. 本机已安装 Codex CLI
2. 已执行过 `codex auth login`
3. `~/.codex/auth.json` 存在且可读
4. 机器可访问：
   - `https://chatgpt.com/backend-api/codex/responses`
   - `https://auth.openai.com/oauth/token`

如果 `~/.codex/auth.json` 不存在，不要猜测或绕过。直接提示用户先运行：

```bash
codex auth login
```

## 这个 skill 能做什么

- 文生图
- 配图 / 插图 / 封面图生成
- image-to-image / 编辑
- 用 `--image` 与 `--reference-image` 显式区分主编辑画布和身份/风格参考，避免多图角色混淆
- 每次生成自动保存可审计、可继续编辑的 manifest；可用 `--continue-from` 接着上一轮返修
- 把本地参考图编码成 `data:image/...;base64,...` 后发给 Codex Responses API
- 自动检查 access token 是否过期
- access token 过期时自动用 refresh token 刷新，并写回 `~/.codex/auth.json`
- 从 SSE 流里提取图片 base64，保存为本地 PNG

## 核心脚本

相对路径：`scripts/codex_image.py`

典型调用方式：

```bash
python3 scripts/codex_image.py \
  --prompt "极简科技感课程封面，无文字" \
  --aspect landscape
```

如果 Agent 不是在 skill 根目录执行，就显式传 skill 相对路径或绝对路径，例如：

```bash
python3 .claude/skills/codex-image-gen/scripts/codex_image.py \
  --prompt "商业文章封面插图，克制，干净，无文字" \
  --aspect landscape \
  --quality high \
  --out-dir ./outputs
```

## CLI 参数

### 必填

二选一：

- `--prompt "..."`
- `--prompt-file /path/to/prompt.txt`

### 可选

- `--quality low|medium|high`：默认 `medium`
- `--aspect landscape|square|portrait`：选择后端母版方向，默认 `square`
- `--out-dir /path/to/output-dir`：默认当前目录
- `--image /path/to/image.png`：主编辑图 / 输入图
- `--reference-image /path/to/ref.png`：参考图，可重复传入
- `--model gpt-image-2`：默认 `gpt-image-2`
- `--response-model gpt-6-astra`：负责理解 prompt、图片区分和调度生图工具的外层模型，默认 `gpt-6-astra`
- `--continue-from /path/to/previous.png.manifest.json`：自动把上一张成图作为主编辑图，并复用上一轮可复用参考图
- `--manifest-out /path/to/run.json`：自定义 manifest 路径；默认与最终图片同名并追加 `.manifest.json`
- `--name 基础名`：输出 `<基础名>.png` 与 `<基础名>.png.manifest.json`；同名已存在时不覆盖，自动改为 `<基础名>-2`、`-3`。不传则用默认随机文件名

Codex 通道目前在服务端把尺寸与质量改为 `auto`（2026-10 实测，见 `references/api-notes.md`），请求的方向常被忽略；需要横版或竖版时在 prompt 里写清画幅。脚本会把实际 PNG 原样保存，并在 manifest 中记录 `aspect` 与实际尺寸；不做扩边、裁切或缩放。若比例偏离，直接返修或重生成。

## 推荐工作方式

### 1) 最短路径：文生图

```bash
python3 scripts/codex_image.py \
  --prompt "蓝白配色的 AI 课程封面插图，几何感，极简，无文字" \
  --aspect landscape \
  --quality high \
  --out-dir ./outputs
```

### 2) 用 prompt 文件

```bash
python3 scripts/codex_image.py \
  --prompt-file ./prompt.txt \
  --aspect portrait \
  --out-dir ./outputs
```

### 3) image-to-image / 编辑

```bash
python3 scripts/codex_image.py \
  --prompt "把这张草图做成干净的白板商业插图风格" \
  --image ./draft.png \
  --reference-image ./style-ref.png \
  --aspect landscape \
  --out-dir ./outputs
```

`--image` 是要修改的主画布；`--reference-image` 只提供角色身份、风格、材质或约束。脚本会把两类图片及其语义标签按顺序发给外层调度模型，不再把所有图片当成无差别输入。

## Agent 执行规则

1. 先确认 `~/.codex/auth.json` 存在；不存在就停止并提示 `codex auth login`
2. 优先直接跑 `python3 scripts/codex_image.py --help` 自检 CLI
3. 写提示词前读 `references/prompting.md`，按其结构写用途、分段画面、逐行文字与约束；封面、海报、课件页按其「三层写法」写设计规则、画面主意与精确文字
4. 如果用户要封面/配图，默认优先：
   - `--aspect landscape`
   - `--quality high`
   - 只按 `--aspect` 选择原生母版方向；不承诺16:9、2.35:1或3:4等后处理比例
5. 如果用户要头像、图标、方图，默认优先：
   - `--aspect square`
   - 头像和系列图（多角色、多张同风格）先按 `references/prompting.md`「头像与系列图」列区分表，再逐张写提示词
6. 如果返回 401，直接提示重新登录 Codex
7. 如果返回 403，优先怀疑 Cloudflare / 请求头不完整 / 登录态异常，不要误判成 prompt 问题
8. 返修上一轮成图时优先使用返回的 `manifest` 配合 `--continue-from`，不要靠聊天记忆重构参考图集合
9. 默认文件名带随机后缀，可并行跑同一提示词；批量或系列出图用 `--name` 直接命名（如角色名），省去手动改名和改 manifest。两种方式都不覆盖已有文件；manifest 存绝对路径，若图片与 manifest 一起挪了目录，`--continue-from` 会回落到 manifest 所在目录找同名文件，不用手改路径

## 成功输出约定

脚本成功时会输出 JSON：

```json
{"success": true, "image": "/absolute/path/to/file.png", "manifest": "/absolute/path/to/file.png.manifest.json", "source_size": "1536x1024", "response_model": "gpt-6-astra", "image_model": "gpt-image-2", "quality": "high"}
```

`image` 与 `manifest` 是实际写入路径；传 `--name` 时额外输出 `requested_name`，若遇同名，实际路径已带 `-2` 等后缀，以 `image` 为准。

Agent 应返回：

- 最终图片路径
- 使用的 prompt（必要时可简述）
- 是否用了输入图 / 参考图
- manifest 路径，方便下一轮直接继续编辑

## 失败处理

### auth.json 不存在

明确提示：

```bash
codex auth login
```

### 401 Unauthorized

说明本地登录态失效，建议重新登录：

```bash
codex auth login
```

### 403 Forbidden

说明大概率是 Cloudflare / 关键请求头 / 账号态问题。先检查：

- `User-Agent: codex_cli_rs/0.0.0`
- `originator: codex_cli_rs`
- `ChatGPT-Account-ID`

### 400 / 404 且错误提到模型

说明当前 ChatGPT 账号的 Codex 不支持默认调度模型 `gpt-6-astra`。用 `--response-model` 换成该账号 Codex 可用的模型（在 Codex CLI 里 `/model` 可查看），`--model gpt-image-2` 保持不变。

### 没拿到图片数据

说明上游 SSE 响应格式变了，或只返回了中间事件但没有可用图片字段。此时应检查 `references/api-notes.md` 并根据新响应结构更新脚本。

## 参考文档

- 提示词写法：`references/prompting.md`
- API 细节：`references/api-notes.md`
- 核心脚本：`scripts/codex_image.py`
- 回归案例：`evals/evals.json`（仅维护和验证时读取）
