# OpenCLI Fallback

OpenCLI is an optional compatibility path. Use it only when the user explicitly asks for OpenCLI, or when the Codex Chrome plugin is unavailable and OpenCLI preflight succeeds.

## Eligibility

Run:

```bash
opencli doctor
opencli profile list
```

Continue only when the daemon, browser bridge, connected profile, ChatGPT login, and Pro picker are available. If any check fails, return to the Chrome path or mark the consultation incomplete.

The bundled wrapper is text-only:

```bash
SKILL_DIR="<path-to-installed-gpt56-sol-pro-consult>"
python3 "$SKILL_DIR/scripts/run_gpt56_sol_pro_consult.py" \
  --prompt-file /path/to/context-packet.md
```

It performs the packet safety check, opens ChatGPT, selects and verifies Pro, fills the composer, sends once, waits, extracts the latest assistant turn, and verifies the sentinel.

## Boundaries

- Do not use OpenCLI for file uploads.
- When real attachments are required and Chrome is unavailable, paste small content into the packet or stop with a clear incomplete status.
- Do not accept legacy GPT 5.5 Pro, `Pro Extended`, or base Sol `Extra High` as GPT 5.6 Sol Pro.
- Do not bypass model confirmation with `--skip-doctor` in normal use.
- Do not start a duplicate session after timeout; inspect and recover the original browser conversation first.

## Manual recovery

List or inspect the existing OpenCLI browser session, extract the complete `main` region, and pass the extract JSON to:

```bash
SKILL_DIR="<path-to-installed-gpt56-sol-pro-consult>"
python3 "$SKILL_DIR/scripts/extract_chatgpt_reply.py" \
  /path/to/extract.json \
  --sentinel GPT56_SOL_PRO_RESULT_YYYYMMDD_HHMMSS
```

A sentinel visible only in the user's prompt is not completion evidence.
