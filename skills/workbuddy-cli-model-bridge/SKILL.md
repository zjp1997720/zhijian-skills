---
name: workbuddy-cli-model-bridge
description: Install, audit, repair, and manage a loopback-only CLIProxyAPI bridge that registers subscription-backed Codex, Grok, Antigravity/Gemini, or newly added CLI models in WorkBuddy. Use whenever the user asks to connect a local CLI or agent model to WorkBuddy, install CLIProxyAPI, add or repair a WorkBuddy custom model, preserve image/tool/reasoning/Fast capabilities, onboard another CLI provider, or diagnose a WorkBuddy model that stopped working. This Skill is macOS-first and should be used even when the user names only the model or says their local WorkBuddy API has expired.
---

# WorkBuddy CLI Model Bridge

Turn supported CLI subscriptions into verified WorkBuddy custom-model entries through CLIProxyAPI. Use the bundled script for discovery, installation, OAuth handoff, capability probes, and idempotent WorkBuddy updates. Keep model claims tied to real probes; a model name or marketing page is not evidence that a particular proxy route preserves the capability.

## Resolve the Skill directory

Resolve this loaded Skill's directory and use its absolute path as `<skill-dir>`. Do not assume a specific installation root.

The deterministic entry point is:

```bash
python3 <skill-dir>/scripts/bridge.py
```

## Default workflow

### 1. Audit before changing anything

```bash
python3 <skill-dir>/scripts/bridge.py audit
```

Read the JSON findings. The audit redacts secrets and detects:

- Homebrew, CLIProxyAPI, active config, bind address, and proxy reachability
- WorkBuddy initialization and existing model count
- bundled and local Provider manifests
- CLI executables and login signals without reading token contents
- CLIProxyAPI auth-file counts without exposing account names

Treat an existing CLI login as a discovery signal. CLIProxyAPI may still require its own OAuth grant; do not copy another CLI's token file.

### 2. Bootstrap CLIProxyAPI when required

Preview:

```bash
python3 <skill-dir>/scripts/bridge.py bootstrap
```

Apply the plan when the user asked to install, configure, repair, or converge the bridge:

```bash
python3 <skill-dir>/scripts/bridge.py bootstrap --apply
```

The request to set up the bridge authorizes reversible Homebrew installation, loopback service startup, a dedicated random proxy client key, secure local state, and timestamped backups. Pause only when:

- Homebrew itself is missing and its installer requires administrator interaction
- an existing proxy listens beyond loopback; explain the remote-client impact before using `--allow-rebind-local`
- an overlapping deployment or config conflict makes ownership ambiguous

Keep a healthy existing installation in place. Prefer official Homebrew installation for a new macOS setup.

### 3. Authorize only relevant Providers

Bundled Provider IDs are `codex`, `xai-grok`, and `antigravity`. Authorize a Provider when the user requested it or the audit found its CLI/login signal and CLIProxyAPI has no matching auth/model route.

```bash
python3 <skill-dir>/scripts/bridge.py authorize codex
python3 <skill-dir>/scripts/bridge.py authorize xai-grok
python3 <skill-dir>/scripts/bridge.py authorize antigravity
```

The command delegates to CLIProxyAPI's native OAuth flag. Tell the user to approve the browser page, then continue automatically. Never paste, print, transform, or reuse OAuth tokens. Secure resulting auth JSON files to owner-only permissions.

Do not authorize unrelated Providers merely because they are bundled.

### 4. Probe and synchronize WorkBuddy

Pass only the relevant Provider IDs:

```bash
python3 <skill-dir>/scripts/bridge.py sync --providers codex,xai-grok --apply
```

The sync command:

- fetches the live `/v1/models` list
- selects recommended chat/agent models from Provider manifests
- probes text, SSE streaming, tools, images, and reasoning controls where declared
- skips models whose text or streaming probes fail
- downgrades optional capability flags when their probes fail
- backs up and atomically updates `~/.workbuddy/models.json`
- preserves manual entries and stale managed entries
- refuses to overwrite a manual entry with the same model ID
- records ownership separately under `~/.config/workbuddy-cli-model-bridge/`

Do not use `--skip-probes` for a live setup. That option exists for deterministic offline tests only.

When the user explicitly requests Fast mode and no Fast model appears, read the Fast-model section in [troubleshooting.md](references/troubleshooting.md). A Fast alias needs both a distinct CLIProxyAPI route and verified priority semantics; never relabel an ordinary model as Fast.

A reasoning probe verifies control compatibility. It cannot expose private chain of thought. For teaching or screen recording, ask the model to emit a deliberate problem decomposition as normal answer content.

WorkBuddy represents each custom model as a separate entry. This Skill registers verified entries; it does not change the user's currently selected conversation model.

### 5. Verify the application consumed the change

Run the audit again. If WorkBuddy is already open, inspect its current main-thread log for a `models.json changed` or `Loaded custom models config` event. If no reload event appears, ask the user to reopen model settings or start a new conversation; do not rewrite the same config repeatedly.

Report:

- CLIProxyAPI version/path and local endpoint
- authorized Providers, without account identifiers
- models added or updated
- capability probe results
- conflicts, skipped models, and preserved stale entries
- backup paths and any remaining user action

Never include API keys, OAuth URLs containing one-time codes, token file contents, or raw request bodies.

## Repair workflow

For an expired or broken model:

1. Run `audit` and distinguish proxy-down, missing key, missing OAuth, unavailable model, and WorkBuddy-cache failures.
2. Start or repair the existing service before reinstalling anything.
3. Rerun `authorize <provider>` only when auth is absent or an authenticated probe fails.
4. Rerun `sync --providers <affected-provider> --apply`.
5. Verify a real text request and every declared optional capability.

Do not rotate the WorkBuddy API key merely because a Provider OAuth session changed. The proxy client key and upstream OAuth credentials have different lifecycles.

Read [troubleshooting.md](references/troubleshooting.md) for failure classification and rollback guidance.

## Add a new CLI Provider

Read both:

- [provider-schema.md](references/provider-schema.md)
- [onboarding-new-cli.md](references/onboarding-new-cli.md)

Prefer, in order:

1. CLIProxyAPI native OAuth Provider
2. official OpenAI-compatible endpoint
3. declarative model alias/protocol mapping
4. a bounded local adapter as a separately disclosed last resort

Save machine-local manifests under:

```text
~/.config/workbuddy-cli-model-bridge/providers.d/<provider-id>.json
```

Validate before use:

```bash
python3 <skill-dir>/scripts/bridge.py validate-provider ~/.config/workbuddy-cli-model-bridge/providers.d/<provider-id>.json
```

Then authorize and sync by the new Provider ID. A new manifest becomes reusable by every Agent on the same machine without modifying this Skill. Promote it into the public Skill only after isolated tests prove installation, authentication handoff, model selection, capability accuracy, and rollback behavior.

## Safety boundaries

Read [security-boundaries.md](references/security-boundaries.md) before changing service exposure, credentials, or adding a local adapter.

- Bind the proxy to loopback and keep remote management disabled.
- Store bridge secrets, OAuth files, WorkBuddy config, and credential-bearing backups with mode `0600`.
- Use only accounts the user owns and respect Provider subscription terms and rate limits.
- Never implement ban evasion, account sharing, automated block reset, token extraction, or hidden traffic cloaking.
- Preserve user-created WorkBuddy models and unrelated CLIProxyAPI configuration.
- Treat Provider manifests as code: validate their source and inspect local overrides before executing login flags.

## Completion gate

Completion requires:

- audit has no unresolved security error
- CLIProxyAPI is reachable on loopback with the dedicated client key
- each registered model passed text and streaming probes
- every enabled optional capability passed its probe
- WorkBuddy loaded the resulting model list
- repeated sync is idempotent
- backups and rollback paths are reported

If any gate remains unproven, report the model as unverified rather than declaring success.
