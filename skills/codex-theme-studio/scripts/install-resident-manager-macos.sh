#!/bin/bash

set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd -P)/common-macos.sh"

PORT=9341
DISABLE="false"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --port) PORT="${2:-}"; shift 2 ;;
    --disable) DISABLE="true"; shift ;;
    *) fail "Unknown resident-manager argument: $1" ;;
  esac
done

ensure_state_root
if [ "$DISABLE" = "true" ]; then
  disable_resident_manager
  printf 'Codex Theme Studio resident manager disabled.\n'
  exit 0
fi

validate_port "$PORT"
discover_codex_app
require_macos_runtime
[ "$PROJECT_ROOT" = "$INSTALL_ROOT" ] \
  || fail "Install the runtime first, then enable the resident manager from $INSTALL_ROOT."

/bin/mkdir -p "$HOME/Library/LaunchAgents"

"$NODE" -e '
  const fs = require("node:fs");
  const [configPath, plistPath, label, manager, stdoutPath, stderrPath, port] = process.argv.slice(1);
  const escape = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
  const config = {
    schemaVersion: 1,
    enabled: true,
    autoRestartNormalLaunch: true,
    port: Number(port),
    approvedAt: new Date().toISOString(),
  };
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>${escape(label)}</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>${escape(manager)}</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>ProcessType</key><string>Background</string>
  <key>ThrottleInterval</key><integer>5</integer>
  <key>StandardOutPath</key><string>${escape(stdoutPath)}</string>
  <key>StandardErrorPath</key><string>${escape(stderrPath)}</string>
</dict></plist>
`;
  const writeAtomic = (file, content, mode) => {
    const temporary = `${file}.${process.pid}.tmp`;
    fs.writeFileSync(temporary, content, { mode });
    fs.renameSync(temporary, file);
    fs.chmodSync(file, mode);
  };
  writeAtomic(configPath, `${JSON.stringify(config, null, 2)}\n`, 0o600);
  writeAtomic(plistPath, xml, 0o600);
' "$RESIDENT_MANAGER_CONFIG" "$RESIDENT_MANAGER_PLIST" "$RESIDENT_MANAGER_JOB_LABEL" \
  "$SCRIPT_DIR/resident-manager-macos.sh" "$RESIDENT_MANAGER_LOG" "$RESIDENT_MANAGER_ERROR_LOG" "$PORT"

/usr/bin/plutil -lint "$RESIDENT_MANAGER_PLIST" >/dev/null \
  || { disable_resident_manager; fail "Resident manager LaunchAgent is invalid."; }

domain="gui/$(/usr/bin/id -u)"
/bin/launchctl bootout "$domain/$RESIDENT_MANAGER_JOB_LABEL" >/dev/null 2>&1 || true
if ! /bin/launchctl bootstrap "$domain" "$RESIDENT_MANAGER_PLIST"; then
  disable_resident_manager
  fail "Could not register the resident manager LaunchAgent."
fi
/bin/launchctl kickstart -k "$domain/$RESIDENT_MANAGER_JOB_LABEL" >/dev/null 2>&1 || true

printf 'Codex Theme Studio resident manager enabled on loopback port %s. Normal Codex launches will be restarted once to restore the theme.\n' "$PORT"
