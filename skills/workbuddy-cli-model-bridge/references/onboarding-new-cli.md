# Onboard a new CLI Provider

Use this workflow when the requested CLI is not in the bundled Provider directory.

## 1. Establish identity

Collect read-only evidence:

- exact executable path and version
- `--help` output
- official repository and documentation
- documented login/status command
- documented model IDs and protocols
- whether CLIProxyAPI already exposes a native login flag or plugin

Use primary sources for technical claims. Do not treat a blog post, tweet, model name, or another user's config as sufficient evidence.

Do not execute a newly discovered login, update, plugin, or install command until its source and purpose are clear.

## 2. Choose the narrowest route

Use this order:

1. **CLIProxyAPI native Provider** — best preservation of OAuth refresh, tools, streaming, images, and reasoning controls.
2. **Official OpenAI-compatible endpoint** — suitable when the CLI/vendor documents a stable Base URL and credential method.
3. **Declarative alias or payload mapping** — suitable when the upstream route already works but WorkBuddy needs a stable model ID or a verified Fast/priority variant.
4. **Bounded local adapter** — last resort when no compatible protocol exists.

Do not scrape a CLI token and inject it into another application. An existing CLI login only tells you that the Provider is relevant. Use a supported OAuth or credential handoff.

## 3. Inspect runtime models

After the route is authenticated, query CLIProxyAPI's live model list. Record:

- exact model ID
- `owned_by` Provider
- stable versus preview status
- chat/agent suitability
- any Fast or reasoning alias that is actually routed

Filter image-generation, video-generation, embedding, transcription, and deprecated models unless WorkBuddy explicitly gains a matching interface.

## 4. Create a local manifest

Write one JSON file under:

```text
$HOME/.config/workbuddy-cli-model-bridge/providers.d/<provider-id>.json
```

Follow [provider-schema.md](provider-schema.md). Keep credentials and personal account identifiers out of the manifest.

Validate it before authorization or sync:

```bash
python3 <skill-dir>/scripts/bridge.py validate-provider "$HOME/.config/workbuddy-cli-model-bridge/providers.d/<provider-id>.json"
```

## 5. Verify capabilities independently

Run the bridge sync without `--skip-probes`. A successful text answer does not prove tools, images, streaming, or reasoning controls.

For each claimed capability, verify the complete path:

```text
WorkBuddy-compatible request
→ loopback CLIProxyAPI endpoint
→ selected Provider route
→ expected response shape
```

Keep capability claims conservative. If a model accepts an image but silently drops it, image input is not verified. If a tool request returns prose instead of `tool_calls`, tool use is not verified.

## 6. Promote only reusable knowledge

Keep the manifest local until it works across:

- a clean test home
- an existing WorkBuddy config with manual models
- repeated idempotent sync
- missing/expired authentication
- capability failure and rollback

When promoting a Provider into the public Skill, remove personal paths, account names, private endpoints, tokens, cached responses, and machine-specific model availability. Add deterministic fixtures and update the public changelog.

## Local adapter gate

A local adapter introduces protocol, maintenance, and credential risks. Before creating one, document:

- why native OAuth and official compatibility are unavailable
- the exact binary it invokes
- allowed tools, filesystem access, network access, timeouts, and concurrency
- how images and tools are represented
- how streaming is implemented
- how the adapter is stopped and removed

Bind it to loopback, use a separate random key, disable unnecessary tools, and test the raw upstream separately from the adapter. Tell the user that this route is less stable than a native Provider.
