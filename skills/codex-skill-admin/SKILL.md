---
name: codex-skill-admin
description: "核对、启停或恢复Codex Skill可见性与加载开销；不卸载插件。"
---

# Codex Skill Admin

Use Codex's official skill config API. Do not edit `SKILL.md` frontmatter to disable a skill, and do not uninstall plugins unless the user explicitly asks for uninstall.

## Quick Start

Use the bundled script for normal work:

```bash
SKILL_DIR="${CODEX_SKILL_ADMIN_DIR:-$HOME/.agents/skills/codex-skill-admin}"
if [ ! -d "$SKILL_DIR" ]; then
  SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/codex-skill-admin"
fi
python3 "$SKILL_DIR/scripts/codex_skill_admin.py" list --cwd "$PWD"
python3 "$SKILL_DIR/scripts/codex_skill_admin.py" audit-unused --cwd "$PWD" --days 30
python3 "$SKILL_DIR/scripts/codex_skill_admin.py" disable-unused --cwd "$PWD" --days 30
python3 "$SKILL_DIR/scripts/codex_skill_admin.py" disable-unused --cwd "$PWD" --days 30 --apply
python3 "$SKILL_DIR/scripts/codex_skill_admin.py" disable-unused --cwd "$PWD" --days 10 --max-uses 2
python3 "$SKILL_DIR/scripts/codex_skill_admin.py" audit-unused --cwd "$PWD" --days 30 --exclude-session /path/to/session.jsonl
python3 "$SKILL_DIR/scripts/codex_skill_admin.py" verify --cwd "$PWD"
```

The script starts a temporary localhost `codex app-server`, calls:

- `skills/list`
- `skills/config/write`

It saves apply-mode backups under:

```text
${CODEX_HOME:-$HOME/.codex}/backup/skill-disable-unused-YYYYMMDD-HHMMSS/
```

## Workflow

1. Run `list` to get the current total, enabled, and disabled counts.
2. Run `audit-unused --days 30` to inspect high-confidence recent usage.
3. Optionally add `--max-uses N` to include low-frequency skills. Example: `--days 10 --max-uses 2` targets enabled skills used in at most 2 distinct recent session/source files.
4. Run `disable-unused --days 30` without `--apply` and inspect the dry-run output.
5. If the user asked to close unused or low-frequency skills, run `disable-unused --apply`.
6. Verify with `verify`, or with `list --force-reload` plus `prompt-count`.
7. Report counts, backup path, threshold parameters, and any limits of the usage evidence.

System skills are preserved by default. Use `--include-system` only when the user explicitly asks to consider system skills too.

The Codex desktop Skills tab count is a total discovered skill count. It is expected to stay unchanged after disabling skills. Treat `enabledCount` and `availableSkillCount` as the token-load success metrics.

## Usage Evidence

The audit is intentionally conservative:

- Count a read only when a `function_call` or `custom_tool_call` contains an actual file-read operation. `functions.exec` wrappers are parsed for read commands such as `cat` and `sed`; structured read tools are parsed from their path input.
- Require a matching tool result. A result marked successful, with exit code 0, or with non-empty output counts as `success`; a failed result never counts as usage.
- Filter each event timestamp by the requested window. A recent session file does not make an old event recent. Missing or unparseable timestamps are reported as `unknown` and do not count as usage.
- Count `usageCount` as distinct evidence session/source files. Repeated successful reads in one session increase `evidenceCount`, but do not inflate `usageCount`.
- Keep failed, unmatched, unknown, and unsupported read intents in separate audit fields. They protect the affected enabled Skill from becoming a disable candidate until the evidence is classifiable.
- Ignore prose mentions, `SKILL.md` paths in general audit/available-Skills listings, and OMO fingerprints without structured tool events. OMO events are counted only when they retain the same call/result evidence.

This is local evidence, not the product Profile page's server-side analytics.

`audit-unused` and `disable-unused` accept repeatable `--exclude-session PATH` arguments. They also read `CODEX_SKILL_ADMIN_SESSION`, `CODEX_SESSION_FILE`, `CODEX_SESSION_PATH`, `CODEX_SESSION_ID`, and `CODEX_THREAD_ID` when set, so the current audit session can be excluded without copying private session data. The default `--exclude-current-audit` setting ignores calls that invoke this script's own `audit-unused` or `disable-unused` command; use `--no-exclude-current-audit` only when inspecting that invocation itself. An excluded session is reported in `excludedSessionCount` and does not contribute evidence.

The audit JSON keeps the existing `usedEnabled`, `disableCandidates`, `usageCount`, and `evidenceCount` fields. It additionally reports the per-path `readIntent`, `unknown`, `failed`, and `unsupported` evidence, plus `uncertainEnabled`, `rawReadIntentSkillPathCount`, `rawUnknownSkillPathCount`, `rawFailedSkillPathCount`, `unsupportedEvidenceCount`, `outsideWindowCount`, and `missingTimestampCount`. `disableCandidates` contains enabled Skills with no proven usage and no uncertain read intent; an uncertain or unsupported record is never silently treated as zero use.

If the same skill appears through multiple equivalent paths, set path aliases before auditing:

```bash
export CODEX_SKILL_ADMIN_PATH_ALIASES="/old/root=/new/root"
```

Use the platform path separator for multiple aliases.

## Verification

After an apply run:

1. Run `verify --cwd "$PWD"`.
2. Confirm `enabledCount` dropped and target skills appear in `list --force-reload --disabled`.
3. Confirm `availableSkillCount` dropped versus the pre-run count when disabled skills were previously prompt-visible.
4. Ignore the desktop UI tab count for token savings; it counts total discovered skills, including disabled ones.
5. If the result is wrong, run `restore --backup-dir <backupDir>` using the backup path from the apply output.

Backup files include local skill paths and usage evidence. Treat them as private machine-local diagnostics.

## Restore

Restore a previous disable run:

```bash
SKILL_DIR="${CODEX_SKILL_ADMIN_DIR:-$HOME/.agents/skills/codex-skill-admin}"
if [ ! -d "$SKILL_DIR" ]; then
  SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/codex-skill-admin"
fi
python3 "$SKILL_DIR/scripts/codex_skill_admin.py" restore --backup-dir "${CODEX_HOME:-$HOME/.codex}/backup/skill-disable-unused-YYYYMMDD-HHMMSS"
```

## Direct Set

Use `set` for specific skill toggles only after listing or otherwise confirming the target name/path:

```bash
python3 "$SKILL_DIR/scripts/codex_skill_admin.py" set --name codex-skill-admin --no-enabled
python3 "$SKILL_DIR/scripts/codex_skill_admin.py" set --name codex-skill-admin --no-enabled --apply
```

Without `--apply`, `set` prints a dry run and writes nothing.

## Manual Protocol Notes

Read `references/app-server-protocol.md` only when the script fails or the Codex app-server protocol changes.
