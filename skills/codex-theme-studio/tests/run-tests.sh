#!/bin/bash

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
NODE="${NODE:-$(command -v node || true)}"
[ -n "$NODE" ] && [ -x "$NODE" ] || { printf 'Node.js 20+ was not found.\n' >&2; exit 1; }
NODE_MAJOR="$($NODE -p 'process.versions.node.split(".")[0]')"
[ "$NODE_MAJOR" -ge 20 ] || { printf 'Node.js 20+ is required; found %s.\n' "$($NODE --version)" >&2; exit 1; }

while IFS= read -r file; do /bin/bash -n "$file"; done < <(
  find "$ROOT/scripts" "$ROOT/tests" -type f -name '*.sh' -print
)
while IFS= read -r file; do "$NODE" --check "$file" >/dev/null; done < <(
  find "$ROOT/scripts" "$ROOT/assets" -type f \( -name '*.mjs' -o -name '*.js' \) -print
)

if grep -R -n -E 'dream-skin-skin|DREAM_SKIN_SKIN|1\.0\.0-rc2' \
  "$ROOT/scripts" "$ROOT/assets" >/dev/null; then
  printf 'Legacy release-candidate identifiers remain in runtime files.\n' >&2
  exit 1
fi
if grep -R -n -E '(writeFile|rename|copyFile|rm).*app\.asar' "$ROOT/scripts" >/dev/null; then
  printf 'A runtime script appears to mutate app.asar.\n' >&2
  exit 1
fi
if grep -n -E '/usr/bin/python3|(^|[[:space:]])eval([[:space:]]|$)' \
  "$ROOT/scripts/common-macos.sh" >/dev/null; then
  printf 'The shared runtime must parse state with the bundled Node.js, without python3 or eval.\n' >&2
  exit 1
fi
if grep -n -E 'verified_cdp_endpoint.*\|\|.*cdp_http_ready|codex_is_running.*\|\|.*verified_cdp_endpoint' \
  "$ROOT/scripts/common-macos.sh" >/dev/null; then
  printf 'CDP readiness must not bypass listener identity verification.\n' >&2
  exit 1
fi

"$NODE" "$ROOT/scripts/injector.mjs" --check-payload >/dev/null
"$NODE" "$ROOT/tests/theme-contract.test.mjs"
"$NODE" "$ROOT/tests/base-theme-state.test.mjs"
"$NODE" "$ROOT/tests/version-backup-state.test.mjs"
"$NODE" "$ROOT/tests/release-privacy.test.mjs"
"$NODE" "$ROOT/tests/verifier-contract.test.mjs"
"$NODE" "$ROOT/tests/resident-manager.test.mjs"
"$NODE" "$ROOT/tests/skill-contract.test.mjs"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/codex-theme-studio-tests.XXXXXX")"
trap '/bin/rm -rf "$TMP"' EXIT

RUNTIME_HOME="$TMP/runtime-home"
RUNTIME_STATE_ROOT="$RUNTIME_HOME/Library/Application Support/CodexThemeStudio"
RUNTIME_STATE="$RUNTIME_STATE_ROOT/state.json"
STATE_EVAL_MARKER="$TMP/state-eval-marker"
EXPECTED_BUNDLE="$TMP/Codex \$(touch \"$STATE_EVAL_MARKER\").app"
EXPECTED_EXE="$EXPECTED_BUNDLE/Contents/MacOS/ChatGPT; touch \"$STATE_EVAL_MARKER\""
EXPECTED_VERSION='1.0.3 "nightly"'
EXPECTED_TEAM_ID="TEAM'ID"
/bin/mkdir -p "$RUNTIME_STATE_ROOT"
"$NODE" -e '
  const fs = require("node:fs");
  const [file, codexBundle, codexExe, codexVersion, codexTeamId] = process.argv.slice(1);
  fs.writeFileSync(file, `${JSON.stringify({ codexBundle, codexExe, codexVersion, codexTeamId })}\n`);
' "$RUNTIME_STATE" "$EXPECTED_BUNDLE" "$EXPECTED_EXE" "$EXPECTED_VERSION" "$EXPECTED_TEAM_ID"
HOME="$RUNTIME_HOME" NODE="$NODE" /bin/bash -c '
  . "$1/scripts/common-macos.sh"
  restore_runtime_context_from_state
  [ "$CODEX_BUNDLE" = "$2" ]
  [ "$CODEX_EXE" = "$3" ]
  [ "$CODEX_VERSION" = "$4" ]
  [ "$CODEX_TEAM_ID" = "$5" ]
' _ "$ROOT" "$EXPECTED_BUNDLE" "$EXPECTED_EXE" "$EXPECTED_VERSION" "$EXPECTED_TEAM_ID"
[ ! -e "$STATE_EVAL_MARKER" ] || {
  printf 'Runtime state values were evaluated as shell code.\n' >&2
  exit 1
}

/bin/mkdir -p "$TMP/theme"
/bin/cp "$ROOT/assets/default-banner.png" "$TMP/theme/background.png"
"$NODE" "$ROOT/scripts/write-theme.mjs" custom --output-dir "$TMP/theme" \
  --image background.png --name 'Test Theme' --brand-label 'TEST STUDIO' \
  --accent '#11aa55' --secondary '#22bbcc' --highlight '#663399' \
  --background '#f0eee8' --sidebar '#e9e7df' --selected '#ddd9cf' >/dev/null
PAYLOAD_JSON="$("$NODE" "$ROOT/scripts/injector.mjs" --check-payload --theme-dir "$TMP/theme")"
"$NODE" -e '
  const value = JSON.parse(process.argv[1]);
  if (!value.pass || value.themeName !== "Test Theme" || value.imageBytes < 1) process.exit(1);
' "$PAYLOAD_JSON"
/bin/mkdir -p "$TMP/missing-theme"
if MISSING_THEME_OUTPUT="$(
  "$NODE" "$ROOT/scripts/injector.mjs" --check-payload --theme-dir "$TMP/missing-theme" 2>&1
)"; then
  printf 'Explicit theme directory without theme.json unexpectedly passed.\n' >&2
  exit 1
fi
printf '%s\n' "$MISSING_THEME_OUTPUT" | grep -F -q \
  "Explicit theme directory is missing theme.json:"
printf '%s\n' "$MISSING_THEME_OUTPUT" | grep -F -q "/missing-theme/theme.json"
"$NODE" "$ROOT/scripts/write-theme.mjs" reset-demo --output-dir "$TMP/theme" >/dev/null
[ ! -e "$TMP/theme" ]

CONFIG="$TMP/config.toml"
BACKUP="$TMP/theme-backup.json"
printf '%s\n' \
  'model = "gpt-5"' \
  '' \
  '[desktop]' \
  'appearanceTheme = "system"' \
  'appearanceDarkCodeThemeId = "vscode-dark"' \
  'keepMe = true' > "$CONFIG"
/bin/cp "$CONFIG" "$TMP/original.toml"
"$NODE" "$ROOT/scripts/theme-config.mjs" install "$CONFIG" "$BACKUP" >/dev/null
/usr/bin/cmp -s "$CONFIG" "$TMP/original.toml"
"$NODE" -e '
  const backup = JSON.parse(require("fs").readFileSync(process.argv[1], "utf8"));
  if (backup.schemaVersion !== 2 || backup.changedKeys.length !== 0) process.exit(1);
' "$BACKUP"
"$NODE" "$ROOT/scripts/theme-config.mjs" restore "$CONFIG" "$BACKUP" >/dev/null
/usr/bin/cmp -s "$CONFIG" "$TMP/original.toml"

if [ "${CODEX_THEME_STUDIO_LIVE_TEST:-0}" = "1" ] && [ "$(uname -s)" = "Darwin" ]; then
  "$ROOT/scripts/doctor-macos.sh" >/dev/null
else
  printf 'SKIP: live macOS doctor (set CODEX_THEME_STUDIO_LIVE_TEST=1 to enable).\n'
fi

printf 'PASS: syntax, payload, brand options, backups, runtime-state safety, custom colors, non-destructive config, and portable checks.\n'
