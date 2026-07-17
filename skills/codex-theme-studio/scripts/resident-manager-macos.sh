#!/bin/bash

# Opt-in resident manager. It never launches Codex from a stopped state. When
# the user opens Codex normally, it performs the explicitly authorized restart
# needed to restore the loopback CDP endpoint and theme injector.

set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd -P)/common-macos.sh"

discover_codex_app
require_macos_runtime
ensure_state_root

resident_log() {
  printf '%s %s\n' "$(/bin/date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >> "$RESIDENT_MANAGER_LOG"
}

last_restart=0
while resident_manager_enabled; do
  if ! codex_is_running; then
    /bin/sleep 2
    continue
  fi

  port="$(resident_manager_port 2>/dev/null || true)"
  case "$port" in
    ''|*[!0-9]*) resident_log "disabled: invalid configured port"; exit 0 ;;
  esac
  if [ "$port" -lt 1024 ] || [ "$port" -gt 65535 ]; then
    resident_log "disabled: invalid configured port"
    exit 0
  fi

  if verified_cdp_endpoint "$port" 2>/dev/null; then
    if ! recorded_injector_is_running; then
      resident_log "repairing injector on verified port $port"
      if ! "$SCRIPT_DIR/start-dream-skin-macos.sh" --port "$port" >>"$RESIDENT_MANAGER_LOG" 2>>"$RESIDENT_MANAGER_ERROR_LOG"; then
        resident_log "injector repair failed"
      fi
    fi
    /bin/sleep 2
    continue
  fi

  /bin/sleep 2
  codex_is_running || continue
  verified_cdp_endpoint "$port" 2>/dev/null && continue

  now="$(/bin/date +%s)"
  if [ $((now - last_restart)) -lt 45 ]; then
    /bin/sleep 2
    continue
  fi
  last_restart="$now"
  resident_log "normal Codex launch detected; restoring managed theme on port $port"
  if ! "$SCRIPT_DIR/start-dream-skin-macos.sh" --port "$port" --restart-existing \
    >>"$RESIDENT_MANAGER_LOG" 2>>"$RESIDENT_MANAGER_ERROR_LOG"; then
    resident_log "managed restart failed; cooldown active"
  fi
  /bin/sleep 2
done

resident_log "resident manager disabled"
