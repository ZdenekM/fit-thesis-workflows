# Opponent Review Value Plan

Status: active
Created: 2026-05-06

## Goal

Prioritize and sequence the TODO items that most improve the quality,
repeatability, and defensibility of opponent materials and opponent-report
review.

The first implementation wave should make `outputs/oponent_podklady_revidovane.md`
and `work/oponent_posudek_draft.md` easier to defend from concrete evidence:
assignment coverage, artifact presence, code reproducibility, reviewed evidence
provenance, role-specific agent inputs, and report-review checks that can point
back to the exact supporting artifacts.

## Audit Base

Source of candidates: `TODO.md` on 2026-05-06.

Selected high-value TODO items:

| Rank | TODO item | Why it matters for opponent reports | First-wave decision |
|---:|---|---|---|
| 1 | Assignment coverage map helper (`TODO.md` lines 63-65) | Opponent reports must judge fulfillment of assignment points and IS criteria; an advisory map gives the synthesis and report reviewer a concrete checklist. | include |
| 2 | First-class evidence-presence checks (`TODO.md` lines 41-45) | Opponent findings need to distinguish missing evidence, available-but-uninspected evidence, and inspected support for strong claims. | include |
| 3 | Code workspace reproducibility classification (`TODO.md` lines 46-49) | Code-bearing theses need fair separation between implementation failure and missing or unreproducible review setup. | include |
| 4 | Thin validators for core internal evidence artifacts (`TODO.md` lines 33-36) | Opponent synthesis relies on internal evidence outputs; structural validators reduce placeholder, unsupported-claim, and path-leak risk. | include |
| 5 | Incremental review provenance (`TODO.md` lines 20-24) | Multi-agent opponent workflows need an auditable record of generator/reviewer roles, hashes, limitations, and artifact use before closeout. | include |
| 6 | Role-specific agent packets (`TODO.md` lines 66-69) | Better per-role packets reduce prompt drift and improve coverage of text, code, literature, figure/media, typography, and synthesis. | include |
| 7 | Historical reference-report comparison (`TODO.md` lines 89-93) | Helpful for calibration, but only after reviewed opponent materials exist and only as operator-only comparison evidence. | defer to follow-up |

Cross-cutting TODO item:

- Deterministic tests for workflow validators and helper contracts (`TODO.md`
  lines 8-11) are part of every implementation slice. Each new helper or
  validator must land with focused pytest coverage and smoke coverage where it
  changes an operator command surface.

Relevant current workflow surfaces:

- `outputs/oponent_podklady_revidovane.md` is the reviewed internal opponent
  material.
- `work/oponent_posudek_draft.md` is only a bridge draft and must remain blocked
  until human point/grade calibration and `scripts/check-opponent-report`.
- `scripts/opponent-preflight`, `scripts/check-opponent-materials`,
  `scripts/check-opponent-report`, and `scripts/opponent-closeout` are the
  existing opponent command surfaces.
- `work/review_manifest.json` and `work/agent_coverage.json` are the existing
  provenance and role-coverage surfaces.
- `scripts/draft-opponent-report` and `scripts/check-opponent-report` are the
  existing bridge between reviewed materials and the human-calibrated report
  draft; they should benefit from new advisory evidence without making the draft
  look final.
- Internal evidence artifacts include `outputs/code_consistency.md`,
  `outputs/code_quality_review.md`, `outputs/revision_diff.md`,
  `outputs/figure_media_review.md`, `outputs/literature_citation_review.md`, and
  `outputs/typography_formal_review.md`.

Constraints:

- Keep all private case data, submitted code, PDFs, source zips, notes, and
  generated case outputs under ignored `cases/`.
- Tracked tests must use anonymized fixtures only.
- Do not make advisory checks into verdict engines. Missing evidence is a review
  risk or evidence request, not automatic proof that a thesis claim is false.
- Do not widen supervisor workflow behavior unless the slice explicitly tests the
  shared behavior.
- Do not add backwards compatibility for older `~/code/diplomky` workflows.
- Keep Windows operator support intact: new operator commands need Python/Pants/
  PEX or native launcher surfaces, not Bash-only contracts.
- Use Serena for non-trivial Python navigation when practical.
- Run Pants commands sequentially.
- Use `pants run :omen` as a developer-hygiene signal on larger implementation
  slices and final closeout. Keep it out of case pipeline gates.

## Scope

In scope:

- opponent-materials and opponent-report-review support;
- advisory assignment coverage and evidence presence surfaces;
- structural validators for internal evidence artifacts used by opponent
  synthesis;
- incremental manifest/provenance helper work that starts with opponent
  artifacts;
- role packet generation into ignored round workspaces;
- report-review consumption of the new advisory artifacts without bypassing
  human point/grade calibration;
- focused README/skill/template updates needed to route opponent workflows.

Out of scope:

- generating a final IS-ready opponent report without human calibration;
- treating advisory assignment/evidence/reproducibility outputs as grading
  decisions;
- changing the meaning of existing score, grade, or point calibration;
- broad case-data migration/versioning work;
- executing student code by default;
- full sandbox workflow for running submitted code;
- heavyweight video/demo inspection workflow;
- historical reference-report comparison in V1;
- expanded GitHub intake, literature source collection automation, and advanced
  typography engines.

## Slices

### Slice 1 - Plan Hardening And Baseline

- Status: pending
- Proposed commit message: `docs(workflow): plan opponent review value work`
- Why: The selected TODO items span validators, provenance, generated evidence,
  and agent workflow contracts. The plan needs a reviewed baseline before
  implementation.
- Expected paths:
  - `plans/opponent_review_value_plan.md`
- Tasks:
  - Review this plan with role-split agents before implementation.
  - Confirm selected TODO items and explicitly keep excluded TODO items as later
    work.
  - Record any scope cuts needed to keep V1 opponent-focused.
- Verification:
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

### Slice 2 - Work Artifact And Command Surface Contract

- Status: pending
- Proposed commit message: `feat(workflow): define opponent work artifact contracts`
- Why: The first implementation slices create new ignored `work/*` artifacts and
  new operator commands. They need a minimal schema/hash/packaging contract
  before downstream helpers rely on them.
- TODO source:
  - `TODO.md` lines 5-7 for native command-surface compatibility on new helpers
  - `TODO.md` lines 8-19 for deterministic tests and the minimal V1 subset of
    case-data contracts
  - `TODO.md` lines 20-24 for manifest/provenance work-artifact support
- Expected paths:
  - `src/thesis_review_workflow/work_artifacts.py`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `src/thesis_review_workflow/cli/case_doctor.py`
  - `tests/test_work_artifacts.py`
  - `tests/test_review_manifest_helpers.py`
  - `README.md`
- Tasks:
  - Define V1 work-artifact records for `work/assignment_coverage_map.json`,
    `work/evidence_presence.json`, `work/code_reproducibility.json`,
    `work/figure_media/visual_inventory.jsonl`, and
    `work/opponent_packets/*.md`.
  - Require JSON artifacts to include `schema_version`, `case_id`, `round_id`,
    `generated_at`, and deterministic advisory payload fields.
  - Include these files in manifest `supporting_work_artifacts` with hashes when
    present, and make stale/missing relied-on artifacts diagnosable.
  - Document the command-surface checklist for each new helper: POSIX wrapper,
    CLI `BUILD` target, `WORKFLOW_COMMAND_MODULES`, `scripts/BUILD` shell
    source/runtime dependency/`workflow-tool` PEX target, targeted smoke, and
    `scripts/smoke-package-workflow-tools`.
  - Keep broader migration tooling out of V1; only define the new artifact
    contracts introduced by this plan.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests::`
  - `scripts/smoke-review-manifest`
  - `scripts/check-private`
  - `scripts/check-scripts`

### Slice 3 - Static Code Reproducibility Classification

- Status: pending
- Proposed commit message: `feat(workflow): classify code review reproducibility`
- Why: Opponent reports need fair language about whether code was inspectable,
  missing setup instructions, already has recorded run evidence, or could not be
  assessed from submitted materials. This must be available before the
  evidence-presence aggregator talks about code setup risk.
- TODO source:
  - `TODO.md` lines 46-49
  - `TODO.md` lines 8-11 for deterministic helper tests
- Expected paths:
  - `src/thesis_review_workflow/code_reproducibility.py`
  - `src/thesis_review_workflow/cli/check_code_reproducibility.py`
  - `src/thesis_review_workflow/cli/prepare_code_workspace.py`
  - `src/thesis_review_workflow/cli/opponent_preflight.py`
  - `src/thesis_review_workflow/cli/draft_opponent_report.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `scripts/check-code-reproducibility`
  - `scripts/smoke-code-reproducibility`
  - `scripts/BUILD`
  - `tests/test_code_reproducibility.py`
  - `scripts/smoke-prepare-code-workspace`
  - `scripts/smoke-opponent-preflight`
- Tasks:
  - Classify from static evidence and already-recorded, explicitly authorized
    run evidence only.
  - Do not run imports, tests, examples, or arbitrary submitted code in this
    plan. If no sandboxed/operator run evidence exists, record
    `not_attempted`, `missing instructions`, or `not locally reproducible from
    submitted instructions` rather than executing commands.
  - Include detected missing packages, expected entry points, available
    dependency files, existing run logs, and suggested next evidence requests.
  - Route the classification into opponent preflight and report-draft context so
    reviewer agents can use fair language without rerunning code.
  - Add the full workflow-command checklist, including packaged Windows
    launchers through `scripts/smoke-package-workflow-tools`.
  - Keep the student-code sandbox workflow as a separate future plan.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests::`
  - `scripts/smoke-code-reproducibility`
  - `scripts/smoke-prepare-code-workspace`
  - `scripts/smoke-opponent-preflight`
  - `scripts/smoke-opponent-materials`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `scripts/smoke-package-workflow-tools`

### Slice 4 - Assignment Coverage Map

- Status: pending
- Proposed commit message: `feat(workflow): map assignment coverage for opponent review`
- Why: Assignment fulfillment is the strongest direct input to an opponent
  report. The helper should make missing, partial, covered, and unverifiable
  assignment points visible before synthesis without turning the map into a
  grading decision.
- TODO source:
  - `TODO.md` lines 63-65
  - `TODO.md` lines 8-11 for deterministic helper tests
- Expected paths:
  - `src/thesis_review_workflow/assignment_coverage.py`
  - `src/thesis_review_workflow/cli/check_assignment_coverage.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `scripts/check-assignment-coverage`
  - `scripts/smoke-assignment-coverage`
  - `scripts/BUILD`
  - `.agents/skills/thesis-opponent-materials/SKILL.md`
  - `.agents/skills/thesis-opponent-materials-review/SKILL.md`
  - `tests/test_assignment_coverage.py`
  - `scripts/smoke-opponent-materials`
- Tasks:
  - Parse `notes/assignment.md` into rough assignment points.
  - Produce only an ignored advisory artifact in V1, for example
    `work/assignment_coverage_map.json`.
  - Record whether reviewed opponent materials and report draft cover, defer, or
    mark each point as unverifiable.
  - Keep the helper advisory. Final interpretation stays with reviewer agents
    and the human opponent.
  - Add targeted smoke coverage for parser, artifact schema, idempotent writes,
    and absence of case-output leakage into tracked fixtures.
  - Add a workflow-tool PEX target and keep packaged `.cmd`/`.ps1` launchers in
    scope through `scripts/smoke-package-workflow-tools`.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests::`
  - `scripts/smoke-assignment-coverage`
  - `scripts/smoke-opponent-materials`
  - `scripts/smoke-opponent-report`
  - `scripts/smoke-opponent-closeout`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `scripts/smoke-package-workflow-tools`

### Slice 5 - Evidence Presence And Media Inventory

- Status: pending
- Proposed commit message: `feat(workflow): flag opponent evidence-presence risks`
- Why: Opponent materials should make strong claims only after surfacing whether
  the corresponding thesis, code, data, demo, or experiment evidence is present
  and inspectable. V1 should also record cheap visual/media presence state
  without doing heavyweight media review.
- TODO source:
  - `TODO.md` lines 41-45
  - `TODO.md` lines 70-81 for a narrow media-presence subset
  - `TODO.md` lines 8-11 for deterministic helper tests
- Expected paths:
  - `src/thesis_review_workflow/evidence_presence.py`
  - `src/thesis_review_workflow/cli/check_evidence_presence.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `scripts/check-evidence-presence`
  - `scripts/BUILD`
  - `src/thesis_review_workflow/cli/opponent_preflight.py`
  - `src/thesis_review_workflow/cli/draft_opponent_report.py`
  - `tests/test_evidence_presence.py`
  - `scripts/smoke-evidence-presence`
  - `scripts/smoke-opponent-materials`
- Tasks:
  - Detect likely required demo/video/poster/presentation artifacts from
    assignment notes and submitted inputs as presence state only.
  - Write a narrow ignored visual/media inventory, reusing
    `work/figure_media/visual_inventory.jsonl` where possible, with states such
    as `required`, `present-uninspected`, `inspected`, `not-playable`, and
    `missing`.
  - Detect quantitative result claims needing raw data, calculation scripts,
    experiment logs, notebooks, screenshots, or reproducibility description.
  - Consume the code reproducibility classification from Slice 3 rather than
    duplicating dependency/test-command heuristics.
  - Surface findings as review risks and precise evidence requests.
  - Make opponent preflight and draft-generation output mention the advisory
    artifact path when evidence-presence risks exist, without blocking a draft by
    itself.
  - Keep detailed video/demo inspection and figure-quality automation out of V1.
  - Add a workflow-tool PEX target and keep packaged `.cmd`/`.ps1` launchers in
    scope through `scripts/smoke-package-workflow-tools`.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests::`
  - `scripts/smoke-evidence-presence`
  - `scripts/smoke-opponent-preflight`
  - `scripts/smoke-evaluation-claims`
  - `scripts/smoke-opponent-materials`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `scripts/smoke-package-workflow-tools`

### Slice 6 - Thin Validators For Opponent Evidence Inputs

- Status: pending
- Proposed commit message: `feat(workflow): validate opponent evidence artifacts`
- Why: Reviewed opponent materials should not rely on malformed internal
  evidence artifacts, placeholders, path leaks, or unanchored claims.
- TODO source:
  - `TODO.md` lines 33-36
  - `TODO.md` lines 8-11 for deterministic validator tests
- Expected paths:
  - `src/thesis_review_workflow/cli/check_code_consistency.py`
  - `src/thesis_review_workflow/cli/check_code_quality_review.py`
  - `src/thesis_review_workflow/cli/check_revision_diff.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/check_opponent_report.py`
  - `scripts/check-code-consistency`
  - `scripts/check-code-quality-review`
  - `scripts/check-revision-diff`
  - `scripts/smoke-internal-evidence-validators`
  - `scripts/BUILD`
  - `tests/test_internal_evidence_validators.py`
  - `scripts/smoke-opponent-materials`
- Tasks:
  - Add structural validators for required headings, concrete evidence anchors,
    limitations, no placeholders, and no internal path leaks.
  - Reuse `markdown_utils.py` and existing privacy/path-leak patterns where they
    fit.
  - Keep validator outputs advisory about evidence shape only; do not judge the
    thesis or code quality itself.
  - Let opponent-report review surface stale or malformed relied-on evidence
    before the human calibrates points and grade.
  - Add anonymized fixture snippets under tracked tests, not copied case outputs.
  - Add workflow-tool PEX targets and keep packaged `.cmd`/`.ps1` launchers in
    scope through `scripts/smoke-package-workflow-tools`.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests::`
  - `scripts/smoke-internal-evidence-validators`
  - `scripts/smoke-opponent-materials`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `scripts/smoke-package-workflow-tools`

### Slice 7 - Role-Specific Opponent Agent Packets

- Status: pending
- Proposed commit message: `feat(workflow): generate opponent reviewer packets`
- Why: Opponent workflows require role-split agents. Generated packets should
  reduce prompt drift and give each reviewer the right inputs and limitations
  without leaking private data into tracked templates.
- TODO source:
  - `TODO.md` lines 66-69
  - `TODO.md` lines 8-11 for deterministic helper tests
- Expected paths:
  - `src/thesis_review_workflow/opponent_packets.py`
  - `src/thesis_review_workflow/cli/prepare_opponent_packets.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `scripts/prepare-opponent-packets`
  - `scripts/BUILD`
  - `scripts/smoke-opponent-packets`
  - `.agents/skills/thesis-opponent-materials/SKILL.md`
  - `.agents/skills/thesis-opponent-materials-review/SKILL.md`
  - `tests/test_opponent_packets.py`
- Tasks:
  - Generate concise packets under ignored round workspace, for example
    `work/opponent_packets/<role>.md`.
  - Include case/round metadata, authoritative input paths, required role output,
    known limitations, and privacy constraints.
  - Cover text structure, assignment coverage, code consistency, code quality,
    figure/media, literature/citation, typography/formal, and synthesis roles.
    Include assignment coverage, evidence-presence, reproducibility, and media
    inventory paths when those artifacts exist.
  - Do not encode findings or conclusions in reusable tracked templates.
  - Add a workflow-tool PEX target and keep packaged `.cmd`/`.ps1` launchers in
    scope through `scripts/smoke-package-workflow-tools`.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests::`
  - `scripts/smoke-opponent-packets`
  - `scripts/smoke-opponent-materials`
  - `scripts/smoke-agent-coverage`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `scripts/smoke-package-workflow-tools`

### Slice 8 - Incremental Opponent Provenance Helper

- Status: pending
- Proposed commit message: `feat(workflow): record opponent review artifacts incrementally`
- Why: Opponent workflows currently depend on final manifest reconstruction. A
  small helper should let generator/reviewer agents register reviewed artifacts
  as work progresses.
- TODO source:
  - `TODO.md` lines 20-24
  - `TODO.md` lines 8-11 for deterministic manifest tests
- Expected paths:
  - `src/thesis_review_workflow/review_manifest.py`
  - `src/thesis_review_workflow/cli/register_review_artifact.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `scripts/register-review-artifact`
  - `scripts/BUILD`
  - `scripts/smoke-register-review-artifact`
  - `tests/test_review_manifest_helpers.py`
  - `scripts/smoke-review-manifest`
- Tasks:
  - Add a helper that records artifact path, artifact hash, role, reviewer role
    when present, agent identifier when present, scope, limitations, and whether
    the artifact feeds opponent materials or report review.
  - Start with existing manifest schema instead of inventing a parallel
    provenance format.
  - Support bootstrap/update mode for ignored round workspaces.
  - Keep supervisor artifacts supported only where the existing schema already
    makes that mechanical; do not change supervisor gates in this slice.
  - Add a workflow-tool PEX target and keep packaged `.cmd`/`.ps1` launchers in
    scope through `scripts/smoke-package-workflow-tools`.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests::`
  - `scripts/smoke-register-review-artifact`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-opponent-closeout`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `scripts/smoke-package-workflow-tools`

### Slice 9 - Wire Evidence Validators Into Opponent Closeout

- Status: pending
- Proposed commit message: `feat(workflow): include evidence validators in opponent closeout`
- Why: New validators only help if opponent closeout and manifest refresh record
  their status when the corresponding evidence artifacts exist.
- TODO source:
  - `TODO.md` lines 20-24 and 33-36
  - `TODO.md` lines 8-11 for deterministic closeout tests
- Expected paths:
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `src/thesis_review_workflow/cli/opponent_closeout.py`
  - `src/thesis_review_workflow/agent_coverage.py`
  - `src/thesis_review_workflow/cli/check_opponent_report.py`
  - `scripts/smoke-opponent-closeout`
  - `scripts/smoke-review-manifest`
- Tasks:
  - Register the new evidence validators as required checks only when their
    target evidence artifacts exist or are relied on by reviewed opponent
    materials.
  - Preserve current supervisor closeout behavior unless covered by explicit
    tests.
  - Ensure stale hashes or missing review records are surfaced before opponent
    report draft use.
  - Keep the opponent-report draft blocked on human calibration exactly as it is
    today; new evidence checks may add reasons to stop, not reasons to pass.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests::`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-agent-coverage`
  - `scripts/smoke-opponent-closeout`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `scripts/smoke-package-workflow-tools`
  - `pants run :omen`

### Slice 10 - Closeout Documentation And TODO Reconciliation

- Status: pending
- Proposed commit message: `docs(workflow): close opponent review value plan`
- Why: The selected TODO items should either be completed, explicitly deferred,
  or copied into narrower follow-up items once the implementation series lands.
- Expected paths:
  - `plans/opponent_review_value_plan.md`
  - `TODO.md`
  - `README.md`
  - `docs/opponent-review-workflow.md`
- Tasks:
  - Rerun opponent workflow smoke tests and lightweight repo checks.
  - Remove completed TODO bullets or replace them with narrower residual work.
  - Reconcile the deterministic-tests TODO by removing only the parts completed
    by this plan and preserving any remaining open coverage work in `TODO.md`.
  - Record deferred follow-up candidates: historical report comparison,
    video/demo inspection, sandbox execution workflow, expanded GitHub intake,
    literature-source collection automation, and advanced typography automation.
  - Record final developer-hygiene output, including Omen, as plan-closeout
    evidence rather than a case-pipeline requirement.
  - Archive this plan under `plans/archive/` after final audit.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants lint ::`
  - `pants check ::`
  - `pants test tests::`
  - `scripts/smoke-opponent-preflight`
  - `scripts/smoke-opponent-materials`
  - `scripts/smoke-opponent-report`
  - `scripts/smoke-opponent-closeout`
  - `scripts/smoke-package-workflow-tools`
  - `pants run :omen`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

## Deferred TODO Items

These TODO items are relevant but intentionally excluded from this V1 plan:

- Broader native Windows compatibility retrofit (`TODO.md` lines 5-7): this plan
  keeps Windows support mandatory for new commands, but defers migration of
  older POSIX-only maintenance smoke helpers.
- Full case-data contract and migrations (`TODO.md` lines 12-19): broad
  structural change, should have its own plan. This plan only defines the minimal
  schema/version contract for new opponent-review work artifacts it introduces.
- Supervisor preflight and closeout bundle (`TODO.md` lines 25-28): a different
  workflow surface.
- Student-code sandbox workflow (`TODO.md` lines 50-57): valuable but
  security/process heavy; V1 only classifies reproducibility.
- Evidence-resolved wording pass for student feedback (`TODO.md` lines 58-62):
  student-facing, not opponent-first.
- Standardized visual/media intake and demo/video workflow (`TODO.md` lines
  70-81): useful later after assignment coverage and evidence presence are
  stable.
- Figure/media graph and table quality checks (`TODO.md` lines 82-85): defer
  until the evidence-presence layer can route unresolved visual/result risks.
- Historical reference-report comparison (`TODO.md` lines 89-93): high value for
  calibration, but best as an optional follow-up once reviewed opponent materials
  are stable.
- Advanced typography automation, expanded GitHub intake, and literature-source
  collection automation (`TODO.md` lines 94-112): P2-level expansion.

The deterministic-tests TODO (`TODO.md` lines 8-11) is not deferred wholesale.
It is cross-cutting: each implementation slice must add focused tests for its
new helper, validator, or manifest contract, and Slice 10 reconciles only the
parts actually completed.

## Progress

- Slice 1: done - plan hardening and baseline
- Slice 2: done - work artifact and command surface contract
- Slice 3: done - static code reproducibility classification
- Slice 4: done - assignment coverage map
- Slice 5: done - evidence presence and media inventory
- Slice 6: done - thin validators for opponent evidence inputs
- Slice 7: done - role-specific opponent agent packets
- Slice 8: done - incremental opponent provenance helper
- Slice 9: pending - wire evidence validators into opponent closeout
- Slice 10: pending - closeout documentation and TODO reconciliation

## Decision Log

- 2026-05-06: Prioritized opponent-specific evidence quality over broad repo
  reliability work. Windows compatibility, case migrations, and supervisor
  closeout remain important but outside this plan.
- 2026-05-06: Kept historical reference-report comparison out of V1. It is
  useful for calibration only after reviewed opponent materials exist, not as
  primary evidence.
- 2026-05-06: Chose static reproducibility classification before a sandbox
  execution workflow, because opponent reports benefit immediately from fair
  reproducibility wording without adding code-execution risk.
- 2026-05-06: Plan review moved assignment coverage, evidence presence, and
  static reproducibility ahead of provenance/closeout wiring so implementation
  order matches opponent-report value ranking.
- 2026-05-06: New operator commands must update Pants/PEX packaging paths, not
  only POSIX `scripts/*` wrappers, to preserve Windows support.
- 2026-05-06: Added report-review consumption and Omen developer-hygiene
  evidence to the plan. These improve implementation closeout without making
  advisory artifacts into grading decisions or case-pipeline gates.
- 2026-05-06: Agent review moved minimal work-artifact schema and command-surface
  packaging ahead of new helpers, moved static code reproducibility before the
  evidence-presence aggregator, and narrowed the Windows/case-data defers to
  broader follow-up work rather than new-command obligations.

## Final Audit

Not run yet. This plan is active. Slice 1 baseline checks passed:

- `git diff --check`
- `scripts/check-private`
- `scripts/check-scripts`
- `pants run :omen` baseline: grade A, score 93.50, 3 critical hotspots, 7 high
  hotspots
