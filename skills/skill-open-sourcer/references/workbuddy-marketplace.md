# WorkBuddy marketplace adaptation and verification

Use this branch when adapting the canonical Portfolio as a WorkBuddy custom source, maintaining its generated catalog, or diagnosing a plugin that installs but disappears after restart. Ordinary Skill releases also enter this branch when they change data consumed by an existing catalog.

## Scope and source

Resolve and verify the canonical checkout and its synchronization guard using the main Skill workflow. Preserve unrelated edits. Adapter-only work changes marketplace metadata, generation/verification tooling, and setup documentation; it does not authorize a new Skill release, bulk installation into the user's environment, or changes to host security settings. If Skill payloads change, return to the full per-Skill version and release workflow.

The repository-owned tools below live under `<zhijian-skills>/scripts/`, not inside this installed Skill. Read their current `--help` and implementation before use; keep one implementation in the Portfolio.

## Build the adapter

1. Use the cloneable repository source `zjp1997720/zhijian-skills` or `https://github.com/zjp1997720/zhijian-skills.git`. A `/tree/main/skills` page is not a Git source. Use Git distribution for this catalog's relative plugin paths and complete payloads; a raw JSON URL alone is insufficient.
2. Keep inventory, lifecycle, and versions in `registry/skills.json`. Reuse existing documentation for descriptions and preserve actual runtime requirements. Catalog presence is not evidence of WorkBuddy runtime compatibility; identify entries that depend on Codex host capabilities.
3. Generate `.codebuddy-plugin/marketplace.json` and one `plugins/<name>/.codebuddy-plugin/plugin.json` per bundle. Require the standalone plugin manifests, with explicit Skill paths. WorkBuddy 5.5.6 on macOS accepted `strict: false` entries without a plugin manifest during installation but omitted them on cold start; schema validation and an installation success message did not catch this.
4. Keep editable payloads in `skills/<name>/`. Generated wrapper links may resolve to those payloads inside the same repository; require installation to materialize them as real files inside the versioned plugin cache. Reject links outside the repository or installed cache. A wrapper link is not permission for an installed Skill to depend on external paths. Record the tested OS and host version; Windows symlink behavior needs its own test.

Run from the canonical checkout:

```bash
python3 scripts/build_workbuddy_marketplace.py
python3 scripts/build_workbuddy_marketplace.py --check
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_workbuddy_marketplace.py -v
```

Inspect the resulting diff for exactly the intended active entries, versions, descriptions, manifests, and links. Verify each manifest with the WorkBuddy-bundled CLI's `plugin validate` command. Derive the CLI path from the installed host; do not publish a personal machine path.

## Install and cold-start acceptance

Use a clean Git snapshot of the exact committed candidate. The verifier hashes files present on disk; `__pycache__`, dependency folders, or untracked drafts can cause a false mismatch or contaminate a local installation. Export the candidate with `git archive` into a fresh temporary directory and run the verifier from that snapshot. Use `PYTHONDONTWRITEBYTECODE=1` for tests, and keep test outputs outside the snapshot. Do not clean a shared dirty checkout to manufacture this baseline.

Before publication, from the clean snapshot:

```bash
python3 scripts/verify_workbuddy_install.py --cli <workbuddy-bundled-codebuddy>
```

The verifier must isolate `CODEBUDDY_CONFIG_DIR` and the test workspace, install the catalog, then invoke `plugin list --json` in a **new process**. Passing requires:

- Every expected plugin is discovered after cold start, enabled, and at its expected version.
- Each installed plugin has its standalone manifest and an accessible `skills/<name>/SKILL.md`.
- Cache paths stay inside the isolated configuration, and payload links have become real files.
- All published payload files match the clean snapshot by SHA-256, with no missing, extra, or changed files.

Use current inventory and file counts from the verifier; historical counts are not acceptance criteria. Validate generated metadata and run the affected Portfolio contracts. If the CLI is unavailable, report cold-start verification as missing evidence rather than treating metadata checks as equivalent.

## Publish and configure

Publish adapter changes only within the current authorization and the repository's short-lived-branch/PR rules; recheck the recorded remote base before merging. Existing per-Skill versions and Tags remain untouched when only wrappers and repository tooling change. Synchronize the source checkout and preserve its unrelated edits under the existing Git guard.

After merge, compare the public source against a clean snapshot of the merged commit:

```bash
python3 scripts/verify_workbuddy_install.py \
  --cli <workbuddy-bundled-codebuddy> \
  --source zjp1997720/zhijian-skills
```

When the user also requests WorkBuddy configuration, use Computer Use to add the repository source under **Skills → Bundles → Add marketplace**. Verify that the named market and expected entries are visibly present. Adding the market and installing plugins are separate actions: keep acceptance installs in the isolated configuration unless the user requested specific real installations. Report the observed auto-update setting; do not infer it from a successful add.

## Completion and evidence

Report the usable source, market name, committed revision/PR when published, metadata and test results, cold-start/plugin counts, payload hash comparison, tested OS/host version, and any requested UI configuration result. Distinguish install/discovery verification from running every Skill's behavior. Clean up task-owned temporary environments after saving necessary evidence.

The adapter-only branch does not require fabricated Skill Tags, release artwork, or launch posts. For initial evidence and the manifest-less cold-start regression, see [canonical PR #26](https://github.com/zjp1997720/zhijian-skills/pull/26), verified on 2026-09-14. Re-run acceptance for the current candidate and host; that historical result is not a new release verdict.
