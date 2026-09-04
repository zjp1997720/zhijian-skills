---
name: skill-open-sourcer
description: Audit, package, add, verify, and publish local Agent Skills through the canonical zjp1997720/zhijian-skills portfolio. Use when the user gives a SKILL.md or Skill directory and asks to open-source, publish, release, share, validate, manage versions, make installable with npx skills, prepare documentation, or generate launch copy. Every public Skill must live in the canonical repository's nested skills directory; never create or update a standalone Skill repository.
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
3. Follow the canonical repository's Git synchronization rules. Run `git_sync_guard.py check --repo <zhijian-skills>` before changing or publishing from an existing checkout; a `needs-sync` marker is a hard stop. Then run:

```bash
SKILL_OPEN_SOURCER_DIR="<zhijian-skills>/skills/skill-open-sourcer"
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/check_release_env.py" \
  --repo-dir <zhijian-skills> --check-npx-skills
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/scan_skill_release.py" \
  /path/to/skill-or-SKILL.md
```

4. Inspect `SKILL.md` and directly referenced `agents/`, `references/`, `scripts/`, and `assets/`. Copy only the complete, sanitized install payload into `skills/<name>/`; preserve required license and third-party notices.
5. Write the eight-field release story from [README design](references/readme-design.md), choose `clean-doc` or `proof-led`, then create or update bilingual docs, Changelog, Registry record, Portfolio catalog, and project-native visuals. A proof-led Hero must use a composition derived from the Skill's real mechanism or output; changing only the title and motif inside a shared layout fails review. Never expose a root-level `SKILL.md` or add human README files inside the Skill payload.
6. Choose the version with [version-contract.md](references/version-contract.md). Use only the canonical Tag `<skill>/v<version>`.
7. Freeze a release plan with the narrowest selector. For a governed Skill, its `manifest.json` must declare `trust_report` and `output_quality_scorecard` as files inside the install payload; both files must exist and be tracked at `HEAD`. Planning fails before candidate refs are created when either baseline is undeclared, missing, untracked, or escapes the payload. Use `--skill <name>` for one Skill; reserve `--all` and optional `--exclude` for an intentional multi-Skill wave:

```bash
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/release_portfolio.py" plan \
  --repo <zhijian-skills> --source-checkout <original-checkout> \
  --skill <name> --dry-run \
  --plan-out /tmp/<name>-release-plan.json
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/release_portfolio.py" verify \
  --plan /tmp/<name>-release-plan.json
```

`--skill` and `--all` are mutually exclusive. Repeat `--skill` only when the user explicitly authorizes a small multi-Skill release. Do not combine `--skill` with `--exclude`.

The plan records the live `origin/main` SHA with `git ls-remote`. `verify` queries it again and fails when it changed. When `--repo` is a temporary clean clone, `--source-checkout` must identify the original checkout; planning marks that checkout `release-in-progress` and installs a pre-commit guard so it cannot create new commits from the stale base.

8. Validate the Skill, declared tests, full Portfolio, documentation, and repository contracts:

```bash
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/portfolio.py" \
  validate-skill <zhijian-skills>/skills/<name>
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/portfolio.py" \
  audit --repo <zhijian-skills> --strict
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/audit_release_readme.py" \
  --repository-root <zhijian-skills> \
  <zhijian-skills>/docs/skills/<name>/README.md \
  <zhijian-skills>/docs/skills/<name>/README.zh-CN.md --strict
python3 -m unittest discover -s <zhijian-skills>/tests -v
```

When README assets are generated by the Portfolio, regenerate them and run the asset tests before accepting the diff. Render every changed Hero at `900px` and `360px`; deterministic checks do not replace visual inspection.

9. Verify local `npx skills` discovery, then run one fail-fast isolated copy install from the canonical repository:

```bash
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/verify_isolated_install.py" \
  --repo <zhijian-skills> --skill <name>
```

The verifier isolates HOME, uses copy mode, and compares SHA-256 manifests byte-for-byte. It returns non-zero immediately when preflight, installation, materialization, missing/extra files, or content comparison fails; do not append a success-printing command that can mask its exit code. Listing success alone is insufficient. Use top-level help only: `npx --no-install skills --help`. Never run `npx skills add <source> --help`; `skills` CLI 1.5.x may perform a real installation because `<source>` is already a valid add request.
10. Commit only on a short-lived branch created from the recorded remote SHA. Immediately before the remote wave, run `verify` again, push the branch, and merge it through a PR into protected `main`; Agents never push directly to `main`. After merge, read the live remote SHA and record the verified transition:

```bash
python3 "$SKILL_OPEN_SOURCER_DIR/scripts/release_portfolio.py" record-step \
  --plan /tmp/<name>-release-plan.json --skill <name> \
  --step canonical-pushed --remote-sha <merged-origin-main-sha>
```

This step verifies that remote `main` contains the planned source and upgrades a temporary-clone source marker to `needs-sync`. Never call `gh repo create` or publish to `<owner>/<skill-name>`.
11. Verify the remote Portfolio listing and isolated install, then create the canonical Tag and launch copy. Clear a source checkout marker only after that checkout is clean and its local `HEAD` exactly equals the verified remote SHA.

## Output contract

Return:

- canonical Skill URL under `zjp1997720/zhijian-skills`
- the canonical commit, version, and `<skill>/v<version>` Tag
- install command using `npx skills add zjp1997720/zhijian-skills`
- Skill validation, Portfolio audit, remote listing, and isolated-install results
- README presentation tier and deliberate visual assets
- the eight-field release story, unique composition choice, and rendered desktop/mobile inspection result
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
- a `release-in-progress` or `needs-sync` checkout marker
- remote `main` changing after the release plan is frozen
- a governed `trust_report` or `output_quality_scorecard` that is undeclared, missing, outside the payload, or not tracked at `HEAD`

Literal credential assignments are blockers. Runtime transformations such as URL-encoding a token variable are not literal secrets and must not be blocked by the generic assignment detector; high-confidence provider key patterns remain blocking.

Never force-push, rewrite published Tags, create a standalone repository, or treat missing evidence as passed.

## Packaging rules

- Every Skill lives at `skills/<skill-name>/`, including a single-file Skill.
- Keep `SKILL.md` lean; put detailed agent guidance in `references/` only when needed.
- Preserve `agents/openai.yaml`; create it when absent with a `$<skill-name>` default prompt.
- Include deterministic scripts and licensed agent-facing assets only.
- Put human docs in `docs/skills/<skill-name>/` and README visuals in its `assets/readme/` directory.
- Update `registry/skills.json`, root README catalogs, and deterministic asset generators together. Every generated proof-led Hero needs a unique, stable `data-composition` value and a matching project-specific generator branch; Portfolio tests must reject duplicate composition IDs.

## Publication verification

```bash
npx --no-install skills --help
npx --no-install skills add zjp1997720/zhijian-skills --list
python3 scripts/verify_isolated_install.py \
  --repo <zhijian-skills> --skill <skill-name> \
  --install-source zjp1997720/zhijian-skills
```

The verifier uses the Portfolio's pinned `skills` CLI and returns non-zero for every failed phase. For a cold check where the pinned package is not installed, install dependencies in the canonical checkout before running it; never improvise a shell chain whose final command can hide an earlier failure.
Never use `npx skills add <source> --help` as a help probe. It may perform a real installation and create `.agents/` plus `skills-lock.json` in the current directory.

## Launch copy

After all gates pass, explain the repeated problem, what the Skill automates, the canonical install command, one concrete example request, and any relevant safety boundary. Never link a standalone Skill repository.
