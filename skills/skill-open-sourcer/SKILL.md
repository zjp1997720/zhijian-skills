---
name: skill-open-sourcer
description: Package and publish a local agent skill as a polished open-source GitHub repository. Use when the user gives a local SKILL.md path or skill directory and asks to open-source, publish, release, share, make installable with npx skills, prepare or beautify the release README, create a public skill repo, or generate launch/social copy for a local Codex, Agents, Claude, or compatible skill. The workflow includes release safety, project-native README design, GitHub-safe visual assets when evidence supports them, validation, and publishing.
---

# Skill Open Sourcer

Turn one local skill into a clean public release package. The normal input is only a `SKILL.md` path or a skill directory.

Default posture: move fast, but stop on release risk. If the safety scan finds secrets, private paths, client data, unpublished proprietary material, or ambiguous ownership, report the blockers and do not publish until the user resolves them.

## Quick Start

1. Resolve the input to a real skill directory. Accept a `SKILL.md` file, a folder containing `SKILL.md`, or a symlink under `.codex/skills`, `.agents/skills`, `.claude/skills`, or another local skill root.
2. Run the environment check before packaging or publishing:

```bash
SKILL_OPEN_SOURCER_DIR="${CODEX_HOME:-$HOME/.codex}/skills/skill-open-sourcer"
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/check_release_env.py"
```

Required local commands are `python3`, `git`, `node`, and `npx`. `gh` is the default local GitHub publishing surface, but GitHub MCP/app or an existing authenticated remote can replace it. If no GitHub publishing surface is available, build and validate the repo locally, then stop with the missing setup.

3. Read the skill entrypoint and inspect directly referenced `scripts/`, `references/`, `assets/`, and `agents/` files. Do not copy unrelated local folders.
4. Run the safety scanner:

```bash
SKILL_OPEN_SOURCER_DIR="${CODEX_HOME:-$HOME/.codex}/skills/skill-open-sourcer"
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/scan_skill_release.py" /path/to/skill-or-SKILL.md
```

5. If the environment and safety scans are clear, create a fresh release repository outside the source skill directory.
6. Choose the package layout from the install payload. A truly self-contained, single-file Skill may keep `SKILL.md` at the repo root. If the Skill needs `agents/`, `references/`, `scripts/`, or agent-facing `assets/`, place the complete payload under `skills/<skill-name>/`. Current `npx skills` root-level remote installs intentionally copy only `SKILL.md`; a flat package with support files installs incompletely. Preserve applicable source license and third-party notice files. Multi-skill collections also use `skills/<skill-name>/`; add `skills.sh.json` only when curated grouping metadata is useful.
7. Extract the release story, choose the README presentation tier, and build the public release files described in `references/release-package.md`. Read `references/readme-design.md` before writing either README or any `assets/readme/` visual.
8. Audit the README package before publishing:

```bash
SKILL_OPEN_SOURCER_DIR="${CODEX_HOME:-$HOME/.codex}/skills/skill-open-sourcer"
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/audit_release_readme.py" /path/to/release-repo --strict
```

9. Validate the packaged skill, `npx skills` listing, and one isolated real installation before publishing. Inspect the installed file tree; listing success alone does not prove support files were copied.
10. Publish to GitHub when low-risk checks pass, then produce launch copy.

Read `references/release-package.md` before writing the release repo.

## Output Contract

For a successful release, return:

- GitHub repo URL.
- Install command using `npx skills`.
- Verification results for skill validation and `npx skills add <owner>/<repo> --list`.
- README audit result, presentation tier used, and any visual assets deliberately included or omitted.
- Short risk summary: what was scanned, what was removed or sanitized, and any residual assumptions.
- GitHub Description and Topics recommendations when creating a new public repo.
- Launch copy: at least one X/Twitter post, plus optional Chinese version when the user works in Chinese.

If blocked, return:

- Blocker list with file paths and reasons.
- Suggested sanitization steps.
- The safest next action, usually "clean these files, then rerun the release".

## Safety Rules

Hard stop when any of these appear in the source package:

- API keys, tokens, private keys, cookies, credentials, `.env` files, or auth config.
- Absolute personal paths such as `/Users/...`, `/home/...`, local vault paths, or machine-only cache paths that would confuse public users.
- Customer names, private company data, internal docs, private URLs, unpublished prompts, or paid/proprietary assets without a clear license.
- Symlinks that escape the package, large binaries, databases, logs, browser profiles, `.DS_Store`, `__pycache__`, or generated cache files.
- Unclear license or ownership for bundled code/assets.

Low-risk auto publish is allowed only when the scanner and manual review find no blockers. If the target GitHub repo already exists with unrelated content, stop and ask before overwriting or force pushing.

## Packaging Rules

- Keep the original skill behavior intact. Refactor only enough to remove private assumptions and make public installation reliable.
- Use a flat root layout only for a self-contained `SKILL.md` with no supporting payload. Use `skills/<skill-name>/` whenever installation must include `agents/`, `references/`, `scripts/`, or agent-facing `assets/`, including single-skill repositories.
- Prefer a lean `SKILL.md`; move detailed public guidance into `references/` only when an agent will genuinely need it.
- Do not add a README inside the skill folder. Put human-facing documentation at the release repo root.
- Preserve `agents/openai.yaml` when present. If absent, create it with `display_name`, `short_description`, and a `default_prompt` that explicitly mentions `$<skill-name>`.
- Include `scripts/` only for deterministic helper logic the skill actually uses.
- Include `assets/` only when licensing and size are safe for public release.
- Put release-specific visuals under `assets/readme/`. Use real outputs or project-native diagrams; skip visuals when they add no explanatory value.
- Keep install commands, requirements, links, and long explanations in Markdown. Visuals support the story and must not become the only carrier of essential information.
- Use MIT as the default license only when the source skill has no conflicting license and ownership is clear.

## Publication Flow

1. Run `scripts/check_release_env.py`. Add `--repo-dir <release-repo>` when updating an existing local repo. Add `--check-npx-skills` when package/network access is uncertain.
2. If required commands are missing, stop and report the exact blockers. If only `gh` is missing, continue only when GitHub MCP/app is available or the release repo already has an authenticated `origin` remote.
3. Build the release repo locally, including the README package and any licensed proof assets.
4. Run `scripts/audit_release_readme.py <release-repo> --strict`. Fix hard failures and review every warning; visual taste still requires local rendering and inspection.
5. Validate with the system skill validator when available:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" .
```

6. Create or update the GitHub repository using the available GitHub surface (`gh`, GitHub MCP/app, or existing remote). Avoid force push.
7. Push the branch or `main`.
8. Verify listing:

```bash
npx skills add <owner>/<repo> --list
```

9. Run an isolated real install with copy mode, then verify the expected support files exist under the temporary agent skill directory. Use the exact target agent intended by the release. Never treat `--list` as sufficient package validation.

10. If listing and the isolated install work, provide the install command:

```bash
npx skills add <owner>/<repo> -g -a codex --skill <skill-name> --copy -y
```

Adjust the agent flag and install wording when the target platform is not Codex.

## Launch Copy

After a successful release, draft concise social copy that explains:

- The problem the skill solves.
- What a user gives it.
- What it publishes or automates.
- The install command or repo link.
- One concrete example request.

For Chinese users, include a natural Chinese launch post. Keep it human-facing; do not over-explain scripts.
