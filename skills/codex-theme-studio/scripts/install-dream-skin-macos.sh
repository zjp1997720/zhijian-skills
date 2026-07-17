#!/bin/bash

set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd -P)/common-macos.sh"

PORT=9341
CREATE_LAUNCHERS="false"
LAUNCH_AFTER_INSTALL="false"
THEME_EXPORT=""
SOURCE_THEME_DIR=""
IN_PLACE="false"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --port) PORT="${2:-}"; shift 2 ;;
    --launchers) CREATE_LAUNCHERS="true"; shift ;;
    --no-launchers) CREATE_LAUNCHERS="false"; shift ;;
    --launch) LAUNCH_AFTER_INSTALL="true"; shift ;;
    --no-launch) LAUNCH_AFTER_INSTALL="false"; shift ;;
    --theme-export) THEME_EXPORT="${2:-}"; shift 2 ;;
    --theme-dir) SOURCE_THEME_DIR="${2:-}"; shift 2 ;;
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
    [ -d "$THEME_DIR" ] || fail "Existing Codex Theme Studio install has no active theme directory to snapshot: $THEME_DIR"
    PREVIOUS_VERSION="$(/bin/cat "$INSTALL_ROOT/VERSION" 2>/dev/null || printf 'unknown')"
    VERSION_BACKUP_LABEL="$("$NODE" -e '
      const value = String(process.argv[1] || "unknown").toLowerCase().replace(/[^a-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 42) || "unknown";
      process.stdout.write(`pre-upgrade-${value}`);
    ' "$PREVIOUS_VERSION")"
    "$NODE" "$PROJECT_ROOT/scripts/version-backup-state.mjs" snapshot \
      --state-root "$STATE_ROOT" \
      --install-root "$INSTALL_ROOT" \
      --theme-dir "$THEME_DIR" \
      --label "$VERSION_BACKUP_LABEL" >/dev/null
    /usr/bin/printf '%s\n' "$VERSION_BACKUP_LABEL" > "$VERSION_BACKUP_LABEL_PATH"
    /bin/chmod 600 "$VERSION_BACKUP_LABEL_PATH"
  fi
  deploy_project
  install_args=(--in-place --port "$PORT")
  [ "$CREATE_LAUNCHERS" = "false" ] || install_args+=(--launchers)
  [ "$LAUNCH_AFTER_INSTALL" = "false" ] || install_args+=(--launch)
  [ -z "$THEME_EXPORT" ] || install_args+=(--theme-export "$THEME_EXPORT")
  [ -z "$SOURCE_THEME_DIR" ] || install_args+=(--theme-dir "$SOURCE_THEME_DIR")
  exec "$INSTALL_ROOT/scripts/install-dream-skin-macos.sh" "${install_args[@]}"
fi

discover_codex_app
require_macos_runtime
ensure_state_root
[ -f "$CONFIG_PATH" ] || fail "Codex config not found: $CONFIG_PATH. Launch Codex once, close it, and rerun the installer."

install_theme_from_source() {
  local source="$1"
  local resolved image brand temporary previous
  resolved="$("$NODE" -e 'process.stdout.write(require("node:path").resolve(process.argv[1]))' "$source")"
  [ -d "$resolved" ] || fail "Theme source directory does not exist: $resolved"
  "$NODE" "$INJECTOR" --check-payload --theme-dir "$resolved" >/dev/null
  image="$("$NODE" -e 'const t=JSON.parse(require("fs").readFileSync(require("path").join(process.argv[1],"theme.json"),"utf8"));process.stdout.write(t.image)' "$resolved")"
  brand="$("$NODE" -e 'const t=JSON.parse(require("fs").readFileSync(require("path").join(process.argv[1],"theme.json"),"utf8"));process.stdout.write(t.brandImage||"")' "$resolved")"
  temporary="$STATE_ROOT/.theme-installing.$$"
  previous="$STATE_ROOT/.theme-previous.$$"
  /bin/rm -rf "$temporary" "$previous"
  /bin/mkdir -p "$temporary"
  /bin/chmod 700 "$temporary"
  /bin/cp "$resolved/theme.json" "$resolved/$image" "$temporary/"
  [ -z "$brand" ] || /bin/cp "$resolved/$brand" "$temporary/"
  /bin/chmod 600 "$temporary/"*
  if [ -e "$THEME_DIR" ]; then /bin/mv "$THEME_DIR" "$previous"; fi
  if ! /bin/mv "$temporary" "$THEME_DIR"; then
    [ -e "$previous" ] && /bin/mv "$previous" "$THEME_DIR"
    fail "Could not install the prepared theme."
  fi
  /bin/rm -rf "$previous"
}

if [ -n "$SOURCE_THEME_DIR" ]; then
  install_theme_from_source "$SOURCE_THEME_DIR"
fi

BUNDLED_THEME_ID="$("$NODE" -e 'const t=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));process.stdout.write(t.id)' "$PROJECT_ROOT/assets/theme.json")"
BUNDLED_THEME_IMAGE="$("$NODE" -e 'const t=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));process.stdout.write(t.image)' "$PROJECT_ROOT/assets/theme.json")"
BUNDLED_BRAND_IMAGE="$("$NODE" -e 'const t=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));process.stdout.write(t.brandImage||"")' "$PROJECT_ROOT/assets/theme.json")"
ACTIVE_THEME_ID=""
if [ -f "$THEME_DIR/theme.json" ]; then
  ACTIVE_THEME_ID="$("$NODE" -e 'try{const t=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));process.stdout.write(t.id||"")}catch{}' "$THEME_DIR/theme.json")"
fi

# Refresh the bundled theme across installer upgrades, while preserving a different custom theme.
if [ -z "$SOURCE_THEME_DIR" ] && { [ ! -f "$THEME_DIR/theme.json" ] || [ "$ACTIVE_THEME_ID" = "$BUNDLED_THEME_ID" ]; }; then
  /bin/mkdir -p "$THEME_DIR"
  /bin/chmod 700 "$THEME_DIR"
  /bin/cp "$PROJECT_ROOT/assets/theme.json" "$PROJECT_ROOT/assets/$BUNDLED_THEME_IMAGE" "$THEME_DIR/"
  if [ -n "$BUNDLED_BRAND_IMAGE" ]; then
    /bin/cp "$PROJECT_ROOT/assets/$BUNDLED_BRAND_IMAGE" "$THEME_DIR/"
    /bin/chmod 600 "$THEME_DIR/$BUNDLED_BRAND_IMAGE"
  fi
  /bin/chmod 600 "$THEME_DIR/theme.json" "$THEME_DIR/$BUNDLED_THEME_IMAGE"
fi
"$NODE" "$INJECTOR" --check-payload --theme-dir "$THEME_DIR" >/dev/null
base_snapshot_args=(snapshot --state-root "$STATE_ROOT" --config "$CONFIG_PATH" --global-state "$GLOBAL_STATE_PATH")
[ -z "$THEME_EXPORT" ] || base_snapshot_args+=(--theme-export "$THEME_EXPORT")
"$NODE" "$SCRIPT_DIR/base-theme-state.mjs" "${base_snapshot_args[@]}" >/dev/null
"$NODE" "$SCRIPT_DIR/theme-config.mjs" install "$CONFIG_PATH" "$THEME_BACKUP_PATH"

shell_quote() {
  "$NODE" -e 'process.stdout.write(JSON.stringify(process.argv[1]))' "$1"
}

write_launcher() {
  local target="$1"
  local command="$2"
  if [ -e "$target" ] && ! /usr/bin/grep -q '^# CodexThemeStudio launcher$' "$target" 2>/dev/null; then
    fail "Refusing to overwrite an unrelated Desktop file: $target"
  fi
  /usr/bin/printf '%s\n' \
    '#!/bin/bash' \
    '# CodexThemeStudio launcher' \
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
  screenshot="$(shell_quote "$HOME/Desktop/Codex Theme Studio Verification.png")"
  write_launcher "$HOME/Desktop/Codex Theme Studio.command" "exec $start_script --port $PORT --prompt-restart"
  write_launcher "$HOME/Desktop/Codex Theme Studio - Customize.command" "exec $customize_script"
  write_launcher "$HOME/Desktop/Codex Theme Studio - Pause.command" "exec $pause_script"
  write_launcher "$HOME/Desktop/Codex Theme Studio - Verify.command" "$verify_script --screenshot $screenshot && /usr/bin/open $screenshot"
  write_launcher "$HOME/Desktop/Codex Theme Studio - Restore.command" "exec $restore_script --restore-base-theme --restart-codex"
fi

printf 'Codex Theme Studio %s installed at %s for Codex %s using its signed Node.js %s.\n' \
  "$SKIN_VERSION" "$PROJECT_ROOT" "$CODEX_VERSION" "$NODE_VERSION"
if [ "$CREATE_LAUNCHERS" = "true" ]; then
  printf 'Desktop launchers were created for customize, start, pause, verify, and restore.\n'
else
  printf 'No Desktop launchers were created. Use the scripts in %s/scripts.\n' "$PROJECT_ROOT"
fi

if [ "$LAUNCH_AFTER_INSTALL" = "true" ]; then
  "$SCRIPT_DIR/start-dream-skin-macos.sh" --port "$PORT" --prompt-restart
fi
