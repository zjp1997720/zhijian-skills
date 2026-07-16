# Skill Open Sourcer

[中文文档](README.zh-CN.md)

Turn a local agent skill into a clean, installable open-source GitHub repository.

## Agent Install

```bash
npx skills add zjp1997720/skill-open-sourcer -g -a codex --skill skill-open-sourcer -y
```

List the skill before installing:

```bash
npx skills add zjp1997720/skill-open-sourcer --list
```

After installing, ask Codex to use `$skill-open-sourcer` with a local `SKILL.md` path or skill directory.

## Requirements

- Python 3
- Git
- Node.js with `npx`
- GitHub publishing access through one of:
  - authenticated `gh` CLI
  - GitHub MCP/app in the agent runtime
  - an existing authenticated `origin` remote

## What It Does

- Audits a local skill for obvious public-release blockers.
- Packages the skill into the layout expected by `npx skills`.
- Generates human-facing release files such as README, Chinese README, and LICENSE. For multi-skill collections, it can also generate `skills.sh.json`.
- Validates the packaged skill before publishing.
- Publishes through GitHub when a safe publishing surface is available.
- Produces install instructions, GitHub metadata recommendations, and launch copy.

## How It Works

The skill treats open-sourcing as a gated release workflow, not a file copy.

It first checks the local environment, then scans the source skill for release blockers such as secrets, personal absolute paths, cache files, large generated artifacts, and unclear assets. When the package is safe, it builds a small release repository with the agent-facing skill and human-facing docs in the right place for the release shape.

The detailed agent workflow lives in [`SKILL.md`](SKILL.md). Humans usually do not need to run the helper scripts directly.

## Example Requests

```text
Use $skill-open-sourcer to publish ~/.codex/skills/my-skill as an open-source repo.
Use $skill-open-sourcer to package this local SKILL.md for npx skills installation.
Use $skill-open-sourcer to audit this skill before I share it publicly.
```

## Repository Layout

```text
.
├── README.md
├── README.zh-CN.md
├── LICENSE
├── SKILL.md
├── agents/openai.yaml
├── references/release-package.md
└── scripts/
    ├── check_release_env.py
    └── scan_skill_release.py
```

## License

[MIT](LICENSE)
