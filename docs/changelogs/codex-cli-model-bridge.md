# codex-cli-model-bridge Changelog

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
