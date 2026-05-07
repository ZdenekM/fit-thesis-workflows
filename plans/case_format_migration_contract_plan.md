# Case Format Migration Contract Plan

Status: planned
Created: 2026-05-06

## Goal

Define and implement an explicit case-data contract for `cases/<case-id>/` and a
diagnostic-first migration workflow. The result should let operators and agents
see whether a case is in the current layout, whether it is ready for review, and
whether generated provenance can be trusted before any future structural change
depends on those assumptions.

## Audit Base

This plan is a follow-up to `plans/workflow_reliability_contract_plan.md`.

Current workflow assumptions:

- `case.md` and `current-round.txt` identify the case metadata and active round.
- Active round data lives under
  `rounds/<round-id>/{notes,inputs,extracted,work,outputs}`.
- Generated review provenance lives in ignored round workspaces, mainly
  `work/review_manifest.json`, `work/agent_coverage.json`, reusable JSONL
  evidence files, and reviewed output hashes.
- `scripts/case-doctor` summarizes state but does not report format level,
  target format, migration need, or migration safety.
- Many workflow helpers currently assume current layout directly. Future
  structure changes should be handled by explicit diagnostics and migrations,
  not long-lived compatibility branches in normal helper code.

Constraints:

- Keep all private case inputs, PDFs, code submissions, notes, generated outputs,
  caches, and migration logs under ignored `cases/`.
- Tracked tests must use anonymized synthetic fixtures only.
- Do not migrate real private cases during implementation.
- Do not preserve compatibility with older `~/code/diplomky` workflows unless
  explicitly requested.
- Prefer explicit migrations over compatibility layers in normal workflow code.
- `scripts/check-case-format` must be strictly read-only. `migrate-case
  --dry-run` is case-data non-mutating: it may write only a migration plan/log
  under a fixed ignored path such as `work/migrations/<run-id>/`, and must not
  rewrite `case.md`, `current-round.txt`, round directories, inputs, extracted
  text, work evidence, or outputs.
- Do not introduce brittle free-text heuristics. Migration and readiness
  decisions must use file layout, structured metadata, manifests, hashes,
  explicit operator configuration, typed evidence classes, or agent-produced
  structured artifacts.
- Windows remains supported: new operator commands need Python/Pants/PEX command
  surfaces and generated `.cmd`/`.ps1` launchers.
- Run Pants commands sequentially.
- Use Serena for non-trivial Python navigation when practical.
- Use `pants run :omen` as developer-hygiene evidence on implementation slices;
  do not make it a case-pipeline gate.

## Contract Levels

`layout_current`

- The case has the current directory shape:
  `case.md`, `current-round.txt`, and
  `rounds/<round-id>/{notes,inputs,extracted,work,outputs}`.
- Required metadata labels are structurally parseable.
- The active round can be resolved without guessing from free-form text.
- This level says only that the layout is current; it does not say the round is
  ready for supervisor or opponent review.

`review_ready`

- `layout_current` holds.
- The active round has the required assignment and reviewer-profile context for
  the requested workflow.
- Supervisor-specific readiness still goes through `scripts/check-supervisor-ready`.
- Opponent/internal readiness still goes through `scripts/check-round-ready`.
- Missing required inputs are explicit blockers; advisory evidence warnings do
  not become review conclusions.

`provenance_ready`

- `review_ready` holds for the relevant workflow.
- `scripts/init-review-manifest --run-checks` has recorded current inputs and
  checks.
- `scripts/check-agent-coverage` passes when role coverage is required, or the
  manifest records typed limitations.
- `scripts/check-review-manifest --require-complete` passes for the artifacts
  that downstream workflow will rely on.
- Reviewed outputs and reusable evidence artifacts have current hashes and no
  private tracked-path leaks.

## Supported Formats

Target format:

- `case-format-v1`: the current layout described by `layout_current`.

Supported source formats for this plan:

- `case-format-v1`: already current; detector and migration planner must report
  no migration needed.
- one anonymized legacy fixture format introduced by this plan after the first
  detector slice names it explicitly. Until that fixture exists, the migration
  planner may not claim support for a historical layout.

Unsupported formats:

- unknown, unversioned, partially recognized, or ambiguous layouts are
  diagnostics only. The tooling may report blockers and suggested manual
  inspection, but it must not invent a migration plan from filename or raw text
  patterns.
- Real private cases may be inspected only by read-only diagnostics unless the
  operator explicitly runs a reviewed migration command after dry-run semantics
  have landed.

## Scope

In scope:

- define a pure case-format detector for the current layout;
- add `scripts/check-case-format` as a read-only diagnostic command;
- add `case-doctor` format diagnostics: current level, target level, migration
  needed, blockers, and next operator command;
- add a case-data non-mutating `scripts/migrate-case --dry-run` that writes an
  operator plan and log under `work/migrations/<run-id>/` in the ignored case
  workspace;
- add anonymized old-format and current-format fixtures;
- add deterministic tests for detector, diagnostics, dry-run output, idempotence
  planning, and private-path safety;
- package any new operator command through the standard workflow command
  surface.

Out of scope:

- bulk write migrations before the read-only dry-run contract is stable;
- migrating real private cases in this rollout;
- keeping normal workflow helpers compatible with every historical case shape;
- changing supervisor or opponent artifact content;
- changing generated review-provenance semantics beyond format/readiness
  diagnostics;
- executing submitted student code.

## Slices

### Slice 1 - Plan Review And Current-Layout Detector

- Status: pending
- Proposed commit message: `docs(workflow): plan case format migration work`
- Expected paths:
  - `plans/case_format_migration_contract_plan.md`
  - `src/thesis_review_workflow/case_format.py`
  - `tests/test_case_format.py`
- Tasks:
  - Review this plan with agents before implementation.
  - Scan `WORKFLOW_MEMORY.md` and promote only relevant active lessons into this
    plan or operator docs; do not treat memory as a second instruction system.
  - Define typed results for `layout_current`, `review_ready`, and
    `provenance_ready`.
  - Add pure detector coverage for valid current layout, missing active round,
    missing required directories, invalid `current-round.txt`, and ambiguous
    metadata.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_case_format.py`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 2 - Check Case Format Command

- Status: pending
- Proposed commit message: `feat(workflow): add case format diagnostics`
- Expected paths:
  - `scripts/check-case-format`
  - `scripts/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/check_case_format.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-check-case-format`
- Tasks:
  - Add the operator command and package it through the standard workflow tool
    contract.
  - Print exact format level, blockers, warnings, and next command.
  - Keep the command read-only and case-neutral.
  - Add smoke and deterministic tests.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_case_format.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-check-case-format`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 3 - Case Doctor Format Diagnostics

- Status: pending
- Proposed commit message: `feat(workflow): report case format in doctor`
- Expected paths:
  - `src/thesis_review_workflow/case_doctor_summary.py`
  - `src/thesis_review_workflow/cli/case_doctor.py`
  - `tests/test_case_doctor_summary.py`
  - `scripts/smoke-case-doctor`
- Tasks:
  - Add format-level output to `case-doctor`.
  - Keep `case-doctor` diagnostic; required missing inputs remain enforced by
    readiness and closeout commands.
  - Test that diagnostics do not infer workflow state, readiness, role routing,
    evidence status, output wording, thesis quality, or review conclusions from
    file names or raw document text.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_case_doctor_summary.py tests/test_case_format.py`
  - `scripts/smoke-case-doctor`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 4 - Case-Data Non-Mutating Migration Dry Run

- Status: pending
- Proposed commit message: `feat(workflow): plan case migrations read-only`
- Expected paths:
  - `scripts/migrate-case`
  - `scripts/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/migrate_case.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/case_migration.py`
  - `tests/test_case_migration.py`
  - `scripts/smoke-migrate-case`
- Tasks:
  - Implement `migrate-case --dry-run` before any write mode.
  - Write the operator plan and migration log only under
    `work/migrations/<run-id>/` in the ignored case workspace.
  - Prove that dry run does not rewrite `case.md`, `current-round.txt`, round
    directories, inputs, extracted text, work evidence, or outputs.
  - Include planned backup paths but do not create backups in dry run.
  - Prove idempotent planning for already-current cases.
  - Keep `--case`, `--from`, and `--to` semantics explicit; defer `--all` and
    write mode until a later slice or plan review approves them.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_case_migration.py tests/test_case_format.py`
  - `scripts/smoke-migrate-case`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 5 - Documentation, TODO Reconciliation, And Archive

- Status: pending
- Proposed commit message: `docs(workflow): close case format migration plan`
- Expected paths:
  - `README.md`
  - `TODO.md`
  - `plans/case_format_migration_contract_plan.md`
  - `plans/archive/case_format_migration_contract_plan.md`
- Tasks:
  - Update operator documentation only for the command surfaces that actually
    landed.
  - Reconcile TODO to preserve write/bulk migration only if still deferred.
  - Run final hygiene including Omen.
  - Archive this plan after final audit.
- Verification:
  - `pants fmt ::`
  - `pants lint ::`
  - `pants check ::`
  - `pants test tests::`
  - `scripts/smoke-check-case-format`
  - `scripts/smoke-case-doctor`
  - `scripts/smoke-migrate-case`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git status --short --untracked-files=all`
  - `pants run :omen`
  - `git diff --check`

## Deferred TODO Items

- Write-mode `migrate-case`, backups, and bulk `migrate-cases` are deferred
  until the dry-run contract is reviewed against real operator needs. This
  residual must remain in `TODO.md` if this plan archives before implementing
  write or bulk migration.
- Native Windows runtime proof remains a separate command-surface verification
  task unless a Windows CI or manual run is added during this plan.
- Supervisor preflight and closeout are handled by
  `plans/supervisor_workflow_closeout_plan.md`.

## Progress

- Not started.

## Decision Log

- 2026-05-06: Started as a follow-up to the workflow reliability contract plan.
  The first migration surface must be read-only and diagnostic so the repo does
  not add compatibility branches or silently rewrite private cases.

## Final Audit

Not run yet.
