# codex-cli-model-bridge Changelog

## Unreleased

- Add bundled model manifest for Moonshot Kimi K3 (`kimi-k3`) with 256K context window and reasoning effort support.
- Add bundled model manifest for Google Gemini 3.8 Flash (`gemini-3.8-flash`) with 1M context window and vision support.
- Support optional `auto_compact_token_limit` and `truncation_token_limit` in model manifests and preserve them through `build_entry`.

## 1.0.1 — 2026-09-02

- Support automatic resolution of active desktop model catalog from `~/.codex/config.toml` during `--desktop` probes.
- Expand test suite with desktop probe catalog resolution and explicit override verification.
- Update documentation for desktop probe catalog ergonomics.

## 1.0.0 — 2026-08-22

- Publish the Codex CLIProxyAPI bridge: audit, restore the dominant history Provider, isolated profile, catalog sync, and `codex exec` probes.
- Keep Desktop on `model_provider = "openai"` when ChatGPT owns most task history; refuse vendor `ZAI` overwrites.
- Make isolated `codex --profile cli-proxy` the default Windows path. Discover CLIProxyAPI from PATH and common config locations; use a Python credential helper so Ruby is not required.
- Start the optional 8318 header proxy as a detached Node process outside macOS LaunchAgents.
- Document GLM Coding Plan coexistence without `npx @z_ai/coding-helper`, and keep Fast as a service tier.
