#!/bin/bash

set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd -P)/common-macos.sh"

REQUIRE_LIVE="false"
REQUIRE_VERSION_BACKUP="false"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --require-live) REQUIRE_LIVE="true"; shift ;;
    --require-version-backup) REQUIRE_VERSION_BACKUP="true"; shift ;;
    *) fail "Unknown doctor argument: $1" ;;
  esac
done

discover_codex_app
require_macos_runtime
[ -f "$CONFIG_PATH" ] || fail "Codex config not found: $CONFIG_PATH"
for required in \
  "$PROJECT_ROOT/assets/dream-skin.css" \
  "$PROJECT_ROOT/assets/renderer-inject.js" \
  "$PROJECT_ROOT/assets/theme.json" \
  "$PROJECT_ROOT/scripts/injector.mjs" \
  "$PROJECT_ROOT/scripts/version-backup-state.mjs"; do
  [ -s "$required" ] || fail "Required project file is missing or empty: $required"
done

if [ -f "$THEME_DIR/theme.json" ]; then
  PAYLOAD_JSON="$("$NODE" "$INJECTOR" --check-payload --theme-dir "$THEME_DIR")"
else
  PAYLOAD_JSON="$("$NODE" "$INJECTOR" --check-payload)"
fi
PORT=9341
if [ -f "$STATE_PATH" ]; then
  PORT="$(state_field port)"
fi
LIVE="false"
if [ -f "$STATE_PATH" ] && verified_cdp_endpoint "$PORT"; then
  if [ -f "$THEME_DIR/theme.json" ]; then
    "$NODE" "$INJECTOR" --verify --port "$PORT" --theme-dir "$THEME_DIR" --timeout-ms 12000 >/dev/null
  else
    "$NODE" "$INJECTOR" --verify --port "$PORT" --timeout-ms 12000 >/dev/null
  fi
  LIVE="true"
fi
[ "$REQUIRE_LIVE" = "false" ] || [ "$LIVE" = "true" ] || fail "No verified live Dream Skin session is active."

VERSION_BACKUP_LABEL=""
if [ -s "$VERSION_BACKUP_LABEL_PATH" ]; then
  VERSION_BACKUP_LABEL="$(/bin/cat "$VERSION_BACKUP_LABEL_PATH")"
fi
VERSION_BACKUP_ROOT="${STATE_ROOT}/version-backups/${VERSION_BACKUP_LABEL}"
if [ -n "$VERSION_BACKUP_LABEL" ] && [ -e "$VERSION_BACKUP_ROOT" ]; then
  VERSION_BACKUP_JSON="$("$NODE" "$SCRIPT_DIR/version-backup-state.mjs" verify \
    --state-root "$STATE_ROOT" --label "$VERSION_BACKUP_LABEL")"
else
  [ "$REQUIRE_VERSION_BACKUP" = "false" ] || fail "Required previous-version backup is missing."
  VERSION_BACKUP_JSON='{"pass":false,"present":false}'
fi

"$NODE" -e '
  const payload = JSON.parse(process.argv[1]);
  const versionBackup = JSON.parse(process.argv[10]);
  const result = {
    pass: true,
    product: "Codex Theme Studio",
    version: process.argv[2],
    platform: `darwin-${process.argv[3]}`,
    codexVersion: process.argv[4],
    codexTeamId: process.argv[5],
    nodeVersion: process.argv[6],
    officialAppSignatureValid: true,
    modifiesAppAsar: false,
    live: process.argv[7] === "true",
    port: Number(process.argv[8]),
    theme: {
      id: payload.themeId,
      name: payload.themeName,
      imageBytes: payload.imageBytes,
      payloadBytes: payload.payloadBytes,
    },
    versionBackup: {
      label: process.argv[9],
      present: versionBackup.present !== false,
      pass: versionBackup.pass === true,
      files: Number(versionBackup.files || 0),
      createdAt: versionBackup.createdAt || "",
    },
  };
  console.log(JSON.stringify(result, null, 2));
' "$PAYLOAD_JSON" "$SKIN_VERSION" "$(/usr/bin/uname -m)" "$CODEX_VERSION" "$CODEX_TEAM_ID" "$NODE_VERSION" "$LIVE" "$PORT" "$VERSION_BACKUP_LABEL" "$VERSION_BACKUP_JSON"
