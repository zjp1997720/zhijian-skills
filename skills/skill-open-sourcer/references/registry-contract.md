# Registry contract

`registry/skills.json` is the only machine-readable Portfolio inventory.

Each active record declares:

- `name`, lifecycle, independent semantic `version`, and canonical `path`
- bilingual documentation and Changelog paths
- canonical Tag `<skill>/v<version>`
- deterministic validation commands and optional live smoke check
- security capabilities and supported Harness identifiers

## Invariants

- `path` equals `skills/<name>`.
- Names and paths are unique.
- Every referenced repository file exists.
- Install payloads do not depend on another Skill directory.
- Executable capabilities are declared.
- Retired records are excluded from active release checks.
- Records must not contain `mirror`, `mirror_tag`, or standalone repository metadata.
- Versions remain independent even though every release shares the same canonical repository.
