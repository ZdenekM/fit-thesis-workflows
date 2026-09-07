# Supervision Season Readiness Plan

Status: in_progress
Created: 2026-09-07

## Start Here

State: Slices 1 to 4 are done. The season gate is unblocked, an
operator-declared review phase travels from `review-round-start` into
materiality, coverage, closeout and both feedback checkers, the early phase
defers three late-phase roles and detects a predecessor round, early student
feedback has its own six-section shape, and the operator reading pass has one
template and one validated round path. Slice 6 and Slice 7 remain.

Next action: implement Slice 6, whose charter is already reviewed. Then charter
Slice 7, review it, and implement.

Do not read: the retrospective's per-case detail or the review transcripts.
Their conclusions are in `## Audit Base` and `## Decision Log`.

## Goal

Make this repository ready for the phase it has never run — early supervision of
a new cohort — and make the first early rounds produce reusable calibration
instead of chat history.

The completed season proved the late-phase pipeline: final feedback, supervisor
reports, opponent materials. Three things the next months need are not proven:
the early-draft phase cannot be declared or acted on, the supervisor-report
calibration workflow has never been run although the reports exist, and the
operator's own reading pass over a thesis has no tracked surface and landed in a
differently-named file each time.

## Audit Base

Retrospective measurements over the completed season, case-neutral. The round,
output, intake-identity and artifact-presence counts are reproducible with these
commands against the private case tree; the size, shape and note-provenance
readings come from the retrospective itself:

```bash
ls -d cases/*/rounds/*/ | wc -l
ls cases/*/rounds/*/outputs/ | grep -v '^$\|/$\|:' | sort | uniq -c | sort -rn
md5sum cases/*/rounds/*/notes/supervisor-intake.md | awk '{print $1}' | sort | uniq -c
find cases -name 'supervisor_report_calibration_profile.md' -o -name 'revision_diff.md'
```

- 32 rounds across the 17 cases that carry rounds; 29 carry at least one
  generated output. Excluding the topic-proposal round and the calibration
  round, 30 are thesis-review rounds, all dated between 2026-04-28 and
  2026-05-22. No round ran an early-draft phase.
- Iteration happened in 6 supervisor cases; 14 rounds followed a predecessor in
  the same case, and 4 of those produced `outputs/revision_diff.md`, although
  `docs/agent-profile-matrix.md` defines revision diff as a validated review
  role rather than an incidental artifact.
- Role frequency across all rounds: code quality 26, code consistency 25,
  typography 14, similarity 13, student feedback 13, literature 10,
  figure/media 9, GitHub intake 4.
- Sendable artifacts are 2-17 KB behind 36-140 KB of per-round evidence
  outputs. The funnel works; the ratio is not the problem.
- Student-facing feedback carried the same 12-section shape in every round of
  every iterated case, first round and final round alike; only length moved,
  from 17 KB down to 9.5 KB.
- Six of the ten opponent rounds carried operator notes. Four used the wired
  post-draft path `notes/opponent-report-operator-feedback.md` (0.8-15.8 KB),
  and at least one of those carried a reading pass rather than post-draft
  calibration. Three carried a reading pass with no tracked surface at all,
  under three different filenames (14-31 KB), one of them the unrelated
  `notes/opponent-report-review-intake.md` template pressed into service.
- Round scaffolding is kind-agnostic: 13 rounds carry a byte-identical unfilled
  `notes/supervisor-intake.md` — eight of the ten opponent rounds plus every
  final supervisor-report round, the latter having its own operator input file.
  The two remaining opponent rounds carry an older template revision.
- Inputs arrive unnormalized: two rounds store the same similarity report twice
  under two names and extract both copies, and filenames carry download
  suffixes and one broken-encoding name.

Code and configuration audit of the early-phase path:

- `config/supervisor-deadlines.tsv` carries only 2025/2026 rows. A probe case
  with `Academic year: 2026/2027` made
  `src/thesis_review_workflow/cli/supervisor_deadline.py::main` print
  "No supervisor deadline configured for academic year 2026/2027, work type BP"
  and exit 1, and `scripts/check-supervisor-ready` failed with it. Its
  `recommended_finish` column is what
  `src/thesis_review_workflow/cli/supervisor_deadline.py::calibration` prefers,
  so a row with that field blank would silently move phase guidance to the
  later official deadline.
- The phase cannot reach the workflow. `scripts/check-review-materiality`
  offers `--phase {auto,final,non_final}`;
  `src/thesis_review_workflow/review_materiality.py::infer_phase` honors an
  explicitly requested phase and falls back to `non_final` for
  `supervisor_feedback` when the request is `auto`. But neither
  `scripts/review-round-start` nor `scripts/prepare-review-round` exposes a
  phase, and
  `src/thesis_review_workflow/cli/prepare_review_round.py::refresh_materiality_before_packets`
  passes `--phase final` only for `supervisor_report`. So supervisor feedback
  always resolves to `non_final`, and an added enum value alone would be
  unreachable. The available carrier is `work/review_run_trace.json`, which
  `src/thesis_review_workflow/cli/prepare_review_round.py::infer_profile_from_trace`
  already reads; `--metadata` is not a carrier, because
  `scripts/review-round-start` documents that raw metadata values are not
  written to the trace.
- The five supervisor phases exist only as prose for the agent in
  `.agents/skills/thesis-supervisor-feedback/SKILL.md` `## Phase Calibration`.
- The opponent calibration loop is closed and current: the calibration round
  consumed all eight current opponent cases including the season's last
  operator corrections, and produced a version-3 profile, checklist, change log,
  append-only history and an independent profile review. Per
  `docs/historical-opponent-calibration.md`, `calibration_profile_owned`
  lessons belong in that profile and not in `profiles/local/`, so nothing is
  owed there.
- The supervisor side has the opposite state: `.agents/skills/historical-supervisor-report-calibration/SKILL.md`
  and `scripts/check-supervisor-report-calibration-profile` exist, the season
  produced five final supervisor reports, and no
  `supervisor_report_calibration_profile.md` or
  `work/calibration/supervisor_report/` exists anywhere.
- Per-round operator corrections already have a surface on both tracks:
  `scripts/record-review-delta` accepts `--profile supervisor_feedback` with
  `--type operator_preference`, promotion and rejected targets, privacy review
  and a redacted profile proposal ref, and
  `.agents/skills/thesis-supervisor-feedback-review/SKILL.md` already requires
  it for post-review corrections. `src/thesis_review_workflow/review_delta.py`
  names the append-only operator note only to forbid hashing it directly.
- `scripts/prepare-code-workspace` unpacks archives and copies code directories
  found under `inputs/`; it does not fetch a remote repository.
  `src/thesis_review_workflow/cli/import_github_code.py` already clones a
  standalone repository into `work/code`, records the selected ref and records a
  live-ref limitation. So the early-round gap is discoverability and defaults,
  not a missing capability.

Constraints:

- Private case contents, personal profiles and generated case outputs stay under
  ignored `cases/`; this plan and its tests use no case identifiers.
- `profiles/README.md` forbids personal strictness, grade tendencies, recurring
  reviewer phrasings and case-derived preferences in tracked
  `profiles/default.md`. One reviewer's corrections are not cross-reviewer
  evidence.
- Deterministic helpers may consume structured metadata, enums, paths and
  hashes. Phase-driven behavior must come from an explicit declared value, never
  from free-text inference over intake prose.
- Windows stays supported: any new or changed operator command needs the
  Python/PEX surface and generated `.cmd`/`.ps1` launchers per
  `docs/workflow-command-surface.md`.
- Pants commands run sequentially.

## Scope

Will touch:

- `config/supervisor-deadlines.tsv`, ignored `profiles/local/`.
- `src/thesis_review_workflow/review_materiality.py`,
  `src/thesis_review_workflow/cli/prepare_review_round.py`,
  `src/thesis_review_workflow/cli/review_round_start.py`,
  `src/thesis_review_workflow/review_pipeline_orchestration.py` and their tests.
- `.agents/skills/thesis-supervisor-feedback/SKILL.md`,
  `.agents/skills/thesis-supervisor-feedback-review/SKILL.md`, and the
  supervisor-side templates.
- A new template plus wiring for the operator reading pass.
- Round scaffolding and input import ergonomics.

Will not touch:

- Assignment and student-brief authoring, owned by
  `plans/assignment_authoring_plan.md`; see `## Decision Log`.
- The opponent pre-draft calibration checkpoint, owned by
  `plans/opponent_methodology_pipeline_plan.md` Slice 4.
- The external opponent-report postmortem loop, owned by
  `plans/supervisor_opponent_feedback_learning_plan.md`.
- Manifest, approval and closeout recovery mechanics, owned by
  `plans/review_manifest_closeout_repair_plan.md`.
- Case-format migration, owned by `plans/case_format_migration_contract_plan.md`.
- Tracked `profiles/default.md`, and the decision whether supervisor feedback
  needs its own applied-preference contract, which `TODO.md` owns.
- The late-phase role set. Nothing here weakens a final-round gate.

Non-goals:

- Automating the operator's judgment about phase. The operator declares it; the
  workflow carries and acts on it.
- A second GitHub intake design, and a second operator-correction ledger beside
  `scripts/record-review-delta`.

## Slices

### Slice 1 - Run the supervisor-report calibration that never ran

Charter form: compacted

Landed: see the commit titled `Route supervisor-report calibration lessons to their owners`.

The calibration workflow ran for the first time over the season's five final
supervisor reports: five per-case analyses by two authorized agents, a
version-1 profile with per-statement attestation counts, an eleven-item
checklist, history, change log, two independent anti-overfit review rounds, and
a passing `check-supervisor-report-calibration-profile`. Baseline and
methodology lessons went to their owners rather than into the profile. Full
charter in `plans/archive/supervision_season_readiness_plan/closed-slices-2026-09-07.md`.
Decisions: the `## Decision Log` entry of 2026-09-07 on the calibration run.

### Slice 2 - Carry an explicit early phase end to end, and unblock the season gate

Charter form: compacted

Landed: see the commit titled `Add 2026/2027 deadlines and carry an explicit early review phase`.

2026/2027 BP and DP deadline rows unblocked `check-supervisor-ready`, and an
operator-declared `review_phase` now travels from `review-round-start` through
`work/review_run_trace.json` into the materiality refresh, scoped to
`supervisor_feedback` and surviving reruns. Full charter in
`plans/archive/supervision_season_readiness_plan/closed-slices-2026-09-07.md`.
Decisions: `## Decision Log` entries of 2026-09-07 on the plan-critic round, the
narrow re-check, and the Slice 2 implementation review.

### Slice 3 - Early-phase role deferral and revision-diff detection

- Status: done
- Proposed commit message: `Defer late-phase roles in the early phase and detect a predecessor round`
- Why: Slice 2 made `early` declarable and carried it end to end, but it changes
  nothing — a test asserts its decision set equals `non_final`. An early round
  would summon typography, literature and figure review the moment their evidence
  exists, on material that does not exist yet. Separately, `## Audit Base`
  measured revision diff produced in 4 of the 14 rounds that followed a
  predecessor, with nothing in the pipeline noticing the predecessor at all.
- Expected paths: `src/thesis_review_workflow/review_materiality.py`,
  `src/thesis_review_workflow/cases.py`,
  `src/thesis_review_workflow/agent_coverage.py`,
  `src/thesis_review_workflow/review_pipeline_orchestration.py`,
  `src/thesis_review_workflow/cli/update_round_reuse_index.py`,
  `src/thesis_review_workflow/cli/review_round_closeout.py`,
  `src/thesis_review_workflow/cli/prepare_review_round.py`,
  `src/thesis_review_workflow/cli/review_round_start.py`,
  `tests/test_review_materiality.py`, `tests/test_review_pipeline_orchestration.py`,
  `tests/test_agent_coverage.py`, `docs/agent-profile-matrix.md`,
  `docs/operator-reference.md`
- Tasks:
  - Defer only `typography_formal`, `literature_citation` and `figure_media` in
    the early phase. `code_consistency` is NOT deferred: `review_profiles.py`
    gives every profile `code_bearing_roles = ("code_consistency",
    "code_quality")`, `review_pipeline_orchestration.py::code_bearing_contract`
    returns `blocked` unless both are satisfied when code evidence is present,
    and `AGENTS.md` requires both code reviews for a code-bearing round.
  - Implement the deferral as a filter after the evidence triggers that replaces a
    material decision with a non-material one carrying a scope that names the
    phase, so the round records why a role was deferred. This needs
    `not_material_decision` to accept a scope; today it hardcodes
    `scope="not_triggered"`. Keep that default for every existing caller.
  - Skip the filter for any decision whose scope is `explicit_request` or
    `existing_review_output`, so an operator request wins and an artifact the
    round already carries stays visible to synthesis.
  - Add `revision_diff` to `MATERIALITY_ROLES` and `MATERIALITY_ROLE_ARTIFACTS`
    (`outputs/revision_diff.md`), and add its impact string to every branch of
    `impact_for`, which raises `KeyError` for an unmapped role and is called by
    `not_material_decision` for every role in every profile.
  - Detect the predecessor with the existing structural contract rather than a new
    one: move `update_round_reuse_index.py::previous_round_ids` into
    `cases.py` unchanged — lexical sort over non-hidden round directories — and
    call it from both places. Mark `revision_diff` material when any earlier round
    carries the workflow's synthesis artifact from `SYNTHESIS_ARTIFACT_BY_WORKFLOW`.
  - State the limitation in `docs/operator-reference.md`: `ids.py` permits any safe
    id, so ordering is lexical and a case whose round ids are not
    timestamp-prefixed may order differently from its real chronology.
  - Scope this as advisory detection, not enforcement. Role records are built from
    packet roles in `review_pipeline_orchestration.py`, `revision_diff` has no
    producer role there, and `NEXT_ACTION_ROLES` covers only `github_intake`,
    `quantitative_claims` and `theses_similarity`. So this slice makes the
    predecessor visible in the materiality decision; wiring a required producer
    role or a next action is not in it.
  - Tests: the three roles are deferred in `early` with their evidence present;
    `code_consistency` and `code_quality` stay material in `early` with a code
    workspace, and `code_bearing_contract` still reports `satisfied`;
    `--request-role` and an existing review output both override the deferral;
    `revision_diff` is material when an earlier round carries
    `outputs/feedback_student.md` and not material in a first round;
    `impact_for` returns a string for `revision_diff` in all three profiles; and
    the `non_final` and `final` decision sets are unchanged for the existing eight
    roles. Replace the Slice 2 test asserting `early` equals `non_final` with one
    that gives the fixture triggering evidence, since an empty round is equal
    under both phases either way.
- Out of scope: the student-facing output shape (Slice 4); what any role does;
  a producer role, packet or next action for `revision_diff`; and any change to
  how `final` behaves.
- Verification:
  - `pants test tests/test_review_materiality.py tests/test_agent_coverage.py`
  - `pants test tests/test_review_pipeline_orchestration.py tests/test_review_round_closeout.py`
  - `pants test tests/test_round_reuse_index.py tests/test_agent_profile_contracts.py`
  - `pants lint src/thesis_review_workflow/ tests/`
  - `scripts/smoke-prepare-review-round`
  - `scripts/smoke-agent-coverage`
  - `scripts/smoke-review-round-closeout`
  - `scripts/smoke-round-reuse-index`
  - `scripts/check-scripts`
  - `python3 tests/test_plan_contract.py`

### Slice 4 - Early-phase feedback shape

Charter form: compacted

Landed: see the commit titled `Give early-phase student feedback its own shape and heading contract`.

A declared early phase now selects a six-section required-heading subset in
`check-feedback-language`, skips the checklist requirement and caps priorities at
five rows and two `P0` in `check-feedback-output`, and both skills carry the
reduced shape with the omission rule marked reviewer-enforced. The two feedback
checkers gained their first pytest coverage and the output smoke gained
early-phase cases. Full charter in
`plans/archive/supervision_season_readiness_plan/closed-slices-2026-09-07.md`.
Decisions: the `## Decision Log` entry of 2026-09-07 on the same lesson one gate
further down.

### Slice 5 - Operator reading-pass intake

Charter form: compacted

Landed: see the commit titled `Give the operator reading pass one template and one wired round path`.

The supervisor's dictated reading pass now has one tracked template, the
canonical round path `notes/supervisor-reading-pass.md`, a structural validator
chained inside `check-supervisor-ready` that an absent file passes, and a
four-value routing enum in which only `student_feedback` permits student-facing
use. `supervisor_reading_pass.py` owns the path, the enum and the parser; nine
consumers read them from there, bound by one test. Full charter in
`plans/archive/supervision_season_readiness_plan/closed-slices-2026-09-07.md`.
Decisions: the `## Decision Log` entry of 2026-09-07 on the reading-pass
implementation review.

### Slice 6 - Early code surface

- Status: charter
- Proposed commit message: `Declare a GitHub-only code source and make the intake its next action`
- Why: `## Audit Base` measured GitHub intake in 4 rounds while code quality ran
  in 26, and established the capability is not missing:
  `cli/import_github_code.py` already clones a standalone repository, records the
  selected ref and records a live-ref limitation. The gap is what an early round
  declares. `review_materiality.github_structured_refs` marks `github_intake`
  material only once `inputs/github` or `work/github-intake` exists, and
  `code_consistency` and `code_quality` only once a prepared workspace exists. So
  a round whose only code is a live repository is silent - no material role, no
  next action, no typed limitation - and `scripts/prepare-code-workspace` finds
  nothing to say. Early rounds are exactly that shape, because a submitted
  archive does not exist yet.
- Expected paths: `src/thesis_review_workflow/review_materiality.py`,
  `src/thesis_review_workflow/review_pipeline_orchestration.py`,
  `src/thesis_review_workflow/code_workspace.py`,
  `src/thesis_review_workflow/cli/review_round_start.py`,
  `src/thesis_review_workflow/cli/prepare_review_round.py`,
  `src/thesis_review_workflow/cli/review_round_closeout.py`,
  `src/thesis_review_workflow/cli/prepare_code_workspace.py`,
  `src/thesis_review_workflow/cli/case_doctor.py`,
  `tests/test_review_materiality.py`,
  `tests/test_review_pipeline_orchestration.py`,
  `tests/test_review_round_closeout.py`, `tests/test_case_doctor_summary.py`,
  `docs/operator-reference.md`, `docs/agent-profile-matrix.md`,
  `.agents/skills/thesis-supervisor-feedback/SKILL.md`,
  `.agents/skills/thesis-github-code-intake/SKILL.md`
- Tasks:
  - Add `--code-source {auto,github}` to `review-round-start` and
    `prepare-review-round`, with `auto` the default meaning undeclared, mirroring
    `--review-phase`. Only values that change behavior exist: the Slice 2 review
    found an added enum value with no reachable behavior, and `archive` and
    `none` would be exactly that, since evidence detection already covers an
    archive and a round with no code already produces no code roles.
  - Carry it as the round-level trace field `code_source` beside `review_phase`,
    through `build_review_run_trace_payload` and
    `validate_review_run_trace_payload`. Unlike the phase it applies to every
    profile - a GitHub-only submission is not specific to supervisor feedback -
    so it gets no out-of-scope rejection guard.
  - One owner: `declared_code_source_from_trace` in `review_materiality.py`,
    beside `declared_review_phase_from_trace`, with the same contract that an
    undeclared value is the documented default and not an error.
  - Resolve flag-or-trace once and re-emit the value in the recorded invocation,
    in the closeout recovery command, and through closeout's schema-mismatch
    trace rebuild - the three places where the Slice 2 review found
    `review_phase` erased.
  - Materiality: when the declared source is `github` and
    `github_structured_refs` is empty, mark `github_intake` material with scope
    `declared_github_code_source` and the synthetic source ref
    `code-source:github`, adding that prefix to `ALLOWED_SYNTHETIC_REFS`. The
    existing `github_intake` entry in `NEXT_ACTION_CONFIG` already carries the
    `import-github-code` command and the `thesis-github-code-intake` skill, so
    the next action comes from the machinery that exists.
  - Charter the consequence rather than calling this discoverability. Reused
    next actions are built with `severity="required"`, `review_wave_gate` turns
    an unresolved one into a wave error, and
    `cli/supervisor_report_closeout.py` blocks on unresolved final actions. So a
    declared `github` round cannot pass its wave or close until either the intake
    artifact exists or an accepted typed limitation with scope `github_intake` is
    recorded. That is the intended discipline - a declaration the operator made
    and then ignored should not pass silently - and the escape already exists, so
    this slice adds no new escape hatch. It also means the declaration must not
    be made casually on a late round.
  - Leave `code_consistency` and `code_quality` declaration-independent. Making
    them material on a declaration alone would make
    `review_pipeline_orchestration.code_bearing_contract` block a round whose
    code has not been fetched yet, which inverts the intent.
  - Close the empty-preparation trap that would otherwise defeat that premise.
    `code_workspace.prepare_workspace` calls `write_workspace_manifest` and
    `write_report` unconditionally, so a run that prepares zero sources still
    creates `work/code/.prepare-code-workspace-manifest.json` and
    `work/code_workspace.md` - two of the three `CODE_WORKSPACE_PATHS` markers
    materiality tests with a bare existence check. Today that already makes both
    code roles material with no code present; on a GitHub-only round it is the
    operator's first move. Give `code_workspace.py` one exported predicate over
    the manifest's recorded sources - the module already exposes
    `manifest_sources` and `workspace_source_fingerprint_records` - and have
    `review_materiality` require it instead of bare existence.
    `code_workspace.py` imports no module that imports materiality, so the
    direction is cycle-free.
  - `prepare-code-workspace`: when it prepares no source, print the declared code
    source when there is one and the `import-github-code` pointer either way,
    instead of ending with no next step. The behavior lives in
    `code_workspace.py`; `cli/prepare_code_workspace.py` only forwards to it.
  - `case-doctor`: report the declared code source beside the existing
    code-evidence line, so the read-only snapshot shows a declaration that has
    not been acted on.
  - Docs and skills: `docs/operator-reference.md` documents the flag and that a
    live repository ref is a moving target rather than a submitted artifact,
    `docs/agent-profile-matrix.md` records the new `github_intake` trigger, and
    the code step of `thesis-supervisor-feedback` plus
    `thesis-github-code-intake` name the declaration.
  - Tests: a declared `github` with no evidence makes `github_intake` material
    and produces its unresolved next action, the wave gate reports it as an
    error, and an accepted typed limitation with scope `github_intake` clears
    both; a declaration alongside existing GitHub evidence changes nothing;
    `code_consistency` and `code_quality` stay non-material after a
    zero-source `prepare-code-workspace` run while a run with one prepared source
    still makes them material and keeps `code_bearing_contract` satisfied; a
    flagless rerun preserves the value; closeout's rebuild preserves it; the
    trace validator rejects an unknown value; and the dry-run CLI writes it to
    disk.
- Out of scope: PR-contribution depth, which `TODO.md` owns; any change to
  `cli/import_github_code.py` or to `scripts/prepare-code-workspace`'s copying
  and unpacking; a second intake design; and archive-versus-GitHub authority,
  which `AGENTS.md` already settles.
- Verification:
  - `pants test tests/test_review_materiality.py tests/test_review_pipeline_orchestration.py`
  - `pants test tests/test_review_round_closeout.py tests/test_case_doctor_summary.py`
  - `pants test tests/test_agent_coverage.py tests/test_github_intake.py`
  - `pants test tests/test_review_wave_gate.py tests/test_code_reproducibility.py`
  - `pants lint src/thesis_review_workflow/ tests/`
  - `scripts/smoke-prepare-review-round`
  - `scripts/smoke-prepare-code-workspace`
  - `scripts/smoke-github-code-intake`
  - `scripts/smoke-review-round-closeout`
  - `scripts/smoke-case-doctor`
  - `scripts/check-scripts`
  - `python3 tests/test_plan_contract.py`

### Slice 7 - Round scaffolding and input ergonomics

Charter form: stub

Objective: kind-aware round scaffolding instead of every intake template in
every round, plus input normalization at import: identical-file dedup, stable
filenames, original name kept in provenance.

Boundary: ergonomics only; the case layout contract stays with its own plan.

Serves: every round of the new season.

## Progress

Slices 1 to 4 are done. Slice 1 produced a supervisor-report calibration profile
at version 5, `reviewed_with_notes`, gated to BP reports in the A and B bands and
backed by a deterministic correction ledger; its calibration content is seven
correction patterns, seven of eight carrying a counter-attestation, and the
private profile layer carries only a pointer. Slice 2 added the 2026/2027 BP and
DP deadline rows and the `review_phase` carrier from `review-round-start` through
the run trace into the materiality refresh. Slice 3 deferred `typography_formal`,
`literature_citation` and `figure_media` in the early phase, kept both code roles
mandatory, and made a predecessor round visible as `revision_diff` materiality.
Slice 4 gave early student feedback a six-section heading contract, dropped the
checklist requirement and capped priorities at five rows and two `P0`, enforced
by both feedback checkers.

Every slice's verification block ran green, including `pants run :omen` for
Slice 2 (grade A, 0 critical). Eleven review rounds are adjudicated in
`## Decision Log`.

Slice 5 is done: one template, one validated round path, a binding routing enum
and nine wired consumers. Its verification block ran green, including the full
`pants test tests::` sweep and `pants run :omen` (grade A, 0 critical). Slice 6
carries a reviewed full charter and is next. Slice 7 remains a stub.

## Decision Log

### 2026-09-07 - This plan is created `planned`, not `in_progress`

Trigger: the session-start hook reports two `in_progress` plans, which the plan
contract does not allow, and this would be a third.

- `plans/assignment_authoring_plan.md` is seasonally urgent: the operator is
  writing assignments now, and its Slice 1 charter is the declared next action.
- `plans/supervisor_opponent_feedback_learning_plan.md` has Slices 3-4 still
  `planned` and no external opponent report pending, so its work is paused
  rather than blocked.

Decision: this plan starts `planned`; the operator chooses which single plan
holds `in_progress`. Why: the contract's one-active-plan property is what makes
`## Start Here` trustworthy, and resolving it by fiat would pick the operator's
priority for them.

Residual risk: the conflict persists until answered. Recorded here so it cannot
be lost.

### 2026-09-07 - Assignment authoring stays in its own plan

Trigger: the retrospective produced six improvement items, one of which is
"continue assignment authoring", and folding it in would have merged two plans.

- That work already has a plan with Slice 0 closed, a probe, eight adjudicated
  findings and its own decision log.
- Its three-layer style decision is a constraint on this plan's Slice 1, not a
  duplicate: both write into the same profile structure.

Decision: assignment authoring and student briefs stay out of scope here, cited
as a dependency. Why: two plans over one artifact set would need cross-plan
sequencing text that neither plan could keep honest.

### 2026-09-07 - Slice 1 re-derived: the unrun calibration is the supervisor one

Trigger: parent verification before the review round contradicted this plan's
first premise, that season calibration had never reached the profile layer.

- The opponent calibration round consumed all eight current opponent cases and
  produced a version-3 profile with an independent review; evidence in the
  calibration case's `work/calibration/` artifacts and `outputs/`.
- `docs/historical-opponent-calibration.md:63` makes calibration-profile-owned
  lessons belong in that profile, so none was ever owed to `profiles/local/`.
- No `supervisor_report_calibration_profile.md` or
  `work/calibration/supervisor_report/` exists, although the skill, the checker
  and five final supervisor reports do.

Decision: Slice 1 becomes running the supervisor-report calibration workflow and
routing its lessons by ownership. Why: the measured gap is an unrun workflow,
not an unpromoted lesson.

Residual risk: the run may find little to calibrate from five reports; the
ownership triage still produces the routing decisions.

### 2026-09-07 - Plan-critic round 1: eight findings, all accepted

Trigger: `scripts/agent-review --profile plan-critic --staged`, verdict
`changes_required`. Every finding was reproduced against the tree before folding in.

- P1 phase unreachable, `prepare_review_round.py:122`: accepted, Slice 2 builds the trace carrier.
- P1 tracked-default leak, `profiles/README.md:35`: accepted, Slice 1 is private-layer only.
- P1 duplicate correction ledger, `record_review_delta.py:35`: accepted, old Slice 6 dropped.
- P1 opponent overlap, `opponent_methodology_pipeline_plan.md:726`: accepted, Slice 5 is supervisor-only.
- P1 deadline row underspecified, `supervisor_deadline.py:101`: accepted, every column required.
- P2 revision-diff finding unowned: accepted, the role moves into Slice 3.
- P2 scaffolding slice had no audit base: accepted, the measurements were added.
- P2 false code-workspace premise, `code_workspace.py:657`, and unreproducible
  counts: accepted, premise corrected, Slice 6 narrowed, commands added.

Decision: all eight accepted, six changing what gets built. Why: each was
reproducible. Per `plans/README.md` a narrow re-check of this fix batch is owed
before Slice 1, scoped to the fixes only.

### 2026-09-07 - Narrow re-check of the fix batch closes the chain

Trigger: the owed re-check of the eight fixes, run as a read-only internal
reviewer because a fix answering a cross-provider round is not re-reviewed
across providers. Verdict `changes_required`; every defect reproduced.

- All eight fixes present, two with false glosses. Counts wrong: cases with
  rounds is 17 not 18, and the review span ends 2026-05-22, because 2026-05-25
  is the excluded calibration round.
- The identical-intake gloss overreached: 8 of 10 opponent rounds, the rest on an
  older template. The reproducibility lead-in claimed every count over four commands.
- Slice 2 named a nonexistent `tests/test_review_pipeline.py` and its deadline
  test had no owning file: `tests/test_supervisor_ready.py` added. Slice 1 named
  the opponent-side smoke, not `scripts/smoke-supervisor-report-calibration-profile`.
- `review_pipeline_orchestration.py:211` already uses `phase` per trace event,
  so the new field is `review_phase`.

Decision: all fixed in this batch; the chain ends here, no third round. Why: the
stopping rule caps a chain at one round plus one re-check, and these were prose
and command exactness, not scope errors.

### 2026-09-07 - This plan takes `in_progress`; Slice 2 runs before Slice 1

Trigger: the operator directed work to this plan and supplied the 2026/2027 BP
and DP submission dates, which was Slice 2's only missing input.

- The two previously active plans are demoted to `planned`: neither is being
  executed right now, and the session-start hook blocks plan work while more
  than one plan claims `in_progress`.
- Slice 1 runs a semantic calibration workflow over private supervisor reports,
  which `AGENTS.md` and its skill both gate behind explicit agent authorization
  in the current request. That authorization has not been given.
- Slice 2 is deterministic config, code and tests, and Slice 1's dependency on
  it is soft: its lessons inform Slices 3-4, not Slice 2.

Decision: this plan is `in_progress`, Slice 2 executes first, and Slice 1 waits
for authorization. Why: the cheapest unblocked slice runs rather than the queue
stalling on a permission.

Residual risk: assignment authoring shows `planned` while the operator may still
be writing assignments; one status line flips it back.

### 2026-09-07 - Slice 2 implementation review: seven findings, all fixed

Trigger: independent read-only review of the Slice 2 diff, the Claude-internal round of the
funnel; the cross-provider round was spent on the plan. Verdict `changes_required`.

- P2 a rerun erased the declaration, because `write_trace` rebuilds the trace and closeout printed a recovery command without the flag: the phase is now resolved once from flag-or-trace and the recovery command carries it.
- P2 no test covered the CLI-to-trace hop: the dry-run CLI test now asserts `review_phase` on disk, a flagless rerun, and the out-of-scope rejection.
- P2 a declared phase was forwarded for opponent profiles, overriding their intrinsic `final`: added `reject_out_of_scope_review_phase` plus a materiality-profile guard in the refresh.
- P3 `early` is behaviorally identical to `non_final` and one assertion was vacuous: the test now asserts that identity so Slice 3 must change it, and the docs no longer claim calibration.
- P3 closeout's schema-mismatch rebuild dropped the field, the trace's recorded invocation omitted the flag, and no test drove `supervisor-deadline` for the new year: all three fixed.

Decision: all seven fixed in this batch and the chain ends here. Why: five were
one-line contract fixes and two were test gaps; none changed the slice's shape.

### 2026-09-07 - Slice 4: the same lesson, one gate further down

Trigger: the implementation review found the Slice 3 defect shape again — a phase
honoured by the heading checker and rejected by `check-feedback-output`, which
runs in both wave gates, both closeout gates and the manifest check.

- `check_checklist` demanded its section unconditionally, so this slice's shape
  would have failed every gate below it. The charter listed that file and the
  first implementation did not touch it.
- The priority cap turned out code-enforceable: the labels are already parsed.
- The reviewer skill mandated the twelve-section structure in `## Output` while
  its new step narrowed it, and two numbered steps required omitted sections.
- Inserting the new skill section above the shared `Priority:` rules had scoped
  them to the early phase; they now have their own heading.

Decision: every gate reading the artifact's shape reads the declared phase from
the same owner, and the smoke gained the phase coverage whose absence hid the
gap. Why: a third instance of one defect shape is a signal about the sweep.
Residual risk: omitting a section rather than filling it stays reviewer-enforced;
no checker can tell a thin section from an honest one.

### 2026-09-07 - Slice 3: the declared phase needed one owner, not one consumer

Trigger: two review rounds found the same defect shape — a phase honoured in one
place and ignored in the next.

- Charter round: `code_consistency` cannot be deferred, since the code-bearing
  contract blocks without it; `impact_for` raises `KeyError` for an unmapped role;
  predecessor detection reuses `previous_round_ids` rather than assuming timestamps.
- Implementation review: the deferral stopped at packet preparation.
  `agent_coverage.py::inferred_role_specs` still demanded the deferred outputs and
  closeout reran materiality at `final`, so declaring `early` made a round fail its
  own closeout.
- A test caught a third: the existing-output exemption keyed off decision scope,
  which `merge_material` overwrites.

Decision: `declared_review_phase_from_trace` moved into `review_materiality.py`
and every consumer reads it there. Why: a phase honoured by one consumer is worse
than none, because it makes a round fail a gate it used to pass. Residual risk: the
deferral binds only `figure_media` today, since typography is final-only and
literature needs an existing output, which is exempt.

### 2026-09-07 - Slice 1 closeout: five review rounds and one instrument

Trigger: the profile reached version 5 through five review rounds and two roles.

- Rounds 1-3, one role: a fabricated ceiling quotation, ten attestation defects in
  the fix, then a measurement comparing drafts carrying a template header against
  finals; prose deltas are -2, 0, -3, -67, -5. The operator then chose a short true
  profile, so version 3 dropped the descriptive inventory as calibration.
- Rounds 4-5, a fresh role: two confirmed corrections were missing while the
  profile claimed none touched grading, post-review edits were undercounted, and
  no counter-attestation search had run. Seven of eight patterns have one.
- The third measurement correction triggered the instrument rule:
  `work/supervisor_report_correction_ledger.json` now computes what the profile
  counted by hand.

Decision: version 5 is `reviewed_with_notes` with its own repairs unreviewed, and
the chain closed under the stopping rule, not by convergence. Why: every round
found a defect in the text answering the previous one, so the next place to catch
errors is real use. Residual risk: the calibration content rests on two confirmed
cases, because four of five finals are this workflow's own approved output.

### 2026-09-07 - Slice 1 calibration run: what the corpus could and could not support

Trigger: the first run of the supervisor-report calibration workflow over the
season's five final reports, with explicit agent authorization.

- Round 1: four P0s, including a fabricated Czech ceiling quotation whose wording
  inverted the supervisor's meaning; all reproduced against the primary reports.
- Round 2: ten notes in the attestation layer the rewrite added; nine closed in
  the same pass, one a partial false positive because the counts it called
  approximations were `wc -w` measurements it had no shell to reproduce.
- Corpus is BP-only, A and B bands only, code-bearing only, and four of five
  intakes are dated the same day as their report.
- Routed away from the profile: two evidence rules to the supervisor-report
  skill, unclosed-round visibility to `TODO.md`, a stale-manifest instance to
  the repair plan.

Decision: version 1 is `reviewed_with_notes` and applicability-gated; the private
layer carries only a pointer. Why: a corpus that cannot separate house style from
a one-off instruction must not become an always-on preference. Residual risk:
four operator questions are recorded in the review rather than answered.

### 2026-09-07 - Charter round for Slices 5 and 6: five findings, all accepted

Trigger: one `plan-critic` round over both charters, `changes_required`; every
finding reproduced against the tree.

- P1 the private-markdown check has no `templates/` exception, so a template
  sharing the round basename fails `check-private`. Renamed with `-intake`.
- P2 the GitHub declaration is not discoverability: reused next actions carry
  `severity="required"`, so a declared round is blocked by the wave gate and by
  supervisor-report closeout until the intake exists or a typed limitation is
  accepted. Kept, now chartered as enforcement with its existing escape.
- P2 a zero-source `prepare-code-workspace` run already writes two of the three
  markers materiality tests by existence, making both code roles material with no
  code. Slice 6 closes it, keyed on the manifest's sources.
- P2 `verify_first` had no successful outcome; verification now upgrades the item
  by replacing the unverified token with the confirming anchor. P3 my Progress
  edit duplicated the plan body, matching its mention in `## Start Here`.

Decision: all five accepted, three changing what gets built. Why: each was
reproducible. The lint gap that let a duplicated body pass goes to `TODO.md`.

### 2026-09-07 - Slice 5: the enum was defeatable by a backtick

Trigger: the implementation review, plus three consumers the parent found first.
Eleven findings, all accepted, every one reproduced.

- Two P1s in the one rule the enum exists for: an unverified observation routed
  to `student_feedback` passed when the token carried backticks or a full stop,
  and blocks outside `## Poznamky` parsed as absent while the gate said usable.
  Both now normalize and fail loudly; a `####` block no longer merges into its
  parent, and a self-correction leaving two `Routing:` lines is an error.
- Nine consumers, not the chartered five. Missing were the packet base inputs,
  its first role's inputs, the common briefing, and the manifest helper
  dependency hashes; without the last, a recorded pass stayed fresh.
- `verify_first` had no recorded outcome, so its review check was vacuous for an
  anchored-but-unconfirmed claim. Promotion is now the routing value itself. The
  owner is a dedicated module, not `paths.py`: it carries the parser too.

Decision: all fixed in one batch; the binding test enumerates all nine. Why: a
declared value with one owner is only worth having if every consumer reads it
there, and this slice needed three passes to find them.

## Final Audit

Not reached. On closure this section records: the commands run per slice, the
first early-phase round that exercised Slices 2-4 end to end, whatever residual
items were copied into `TODO.md`, and the archive decision.
