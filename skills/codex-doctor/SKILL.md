---
name: codex-doctor
description: Audit Codex installation health and workspace context quality by combining the built-in `codex doctor` report with read-only checks for AGENTS.md scope, instruction bloat or duplication, Skills, MCP, hooks, config, Git state, and repository-root hygiene. Use whenever the user asks for `/doctor`, `/checkup`, Codex health checks, context cleanup, AGENTS.md cleanup, unused or broken Skills/MCP/hooks, slow or polluted context, or asks why Codex is ignoring rules. Default to diagnosis only; never edit, disable, delete, trust, install, update, authenticate, move, or clean anything without a separately approved finding-level diff.
---

# Codex Doctor

Run a two-layer health check:

1. Reuse Codex's stable built-in `codex doctor --json` for installation, config, auth, runtime, Git environment, terminal, app-server, update, and thread-inventory checks.
2. Run the bundled read-only scanner for workspace context governance that the built-in command does not cover.

The scanner gathers deterministic evidence. You make the semantic judgment. This separation matters because a script can prove that text repeats, but it cannot safely decide that a business fact, safety boundary, brand voice, or directory rule is disposable.

## Run the check

Resolve the Skill directory from the loaded Skill path, then run:

```bash
python3 <skill-dir>/scripts/scan_workspace.py --cwd "$PWD" --compact-json
```

For a faster workspace-only pass when the built-in report was already run in the same task:

```bash
python3 <skill-dir>/scripts/scan_workspace.py --cwd "$PWD" --compact-json --skip-built-in
```

`--compact-json` preserves every finding and every built-in check row while omitting large Skill inventories and verbose passing-check details. Use `--json` only when full deterministic inventory evidence is required.

Do not save the raw built-in report inside the repository. If temporary storage is needed, use `/tmp` and remove it before finishing.

## Interpret findings

Read [checks-and-repair-policy.md](references/checks-and-repair-policy.md) before proposing any cleanup or repair. Keep severity and confidence separate:

- `S0`: proven secret exposure or proven destructive risk
- `S1`: broken effective configuration, truncated hard rules, missing enabled executables, or installation/update mismatch
- `S2`: exact redundancy, duplicate active names/sources, or a clear project hygiene violation
- `S3`: maintenance pressure, stale disabled entries, new-version notice, or oversized descriptions
- `S4`: informational, semantic candidate, or evidence gap

Treat `semantic_candidates` as prompts for inspection, not findings. Read the relevant source section and classify it as one of:

- behavior rule or safety boundary: preserve
- user preference, brand voice, business fact, or directory contract: preserve
- repo fact that requires multi-file synthesis: usually preserve
- directly discoverable inventory, framework version, dependency list, or directory listing: candidate to trim
- stale or contradictory statement: verify against the repository before proposing a change

## Unused Skill evidence

Static discovery cannot prove a Skill is unused. If the user explicitly asks for unused or low-frequency Skills, use the installed `codex-skill-admin` Skill in read-only audit mode:

```bash
python3 <codex-skill-admin-dir>/scripts/codex_skill_admin.py audit-unused --cwd "$PWD" --days 30
```

Report the evidence window and distinct session/source count. Do not disable anything unless the user separately asks and approves the target list.

## Report structure

Lead with the overall result, then show only actionable or decision-relevant items:

```markdown
# Codex 健康检查

状态：PASS / WARN / FAIL

## 需要处理
- [finding id] severity / confidence — conclusion
  Evidence: source and observed state
  Impact: concrete failure or context cost
  Recommendation: exact next action

## 建议人工审查
- semantic candidates with why they may be inferable or stale

## 已通过
- grouped domains, not every low-level row

## Evidence gaps
- checks that cannot be proven from public/local data
```

Preserve built-in doctor sub-checks as separate facts. For example, an HTTP reachability failure and a WebSocket success must remain two rows; do not collapse them into “the network is broken.”

## Repair protocol

Diagnosis does not authorize repair. When the user asks to fix findings:

1. Show one finding ID, the exact source, why it is wrong, and a single-file unified diff.
2. Ask for explicit approval of that finding ID when the change deletes or semantically rewrites instructions, changes config, enables/disables a component, or moves files.
3. Recompute the source file SHA-256 immediately before applying the patch. Stop if it differs from the scan evidence.
4. Apply only the approved diff with `apply_patch`.
5. Rerun the relevant check and report the before/after result.

Never automatically:

- delete or weaken safety rules, brand/persona rules, business facts, project facts, Git gates, or directory boundaries
- delete text merely because it is duplicated across AGENTS.md and CLAUDE.md; cross-host parity may be intentional
- execute hooks to measure performance
- trust hooks, log in to MCP, expose credentials, install dependencies, update Codex, or change providers
- modify sandbox, approval, model, network, or authentication settings
- run destructive Git commands, clean untracked files, or move protected project directories

## Completion checks

Before reporting completion:

- confirm the scanner made no repository changes
- distinguish built-in Codex diagnostics from workspace-governance findings
- label inference as inference
- report skipped checks and evidence gaps
- if repairs were approved, verify each changed file and rerun its domain check
