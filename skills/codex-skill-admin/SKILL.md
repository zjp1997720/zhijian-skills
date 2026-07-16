---
name: codex-skill-admin
description: Codex-only skill administration for auditing, enabling, disabling, restoring, and verifying local Codex skills. Use when the user asks to manage Codex skills, reduce skill token load, close unused skills without uninstalling them, restore disabled skills, inspect current skill visibility, or automate skill enablement through Codex's official app-server protocol.
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

- Count actual `SKILL.md` reads from recent Codex session tool calls.
- Count OMO dynamic session fingerprints that include `SKILL.md`.
- Count usage as distinct evidence source/session files, so repeated reads inside one session do not inflate `usageCount`.
- Ignore always-loaded "Available skills" lists, because they are not usage.

This is local evidence, not the product Profile page's server-side analytics.

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
