# Ephemeral Codex CLI Surface

`ephemeral_codex_cli` is a manual execution Surface for a user-requested exact model. It is never an automatic Provider route and never represents a native subagent or App Thread.

## Admission

- Require `surface_intent=ephemeral_cli`, one first-position candidate, `explicit_user_request=true`, `fresh_context=true`, and `speed=standard`.
- Require current `codex exec --help` evidence for `--ephemeral`, read-only sandbox, exact model, config override, JSONL, output-last-message, and stdin prompt support.
- Require the exact model and thinking value in a current local effective model catalog. Bind combined evidence to host, Surface, model, thinking, speed, fresh context, and a timestamp; it expires after 10 minutes.
- Require `cli_authorization.user_authorized=true` and `host_policy=allowed`. A user request authorizes this run only; it does not convert manual or experimental Provider status to official terms approval. An explicit host prohibition wins.
- Reject `live_spawn_schema`, `accepted=true`, or any claim that help/catalog evidence proves native schema acceptance.

`manual_authorized` and `experimental_authorized` are per-run routing states. Registry entries remain `automatic=false` until a future reviewed Provider gate changes them.

## Dispatch and lifecycle

The compiler returns an argv array equivalent to:

```text
codex exec --ephemeral -s read-only -m <exact-model> -c model_reasoning_effort="<thinking>" --json -o <output> -
```

The caller supplies the prompt on stdin and starts each Worker in a fresh isolated directory. The lifecycle is the local process: start, collect JSONL and the output file, record the exit code, then close. CLI JSONL may expose a diagnostic thread id, but it is not a current collaboration agent or App Thread identity and cannot authorize follow-up, archive, or native release tools.

Audit against [`cli-audit-schema.json`](cli-audit-schema.json). Record requested identity separately from observed identity. If JSONL does not explicitly report the runtime model or thinking, write `observed_runtime_model=unknown` and `observed_runtime_thinking=unknown`; never copy requested values into observed fields.
