# Registry contract

`registry/skills.json` is the only machine-readable Portfolio inventory.

Each active record declares:

- `name`, lifecycle, independent semantic `version`, canonical path, and compatibility mirror
- Human documentation, localized documentation, and Changelog paths
- Canonical and mirror Tag names
- Deterministic validation commands and an optional live smoke check
- Security capabilities: network, subprocess, filesystem, and credentials
- Supported Harness identifiers

## Invariants

- `path` equals `skills/<name>`.
- Names, paths, and mirrors are unique.
- Every referenced repository file exists.
- Install payloads do not depend on another Skill directory.
- A capability used by executable files is declared.
- Retired records are excluded from active audit and release.
- Versions are independent; a change to one Skill does not bump another.

The JSON Schema is the transport contract. `portfolio.py` adds repository and filesystem checks that JSON Schema cannot express.

