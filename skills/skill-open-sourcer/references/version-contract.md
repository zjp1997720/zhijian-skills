# Per-Skill Version Contract

Each Skill owns an independent SemVer line. Canonical tags use `<skill>/v<version>` and mirror tags use `v<version>`.

- Patch: compatible instruction, fixture, documentation, packaging, or implementation correction.
- Minor: compatible new capability, command, output, asset, or supported Harness.
- Major: removed capability, changed trigger identity, incompatible output or runtime contract, renamed entrypoint, or destructive migration requirement.

The first governed release is `1.0.0`. A release plan must state the matched reason; an unmatched semantic change blocks release until the Registry version and changelog are updated deliberately.
