---
name: codex-theme-studio
description: Design, generate visual assets for, safely install, verify, iterate, and restore custom themes for the official Codex Desktop app on macOS. Use when a user asks to redesign Codex UI, create/apply/inject/replace a Codex skin or theme, adapt Codex to a brand system, generate a Codex banner or page background, repair defects in an injected theme, or roll back a custom theme. Do not use for general Codex health/config debugging, ordinary website theming, Windows/Linux, or direct app.asar modification.
---

# Codex Theme Studio

Turn a brand system and optional artwork into a reversible Codex Desktop theme through loopback-only Chrome DevTools injection.

## Boundaries

- Support the official macOS app (`com.openai.codex`) only.
- Never modify, unpack, replace, re-sign, or patch `app.asar` or the app bundle.
- Keep CDP on `127.0.0.1` and reject foreign targets.
- Preserve any supplied `codex-theme-v1:` export and native appearance keys.
- Treat theme JSON and images as untrusted input; reject unsafe paths, symlinks, formats, and sizes.
- Require explicit restart authorization before stopping a running Codex app.

## Workflow

1. Collect the brand source of truth, current theme export, annotated screenshots, viewport, optional logo/IP, and image placement (`hero` or `all`). Read [design-workflow.md](references/design-workflow.md). Preserve native navigation, tabs, suggestion cards, composer controls, focus states, and hit targets.
2. If a new raster Banner, texture, illustration, or page background is required, invoke `$imagegen` when available and follow [imagegen-assets.md](references/imagegen-assets.md). Keep logos and vector systems native. Copy every accepted project-bound image from `$CODEX_HOME/generated_images` into the prepared theme directory. If ImageGen is unavailable, use a supplied asset or the neutral fallback and record `missing evidence`.
3. Build outside the installed Skill. Use `artPlacement=hero` by default; use `all` only for an intentional, readable task-page background. Follow [operator-runbook.md](references/operator-runbook.md) to write `theme.json`, check the payload, and test before live changes.
4. Read [safety-and-rollback.md](references/safety-and-rollback.md). Install without launching. Apply only within the restart authorization boundary; never infer restart permission from design or installation permission.
5. Follow [verification-contract.md](references/verification-contract.md). Verify home and task routes, sample the New Task transition, and inspect screenshots. Fix one defect class at a time and rerun the affected contract. Use [troubleshooting.md](references/troubleshooting.md) for selector drift, missing native UI, route races, crop problems, and CDP failures.
6. Hand off the theme source, active name and placement, asset source or ImageGen prompt, backup location, screenshots, verification result, and exact pause and restore commands.

## Output contract

A complete result contains:

- one portable theme directory with local assets and valid `theme.json`
- dry-check and deterministic test results
- live route evidence when Codex access and restart authorization exist
- immutable backup and an explicit rollback boundary
- exact pause, restore, and previous-version recovery commands

Stop before mutation when app identity, loopback ownership, input safety, payload validation, or backup creation fails. A live verification failure leaves the prepared theme and backups intact for diagnosis.

## Governed evidence

Implementation lives in `scripts/`; fixtures live in `evals/`. Every release declares a `file-backed fixture`, `input_files`, a testable `output contract`, an explicit `rollback boundary`, and a current `trust report`. Ship [output-eval-baseline.md](references/output-eval-baseline.md) and [trust-baseline.md](security/trust-baseline.md); generate run evidence locally at ignored `reports/output_quality_scorecard.md`. Treat unobserved Codex, ImageGen, human, or viewport coverage as `missing evidence`.
