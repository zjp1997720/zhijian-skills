---
name: codex-theme-studio
description: Design, install, switch, verify, repair, pause, or restore reversible themes for the official Codex Desktop app on macOS. Use when a user asks to change Codex fonts, colors, artwork, homepage banners, radii, density, selection states, or advanced layout; reuse a bundled preset; diagnose a failed skin injection; or return to the official appearance. Do not use for Windows, Linux, ChatGPT web, ZCode, Doubao Work, third-party Codex builds, or direct app.asar modification.
---

# Codex Theme Studio

Turn a visual direction, brand system, or supplied image into a reversible Codex Desktop theme through loopback-only Chrome DevTools injection.

## Modes

- **Design**: prepare a portable theme directory and validate it without installing or restarting Codex.
- **Apply**: run the safety preflight, install the runtime, and import or create a theme. Obtain explicit authorization before restarting a running Codex app.
- **Verify or repair**: reproduce the affected route, run deterministic tests, Doctor, and live Verify, then repair only selector or layout failures supported by evidence.
- **Pause or restore**: Pause removes the active styling. Restore also stops the managed CDP session and returns Codex to the official appearance.

## Workflow

1. Read [capability-boundary.md](references/capability-boundary.md). Confirm the official macOS host, authorization boundary, and excluded targets.
2. For design work, read [design-workflow.md](references/design-workflow.md), [theme-schema.md](references/theme-schema.md), and [preset-policy.md](references/preset-policy.md). For layout changes, also read [compatibility-policy.md](references/compatibility-policy.md).
3. Run `./tests/run-tests.sh`. Repair failures before proceeding.
4. For design-only work, build outside the installed Skill and validate the prepared directory with `./scripts/injector.mjs --check-payload --theme-dir <theme-directory>`.
5. For installation, read [safety-and-rollback.md](references/safety-and-rollback.md), then run `./scripts/install-dream-skin-macos.sh --no-launch`.
6. For a bundled preset, run `./scripts/list-presets.mjs`, then import it without applying: `./scripts/import-preset-macos.sh --id <preset-id> --no-apply`.
7. For user-supplied artwork, use `./scripts/customize-theme-macos.sh`; never overwrite bundled Skill assets. If new raster artwork is required, invoke `$imagegen` when available and follow [imagegen-assets.md](references/imagegen-assets.md).
8. Restart only with explicit authorization by running the installed `scripts/start-dream-skin-macos.sh --prompt-restart`. Persistence through the resident manager requires separate explicit authorization.
9. Follow [verification-contract.md](references/verification-contract.md). Verify the home route, task route, New Task transition, normal window, and full screen. Inspect screenshots for overlap, overflow, weak contrast, crop errors, and missing native controls.
10. If verification fails, use [troubleshooting.md](references/troubleshooting.md), repair one defect class at a time, and restore before reporting a failed outcome.

## Safe theme layer

Use this layer by default. It exposes validated colors, UI and code fonts, body/emphasis/code weights, local artwork, radii, density, and selection states. Prefer stable semantic markers and the native DOM. Decorative layers must use `pointer-events: none`.

Bundled presets:

- `graphite-paper`: neutral, unbranded default with system fonts and abstract workflow artwork.
- `zhijian-ai`: optional ZhiJian AI warm-paper preset with its separately licensed original control-lever banner.

## Advanced layout layer

Enter this layer only when the user explicitly asks to change component width, placement, arrangement, or responsive behavior. Every layout change must preserve native interaction, focus, scrolling, keyboard paths, and hit targets; use live semantic markers; cover every affected route; pass normal-window and full-screen checks; and add a deterministic regression assertion or verification probe.

## output contract

Report the mode, Skill version, Codex version, theme or preset ID, files and surfaces changed, deterministic test result, Doctor result, whether live Verify returned `pass: true`, screenshot paths, installation directory, restore entrypoint, official signature status, resident-manager status, and every unverified route or viewport.

## Input files

Treat supplied images, fonts, theme JSON, and screenshots as file-backed fixtures. Read only files the user explicitly provides. Do not search personal directories, upload artwork, or write local absolute paths into a distributable theme.

## rollback boundary

Rollback may touch only this project's runtime, state, launchers, and managed loopback CDP session. Never delete tasks, conversations, projects, or unrelated configuration. Never modify the official `.app`, `app.asar`, code signature, macOS security settings, or another application.

## trust report

Read [trust-baseline.md](security/trust-baseline.md) before release, upgrade, or third-party delivery. Missing live, viewport, host, or future-version evidence must remain explicit `missing evidence`; do not claim universal or cross-version compatibility.

## Do not use

Do not use this Skill for Windows, Linux, ChatGPT web, unofficial Codex packages, ZCode, Doubao Work, other Electron applications, models, accounts, permissions, conversation content, arbitrary user JavaScript, screenshot overlays that replace real UI, unsigned app mutation, disabled signature checks, unauthorized persistence, or unauthorized restart.
