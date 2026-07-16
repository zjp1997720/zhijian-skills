# codex-doctor characterization

- **Trigger contract:** Codex health, `/doctor`, context pollution, broken Skills/MCP/hooks, and ignored instruction diagnosis.
- **Safety contract:** Read-only diagnosis by default; every repair requires a separate approved finding-level diff.
- **Workflow invariant:** Combine `codex doctor --json` with the bundled workspace scanner.
- **Output invariant:** Evidence-backed health findings; no silent mutation.
- **Resource graph:** `scripts/scan_workspace.py`, `references/checks-and-repair-policy.md`, `evals/evals.json`.

