# codex-skill-admin characterization

- **Trigger contract:** Audit, enable, disable, restore, and verify local Codex Skills.
- **Safety contract:** Use the official app-server protocol; never rewrite Skill frontmatter or uninstall plugins without explicit authorization.
- **Workflow invariant:** Start a temporary local app-server and call the supported Skill configuration API.
- **Output invariant:** Explicit inventory and change results with a dry-run path for disabling.
- **Resource graph:** `scripts/codex_skill_admin.py`, `references/app-server-protocol.md`, and agent metadata.

