# Supervisor Workflow Closeout Plan

Status: superseded
Created: 2026-05-06
Superseded: 2026-05-15 by `plans/review_pipeline_optimization_plan.md`

## Goal

Add transparent supervisor-feedback preflight and closeout bundles comparable to
the opponent workflow, without changing the content policy for student-facing
feedback. This standalone supervisor-only command family is superseded by the
shared `review-round-start` / `prepare-review-round` /
`review-round-closeout` path in `plans/review_pipeline_optimization_plan.md`.

## Audit Base

This plan is a follow-up to `plans/workflow_reliability_contract_plan.md`.

Current supervisor surfaces:

- `scripts/check-supervisor-ready <case-id> [round-id]` verifies assignment,
  deadline, work type, reviewer profile, and student-feedback language context.
- `scripts/case-doctor <case-id> [round-id]` gives a read-only diagnostic
  snapshot, but it is not a replacement for required workflow gates.
- `scripts/init-review-manifest --run-checks <case-id> [round-id]` records
  current inputs, checks, skills, artifacts, and hashes.
- `scripts/check-agent-coverage <case-id> [round-id]` validates required
  multi-agent role coverage when the manifest says coverage is required.
- `scripts/check-review-manifest --require-complete <case-id> [round-id]`
  validates reviewed artifact provenance.
- `scripts/check-feedback-language <case-id> [round-id]` and
  `scripts/check-feedback-output <case-id> [round-id]` validate the final
  student-facing supervisor feedback shape.

Current gap, preserved here only as superseded context:

- Supervisor feedback has required gates in instructions, but no single
  transparent operator command equivalent to opponent preflight/closeout.
- Required checks are easy to run inconsistently after a multi-agent feedback
  loop.
- Case-format diagnostics are not implemented yet; this plan should depend on
  them only where useful and must not block on the migration implementation.

Constraints:

- Do not generate or rewrite student-facing feedback in this plan.
- Do not loosen the existing generated-artifact review loop.
- Do not infer readiness or semantic evidence state from raw thesis/code text
  substring matches. Free-form text interpretation belongs in agent-produced
  structured artifacts; deterministic preflight and closeout code should validate
  those artifacts and keep any remaining lexical checks advisory.
- Keep advisory diagnostics separate from hard gates.
- Keep all private case data and generated artifacts under ignored `cases/`.
- New operator commands need Python/Pants/PEX packaging and generated
  `.cmd`/`.ps1` launchers.
- Run Pants commands sequentially.
- Use Serena for non-trivial Python navigation when practical.
- Use `pants run :omen` as developer-hygiene evidence on implementation slices;
  do not make it a case-pipeline gate.

## Hard And Diagnostic Semantics

Supervisor preflight should hard-fail on:

- `scripts/check-supervisor-ready <case-id> [round-id]`;
- missing or unreadable active case/round paths;
- missing required assignment/profile/deadline context;
- code-workspace preparation errors when code evidence exists and the workflow
  requires inspectable code before agent review.

Supervisor preflight should treat as diagnostic or warning:

- `scripts/case-doctor` findings unless they identify required missing inputs;
- `scripts/check-assignment-coverage <case-id> [round-id]`, which validates an
  agent/human-authored map for reviewer verification and must not become an
  automatic assignment-fulfillment verdict;
- `scripts/check-evidence-presence <case-id> [round-id]`, which validates an
  agent/human-authored evidence-requirements artifact and writes structural
  media inventory without turning missing evidence into proof that a claim is
  false;
- `scripts/check-evaluation-claims <case-id> [round-id]`, which validates an
  agent/human-authored quantitative-claims artifact for reviewer verification
  and must not infer metric meaning from raw thesis text;
- optional tooling availability that is irrelevant to the current round;
- advisory assignment/evidence warnings that require reviewer interpretation.

Supervisor closeout should hard-fail on:

- `scripts/check-supervisor-ready <case-id> [round-id]`;
- `scripts/init-review-manifest --run-checks <case-id> [round-id]`;
- `scripts/check-agent-coverage <case-id> [round-id]` when role coverage is
  required;
- `scripts/check-review-manifest --require-complete <case-id> [round-id]`;
- `scripts/check-feedback-language <case-id> [round-id]`;
- `scripts/check-feedback-output <case-id> [round-id]`;
- `scripts/check-private`;
- `scripts/check-scripts`;
- `git diff --check`.

Supervisor closeout should consume structured provenance prepared by
`scripts/init-review-manifest --run-checks`, not parse review-agent prose. The
active shared plan owns the canonical supervisor-feedback approval path and the
generic closeout dispatcher contract.

Supervisor closeout should print every underlying command before running it and
show pass/fail status for each one.

## Superseded Scope

No slices in this plan are active. The shared review-pipeline plan owns the
replacement command surface:

- `review-round-start` for deterministic import, freshness, extraction, trace,
  and readiness-gate preparation;
- `prepare-review-round` for role-plan, packet, wave, and role-progress
  preparation before semantic agents run;
- `review-round-closeout` for manifest, role coverage, approval-record,
  profile-output, privacy, script, and whitespace gates.

Remaining supervisor-specific diagnostics should be implemented as profile
adapters under that shared command surface, not as a separate
`supervisor-preflight` / `supervisor-closeout` family.

## Deferred TODO Items

- Case-format detection and migration are handled by
  `plans/case_format_migration_contract_plan.md`.
- Deadline-source updates remain recurring data maintenance.
- Evidence-resolved wording checks should be considered after closeout makes the
  supervisor workflow easier to validate mechanically.
- Student-code sandbox execution remains a separate safety-model plan.

## Progress

- 2026-05-15: Superseded before implementation by
  `plans/review_pipeline_optimization_plan.md` Slice 1. The generic review
  pipeline now owns `review-round-start`, `prepare-review-round`, and
  `review-round-closeout`; no parallel supervisor-only command family should be
  implemented from this plan.

## Decision Log

- 2026-05-06: Started as a follow-up to the workflow reliability contract plan.
  The closeout command should bundle existing supervisor gates rather than
  weakening the generated-artifact review loop or adding new feedback content
  policy.
- 2026-05-15: Superseded by the shared review pipeline to avoid duplicating
  supervisor-only closeout ownership next to opponent and supervisor-report
  closeout dispatchers.

## Final Audit

- Superseded without implementation. Remaining supervisor-feedback closeout
  work is carried by `plans/review_pipeline_optimization_plan.md`; deadline
  data maintenance remains in `TODO.md`.
