# skill-open-sourcer Changelog

## 2.4.2 — 2026-09-04

- Fail release planning before candidate creation when a governed Skill does not declare both `trust_report` and `output_quality_scorecard`.
- Require each declared governance baseline to stay inside the Skill payload, exist as a file, and be tracked at `HEAD`.
- Freeze verified baseline paths and SHA-256 digests into the immutable release plan so ignored local reports cannot satisfy public release evidence.

## 2.4.1 — 2026-07-27

- Exclude generated `dist`, `coverage`, and `reports` directories from isolated-install payload manifests, matching the canonical release manifest and preventing local test artifacts from causing false remote mismatches.

## 2.4.0 — 2026-07-27

- Bind every release plan to the live `origin/main` SHA and fail verification when the remote changes before publication.
- Require the original checkout path when a temporary clean clone publishes; mark that checkout `needs-sync` and install a pre-commit guard against stale-base commits.
- Replace direct `main` pushes with short-lived branches and PR merges, and verify that merged remote history contains the planned source before recording publication.
- Keep post-merge recording valid after GitHub switches the integration checkout to merged `main` by verifying frozen commit objects and candidate refs instead of requiring the old checkout HEAD.

## 2.3.0 — 2026-07-27

- Add `verify_isolated_install.py` as the single fail-fast isolated copy-install verifier for local and remote release sources.
- Compare canonical and installed payloads by SHA-256 manifest, rejecting install failures, non-materialization, missing files, extra files, and changed content with non-zero exit status.
- Replace ad-hoc shell comparison guidance with one deterministic command whose result cannot be masked by a later success-printing command.

## 2.2.1 — 2026-07-26

- Distinguish literal credential assignments from safe environment, config, and runtime reads.
- Detect Python string literals structurally across assignments, annotated assignments, mappings, and keyword arguments.
- Ignore generic fake credential literals in test fixtures while continuing to block provider-formatted tokens in every file.
- Redact every detected secret value from scanner output and add deterministic regression coverage for true positives, placeholders, and prior false positives.

## 2.2.0 — 2026-07-25

- Add `release_portfolio.py plan --skill <name>` for narrow, deterministic single-Skill release plans.
- Make `--skill` and `--all` mutually exclusive, reject `--skill` plus `--exclude`, and fail on unknown Skill names before creating candidate refs.
- Keep repeated `--skill` available for an explicitly authorized small release set while preserving `--all` for intentional Portfolio waves.

## 2.1.0 — 2026-07-24

- Add a required eight-field README release story and explicit `clean-doc` / `proof-led` tier decision.
- Require project-native composition IDs, deterministic generator updates, and Portfolio-level duplicate-composition tests for proof-led Heroes.
- Strengthen README audits with semantic alt text, accessible SVG root metadata, meaningful titles/descriptions, and strict Hero composition checks.
- Require rendered desktop and mobile inspection so deterministic validation cannot substitute for visual review.

## 2.0.1 — 2026-07-24

- Add an explicit `--repository-root` boundary for auditing Portfolio README files that link to shared repository assets such as `LICENSE`.
- Keep repository-boundary checks fail-closed when a README or local link resolves outside the selected root.
- Replace ambiguous add-subcommand help probes with top-level CLI help and document that `skills add <source> --help` may perform a real installation.
- Add deterministic regression tests for repository-root containment and CLI help safety guidance.

## 2.0.0 — 2026-07-17

- Make `zjp1997720/zhijian-skills` the only publishing repository for every imported Skill.
- Remove Single-Skill repository creation, mirror export, mirror metadata, mirror Tags, and redirect workflows.
- Require canonical Portfolio discovery, validation, isolated installation, commit, push, and per-Skill canonical Tags.
- Pin the `skills` CLI explicitly for cold isolated-HOME installation checks.

## 1.1.2 — 2026-07-17

- Export documentation SVG assets into standalone mirrors and record them in `SOURCE.json`.
- Add deterministic, brand-aligned README visuals and asset safety tests.
- Keep README links valid in both the canonical Portfolio and generated mirror.

## 1.1.1 — 2026-07-17

- Create one deterministic detached candidate commit per Skill and freeze mirror export digests in every release plan.
- Add namespace-safe candidate-ref cleanup after release completion.
- Journal local Harness link migrations before every mutation so interrupted runs remain recoverable.
- Ignore generated Python caches during local audits while continuing to exclude them from release packages.

## 1.1.0 — 2026-07-17

- Add Registry-driven Portfolio audit, immutable release planning, deterministic mirror export, and resumable release ledgers.
- Add reversible local Harness Symlink migration with external backups and explicit handling for local differences.
- Add complete package, security, capability, install, and mirror-drift validation.

## 1.0.0 — 2026-07-16

- Establish the first independently versioned governance baseline.
- Preserve current single-Skill safety, environment, README, and package checks.
