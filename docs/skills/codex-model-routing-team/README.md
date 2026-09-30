# Codex Model Routing Team

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="A task contract routes specified execution to GPT-6 Luna and unresolved judgment to GPT-6.1 Sol">
</p>

<p align="center"><strong>Turn independent work into verified leaf-Worker units: GPT-6 Luna executes decided work; GPT-6.1 Sol handles unresolved judgment.</strong></p>

<p align="center"><a href="./README.zh-CN.md">简体中文</a> · <a href="https://github.com/zjp1997720/zhijian-skills/tree/main/skills/codex-model-routing-team">Canonical source</a></p>

Use it only when a task has at least two independent, verifiable deliverables and the expected parallel benefit exceeds coordination cost. The lead keeps its current model and owns planning, file ownership, integration, and final verification.

## Install

```bash
npx skills add zjp1997720/zhijian-skills
```

For a global copied Codex installation:

```bash
npx skills add zjp1997720/zhijian-skills \
  -g -a codex --skill codex-model-routing-team --copy -y
```

## Requirements

- Codex native Multi-Agent V2, Codex App thread tools, or both.
- A live schema accepting the exact model, reasoning, context, and optional speed tuple before dispatch.
- Provider terms, credentials, and project data boundaries that allow each candidate.
- Current CLI help and model-catalog evidence when the user explicitly requests an experimental exact CLI model.

## Activate it

```text
Use $codex-model-routing-team to implement and test these three independent modules, then verify the integrated result.
```

Optional automatic authorization for `AGENTS.md`:

```markdown
## Codex model-routing authorization

- Automatically use `$codex-model-routing-team` only when work has at least two independent, verifiable deliverables and positive net parallel benefit.
- Brief the Worker count, surface, model, reasoning, speed, and responsibility before dispatch. The lead keeps its model and owns integration and final verification.
- For every automatic route, declare `task_contract`: whether the decision is specified and what evidence passes acceptance.
- Route specified execution to GPT-6 Luna XHigh by default and complex specified execution to Luna Max. Route unresolved judgment to GPT-6.1 Sol Medium/High, high-risk work to Sol High, and critical independent review to Sol XHigh.
- Workers are leaf-only: no Ultra, further delegation, publishing, sending, payment, deletion, account, or production changes.
```

## What it does

- Applies a net-benefit gate; simple or strongly sequential work stays with the lead.
- Compiles two or more units into a lightweight TeamPlan with dependencies, ownership, budgets, and integration order.
- Requires a `task_contract` before automatic model selection; prompt length and file count do not justify a stronger model by themselves.
- Uses GPT-6 Luna XHigh/Max for decided execution and GPT-6.1 Sol Medium/High/XHigh for unresolved, risky, or critical judgment.
- Keeps GPT-6 Astra explicit-only, Terra explicit-first-only, Grok preflight-gated, Gemini 3.6 blocked, and DeepSeek 4.1/Gemini 3.8 on an explicit manual CLI surface.
- Keeps App threads for worktrees, sidebar visibility, cross-task recovery, durable supervision, or a predeclared fallback.
- Audits requested, accepted, and observed model/speed identity separately.

## How it works

1. The lead confirms independent units and writes acceptance evidence.
2. For two or more Workers, the TeamPlan validator rejects dependency cycles, same-wave write conflicts, budget overflow, and delegated final verification.
3. `prepare_native_team.py` can compile validated native dispatch arguments and an initial ledger in one step; it never creates Workers.
4. Each Worker receives one unique task ID, exact ownership, one RoutePlan, and at most two attempts plus one follow-up.
5. Native results are released through live close or verified completed-idle state; durable App work retains pending, UNKNOWN, recovery, and archive gates.
6. The lead inspects real outputs, integrates them in order, and validates the final ledger.

```bash
python3 scripts/prepare_native_team.py --help
printf '%s' "$TEAM_PLAN_JSON" | python3 scripts/validate_team_plan.py -
printf '%s' "$ROUTE_PLAN_JSON" | python3 scripts/validate_route_plan.py -
printf '%s' "$TEAM_LEDGER_JSON" | python3 scripts/validate_team_ledger.py -
```

## Example Requests

```text
Use $codex-model-routing-team. The API contract is already decided: give three GPT-6 Luna XHigh Workers non-overlapping modules, then run the acceptance suite.
```

```text
Use GPT-6.1 Sol High to resolve the two architectural questions first; do not start implementation until the lead adopts the decisions.
```

```text
I explicitly want DeepSeek 4.1 Flash for a read-only comparison through the CLI. Verify the current CLI model catalog and use fresh context.
```

## Safety and Limitations

- Luna requires a specified decision and concrete acceptance evidence; it cannot claim high-risk or critical-review work.
- Sol never goes below Medium; Luna never goes below XHigh; Ultra is forbidden.
- Catalog eligibility is not live runtime evidence. Unsupported exact tuples must not be dispatched.
- Fast means `service_tier=priority`; without a live field, the route remains Standard.
- Exact CLI routes are explicit, read-only, fresh-context, non-automatic, and cannot replace native/App lifecycle evidence.
- No measured speed or cost advantage is claimed.

## Validation

The release runs 82 routing tests covering task contracts, Luna/Sol admission, native quick preparation, CLI exact-model boundaries, Provider gates, live tuples, speed, TeamPlan ownership, attempts, lifecycle, recovery, and isolated installation.

## License

[MIT](../../../skills/codex-model-routing-team/LICENSE)
