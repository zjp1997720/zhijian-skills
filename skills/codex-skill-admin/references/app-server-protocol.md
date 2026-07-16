# Codex App-Server Skill Protocol

Use this reference only when `scripts/codex_skill_admin.py` fails or needs patching.

## Methods

Initialize before any request:

```json
{
  "id": 1,
  "method": "initialize",
  "params": {
    "clientInfo": {
      "name": "codex-skill-admin",
      "version": "1.0.0"
    },
    "capabilities": {
      "experimentalApi": true
    }
  }
}
```

List skills:

```json
{
  "id": 2,
  "method": "skills/list",
  "params": {
    "cwds": ["/absolute/workspace/path"],
    "forceReload": true
  }
}
```

Enable or disable by path:

```json
{
  "id": 3,
  "method": "skills/config/write",
  "params": {
    "path": "/absolute/path/to/SKILL.md",
    "enabled": false
  }
}
```

Path-based writes are safest. Name-based writes are supported by the protocol, but duplicate names exist in real installs.

## Transport

The bundled script uses only this temporary localhost transport. It does not depend on a persistent Codex daemon or proxy socket.

Reliable path:

1. Start a temporary app server:

```bash
codex app-server --listen ws://127.0.0.1:PORT
```

2. Wait for:

```text
http://127.0.0.1:PORT/readyz
```

3. Connect with local WebSocket and JSON-RPC messages.

Avoid assuming `codex app-server proxy` works. It requires a managed daemon control socket at:

```text
~/.codex/app-server-control/app-server-control.sock
```

Desktop Codex may run without that socket, and `codex app-server daemon start` may fail if the standalone daemon install is absent.

## Validation

After config writes:

```bash
codex debug prompt-input "skill visibility check"
```

Count lines between `### Available skills` and `### How to use skills`. This validates what a new model prompt actually sees.
