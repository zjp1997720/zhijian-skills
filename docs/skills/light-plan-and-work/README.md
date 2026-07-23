# Light Plan and Work

**Plan bounded work in a few steps, execute it immediately, verify the result, and escalate only when the risk deserves a heavier workflow.**

[简体中文](./README.zh-CN.md) · [Canonical source](https://github.com/zjp1997720/zhijian-skills/tree/main/skills/light-plan-and-work)

## Install

```bash
npx skills add zjp1997720/zhijian-skills \
  --skill light-plan-and-work --agent codex --global --copy --yes
```

Invoke it explicitly with `$light-plan-and-work`. Automatic invocation is disabled because this Skill chooses how a task is orchestrated.

## Requirements

- An Agent Skills-compatible Harness such as Codex or Claude Code.
- A request with a concrete outcome and bounded scope.
- Access to the relevant project files and instructions when the task changes a workspace.

## What It Does

- Locks a compact execution brief: goal, deliverable, boundary, and acceptance evidence.
- Uses direct execution for trivial work and a 3–7 step plan for bounded work.
- Starts implementation immediately after showing the plan.
- Uses specialist Skills for artifacts they already own.
- Routes unresolved direction to brainstorming or discovery before execution.
- Escalates security-sensitive, destructive, cross-system, migration, multi-owner, and release work to a durable planning workflow.
- Verifies in proportion to risk and hands back concrete evidence.

## How It Works

```text
Inspect context
  → choose direct / light / specialist / discovery / heavy route
  → lock execution brief
  → plan 3–7 observable steps
  → execute continuously
  → verify proportionately
  → hand back result and evidence
```

It does not create a plan document by default. A durable plan is justified only by future resumption, external handoff, multiple owners, a lasting design decision, or an explicit user request.

## Example Requests

```text
Use $light-plan-and-work to turn these notes into a client-ready training brief, save it in the correct project, and verify the final file.
```

```text
Use $light-plan-and-work to improve this one website section, run the existing tests, and hand back the changed files.
```

```text
Use $light-plan-and-work to add this bounded CLI option, run targeted checks, and preserve unrelated work.
```

## Safety and Limitations

- Manual invocation prevents this orchestration Skill from stealing ordinary direct tasks.
- Open-ended concept selection belongs to brainstorming or discovery.
- Production migrations, authentication, billing, compliance, destructive actions, multi-system architecture, and coordinated releases require a heavier workflow.
- The Skill does not weaken repository instructions, approval boundaries, or external-action permissions.
- A passing check proves only the contract it actually evaluates; unverified assumptions remain visible in the handoff.

## Development

```bash
python3 -m unittest discover -s skills/light-plan-and-work/tests -v
```

The package also includes trigger positives, negatives, near neighbors, and baseline-vs-Skill output cases under `evals/`.

## License

[MIT](../../../LICENSE)
