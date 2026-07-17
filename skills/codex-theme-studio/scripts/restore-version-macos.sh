#!/bin/bash

set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd -P)/common-macos.sh"

PORT=9341
PORT_EXPLICIT="false"
VERSION_BACKUP_LABEL=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --port) PORT="${2:-}"; PORT_EXPLICIT="true"; shift 2 ;;
    --label) VERSION_BACKUP_LABEL="${2:-}"; shift 2 ;;
    *) fail "Unknown version restore argument: $1" ;;
  esac
done
validate_port "$PORT"

discover_codex_app
require_macos_runtime
ensure_state_root
[ -n "$VERSION_BACKUP_LABEL" ] || VERSION_BACKUP_LABEL="$(/bin/cat "$VERSION_BACKUP_LABEL_PATH" 2>/dev/null || true)"
[ -n "$VERSION_BACKUP_LABEL" ] || fail "No previous-version backup label is available. Pass --label <label>."
[ -d "$INSTALL_ROOT" ] || fail "Codex Theme Studio install is missing: $INSTALL_ROOT"
[ -d "$THEME_DIR" ] || fail "Active theme directory is missing: $THEME_DIR"
"$NODE" "$SCRIPT_DIR/version-backup-state.mjs" verify \
  --state-root "$STATE_ROOT" --label "$VERSION_BACKUP_LABEL" >/dev/null

if [ "$PORT_EXPLICIT" = "false" ] && [ -f "$STATE_PATH" ]; then
  saved_port="$(state_field port 2>/dev/null || true)"
  [ -n "${saved_port:-}" ] && PORT="$saved_port"
fi

[ -f "$STATE_PATH" ] && stop_recorded_injector
release_codex_launchd_job || true
if codex_is_running; then
  verified_cdp_endpoint "$PORT" \
    || fail "Codex is running but the managed CDP endpoint cannot be verified; version restore stopped before file exchange."
  "$NODE" "$INJECTOR" --remove --port "$PORT" --theme-dir "$THEME_DIR" --timeout-ms 8000 >/dev/null \
    || fail "The live skin could not be removed; version restore stopped before file exchange."
fi

"$NODE" "$SCRIPT_DIR/version-backup-state.mjs" restore \
  --state-root "$STATE_ROOT" \
  --install-root "$INSTALL_ROOT" \
  --theme-dir "$THEME_DIR" \
  --label "$VERSION_BACKUP_LABEL" >/dev/null

exec "$INSTALL_ROOT/scripts/start-dream-skin-macos.sh" --port "$PORT" --prompt-restart
