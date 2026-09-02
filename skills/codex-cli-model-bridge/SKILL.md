---
name: codex-cli-model-bridge
description: Install, audit, repair, and manage Codex custom model
  Providers and model catalogs backed by a loopback CLIProxyAPI or Codex
  Router. Use whenever the user asks to add, remove, upgrade, restore, or
  diagnose third-party models in Codex or the Codex desktop model picker;
  mentions Grok, OpenCode Go, DeepSeek, Gemini, GLM Coding Plan, GLM-5.3,
  subscription-backed CLI models, custom model_provider, model_catalog_json,
  or Codex Fast mode; or wants the same local proxy models synchronized
  between Codex and WorkBuddy. Preserve unrelated Codex configuration and
  credentials. Isolated profile is the default Windows path.
---

# Codex CLI Model Bridge

Manage subscription-backed or local proxy models in Codex without treating Codex like WorkBuddy. Codex uses a Responses API Provider plus a model catalog; WorkBuddy uses independent JSON entries. Share CLIProxyAPI infrastructure and verified Provider facts, but keep each application's writer and state separate.

Codex selects one `model_provider` for a task. Model catalog entries do not carry per-model Provider routing. Preserve the Provider identity that owns the majority of indexed task history (normally `openai`). For normal Desktop use, the supported bridge design keeps `model_provider = "openai"`, keeps ChatGPT subscription auth intact, and points the built-in Provider's `openai_base_url` at an owner-only loopback header-rewriting proxy. CLIProxyAPI then routes native GPT subscription models and verified third-party models behind one catalog without changing the task Provider identity. Keep the isolated `$CODEX_HOME/cli-proxy.config.toml` profile as the default path on Windows and as a fallback everywhere else.

This is transparent single-Provider routing, not per-model Provider routing. Never set the Desktop default to `cli_proxy` or vendor `ZAI` when most history belongs to `openai`.

When the user wants GLM-5.3 from a Coding Plan key, read [glm-coding-plan.md](references/glm-coding-plan.md). If Desktop already uses Codex Router on port 4202, add `zai-coding` there and keep the OpenAI Provider identity. Do not run `npx @z_ai/coding-helper`.

On Windows, start with the isolated profile. Read [windows.md](references/windows.md). Do not require Homebrew, LaunchAgents, or Codex Router.

## Resolve the Skill directory

Resolve this loaded Skill's directory as `<skill-dir>`. Resolve `<python>` as the first available of `python3`, `py -3`, and `python`. Use the deterministic entry point:

```bash
<python> <skill-dir>/scripts/bridge.py
```

Examples below use `python3`. Substitute `<python>` when that command is missing.

## Default workflow

### 1. Audit before mutation

```bash
python3 <skill-dir>/scripts/bridge.py audit
```

The audit must redact secrets and verify:

- Codex CLI version, `~/.codex/config.toml`, file permissions, and TOML validity
- default `model_provider`, indexed task counts by Provider, SQLite integrity, and the dominant history Provider
- active bridge mode: Desktop-transparent or isolated-profile
- Desktop-transparent `openai_base_url`, ChatGPT auth continuity, loopback health, or the isolated profile's command-backed authentication
- loopback-only CLIProxyAPI reachability and live `/v1/models`
- the active catalog's validity, visible model IDs, and bridge ownership state
- stale catalog entries, missing live routes for managed models, listed native models, or the current default model, and models present in the proxy but absent from Codex

Codex officially supports only the Responses wire API for custom Providers. Do not register a Chat Completions-only route and call it Codex-compatible.

If the default Provider differs from the dominant indexed-history Provider, treat history restoration as the first repair. Do not edit task rows to make the current Provider fit.

### 2. Restore the desktop default and history

Preview:

```bash
python3 <skill-dir>/scripts/bridge.py restore-default
```

The preview reports one finding ID, the current config SHA-256, the exact single-file diff, and the before-state thread inventory. Apply only after the repair is authorized and the SHA is still current:

```bash
python3 <skill-dir>/scripts/bridge.py restore-default \
  --expected-sha256 <approved-sha256> \
  --apply
```

The default target is the Provider with the largest indexed task count. The command refuses a minority Provider unless `--allow-minority-provider` is explicit, restores a native model, removes the custom root catalog override, preserves unrelated TOML, creates a `0600` backup, and proves the task inventory digest did not change.

### 3. Configure or repair the isolated CLIProxyAPI profile

This is the default path on Windows. Preview and apply:

```bash
python3 <skill-dir>/scripts/bridge.py configure
python3 <skill-dir>/scripts/bridge.py configure --apply
```

The command does not rewrite `~/.codex/config.toml`. It preserves unrelated profile sections, creates timestamped `0600` backups, installs an owner-only credential helper that reads the existing CLIProxyAPI client key without copying it, and configures `~/.codex/cli-proxy.config.toml` with:

- `model_provider = "cli_proxy"`
- `model_catalog_json = "~/.codex/model-catalog-cli-proxy.json"`
- `[model_providers.cli_proxy]` with a loopback URL and `wire_api = "responses"`
- `[model_providers.cli_proxy.auth]` using the local helper command

The helper is Python by default so Windows does not need Ruby. An existing `.rb` helper is left in place. Do not set or change the user's default model unless they explicitly ask. Do not overwrite built-in Provider IDs. After this profile exists, use `codex --profile cli-proxy`.

### 4. Synchronize the profile model catalog

Preview bundled models:

```bash
python3 <skill-dir>/scripts/bridge.py sync
```

Apply after live route verification:

```bash
python3 <skill-dir>/scripts/bridge.py sync --apply
```

The sync command starts with Codex's native model cache only to inherit required runtime metadata, overlays verified model manifests from `<skill-dir>/models/`, preserves unmanaged/manual profile entries, refuses to overwrite an unowned collision unless `--adopt` is explicit, backs up the target, writes atomically, and records managed IDs under `~/.config/codex-cli-model-bridge/state.json`.

The picker policy lives at `<skill-dir>/policies/catalog.json`. IDs in `hidden_native_model_ids` remain in the catalog with Codex's native `visibility = "hide"` semantics, so existing tasks and routes keep working while those entries disappear from the model picker. Always change this canonical policy instead of hand-editing the generated catalog; every later sync reapplies it after a Codex update refreshes `models_cache.json`.

IDs in `protected_native_model_ids` must also remain under their exact native slugs. Codex App `create_thread` validates those IDs independently of cosmetic catalog aliases, so a managed manifest must never `supersede` them. Represent Fast through the service tier; do not replace `gpt-5.6-sol` with a `*-standard` picker alias. If WorkBuddy needs extra Fast/standard aliases, CLIProxyAPI `oauth-model-alias` must set `fork: true` so the native slug stays in live `/v1/models`. Audit fails when a listed catalog model or the current default model is missing from that live list.

Native entries copied into the bridge catalog are metadata only. In isolated-profile mode they route through `cli_proxy`; in Desktop-transparent mode they route through the built-in `openai` Provider identity and its loopback `openai_base_url`. The catalog itself never chooses the Provider.

Use `--models <comma-separated-ids>` to select a subset. Use `--catalog-policy <path>` only for an explicit alternate policy or an isolated test. Use `--prune-managed` only when the user explicitly asked to remove stale bridge-managed models. Never prune native or manual entries; hide native picker entries through the policy.

When onboarding a new model, read [model-manifests.md](references/model-manifests.md). A manifest is metadata, not proof. Its route must appear in live `/v1/models`, and a real `codex exec` probe must pass before success is reported.

### 5. Enable transparent Desktop coexistence

Skip this on Windows unless the user explicitly wants the normal Desktop picker and will keep a Node process running. Isolated profile is enough.

First preview the exact root config diff and history guard:

```bash
python3 <skill-dir>/scripts/bridge.py configure-desktop
```

After the finding-level diff is authorized, apply with the reported SHA-256:

```bash
python3 <skill-dir>/scripts/bridge.py configure-desktop \
  --expected-sha256 <approved-sha256> \
  --apply
```

The command refuses to proceed unless `openai` owns the majority of indexed history, `auth.json` still contains healthy ChatGPT tokens, both endpoints are loopback-only, and the selected default model exists in the catalog. It installs:

- `~/.config/codex-cli-model-bridge/transparent_proxy.mjs`, owner-executable
- on macOS, `~/Library/LaunchAgents/com.zhijian.codex-cli-model-bridge-transparent-proxy.plist`
- on Windows and Linux, a detached `node` process instead of a LaunchAgent
- a listener on `127.0.0.1:8318` that rewrites only the downstream Authorization header before forwarding to authenticated CLIProxyAPI on `127.0.0.1:8317`

It then keeps `model_provider = "openai"`, sets `openai_base_url = "http://127.0.0.1:8318/v1"`, activates the verified catalog, preserves ChatGPT login and unrelated TOML, creates a `0600` backup, and proves the task inventory digest did not change. Do not run a second CLIProxyAPI instance against the same OAuth directory; concurrent token refresh can invalidate credentials.

### 6. Handle Fast mode correctly

Codex Fast mode is a service tier on a model, not normally a second model entry. For a model whose catalog advertises the Fast tier, use:

```toml
service_tier = "fast"
```

or launch a one-off run with:

```bash
codex -c 'service_tier="fast"'
```

Codex maps `fast` to the priority request value. Do not create `*-fast` as a cosmetic catalog alias. A separate route is acceptable only when the upstream truly requires it and a live Responses probe verifies the distinct routing semantics.

### 7. Probe through Codex itself

After catalog sync, probe affected models:

```bash
python3 <skill-dir>/scripts/bridge.py probe --models grok-4.6,deepseek-v4-pro
```

The probe runs `codex exec --profile cli-proxy` in ephemeral, read-only mode for each model and verifies a successful final response. Use `--fast` only for a model that advertises Fast. Keep prompts non-sensitive and do not persist sessions.

For the normal Desktop-transparent path, probe without switching Provider identity:

```bash
python3 <skill-dir>/scripts/bridge.py probe \
  --desktop \
  --models grok-4.6,deepseek-v4-pro,deepseek-v4-flash,gpt-5.6-sol
```

With `--desktop`, the probe reads the active root `model_catalog_json` from
`~/.codex/config.toml`; use `--catalog` only as an explicit override.

Direct HTTP probes can diagnose the proxy, but they do not prove that Codex consumed the Provider and model catalog. Completion requires the Codex-level probe.

When a model can chat but Codex reports an empty or incompatible Shell payload, require an actual read-only command event:

```bash
python3 <skill-dir>/scripts/bridge.py probe \
  --desktop \
  --shell \
  --models grok-4.6
```

This passes only when Codex records a successful `pwd` command execution; a model that merely prints or simulates a path does not pass. If the failing custom model inherited `tool_mode = "code_mode_only"` from an OpenAI template, set `"tool_mode": null` in that model manifest and resync. Do not remove code mode from native OpenAI models globally.

### 7.1 Repair Codex Multi-Agent input for third-party models

Codex Multi-Agent v2 uses a private Responses input item named `agent_message`. Native OpenAI/Codex routes accept it, while xAI and other third-party Responses endpoints may reject it with HTTP 422 and `ModelInput`. CLIProxyAPI 7.2.125+ contains the compatibility transform; do not duplicate this protocol rewrite in the transparent header proxy.

Preview and enable it in the canonical CLIProxyAPI config:

```bash
python3 <skill-dir>/scripts/bridge.py configure-multi-agent
python3 <skill-dir>/scripts/bridge.py configure-multi-agent \
  --expected-sha256 <approved-sha256> \
  --apply
```

This changes only `codex.optimize-multi-agent-v2` to `true`, creates a `0600` backup, restarts CLIProxyAPI when a macOS Homebrew service exists, and waits for the transparent route to recover. On Windows, tell the user to restart CLIProxyAPI locally if the live `/v1/models` check does not recover. The transform is gated to official Codex user agents. For xAI, it converts `agent_message` into a standard user `message`, normalizes its encrypted content wrapper, and leaves normal OpenAI history/provider identity untouched.

Verify the exact failing shape, then run the normal Codex probe:

```bash
python3 <skill-dir>/scripts/bridge.py probe-multi-agent --models grok-4.6
python3 <skill-dir>/scripts/bridge.py probe --desktop --tool-sequence --models grok-4.6
```

For Grok agentic use, require CLIProxyAPI `7.2.130` or newer plus both probes above. A plain text completion or one successful `pwd` does not qualify the model for multi-tool or Subagent work. Older proxy versions may mishandle Responses tool identity, incremental tool state, or Codex multi-agent namespaces.

### 8. Verify consumption

Run `audit` again and repeat `sync`; the second sync must be idempotent. Normal Desktop tasks must remain on the dominant history Provider. In Desktop-transparent mode all selected models route through the loopback bridge while task identity remains `openai`; do not describe this as independent per-model Provider selection. Use `codex --profile cli-proxy` for Windows and for fallback diagnosis.

Report:

- Codex and CLIProxyAPI versions and local endpoint
- default Provider, task counts by Provider, and the verified unchanged task-inventory digest
- profile Provider and catalog paths, with secrets omitted
- models added, updated, removed, preserved, or conflicted
- live route and `codex exec` probe results
- Fast semantics when requested
- backup paths, reload action, and rollback command

## Repair workflow

1. Audit and distinguish history-scope mismatch, invalid TOML, proxy-down, helper/auth failure, missing route, invalid profile catalog, stale task, and Provider protocol mismatch.
2. Restore the dominant history Provider before model work; do not rewrite task rows.
3. Repair the smallest failing layer; do not reinstall a healthy proxy.
4. Re-authorize upstream Providers with the WorkBuddy bridge only when CLIProxyAPI authentication is actually absent or rejected.
5. Re-run profile catalog sync and the affected Codex-level probes.
6. Verify normal desktop history remains visible under the default Provider.

For a Subagent failure whose HTTP 422 body mentions `ModelInput`, inspect the failed task for an `agent_message` input item. On CLIProxyAPI 7.2.125+, enable `codex.optimize-multi-agent-v2`, then run `probe-multi-agent`; do not flatten all requests indiscriminately in the transparent header proxy.

Read [troubleshooting.md](references/troubleshooting.md) for failure classification and rollback.

## Safety boundaries

- Keep CLIProxyAPI on explicit loopback and remote management disabled.
- Do not restart CLIProxyAPI or the 8318 transparent proxy while the current Desktop session is using a third-party model such as Grok. A restart drops live routes for a few seconds and can abort this session with `unknown provider`. Wait until after the Sol/Grok repair is verified, or tell the user first.
- Preserve unrelated `config.toml` sections, MCP servers, hooks, skills, permissions, and project trust settings.
- Never print API keys, bearer headers, OAuth files, one-time codes, raw credential-helper output, or credential-bearing TOML blocks.
- Keep `config.toml`, catalog/state files, proxy config, helper, and backups owner-only when they can reveal private infrastructure. Unix mode `0600` is the target; on Windows keep the files in the current user profile and do not share them.
- Use command-backed auth or the owner-only transparent header rewriter; do not embed `experimental_bearer_token` or duplicate the proxy client key.
- Treat native `models_cache.json` as upstream input, not a file this Skill owns.
- Do not directly edit Codex SQLite state or the desktop app bundle to force a model into the picker.
- Never switch the default Provider without first reading the indexed Provider distribution. Refuse a switch that would hide the majority of history unless the user explicitly accepts that result.
- Do not advertise per-model Provider routing. Desktop coexistence works only because the built-in `openai` Provider identity transparently routes every selected catalog model through the same loopback bridge.
- Respect Provider subscription terms, quotas, and account ownership.

## Completion gate

Completion requires:

- default Codex TOML anchored to the dominant indexed-history Provider
- unchanged, integrity-checked task inventory across the repair
- valid isolated fallback profile or a healthy Desktop-transparent loopback bridge with ChatGPT auth preserved
- valid active model catalog with no unapproved collision
- requested native picker exclusions retained with `visibility = "hide"`
- every newly managed route visible from CLIProxyAPI
- a successful ephemeral `codex exec` probe for every affected model through the active mode
- Fast represented and tested as a service tier when requested
- a second sync with no changes
- backups and rollback paths reported

If Codex cannot complete a Responses request through a route, report it as unverified and do not advertise it as usable merely because `/v1/models` lists the name.
