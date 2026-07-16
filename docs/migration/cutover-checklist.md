# Cutover checklist

## Source baseline

- [x] Record all eight selected runtime sources.
- [x] Record public Commit SHAs.
- [x] Exclude generated, private, cached, and dependency content.
- [x] Preserve local working copies until canonical verification.
- [x] Capture trigger, workflow, output, and resource invariants.

## Canonical repository

- [ ] Import all eight payloads into `skills/<name>/`.
- [ ] Create Registry records, public docs, and Changelogs.
- [ ] Pass repository contract and catalog discovery.
- [ ] Pass Portfolio audit and isolated install matrix.

## Compatibility mirrors

- [ ] Produce one canary mirror from the exporter.
- [ ] Verify candidate Refs before updating `main`.
- [ ] Verify canonical and mirror `main` before Tags/Releases.
- [ ] Preserve history and historical install URLs.
- [ ] Redirect Issues and PRs to the canonical repository.

## Local Harnesses

- [ ] Dry-run every replacement and create an external backup.
- [ ] Replace active public copies with canonical Symlinks.
- [ ] Verify every declared Skill/Harness pair.
- [ ] Confirm rollback restores the previous directory.

## Retirement

- [ ] Add retirement README to `content-twin-toolkit`.
- [ ] Add retirement README to `agents-team-orchestrator`.
- [ ] Preserve or redirect existing open work.
- [ ] Archive both repositories after redirect verification.

