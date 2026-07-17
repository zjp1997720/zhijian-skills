# Security trust baseline

Reviewed: 2026-07-17

Owner: Zhijian AI

Review due: 2027-07-17

## Trust boundary

The runtime writes only the prepared theme, the installed runtime, owner-only recovery state, and—after explicit persistence authorization—one user LaunchAgent plist. Live connections are limited to an operator-selected DevTools endpoint on `127.0.0.1`. Bundled scripts make no outbound internet request and receive no credentials.

The Skill does not modify `app.asar`, the signed application bundle, authentication state, repositories, or conversations. It validates the official Codex bundle identifier and signer before live injection. Restarting a running Codex app requires explicit authorization; enabling the resident manager records separate recurring authorization and never launches Codex from a stopped state.

## Capability decisions

| Capability | Decision | Scope |
| --- | --- | --- |
| Loopback network | Approved | Local CDP discovery, injection, removal, and verification |
| File write | Approved | Prepared theme, installed runtime, logs, immutable backups, owner-only resident approval, and opt-in user LaunchAgent |
| Subprocess | Approved | Local tests, app identity checks, managed injector, authorized restart or restore, and opt-in resident lifecycle |
| Outbound internet | Denied | No bundled script may contact an internet host |
| Credentials | Not required | Image creation is delegated to the host's separately governed ImageGen Skill |

## Evidence status

The repository tests cover package, payload, route, art-placement, native-UI, privacy, recovery, and resident-manager lifecycle contracts. The network and permission policies record the approved scopes and enforcement points.

- Live public installer on a clean macOS account: missing evidence.
- Live ImageGen invocation through every supported host: missing evidence.
- Independent security review: missing evidence.

Generated trust reports remain local ignored evidence. This checked-in baseline is the release source of truth until newer reviewed evidence replaces it.
