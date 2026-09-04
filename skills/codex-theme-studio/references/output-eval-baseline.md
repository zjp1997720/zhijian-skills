# Output evaluation baseline

Reviewed: 2026-09-04

Method: deterministic assertion grading over the checked-in output cases

## Result

| Metric | Value |
| --- | ---: |
| Cases | 3 |
| Assertions | 11 |
| Baseline assertions passed | 0 / 11 |
| With-Skill assertions passed | 11 / 11 |
| Regressions | 0 |
| Static gate | Pass |

The cases cover safe installation, refusal to reuse Codex selectors in ZCode or Doubao Work, and design-only preparation without installation or restart. With-Skill outputs preserve official-app identity, loopback CDP, explicit authorization, verification, rollback, target boundaries, payload validation, and no-install behavior.

## Evidence boundary

This baseline proves deterministic output-contract coverage for the committed cases. It does not prove provider-backed behavior, universal compatibility, or visual quality on every Codex release.

- Independent blind human adjudication: missing evidence.
- Provider-backed holdout execution: missing evidence.
- Fresh second-Mac installation: missing evidence.
- Live multi-viewport screenshots for the public `graphite-paper` preset: missing evidence.

Generated scorecards remain local ignored evidence. The release carries the source cases and this reproducible baseline.
