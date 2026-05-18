# Opponent Report Clean Export And Closeout Plan

Status: active
Created: 2026-05-18

## Goal

Make opponent-report drafting produce and validate two explicit artifacts:

- an internal canonical workflow draft with trace hashes, source metadata, and
  private pre-submission checklist; and
- a clean IS-entry report proposal that contains the fields intended for the
  opponent/report form, including the non-public student-comment field when the
  IS report supports it.

The optimized workflow should let a parent agent or operator draft, review,
approve, and close out an opponent report without ad hoc manual manifest edits,
temporary work-local clean draft files, invalid review-status strings, or stale
evidence-hash repair scripts.

Terminology used by this plan:

- **Canonical draft** means `work/oponent_posudek_draft.md`: internal,
  hash-bound, and allowed to contain provenance comments and the private
  pre-submission checklist.
- **IS-entry proposal** means `outputs/oponent_posudek_navrh.md`: case-local and
  copy-oriented for IS entry. It contains public report prose, structured IS
  selectbox/point fields, and the non-public student-comment field, but no
  internal workflow metadata.
- **Public IS projection** means a derived public-only view of the IS-entry
  proposal for comparison with the submitted PDF export. It excludes the
  non-public student-comment field because that field is not present in the
  public PDF.

## Audit Base

This plan is based on a recent final opponent-report drafting loop. The concrete
case artifacts remain private under ignored `cases/`; this plan records only
case-neutral workflow findings.

Observed friction:

- The canonical `work/oponent_posudek_draft.md` must contain private provenance
  comments and a `## 12. Před odevzdáním` checklist so
  `scripts/check-opponent-report` can verify trace and source hashes. Those
  lines are useful internally but must not be copied into IS-facing prose.
- The report-facing text therefore had to be written to an ad hoc clean file.
  That worked, but the path was not a first-class workflow artifact.
- `scripts/check-opponent-report` currently mixes two contracts: internal
  canonical-draft validation and IS-entry proposal validation. A clean report
  proposal intentionally fails canonical validation because it omits private
  metadata and the private checklist.
- `outputs/feedback_k_posudku.md` is the reviewed opponent-report-review
  artifact, while the report text actually reviewed is the draft basis. The
  approval path can represent this with `review_basis_path`, but the manifest
  and helper-check target plumbing did not make that normal path automatic.
- `scripts/init-review-manifest --run-checks` did not automatically record all
  metadata needed for the new opponent-report-review approval to satisfy
  `scripts/check-review-wave --workflow opponent_report_review --wave final`
  and `scripts/check-review-manifest --require-complete`.
- `scripts/register-review-artifact` accepted an invalid
  `--review-status covered_by_downstream_synthesis` value; the error was only
  caught later by the manifest checker.
- After operator notes changed, hash-bound internal artifacts such as common
  briefing, literature source acquisition, and review deltas reported stale
  source/evidence hashes. The repair was mechanical but had no single supported
  command.
- The human opponent workflow needs a private student comment in addition to
  the public report fields. In the observed case this had to be added manually
  after the public text stabilized; future drafts should scaffold and validate
  it as a normal report field.
- The IS opponent form also contains non-prose fields: selectbox values for
  assignment difficulty, assignment fulfillment, and technical-report scope,
  plus point fields for presentation, formal quality, literature work, and
  implementation output. Earlier drafts only produced prose plus overall
  points/grade, leaving these fields to be reconstructed manually during IS
  entry.
- It was too easy to treat a direct `pytest` run as final test evidence. In this
  repo, Python test closeout should use the `pants` executable from `PATH`, run
  sequentially; direct `pytest` is only an exploratory local probe.
- Smoke fixtures can drift behind manifest/approval contracts. In the observed
  loop, a smoke approval record missed newly required observed checks and a
  synthetic coverage mutation left a stale `check-agent-coverage` target hash.
- Reviewer agents can still hand-write `work/reviews/*_review.json` in a shape
  that is semantically understandable but invalid for the deterministic
  approval schema. In the observed final revalidation, `checks_observed` was
  written as structured command/result objects, while validators require a list
  of check names. The repair was mechanical, but the normal path should make it
  hard to write an invalid approval after a valid independent review.
- Switching from opponent-materials closeout to opponent-report-review closeout
  exposed profile-state coupling: `work/review_run_trace.json` and
  `work/review_role_plan.json` can still describe the previous profile, causing
  `review-round-closeout --profile opponent_report_review` to fail until the
  round is explicitly restarted/prepared for the new profile.
- Packet/manifest merging can preserve stale references from the previous
  profile. In the observed run, missing `work/opponent_packets/materials_review.md`
  and `work/opponent_packets/report_trace.md` links survived in
  `supporting_work_artifacts` and `handoff_refs` even though the current
  opponent-report-review packet set no longer generated those files.
- `work/common_briefing.json` can become stale after a review approval is
  rewritten or normalized, because it snapshots `work/reviews/*.json`. The
  current closeout can refresh it, but the ordering should be explicit and
  automatic in the approval/write/closeout path.
- Materiality output can be noisier than the final manifest result. A
  synthesis-covered Theses.cz/similarity artifact was still surfaced as a
  `next action` by materiality even though final manifest closeout passed. This
  makes the operator distinguish real blockers from already-covered advisory
  evidence by reading multiple artifacts.
- After the report was submitted in IS, the workflow had no first-class
  opponent equivalent of `record-submitted-supervisor-report`. The submitted
  PDF could be copied and checked case-locally, but the record was an ad hoc
  `work/submitted_reports/opponent_report.json` rather than a supported
  validator-backed command.
- The submitted IS PDF is not a byte-for-byte rendering of the clean Markdown
  draft. IS renders its own field labels such as `Souhrnné hodnocení` and
  `Využitelnost výsledků` and places selectbox values next to field headings.
  The submitted PDF is a public export, so it must be compared against an
  IS-rendered public-text projection, not against the full Markdown draft
  including non-public fields.
- During final IS entry the operator may make small wording edits directly in
  the form, for example shortening a sentence or dropping a less central clause.
  Key-value checks alone can miss these differences. Submitted-report capture
  should produce a normalized section-level diff between the reviewed public
  draft/projection and the submitted PDF text, then require either exact match
  or explicit operator classification of the delta as intentional/non-material.

Current relevant paths and commands:

- Internal opponent report draft: `work/oponent_posudek_draft.md`.
- Current IS-entry proposal should become
  `outputs/oponent_posudek_navrh.md`.
- Opponent report review output:
  `outputs/feedback_k_posudku.md`.
- Approval record:
  `work/reviews/opponent_report_review.json`.
- Existing validator:
  `scripts/check-opponent-report <case-id> [round-id]`.
- Existing final review wave:
  `scripts/check-review-wave --workflow opponent_report_review --wave final <case-id> [round-id]`.
- Existing closeout gates:
  `scripts/init-review-manifest --run-checks`,
  `scripts/check-agent-coverage`, and
  `scripts/check-review-manifest --require-complete`.

Constraints:

- Do not store concrete student/case facts in tracked files.
- Do not weaken the independent review loop for opponent reports.
- Do not make a clean Theses.cz report visible in formal prose just to show that
  a check happened.
- Do not infer report materiality from free-form thesis text with deterministic
  substring heuristics.
- Do not add backward-compatibility layers for older `~/code/diplomky`
  workflows.
- Keep Windows-supported command surfaces: Python CLI modules plus generated
  wrappers, not shell-only entrypoints.
- Run Pants commands sequentially.
- Use `pants test ...` for Python test evidence in final closeout. A direct
  `python -m pytest ...` command may be recorded only as exploratory debugging,
  not as the authoritative repo check.

## Scope

In scope:

- Define a first-class clean opponent-report proposal artifact.
- Split canonical workflow validation from clean IS-entry proposal validation.
- Add an export/render command that derives or updates the clean IS-entry proposal
  from the canonical workflow draft while stripping private metadata and private
  checklist content.
- Treat the private student comment as a first-class report field: scaffold it,
  require it before closeout, validate that helper placeholder wording was
  replaced, and keep it separate from public report prose.
- Treat IS selectbox choices and category point values as first-class report
  fields: scaffold them, validate exact allowed option values, and require
  numeric point values before a report draft is closeout-ready.
- Teach opponent-report review packets, approval records, role coverage, and
  manifest closeout that the reviewed report basis may be the IS-entry proposal.
- Make `init-review-manifest --run-checks` and review-wave validation record the
  right helper-check targets without manual JSON repair.
- Make reviewer approval creation helper-first: agents should call
  `scripts/write-review-approval` or an equivalent validator-backed writer
  instead of hand-writing schema-sensitive approval records.
- Make profile transitions explicit: starting or closing an
  opponent-report-review pass should refresh or replace stale
  `review_run_trace`/`review_role_plan` records from older profiles, or fail
  with one exact recovery command.
- Prune missing/stale packet refs when regenerating manifests for a current
  profile, especially for not-material roles whose packets are intentionally not
  produced.
- Add enum validation to `register-review-artifact`.
- Add a deterministic hash-refresh command for known hash-bound internal
  artifacts after operator notes or stable evidence refs change.
- Add submitted-opponent-report capture after IS submission, including PDF
  copy, text extraction, hash-bound record, key form-value checks, operation-log
  entry, and manifest integration.
- Add submitted public-text projection/diff support so the system can
  distinguish IS rendering differences, intentional final form edits, and
  accidental public-text drift.
- Update skills/docs/tests/smokes so the normal path is discoverable.

Out of scope:

- Changing the semantic criteria for grading opponent reports.
- Changing the content of any current private case report.
- Adding automatic grading or point recommendation logic.
- Reworking supervisor feedback/report clean-export behavior unless the shared
  helper abstractions make it essentially free and covered by tests.
- Backfilling old case rounds.

## Target Operator Path

The intended final path for an opponent report is:

1. `scripts/draft-opponent-report <case-id> [round-id]` writes the internal
   canonical draft to `work/oponent_posudek_draft.md`.
2. The parent agent or human calibrates points, grade, public report prose, and
   the private student comment in the canonical draft or through a supported
   clean-export edit flow.
3. `scripts/export-opponent-report <case-id> [round-id]` writes the IS-facing
   proposal to `outputs/oponent_posudek_navrh.md`.
4. `scripts/check-opponent-report --mode canonical <case-id> [round-id]`
   validates trace/materials hashes, required internal sections, points, grade,
   IS form selections/point values, and private checklist state.
5. `scripts/check-opponent-report --mode clean --path outputs/oponent_posudek_navrh.md <case-id> [round-id]`
   validates IS-entry proposal safety, private student-comment presence, IS item
   coverage, defense questions, IS form selections/point values, overall
   points, grade, and absence of internal paths, hashes, workflow terms,
   private checklist content, scaffold placeholder wording, and unresolved
   calibration wording. It must not infer similarity-report materiality from
   report prose; Theses.cz/similarity handling is validated only through
   structured trace, materiality, review, or approval records.
6. `scripts/review-round-start --profile opponent_report_review <case-id>
   [round-id]` refreshes profile-specific closeout state for this profile.
7. `scripts/prepare-review-round --profile opponent_report_review <case-id>
   [round-id]` writes the current role plan and packet references; stale packet
   refs from `opponent_materials` must be pruned or reported with one exact
   recovery command before manifest mutation.
8. `scripts/check-review-wave --workflow opponent_report --wave draft <case-id>
   [round-id]` confirms the reviewed draft basis is current before the final
   report-review agent runs.
9. The opponent-report-review agent reviews `outputs/oponent_posudek_navrh.md`
   as the primary report text and writes `outputs/feedback_k_posudku.md`.
10. `work/reviews/opponent_report_review.json` records
   `reviewed_artifact_path=outputs/feedback_k_posudku.md` and
   `review_basis_path=outputs/oponent_posudek_navrh.md`.
11. `scripts/init-review-manifest --run-checks <case-id> [round-id]` records the
   IS-entry proposal, review output, approval record, helper-check targets, role
   coverage, and synthesis-covered internal evidence without manual patching.
12. `scripts/check-review-wave --workflow opponent_report_review --wave final`,
   `scripts/check-agent-coverage`, and
   `scripts/check-review-manifest --require-complete` pass in the normal path.

## Design Decisions

- `work/oponent_posudek_draft.md` remains the internal canonical draft because
  it is hash-bound to reviewed opponent materials and report trace.
- `outputs/oponent_posudek_navrh.md` becomes the clean report-facing proposal.
  It is case-private because all `cases/` content is ignored, but it is the
  artifact intended for human copying into IS.
- Temporary work-local clean draft paths from earlier runs are not new
  supported workflow contracts.
- `check-opponent-report` gets explicit modes instead of guessing intent from
  missing metadata.
- Approval records continue to approve the review output
  `outputs/feedback_k_posudku.md`; the IS-entry proposal is recorded as the
  review basis.
- Clean report export must be deterministic and conservative: it strips only
  known private metadata/checklist sections and must fail if required public
  sections, the private student comment, points, or grade are missing.
- The private student comment is not part of public report prose, but it is still
  IS-facing. It may contain short coaching, defense preparation, and future-work
  advice, but it must not contain internal paths, hashes, review mechanics, or
  unsupported allegations.
- IS form choices should be represented as literal IS option labels, not
  inferred from prose at closeout time. If the IS labels change, the allowed
  values must be updated in one deterministic validator contract.
- Mode-specific helper checks must be manifest-visible. A final closeout must
  prove both canonical and clean report checks ran, either through distinct
  helper-check names such as `check-opponent-report:canonical` and
  `check-opponent-report:clean`, or through a typed `mode` field that records
  exact command arguments and target hashes for each mode.
- Hash refresh is cache maintenance only. It may update derived snapshots such
  as common briefing hashes, but it must not refresh approval-bound hashes after
  report text, private comments, grades, review verdicts, or evidence findings
  change. Those changes require `record-review-delta` with a typed
  non-material classification or a fresh independent review before closeout.

## Slices

### Slice 1 - Clean Artifact Contract And Checker Modes

- Status: completed
- Proposed commit message: `feat(workflow): split opponent report draft checks`
- Expected paths:
  - `src/thesis_review_workflow/cli/check_opponent_report.py`
  - `src/thesis_review_workflow/artifact_registry.py`
  - `src/thesis_review_workflow/opponent_calibration.py`
  - `src/thesis_review_workflow/review_approvals.py`
  - `src/thesis_review_workflow/review_profiles.py`
  - `src/thesis_review_workflow/review_wave_gate.py`
  - `tests/test_opponent_report.py`
  - `tests/test_artifact_registry.py`
  - `tests/test_review_approvals.py`
  - `tests/test_review_wave_gate.py`
- Tasks:
  - Add `--mode canonical|clean` to `check-opponent-report`; preserve canonical
    behavior for `work/oponent_posudek_draft.md`.
  - Add clean-mode required headings without `## 12. Před odevzdáním`.
  - Require `## Komentář pro studenta (neveřejná část)` in both canonical and
    clean modes when the report draft is treated as calibrated for IS entry.
  - Require `## IS formulář (výběry a body)` in both canonical and clean modes,
    with exact selectbox values and numeric 0-100 values for point fields.
  - Reject generic helper scaffold text in the private student comment so the
    placeholder cannot pass as a finalized comment.
  - Reject generic helper scaffold text in IS form fields so placeholders such
    as "k ručnímu výběru" or "k ručnímu zadání bodů" cannot pass as finalized
    values.
  - In clean mode, require absence of source metadata comments, local paths,
    workflow artifact names, private checklist sections, unresolved calibration
    wording, internal confidence labels, and known scaffold placeholders.
  - Do not gate clean mode on free-text interpretation of Theses.cz/similarity
    prose. If similarity evidence affects report wording, require a structured
    reviewed concern, trace item, materiality decision, or approval hash and
    validate that structured linkage instead of scanning prose for semantic
    meaning.
  - Add `outputs/oponent_posudek_navrh.md` as an allowed opponent-report-review
    basis in approval/profile validation, artifact registry review-basis
    candidates, workflow profile draft artifacts, and review-wave expectations.
  - Update final review wave expectations so the opponent-report-review
    approval can be hash-bound to the IS-entry proposal without manual
    manifest edits.
  - Define the manifest representation for canonical and clean report checks so
    `init-review-manifest --run-checks` and `check-review-manifest` can verify
    both modes with separate target hashes.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_opponent_report.py tests/test_artifact_registry.py tests/test_review_approvals.py tests/test_review_wave_gate.py`
  - `scripts/check-scripts`
  - `scripts/check-private`
  - `git diff --check`

### Slice 2 - Export Command And Docs

- Status: planned
- Proposed commit message: `feat(workflow): export clean opponent reports`
- Expected paths:
  - `scripts/export-opponent-report`
  - `scripts/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/cli/export_opponent_report.py`
  - `.agents/skills/thesis-opponent-report-review/SKILL.md`
  - `.agents/skills/thesis-opponent-materials/SKILL.md`
  - `AGENTS.md`
  - `README.md`
  - `templates/opponent-intake.md`
  - `tests/test_export_opponent_report.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-export-opponent-report`
  - `scripts/smoke-package-workflow-tools`
- Tasks:
  - Implement a Python CLI that reads the canonical draft and writes
    `outputs/oponent_posudek_navrh.md`.
  - Strip only source metadata comments, draft status lines, and private
    `## 12. Před odevzdáním` content.
  - Preserve the private student-comment section as an IS-facing private field.
  - Preserve the structured IS form section as IS-facing operator data.
  - Fail when public sections, concrete points, grade, defense questions, or the
    private student comment are missing.
  - Fail when assignment-difficulty, assignment-fulfillment, report-scope, or
    category point fields are missing or still placeholders.
  - Fail when the private student comment still contains generated placeholder
    instructions instead of a human-calibrated comment.
  - Run both canonical and clean checks after export.
  - Update skills and README so agents review the IS-entry proposal as the
    primary report text while keeping the canonical draft as the trace-bound
    basis.
  - Update intake templates so operator notes can distinguish public report
    judgments from useful private advice for the student.
  - Add script wrapper coverage for Linux and packaged Windows command surfaces.
  - Register the command in `WORKFLOW_COMMAND_MODULES`, `src/.../cli/BUILD`, and
    `scripts/BUILD`; verify the generated `.cmd`/`.ps1` launchers through the
    package-workflow-tools smoke.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_export_opponent_report.py tests/test_opponent_report.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-export-opponent-report`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-scripts`
  - `scripts/check-private`
  - `git diff --check`

### Slice 3 - Manifest, Coverage, And Approval Closeout Plumbing

- Status: planned
- Proposed commit message: `fix(workflow): close out clean opponent report reviews`
- Expected paths:
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `src/thesis_review_workflow/review_manifest.py`
  - `src/thesis_review_workflow/agent_coverage.py`
  - `src/thesis_review_workflow/opponent_calibration.py`
  - `src/thesis_review_workflow/review_profiles.py`
  - `src/thesis_review_workflow/review_wave_gate.py`
  - `src/thesis_review_workflow/artifact_registry.py`
  - `tests/test_review_manifest_helpers.py`
  - `tests/test_agent_coverage.py`
  - `tests/test_opponent_calibration.py`
  - `tests/test_review_wave_gate.py`
- Tasks:
  - Record `outputs/oponent_posudek_navrh.md` as a draft/review-basis artifact
    whenever it exists.
  - Ensure `outputs/feedback_k_posudku.md` has recorded generator/finalizer
    metadata and a structured approval imported from
    `work/reviews/opponent_report_review.json`.
  - Ensure helper-check records include targets required by approval validation
    without manually adding `outputs/feedback_k_posudku.md`.
  - Represent canonical and clean report checks as separate manifest-verifiable
    helper records or as one helper record with typed mode entries. The checker
    must reject a final opponent-report-review closeout where only one generic
    `check-opponent-report` command was observed.
  - Add the normal operator route before review: `review-round-start --profile
    opponent_report_review`, `prepare-review-round --profile
    opponent_report_review`, `check-review-wave --workflow opponent_report
    --wave draft`, agent review from the current role plan, and
    `check-review-wave --workflow opponent_report_review --wave final`.
  - Make profile transition recovery explicit: stale `review_run_trace` or
    `review_role_plan` from `opponent_materials` must be replaced by the start
    and prepare commands or produce one exact recovery command before manifest
    mutation.
  - Ensure `init-review-manifest` prunes missing `supporting_work_artifacts` and
    generated `handoff_refs` instead of preserving stale packet refs from a
    previous profile.
  - Ensure role plans do not advertise missing packet paths as actionable
    artifacts for roles marked `not_material`; if a packet is intentionally not
    generated, the role plan should record that as a state, not as a missing
    file to be carried into manifest handoffs.
  - Ensure `check-agent-coverage` infers the opponent-report-review role from
    current manifest records and sees generator/reviewer/hash fields after
    `init-review-manifest --run-checks`.
  - Ensure post-review edits to either public report prose or the private
    student comment are represented as structured review deltas and make the
    previous approval visibly stale until revalidated or explicitly classified
    as a typed non-material exception.
  - Keep synthesis-covered internal evidence such as clean Theses.cz reviews
    silent but manifest-valid with `not_required`, `covered_by_artifact`,
    `used_findings`, and evidence hash.
  - Align materiality `next action` output with synthesis-covered evidence so
    already-reviewed or intentionally silent similarity evidence does not look
    like a fresh blocker during closeout.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_review_manifest_helpers.py tests/test_agent_coverage.py tests/test_opponent_calibration.py tests/test_review_wave_gate.py`
  - `scripts/check-scripts`
  - `scripts/check-private`
  - `git diff --check`

### Slice 4 - Registration Enums And Hash Refresh

- Status: planned
- Proposed commit message: `fix(workflow): validate review registration metadata`
- Expected paths:
  - `src/thesis_review_workflow/cli/write_review_approval.py`
  - `src/thesis_review_workflow/cli/register_review_artifact.py`
  - `src/thesis_review_workflow/review_manifest.py`
  - `src/thesis_review_workflow/cli/refresh_round_hashes.py`
  - `src/thesis_review_workflow/commands.py`
  - `scripts/refresh-round-hashes`
  - `scripts/BUILD`
  - `src/thesis_review_workflow/cli/BUILD`
  - `tests/test_review_manifest_helpers.py`
  - `tests/test_refresh_round_hashes.py`
  - `scripts/smoke-register-review-artifact`
  - `scripts/smoke-refresh-round-hashes`
  - `scripts/smoke-package-workflow-tools`
- Tasks:
  - Validate `--review-scope` and `--review-status` against the manifest
    checker enums at registration time.
  - Print valid enum choices in registration errors.
  - Make opponent-report-review agent instructions and smoke paths use
    `scripts/write-review-approval` for approval records, not hand-written JSON.
  - Either reject invalid `checks_observed` item shapes at write time with a
    precise error or normalize known command/result objects into check-name
    strings before persistence. Prefer rejection unless there is a clean typed
    schema for command evidence.
  - Add `scripts/refresh-round-hashes <case-id> [round-id]` for mechanical
    cache refresh in known derived structured artifacts such as
    `work/common_briefing.json` and explicit hash snapshots already covered by
    validators.
  - The refresh command must not change semantic verdicts, review statuses,
    approval records, review-delta decisions, grades, report text, private
    student comments, or synthesis findings.
  - For `work/literature/source_acquisition.json`,
    `work/review_deltas/*.json`, and any other artifact that binds evidence or
    materiality decisions, refresh only after the relevant validator confirms
    the semantic payload is unchanged and either a typed non-material delta has
    been recorded or a fresh review has been run.
  - Teach `review-round-closeout` or the closeout documentation when to run the
    refresh command after operator-note edits.
  - Refresh `work/common_briefing.json` after approval-record writes or include
    it in the same deterministic hash-refresh path, because common briefing
    snapshots `work/reviews/*.json`.
  - Register the command in `WORKFLOW_COMMAND_MODULES`, `src/.../cli/BUILD`, and
    `scripts/BUILD`; verify the generated `.cmd`/`.ps1` launchers through the
    package-workflow-tools smoke.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_review_manifest_helpers.py tests/test_refresh_round_hashes.py`
  - `scripts/smoke-register-review-artifact`
  - `scripts/smoke-refresh-round-hashes`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-scripts`
  - `scripts/check-private`
  - `git diff --check`

### Slice 5 - Pre-Submission Smokes And Report-Review Closeout

- Status: planned
- Proposed commit message: `test(workflow): cover clean opponent report review`
- Expected paths:
  - `src/thesis_review_workflow/cli/review_round_start.py`
  - `src/thesis_review_workflow/cli/review_round_closeout.py`
  - `src/thesis_review_workflow/review_pipeline_orchestration.py`
  - `scripts/smoke-opponent-report`
  - `scripts/smoke-export-opponent-report`
  - `scripts/smoke-review-wave`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-agent-coverage`
  - `scripts/smoke-package-workflow-tools`
  - `docs/dev-hygiene.md`
  - `TODO.md`
- Tasks:
  - Add smoke coverage for:
    - canonical draft generation;
    - clean report export;
    - canonical and clean report checks;
    - `review-round-start --profile opponent_report_review`;
    - `prepare-review-round --profile opponent_report_review`;
    - generated-draft wave validation before final review;
    - transition from an already-closed opponent-materials profile to a fresh
      opponent-report-review profile in the same round;
    - opponent-report-review approval using the IS-entry proposal as review basis;
    - `init-review-manifest --run-checks`;
    - final review wave;
    - agent coverage;
    - complete pre-submission review manifest closeout.
  - Keep synthetic smoke approvals aligned with the current approval contract,
    including all required observed checks for the profile.
  - Assert that `review-round-closeout --profile opponent_report_review` does
    not reuse stale `review_run_trace` or `review_role_plan` data from
    `opponent_materials`; it should either refresh them automatically or fail
    before manifest mutation with one recovery command.
  - Assert that regenerated manifests contain no references to missing packet
    files and no stale common-briefing hashes after approval normalization.
  - When smoke fixtures mutate `work/agent_coverage.json`, refresh both the
    supporting artifact hash and any helper-check `target_sha256` entry that
    points at it.
  - Update `TODO.md` only for residual pre-submission review work not completed
    by this slice. Do not archive this plan here; submitted-report capture still
    follows.
- Verification:
  - `pants fmt ::`
  - `pants lint ::`
  - `pants check ::`
  - `pants test tests::`
  - `scripts/smoke-opponent-report`
  - `scripts/smoke-export-opponent-report`
  - `scripts/smoke-review-wave`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-agent-coverage`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-scripts`
  - `scripts/check-private`
  - `git diff --check`

### Slice 6 - Submitted Opponent Report Capture And Archive Closeout

- Status: planned
- Proposed commit message: `feat(workflow): record submitted opponent reports`
- Expected paths:
  - `src/thesis_review_workflow/submitted_reports.py`
  - `src/thesis_review_workflow/cli/record_submitted_opponent_report.py`
  - `src/thesis_review_workflow/cli/check_opponent_report.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/submitted_report_deltas.py`
  - `src/thesis_review_workflow/cli/record_submitted_report_delta.py`
  - `scripts/record-submitted-opponent-report`
  - `scripts/record-submitted-report-delta`
  - `scripts/BUILD`
  - `README.md`
  - `.agents/skills/thesis-opponent-report-review/SKILL.md`
  - `tests/test_submitted_reports.py`
  - `tests/test_submitted_report_deltas.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-record-submitted-opponent-report`
  - `scripts/smoke-package-workflow-tools`
- Tasks:
  - Implement `scripts/record-submitted-opponent-report <case-id> [round-id]
    --pdf <path> --recorded-by <name> [--force]`.
  - Copy the submitted IS PDF to `work/submitted_reports/opponent_report.pdf`
    and extract text to `extracted/submitted_reports/opponent_report.txt`.
  - Write `work/submitted_reports/opponent_report.json` with schema,
    submitted PDF/text hashes, normalized text hash, reviewed draft/review
    hashes, extracted IS selectbox values, category points, overall points,
    grade, and readiness flags.
  - Validate that submitted public PDF values match the reviewed clean report
    basis: assignment difficulty, assignment fulfillment, technical-report
    scope, category points, overall points/grade, and defense questions.
  - Build an IS-public projection from the reviewed clean report basis: public
    prose sections only, IS field labels as rendered by the PDF, selectbox
    values and point labels inline.
  - Produce a normalized section-level diff between that projection and the
    submitted PDF text.
  - Add a typed delta/acceptance artifact for submitted-form edits, for example
    `work/submitted_reports/opponent_report_deltas.json`, written by a
    validator-backed command. Each accepted delta must include the reviewed
    basis hash, submitted PDF/text hash, affected section, normalized before and
    after text, operator classification, concise rationale, and reviewer or
    operator identity.
  - Treat non-empty semantic diffs as blocking archive readiness unless the
    typed delta artifact classifies them as intentional/non-material. Material
    diffs reopen report review instead of being archived as accepted drift.
  - Validate that the public PDF does not contain internal paths, manifest
    hashes, or workflow terms.
  - Record a `submitted-opponent-report-capture` operation-log event and include
    the submitted record and accepted delta artifact in review manifest
    supporting work artifacts.
  - Add an explicit limitation when the IS PDF format changes enough that text
    extraction cannot parse all fields; this should block archive readiness but
    not rewrite the submitted report.
  - Record public/private split explicitly: the submitted PDF is only the public
    export. The case should still keep the private comment basis and any
    operator confirmation needed for the non-public IS field, but submitted-PDF
    validation must not try to infer that private field from the public export.
  - Register new commands in `WORKFLOW_COMMAND_MODULES`, `src/.../cli/BUILD`, and
    `scripts/BUILD`; verify the generated `.cmd`/`.ps1` launchers through the
    package-workflow-tools smoke.
  - Extend end-to-end smokes so submitted opponent-report capture, accepted
    submitted-form deltas, manifest integration, and archive-readiness checks
    run after the pre-submission report-review closeout.
  - Record final audit commands and archive decision in this plan only after the
    submitted-report capture path is covered or explicitly left as residual
    `TODO.md` work.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_submitted_reports.py tests/test_submitted_report_deltas.py tests/test_workflow_python_contracts.py tests/test_opponent_report.py`
  - `scripts/smoke-record-submitted-opponent-report`
  - `scripts/smoke-opponent-report`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-agent-coverage`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-scripts`
  - `scripts/check-private`
  - `git diff --check`

## Progress

- 2026-05-18: Plan created from observed opponent-report workflow friction.
  Implementation is still uncommitted; the working tree already contains
  candidate changes for parts of Slice 1 and Slice 3, so execution should first
  reconcile those edits with this reviewed plan rather than starting from a
  clean baseline.
- 2026-05-18: Expanded after additional report calibration. Added
  first-class private student-comment handling, Pants-as-authoritative-test
  closeout guidance, and smoke fixture contract hardening for approval observed
  checks and coverage target hashes.
- 2026-05-18: Expanded after final report revalidation. Added
  helper-first approval writing, profile-transition closeout hardening,
  stale packet-ref pruning, common-briefing refresh after approval writes, and
  materiality-warning calibration for synthesis-covered similarity evidence.
- 2026-05-18: Expanded after IS entry calibration. Added first-class handling
  for IS selectbox choices and category point fields so the report pipeline no
  longer leaves those values to manual reconstruction during IS entry.
- 2026-05-18: Expanded after actual IS submission. Added a planned submitted
  opponent report capture command because only the supervisor-report submission
  path currently has first-class tooling.
- 2026-05-18: Expanded after comparing the actual IS PDF with the clean draft.
  Added IS-rendered public-text projection and submitted-text diff handling, so
  final form edits are captured explicitly instead of hidden behind key-value
  checks.
- 2026-05-18: Reviewed with two read-only agents and repaired the plan. Added
  explicit review-round start/prepare routing, removed free-text similarity
  gating, tightened hash-refresh boundaries, split pre-submission closeout from
  post-submission archive closeout, added Windows/PEX command-surface coverage,
  and required typed submitted-form delta acceptance.
- 2026-05-18: Reviewed the current uncommitted implementation with two
  read-only agents. Fixed checker type hygiene, duplicate IS field detection,
  private-comment placeholder rejection, and removed the misleading manifest
  target that made `check-opponent-report` appear to validate
  `outputs/feedback_k_posudku.md`.
- 2026-05-18: Slice 1 implementation started from a clean tracked baseline
  despite the older progress note about candidate edits. Added explicit
  canonical/clean opponent-report checker modes, first-class
  `outputs/oponent_posudek_navrh.md` artifact registration, clean proposal
  review-basis routing, and separate manifest helper identities
  `check-opponent-report:canonical` / `check-opponent-report:clean`. Targeted
  Pants fmt/lint/check/test passed for the touched Slice 1 modules and tests.
  Omen MCP was attempted on the touched Python paths but returned zero files,
  so it is recorded as an MCP/path limitation rather than a code-quality signal.
- 2026-05-18: Slice 1 post-change agent review found three contract gaps:
  opponent-materials approvals still using the old generic helper-check name,
  approval validation not proving mode-specific helper targets, and
  `review-round-start` dropping option-bearing readiness gate arguments. Fixed
  those gaps, tightened clean-mode privacy checks, updated smoke fixtures, and
  verified Slice 1 with Pants fmt/lint/check/test, opponent/report review
  smokes, check-scripts, check-private, git diff --check, and `pants run :omen`
  (grade A; remaining hotspot output is repo-baseline advisory evidence).

## Decision Log

- 2026-05-18: Chose a first-class clean artifact path
  `outputs/oponent_posudek_navrh.md` instead of preserving ad hoc work-local
  clean draft paths.
- 2026-05-18: Kept `work/oponent_posudek_draft.md` as the trace-bound internal
  draft. The IS-entry proposal is report-facing; the canonical draft remains the
  machine-checkable provenance anchor.
- 2026-05-18: Chose explicit checker modes over heuristics based on missing
  metadata. Missing metadata in clean mode is intentional; missing metadata in
  canonical mode is an error.
- 2026-05-18: Treated hash refresh as deterministic maintenance, not semantic
  review. The refresh command must only update hashes/statuses for existing
  file references.
- 2026-05-18: Treated the private student comment as an IS-facing but non-public
  report field. It should be generated, checked, reviewed, and revalidated like
  the public report text, while allowing practical defense/future-work advice
  that would be too detailed for the public report.
- 2026-05-18: Confirmed that Pants, not direct `pytest`, is the authoritative
  Python test runner for closeout in this repository. Pants invocations must be
  serialized.
- 2026-05-18: Decided that approval records should be created through
  validator-backed tooling rather than by reviewer agents hand-writing JSON.
  Independent semantic review remains mandatory; the tooling only records the
  already-completed review in the schema expected by manifest and coverage
  checks.
- 2026-05-18: Decided that profile-specific closeout state must be explicit.
  A round may legitimately move from opponent materials to opponent report
  review, but stale `review_run_trace`, role plans, packet refs, and common
  briefing hashes must not require ad hoc manual JSON repair.
- 2026-05-18: Decided that IS form values should be explicit fields in the
  report draft. They are report-entry data, not prose, and therefore should be
  validated against controlled option labels and numeric ranges.
- 2026-05-18: Decided that the submitted IS PDF is a distinct archival artifact.
  It should be captured after submission and checked against the reviewed report
  basis, but it should not replace the reviewed draft or reopen semantic review
  unless the submitted values/text materially differ.
- 2026-05-18: Decided that submitted-report validation should compare a public
  IS projection, not the full Markdown draft. The submitted PDF is the public
  export and uses IS-specific labels, while any prose differences need either
  exact matching or explicit operator acceptance as submitted-form edits. The
  non-public student comment remains separate submitted-form evidence, not PDF
  comparison evidence.
- 2026-05-18: Decided that the normal opponent-report-review route must use
  `review-round-start` and `prepare-review-round` for the
  `opponent_report_review` profile before spawning the final reviewer. The plan
  should not rely on a chat-only agent launch or manually patched role state.
- 2026-05-18: Decided that clean report validation may check privacy, structure,
  placeholder state, and structured evidence links, but must not infer
  similarity materiality from free-form report prose.
- 2026-05-18: Decided that post-submission archive readiness comes after
  submitted PDF capture and typed delta classification. Slice 5 is therefore
  pre-submission report-review closeout; Slice 6 is archive closeout.

## Final Audit

Not run. This plan is active. Implementation is not complete; reconcile the
current uncommitted candidate edits with Slice 1 and Slice 3 before executing
later slices.
