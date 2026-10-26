# Codex Image Gen

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Codex Image Gen 复用本机 Codex CLI 的 OAuth 登录态，把 gpt-image-2 的流式结果落地为本地 PNG">
</p>

<p align="center"><strong>把已经登录的 Codex CLI 变成任何 Agent 都能用的生图能力——不需要 API Key，一个零依赖的 Python 脚本。</strong></p>

<p align="center"><a href="./README.md">English</a> · <a href="https://github.com/zjp1997720/zhijian-skills/tree/main/skills/codex-image-gen"> canonical 源码</a></p>

多数本地 Agent 想生图，都得先买一个 OpenAI API Key 再接线。如果你已经在用 `codex` 并且用 ChatGPT 账号登录过，这个 Skill 直接复用那份 OAuth 登录态来驱动 `gpt-image-2`：自动刷新过期 token、带上后端必需的请求头调用 Codex Responses 接口、解析 SSE 流、把图片写成本地 PNG。Claude Code、Codex、OpenCode 或任何能跑 `python3` 的 Agent 都能用。

## 安装

```bash
npx skills add zjp1997720/zhijian-skills \
  --skill codex-image-gen --agent codex --global --copy --yes
```

## 前置条件

- 已安装 Codex CLI，并且执行过一次 `codex auth login`
- 运行 Agent 的机器上存在可读的 `~/.codex/auth.json`
- Python 3.9 及以上；无任何第三方依赖
- 机器可访问 `chatgpt.com` 与 `auth.openai.com`

## 它能做什么

- 文生图，支持 `--prompt` 或 `--prompt-file`
- 图像编辑与 image-to-image：`--image` 是要修改的主画布，`--reference-image` 只提供身份、风格或材质参考（都可重复，支持本地路径、HTTP(S) URL 或 data URL）。两类图片带语义标签按顺序发出，多图编辑时不再把参考图当成要改的画布
- 每次生成都写一份 manifest（prompt、模型、输入图、成图 SHA-256 与实际尺寸）；`--continue-from <manifest>` 直接以上一张成图为画布接着返修，并带上可复用的参考图。图片和 manifest 一起挪目录也能找回
- `--name hero` 输出 `hero.png`，同名已存在时自动改成 `hero-2.png`，从不覆盖；不传则用带随机后缀的文件名，同一提示词并行跑也不会互相覆盖
- 附一份提示词写法指南（`references/prompting.md`）：封面、海报、课件页的“设计规则 / 画面主意 / 精确文字”三层写法，带中文标题的成品设计，头像与系列图的区分度做法
- `--aspect square|landscape|portrait` 与 `--quality low|medium|high` 会写进请求，但 Codex 通道目前在服务端把尺寸和质量改成 `auto`（见下文“实测边界”），实际尺寸以 manifest 为准
- 解析 access token 的 JWT 过期时间，过期时用 refresh token 刷新，并把新 token 写回 `~/.codex/auth.json`
- 从 SSE 流提取最终图片，必要时回退到最后一帧 partial 图，保存为 PNG
- 输出一行可解析的 JSON，含 `image`、`manifest`、实际尺寸与所用模型

## 工作原理

1. 脚本读取 `~/.codex/auth.json`，解码 access token 的 JWT payload，临过期时通过 `auth.openai.com` 刷新。
2. 按后端要求的请求头（`User-Agent: codex_cli_rs/0.0.0`、`originator: codex_cli_rs`、`ChatGPT-Account-ID`）调用 Codex Responses 接口，这正是避免莫名 403 的关键。
3. 外层调度模型（默认 `gpt-6-astra`，可用 `--response-model` 换）挂载 `image_generation` 工具；本地图片 base64 编码成 `input_image`，每张图前插一句说明它是“主画布”还是“参考图”。
4. SSE 解析器保留最后一个 `image_generation_call.result`，缺失时回退到最后一个 `partial_image_b64`，以独占方式写成 PNG，再写同名 `.manifest.json`。

## 实测边界

2026-10-26 实跑，服务端在 `response.completed` 里回显的工具配置是 `"model": "gpt-image-2-codex", "quality": "auto", "size": "auto"`，请求 `landscape` 得到 1254x1254。也就是说：

- 经 Codex 订阅通道生图，用的是 `gpt-image-2` 的 Codex 版本，改 `--model` 不会换成 GPT Image 2.5。要用 2.5 只能走 OpenAI 平台 API Key。
- 比例和质量目前由服务端决定。要横版或竖版，请在 prompt 里写清画幅；脚本不做裁切或扩边，实际尺寸记在 manifest 里。

## 示例请求

```text
用蓝白配色生成一张极简课程封面插图，16:9，无文字，保存到 ./outputs
```

```text
这台机器没有 OpenAI API Key，但 Codex CLI 已经登录了。画一张极简科技插图。
```

```text
把 draft.png 改成干净的白板商业插图风格，参考 style-ref.png 的风格。
```

等价的直接调用：

```bash
python3 scripts/codex_image.py \
  --prompt "蓝白配色的 AI 课程封面插图，几何感，极简，无文字" \
  --aspect landscape --quality high --out-dir ./outputs
```

## 安全与边界

- 本 Skill 复用你自己的 ChatGPT/Codex 登录态，消耗该账号的生图额度；不会凭空产生额度。
- refresh token 是一次性的，所以脚本刷新成功后立即以 `0600` 权限写回 `~/.codex/auth.json`。
- 默认调度模型 `gpt-6-astra` 若你的账号用不了，会报 400/404 并提示改 `--response-model`，换成你的 Codex 里可选的模型即可。
- `401` 表示本地登录态失效——重新执行 `codex auth login`。`403` 通常是请求头缺失或 Cloudflare/账号风控，不要误判成 prompt 问题。
- 生图行为受你的账号条款约束；prompt 与参考图都应在账号允许处理的范围内。
- 每次运行生成一张图。批量调度、任务队列和高级后处理明确不在范围内。
- 上游响应结构变化时，脚本会显式失败而不是保存坏数据；`references/api-notes.md` 记录了完整协议细节便于修复。

## 仓库结构

```text
skills/codex-image-gen/
├── SKILL.md
├── agents/openai.yaml
├── evals/evals.json
├── references/api-notes.md
├── references/prompting.md
├── scripts/codex_image.py
└── tests/test_codex_image.py
```

## 许可证

[MIT](../../../LICENSE)
