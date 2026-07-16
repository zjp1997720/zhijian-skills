# Release Package Reference

Use this reference when turning a local skill into a public repository.

## Repo Layout

Use a flat root layout only for a self-contained single-file Skill:

```text
.
├── README.md
├── README.zh-CN.md
├── LICENSE
└── SKILL.md
```

Current remote `npx skills` installation intentionally copies only the root `SKILL.md`. Do not use this layout when the Skill needs support files.

Use a nested install-payload layout whenever one or more Skills need `agents/`, `references/`, `scripts/`, or agent-facing `assets/`. This includes single-skill repositories:

```text
.
├── README.md
├── README.zh-CN.md
├── LICENSE
└── skills/
    └── <skill-name>/
        ├── SKILL.md
        ├── agents/openai.yaml
        ├── scripts/
        ├── references/
        └── assets/
```

Only include support directories the source Skill actually needs. Add `skills.sh.json` when a multi-skill collection benefits from curated grouping metadata; nested discovery does not require a manifest.

## skills.sh.json

For a self-contained flat Skill, omit `skills.sh.json` and let `npx skills` discover the root `SKILL.md`.

For a multi-skill collection repo, use a small manifest so `npx skills add <owner>/<repo> --list` can discover the skills.

```json
{
  "$schema": "https://skills.sh/schemas/skills.sh.schema.json",
  "groupings": [
    {
      "title": "Agent Skills",
      "description": "Installable agent skills.",
      "skills": ["<skill-name>"]
    }
  ]
}
```

Choose a grouping title and description that match the domain. Keep the `skills` values equal to folder names under `skills/`.

## README Contract

Root README files are trust entrances and install entrances. They should answer three questions within the first screen:

1. What is this?
2. Why is it worth using?
3. How does an agent install or start?

README is not the full manual. Put detailed agent procedure in `skills/<skill-name>/SKILL.md`, and put long references in the skill's `references/` folder.

Read `readme-design.md` before writing. It defines the story sequence, presentation tiers, project-native visual direction, GitHub-safe SVG rules, and preview checks. Every release gets the content architecture; only evidence-rich releases get visual assets.

Root README files should explain:

- What the skill is.
- Why someone would use it.
- What problem it removes.
- How an agent installs it.
- What the agent-facing skill does at a high level.
- Safety or requirements that matter.

Avoid dumping long script manuals into README. If the Skill has support files, say that the agent-facing workflow lives in `skills/<skill-name>/SKILL.md`. Reserve a root `SKILL.md` for genuinely self-contained releases.

Before writing, extract these fields from the skill:

| Field | Purpose |
| --- | --- |
| `project_name` | Public repo and README title |
| `tagline` | One short value proposition |
| `audience` | Which agent users need it |
| `problem` | The repeated pain it removes |
| `promise` | What result the user gets |
| `proof` | Real commands, outputs, screenshots, or examples |
| `start` | Shortest safe install/use path |
| `native_material` | The real interface, artifact, transformation, diagram, or command output that can carry the visual story |

Required README sections:

```text
# <Skill Display Name>

`README.zh-CN.md`

One short value proposition.

## Agent Install

`npx skills add ...`

## Requirements

Short environment requirements.

## What It Does

Human-readable bullets.

## How It Works

Plain-language principle, not implementation trivia.

## Example Requests

Prompts that show when to use `$<skill-name>`.

## Repository Layout

Short tree.

## License
```

`README.zh-CN.md` should mirror the same contract in natural Chinese. Do not mechanically translate awkward English.

Quality gate:

- The first screen must show the project name, value proposition, and install path or clear path to install.
- Keep badges to 0-3. Use only badges that help trust or installation.
- Prefer 3 result-oriented capability bullets over a long feature wall.
- Keep script details out of README unless humans must run them directly.
- Explain safety boundaries plainly when the skill touches local files, GitHub publishing, credentials, browser state, or user data.
- Do not include internal design scores, private workflow notes, generated file inventories, or implementation trivia.
- Do not add decorative ASCII art, emoji heading systems, social-link tables, or marketing claims that the skill does not prove.
- Move detailed configuration, troubleshooting, and protocol notes to `docs/` or the skill's `references/`.
- Put real proof before abstract claims. One complete example is stronger than a wall of disconnected features.
- Make every visual module perform a communication job: identity, proof, comparison, sequence, or architecture.
- Keep the README meaningful when images fail; headings, alt text, commands, and links must still carry the release.

For visual assets:

- Use the `clean-doc` tier for small infrastructure skills or releases without honest visual proof.
- Use the `proof-led` tier for skills with a real UI, document, chart, media output, before/after result, or architecture that helps adoption.
- Default to one project-native hero or one proof board. Add both only when the hero stays concise and the proof needs more room to remain legible.
- Store release visuals under stable paths such as `assets/readme/hero.svg` and `assets/readme/showcase.webp`.
- Do not create dense flow images, tiny text diagrams, generic technical decoration, or covers that could belong to an unrelated repository.
- Do not insert attribution, backlinks, or a “made with” badge unless the repository owner explicitly requests it.

## Skill Folder Contract

The public skill folder must remain agent-first:

- `SKILL.md` contains triggerable workflow instructions.
- `agents/openai.yaml` contains UI metadata only.
- `references/` contains detailed agent guidance that should not always load.
- `scripts/` contains deterministic helpers.
- `assets/` contains only licensed, necessary assets.

Do not add `README.md`, install guides, changelogs, or marketing docs inside `skills/<skill-name>/`.

For a self-contained flat repo, the root README is human-facing and the root `SKILL.md` is agent-facing. For a nested install payload, each `skills/<skill-name>/` folder stays agent-facing only.

## Sanitization Checklist

Before publishing:

- Replace absolute local paths with placeholders such as `/path/to/input`.
- Remove personal names unless they are part of public authorship.
- Remove client, customer, and private project identifiers.
- Remove machine-specific caches, logs, backups, `.DS_Store`, and `__pycache__`.
- Remove credentials and generated auth files.
- Confirm every bundled asset has public redistribution rights.
- Confirm any copied third-party code has compatible license text.

## Validation Checklist

Before creating or publishing the release repo, run:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/skill-open-sourcer/scripts/check_release_env.py"
```

Interpretation:

- `python3`, `git`, `node`, and `npx` are required.
- `gh` plus successful `gh auth status` is the default local GitHub publishing route.
- If `gh` is missing or unauthenticated, publishing can still proceed through GitHub MCP/app or an existing authenticated `origin` remote.
- If no GitHub publishing surface is available, stop after local packaging and validation.
- Use `--check-npx-skills` before final release verification when network access, npm access, or the `skills` package availability is uncertain.

Run these checks from the release repo root:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/skill-open-sourcer/scripts/audit_release_readme.py" . --strict
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" "."
npx skills add <owner>/<repo> --list
```

For any nested repository, validate each skill folder under `skills/`.

Then perform a real installation in an isolated home directory and inspect the installed tree. For a Codex-targeted Skill:

```bash
TEMP_HOME="$(mktemp -d)"
HOME="$TEMP_HOME" npx skills add <owner>/<repo> \
  -g -a codex --skill <skill-name> --copy -y
find "$TEMP_HOME/.agents/skills/<skill-name>" -maxdepth 3 -type f | sort
```

Every file referenced by `SKILL.md` must be present. A successful `--list` or an installed `SKILL.md` alone does not prove that the package is complete.

If publishing before the remote exists, run the validator first, then run the `npx skills` check after the first push.

The README audit checks deterministic structure, local links and images, alt text, and basic SVG compatibility. Render and inspect every visual separately; the script cannot judge composition, clipping, proof legibility, or visual originality.

Also inspect `git status --short` before committing. Do not commit caches, logs, secrets, large generated files, or unrelated edits.

## GitHub Publishing

Use the available GitHub interface in this order:

1. GitHub app/MCP when available and authenticated.
2. `gh` CLI when authenticated.
3. Existing remote when already configured.

Default repo name: the skill name. If the name is too generic, prefix the target agent, for example `codex-<skill-name>`.

Use normal commits and pushes. Do not force push. If a remote repo exists and has unrelated content, stop and ask.

## GitHub Metadata

Recommend GitHub Description and Topics in the final answer. Do not write them into README as a substitute for setting repo metadata.

Description rules:

- Prefer English.
- Keep it under 160 characters.
- Start with an action verb when natural.
- Name the specific outcome and audience.
- Include 2-3 precise keywords.
- Avoid emoji, hype words, and unsupported claims.

Generate 2-3 description candidates, then name the recommended one.

Topics rules:

- Recommend 7-9 topics when enough signal exists; fewer is better than noisy.
- Use lowercase letters, numbers, and hyphens.
- Include factual categories such as `agent-skill`, `codex`, `developer-tools`, `open-source`, `github-readme`, `automation`, `cli`.
- Avoid overly broad topics such as `ai`, `tool`, `project`, `software`, or `github` unless the topic is truly specific in context.
- Do not add trending topics that the repo does not actually support.

If `gh` is authenticated and the user explicitly asks to update metadata, use:

```bash
gh repo edit OWNER/REPO \
  --description "<final-description>" \
  --add-topic topic-one \
  --add-topic topic-two
```

Do not update Description or Topics silently. Git cannot update these fields; they are GitHub platform metadata.

## Launch Copy

Generate launch copy only after verification passes. Include:

- A short hook naming the problem.
- What the skill automates.
- The install command or repo link.
- One example request.
- A plain safety note if the skill touches local files, credentials, publishing, or user data.

For X/Twitter, keep the main version short enough to post as one tweet. If the explanation needs more room, produce a thread with 2-4 posts.
