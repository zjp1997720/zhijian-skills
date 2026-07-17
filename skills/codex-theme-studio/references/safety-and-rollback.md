# Safety and rollback

## What the engine changes

- Copies the Skill runtime to `~/.codex/codex-theme-studio`.
- Stores active theme, process state, logs, and backups under `~/Library/Application Support/CodexThemeStudio` with owner-only permissions.
- Launches the official signed Codex app with a loopback-only CDP port.
- Injects CSS, a renderer helper, and theme assets into verified `app://` Codex pages.

It does not modify the app bundle, `app.asar`, native theme settings, authentication, repositories, or user conversations.

## Backup layers

1. **Base appearance snapshot** — immutable first-install snapshot of `config.toml`, optional global state, and optional `codex-theme-v1:` export. Existing valid backup is reused and never silently replaced.
2. **Selective config backup** — records appearance keys but currently changes none. Restore therefore preserves later user edits.
3. **Pre-upgrade engine snapshot** — immutable hash manifest of the installed engine and active theme before replacement.
4. **Atomic deployment** — new engine and theme are staged, verified, then renamed into place. A failed exchange restores the previous directory.

## Authorization gates

- Design, image generation, file preparation, payload checks, and read-only doctor checks do not authorize a Codex restart.
- A running Codex without the managed CDP port requires explicit restart authorization before `--restart-existing` or a restore with `--restart-codex`.
- Desktop launchers are opt-in through `--launchers`.
- Uninstallation is explicit through `--uninstall`.

## Failure behavior

- Invalid app signature, signer mismatch, non-loopback CDP, foreign listener, invalid image, unsafe path, missing theme file, or failed payload check stops before injection.
- If strict verification fails after launch, stop the injector and retain backups and the prepared theme for diagnosis.
- If the live removal endpoint cannot be verified while Codex is running, stop restore before file exchange. Obtain restart authorization instead of killing an unknown process.

## Recovery commands

```bash
# Remove injected styles while leaving Codex running when possible
bash ~/.codex/codex-theme-studio/scripts/pause-dream-skin-macos.sh

# Remove live injection and restart official Codex normally
bash ~/.codex/codex-theme-studio/scripts/restore-dream-skin-macos.sh \
  --restore-base-theme --restart-codex

# Also remove optional Desktop launchers
bash ~/.codex/codex-theme-studio/scripts/restore-dream-skin-macos.sh \
  --restore-base-theme --restart-codex --uninstall

# Restore latest pre-upgrade engine and active theme
bash ~/.codex/codex-theme-studio/scripts/restore-version-macos.sh
```

Keep the prepared theme directory and the user's original exported theme in the handoff. They are independent recovery artifacts.
