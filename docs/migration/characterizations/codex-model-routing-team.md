# codex-model-routing-team characterization

- **Trigger contract:** Route complex parallel Codex work to independently configured background tasks.
- **Boundary:** Never use native `spawn_agent` as a model-routing substitute; simple or destructive tasks do not auto-dispatch.
- **Workflow invariant:** Main Agent plans, assigns, validates, integrates, and archives bounded Worker tasks.
- **Output invariant:** Traceable task packets, model/thinking choices, lifecycle state, and integrated evidence.
- **Resource graph:** routing, task-packet, lifecycle, durable-mode, upstream-adapter, validation references, and agent metadata.

