# Codex Image Gen

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Codex Image Gen reuses the local Codex CLI OAuth login to stream gpt-image-2 results into local PNG files">
</p>

<p align="center"><strong>Turn an already-logged-in Codex CLI into image generation for any Agent — no API key, one dependency-free Python script.</strong></p>

<p align="center"><a href="./README.zh-CN.md">简体中文</a> · <a href="https://github.com/zjp1997720/zhijian-skills/tree/main/skills/codex-image-gen">Canonical source</a></p>

Most local Agents cannot generate images unless you buy and wire an OpenAI API key. If you already run `codex` and logged in with your ChatGPT account, this Skill reuses that exact OAuth login to drive `gpt-image-2`: it refreshes expired tokens, calls the Codex Responses endpoint with the headers the backend requires, parses the SSE stream, and writes a local PNG. It works from Claude Code, Codex, OpenCode, or any Agent that can run `python3`.

## Install

```bash
npx skills add zjp1997720/zhijian-skills \
  --skill codex-image-gen --agent codex --global --copy --yes
```

## Requirements

- Codex CLI installed and logged in once: `codex auth login`
- A readable `~/.codex/auth.json` on the machine that runs the Agent
- Python 3.9 or newer; no third-party packages
- Network access to `chatgpt.com` and `auth.openai.com`

## What It Does

- Text-to-image from a `--prompt` or a `--prompt-file`
- Image editing and image-to-image: `--image` is the canvas to edit, `--reference-image` only guides identity, style, or material (both repeatable; local paths, HTTP(S) URLs, or data URLs). Each image is sent with a role label, so multi-image edits stop treating a reference as the canvas
- Every run writes a manifest (prompt, models, inputs, output SHA-256, and actual size); `--continue-from <manifest>` keeps editing the previous result with its reusable references, even after the folder is moved
- `--name hero` writes `hero.png` and switches to `hero-2.png` instead of overwriting; without it, file names carry a random suffix so parallel runs of the same prompt never collide
- A prompting guide (`references/prompting.md`): a three-layer method (design rules, visual idea, exact text) for covers, posters, and slides, finished designs with Chinese titles, and distinct series such as avatar sets
- `--aspect square|landscape|portrait` and `--quality low|medium|high` are sent with the request, but the Codex channel currently rewrites size and quality to `auto` server-side (see "Measured limits"); the manifest records the real size
- Checks the access token's JWT expiry and refreshes it with the refresh token when needed, writing new tokens back to `~/.codex/auth.json`
- Extracts the final image from the SSE stream, falling back to the last partial image, and saves it as a PNG
- Emits one line of JSON with `image`, `manifest`, actual size, and the models used

## How It Works

1. The script reads `~/.codex/auth.json`, decodes the access token's JWT payload, and refreshes the token through `auth.openai.com` when it is near expiry.
2. It posts to the Codex Responses endpoint with the exact headers the backend expects (`User-Agent: codex_cli_rs/0.0.0`, `originator: codex_cli_rs`, `ChatGPT-Account-ID`), which is what prevents gratuitous 403s.
3. The outer dispatcher model (default `gpt-6-astra`, override with `--response-model`) carries an `image_generation` tool; local images are base64-encoded into `input_image` content, each preceded by a line saying whether it is the canvas or a reference.
4. The SSE parser keeps the last `image_generation_call.result`, falls back to the last `partial_image_b64`, creates the PNG exclusively, then writes the matching `.manifest.json`.

## Measured Limits

In a live run on 2026-10-26 the server echoed the tool config in `response.completed` as `"model": "gpt-image-2-codex", "quality": "auto", "size": "auto"`, and a `landscape` request returned 1254x1254. In practice:

- The Codex subscription channel runs the Codex build of `gpt-image-2`; changing `--model` does not unlock GPT Image 2.5. Use an OpenAI Platform API key for 2.5.
- Aspect and quality are decided server-side for now. Describe the frame in the prompt; the script never crops or pads, and the manifest records the real size.

## Example Requests

```text
Generate a blue-and-white minimal course cover illustration, no text, 16:9, into ./outputs
```

```text
This machine has no OpenAI API key, but Codex CLI is logged in. Draw a minimal tech illustration.
```

```text
Turn draft.png into a clean whiteboard-style business illustration, using style-ref.png as the style reference.
```

Equivalent direct call:

```bash
python3 scripts/codex_image.py \
  --prompt "minimal blue-white AI course cover, geometric, no text" \
  --aspect landscape --quality high --out-dir ./outputs
```

## Safety and Limitations

- The Skill reuses your own ChatGPT/Codex login and consumes that account's image quota; it does not create entitlements.
- Refresh tokens are single-use, so the script writes refreshed tokens back to `~/.codex/auth.json` immediately with `0600` permissions.
- If your account cannot use the default dispatcher `gpt-6-astra`, the script reports the 400/404 and points to `--response-model`; pick any model your Codex offers.
- `401` means the local login is gone — run `codex auth login` again. `403` is usually missing headers or Cloudflare/account checks, not a bad prompt.
- Image generation runs under your account terms; keep prompts and reference images within what your account is allowed to process.
- The Skill generates one image per run. Batch scheduling, queues, and post-processing are explicitly out of scope.
- If the upstream response format changes, the script fails loudly instead of saving garbage; `references/api-notes.md` documents the wire protocol for repairs.

## Repository Layout

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

## License

[MIT](../../../LICENSE)
