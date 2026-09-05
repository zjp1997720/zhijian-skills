# codex-model-routing-team Changelog

## Unreleased

## 3.1.0 - 2026-09-05

- Default ordinary execution to native Sol Medium Standard; route complex/high-risk work to Sol High, critical review to Sol XHigh, and mechanically verifiable batches to Luna XHigh.
- Add a registry-driven stdin RoutePlan compiler that returns validated dispatch arguments without creating Workers.
- Keep live capability evidence separate from App task authorization and reject risk-inappropriate reasoning overrides.
- Reuse approved upstream plans and reduce duplicate lead work while preserving Provider, lifecycle, attempt and external-action boundaries.
- Add deterministic compiler and routing coverage; no claim of measured speed or cost superiority over Luna.


## 3.0.0 - 2026-08-16

- Change the automatic route from Luna App threads to native Multi-Agent V2 Luna leaf Workers: XHigh Standard by default, Max for high-risk or high-ambiguity units.
- Add RoutePlan v3 with `surface_intent`, explicit native `fork_turns`, tuple-bound context evidence, and completion-only compatibility for v2.1 runs.
- Reserve App threads for worktrees, sidebar visibility, cross-task recovery, and durable supervision; durable fallback chains cannot leave the App surface.
- Replace mandatory native close with the `RELEASED` lifecycle, using live close when available or verified completed-idle release when it is not.
- Keep Fast live-gated: Standard native evidence does not invent speed/service-tier fields; Fast requires explicit priority capability evidence.
- Document the official Codex leaf-model support source and deliberately keep the orchestrator free of `model: luna` frontmatter.

- Separate Fast eligibility from model policy: Standard remains the default without live priority evidence; Sol and Terra also require an explicit user request for Fast.
- Replace the fixed 6/8/3 ceiling with registry-backed TeamPlan profiles: conservative `standard` remains the default, while justified, ownership-isolated, host-confirmed `expanded` runs may use 12 concurrent Workers, 16 root attempts, and 6 new Workers per wave with at least two reserved slots.
- Add a lightweight TeamPlan compiler and dependency-free validator before every two-or-more-Worker dispatch, covering dependencies, same-wave ownership conflicts, budgets, integration order, and lead-only final verification.
- Compile CE Plans, Codex Plans, and upstream Skill decompositions without rewriting them; keep two-to-three-unit micro plans in context and persist only durable four-plus-Worker or resumable runs.
- Bind Worker ledger entries to `team_plan_revision` and `unit_id`, reject mid-wave structural revisions and plan-external Workers, and warn when valid units remain undispatched.
- Replace vague complexity activation with a net-benefit gate that preserves the quality floor and compares expected time or model-cost savings against coordination cost.
- Make `speed` a versioned RoutePlan dimension with backward-compatible legacy Standard behavior.
- Require tuple-bound live speed evidence for every Fast route while preserving separate requested/accepted/observed speed audit fields.
- Slim initial Skill/interface context from 1708 to 890 estimated tokens by keeping only triggers, branch selection, the shared execution skeleton, hard gates, and the output contract; defer detailed policy and lifecycle rules to existing references.

## 2.1.0 — 2026-07-27

- Add a `native-light` profile for bounded OpenAI native Workers: load only relevant policies, keep coordination state in memory, and avoid `agent_team/` files.
- Keep recovery, worktree, independent history, high-risk approval, cross-Provider, and fallback work on the fully governed path; duration and file count are now signals rather than standalone App Thread triggers.
- Accept RoutePlan and ledger JSON from stdin while preserving existing file-path validation and all model, Provider, attempt, identity, and lifecycle gates.

## 2.0.0 — 2026-07-27

- Upgrade the Thread-only router into a dual-surface router: exact-model native subagents for bounded parent-integrated work and Codex App threads for durable, recoverable, worktree, or audit-heavy work.
- Add live native spawn confirmation, V1/V2 fresh-context rules, separate requested/accepted/observed model identity, native close gates, and mixed-surface ledger validation.
- Bind native runtime evidence to host/Surface/model/thinking with a 10-minute TTL; Responses semantic probes cannot authorize native spawn routes.
- Reject non-boolean authorization fields, mismatched native identity, inherited context, unclosed completed agents, and inconsistent legacy/canonical attempt counters.
- Add explicit `surface` RoutePlan candidates with backward-compatible omission defaulting to `app_thread`; cross-surface fallback remains deterministic and predeclared.
- Add native Sol low/medium/high profiles. Register `gpt-5.6-terra` as opt-in, first-candidate-only, default-off, and never a silent fallback.
- Preserve the existing Luna/Sol/Grok/Gemini provider policy, one- or two-candidate ceilings, Thread recovery invariants, and upstream Skill stage gates.

### Additional 2.0.0 release details

- Replace the two-model hardcoded policy with a registry-driven four-model policy covering Luna, Sol, conditional Grok 4.5, and a provider-blocked Antigravity Gemini entry that preserves a future official-route template.
- Add provider/data-boundary gates, deterministic candidate chains, scoped circuit breakers, and a two-Worker recovery ceiling.
- Add dependency-free model and RoutePlan validators for registry/runtime evidence, optional semantic nonces, ordered fallbacks, Provider allowlists, and minimum thinking.
- Add a single audit schema with conservative creation-attempt accounting and backward-compatible `model` records.
- Expand contract tests and evaluation cases for provider quota, semantic mismatch, MCP isolation, and explicit Gemini routing.
- Add a minimal Thread supervision state model inspired by FirstMate's authoritative-state and reconciliation contracts, without importing its terminal fleet runtime.
- Support queued `pendingWorktreeId` creation through unique task-id discovery and stable official observations; ambiguous zero/multiple matches now remain `UNKNOWN` and block follow-up, fallback, duplicate creation, and archival.
- Add task-intent mutation boundaries, durable resume ordering, a dependency-free team-ledger validator, and focused regression coverage for state truth, pending recovery, archive gates, and duplicate prevention.

## 1.0.4 — 2026-07-26

- Admit `gpt-5.6-sol` with `medium` thinking for explicit single-candidate RoutePlans after live runtime support is confirmed.
- Keep default task profiles at their existing `high` or stronger minimum; the new level never silently downgrades automatic routing.

## 1.0.3 — 2026-07-26

- Allow a one-candidate RoutePlan to declare `max_worker_threads: 1` when failure returns directly to the lead Agent.
- Require the Worker ceiling to match the declared candidate count, preventing undeclared fallback capacity.

## 1.0.2 — 2026-07-17

- Publish and install exclusively through `zjp1997720/zhijian-skills`.

## 1.0.1 — 2026-07-17

- Add a brand-aligned light README hero and clearer bilingual first-screen guidance.
- Preserve the existing Codex App model-routing contract and runtime behavior.

## 1.0.0 — 2026-07-16

- Establish the first independently versioned governance baseline.
- Preserve explicit Codex App model routing, bounded concurrency, task packets, and lifecycle contracts.
