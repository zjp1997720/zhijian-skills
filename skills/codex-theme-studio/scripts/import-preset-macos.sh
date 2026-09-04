#!/bin/bash

set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd -P)/common-macos.sh"

PRESET_ID=""
APPLY_NOW="false"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --id) PRESET_ID="${2:-}"; shift 2 ;;
    --apply) APPLY_NOW="true"; shift ;;
    --no-apply) APPLY_NOW="false"; shift ;;
    *) fail "Unknown preset argument: $1" ;;
  esac
done

[ -n "$PRESET_ID" ] || fail "Usage: import-preset-macos.sh --id <preset-id> [--apply]"
case "$PRESET_ID" in
  *[!a-z0-9-]*|-*|*-) fail "Invalid preset id: $PRESET_ID" ;;
esac

SRC="$PROJECT_ROOT/presets/$PRESET_ID"
[ -d "$SRC" ] || fail "Bundled preset not found: $PRESET_ID"
[ -f "$SRC/preset.json" ] || fail "preset.json missing in $PRESET_ID"
[ -f "$SRC/theme.json" ] || fail "theme.json missing in $PRESET_ID"

ensure_node_runtime
"$NODE" "$INJECTOR" --check-payload --theme-dir "$SRC" >/dev/null
ensure_state_root
THEMES_ROOT="$STATE_ROOT/themes"
DEST="$THEMES_ROOT/$PRESET_ID"
/bin/mkdir -p "$THEMES_ROOT"
/bin/chmod 700 "$THEMES_ROOT"

temporary="$THEMES_ROOT/.${PRESET_ID}.importing.$$"
/bin/mkdir -p "$temporary"
cleanup_temporary() { /bin/rm -rf "$temporary"; }
trap cleanup_temporary EXIT
/usr/bin/rsync -a --delete --exclude 'preset.json' "$SRC/" "$temporary/"
"$NODE" "$INJECTOR" --check-payload --theme-dir "$temporary" >/dev/null
if [ -e "$DEST" ]; then /bin/rm -rf "$DEST"; fi
/bin/mv "$temporary" "$DEST"
/bin/chmod 700 "$DEST"
/bin/chmod 600 "$DEST"/*
trap - EXIT

if [ "$APPLY_NOW" = "true" ]; then
  exec "$SCRIPT_DIR/switch-theme-macos.sh" --id "$PRESET_ID"
fi

printf 'Imported preset %s. Apply it with: %s --id %s\n' \
  "$PRESET_ID" "$SCRIPT_DIR/switch-theme-macos.sh" "$PRESET_ID"
