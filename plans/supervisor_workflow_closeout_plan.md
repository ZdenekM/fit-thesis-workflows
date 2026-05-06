# Supervisor Workflow Closeout Plan

Status: planned
Created: 2026-05-06

## Goal

Add transparent supervisor-feedback preflight and closeout bundles comparable to
the opponent workflow, without changing the content policy for student-facing
feedback. The result should make missing inputs, stale provenance, role-coverage
gaps, feedback-language errors, and repo hygiene failures visible before a
supervisor feedback artifact is treated as ready.

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

Current gap:

- Supervisor feedback has required gates in instructions, but no single
  transparent operator command equivalent to opponent preflight/closeout.
- Required checks are easy to run inconsistently after a multi-agent feedback
  loop.
- Case-format diagnostics are not implemented yet; this plan should depend on
  them only where useful and must not block on the migration implementation.

Constraints:

- Do not generate or rewrite student-facing feedback in this plan.
- Do not loosen the existing generated-artifact review loop.
- Do not infer readiness from raw thesis/code text substring matches.
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
- `scripts/check-assignment-coverage <case-id> [round-id]`, which produces an
  advisory map for reviewer verification and must not become an automatic
  assignment-fulfillment verdict;
- `scripts/check-evidence-presence <case-id> [round-id]`, which records missing
  or present-but-uninspected evidence as review risk, not as proof that a claim
  is false;
- `scripts/check-evaluation-claims <case-id> [round-id]`, which warns about
  metric/evaluation evidence gaps and semantic sanity risks; failures caused by
  missing required source material should be surfaced as preflight blockers only
  through the required-input/readiness path;
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

Supervisor closeout should print every underlying command before running it and
show pass/fail status for each one.

## Scope

In scope:

- add `scripts/supervisor-preflight`;
- add `scripts/supervisor-closeout`;
- package both commands through the standard workflow tool surface;
- add deterministic tests for command planning, hard/warn semantics, and command
  ordering;
- add smoke tests with anonymized synthetic cases;
- update README and supervisor skills with the new command names after they
  exist;
- keep supervisor deadline maintenance as a recurring data task.

Out of scope:

- case-format detector or migration implementation;
- changing generated feedback wording policy;
- changing reviewer-profile or deadline data;
- executing submitted student code;
- replacing the required independent review loop for sendable feedback;
- making advisory assignment/evidence checks into grading or quality
  conclusions.

## Slices

### Slice 1 - Plan Review And Command Planner

- Status: pending
- Proposed commit message: `docs(workflow): plan supervisor closeout work`
- Expected paths:
  - `plans/supervisor_workflow_closeout_plan.md`
  - `src/thesis_review_workflow/supervisor_checks.py`
  - `tests/test_supervisor_checks.py`
- Tasks:
  - Review this plan with agents before implementation.
  - Scan `WORKFLOW_MEMORY.md` and promote only relevant active lessons into this
    plan or supervisor docs/skills; do not treat memory as a second instruction
    system.
  - Add a pure command planner for preflight and closeout steps.
  - Encode hard versus diagnostic steps as typed data, not stringly shell
    control flow.
  - Test command ordering and required hard gates.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_supervisor_checks.py`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 2 - Supervisor Preflight Command

- Status: pending
- Proposed commit message: `feat(workflow): add supervisor preflight`
- Expected paths:
  - `scripts/supervisor-preflight`
  - `scripts/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/supervisor_preflight.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `tests/test_supervisor_checks.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-supervisor-preflight`
- Tasks:
  - Implement the command from the typed preflight plan.
  - Hard-fail on supervisor readiness and required missing inputs.
  - Print diagnostic `case-doctor` status without replacing readiness checks.
  - Run assignment coverage, evidence presence, and evaluation-claim diagnostics
    after readiness and before role packets so agents can use advisory evidence
    without treating it as a verdict.
  - Prepare code workspace only when code evidence exists and static review
    needs inspectable source.
  - Package the command and add smoke coverage.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_supervisor_checks.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-supervisor-preflight`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 3 - Supervisor Closeout Command

- Status: pending
- Proposed commit message: `feat(workflow): add supervisor closeout`
- Expected paths:
  - `scripts/supervisor-closeout`
  - `scripts/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/supervisor_closeout.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `tests/test_supervisor_checks.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-supervisor-closeout`
- Tasks:
  - Implement closeout as an ordered bundle of existing required gates.
  - Hard-fail on readiness, manifest update, required agent coverage, manifest
    completeness, feedback language/output, private checks, script checks, and
    whitespace hygiene.
  - Print the exact commands and pass/fail status.
  - Keep Omen and other dev-hygiene targets outside the case closeout command.
  - Package the command and add smoke coverage.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_supervisor_checks.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-supervisor-closeout`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 4 - Documentation, TODO Reconciliation, And Archive

- Status: pending
- Proposed commit message: `docs(workflow): close supervisor workflow plan`
- Expected paths:
  - `README.md`
  - `.agents/skills/thesis-supervisor-feedback/SKILL.md`
  - `.agents/skills/thesis-supervisor-feedback-review/SKILL.md`
  - `TODO.md`
  - `plans/supervisor_workflow_closeout_plan.md`
  - `plans/archive/supervisor_workflow_closeout_plan.md`
- Tasks:
  - Update supervisor workflow docs and skills to use the new preflight and
    closeout commands.
  - Keep deadline maintenance as recurring data work unless verified deadline
    data was changed.
  - Reconcile TODO for only the completed supervisor closeout scope.
  - Run final hygiene including Omen.
  - Archive this plan after final audit.
- Verification:
  - `pants fmt ::`
  - `pants lint ::`
  - `pants check ::`
  - `pants test tests::`
  - `scripts/smoke-supervisor-preflight`
  - `scripts/smoke-supervisor-closeout`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git status --short --untracked-files=all`
  - `pants run :omen`
  - `git diff --check`

## Deferred TODO Items

- Case-format detection and migration are handled by
  `plans/case_format_migration_contract_plan.md`.
- Deadline-source updates remain recurring data maintenance.
- Evidence-resolved wording checks should be considered after closeout makes the
  supervisor workflow easier to validate mechanically.
- Student-code sandbox execution remains a separate safety-model plan.

## Progress

- Not started.

## Decision Log

- 2026-05-06: Started as a follow-up to the workflow reliability contract plan.
  The closeout command should bundle existing supervisor gates rather than
  weakening the generated-artifact review loop or adding new feedback content
  policy.

## Final Audit

Not run yet.
