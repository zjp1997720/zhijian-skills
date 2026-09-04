#!/bin/bash

set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd -P)/common-macos.sh"

PORT=9341
CREATE_LAUNCHERS="true"
LAUNCH_AFTER_INSTALL="true"
IN_PLACE="false"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --port) PORT="${2:-}"; shift 2 ;;
    --no-launchers) CREATE_LAUNCHERS="false"; shift ;;
    --no-launch) LAUNCH_AFTER_INSTALL="false"; shift ;;
    --in-place) IN_PLACE="true"; shift ;;
    *) fail "Unknown installer argument: $1" ;;
  esac
done
validate_port "$PORT"

deploy_project() {
  local temporary="$INSTALL_ROOT.installing.$$"
  local previous="$INSTALL_ROOT.previous.$$"
  /bin/rm -rf "$temporary"
  /bin/mkdir -p "$temporary"
  /usr/bin/rsync -a --checksum \
    --exclude '.git/' \
    --exclude '.DS_Store' \
    --exclude '._*' \
    --exclude 'client-delivery/' \
    --exclude 'assets/portal-hero.png' \
    --exclude 'assets/portal-hero-v2.png' \
    --exclude 'assets/zhijian-ai-mark.png' \
    --exclude 'assets/zhijian-ai-wordmark.png' \
    --exclude 'release/' \
    --exclude 'runtime/' \
    --exclude 'references/screenshots/' \
    "$PROJECT_ROOT/" "$temporary/"
  /bin/chmod 700 "$temporary"/*.command "$temporary"/scripts/*.sh 2>/dev/null || true
  if [ -e "$INSTALL_ROOT" ]; then /bin/mv "$INSTALL_ROOT" "$previous"; fi
  if ! /bin/mv "$temporary" "$INSTALL_ROOT"; then
    [ -e "$previous" ] && /bin/mv "$previous" "$INSTALL_ROOT"
    fail "Could not install the project at $INSTALL_ROOT"
  fi
  /bin/rm -rf "$previous"
}

if [ "$IN_PLACE" = "false" ] && [ "$PROJECT_ROOT" != "$INSTALL_ROOT" ]; then
  discover_codex_app
  require_macos_runtime
  ensure_state_root
  /bin/mkdir -p "$(dirname "$INSTALL_ROOT")"
  if [ -d "$INSTALL_ROOT" ]; then
    [ -d "$THEME_DIR" ] || fail "Existing Dream Skin install has no active theme directory to snapshot: $THEME_DIR"
    [ -f "$VERSION_BASELINE_PATH" ] || fail "V2 baseline is missing: $VERSION_BASELINE_PATH"
    [ -f "$INSTALL_ROOT/VERSION" ] || fail "Existing Dream Skin install has no VERSION file: $INSTALL_ROOT/VERSION"
    INSTALLED_VERSION="$(/usr/bin/tr -d '[:space:]' < "$INSTALL_ROOT/VERSION")"
    BASELINE_VERSION="$("$NODE" -e 'const value=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));process.stdout.write(value.version||"")' "$VERSION_BASELINE_PATH")"
    [ -n "$BASELINE_VERSION" ] || fail "V2 baseline has no version: $VERSION_BASELINE_PATH"
    if ! "$NODE" "$PROJECT_ROOT/scripts/version-backup-state.mjs" verify \
      --state-root "$STATE_ROOT" --label "$VERSION_BACKUP_LABEL" >/dev/null 2>&1; then
      if [ -e "$STATE_ROOT/version-backups/$VERSION_BACKUP_LABEL" ]; then
        fail "Existing V2 version backup failed integrity verification: $STATE_ROOT/version-backups/$VERSION_BACKUP_LABEL"
      fi
      if [ "$INSTALLED_VERSION" = "$BASELINE_VERSION" ]; then
        "$NODE" "$PROJECT_ROOT/scripts/version-backup-state.mjs" snapshot \
          --state-root "$STATE_ROOT" \
          --install-root "$INSTALL_ROOT" \
          --theme-dir "$THEME_DIR" \
          --baseline "$VERSION_BASELINE_PATH" >/dev/null
      fi
    fi
  fi
  deploy_project
  install_args=(--in-place --port "$PORT")
  [ "$CREATE_LAUNCHERS" = "true" ] || install_args+=(--no-launchers)
  [ "$LAUNCH_AFTER_INSTALL" = "true" ] || install_args+=(--no-launch)
  exec "$INSTALL_ROOT/scripts/install-dream-skin-macos.sh" "${install_args[@]}"
fi

discover_codex_app
require_macos_runtime
ensure_state_root
[ -f "$CONFIG_PATH" ] || fail "Codex config not found: $CONFIG_PATH. Launch Codex once, close it, and rerun the installer."

BUNDLED_THEME_ID="$("$NODE" -e 'const t=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));process.stdout.write(t.id)' "$PROJECT_ROOT/assets/theme.json")"
BUNDLED_THEME_IMAGE="$("$NODE" -e 'const t=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));process.stdout.write(t.image)' "$PROJECT_ROOT/assets/theme.json")"
ACTIVE_THEME_ID=""
if [ -f "$THEME_DIR/theme.json" ]; then
  ACTIVE_THEME_ID="$("$NODE" -e 'try{const t=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));process.stdout.write(t.id||"")}catch{}' "$THEME_DIR/theme.json")"
fi

# Refresh the bundled theme across installer upgrades, while preserving a different custom theme.
if [ ! -f "$THEME_DIR/theme.json" ] || [ "$ACTIVE_THEME_ID" = "$BUNDLED_THEME_ID" ]; then
  /bin/mkdir -p "$THEME_DIR"
  /bin/chmod 700 "$THEME_DIR"
  /bin/cp "$PROJECT_ROOT/assets/theme.json" "$PROJECT_ROOT/assets/$BUNDLED_THEME_IMAGE" "$THEME_DIR/"
  /bin/chmod 600 "$THEME_DIR/theme.json" "$THEME_DIR/$BUNDLED_THEME_IMAGE"
fi
"$NODE" "$INJECTOR" --check-payload --theme-dir "$THEME_DIR" >/dev/null
"$NODE" "$SCRIPT_DIR/base-theme-state.mjs" snapshot \
  --state-root "$STATE_ROOT" \
  --theme-export "$BASE_THEME_EXPORT" \
  --config "$CONFIG_PATH" \
  --global-state "$GLOBAL_STATE_PATH" >/dev/null
"$NODE" "$SCRIPT_DIR/theme-config.mjs" install "$CONFIG_PATH" "$THEME_BACKUP_PATH"

shell_quote() {
  "$NODE" -e 'process.stdout.write(JSON.stringify(process.argv[1]))' "$1"
}

write_launcher() {
  local target="$1"
  local command="$2"
  if [ -e "$target" ] && ! /usr/bin/grep -q '^# CodexDreamSkinStudio launcher$' "$target" 2>/dev/null; then
    fail "Refusing to overwrite an unrelated Desktop file: $target"
  fi
  /usr/bin/printf '%s\n' \
    '#!/bin/bash' \
    '# CodexDreamSkinStudio launcher' \
    'set -e' \
    "$command" > "$target"
  /bin/chmod 700 "$target"
}

if [ "$CREATE_LAUNCHERS" = "true" ]; then
  /bin/mkdir -p "$HOME/Desktop"
  start_script="$(shell_quote "$SCRIPT_DIR/start-dream-skin-macos.sh")"
  customize_script="$(shell_quote "$SCRIPT_DIR/customize-theme-macos.sh")"
  pause_script="$(shell_quote "$SCRIPT_DIR/pause-dream-skin-macos.sh")"
  verify_script="$(shell_quote "$SCRIPT_DIR/verify-dream-skin-macos.sh")"
  restore_script="$(shell_quote "$SCRIPT_DIR/restore-dream-skin-macos.sh")"
  screenshot="$(shell_quote "$HOME/Desktop/Codex Dream Skin Verification.png")"
  write_launcher "$HOME/Desktop/Codex Dream Skin.command" "exec $start_script --port $PORT --prompt-restart"
  write_launcher "$HOME/Desktop/Codex Dream Skin - Customize.command" "exec $customize_script"
  write_launcher "$HOME/Desktop/Codex Dream Skin - Pause.command" "exec $pause_script"
  write_launcher "$HOME/Desktop/Codex Dream Skin - Verify.command" "$verify_script --screenshot $screenshot && /usr/bin/open $screenshot"
  write_launcher "$HOME/Desktop/Codex Dream Skin - Restore.command" "exec $restore_script --restore-base-theme --restart-codex"
fi

printf 'Codex Dream Skin Studio %s installed at %s for Codex %s using its signed Node.js %s.\n' \
  "$SKIN_VERSION" "$PROJECT_ROOT" "$CODEX_VERSION" "$NODE_VERSION"
printf 'Use the Desktop launchers to customize, start, pause, verify, or restore the official appearance.\n'

if [ "$LAUNCH_AFTER_INSTALL" = "true" ]; then
  "$SCRIPT_DIR/start-dream-skin-macos.sh" --port "$PORT" --prompt-restart
fi
