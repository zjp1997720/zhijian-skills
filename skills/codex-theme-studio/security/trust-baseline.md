# Security trust baseline

Reviewed: 2026-09-04

Owner: Zhijian AI

Review due: 2027-09-04

## Trust boundary

The runtime writes only the prepared theme, installed runtime, owner-only recovery state, generated Desktop launchers, and—after separate persistence authorization—one user LaunchAgent plist. Live connections are limited to an operator-selected DevTools endpoint on `127.0.0.1`. Bundled runtime scripts make no outbound internet request and receive no credentials.

The Skill does not modify `app.asar`, the signed application bundle, authentication state, repositories, tasks, projects, or conversations. It validates the official Codex bundle identifier, signer, architecture, signed bundled Node.js, port owner, and renderer identity before live injection. Restarting a running Codex app requires explicit authorization; enabling the resident manager records separate recurring authorization and never launches Codex after the user intentionally quits it.

## Capability decisions

| Capability | Decision | Scope |
| --- | --- | --- |
| Loopback network | Approved | Local CDP discovery, injection, removal, and verification |
| File write | Approved | Prepared theme, installed runtime, logs, immutable backups, owner-only resident approval, and opt-in user LaunchAgent |
| Subprocess | Approved | Local tests, app identity checks, managed injector, authorized restart or restore, and opt-in resident lifecycle |
| Outbound internet | Denied | No bundled runtime script may contact an internet host |
| Credentials | Not required | Optional artwork creation is delegated to the host's separately governed ImageGen capability |

## Release evidence

- Theme schema validation covers colors, UI/code fonts, body/emphasis/code weights, local image paths and sizes, control/card/hero/composer radii, and homepage density.
- Deterministic tests cover both bundled presets, installation state, immutable version backups, config preservation, route transitions, native controls, typography, keyboard visibility, overflow, task-art suppression, and resident-manager lifecycle.
- The public payload scan returns zero blockers. The only accepted binary warnings are the declared `graphite-paper` PNG copies and the separately licensed `zhijian-ai` preset artwork.
- Local Portfolio validation, strict bilingual README audit, complete Portfolio tests, local `npx skills` discovery, and isolated copy installation with byte-for-byte comparison passed for version `1.2.0` before publication.
- A macOS no-launch upgrade validated official Codex `26.901.22334` and its signed Node.js `v24.19.0`, upgraded the runtime from `1.1.11` to `1.2.0`, and preserved the active custom theme ID.

## Missing evidence

- Fresh second-Mac installation through Restore: missing evidence.
- Post-upgrade live Doctor, Verify, and screenshot run for `1.2.0`: missing evidence because the release task did not authorize restarting the active Codex session.
- Compatibility with future unlisted Codex versions: missing evidence.
- Independent third-party security review: missing evidence.

Generated run reports remain local and ignored. This checked-in baseline is the public release source of truth until newer reviewed evidence replaces it.
