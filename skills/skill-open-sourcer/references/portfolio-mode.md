# Canonical Portfolio mode

Zhijian Skills publishes every public Skill from `zjp1997720/zhijian-skills`. A local `SKILL.md` is always imported into this Portfolio; it never becomes a standalone repository.

## Entry contract

The canonical checkout contains:

- `registry/skills.json`
- `skills/<name>/SKILL.md` for every active record
- bilingual documentation and a Changelog referenced by the Registry
- a lockfile-pinned `skills` CLI
- an `origin` that resolves to `zjp1997720/zhijian-skills`

Run:

```bash
python3 <skill-open-sourcer-dir>/scripts/portfolio.py audit \
  --repo <zhijian-skills> --strict
```

## Release flow

1. Audit the canonical repository and the incoming Skill.
2. Sanitize and copy the complete payload into `skills/<name>/`.
3. Add bilingual docs, Changelog, Registry metadata, catalog entry, and visual assets.
4. Run declared tests, Portfolio contracts, local discovery, and isolated copy installation.
5. Build one immutable candidate per changed Skill and produce one dry-run summary.
6. Verify the frozen plan, push canonical `main`, verify the remote Portfolio, then create only the canonical Tag `<skill>/v<version>`.
7. Record each remote transition in the release ledger and resume from verified state after interruption.

No step creates, updates, redirects, or releases a standalone Skill repository.
