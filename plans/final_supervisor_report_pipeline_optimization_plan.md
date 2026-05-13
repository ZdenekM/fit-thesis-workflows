# Final Supervisor Report Pipeline Optimization Plan

Status: active
Created: 2026-05-13

## Goal

Make the final supervisor-report pipeline self-contained enough that a
code-bearing final report can be prepared, reviewed, provenance-bound, and
closed out without manual manifest surgery or ad hoc evidence bookkeeping.

The target is not a new semantic review policy. It is a cleaner orchestration
contract around the workflow that already exists:

- current evidence and materiality are refreshed before final wave checks;
- required specialist handoffs are either current, reviewed, or recorded as
  typed limitations;
- low-risk internal evidence can remain silent without manual glue code;
- `init-review-manifest --run-checks` and artifact registration converge on a
  correct manifest in one normal pass;
- final closeout tells the operator exactly which gate is missing.

## Audit Base

This plan follows a real final-supervisor-report run and a follow-up repository
audit. It intentionally records only case-neutral workflow issues.

Observed friction:

- Final report generation worked, but the operator path still required several
  manual joins between role outputs, review approval records, helper checks,
  manifest refs, and final closeout.
- `scripts/check-evaluation-claims` correctly requires
  `work/quantitative_claims.json`, but the final-report path needs a smoother
  way to resolve "quantitative claims are material" as reviewed current
  evidence, downstream synthesis-covered evidence, or a typed accepted
  limitation before synthesis/closeout.
- Imported Theses.cz evidence can be clean and silent, but the current path
  still needs manual assessment/review/manifest registration to keep it from
  becoming either ignored evidence or unnecessary formal-report prose.
- `register-review-artifact` is useful but too low-level for common
  final-report cases. It allows correct refs, but it does not guide the operator
  away from classifying notes/extracted inputs as evidence refs or work
  artifacts as input refs.
- Reviewer outputs can be semantically useful while failing structural
  validators because the expected Markdown skeleton is not prominent enough in
  generated role packets.
- Missing heavyweight framework dependencies in submitted projects should be
  recorded as review/reproducibility limitations when relevant. The pipeline
  should not make local availability of such frameworks a prerequisite for
  report closeout.

Current related implementation:

- `plans/archive/supervisor_report_workflow_plan.md` is `done`; the first-class
  supervisor-report workflow, report draft, review approval, confirmation, and
  closeout commands already exist.
- `scripts/supervisor-report-closeout` currently runs supervisor-report
  readiness, reviewed/confirmed report validation, final review-wave validation,
  `init-review-manifest --run-checks`, agent coverage, review-manifest
  completeness, and repo hygiene.
- `scripts/check-review-materiality --workflow supervisor_report --phase final`
  exists, but closeout does not yet make that final materiality refresh a
  first-class step.
- `scripts/record-submitted-supervisor-report` and
  `scripts/record-report-amendment` already exist. The remaining work is to
  validate their integration with closeout, TODO, and operator docs rather than
  implement them from scratch.
- `init-review-manifest --run-checks` already applies review approval records
  before refreshing `work/agent_coverage.json`; the remaining work is to cover
  that behavior with explicit regression tests and remove stale TODO wording.

TODO check:

- `TODO.md` currently has a P0 item about making supervisor-report closeout
  self-contained. This plan should absorb the still-open parts of that item and
  delete or narrow completed subpoints during the documentation slice.
- `TODO.md` also has a separate P1 item about executing submitted code in a
  controlled environment. That item is not part of this plan.
- The new `plans/reviewer_agent_profiles_plan.md` covers missing durable agent
  profiles. This plan may rely on those profiles when they exist, but it should
  not duplicate that work.
- Until the Codex agent role profiles land, final-report packets and docs should
  name the repo-local skills and acceptable default-agent invocation. After the
  profile registry exists, packets, manifest role ids, and docs should use the
  stable profile ids from that registry.

## Scope

In scope:

- strengthen `scripts/supervisor-report-closeout` for final report materiality,
  unresolved next actions, submitted-report records, amendments, and clearer
  operator output;
- make `scripts/prepare-supervisor-report-packets` refresh or verify current
  evidence before materiality decisions and role packet emission;
- improve final-report packet or wave gates so quantitative and similarity
  actions resolve through current structured artifacts or typed limitations;
- reduce manual `work/review_manifest.json` edits by improving artifact
  registration defaults, presets, validation, or diagnostics;
- make low-risk imported similarity evidence a smooth internal-evidence path
  without forcing official report prose;
- make role packets surface exact output skeletons and validator commands for
  the artifacts they expect;
- update README, skills, TODO, and smoke tests after behavior exists.

Out of scope:

- installing heavyweight third-party frameworks required by individual student
  submissions;
- running unknown submitted code as a default report-pipeline step;
- changing grading semantics, supervisor authority, or the reviewed-report
  confirmation boundary;
- inferring material quantitative, similarity, or quality conclusions from raw
  free-text substring scans;
- replacing role-split agents with a fully automated agent runner.

## Target Operator Path

For a final supervisor report with code and optional similarity/evaluation
evidence, the intended path after this plan should be:

1. Import/update the round and run `scripts/check-supervisor-report-ready`.
2. Prepare static code evidence when code is present.
3. Confirm that the current request explicitly authorizes role agents, synthesis,
   and the independent final-review loop. If not, stop before packets, role
   agents, trace/draft generation, or reviewed/sendable outputs.
4. Refresh current evidence and final materiality for
   `supervisor_report` before packet emission.
5. Prepare supervisor-report packets and run only the required role agents or
   record typed limitations for unavailable/non-material handoffs.
6. For code-bearing final reports, produce current reviewed-or-covered
   `outputs/code_consistency.md` and `outputs/code_quality_review.md`, or record
   concrete typed limitations for whichever evidence could not be performed.
7. Generate trace and draft, run independent report review, then write
   `work/reviews/supervisor_report_review.json`.
8. Run one manifest refresh with checks and get a valid manifest without manual
   ref reclassification.
9. Confirm the report for IS and run `scripts/supervisor-report-closeout`.
10. If a submitted report PDF or post-review amendment is present, closeout
   validates that it is hash-bound to the reviewed/confirmed report state.

## Slices

### Slice 1 - Current-State Regression Audit And TODO Reconciliation

- Status: done
- Proposed commit message: `docs(workflow): plan final report pipeline cleanup`
- Expected paths:
  - `plans/final_supervisor_report_pipeline_optimization_plan.md`
  - `TODO.md`
  - `tests/test_review_manifest_helpers.py`
  - `tests/test_supervisor_report.py`
  - `tests/test_workflow_python_contracts.py`
- Tasks:
  - Add or adjust focused tests proving that `init-review-manifest --run-checks`
    applies review approvals before refreshing agent coverage.
  - Add tests proving `record-submitted-supervisor-report` and
    `record-report-amendment` are registered in the command surface and are
    covered by existing smoke tests.
  - Reconcile the P0 supervisor-report TODO item: remove completed subpoints and
    leave only work not covered by this plan or current tests.
  - Keep unrelated TODO items intact.
- Verification:
  - `pants test tests/test_review_manifest_helpers.py tests/test_supervisor_report.py tests/test_workflow_python_contracts.py`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 2 - Current Evidence And Closeout Gate Ordering

- Status: done
- Proposed commit message: `fix(workflow): refresh supervisor report materiality in closeout`
- Expected paths:
  - `src/thesis_review_workflow/cli/prepare_supervisor_report_packets.py`
  - `src/thesis_review_workflow/cli/supervisor_report_closeout.py`
  - `src/thesis_review_workflow/review_materiality.py`
  - `tests/test_supervisor_report_packets.py`
  - `tests/test_supervisor_report.py`
  - `tests/test_supervisor_report_closeout.py`
  - `tests/test_review_materiality.py`
  - `scripts/smoke-supervisor-report`
- Tasks:
  - Create `tests/test_supervisor_report_closeout.py` for closeout orchestration
    tests instead of hiding closeout subprocess-order assertions in broader
    supervisor-report tests.
  - Make `prepare-supervisor-report-packets` run or verify
    `scripts/update-current-evidence-snapshot <case-id> [round-id]` before
    materiality and packet emission when source evidence exists.
  - Make closeout run or verify
    `scripts/update-current-evidence-snapshot <case-id> [round-id]` before the
    final materiality check when source evidence exists.
  - Make closeout run
    `scripts/check-review-materiality --workflow supervisor_report --phase final <case-id> [round-id]`
    before the final review-wave gate.
  - Make closeout refresh `work/review_manifest.json` with
    `scripts/init-review-manifest --run-checks <case-id> [round-id]` before the
    final review-wave gate, so approval records and `work/agent_coverage.json`
    are current when `check-review-wave --workflow supervisor_report --wave final`
    runs.
  - Keep a post-wave manifest refresh only for evidence/check metadata that can
    change after the final wave; do not require manual manifest surgery between
    the two passes.
  - Fail with a clear message when final materiality has unresolved required
    next actions and no current artifact or typed limitation resolves them.
  - Keep advisory materiality warnings separate from hard closeout blockers.
  - Preserve `--skip-repo-hygiene` semantics.
- Verification:
  - `pants test tests/test_supervisor_report.py tests/test_supervisor_report_packets.py tests/test_supervisor_report_closeout.py tests/test_review_materiality.py`
  - `scripts/smoke-supervisor-report`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 3 - Structured Action Resolution For Quantitative And Similarity Evidence

- Status: done
- Proposed commit message: `feat(workflow): validate final report evidence actions`
- Expected paths:
  - `src/thesis_review_workflow/review_materiality.py`
  - `src/thesis_review_workflow/review_wave.py`
  - `src/thesis_review_workflow/agent_coverage.py`
  - `src/thesis_review_workflow/work_artifacts.py`
  - `tests/test_review_materiality.py`
  - `tests/test_review_wave_gate.py`
  - `tests/test_agent_coverage.py`
  - `tests/test_work_artifacts.py`
- Tasks:
  - Update tests first so a merely valid/current `work/quantitative_claims.json`
    no longer clears final supervisor-report materiality unless it is reviewed,
    explicitly covered by downstream synthesis/review approval, or replaced by a
    typed limitation.
  - Ensure final-report materiality treats quantitative claims as resolved only
    when `work/quantitative_claims.json` is valid, current, and either reviewed
    or explicitly covered by downstream synthesis.
  - Ensure imported Theses.cz evidence is resolved only through a valid
    `work/theses_similarity/assessment.json`, reviewed
    `outputs/theses_similarity_review.md`, or a typed limitation.
  - Add a clean "silent internal evidence" status for no-material-concern
    similarity assessments. It should satisfy internal coverage while keeping
    official report text quiet unless an unresolved concern exists.
  - Clarify the boundary: assessment-only silent status is not a standalone
    reviewed evidence artifact. It may satisfy final-report materiality only when
    the assessment schema records no material concern, source hashes are current,
    the supervisor-report synthesis/review records that no official prose is
    needed, and manifest/coverage records treat it as supporting internal
    evidence. Standalone similarity evidence still requires
    `outputs/theses_similarity_review.md` plus review approval, or a typed
    limitation.
  - Keep all semantic interpretation in agent/human-authored structured
    artifacts; deterministic code validates structure, hashes, and currentness.
  - Create `tests/test_agent_coverage.py` for agent-coverage-specific assertions
    that would otherwise make `tests/test_workflow_python_contracts.py` harder
    to scan.
- Verification:
  - `pants test tests/test_review_materiality.py tests/test_review_wave_gate.py tests/test_agent_coverage.py tests/test_workflow_python_contracts.py tests/test_work_artifacts.py`
  - `scripts/smoke-review-wave`
  - `scripts/smoke-agent-coverage`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 4 - Manifest Registration Presets And Ref Classification

- Status: done
- Proposed commit message: `fix(workflow): reduce manual review manifest registration`
- Expected paths:
  - `src/thesis_review_workflow/review_manifest.py`
  - `src/thesis_review_workflow/cli/register_review_artifact.py`
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `tests/test_review_manifest_helpers.py`
  - `scripts/smoke-register-review-artifact`
  - `scripts/smoke-review-manifest`
- Tasks:
  - Add a safer registration path for common final-report artifacts:
    code-consistency evidence, code-quality evidence, similarity evidence, and
    reviewed supervisor reports.
  - Prefer structured presets or diagnostics over more free-form flags when the
    artifact path already implies the normal contribution/review scope.
  - Validate that refs under `notes/`, `inputs/`, and `extracted/` are treated
    as input refs, while refs under `work/` are supporting evidence refs unless
    the operator explicitly overrides the classification.
  - Improve error messages when a registered artifact references a path that is
    not recorded in manifest inputs, work artifacts, or outputs.
  - Keep manual expert override available, but make the normal path less
    error-prone.
  - Ensure presets are Windows-neutral command-surface behavior; do not add a
    POSIX-only operator path.
- Verification:
  - `pants test tests/test_review_manifest_helpers.py`
  - `scripts/smoke-register-review-artifact`
  - `scripts/smoke-review-manifest`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 5 - Role Packet Skeletons And Validator Prominence

- Status: pending
- Proposed commit message: `docs(workflow): harden final report role packet outputs`
- Expected paths:
  - `.agents/skills/thesis-code-consistency/SKILL.md`
  - `.agents/skills/thesis-code-quality-review/SKILL.md`
  - `.agents/skills/thesis-theses-similarity-review/SKILL.md`
  - `.agents/skills/thesis-supervisor-report-review/SKILL.md`
  - `src/thesis_review_workflow/supervisor_report_packets.py`
  - `tests/test_supervisor_report_packets.py`
  - `scripts/smoke-supervisor-report-packets`
- Tasks:
  - Make generated supervisor-report packets include the exact expected output
    path, required top-level headings or schema name, and validator command for
    each role-owned artifact.
  - Make packets include the current-evidence snapshot path/hash or a clear
    "snapshot unavailable" limitation, so role agents do not work from stale
    packets that closeout rejects later.
  - Include the current-request agent authorization status in packet generation
    output; if authorization is absent, packet generation should stop before
    producing role-execution instructions.
  - Keep skill bodies as the canonical procedure; packets should provide a
    compact skeleton/checklist, not duplicate the full skill.
  - Add packet tests that catch missing validator commands or missing output
    skeletons for code consistency, code quality, quantitative claims,
    similarity evidence, and supervisor-report review.
  - Ensure packet prompts still prefer compact handoffs and targeted evidence
    opens over broad source rereads.
- Verification:
  - `pants test tests/test_supervisor_report_packets.py`
  - `scripts/smoke-supervisor-report-packets`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 6 - Final Documentation, Smoke Path, And Archive Decision

- Status: pending
- Proposed commit message: `docs(workflow): close final report pipeline cleanup`
- Expected paths:
  - `README.md`
  - `.agents/skills/thesis-supervisor-report/SKILL.md`
  - `.agents/skills/thesis-supervisor-report-review/SKILL.md`
  - `docs/workflow-command-surface.md`
  - `TODO.md`
  - `plans/final_supervisor_report_pipeline_optimization_plan.md`
  - `plans/archive/final_supervisor_report_pipeline_optimization_plan.md`
- Tasks:
  - Update the chat-first README path for final supervisor reports to reflect
    materiality refresh, action resolution, manifest refresh, confirmation, and
    closeout.
  - Preserve logical-command wording and Windows launcher examples for the final
    supervisor-report path. `scripts/<tool>` examples remain Linux/dev shorthand;
    Windows operator docs must route through packaged `.cmd` or `.ps1` launchers.
  - Update skills only where the operator or agent sequence changed.
  - Add or update a synthetic smoke path that covers code evidence, a
    quantitative action resolved by structured evidence or typed limitation,
    imported similarity evidence that stays silent, manifest registration,
    approval, confirmation, and closeout.
  - In that synthetic smoke path, assert clean/silent similarity evidence does
    not introduce official report prose unless the structured assessment records
    an unresolved concern.
  - Reconcile `TODO.md` after implementation so it remains an open-work index,
    not a list of completed helper names.
  - Record final audit commands and archive this plan when done.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests:: scripts::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_review_manifest_helpers.py tests/test_review_materiality.py tests/test_review_wave_gate.py tests/test_agent_coverage.py tests/test_supervisor_report.py tests/test_supervisor_report_packets.py tests/test_work_artifacts.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-supervisor-report`
  - `scripts/smoke-supervisor-report-packets`
  - `scripts/smoke-review-wave`
  - `scripts/smoke-agent-coverage`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-register-review-artifact`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git status --short --untracked-files=all`
  - `git diff --check`

## Progress

- 2026-05-13: Created the plan after a final-supervisor-report run exposed
  manual materiality, quantitative-claim, similarity-evidence, manifest, and
  packet-structure friction. Checked `TODO.md`; the separate submitted-code
  execution environment item remains outside this plan.
- 2026-05-13: Agent review tightened the plan around explicit agent
  authorization, mandatory code-consistency/code-quality evidence for
  code-bearing reports, current-evidence refresh before packet emission,
  manifest-before-final-wave closeout ordering, real test homes, and the
  assessment-only boundary for silent similarity evidence.
- 2026-05-13: Slice 1 done. Added a regression proving
  `init-review-manifest --run-checks` applies structured review approvals before
  deferred `check-agent-coverage`, added command/smoke coverage assertions for
  `record-submitted-supervisor-report` and `record-report-amendment`, and
  narrowed the P0 TODO to the still-open closeout integration work. Verification
  passed: `pants test tests/test_review_manifest_helpers.py
  tests/test_supervisor_report.py tests/test_workflow_python_contracts.py`,
  `scripts/check-private`, `scripts/check-scripts`, and `git diff --check`.
- 2026-05-13: Slice 2 done. Added focused closeout orchestration tests, made
  supervisor-report packet preparation refresh current evidence before final
  materiality, and reordered closeout to refresh current evidence, run final
  materiality and unresolved-next-action checks, refresh manifest/coverage before
  final wave validation, then refresh post-wave metadata. Closeout uses a
  stable final snapshot ref set so volatile `work/review_manifest.json` and
  `work/agent_coverage.json` do not immediately stale the snapshot. Verification
  passed: `pants test tests/test_supervisor_report.py
  tests/test_supervisor_report_packets.py tests/test_supervisor_report_closeout.py
  tests/test_review_materiality.py`, `scripts/smoke-supervisor-report`,
  `scripts/check-private`, `scripts/check-scripts`, and `git diff --check`.
- 2026-05-13: Slice 3 done. Final supervisor-report quantitative materiality now
  requires a current structured artifact plus independent review, downstream
  synthesis coverage, or a typed limitation. Theses.cz similarity materiality
  now resolves through reviewed similarity evidence, typed limitation, or an
  explicitly hash-bound silent no-concern assessment covered by the reviewed
  supervisor-report synthesis. Added dedicated agent-coverage tests and kept
  supporting work-artifact synthesis metadata across manifest refreshes.
  Verification passed: `pants test tests/test_review_materiality.py
  tests/test_review_wave_gate.py tests/test_agent_coverage.py
  tests/test_workflow_python_contracts.py tests/test_work_artifacts.py
  tests/test_review_manifest_helpers.py`, `scripts/smoke-review-wave`,
  `scripts/smoke-agent-coverage`, `scripts/check-private`,
  `scripts/check-scripts`, and `git diff --check`.
- 2026-05-13: Slice 4 done. `register-review-artifact` now has auto presets for
  common final-report artifacts and a `--ref` path that classifies
  notes/inputs/extracted as input refs and work/outputs as evidence refs.
  Accidental manual misclassification is rejected unless the operator uses an
  explicit override, and manifest diagnostics now say which manifest section is
  missing the referenced path. `init-review-manifest` also treats reviewed
  supervisor reports as synthesis targets for internal evidence. Verification
  passed: `pants test tests/test_review_manifest_helpers.py`, targeted
  `pants lint`/`pants check` for touched files, `scripts/smoke-register-review-artifact`,
  `scripts/smoke-review-manifest`, `scripts/check-private`,
  `scripts/check-scripts`, and `git diff --check`.

## Decision Log

- Optimize the current final supervisor-report pipeline instead of adding a new
  parallel workflow.
- Treat unavailable heavyweight project runtimes as possible reproducibility
  evidence, not as a prerequisite for supervisor-report closeout.
- Keep clean similarity evidence internal and silent unless reviewed evidence
  records a real unresolved concern.
- Do not use deterministic substring scans to decide whether quantitative or
  similarity findings are material.
- Make normal manifest registration safer before adding more operator-facing
  commands.
- Do not treat assessment-only Theses.cz similarity records as standalone final
  evidence. They can be silent internal support for supervisor-report synthesis
  only under a current no-concern assessment, synthesis/review coverage, and
  manifest/coverage bookkeeping.
- Closeout should refresh manifest/approval/coverage before final review-wave
  validation, then refresh again only where checks can update provenance.
- Until dedicated Codex agent role profiles exist, packet instructions should
  route by repo-local skill and explicit default-agent invocation; after the
  profile registry lands, use stable profile ids.

## Final Audit

Not started.
