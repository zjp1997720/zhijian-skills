# Checks and repair policy

## Capability boundary

The stable built-in `codex doctor` owns runtime diagnostics. This Skill extends it with workspace context governance. Do not reimplement or reinterpret a built-in check when its redacted JSON result is available.

| Domain | Deterministic evidence | Semantic judgment | Automatic repair |
|---|---|---|---|
| Built-in health | `codex doctor --json` | preserve independent sub-checks | none |
| AGENTS effective chain | global and root-to-CWD discovery, byte limit | whether a rule belongs at this scope | none |
| Exact duplication | normalized blocks outside frontmatter | intentional reinforcement vs waste | none |
| Inferable content | heading and section candidates | whether code discovery is cheaper and reliable | none |
| Skills | frontmatter, names, references, size, path | trigger overlap and source ownership | none |
| MCP | enabled state, command existence, URL shape | whether the server is useful | none |
| Hooks | JSON/TOML shape, source merging, command existence | business intent and performance | none |
| Config | TOML parse, secret-shaped project keys | whether a high-permission choice is acceptable | none |
| Git/root hygiene | read-only status and known generated directories | whether an untracked item has long-term value | none |

## AGENTS discovery

Build the effective chain for the current working directory:

1. `$CODEX_HOME/AGENTS.override.md`, otherwise `$CODEX_HOME/AGENTS.md`; use only the first non-empty global file.
2. From Git root to CWD, select at most one file per directory: `AGENTS.override.md`, then `AGENTS.md`, then configured fallback names.
3. Concatenate root to leaf. Later, more local guidance overrides earlier guidance.
4. Flag the point where combined bytes exceed `project_doc_max_bytes` (32 KiB when unset).

Analyze only the effective chain for conflicts. Keep sibling-directory files as inventory; their scopes do not overlap.

## Protected semantic classes

Default to preserve when a rule contains any of these meanings:

- authorization, destructive-action, privacy, credential, Git, publication, payment, production, or account boundaries
- persona, voice, language, brand, customer, product, business, or historical facts
- file ownership, generated-source, plugin-cache, protected-directory, or cross-device synchronization contracts
- dates, named organizations, named people, IDs, exact paths, or operational thresholds

These classes may repeat intentionally across hosts or scopes. Repetition is evidence of context cost, not proof of redundancy.

## Inferable-content test

A section is a strong trim candidate only when all are true:

- it states static inventory that a short deterministic command can recover
- it contains no reason, exception, historical constraint, or decision context
- it contains no organization-specific behavior or acceptance criterion
- removing it does not change how Codex should act
- the repository evidence is current and unambiguous

Framework names, dependency versions, generated directory trees, and exhaustive file lists often qualify. Architectural boundaries that require reading several files often do not.

## Repair gates

Every proposed repair must pass:

1. Evidence gate: source, scope, observed state, expected state, impact.
2. Confidence gate: high confidence for mechanical edits; semantic deletion remains manual even at high confidence.
3. Diff gate: one file and one finding per approval.
4. Authorization gate: explicit approval of the finding ID.
5. Concurrency gate: pre-apply SHA-256 equals the scan-time SHA-256.
6. Verification gate: rerun the domain check and inspect Git diff.

Severity never grants permission. S0/S1 findings often require more caution because their repair impact is higher.

## Known evidence gaps

- Claude Code's private `/doctor` prompts, telemetry, and interactive repair state machine
- reliable proof that a Skill, MCP server, or plugin is unused without usage telemetry
- historical hook latency without executing hooks or reading trusted telemetry
- deterministic classification of “Claude/Codex can infer this from the repo”
- full parity between CLI, desktop, IDE, cloud, and managed-policy effective configuration
- long-term stability of every field in `codex doctor --json`; parse by `schemaVersion` and tolerate unknown fields
