---
name: skill-open-sourcer
description: Audit, package, add, verify, and publish local Agent Skills through the canonical zjp1997720/zhijian-skills portfolio. Use when the user gives a SKILL.md or Skill directory and asks to open-source, publish, release, share, validate, manage versions, make installable with npx skills, prepare documentation, or generate launch copy. Every public Skill must live under skills/<name>/ in Zhijian Skills; never create or update a standalone Skill repository.
---

# Skill Open Sourcer

Publish every public Skill from the single canonical repository: `https://github.com/zjp1997720/zhijian-skills`.

## Hard publishing boundary

- A `SKILL.md` path or Skill directory is an import candidate, not a request to create a repository.
- Put the complete agent payload in `skills/<name>/`, human docs in `docs/skills/<name>/`, and release notes in `docs/changelogs/<name>.md`.
- Register the Skill in `registry/skills.json`. Never add `mirror`, `mirror_tag`, standalone repository, redirect workflow, or mirror-export metadata.
- Publish commits, per-Skill Tags, and install instructions only from `zjp1997720/zhijian-skills`.
- Stop on secrets, private paths, client data, unpublished proprietary material, unclear asset ownership, or an unverified canonical remote.

Read [Portfolio mode](references/portfolio-mode.md), [Registry contract](references/registry-contract.md), [Release package](references/release-package.md), and [README design](references/readme-design.md) before writing.

## Workflow

1. Resolve the input to a real Skill directory. Accept a `SKILL.md`, its containing directory, or a symlink from a local Skill root.
2. Resolve the canonical checkout from the current repository, `ZHIJIAN_SKILLS_REPO`, or `~/Documents/GitHub/zhijian-skills`. Verify `origin` resolves to `zjp1997720/zhijian-skills`; never guess another destination.
3. Follow the canonical repository's Git synchronization rules, then run:

```bash
SKILL_OPEN_SOURCER_DIR="<zhijian-skills>/skills/skill-open-sourcer"
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/check_release_env.py" \
  --repo-dir <zhijian-skills> --check-npx-skills
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/scan_skill_release.py" \
  /path/to/skill-or-SKILL.md
```

4. Inspect `SKILL.md` and directly referenced `agents/`, `references/`, `scripts/`, and `assets/`. Copy only the complete, sanitized install payload into `skills/<name>/`; preserve required license and third-party notices.
5. Create or update bilingual docs, Changelog, Registry record, Portfolio catalog, and project-native visuals. Never expose a root-level `SKILL.md` or add human README files inside the Skill payload.
6. Choose the version with [version-contract.md](references/version-contract.md). Use only the canonical Tag `<skill>/v<version>`.
7. Validate the Skill, declared tests, full Portfolio, documentation, and repository contracts:

```bash
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/portfolio.py" \
  validate-skill <zhijian-skills>/skills/<name>
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/portfolio.py" \
  audit --repo <zhijian-skills> --strict
python3 -m unittest discover -s <zhijian-skills>/tests -v
```

8. Verify local `npx skills` discovery and one isolated copy install from the canonical repository. Inspect the installed tree; listing success alone is insufficient.
9. Commit and push canonical `main` only when publishing is authorized. Never call `gh repo create` or publish to `<owner>/<skill-name>`.
10. Verify the remote Portfolio listing and isolated install, then create the canonical Tag and launch copy.

## Output contract

Return:

- canonical Skill URL under `zjp1997720/zhijian-skills`
- the canonical commit, version, and `<skill>/v<version>` Tag
- install command using `npx skills add zjp1997720/zhijian-skills`
- Skill validation, Portfolio audit, remote listing, and isolated-install results
- README presentation tier and deliberate visual assets
- safety summary and residual assumptions
- at least one X/Twitter launch post, plus a Chinese version for Chinese users

If blocked, return the file paths, reasons, sanitization steps, and safest next action.

## Safety rules

Hard stop on:

- API keys, tokens, private keys, cookies, credentials, `.env`, or auth config
- personal absolute paths, local vault paths, or machine-only caches
- client data, private URLs, unpublished prompts, or assets without redistribution rights
- escaping symlinks, databases, logs, browser profiles, `.DS_Store`, dependency caches, or unexplained binaries
- a dirty or unverified canonical repository that cannot be reconciled safely

Never force-push, rewrite published Tags, create a standalone repository, or treat missing evidence as passed.

## Packaging rules

- Every Skill lives at `skills/<skill-name>/`, including a single-file Skill.
- Keep `SKILL.md` lean; put detailed agent guidance in `references/` only when needed.
- Preserve `agents/openai.yaml`; create it when absent with a `$<skill-name>` default prompt.
- Include deterministic scripts and licensed agent-facing assets only.
- Put human docs in `docs/skills/<skill-name>/` and README visuals in its `assets/readme/` directory.
- Update `registry/skills.json`, root README catalogs, and deterministic asset generators together.

## Publication verification

```bash
npx --no-install skills add zjp1997720/zhijian-skills --list
npx skills add zjp1997720/zhijian-skills \
  -g -a codex --skill <skill-name> --copy -y
```

Use the Portfolio's pinned `skills` CLI for deterministic checks. In an empty isolated HOME, invoke the recorded version explicitly with `npx --yes skills@<version>`.

## Launch copy

After all gates pass, explain the repeated problem, what the Skill automates, the canonical install command, one concrete example request, and any relevant safety boundary. Never link a standalone Skill repository.
