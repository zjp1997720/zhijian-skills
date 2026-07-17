# Cutover checklist

## Source baseline

- [x] Record all eight selected runtime sources.
- [x] Record public Commit SHAs.
- [x] Exclude generated, private, cached, and dependency content.
- [x] Preserve local working copies until canonical verification.
- [x] Capture trigger, workflow, output, and resource invariants.

## Canonical repository

- [x] Import all eight payloads into `skills/<name>/`.
- [x] Create Registry records, public docs, and Changelogs.
- [x] Pass repository contract and catalog discovery.
- [x] Pass Portfolio audit and isolated install matrix.

## Compatibility mirrors

- [x] Produce one canary mirror from the exporter.
- [x] Verify candidate Refs before updating `main`.
- [x] Verify canonical and mirror `main` before Tags/Releases.
- [x] Preserve history and historical install URLs.
- [x] Redirect Issues and PRs to the canonical repository.

## Local Harnesses

- [x] Dry-run every replacement and create an external backup.
- [x] Replace active public copies with canonical Symlinks.
- [x] Verify every declared Skill/Harness pair.
- [x] Confirm rollback restores the previous directory in automated tests.

The live cutover rollback manifest is stored outside every Skill root under `~/.local/state/zhijian-skills/link-backups/`.

## Retirement

- [x] Add retirement README to `content-twin-toolkit`.
- [x] Add retirement README to `agents-team-orchestrator`.
- [x] Preserve or redirect existing open work.
- [x] Archive both repositories after redirect verification.
