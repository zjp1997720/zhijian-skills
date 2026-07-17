# Operator runbook

Resolve the installed or source Skill directory as `<skill-dir>`. Prepare themes outside that directory so upgrades cannot overwrite user work.

## Build and dry-check

```bash
node <skill-dir>/scripts/write-theme.mjs custom \
  --output-dir <theme-dir> \
  --image banner.png \
  --name "<theme name>" \
  --brand-label "<short brand label>" \
  --art-placement hero \
  --background '#F5F3EE' \
  --panel '#FAF9F6' \
  --panel-alt '#EEECE6' \
  --sidebar '#F1F0EC' \
  --selected '#E8E6DC' \
  --border '#E4E1DA' \
  --paper-blue '#E7EDF2' \
  --accent '#DA7756' \
  --accent-alt '#CC7D5E' \
  --secondary '#1B365D' \
  --highlight '#1B365D' \
  --text '#1D1B16' \
  --muted '#69675F'

node <skill-dir>/scripts/injector.mjs --check-payload --theme-dir <theme-dir>
bash <skill-dir>/tests/run-tests.sh
```

Use `--art-placement all` only after designing a low-detail center reading zone. Add `--brand-image <filename>` only after placing the asset inside `<theme-dir>`. Use `--hide-brand` when no top mark should appear.

## Install without launching

If the user supplied a native theme export, store it in a UTF-8 file beginning with `codex-theme-v1:`.

```bash
bash <skill-dir>/scripts/install-dream-skin-macos.sh \
  --theme-dir <theme-dir> \
  --theme-export <optional-export-file> \
  --no-launch --no-launchers
```

The runtime is installed at `~/.codex/codex-theme-studio`; recovery state lives under `~/Library/Application Support/CodexThemeStudio`.

## Apply

When Codex is closed:

```bash
bash ~/.codex/codex-theme-studio/scripts/start-dream-skin-macos.sh --port 9341
```

When Codex is running without the managed endpoint, obtain explicit restart authorization:

```bash
bash ~/.codex/codex-theme-studio/scripts/start-dream-skin-macos.sh \
  --port 9341 --restart-existing
```

## Verify

Run both routes and sample the transient New Task state:

```bash
bash ~/.codex/codex-theme-studio/scripts/verify-dream-skin-macos.sh \
  --viewport 1440x900 --screenshot <evidence-dir>/task.png

bash ~/.codex/codex-theme-studio/scripts/verify-dream-skin-macos.sh \
  --viewport 1440x900 --sample-new-task <evidence-dir>/new-task \
  --screenshot <evidence-dir>/home.png
```

Inspect the screenshots rather than treating a DOM pass as visual approval.

## Recover

```bash
# Remove injected styles while leaving the app running when possible
bash ~/.codex/codex-theme-studio/scripts/pause-dream-skin-macos.sh

# Restore normal launch behavior and the base native appearance snapshot
bash ~/.codex/codex-theme-studio/scripts/restore-dream-skin-macos.sh \
  --restore-base-theme --restart-codex

# Restore the latest immutable pre-upgrade runtime and active theme
bash ~/.codex/codex-theme-studio/scripts/restore-version-macos.sh
```
