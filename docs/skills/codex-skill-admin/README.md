# Codex Skill Admin

[![skills.sh](https://skills.sh/b/zjp1997720/codex-skill-admin)](https://skills.sh/zjp1997720/codex-skill-admin)

[中文文档](README.zh-CN.md)

Codex Skill Admin is a Codex-only agent skill for auditing, disabling, restoring, and verifying local Codex skills through Codex's local app-server API.

Use it when you want to reduce prompt token load by disabling unused skills without uninstalling them.

## Agent Install

```bash
npx skills add zjp1997720/codex-skill-admin -g -a codex --skill codex-skill-admin -y
```

List the skill before installing:

```bash
npx skills add zjp1997720/codex-skill-admin --list
```

After installing, ask Codex to use `$codex-skill-admin` for skill cleanup tasks. The agent-facing workflow lives in `skills/codex-skill-admin/SKILL.md`; humans do not need to run the helper script directly.

## Requirements

- Codex CLI with `codex app-server`
- Python 3.10+

## What It Does

- Lists enabled and disabled Codex skills.
- Audits recently used skills from local Codex session evidence.
- Disables unused enabled skills with a dry-run first.
- Supports low-frequency cleanup, such as disabling skills used at most 2 times in the last 10 days.
- Restores a previous disable run from backup files.
- Counts skills visible in the next Codex prompt.
- Explains the difference between the desktop UI total count and effective enabled/prompt-visible counts.

## How It Works

Codex loads skill metadata into the prompt so it can decide which skill to use. When many skills stay enabled, the prompt gets heavier even if most of them are not useful for the current task.

This tool looks at local Codex session files and searches for real `SKILL.md` reads. If a skill was read recently, it is treated as used. If it was not read, or if it was read no more than your `--max-uses` threshold, it becomes a disable candidate.

Disabling a skill does not delete it. The script calls Codex's local `skills/config/write` API to mark the skill as disabled, writes a local backup, and lets you restore it later. The desktop UI may still count the skill because the file still exists; the important numbers are enabled skills and prompt-visible skills.

## Safety Defaults

- `disable-unused` is a dry run unless `--apply` is passed.
- `set` is a dry run unless `--apply` is passed.
- System skills are preserved by default. Use `--include-system` only when you explicitly want to consider system skills.
- Apply-mode backups are written under `${CODEX_HOME:-$HOME/.codex}/backup/`.
- Backup files contain local skill paths and usage evidence. Treat them as private machine-local diagnostics.

## Example Requests

```text
Use $codex-skill-admin to audit skills I have not used in the last 30 days.
Use $codex-skill-admin to disable skills used at most 2 times in the last 10 days.
Use $codex-skill-admin to restore the last disable run.
Use $codex-skill-admin to verify whether the cleanup reduced prompt-visible skills.
```

The desktop Skills tab count may stay unchanged because it counts installed/discovered skills, including disabled ones. The useful success signals are fewer enabled skills and fewer prompt-visible skills.

## Repository Layout

```text
.
├── README.md
├── README.zh-CN.md
├── LICENSE
├── skills.sh.json
└── skills/
    └── codex-skill-admin/
        ├── SKILL.md
        ├── agents/openai.yaml
        ├── scripts/codex_skill_admin.py
        └── references/app-server-protocol.md
```

## License

MIT
