---
name: light-plan-and-work
description: Create a 3–7 step plan for a bounded task, execute immediately, verify, and hand it back. Use when the user explicitly requests a lightweight plan-and-work flow; do not use for open-ended brainstorming, discovery, high-risk migrations, multi-system architecture, or releases.
disable-model-invocation: true
---

# Light Plan and Work

Planning and doing are one continuous workflow.

## Route before planning

Read the request, relevant project instructions, current files, and repository state. Choose one route:

- **Direct execution:** one or two obvious actions. State a one-line brief and do them; do not manufacture a plan.
- **Light plan and work:** the outcome is concrete, the scope is bounded, and 3–7 steps can complete and verify it.
- **Specialist Skill:** a narrower installed Skill owns the artifact or domain. Use it, with this Skill only as the execution wrapper when useful.
- **Discovery or brainstorming:** the user is still choosing the problem, audience, concept, story, or direction. Use a discovery Skill before planning.
- **Heavy workflow:** use the project's full specification or plan/work system when consequence, ambiguity, or coordination cost is high.

Heavy conditions include destructive or sensitive operations, migrations, public API changes, cross-system architecture, releases, multiple owners, unresolved acceptance criteria, and explicit requests for a full specification or Compound Engineering. Read [routing and verification](references/routing-and-verification.md) when the route is unclear.

## Execute

1. Lock a compact execution brief: **Goal**, **Deliverable**, **Boundary**, and **Acceptance**.
2. Resolve reversible choices yourself. Ask one blocking question only when the answer changes the outcome or requires new authority.
3. Use the host plan tracker for 3–7 observable steps, with at most one step in progress. Each step must produce or verify something.
4. Start after the plan is visible. Read before editing, preserve unrelated work, follow project instructions, and keep the plan aligned with evidence.
5. If a heavy condition appears, preserve completed safe work, pause the affected mutation, explain the evidence, and switch to the heavier workflow.
6. Verify in proportion to risk; hand back the result, artifacts, evidence, and residual risk.

Do not create a durable plan file by default. Create one only for an explicit request, future resumption, external handoff, multiple owners, or a lasting design decision, and follow the project's existing plan location.

Maintain trigger boundaries with `evals/trigger_cases.json` and output behavior with the baseline comparisons in `evals/output/cases.jsonl`.
