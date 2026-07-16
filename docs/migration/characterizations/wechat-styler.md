# wechat-styler characterization

- **Trigger contract:** Convert Markdown to WeChat-compatible inline HTML; component mode is opt-in.
- **Workflow invariant:** Pure layout remains the default; themes, components, SVG intro animation, image pipeline, OpenCLI injection, and publishing remain explicit capabilities.
- **Output invariant:** One publishable HTML file with no external CSS dependency.
- **Runtime invariant:** Existing Node test suite and package lock remain authoritative.
- **Resource graph:** `scripts/`, `references/`, `themes/`, `agents/openai.yaml`, and deterministic tests.

