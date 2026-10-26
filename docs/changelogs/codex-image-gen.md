# codex-image-gen Changelog

## 1.1.0 — 2026-10-26

- Separate the edit canvas (`--image`) from guidance images (`--reference-image`) and label each image's role in the request.
- Write a run manifest next to every image and add `--continue-from` to keep editing the previous result with its reusable references; fall back to the manifest folder when files were moved together.
- Add `--name` for predictable output names that never overwrite (`-2`, `-3` suffixes), and add a random suffix to default names so parallel runs of the same prompt cannot collide.
- Add `--response-model` (default `gpt-6-astra`) and an actionable error when the account cannot use the dispatcher model.
- Add `references/prompting.md`: three-layer prompts for covers, posters, and slides, exact-text rules, and distinct avatar series.
- Document measured server behavior: the Codex channel echoes `gpt-image-2-codex` with `quality` and `size` set to `auto`.
- Cover labeling, naming, and continuation in the test suite.

## 1.0.0 — 2026-08-18

- Publish the first independently governed Portfolio release.
- Reuse the local Codex CLI OAuth login (`~/.codex/auth.json`) to generate and edit images from any bash/python-capable Agent, without an OpenAI API key.
- Refresh expired access tokens with the single-use refresh token and write them back with `0600` permissions.
- Call the Codex Responses endpoint with the required `User-Agent`, `originator`, and `ChatGPT-Account-ID` headers, and parse the SSE stream for `image_generation_call.result` with partial-image fallback.
- Support text-to-image, image editing, repeatable reference images, three aspect presets, and three quality levels through one stdlib-only script.
- Add deterministic argument, request-body, SSE-parsing, JWT-expiry, auth-file, and CLI contract tests.
