# Codex Theme Studio

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Two Codex presets pass through validated theme controls into a verified, reversible macOS Codex session">
</p>

<p align="center"><strong>Design, apply, verify, and restore a custom macOS Codex theme without modifying the signed app bundle.</strong></p>

<p align="center"><a href="./README.zh-CN.md">简体中文</a> · <a href="https://github.com/zjp1997720/zhijian-skills/tree/main/skills/codex-theme-studio">Canonical source</a></p>

Codex Theme Studio turns colors, fonts, local artwork, spacing, and an optional brand system into a portable theme with a tested rollback path. It includes a neutral public default and an optional ZhiJian AI preset, while keeping structural layout work behind an explicit advanced mode.

## Install

```bash
npx skills add zjp1997720/zhijian-skills \
  -g -a codex --skill codex-theme-studio --copy -y
```

Then ask:

```text
Use $codex-theme-studio to design a warm-paper theme for my official macOS Codex app. Prepare and validate it first; do not restart Codex yet.
```

## Requirements

- macOS with the official Codex Desktop app (`com.openai.codex`)
- A Codex or Agent Skills-compatible harness
- Bash and standard macOS command-line tools
- Optional built-in `$imagegen` capability when new raster artwork is needed

The runtime validates and uses the Node.js executable already signed inside Codex. Development tests expect Node.js 20 or newer.

## What It Does

- Validates colors, UI and code fonts, body/emphasis/code weights, local artwork, radii, density, and selection states.
- Ships `graphite-paper`, an unbranded default with abstract workflow artwork.
- Ships `zhijian-ai` as a separate optional preset with its own artwork license; it is never mixed into the default theme.
- Creates a custom theme from a user-supplied image without overwriting bundled assets.
- Applies CSS and renderer helpers through loopback-only Chrome DevTools Protocol instead of editing `app.asar`.
- Preserves native interactions, focus, scrolling, keyboard paths, and hit targets.
- Keeps immutable base-theme and pre-upgrade backups, with pause, restore, and previous-version recovery commands.
- Verifies home, task, transient New Task, normal-window, and full-screen behavior before claiming success.

## How It Works

1. Classify the request as design, apply, verify/repair, or pause/restore.
2. Start with the safe theme layer. Advanced width, placement, arrangement, or responsive changes require an explicit layout request and compatibility diagnosis.
3. Validate the theme directory and run deterministic tests before touching the installed runtime.
4. Install without launching. Restart a running Codex app only after separate, explicit authorization; persistence requires another explicit authorization.
5. Run Doctor and live Verify, inspect captured routes, and restore if the verification contract fails.

The bundled workbench accepts theme variables and local raster assets only. It does not execute arbitrary user JavaScript or replace the real interface with a screenshot.

## Example Requests

```text
Use $codex-theme-studio to list the bundled presets and prepare graphite-paper. Do not apply or restart anything.
```

```text
Use $codex-theme-studio to import the zhijian-ai preset, install it without launching, then wait for explicit restart authorization.
```

```text
Use $codex-theme-studio to diagnose why the conversation typography stopped applying after a Codex update. Verify stable semantic markers and restore if the live checks fail.
```

## Safety or Limitations

- Official macOS Codex only. Windows, Linux, ChatGPT web, ZCode, Doubao Work, unofficial builds, and other Electron apps are outside scope.
- The app bundle, `app.asar`, code signature, accounts, conversations, projects, and authentication data are never modified.
- CDP binds to `127.0.0.1`; the runtime verifies app identity, renderer identity, port ownership, image paths, file sizes, and backups before mutation.
- Design or installation permission does not authorize stopping Codex. The resident manager is opt-in and must not relaunch an app the user intentionally quit.
- Compatibility is evidence-based, not universal. A fresh second-Mac end-to-end run and future Codex versions remain explicit missing evidence until tested.

See the [capability boundary](https://github.com/zjp1997720/zhijian-skills/blob/main/skills/codex-theme-studio/references/capability-boundary.md), [verification contract](https://github.com/zjp1997720/zhijian-skills/blob/main/skills/codex-theme-studio/references/verification-contract.md), and [trust baseline](https://github.com/zjp1997720/zhijian-skills/blob/main/skills/codex-theme-studio/security/trust-baseline.md).

## Validation

```bash
bash skills/codex-theme-studio/tests/run-tests.sh
/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node \
  skills/codex-theme-studio/scripts/injector.mjs --check-payload
```

Live Doctor and screenshot checks remain separate because they require an installed, authorized Codex session.

## License

The software is MIT-licensed and retains attribution to the MIT-licensed [`Fei-Away/Codex-Dream-Skin`](https://github.com/Fei-Away/Codex-Dream-Skin) project whose injection architecture inspired this implementation.

The `zhijian-ai` artwork is bundled under the narrower permissions in `NOTICE.md`: it may be used as this Skill's Codex preset, but may not be extracted, resold, rebranded, or claimed as original work. Codex and OpenAI are trademarks of their respective owners. This project is unofficial and is not endorsed by OpenAI.
