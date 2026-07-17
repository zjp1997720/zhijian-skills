# Output evaluation baseline

Reviewed: 2026-07-17

Method: static Yao assertion grading over the checked-in cases and file-backed fixtures

## Result

| Metric | Value |
| --- | ---: |
| Cases | 6 |
| File-backed cases | 3 |
| Baseline pass rate | 0% |
| With-Skill pass rate | 100% |
| Delta | 100 points |
| Regressions | 0 |
| Static gate | Pass |

All six with-Skill outputs satisfied their declared assertions: brand-to-reversible-theme, imagegen-banner-path, intentional-full-page-art, reject-app-bundle-patch, annotated-theme-repair, and governed-handoff-evidence.

## Evidence boundary

This baseline proves deterministic assertion coverage for the committed fixtures. It does not prove provider-backed behavior or visual quality on every Codex release.

- Independent blind human adjudication: missing evidence.
- Provider-backed holdout execution: missing evidence.
- Clean-account macOS installation: missing evidence.
- Live ImageGen execution across supported hosts: missing evidence.
- Multi-viewport live Codex screenshots for the public neutral theme: missing evidence.

Generated scorecards stay local and ignored at `reports/output_quality_scorecard.md`. The release carries the source cases, assertions, fixtures, and this reproducible baseline.
