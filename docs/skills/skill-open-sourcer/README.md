# Skill Open Sourcer

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Skill Open Sourcer verifies and publishes complete Skills through one canonical Portfolio">
</p>

<p align="center"><strong>Turn a local Agent Skill into a complete, verified release inside Zhijian Skills.</strong></p>

<p align="center"><a href="./README.zh-CN.md">简体中文</a> · <a href="https://github.com/zjp1997720/zhijian-skills/tree/main/skills/skill-open-sourcer">Canonical source</a></p>

Use it when a local Skill is ready to become public and installable. Every release is imported into `zjp1997720/zhijian-skills`; the workflow never creates a standalone Skill repository.

## Install

```bash
npx skills add zjp1997720/zhijian-skills \
  -g -a codex --skill skill-open-sourcer --copy -y
```

Then invoke `$skill-open-sourcer` with a local `SKILL.md` or Skill directory.

## Requirements

- Python 3, Git, Node.js, and `npx`
- A verified local checkout of `zjp1997720/zhijian-skills`
- Authenticated push access to that canonical repository when publication is requested

## What It Does

- Scans the incoming Skill for literal secrets, personal paths, caches, private data, unsafe links, and unclear assets; runtime credential reads are allowed and every detected value is redacted from scanner output.
- Imports the complete payload into `skills/<name>/` and creates bilingual docs, Changelog, Registry metadata, and catalog entries.
- Locks an eight-field release story, chooses a clean-doc or proof-led presentation tier, and rejects generic Hero templates shared across unrelated Skills.
- Validates the Skill, full Portfolio, declared tests, README structure and assets, local discovery, and isolated copy installation.
- Runs isolated installation through one fail-fast verifier that checks install exit status, materialization, and byte-for-byte SHA-256 manifests without allowing a later shell command to mask failure.
- Audits shared Portfolio README links against an explicit canonical repository boundary.
- Uses top-level CLI help and list-only discovery so a help probe cannot trigger an unintended installation.
- Plans one Skill with `--skill <name>` by default, so unrelated pending releases cannot enter the candidate set; `--all` remains available for an intentional Portfolio wave.
- Records and re-checks the live remote SHA, blocks stale source checkouts with a `needs-sync` pre-commit guard, and publishes through a short-lived branch plus PR.
- Merges only into the canonical Portfolio and creates only `<skill>/v<version>` Tags.
- Produces the canonical install command and launch copy.

## How It Works

The Skill treats open-sourcing as a governed import into one Portfolio. A direct `SKILL.md` input identifies what to import; it never selects a new-repository mode. README design begins with audience, repeated problem, value, proof, first action, safety boundary, native material, and presentation tier. Proof-led Heroes then receive a unique composition derived from the Skill's real mechanism or output. `verify_isolated_install.py` installs one Skill in copy mode inside temporary HOME/workspace roots and compares the installed payload against the canonical source. The release plan binds the source to a live remote SHA; temporary integration clones freeze their original checkout until it is synchronized. Governed packages must commit the `trust_report` and `output_quality_scorecard` declared by their manifest; ignored local reports cannot satisfy release evidence. Publishing fails closed when the canonical remote, source ownership, security scan, package completeness, governance baselines, README evidence, installation proof, or remote-history continuity is missing.

## Example Requests

```text
Use $skill-open-sourcer to add this local Skill to Zhijian Skills and publish it.
Use $skill-open-sourcer to audit this SKILL.md before importing it into the Portfolio.
Use $skill-open-sourcer to release the next canonical version of this Skill.
```

## Canonical Layout

```text
skills/<name>/          complete agent-facing payload
docs/skills/<name>/     bilingual human documentation
docs/changelogs/        independent release notes
registry/skills.json    version, validation, capabilities, and Harnesses
```

## Safety

The workflow never creates an independent GitHub repository, writes mirror metadata, force-pushes, or rewrites published Tags. README links may resolve inside the explicitly selected canonical repository and nowhere beyond it. Missing evidence remains explicit.

## License

[MIT](../../../LICENSE)
