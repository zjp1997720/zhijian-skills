# Per-Skill version contract

Each Skill owns an independent SemVer line inside the shared Portfolio. Canonical Tags use `<skill>/v<version>`.

- Patch: compatible instruction, fixture, documentation, packaging, or implementation correction.
- Minor: compatible new capability, command, output, asset, or supported Harness.
- Major: removed capability, changed trigger identity, incompatible output or runtime contract, renamed entrypoint, or destructive migration.

The first governed release is `1.0.0`. A release plan must state the matched reason. An unmatched semantic change blocks release until the Registry version and Changelog are updated deliberately. Standalone and mirror Tags do not exist in this release model.
