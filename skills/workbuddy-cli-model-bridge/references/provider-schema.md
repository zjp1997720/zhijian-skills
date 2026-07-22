# Provider manifest schema

Provider manifests are declarative discovery and model-selection rules. They do not contain credentials, shell fragments, endpoints with embedded secrets, or arbitrary install commands.

## Location and precedence

Bundled manifests live in `providers/*.json`. Machine-local manifests live in:

```text
$HOME/.config/workbuddy-cli-model-bridge/providers.d/*.json
```

A local manifest with the same `id` overrides the bundled manifest. Inspect that file before using it; local precedence is intentional but creates a trust boundary.

## Complete example

```json
{
  "schema_version": 1,
  "id": "example-cli",
  "display_name": "Example CLI",
  "cli": {
    "commands": ["example"],
    "auth_hints": [".config/example/auth.json"]
  },
  "cliproxy": {
    "provider": "example",
    "login_flag": "--example-login",
    "auth_file_prefixes": ["example-"]
  },
  "models": [
    {
      "key": "example-primary",
      "candidates": ["example-3-fast", "example-2-fast"],
      "patterns": ["^example-[0-9.]+-fast$"],
      "workbuddy": {
        "supportsToolCall": true,
        "supportsImages": false,
        "supportsReasoning": true,
        "useCustomProtocol": true,
        "onlyReasoning": false,
        "reasoning": {
          "defaultEffort": "medium",
          "supportedEfforts": ["low", "medium", "high"],
          "canDisableThinking": true
        }
      }
    }
  ]
}
```

## Fields

### Top level

- `schema_version`: integer `1`.
- `id`: unique kebab-case Provider ID.
- `display_name`: user-facing Provider name.
- `cli`: local CLI discovery metadata.
- `cliproxy`: CLIProxyAPI integration metadata.
- `models`: ordered recommended-model rules.

### `cli`

- `commands`: candidate executable names. Discovery uses `PATH`; commands are never run from the manifest.
- `auth_hints`: paths relative to the user's home. Existence is only a login signal. The bridge never reads these files.

### `cliproxy`

- `provider`: expected CLIProxyAPI `owned_by` value.
- `login_flag`: optional native CLIProxyAPI OAuth flag. It must start with `--` and is passed as one argument, never evaluated by a shell.
- `auth_file_prefixes`: filename prefixes used only to count matching auth files. Account names and file contents stay hidden.

If the Provider uses an API key or existing OpenAI-compatible route, omit `login_flag`. Configure the compatible route separately and keep its key outside the manifest.

### `models[]`

- `key`: stable rule identity; it does not become the WorkBuddy model ID.
- `candidates`: exact upstream IDs in preference order.
- `patterns`: optional fallback regular expressions.
- `optional`: omit or set `false` for the primary recommendation; use `true` for Fast or secondary variants that may not exist.
- `workbuddy`: claimed capabilities to probe before registration.

Exact candidates win over regular expressions. A pattern match is constrained to the manifest's CLIProxyAPI Provider when `owned_by` is available.

### `workbuddy`

Allowed fields:

- `supportsToolCall`
- `supportsImages`
- `supportsReasoning`
- `useCustomProtocol`
- `onlyReasoning`
- `reasoning`
- `maxInputTokens`
- `maxOutputTokens`

Omit token limits unless an authoritative source and live behavior agree. WorkBuddy can use Provider defaults; a guessed limit is worse than no limit.

Capability booleans are requested claims. Live sync verifies them and downgrades optional claims that fail. Text and streaming are required for every registered model.

## Validation

```bash
python3 <skill-dir>/scripts/bridge.py validate-provider path/to/provider.json
```

Validation rejects unknown WorkBuddy keys, invalid IDs, duplicate recommendation keys, malformed regexes, and login flags that are not single `--flag` arguments.

Validation cannot prove that a login flag is trustworthy or that a model is entitled under the user's plan. Confirm those facts from official documentation and live probes.
