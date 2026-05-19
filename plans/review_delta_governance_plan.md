# Review Delta Governance Plan

Status: active

## Goal

Make operator calibration/profile corrections, maintainer write-scope
escalations, and optional batched operator notes flow through the existing
`record-review-delta`, `record-workflow-operation`, reviewer-profile privacy,
and review closeout contracts, without adding a second review mode, ledger,
approval/hash authority, profile update command, or local-profile CI gate.

## Audit Base

- Source follow-up: `plans/archive/submission_bundle_intake_plan.md` deferred
  calibration/profile governance, maintainer write-scope reporting,
  iterative operator-note batching, and local profile audit boundaries. That
  archived plan explicitly says follow-up work must extend existing owners
  rather than create parallel ledgers or commands.
- Current delta owner:
  - `scripts/record-review-delta`
  - `src/thesis_review_workflow/cli/record_review_delta.py`
  - `src/thesis_review_workflow/review_delta.py`
  - `tests/test_review_delta.py`
  - `scripts/smoke-record-review-delta`
- Current supervisor-report delta wrapper owner:
  - `scripts/record-report-amendment`
  - `src/thesis_review_workflow/cli/record_report_amendment.py`
  - `src/thesis_review_workflow/amendments.py`
  - `tests/test_report_amendments.py`
  - `scripts/smoke-record-report-amendment`
- Current operation-trail owner:
  - `scripts/record-workflow-operation`
  - `src/thesis_review_workflow/cli/record_workflow_operation.py`
  - `src/thesis_review_workflow/operation_log.py`
  - `tests/test_operation_log.py`
- Current closeout/hash owners:
  - `scripts/review-round-closeout`
  - `scripts/init-review-manifest`
  - `scripts/check-review-manifest`
  - `src/thesis_review_workflow/review_round_closeout.py`
  - `src/thesis_review_workflow/review_manifest.py`
- Current profile/privacy owners:
  - `profiles/README.md`
  - `profiles/default.md`
  - `.gitignore`
  - `src/thesis_review_workflow/cli/check_private.py`
  - `src/thesis_review_workflow/cli/check_reviewer_profile.py`
  - `tests/test_check_private.py`
- Current operator command-surface owner:
  - `docs/workflow-command-surface.md`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `scripts/BUILD`
  - `tests/test_workflow_python_contracts.py`
- Current operator docs that already mention the delta/operation surfaces:
  - `README.md`
  - `docs/workflow-command-surface.md`
- `TODO.md` fit:
  - P0 native Windows runtime proof applies only if a workflow command is added
    or changed. This plan should avoid new operator commands; if any command is
    touched, the existing Python/Pants/PEX/launcher surface and focused coverage
    are mandatory.
  - P0 deterministic validator growth applies to any schema or checker change:
    add focused pure tests with anonymized fixtures, never real `cases/` data.
  - P2 supervisor/opponent calibration convergence remains broader later work
    after V1 workflows are exercised. This plan may create governance primitives
    that future convergence can reuse, but it must not decide convergence.
  - P2 historical opponent calibration is already represented by
    `plans/historical_opponent_calibration_plan.md` and remains blocked on
    private historical cases. This plan must not depend on, unblock, or replace
    that private pilot.
  - P2 IS export and feedback-history helpers are adjacent only through
    reviewed Markdown/report-trace boundaries; do not fold that helper work into
    this plan.
- `WORKFLOW_MEMORY.md` scan result: relevant lessons are already promoted into
  active owners: reviewer profiles are active configuration, operator wording
  feedback should calibrate private profiles or workflow rules after current
  artifact closeout, and case operations need `work/operation_log.jsonl`.
  `WORKFLOW_MEMORY.md` stays rationale only.
- Serena preflight: project `diplomky_v2` was activated for Python/Markdown.
  This execution used `get_symbols_overview` on
  `src/thesis_review_workflow/review_delta.py` and confirmed the shared delta
  schema/build/validation symbols before deciding Slice 1. Use Serena again for
  further non-trivial Python navigation during implementation slices.
- Pre-implementation agent review result: the plan has one concrete outcome and
  uses existing owners, but the reviewer identified that the
  `record-report-amendment` wrapper must stay in delta-owner scope, and that any
  Slice 4 command extension must explicitly carry command-surface paths, tests,
  and Windows packaging coverage.
- No private case data has been read for this plan. Do not inspect `cases/`
  during implementation except through synthetic fixtures or explicitly ignored
  operator commands run by the user.

## Scope

- Audit current review-delta schema and promotion-target validation before
  adding fields.
- Extend the existing review-delta record only if the audit proves the current
  fields cannot clearly express calibration/profile governance. Candidate
  extensions are:
  - `classification_reason`
  - `rejected_targets`
  - `privacy_review`
  - `profile_proposal_ref`
- Model maintainer write-scope as explicit tracked-maintenance opt-in. It may
  allow tracked workflow/docs/skills/test fixes only after maintainer consent and
  must keep `scripts/check-private` in closeout.
- Keep default colleague/operator use case-local: limitations, sanitized issue
  reports, review deltas, and operation-log events belong in the ignored round
  workspace.
- Define optional iterative operator-note batching only if needed. While open,
  the staging artifact is non-authoritative. On freeze it must emit existing
  `work/review_deltas/*.json` records and `work/operation_log.jsonl` events,
  then use normal closeout.
- Keep local profile audits private and opt-in. Redacted promotion candidates
  may point to tracked owners, but local profile checks must never become a
  tracked-plan, closeout, or CI prerequisite.
- Reconcile `TODO.md` after implementation so only durable residual work remains
  there.

## Non-goals

- Do not add a calibration ledger.
- Do not add `scripts/record-operator-note`, `scripts/process-operator-inbox`,
  `scripts/propose-profile-update`, or `scripts/check-calibration-governance`
  unless Slice 1 proves no existing owner can reasonably be extended and the
  plan is explicitly updated before implementation.
- Do not add a new review mode, instruction layer, closeout owner,
  approval/hash authority, profile auto-update path, or parallel workflow path.
- Do not edit `AGENTS.md` beyond a short pointer, if one is required at all.
- Do not implement historical opponent calibration, supervisor/opponent
  calibration convergence, IS export helpers, feedback-history extraction, or
  student-code sandboxing in this plan.
- Do not read, copy, stage, or commit private data from `cases/`,
  `profiles/local/`, private reviewer profiles, real theses, real reports, or
  generated case outputs.

## Slices

### Slice 1 - Owner Audit And Field Decision

Status: pending

Expected paths:

- `plans/review_delta_governance_plan.md`
- `TODO.md`

Work:

- Audit `record-review-delta`, `record-workflow-operation`, closeout,
  reviewer-profile privacy, docs, and TODO owners listed in `Audit Base`.
- Decide whether the candidate fields belong in the existing
  `review-delta-v1` payload, existing typed exceptions, existing promotion
  targets, operation-log events, docs only, or no change.
- Record the exact decision in this plan before code/docs edits.
- If any skill/doc duplication is found, name the old owner and the replacement
  owner before editing.
- Confirm no new command, ledger, review mode, closeout owner, or CI/profile
  gate is needed.

Verification:

```bash
git diff --check
scripts/check-private
scripts/check-scripts
```

### Slice 2 - Review-Delta Schema And Promotion Validation

Status: pending

Expected paths if Slice 1 confirms a schema change:

- `src/thesis_review_workflow/review_delta.py`
- `src/thesis_review_workflow/cli/record_review_delta.py`
- `src/thesis_review_workflow/amendments.py`
- `src/thesis_review_workflow/cli/record_report_amendment.py`
- `tests/test_review_delta.py`
- `tests/test_report_amendments.py`
- `scripts/smoke-record-review-delta`
- `scripts/smoke-record-report-amendment`
- `README.md`
- `docs/workflow-command-surface.md`

Work:

- Extend only the existing `record-review-delta` payload and validation.
- Validate governance fields structurally without interpreting free-form thesis
  text or profile prose.
- Keep promotion targets explicit and bounded. `private-reviewer-profile:...`
  may identify a private profile destination, but it must not copy private
  profile content into tracked files.
- Keep material deltas reopening the existing profile independent-review and
  closeout gates.

Verification:

```bash
pants test tests/test_review_delta.py tests/test_workflow_python_contracts.py
scripts/smoke-record-review-delta
git diff --check
scripts/check-private
scripts/check-scripts
```

Run relevant `pants lint`/`pants check` targets sequentially if Python files are
changed.

### Slice 3 - Maintainer Write-Scope And Sanitized Issue Reporting

Status: pending

Expected paths:

- `README.md`
- `docs/workflow-command-surface.md`
- `profiles/README.md`
- relevant `.agents/skills/*/SKILL.md` only if Slice 1 identifies an active
  duplicated instruction in a role skill
- `tests/test_review_delta.py` or focused docs/contract tests if behavior is
  made deterministic

Work:

- Document the default case-local path for colleague/operator issue reporting:
  limitations, sanitized issue reports, review deltas, and operation-log events.
- Document tracked-maintenance opt-in as permission to edit tracked workflow
  files, not as a second review mode or lighter DEEP workflow.
- Require maintainer consent and `scripts/check-private` before tracked fixes.
- Remove or replace any duplicated active instruction found in the old owner.

Verification:

```bash
git diff --check
scripts/check-private
scripts/check-scripts
```

Run focused Pants tests if deterministic behavior changes.

### Slice 4 - Operator-Note Batching Boundary

Status: pending

Expected paths if Slice 1 confirms batching is needed now:

- `README.md`
- `docs/workflow-command-surface.md`
- `src/thesis_review_workflow/review_delta.py` or
  `src/thesis_review_workflow/operation_log.py` only if the existing records need
  structural support
- `src/thesis_review_workflow/cli/record_review_delta.py` or
  `src/thesis_review_workflow/cli/record_workflow_operation.py` only if an
  existing command is extended
- `src/thesis_review_workflow/commands.py`, `src/thesis_review_workflow/cli/BUILD`,
  `scripts/BUILD`, and `tests/test_workflow_python_contracts.py` only if the
  command surface changes
- `tests/test_review_delta.py` or `tests/test_operation_log.py`
- relevant smoke script only if existing command behavior changes

Work:

- Define the open staging artifact as non-authoritative and ignored under the
  round workspace.
- Define freeze behavior as emission of existing review-delta records and
  operation-log events, followed by existing manifest/closeout checks.
- Ensure staging cannot satisfy approval, hash freshness, profile update, or
  closeout gates by itself.
- Prefer docs and existing command extensions. Add no command unless Slice 1
  already updated this plan with proof that existing owners cannot handle it.

Verification:

```bash
pants test tests/test_review_delta.py tests/test_operation_log.py
git diff --check
scripts/check-private
scripts/check-scripts
```

Run relevant `pants lint`/`pants check` targets sequentially if Python files are
changed. If command semantics or package-visible behavior changes, also run the
focused command-surface test and relevant smoke/package launcher check needed by
`docs/workflow-command-surface.md`; do not claim native Windows runtime proof
from Linux structural checks.

### Slice 5 - Local Profile Audit Boundary And TODO Reconciliation

Status: pending

Expected paths:

- `profiles/README.md`
- `README.md`
- `TODO.md`
- `plans/review_delta_governance_plan.md`
- `src/thesis_review_workflow/cli/check_private.py` and
  `tests/test_check_private.py` only if the current privacy guard is incomplete

Work:

- State the private, opt-in local-profile audit boundary in the existing profile
  owner docs.
- Allow redacted promotion candidates without making private profile checks a
  tracked-plan, case closeout, or CI prerequisite.
- Reconcile `TODO.md`: keep broader calibration convergence, historical
  calibration, Windows proof, and deterministic-test items only if still open;
  remove only the pointer to this plan when fully complete.
- Final audit for duplicate active instructions across `README.md`,
  `docs/workflow-command-surface.md`, `profiles/README.md`, relevant skills,
  `TODO.md`, and this plan.

Verification:

```bash
git diff --check
scripts/check-private
scripts/check-scripts
```

Run focused Pants tests if deterministic privacy behavior changes.

## Progress

- 2026-05-19: Created from deferred submission-bundle follow-up items. Reviewed
  `plans/README.md`, `TODO.md`, `plans/archive/submission_bundle_intake_plan.md`,
  `docs/workflow-command-surface.md`, `README.md`, `profiles/README.md`,
  `WORKFLOW_MEMORY.md`, current active plan summaries, and the existing
  `record-review-delta` schema/CLI/test surfaces. Used Serena project
  activation for the repo and bounded shell reads for the first audit. No
  private `cases/` data was read.
- 2026-05-19: Pre-implementation plan review completed with one reviewer agent.
  Findings were incorporated before implementation: added the
  `record-report-amendment` shared-delta wrapper to owner scope and made Slice 4
  command-surface/Windows coverage conditional explicit. Baseline checks passed:
  `git diff --check`, `scripts/check-private`, `scripts/check-scripts`.

## Decision Log

- Keep this as one governance plan around existing review-delta/profile
  boundaries. Do not merge the blocked historical opponent calibration pilot or
  broader supervisor/opponent convergence TODO into this plan.
- Treat `TODO.md` as an index only. Detailed execution rules live in this plan
  while it is active; residual durable work stays in TODO after archive.
- Prefer no new command. If implementation needs behavior beyond docs/schema,
  extend `record-review-delta`, `record-workflow-operation`, profile privacy
  checks, or closeout validators first.
- Local profile audits are private evidence, not tracked repo hygiene.

## Final Audit

Not started.
