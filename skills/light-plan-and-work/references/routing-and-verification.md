# Routing and verification

## Escalation test

Escalate because coordination cost, ambiguity, or consequence is high. Task length alone is not a heavy condition.

Use a heavy workflow when one or more signals are present:

- an operation is destructive or difficult to recover;
- production data, authentication, billing, security, legal, or compliance is in scope;
- the work changes a public API, performs a migration, or coordinates a release;
- architecture spans multiple systems or repositories;
- multiple agents, teams, owners, or approvers need a durable shared contract;
- inspection cannot resolve acceptance criteria without a material product or business choice;
- the user explicitly requests a full specification, detailed implementation plan, or Compound Engineering.

Before switching, keep read-only findings and completed safe work. Pause only mutations affected by the heavy condition. The heavier plan should make migration, verification, rollback, ownership, and approval boundaries explicit when relevant.

## Specialist and discovery routes

- Use a specialist Skill when it owns the artifact: Skill creation, slides, course compilation, deep research, publication, or another defined production workflow.
- Use `brainstorming` when direction benefits from open exploration.
- Use `batch-grill-me` when many user decisions can be asked in dependency-aware batches.
- Return to `light-plan-and-work` after direction and acceptance criteria are settled.

## Plan quality

A useful step names an observable change or proof:

> Update the project-level prototype workflow so it never creates branches, then run a Git-side-effect check.

Avoid activity labels such as “think about the prototype.” Replace obsolete steps when evidence changes instead of preserving a fictional sequence.

## Verification matrix

- Knowledge work: factual consistency, requested structure, audience, path, and delivery readiness.
- Documents or content: required sections, claims, references, rendering, and export when relevant.
- Code or configuration: targeted tests, lint or type checks, smoke run, diff, and side-effect audit.
- Repository work: status, intended file set, secrets and temporary-file scan, plus remote divergence before publishing.

A passing command proves only the contract it checks. Record unverified assumptions as residual risk.

## Handoff contract

Lead with the outcome, then include changed files or artifacts, verification performed, and any residual risk or intentional deferral. Do not append an unrelated menu of next steps when the requested outcome is complete.
