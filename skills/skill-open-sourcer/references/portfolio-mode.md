# Portfolio mode

Portfolio mode manages multiple independently versioned Skills from one canonical repository.

## Entry contract

The target directory must contain:

- `registry/skills.json`
- `skills/<name>/SKILL.md` for every active record
- Human documentation and Changelogs referenced by the Registry
- A lockfile-pinned `skills` CLI

Run:

```bash
python3 <skill-open-sourcer-dir>/scripts/portfolio.py audit --repo <repo> --strict
```

The audit is deterministic and produces stable finding IDs. It checks Registry shape, unique ownership, package paths, frontmatter, referenced files, public-release safety, declared executable capabilities, documentation, and lifecycle state.

## Portfolio release flow

1. Audit the canonical repository and local Harness links.
2. Detect changed active Skills by content digest.
3. Run declared deterministic tests and isolated install checks.
4. Classify each change with the version contract.
5. Build one immutable candidate and one mirror export per passing Skill.
6. Produce one Dry Run summary. Do not acquire release credentials yet.
7. After one confirmation, verify temporary remote candidates, update canonical and mirror `main`, verify both, then create Tags and Releases.
8. Persist every remote transition in the release ledger. Resume from verified state instead of repeating mutations.
9. Isolate a Skill-specific failure. Stop the entire wave when Registry, governance, or shared CI fails.

Portfolio mode never edits a standalone mirror as a source and never force-pushes.

## Single-Skill compatibility

The existing Single-Skill workflow remains valid. `validate-skill` accepts any self-contained Skill directory and does not require a Portfolio Registry.

