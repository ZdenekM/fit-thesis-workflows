# Closed Slice Charters - Supervision Season Readiness Plan

Append-only. Each entry is the charter as it stood when the slice closed.

### Slice 2 - Carry an explicit early phase end to end, and unblock the season gate

- Status: done
- Proposed commit message: `Add 2026/2027 deadlines and carry an explicit early review phase`
- Why: the readiness gate fails for the new academic year, and the phase that
  every later slice keys on cannot reach the deterministic layer at all. Adding
  the enum value without its carrier would produce unreachable code, so the
  carrier and the enum land together with end-to-end tests.
- Expected paths: `config/supervisor-deadlines.tsv`,
  `src/thesis_review_workflow/review_materiality.py`,
  `src/thesis_review_workflow/review_pipeline_orchestration.py`,
  `src/thesis_review_workflow/cli/review_round_start.py`,
  `src/thesis_review_workflow/cli/prepare_review_round.py`,
  `src/thesis_review_workflow/cli/review_round_closeout.py`,
  `tests/test_review_materiality.py`,
  `tests/test_review_pipeline_orchestration.py`,
  `tests/test_supervisor_ready.py`, `tests/BUILD`, `config/BUILD`,
  `docs/operator-reference.md`, `docs/workflow-command-surface.md`
- Tasks:
  - Add 2026/2027 BP and DP rows with every column filled from
    operator-supplied values: `official_deadline`, `recommended_finish`,
    `deferred_window`, `notes`. Do not guess or leave a field blank; stop for
    the operator when a value is unknown, because a blank `recommended_finish`
    silently retargets calibration to the official deadline.
  - Add an `early` phase to the materiality phase set, plus a
    `DECLARABLE_PHASES` set for the phases an operator may declare, which the
    `check-review-materiality`, `review-round-start` and `prepare-review-round`
    argument surfaces derive their choices from.
  - Add an explicit review-phase option to `scripts/review-round-start`, persist
    it as a validated top-level `review_phase` field of
    `work/review_run_trace.json` — `phase` is already taken by the per-event
    `review_pipeline_orchestration.py::TracePhase` — and read it in
    `prepare_review_round.py::refresh_materiality_before_packets` so the
    materiality refresh passes the declared phase instead of defaulting to
    `auto`. Keep `supervisor_report` pinned to `final`.
  - Add a pass-through phase option to `scripts/prepare-review-round` for a
    round whose trace predates the field. Make the refresh helper's phase
    parameter required rather than defaulting, so a future call site cannot
    silently drop the declared phase, which is the failure the charter review
    found.
  - Give `config/supervisor-deadlines.tsv` a `files` target and depend on it
    from `tests/BUILD`, so a test can assert the shipped configuration rather
    than a fixture copy of it.
  - Extend the tests: `early` is accepted end to end from round start to the
    materiality decision, an absent field still resolves as today, an unknown
    phase still errors, and a 2026/2027 case reaches a passing
    `check-supervisor-ready` with a recommended-finish-based calibration line.
  - Regenerate the packaged launchers if the command surface changed, and note
    the new option and the deadline prerequisite in `docs/operator-reference.md`.
- Out of scope: the early-phase role set (Slice 3), the feedback output shape
  (Slice 4), inference of the phase from round contents, and any change to how
  `final` behaves.
- Verification:
  - `pants test tests/test_review_materiality.py`
  - `pants test tests/test_review_pipeline_orchestration.py`
  - `pants test tests/test_supervisor_ready.py`
  - `scripts/smoke-prepare-review-round`
  - `scripts/smoke-review-round-start`
  - `pants test tests/test_workflow_python_contracts.py tests/test_work_artifacts.py`
  - `pants test tests/test_review_round_closeout.py tests/test_closeout_preflight.py`
  - `scripts/smoke-review-round-closeout`
  - `pants lint` over the touched modules and tests
  - `pants run :omen` as dev-hygiene evidence, since code changed materially
  - `scripts/check-scripts`
  - `python3 tests/test_plan_contract.py`

### Slice 1 - Run the supervisor-report calibration that never ran

- Status: done
- Proposed commit message: `Route supervisor-report calibration lessons to their owners`
- Why: the season produced five final supervisor reports and the calibration
  workflow for them has never been exercised, so the next cohort's reports start
  from an uncalibrated baseline while the opponent track already runs at profile
  version 3. This slice needs no new code, and its lessons decide whether any
  later slice is even needed.
- Expected paths: ignored `cases/<supervisor-calibration-case>/`, ignored
  `profiles/local/default.md`, `TODO.md`,
  `.agents/skills/thesis-supervisor-report/SKILL.md`,
  `plans/review_manifest_closeout_repair_plan.md`
- Tasks:
  - Follow `.agents/skills/historical-supervisor-report-calibration/SKILL.md`
    against the season's final supervisor-report rounds: per-case analyses,
    synthesized profile, profile metadata, checklist, history entry, change log,
    and the independent anti-overfit review it requires.
  - Triage every candidate lesson by ownership exactly as the opponent workflow
    does: baseline-workflow-owned, methodology-owned, calibration-profile-owned,
    or do-not-duplicate.
  - Keep calibration-profile-owned lessons in the calibration artifacts, and
    durable personal style in ignored `profiles/local/default.md`. Do not touch
    tracked `profiles/default.md`: this season is one reviewer's evidence, which
    `profiles/README.md` excludes from the tracked default.
  - Promote a baseline or methodology lesson directly to its active owner —
    skill, doc, template, or `TODO.md`. Use `WORKFLOW_MEMORY.md` only for a
    lesson that is not yet an active rule, never as a parking lot for one.
  - Record in `## Progress` which lessons were rejected as case-specific, and
    whether any early-phase slice below changed as a result.
- Out of scope: the opponent calibration profile, which is current; tracked
  `profiles/default.md`; a new correction ledger; and any change to the
  supervisor-report skills themselves.
- Verification:
  - `scripts/check-supervisor-report-calibration-profile <calibration-case-id>`
  - `scripts/smoke-reviewer-profile`
  - `scripts/check-private`
  - `python3 tests/test_plan_contract.py`

### Slice 4 - Early-phase feedback shape

- Status: done
- Proposed commit message: `Give early-phase student feedback its own shape and heading contract`
- Why: `## Audit Base` measured the same 12-section shape in every round of every
  iterated case, first round and final alike, with only length moving from 17 KB
  to 9.5 KB. A student with a chapter skeleton receives the artifact designed for
  a submission check. The shape is not only convention: `check_feedback_language`
  holds fixed `CS_REQUIRED_HEADINGS` and `EN_REQUIRED_HEADINGS` lists and requires
  every heading, and `check_feedback_output` invokes it, so a skill instruction to
  omit a section would produce feedback that fails its own gate.
- Expected paths: `.agents/skills/thesis-supervisor-feedback/SKILL.md`,
  `.agents/skills/thesis-supervisor-feedback-review/SKILL.md`,
  `src/thesis_review_workflow/cli/check_feedback_language.py`,
  `src/thesis_review_workflow/cli/check_feedback_output.py`,
  `src/thesis_review_workflow/cli/init_review_manifest.py`,
  `scripts/smoke-feedback-output`,
  `tests/test_feedback_shape.py` (new: the two feedback checkers have no pytest
  coverage today, only `scripts/smoke-feedback-language` and
  `scripts/smoke-feedback-output`), `docs/operator-reference.md`
- Tasks:
  - Make the heading contract phase-aware: an early-phase required-heading set
    that is a subset of the existing one, selected from the declared
    `review_phase` in `work/review_run_trace.json`, with the existing set as the
    default when no phase is declared. Language selection and the diacritics rule
    stay exactly as they are; only the section requirement moves.
  - Add an early-phase output shape to the feedback skill beside the existing one:
    which sections are written, which are omitted outright rather than filled with
    a placeholder, and a priority cap so an early round cannot ship a full
    late-phase action list.
  - State in the skill that the shape follows the declared phase rather than the
    agent's impression of the draft, and that a role Slice 3 defers must not
    reappear as a feedback item.
  - Keep the iteration rules intact: an early second round still compares against
    the previous round and still must not repeat addressed feedback.
  - In the reviewer skill, add the check that the shape matches the declared phase
    and that no deferred role's findings leaked into the feedback.
  - Enforce the priority cap in `check_feedback_output.py::check_priority_table`
    rather than leaving it to the skill: the labels are already parsed there, so
    five rows and two `P0` is three lines of deterministic code.
  - Guard `check_checklist` on the phase. The early shape omits the checklist
    section, and that checker runs in both wave gates, the closeout gates and the
    manifest-completeness check, so without the guard declaring the phase makes a
    round fail gates an undeclared round passes.
  - Add `work/review_run_trace.json` to the manifest dependency hashes for both
    feedback checks, since the declared phase now decides their verdict.
  - Tests: an early-shape file passes with a declared early phase and fails
    without one and under a later declared phase; a late-shape file still passes
    in every phase; an early file missing a required early heading fails; the
    diacritics and cross-language rules behave identically in both phases; the
    early caps fire at six rows and three `P0`; a late round keeps the wider
    allowance; and `required_headings` rejects an unsupported language. Add the
    same early cases to `scripts/smoke-feedback-output`, which had no phase
    coverage and is why the checklist gap was missed once.
  - Note the two shapes in `docs/operator-reference.md`.
- Out of scope: any change to the late-phase heading set or shape;
  `outputs/feedback_student.md` as a path; the feedback-language selection
  contract; and the operator reading-pass intake, which is Slice 5.
- Verification:
  - `pants test tests/test_feedback_shape.py tests/test_review_manifest_helpers.py`
  - `pants lint src/thesis_review_workflow/ tests/`
  - `scripts/smoke-feedback-output`
  - `scripts/smoke-review-wave`
  - `scripts/smoke-review-round-closeout`
  - `scripts/smoke-feedback-language`
  - `scripts/check-scripts`
  - `python3 tests/test_plan_contract.py`

### Slice 5 - Operator reading-pass intake

- Status: done
- Proposed commit message: `Give the operator reading pass one template and one wired round path`
- Why: `## Audit Base` measured three rounds carrying a pre-draft reading pass
  under three different filenames at 14-31 KB each, one of them the unrelated
  `notes/opponent-report-review-intake.md` template pressed into service. It is
  the largest unshaped operator input of the season, and the workflow does not
  know the file exists: it reaches no packet, no evidence snapshot, no leak
  pattern and no privacy pattern. The opponent track has a wired post-draft
  surface in `notes/opponent-report-operator-feedback.md`; the supervisor
  pre-draft reading pass has no equivalent. The notes are also not hand-written
  prose but dictation an agent formalized, so a fixed shape costs the operator
  nothing.
- Expected paths: `templates/supervisor-reading-pass-intake.md`,
  `src/thesis_review_workflow/paths.py`,
  `src/thesis_review_workflow/structured_evidence.py`,
  `src/thesis_review_workflow/review_delta.py`,
  `src/thesis_review_workflow/cli/check_supervisor_reading_pass.py`,
  `src/thesis_review_workflow/cli/check_supervisor_ready.py`,
  `src/thesis_review_workflow/cli/check_feedback_output.py`,
  `src/thesis_review_workflow/cli/check_opponent_materials.py`,
  `src/thesis_review_workflow/cli/check_private.py`,
  `src/thesis_review_workflow/cli/case_doctor.py`,
  `src/thesis_review_workflow/commands.py`,
  `src/thesis_review_workflow/cli/BUILD`, `scripts/check-supervisor-reading-pass`,
  `scripts/BUILD`, `tests/test_supervisor_reading_pass.py`,
  `tests/test_supervisor_ready.py`, `tests/test_check_private.py`,
  `.agents/skills/thesis-supervisor-feedback/SKILL.md`,
  `.agents/skills/thesis-supervisor-feedback-review/SKILL.md`,
  `docs/operator-reference.md`, `docs/workflow-command-surface.md`
- Tasks:
  - Add `templates/supervisor-reading-pass-intake.md`: a metadata block naming the
    artifact read, the date, whether the notes were dictated, the coverage and
    what was not read, then repeated `###` observation blocks under one
    `## Poznamky` heading, each carrying `Pozorovani:`, `Evidence:` and
    `Routing:`. Match the ASCII-Czech label style of the existing supervisor
    templates.
  - Follow the `templates/supervisor-report-intake.md` model: the template is
    created on demand and named by a "create it from" message. Do NOT add it to
    the unconditional template list in `cli/import_round.py`; `## Audit Base`
    measured 13 rounds carrying a byte-identical unfilled template, and Slice 7
    owns that.
  - Own the round path and the routing enum once, in `paths.py`, the only module
    every consumer below already imports: the path
    `notes/supervisor-reading-pass.md` and the four routing values
    `student_feedback`, `internal_only`, `verify_first`, `discard`.
  - Keep the template basename distinct from the round basename, as
    `templates/supervisor-report-intake.md` already is from
    `notes/supervisor-report-operator-input.md`. The `templates/` exception in
    `check_private.allowed_sensitive_tracked` covers only `is_sensitive_artifact`;
    the private-markdown check has no exception, so a tracked template sharing the
    round basename would fail `check-private`.
  - Add `scripts/check-supervisor-reading-pass` with its `cli` module, registered
    in `scripts/BUILD`, `cli/BUILD` and `commands.py`. An absent file exits 0
    with one line saying a round without a reading pass is valid. A present file
    is validated structurally: the metadata labels exist, there is at least one
    observation block, every block carries all three labels, `Routing:` holds one
    of the four values, `Evidence:` is not a generic filler, and a block whose
    evidence is the explicit unverified token must route to `verify_first` or
    `discard`.
  - Chain the checker from `check-supervisor-ready` after `check-round-ready` and
    `supervisor-deadline`, so a malformed reading pass fails the gate the skill
    already runs while a missing one does not block anything.
  - Wire the path into every consumer that already carries the opponent-side
    operator note, each a separate failure if missed:
    `structured_evidence.CURRENT_EVIDENCE_DEFAULT_SOURCE_REFS`,
    `review_delta.APPEND_ONLY_OPERATOR_NOTE_REFS`,
    `check_feedback_output.INTERNAL_PATTERNS`,
    `check_opponent_materials.INTERNAL_WORKFLOW_PATTERNS` and
    `check_private.PRIVATE_MARKDOWN_RE`. The opponent-side leak list is included
    because both existing lists already carry `supervisor-intake.md`: a private
    filename leaking into any sendable artifact is the same defect.
  - Add the binding test that makes the sweep mechanical: one test asserts the
    owned path appears in each of those five consumers, so a sixth consumer
    cannot be added without it. This is the Slice 3 and Slice 4 lesson in
    executable form.
  - Skills: `thesis-supervisor-feedback` reads the reading pass in the step that
    already reads `notes/supervisor-intake.md`, and its routing is binding in
    three ways: a `student_feedback` item may become a student-facing action item
    directly; a `verify_first` item may become one only after the claim is
    confirmed against the authoritative artifact, and the confirming anchor
    replaces the unverified token in the reading pass, which is what makes the
    upgrade visible rather than implicit; an unconfirmable `verify_first` item and
    every `internal_only` or `discard` item never reach the student output.
    `thesis-supervisor-feedback-review` verifies the routing was honored and that
    no student-facing item traces to an item still carrying the unverified
    token.
  - Docs: `docs/workflow-command-surface.md` gains the command and its Windows
    launcher, `docs/operator-reference.md` the path, the template, the enum and
    the optional-but-validated-when-present contract.
  - Tests: the validator passes on an absent file and on a minimal valid pass,
    and fails on a missing label, an unknown routing value, a generic evidence
    cell, and an unverified evidence token routed to `student_feedback`;
    `check-supervisor-ready` fails on a malformed pass and is unaffected by a
    missing one; the tracked template passes `check-private` while a round-path
    copy of the same content is rejected.
- Out of scope: detecting the season's three legacy filenames, because
  case-derived names must not become an active workflow rule and one of them is
  a real template; the opponent pre-draft calibration stance, owned by
  `plans/opponent_methodology_pipeline_plan.md`; any change to
  `notes/opponent-report-operator-feedback.md` or to
  `scripts/record-review-delta`; per-round scaffolding of the new template,
  owned by Slice 7; making the reading pass a required input; and a smoke script,
  since the validator is covered by pytest and no per-check smoke parity exists.
- Verification:
  - `pants test tests/test_supervisor_reading_pass.py tests/test_supervisor_ready.py`
  - `pants test tests/test_check_private.py tests/test_structured_evidence.py`
  - `pants test tests/test_review_delta.py tests/test_feedback_shape.py`
  - `pants test tests/test_check_scripts_contracts.py tests/test_workflow_python_contracts.py`
  - `pants lint src/thesis_review_workflow/ tests/`
  - `scripts/check-supervisor-reading-pass --help`
  - `scripts/smoke-feedback-output`
  - `scripts/smoke-case-doctor`
  - `scripts/check-scripts`
  - `scripts/check-tooling`
  - `scripts/check-private`
  - `python3 tests/test_plan_contract.py`

### Slice 6 - Early code surface

- Status: done
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

- Status: done
- Proposed commit message: `Scaffold rounds by kind and normalize imported inputs`
- Why: `## Audit Base` measured 13 rounds carrying a byte-identical unfilled
  `notes/supervisor-intake.md` - eight of the ten opponent rounds plus every
  final supervisor-report round, which has its own operator input file - and two
  rounds storing the same similarity report twice under two names, extracting
  both copies, plus filenames with download suffixes and one broken-encoding
  name. `cli/import_round.py` copies five templates unconditionally and stores
  every input under its original basename, so a round cannot tell the operator
  which notes are for it and cannot tell two copies of one file apart. The kind
  is not even missing information: `cli/bootstrap_case.py` already takes a
  `supervisor`/`opponent` mode and then loses it.
- Expected paths: `src/thesis_review_workflow/round_scaffolding.py`,
  `src/thesis_review_workflow/input_provenance.py`,
  `src/thesis_review_workflow/cli/import_round.py`,
  `src/thesis_review_workflow/cli/new_case.py`,
  `src/thesis_review_workflow/cli/bootstrap_case.py`,
  `src/thesis_review_workflow/work_artifacts.py`,
  `src/thesis_review_workflow/cli/case_doctor.py`,
  `tests/test_round_scaffolding.py`, `tests/test_input_provenance.py`,
  `scripts/smoke-bootstrap-case`, `docs/operator-reference.md`,
  `docs/workflow-command-surface.md`
- Tasks:
  - Own the round kind once and reuse the ids that already exist: the five
    `profile_id` values in `review_profiles.py`. A round kind is not a new
    vocabulary, and inventing one would give the repo two names for one thing.
  - Map each kind to its templates in one table: every kind gets
    `round-notes.md` and `assignment.md`; `supervisor_feedback` adds
    `supervisor-intake.md`; `supervisor_report` adds
    `supervisor-report-intake.md`, copied to its consumed name
    `notes/supervisor-report-operator-input.md`; `opponent_materials` and
    `opponent_review` add `opponent-intake.md`; `opponent_report_review` adds
    both the opponent intake and `opponent-report-review-intake.md`.
  - Thread the kind through the whole creation path, not just one entrypoint.
    `bootstrap-case` reaches `import-round` two different ways: directly for an
    existing case, and through `new-case` for a new one, where
    `new_case.main` calls `import-round` with no kind at all. Both need it, or a
    first round silently keeps the full template set.
  - Make the kind reach intake population and readiness selection too, or the
    report kind breaks outright: `bootstrap_case.fill_intake` selects
    `notes/supervisor-intake.md` from `args.mode`, and `replace_field` reads the
    file unconditionally, so scaffolding that omits the intake makes a
    `supervisor_report` bootstrap raise and roll back. The readiness command is
    chosen from the same mode and must follow the kind.
  - Keep `--kind` optional and default to the current full set, but print which
    kind would have been used and what it would have skipped. A required flag
    would break every operator habit at once; an optional one with a visible
    default lets the kind spread by use.
  - Add the guard that stops the regression this slice fixes: one test asserts
    every `templates/*.md` file is either mapped to at least one kind or listed in
    an explicit on-demand set. `supervisor-reading-pass-intake.md` belongs in the
    on-demand set - a reading pass is optional per round, unlike a report intake,
    which a report round needs.
  - Own filename normalization once and specify it fully, because the failure
    mode is a name Windows cannot store or a name that silently loses text:
    strict percent-decoding that leaves an invalid escape literal rather than
    replacing it, NFC normalization applied after decoding, a trailing ` (n)`
    download suffix dropped, characters unsafe on Windows replaced, whitespace
    and repeated separators collapsed, the suffix lowercased, reserved device
    basenames such as `CON` and `NUL` prefixed, trailing dots and spaces
    stripped, and a final basename that can never be empty, `.` or `..`. Keep
    the stem recognizable; this is tidying, not slugging to a hash.
  - Deduplicate physical storage while keeping every logical input. Hash each
    file input and store identical content once, but retain one record per
    declared occurrence with its role, original name and stored ref. Roles are
    load-bearing: `bootstrap_case.build_copy_plan` assigns `thesis_pdf`,
    `assignment_pdf`, `source_archive`, `code` and more, and the assignment
    metadata it writes filters by role, so the same PDF supplied as both thesis
    and assignment must keep both occurrences. Define the conflicting-suffix case
    explicitly: extraction filters on the stored suffix, so identical bytes
    stored first without `.pdf` must not leave the PDF occurrence unextractable.
  - Route bootstrap's own copying through the same owner. `bootstrap-case` does
    not pass inputs to `import-round` at all; it builds `build_copy_plan` and
    copies and extracts inputs itself, so normalizing only `import_round` would
    leave the main operator entrypoint unnormalized, undeduplicated and absent
    from provenance. Generate its assignment and notes references from the final
    stored refs rather than from the requested basenames.
  - Record provenance in `work/input_provenance.json`, and validate it rather
    than merely registering it. Registering a schema in
    `work_artifacts.KNOWN_JSON_ARTIFACT_SCHEMAS` buys only the envelope check -
    schema version, case and round identity, and `generated_at`, which the
    envelope must therefore carry. Add a record validator wired into the
    work-artifact dispatch that rejects a missing stored file, a hash or size
    that does not match it, and a ref that escapes the round.
  - Keep the existing same-destination rejection in both entrypoints, applied to
    normalized names and casefolded, since two different originals can now
    normalize to one name. Content-identical inputs are resolved by dedup first.
  - PDF extraction needs changing, contrary to the obvious assumption:
    `import_round.main` builds both `inputs/<source.name>` and
    `extracted/<source.stem>.txt` from the ORIGINAL path, so normalizing the
    stored name without touching this extracts to a name that no longer matches
    its PDF. Derive both from the stored file and assert the pairing.
  - `case-doctor` reports the stored-versus-original names and the aliases, so an
    operator who cannot find a file by its download name can see where it went.
  - Docs: `docs/operator-reference.md` documents the kinds, what each scaffolds
    and that a reading pass stays on demand; `docs/workflow-command-surface.md`
    keeps its contract accurate for the changed commands.
- Out of scope: renaming or deduplicating inputs in rounds that already exist,
  which is a migration and belongs with
  `plans/case_format_migration_contract_plan.md`; re-extracting text for
  already-imported inputs; the case layout contract; tree hashing for directory
  inputs, which keep `copytree` under a normalized name; and any change to what a
  template says.
- Verification:
  - `pants test tests/test_round_scaffolding.py tests/test_input_provenance.py`
  - `pants test tests/test_work_artifacts.py tests/test_case_doctor_summary.py`
  - `pants test tests/test_check_scripts_contracts.py tests/test_workflow_python_contracts.py`
  - `pants lint src/thesis_review_workflow/ tests/`
  - `scripts/smoke-bootstrap-case`
  - `scripts/smoke-case-doctor`
  - `scripts/check-scripts`
  - `scripts/check-private`
  - `python3 tests/test_plan_contract.py`
