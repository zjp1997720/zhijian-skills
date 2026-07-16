# Codex Model Routing Team

[中文说明](README.zh-CN.md)

Give Codex a bounded team of background tasks, each with an explicit model and reasoning level, while one lead agent keeps control of planning, integration, and verification.

## Install

The standard `skills` CLI shorthand is valid:

```bash
npx skills add zjp1997720/codex-model-routing-team
```

For a global Codex installation without symlinks:

```bash
npx skills add zjp1997720/codex-model-routing-team \
  -g -a codex --skill codex-model-routing-team --copy -y
```

The full GitHub URL works too:

```bash
npx skills add https://github.com/zjp1997720/codex-model-routing-team
```

Verify that the installed package contains both the entrypoint and its supporting policies:

```bash
npx skills ls -g -a codex
find ~/.agents/skills/codex-model-routing-team -maxdepth 2 -type f | sort
```

The file list must include `SKILL.md`, `references/routing-policy.md`, `references/task-packet.md`, and `references/thread-lifecycle.md`. If only `SKILL.md` appears, remove that incomplete installation and install the current release again.

## Activate it

Explicit activation works immediately after installation:

```text
Use $codex-model-routing-team to research these six independent topics in parallel, then verify and synthesize the findings.
```

To let Codex activate the Skill automatically for suitable complex work, add the following standing authorization to `~/.codex/AGENTS.md`. Put it in a project-level `AGENTS.md` instead when the authorization should apply only to that project.

```markdown
## Codex background model-routing authorization

- The user authorizes Codex to use `$codex-model-routing-team` automatically for complex, parallelizable tasks, create independent background tasks, and assign a model and reasoning level to each task. Before dispatch, briefly state the number of tasks, model, reasoning level, and responsibility. No additional confirmation is required.
- The lead agent keeps its current model and owns planning, file ownership, integration, verification, and final delivery.
- Run at most 6 background tasks concurrently and create at most 8 for one root task. Background tasks must not create more background tasks or subagents.
- Background tasks must not use Ultra. Terra is excluded from automatic routing by default. If Codex App background-task tools are unavailable, complete the work locally and do not use MultiAgentV2 `spawn_agent` as a substitute for model routing.
- Do not auto-dispatch simple questions, status checks, small single-file edits, strongly sequential work, publishing, sending, payment, deletion, account, or production operations.
```

This is user-configured Codex instruction, not a hidden OpenAI system prompt. Explicit `$codex-model-routing-team` requests remain available without the standing authorization.

## Why this exists

Codex's native MultiAgentV2 surface does not expose per-worker model or reasoning controls. Native subagents therefore inherit the session model, which can make parallel work unexpectedly expensive.

This Skill uses Codex App background tasks instead. The lead agent plans the work, assigns non-overlapping ownership, verifies results, and integrates the final deliverable. Each background task receives an explicit available model and reasoning level.

## What it does

- Routes only complex, genuinely parallel work such as multi-source research, multi-section content, large Skills or decks, and independent engineering workstreams.
- Uses Sol and Luna as the default routes, prohibits Ultra, and keeps Terra out of automatic routing unless evidence or the user calls for it.
- Limits fan-out to three new tasks per wave, six concurrent tasks, and eight total tasks per root request.
- Treats the first real task as a health probe, verifies every created task, prevents descendants, and archives only completed tasks whose results were adopted.
- Acts as a Thread Orchestrator for upstream workflows such as Deep Research while preserving their stages, artifacts, and quality gates.
- Keeps publishing, payments, deletion, account changes, and production mutations in the lead task.

## How it works

1. The lead agent decides whether parallel execution is worth the coordination cost.
2. It creates one real background task as a health probe and confirms that the task can be read.
3. It creates later tasks in bounded waves with explicit model, reasoning, scope, file ownership, and acceptance criteria.
4. It verifies facts and artifacts, resolves conflicts, and integrates the result.
5. It archives adopted completed tasks one at a time.

When an upstream Skill already owns decomposition, this Skill accepts its stages and task budget. It controls model routing, task lifecycle, and safety caps without rewriting the upstream workflow. Any task with a workspace output path is project-bound; only chat-only work may be projectless.

The default Deep Research budget is `2-4 researchers + 1 verifier + 1 reviewer + 2 retry slots`, within the cumulative eight-task cap.

## Example requests

```text
Use $codex-model-routing-team to implement, test, and review three independent modules without overlapping file ownership.
```

```text
Use $codex-model-routing-team to prepare a training deck with separate research, writing, and review tasks.
```

```text
Use $codex-model-routing-team as the Thread Orchestrator for $deep-research. Preserve its verifier and reviewer stages.
```

## Requirements and boundaries

- Codex App with background-task tools for project discovery, task creation, task reading, follow-up messages, and archiving.
- Access to the models and reasoning levels selected by the lead agent.
- Background task creation must be verifiable. The Skill stops delegation when a task does not materialize.
- This does not change MultiAgentV2 or make native subagents support per-agent model selection.

## Repository layout

```text
.
├── README.md
├── README.zh-CN.md
├── LICENSE
├── skills/
│   └── codex-model-routing-team/
│       ├── SKILL.md
│       ├── agents/
│       ├── evals/
│       └── references/
└── tests/
```

The agent workflow lives in [SKILL.md](skills/codex-model-routing-team/SKILL.md). Supporting policies live in [references](skills/codex-model-routing-team/references/).

## Validation

The workflow has been tested with projectless research tasks and project-bound workspace tasks, including model/reasoning verification, result collection, failure handling, and serial archival. The release is also tested through an isolated `npx skills` installation to confirm that supporting files are copied.

## License

[MIT](LICENSE)
