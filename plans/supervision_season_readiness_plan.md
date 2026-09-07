# Supervision Season Readiness Plan

Status: in_progress
Created: 2026-09-07

## Start Here

State: Slices 1 and 2 are done. The season gate is unblocked, an
operator-declared review phase travels end to end, and supervisor-report
calibration exists at version 5, reviewed with notes. Slices 3-7 are stubs.

Next action: write the Slice 3 charter (early-phase role set, plus revision diff
for rounds with a predecessor) and review it before implementing.

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

### Slice 3 - Early-phase role set

Charter form: stub

Objective: an `early` role set with its own required/advisory split, and a
revision-diff requirement for any round that follows a predecessor.

Boundary: no change to the output shape, and no relaxation of a role a `final`
round requires.

Serves: the first early rounds, and Slice 4, which writes against this set.

### Slice 4 - Early-phase feedback shape

Charter form: stub

Objective: an early-phase output shape and length budget in the supervisor
feedback skill and its reviewer skill, replacing the one shared 12-section form.

Boundary: one shape per phase band, not per case; no new artifact path.

Serves: the first feedback each new student receives.

### Slice 5 - Operator reading-pass intake

Charter form: stub

Objective: one tracked template and one wired round path for the operator's
dictated reading pass, each note carrying an evidence answer and a routing
decision, replacing three ad-hoc filenames.

Boundary: supervisor track and raw reading notes only; opponent pre-draft
calibration stance and routing stay with the methodology plan.

Serves: the largest unshaped operator input measured.

### Slice 6 - Early code surface

Charter form: stub

Objective: make the existing GitHub intake the discoverable default code path
for rounds with no submitted archive or code directory.

Boundary: no new intake capability and no change to
`scripts/prepare-code-workspace`; PR-contribution depth stays in `TODO.md`.

Serves: early rounds, where a submitted archive does not yet exist.

### Slice 7 - Round scaffolding and input ergonomics

Charter form: stub

Objective: kind-aware round scaffolding instead of every intake template in
every round, plus input normalization at import: identical-file dedup, stable
filenames, original name kept in provenance.

Boundary: ergonomics only; the case layout contract stays with its own plan.

Serves: every round of the new season.

## Progress

Slice 2 is done: 2026/2027 BP and DP deadline rows, an `early` materiality
phase, and a `review_phase` carrier from `review-round-start` through the run
trace into the materiality refresh, scoped to `supervisor_feedback`. Its
verification block ran green, including `pants run :omen` (grade A, 0 critical).
Three review rounds are adjudicated in `## Decision Log`: the plan-critic round,
its narrow re-check, and the implementation review.

Slice 1 is done. The calibration profile is version 5, `reviewed_with_notes`,
gated to BP reports in the A and B bands, and backed by a deterministic
correction ledger rather than hand-counted prose. Its calibration content is
seven correction patterns, seven of eight carrying a counter-attestation. The
private profile layer carries only a pointer. All four operator questions are
answered; two skill questions the reviewer raised are recorded for the operator.
Slices 3-7 remain stubs; Slice 3 needs a full charter and a charter review before
implementation.

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

## Final Audit

Not reached. On closure this section records: the commands run per slice, the
first early-phase round that exercised Slices 2-4 end to end, whatever residual
items were copied into `TODO.md`, and the archive decision.
