# Changelog: gpt56-sol-pro-consult

## 1.0.0 — 2026-07-24

- Publish the first governed portfolio release.
- Make the Codex Chrome plugin the default route for text, model selection, attachments, waiting, and extraction.
- Keep OpenCLI as an optional, preflight-gated text-only fallback.
- Require positive GPT-5.6 Sol and checked `Pro` evidence before submission.
- Add context-packet safety scanning, attachment bundling, model-selection tests, contract tests, and bilingual documentation.
- Keep file-chooser promise creation, menu interaction, and `setFiles` in one Chrome invocation so unresolved browser promises never cross calls.
- Reacquire and verify the composer after uploads, with one exact “Show in text field” recovery path for Markdown packet previews.
- Track `NOT_SENT`, `SENT`, and `UNKNOWN` dispatch states so browser resets cannot cause duplicate consultations.
