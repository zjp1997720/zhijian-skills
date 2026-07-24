---
name: gpt56-sol-pro-consult
description: Use ChatGPT Web's GPT 5.6 Sol Pro as a verified second-opinion partner for difficult planning, architecture, debugging, business, product, content-strategy, risk-review, and Skill-design work. Use when the user asks for GPT 5.6 Sol Pro, ChatGPT Pro, a deeper outside judgment, or a file-grounded review. Default to the Codex Chrome plugin for text, model selection, file uploads, waiting, and extraction. Use OpenCLI only when the user explicitly requests it or the Chrome plugin is unavailable and OpenCLI passes preflight.
---

# GPT 5.6 Sol Pro Consult

Ask GPT 5.6 Sol Pro to review a difficult problem with the evidence it needs, then bring the result back into the local Agent workflow. Treat the answer as advisory. The local Agent owns verification, adoption, and final delivery.

## Routing contract

Use the Codex Chrome plugin by default for every consultation, including text-only requests. Read and follow the installed `chrome:control-chrome` Skill before browser work, then read [Chrome workflow](references/chrome-workflow.md).

Use OpenCLI only when one of these is true:

- The user explicitly requests OpenCLI.
- The Codex Chrome plugin is unavailable or disconnected, and `opencli doctor` confirms a working browser bridge.

When OpenCLI is eligible, read [OpenCLI fallback](references/opencli-fallback.md). Do not choose OpenCLI merely because it is installed. Do not use OpenCLI for file uploads.

If neither path is available, prepare the context packet and tell the user exactly which browser connection is missing. Never imply that a Pro consultation completed.

## Requirements

- The default path requires Codex with the Chrome plugin connected.
- The selected Chrome profile must be logged into ChatGPT Web.
- The account must expose `Pro` in the standard ChatGPT model picker.
- OpenCLI is optional and is not an installation prerequisite.

## Hard gates

### Model truthfulness

In standard ChatGPT conversations, OpenAI maps `Pro` to GPT 5.6 Sol Pro. Confirm either:

- a GPT 5.6-specific Pro test ID is checked; or
- the picker shows the `GPT-5.6 Sol` family and the exact `Pro` radio has `aria-checked=true`.

Reject legacy GPT 5.5 Pro selectors, `Pro Extended`, base Sol `Extra High`, and ambiguous `Pro` text outside the model picker. Stop if the model cannot be confirmed.

### Artifact truthfulness

ChatGPT Web cannot read a local path by itself. Upload the actual file, paste its contents, or build a text bundle. Never claim GPT inspected a file when it received only a filename, path, or summary.

### Credential hygiene

Do not send executable credentials: tokens, cookies, passwords, API keys, private keys, OAuth headers, browser profiles, or session dumps. Ordinary user-owned business and project context may be included when it materially improves the judgment.

Run the bundled scanner before submission:

```bash
SKILL_DIR="<path-to-installed-gpt56-sol-pro-consult>"
python3 "$SKILL_DIR/scripts/check_packet_safety.py" packet.md
```

## Workflow

1. Write the local Agent's best judgment before consulting Pro. Identify the decision, success standard, evidence, constraints, options, risks, attempts, and unknowns.
2. Build a restorable context packet using [the template](references/context-packet-template.md). Separate facts, local judgment, and unknowns.
3. Select the smallest evidence set that still contains the truth. Use real attachments when structure, formatting, source layout, logs, images, or implementation details matter.
4. Run the safety scanner. Remove credential-like material; keep useful project context.
5. Execute the default [Chrome workflow](references/chrome-workflow.md). Keep each file-chooser lifecycle inside one browser invocation, then reacquire and verify the composer after uploads. Use the optional [OpenCLI fallback](references/opencli-fallback.md) only when the routing contract permits it.
6. Confirm GPT 5.6 Sol Pro before sending. Verify the complete packet from the composer's rendered text, then record the model evidence, timestamp, context strategy, attachment names, sentinel, and dispatch state.
7. Wait for the complete assistant turn. A preamble or missing sentinel while the page is still generating means “not ready.” Continue or recover the same conversation; do not submit a duplicate request when Send was clicked or its outcome is uncertain.
8. Extract the complete answer, verify the sentinel, compare it with local evidence, and decide what to adopt, reject, or modify.

## Context assembly

Include:

- Exact decision or problem
- Success standard and user intent
- Relevant background and constraints
- Local judgment before consultation
- Evidence and actual artifacts
- Attempts and verbatim errors
- Meaningful options and tradeoffs
- Risks and unknowns
- Requested output: critique, decision, architecture, plan, checklist, or revision

For difficult work, prefer a structured 8,000–15,000-character packet over a short prompt that removes causal details. Ask for a concise reasoning artifact—assumptions, decision frame, evidence weighting, strongest counterargument, tradeoffs, and recommendation—without requesting hidden chain-of-thought.

## Attachments

Use attachments when the answer depends on local Skills, repositories, source files, screenshots, documents, spreadsheets, slides, PDFs, datasets, logs, or rendered output.

When a directory contains many text files, build one reviewable bundle:

```bash
SKILL_DIR="<path-to-installed-gpt56-sol-pro-consult>"
python3 "$SKILL_DIR/scripts/build_attachment_bundle.py" \
  /path/to/artifact-or-directory \
  -o /tmp/gpt56-sol-pro-attachment-bundle.md
```

List every attachment in the packet. Upload original human-readable files first; use a generated Markdown bundle when there are too many files or archives are rejected. Exclude caches, dependencies, build output, `.git`, secrets, and irrelevant binaries.

## Completion contract

A consultation is complete only when all are true:

- GPT 5.6 Sol Pro selection was verified.
- The prompt's distinctive prefix and sentinel were verified in the composer's rendered text, and every required attachment was visibly present before sending.
- The assistant stopped generating.
- The complete assistant turn was extracted.
- The expected `GPT56_SOL_PRO_RESULT_...` sentinel appears in that assistant turn.

If the user says the result is already visible, re-extract the existing conversation before retrying. Never start a duplicate while the original run may still be active.

## Local integration

Return:

```markdown
## Pro Consultation Result
- Status: completed | failed | skipped
- Model confirmed: yes | no
- Sentinel verified: yes | no
- Browser path: Codex Chrome | OpenCLI

## What GPT 5.6 Sol Pro Said
<concise summary>

## Local Adoption Decision
- Adopt:
- Reject:
- Modify:
- Reason:

## Final Answer
<the local Agent's verified recommendation or deliverable>
```

## Failure handling

- **Chrome plugin unavailable:** use OpenCLI only when its preflight succeeds; otherwise stop and report the missing connection.
- **Not logged in:** ask the user to sign in to ChatGPT Web in the selected Chrome profile.
- **Pro unavailable:** stop without silently selecting another model.
- **Attachment failed:** retry through Chrome's real file chooser, paste small content, or use one Markdown bundle. Do not claim the file was received.
- **Composer remains empty:** use the exact packet-preview action “在文本字段中显示” or “Show in text field” once when it is uniquely associated with the uploaded packet, then reacquire and verify the composer. Never send an empty or unverified packet.
- **Chrome resets around Send:** retry preparation only when Send was definitely not clicked. When it was clicked or the outcome is uncertain, recover the existing conversation and never submit a duplicate.
- **Still generating:** keep waiting in the same conversation and inspect targeted completion signals.
- **Missing sentinel after completion:** extract the complete assistant turn once more, including escaped underscores; otherwise mark the consultation incomplete.
- **Low-quality answer:** use only supported parts. The local Agent retains final judgment.
