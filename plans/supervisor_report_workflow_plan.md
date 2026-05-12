# Supervisor Report Workflow Plan

Status: in progress
Created: 2026-05-12

## Goal

Add a first-class workflow for the formal supervisor report (`posudek
vedouciho`) as a new branch separate from iterative student-facing supervisor
feedback. The workflow should produce a reviewed draft for the FIT IS report
fields, use the supervisor's explicit input as authoritative evidence for
student activity and collaboration, and optionally use prior supervisor feedback
and revision evidence when it is available and probative.

## Audit Base

Current state:

- Supervisor workflow currently targets student-facing feedback only:
  `work/feedback_student_draft.md`, `outputs/feedback_student.md`, and
  `work/reviews/feedback_student_review.json`.
- Opponent workflow has a useful report pattern:
  `outputs/oponent_podklady_revidovane.md` ->
  `work/opponent_report_trace.json` -> `work/oponent_posudek_draft.md`,
  with `scripts/check-opponent-report` and independent report review.
- Historical calibration exists only for opponent reports. It is private,
  artifact-based, optional, hash-bound, and supplemental to current-case
  evidence.
- `profiles/default.md` and `profiles/local/<profile-id>.md` already provide a
  preference layer for reviewer style, but they do not replace case evidence or
  supervisor input.
- The public default reviewer profile does not yet say how formal supervisor
  reports should be shaped. The supervisor-report workflow should extend the
  existing profile model instead of introducing a separate profile system.
- No tracked skill, command, artifact registry entry, wave gate, manifest rule,
  template, or TODO item currently defines a formal supervisor-report workflow.
- Operator command surface is a standing contract: every new logical workflow
  command needs a Python CLI module, `WORKFLOW_COMMAND_MODULES` registration,
  Pants/PEX packaging, generated `.cmd`/`.ps1` launchers, smoke coverage, and
  command-surface documentation in the same implementation slice that introduces
  the command.
- Recent context-efficiency work made packet-first, handoff-first review the
  default for larger workflows. Supervisor-report packets must reuse shared
  packet/materiality/handoff helpers rather than inventing a parallel packet
  style.

Audit commands used before creating this plan:

```bash
sed -n '1,220p' AGENTS.md
sed -n '1,240p' plans/README.md
sed -n '1,220p' WORKFLOW_MEMORY.md
rg -n "supervisor[-_ ]report|posudek vedouc|vedouciho posud|feedback_student|oponent_posudek|opponent_report_trace|reviewer_calibration_profile" AGENTS.md README.md TODO.md profiles templates docs plans .agents/skills src scripts tests -S
```

Constraints:

- Keep real supervisor reports, student PDFs, source zips, extracted text,
  submitted code, private notes, and generated case outputs under ignored
  `cases/`.
- Do not merge this workflow into `outputs/feedback_student.md`; the audience,
  authority model, and official IS fields are different.
- Do not infer student activity, independence, communication, preparedness, or
  timeliness from weak indirect signals. The supervisor's explicit report input
  is authoritative for these dimensions.
- Prior feedback is optional secondary evidence. If prior feedback and revision
  diffs show that the student reacted to concrete recommendations, the workflow
  may use that as positive evidence of responsiveness and working process. If
  feedback is absent, stale, not comparable, or inconclusive, the workflow must
  say so internally and rely on supervisor input instead.
- Deterministic code must validate structured artifacts, paths, hashes, and
  required fields. Semantic interpretation of feedback history, student
  activity, or report tone belongs to explicitly authorized agents or human
  reviewers.
- Agents should consume compact structured handoffs first, open full evidence
  artifacts only for verification or contradiction checks, and return short
  final messages that name files, findings, checks, and limitations instead of
  pasting full artifacts already written to disk.
- Windows remains supported. New operator commands need Python/Pants/PEX targets
  and packaged `.cmd`/`.ps1` launchers; POSIX `scripts/<tool>` files may only be
  convenience wrappers.

## Report Fields

The workflow must cover these FIT IS sections:

- `Informace k zadani`: thesis difficulty, relation to previous or running
  projects, satisfaction with results, unmet assignment parts, seriousness, and
  reasons.
- `Prace s literaturou`: student's activity in finding and using study
  materials.
- `Aktivita behem reseni, konzultace, komunikace`: activity, deadlines,
  consultation cadence, communication, and preparedness.
- `Aktivita pri dokoncovani`: whether the work was finished in sufficient
  advance and whether the final content was consulted.
- `Publikacni cinnost, oceneni`: publications, open-source release, responses,
  and awards related to the work.
- `Celkove hodnoceni`: grade `A-F`, points `0-100`, and official free-text
  assessment.
- `Komentar pro studenta`: non-printed IS comment visible to the student only;
  suitable for motivation, future advice, or feedback that does not belong in
  the official public report text.

## Evidence Model

Authoritative supervisor input:

- Lives in `notes/supervisor-report-operator-input.md`.
- Captures non-observable dimensions: activity, independence, communication,
  preparedness, deadline behavior, completion process, publication context,
  preferred grade/points or grade interval, and private student comment intent.
- May override weak secondary signals, but should still be written in a fair,
  evidence-aware style.

Current-case thesis/code evidence:

- Uses the same evidence roles as supervisor feedback and opponent materials:
  assignment/text, code consistency, code quality/design, quantitative claims,
  literature/citation, figure/media, typography/formal, and GitHub intake when
  relevant.
- For code-bearing final reports, the workflow should use both
  `thesis-code-consistency` and `thesis-code-quality-review`, or record a
  concrete typed limitation.
- The submitted thesis PDF remains the authoritative rendered thesis artifact.

Prior feedback and revision evidence:

- The workflow should read previous `outputs/feedback_student.md` files,
  `notes/previous-feedback-index.md`, and `outputs/revision_diff.md` when they
  exist.
- Prior feedback can support statements such as "student reacted well to
  repeated guidance" only when there is concrete evidence that a previous
  recommendation was addressed in later thesis/code artifacts.
- Prior feedback must not be treated as proof of activity if it is only a list
  of comments with no later response evidence.
- Absence of prior feedback is not a blocker and must not be interpreted as poor
  student activity.

Calibration evidence:

- Historical supervisor reports may later be used as private style/strictness
  calibration, analogous to opponent calibration but not opponent-named.
- Historical calibration must remain optional, private, applicability-aware, and
  supplemental to current-case evidence and supervisor input.
- A missing historical profile should produce an advisory only, not a readiness
  failure.

## Target Artifacts

Default artifacts in the active round:

- `notes/supervisor-report-operator-input.md` - supervisor-authored report
  intake for authoritative non-observable dimensions.
- `work/supervisor_report_feedback_history.json` - structured optional summary
  of prior feedback, addressed/unaddressed evidence, and limitations.
- `work/supervisor_report_trace.json` - structured mapping from current
  evidence, supervisor input, optional feedback history, grading calibration,
  and limitations to FIT IS report fields.
- `work/vedouci_posudek_draft.md` - generated draft for supervisor review and
  editing.
- `outputs/vedouci_posudek_revidovany.md` - reviewed supervisor-report draft.
- `work/reviews/supervisor_report_review.json` - independent review approval
  record binding the reviewed output and review basis by hash.
- `work/supervisor_report_confirmation.json` - explicit supervisor confirmation
  that the reviewed output's grade, points, official text, and private student
  comment are the version intended for IS entry.
- Optional later calibration artifacts under `work/calibration/` and
  `outputs/supervisor_report_calibration_profile.md` only when explicitly
  running a private historical supervisor-report calibration workflow.

The reviewed Markdown is still a draft for the human supervisor. The supervisor
must confirm final grade, points, official wording, and private student comment
before copying into IS.

## Scope

In scope:

- New repo-local skills for drafting and reviewing supervisor reports.
- New intake template for supervisor report input.
- Structured trace and feedback-history schemas.
- A report-specific readiness gate that extends existing supervisor readiness
  rather than replacing it.
- Deterministic validators/checkers for trace, draft, review approval, hashes,
  required fields, public/private text boundaries, grade/point consistency, and
  path leaks.
- Draft helper from `work/supervisor_report_trace.json` to
  `work/vedouci_posudek_draft.md`.
- Review and closeout integration with `work/review_manifest.json`,
  `work/agent_coverage.json`, and `scripts/check-review-wave`.
- Optional private historical supervisor-report calibration plan or generalized
  reviewer-report calibration layer.
- README, AGENTS, TODO, artifact registry, command-surface, packaging, tests,
  and smoke coverage updates.

Out of scope:

- Auto-submitting to FIT IS.
- Replacing the supervisor's grade/points judgment.
- Treating prior feedback as mandatory.
- Guessing student activity from commit counts, message frequency, or raw notes
  without explicit supervisor interpretation.
- Copying real historical reports or generated private calibration profiles into
  tracked paths.
- Changing the student-facing feedback workflow except where it exposes reusable
  evidence for this report branch.

## Readiness Semantics

`scripts/check-supervisor-report-ready <case-id> [round-id]` should be the
pre-generation gate. It extends `scripts/check-supervisor-ready <case-id>
[round-id]`; it does not replace the shared supervisor assignment, work type,
academic year, reviewer profile, and language/profile checks. It adds
report-specific checks for the active round, supervisor-report intake, explicit
unknown markers, and completion-timing context.

Supervisor report readiness should hard-fail on:

- missing assignment/work type/reviewer profile context;
- missing `notes/supervisor-report-operator-input.md`;
- missing explicit supervisor statement for activity/communication/completion
  dimensions, or an explicit "unknown / do not assess beyond available evidence"
  marker for each;
- invalid grade or point values when they are provided;
- stale or invalid `work/supervisor_report_trace.json` when drafting/checking a
  report;
- missing independent review approval before treating
  `outputs/vedouci_posudek_revidovany.md` as reviewed;
- missing or stale `work/supervisor_report_confirmation.json` before treating
  the reviewed draft as ready for IS.

Supervisor report readiness should warn, not hard-fail, on:

- no previous supervisor feedback;
- previous feedback exists but no revision diff is available;
- previous feedback is present but inconclusive about responsiveness;
- no historical supervisor-report calibration profile;
- unavailable optional evidence roles that are not material to the current
  report.

Readiness levels should be explicit:

- `draft_ready`: formal inputs exist and role evidence can be generated;
- `reviewed`: `outputs/vedouci_posudek_revidovany.md` has a current independent
  review record;
- `ready_for_is`: the reviewed output is also confirmed by the supervisor in
  `work/supervisor_report_confirmation.json`.

## Slices

### Slice 1 - Plan Review And Workflow Contract

- Status: done
- Proposed commit message: `docs(workflow): plan supervisor report workflow`
- Expected paths:
  - `plans/supervisor_report_workflow_plan.md`
  - `TODO.md`
- Tasks:
  - Review this plan with agents before implementation.
  - Check the plan against `AGENTS.md`, `plans/README.md`,
    `WORKFLOW_MEMORY.md`, and existing supervisor/opponent report patterns.
  - Confirm final artifact names and whether Czech output filenames are kept.
  - Keep this plan case-neutral and free of historical report content.
- Verification:
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

### Slice 2 - Intake Template And Skill Skeleton

- Status: done
- Proposed commit message: `docs(workflow): add supervisor report skill`
- Expected paths:
  - `.agents/skills/thesis-supervisor-report/SKILL.md`
  - `.agents/skills/thesis-supervisor-report-review/SKILL.md`
  - `templates/supervisor-report-intake.md`
  - `templates/reviewer-profile.md`
  - `AGENTS.md`
  - `README.md`
  - `profiles/default.md`
- Tasks:
  - Add a chat-first skill for formal supervisor reports.
  - Add a required review skill for `outputs/vedouci_posudek_revidovany.md`.
  - Add intake fields for the supervisor-only dimensions and explicit unknown
    markers.
  - Document that previous feedback is optional secondary evidence and never a
    substitute for supervisor input.
  - Add an explicit default supervisor-report style section to
    `profiles/default.md`: official-text tone, concision, how to frame
    assignment difficulty/results, how to separate public report text from the
    private student comment, and how to express grade/points calibration without
    pretending the profile is evidence.
  - Extend `templates/reviewer-profile.md` so private profiles can override
    supervisor-report style preferences, while preserving that profiles are only
    preference layers and never authoritative evidence.
  - Require the same context-efficiency contracts as current supervisor/opponent
    workflows: compact agent final responses, handoff-first synthesis, no full
    artifact bodies in chat when files are on disk, bounded agent scheduling, and
    high-reasoning semantic reviewer roles.
- Verification:
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

### Slice 3 - Structured Trace And Feedback-History Contract

- Status: done
- Proposed commit message: `feat(workflow): validate supervisor report trace`
- Expected paths:
  - `src/thesis_review_workflow/artifact_registry.py`
  - `src/thesis_review_workflow/work_artifacts.py`
  - `src/thesis_review_workflow/structured_evidence.py`
  - `src/thesis_review_workflow/supervisor_report.py`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `src/thesis_review_workflow/cli/check_supervisor_report_ready.py`
  - `src/thesis_review_workflow/cli/check_supervisor_report.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `docs/workflow-command-surface.md`
  - `scripts/check-supervisor-report-ready`
  - `scripts/check-supervisor-report`
  - `scripts/BUILD`
  - `tests/test_supervisor_report.py`
  - `tests/test_structured_evidence.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-supervisor-report`
- Tasks:
  - Add single-source artifact metadata for
    `outputs/vedouci_posudek_revidovany.md`, report trace, feedback history,
    confirmation JSON, draft, and review approval before downstream validators
    or closeout logic depend on those paths.
  - Implement `scripts/check-supervisor-report-ready` as an extension of
    `scripts/check-supervisor-ready`, with report-intake checks and
    `case-doctor` diagnostics kept advisory.
  - Define `supervisor-report-feedback-history-v1`.
  - Define `supervisor-report-trace-v1` with report fields, evidence refs,
    supervisor-input refs, prior-feedback status, grading/points state,
    uncertainty, manual checks, and limitations.
  - Define `supervisor-report-confirmation-v1` and its required hash bindings,
    but make it required only for `ready_for_is`, not for draft generation.
  - Validate grade `A-F`, points `0-100`, required IS fields, report refs,
    source hashes, stale references, and path safety.
  - Ensure feedback-history validation distinguishes `absent`, `present`,
    `evidenced_response`, `evidenced_partial_response`,
    `evidenced_nonresponse`, `no_comparable_revision`, and `inconclusive`.
    Evidence-bearing statuses must carry source refs and hashes; deterministic
    code validates structure only.
  - Register the new commands in `WORKFLOW_COMMAND_MODULES`, Pants/PEX targets,
    runtime deps, generated launcher coverage, and command-surface docs in this
    slice.
  - Keep deterministic validation structural; no semantic raw-text inference.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests:: scripts::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_supervisor_report.py tests/test_structured_evidence.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-supervisor-report`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`
  - `pants run :omen`

### Slice 4 - Draft Helper And Report Shape

- Status: done
- Proposed commit message: `feat(workflow): draft supervisor report`
- Expected paths:
  - `src/thesis_review_workflow/cli/draft_supervisor_report.py`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/check_supervisor_report.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `docs/workflow-command-surface.md`
  - `scripts/draft-supervisor-report`
  - `scripts/BUILD`
  - `tests/test_draft_supervisor_report.py`
  - `tests/test_supervisor_report.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-supervisor-report`
- Tasks:
  - Generate `work/vedouci_posudek_draft.md` from
    `work/supervisor_report_trace.json`.
  - Include all FIT IS fields in a stable Markdown structure.
  - Keep official report text separate from the non-printed student comment.
  - Preserve source trace path/hash comments for validation, but prevent those
    comments from leaking into public report prose.
  - Require human/supervisor calibration for final grade, points, and wording
    before reviewed output is treated as ready.
  - Register `scripts/draft-supervisor-report` in `WORKFLOW_COMMAND_MODULES`,
    Pants/PEX targets, runtime deps, generated launcher coverage, and
    command-surface docs in this slice.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests:: scripts::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_draft_supervisor_report.py tests/test_supervisor_report.py tests/test_structured_evidence.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-supervisor-report`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 5 - Materiality, Packets, And Review Waves

- Status: done
- Proposed commit message: `feat(workflow): prepare supervisor report review waves`
- Expected paths:
  - `src/thesis_review_workflow/review_materiality.py`
  - `src/thesis_review_workflow/review_packets.py`
  - `src/thesis_review_workflow/supervisor_report_packets.py`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/review_wave_gate.py`
  - `src/thesis_review_workflow/cli/prepare_supervisor_report_packets.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `docs/workflow-command-surface.md`
  - `scripts/prepare-supervisor-report-packets`
  - `scripts/BUILD`
  - `tests/test_review_materiality.py`
  - `tests/test_supervisor_report_packets.py`
  - `tests/test_review_wave_gate.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-supervisor-report-packets`
  - `scripts/smoke-review-wave`
  - `scripts/smoke-supervisor-report`
- Tasks:
  - Add a `supervisor_report` materiality profile.
  - Reuse the shared packet layer (`PacketRole`, generated-role pruning,
    materiality next actions, current evidence snapshots, and compact
    quantitative handoffs). Add only report-specific role definitions and report
    wording, not a parallel packet implementation style.
  - Prefer a dedicated `work/supervisor_report_packets/` directory unless review
    shows that extending `work/supervisor_packets/` preserves clear
    report-versus-feedback boundaries without prompt bloat.
  - Add `supervisor_report` wave gates for trace, draft, and reviewed final.
  - Require `scripts/check-review-wave --workflow supervisor_report` after
    trace/draft/final waves when expected files should exist.
  - Register packet command surface and package launchers in this slice.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests:: scripts::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_review_materiality.py tests/test_supervisor_report_packets.py tests/test_review_wave_gate.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-supervisor-report-packets`
  - `scripts/smoke-review-wave`
  - `scripts/smoke-supervisor-report`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`
  - `pants run :omen`

### Slice 6 - Review, Manifest, Coverage, Confirmation, And Closeout

- Status: pending
- Proposed commit message: `feat(workflow): close supervisor report review`
- Expected paths:
  - `src/thesis_review_workflow/review_approvals.py`
  - `src/thesis_review_workflow/agent_coverage.py`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/case_doctor_summary.py`
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `src/thesis_review_workflow/cli/check_private.py`
  - `src/thesis_review_workflow/cli/write_review_approval.py`
  - `src/thesis_review_workflow/cli/confirm_supervisor_report.py`
  - `src/thesis_review_workflow/cli/supervisor_report_closeout.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `docs/workflow-command-surface.md`
  - `scripts/confirm-supervisor-report`
  - `scripts/supervisor-report-closeout`
  - `scripts/BUILD`
  - `tests/test_review_wave_gate.py`
  - `tests/test_review_approvals.py`
  - `tests/test_review_manifest_helpers.py`
  - `tests/test_agent_coverage.py`
  - `tests/test_work_artifacts.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-agent-coverage`
  - `scripts/smoke-review-approval`
  - `scripts/smoke-review-wave`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-supervisor-report`
- Tasks:
  - Add approval profile `supervisor-report` for
    `work/reviews/supervisor_report_review.json`, with reviewed artifact
    `outputs/vedouci_posudek_revidovany.md`, review basis
    `work/vedouci_posudek_draft.md`, expected skill role, and required checks.
  - Extend `scripts/write-review-approval --profile supervisor-report` so the
    review approval JSON is generated through the existing helper, not authored
    by hand.
  - Extend manifest collection and closeout checks to consume the artifact/work
    registry entries added in Slice 3.
  - Add `supervisor_report_review` coverage role and ensure code-bearing
    supervisor reports require both code consistency and code quality evidence,
    or a typed limitation.
  - Include `outputs/vedouci_posudek_revidovany.md` as a final synthesis target
    for manifest code-evidence and stale-review checks.
  - Surface supervisor-report state in `case-doctor` without making
    `case-doctor` a readiness gate.
  - Extend privacy checks for new private work/output artifact names.
  - Add `scripts/confirm-supervisor-report` to write or validate
    `work/supervisor_report_confirmation.json` after the supervisor confirms
    grade, points, official text, and private student comment.
  - Ensure material edits after review produce stale-hash failures.
  - Add closeout that runs readiness, trace/draft validation, manifest update,
    agent coverage, review manifest completeness, confirmation validation,
    private checks, script checks, and whitespace hygiene.
  - Register confirmation and closeout command surfaces and package launchers in
    this slice.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests:: scripts::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_review_wave_gate.py tests/test_review_approvals.py tests/test_review_manifest_helpers.py tests/test_agent_coverage.py tests/test_work_artifacts.py tests/test_supervisor_report.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-agent-coverage`
  - `scripts/smoke-review-approval`
  - `scripts/smoke-review-wave`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-supervisor-report`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 7 - Optional Historical Supervisor Calibration

- Status: pending
- Proposed commit message: `feat(workflow): add supervisor report calibration`
- Expected paths:
  - `docs/supervisor-report-calibration.md`
  - `.agents/skills/historical-supervisor-report-calibration/SKILL.md`
  - `src/thesis_review_workflow/supervisor_report_calibration.py`
  - `src/thesis_review_workflow/cli/check_supervisor_report_calibration_profile.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/artifact_registry.py`
  - `src/thesis_review_workflow/work_artifacts.py`
  - `docs/workflow-command-surface.md`
  - `scripts/check-supervisor-report-calibration-profile`
  - `scripts/BUILD`
  - `tests/test_supervisor_report_calibration.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-supervisor-report-calibration-profile`
- Tasks:
  - Choose one implementation direction before coding this slice:
    `reviewer-report-calibration` with explicit `profile_kind`, or
    supervisor-specific artifact names/schemas. Do not reuse opponent-named
    registry entries ambiguously.
  - Register `scripts/check-supervisor-report-calibration-profile` in
    `WORKFLOW_COMMAND_MODULES`, `src/thesis_review_workflow/cli/BUILD`,
    `WORKFLOW_CLI_RUNTIME_DEPS`, `scripts/BUILD` PEX targets, generated launcher
    coverage, and command-surface docs in this slice.
  - Keep real historical supervisor reports private under ignored `cases/`.
  - Synthesize Markdown-first calibration profiles with JSON manifests,
    source-case analyses, profile history, review records, and applicability
    limits.
  - Add current-case use/advisory artifacts that are optional and hash-bound.
  - Add anti-overfit review so style and strictness calibration never substitute
    for current-case evidence or supervisor input.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests:: scripts::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_supervisor_report_calibration.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-supervisor-report-calibration-profile`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 8 - Documentation, TODO Reconciliation, And Archive

- Status: pending
- Proposed commit message: `docs(workflow): close supervisor report workflow`
- Expected paths:
  - `README.md`
  - `AGENTS.md`
  - `TODO.md`
  - `docs/workflow-command-surface.md`
  - `plans/supervisor_report_workflow_plan.md`
  - `plans/archive/supervisor_report_workflow_plan.md`
- Tasks:
  - Document the chat-first supervisor-report workflow in README.
  - Audit packaged command-surface entries for all new logical commands rather
    than adding them for the first time here.
  - Reconcile TODO by removing the completed supervisor-report item or moving
    residual calibration work into a narrower item.
  - Run final validation and archive the plan after the final audit is recorded.
- Verification:
  - `pants fmt ::`
  - `pants lint ::`
  - `pants check ::`
  - `pants test tests::`
  - `scripts/smoke-supervisor-report`
  - `scripts/smoke-supervisor-report-packets`
  - `scripts/smoke-supervisor-report-calibration-profile`
  - `scripts/smoke-review-wave`
  - `scripts/smoke-review-approval`
  - `scripts/smoke-agent-coverage`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git status --short --untracked-files=all`
  - `git diff --check`

## Agent Workflow

When the user explicitly authorizes agents for a supervisor report, run role
agents in bounded waves:

- assignment/text and results evidence;
- code consistency and code quality when code exists;
- quantitative/result claims when metrics or evaluation matter;
- literature/citation when source use is material;
- prior-feedback and revision-response analysis when previous feedback exists;
- `scripts/update-current-evidence-snapshot <case-id> [round-id]`;
- `scripts/check-review-materiality --workflow supervisor_report <case-id>
  [round-id]`;
- `scripts/prepare-supervisor-report-packets <case-id> [round-id]`;
- supervisor-report synthesis into `work/supervisor_report_trace.json`;
- draft generation into `work/vedouci_posudek_draft.md`;
- independent report review into `outputs/vedouci_posudek_revidovany.md`.

Use at most two spawned workflow agents concurrently by default. The synthesis
agent must treat supervisor input as authoritative for non-observable student
process dimensions and must mark prior feedback as absent or inconclusive when
it cannot support a concrete conclusion.

Supervisor-report synthesis and review agents must read `## Synthesis Handoff`
sections and structured JSON summaries first. They should open full prior
feedback, code, thesis extracts, or internal evidence artifacts only to verify
P0/P1 claims, resolve contradictions, or answer reviewer challenges. Chat final
responses should stay compact and should never paste the full report draft or
full historical feedback when those artifacts are already on disk.

## Deferred TODO Items

- Decide whether historical supervisor and opponent calibration should converge
  into one generic reviewer-report calibration subsystem after both V1 workflows
  are exercised.
- Consider a later IS export helper only after Markdown report shape and review
  semantics are stable.
- Consider feedback-history extraction helpers only after manual structured
  feedback-history summaries prove useful; avoid raw-text heuristics.

## Progress

- 2026-05-12: Created initial plan after repository audit and user decision to
  make supervisor reports a separate workflow branch. The user explicitly asked
  for optional use of previous supervisor feedback when it proves responsiveness,
  while keeping supervisor input authoritative when feedback is absent or
  inconclusive.
- 2026-05-12: Agent review findings were incorporated into the plan: command
  packaging moved into command-introducing slices, `check-supervisor-report-ready`
  was made explicit, `work/supervisor_report_confirmation.json` was added for
  the `ready_for_is` boundary, prior-feedback statuses were expanded, and
  manifest/coverage/materiality/work-artifact surfaces were named directly.
- 2026-05-12: Follow-up review tightened context-efficiency and Windows
  command-surface details: supervisor-report packets must reuse shared packet
  helpers, new skills must preserve compact final-response and handoff-first
  contracts, artifact registry entries move into the first implementation slice,
  approval records must use `scripts/write-review-approval`, and calibration
  command packaging must include the same `WORKFLOW_COMMAND_MODULES` and
  `tests/test_workflow_python_contracts.py` coverage as other operator tools.
- 2026-05-12: Seeded `profiles/default.md` with case-neutral supervisor-report
  style preferences synthesized from private historical supervisor reports:
  concise official sections, first-person supervisor voice, calibrated
  assignment/result/process wording, and a strict boundary between official
  report text and the private student comment. No historical report content or
  case-specific facts were copied into tracked files.
- 2026-05-12: Implemented Slice 2 skill/template/docs wiring and folded in
  two-agent review findings: supervisor reports now participate in the
  top-level multi-agent authorization rule, downstream synthesis review wording
  includes supervisor reports, the new skills split required inputs from
  generated outputs, and planned deterministic commands are described as
  implementation blockers until their command surface lands in later slices.
- 2026-05-12: Implemented Slice 3 structured contract and command surface:
  supervisor-report readiness and report checkers now validate intake,
  feedback-history evidence binding, trace fields, reviewed Markdown, grade and
  point consistency, supervisor confirmation, manifest helper checks, approval
  profile coverage, private-artifact scanning, agent coverage, package launcher
  generation, and smoke coverage. Two review agents found structural gaps in
  intake coverage, evidence hashes, draft/review/confirmation consistency,
  private-section slicing, approval checks, and manifest closeout; those
  findings were fixed before commit. Omen passed as developer hygiene with
  grade A / overall score 91.20 and existing hotspot-style warnings, including
  shared manifest and structured-evidence modules.
- 2026-05-12: Implemented Slice 4 draft helper: `draft-supervisor-report`
  generates `work/vedouci_posudek_draft.md` from the structured trace, embeds
  only hash-bound validation comments as metadata, preserves the seven FIT IS
  fields in stable order, keeps the private student comment separate, validates
  the draft immediately, and participates in `WORKFLOW_COMMAND_MODULES`,
  Pants/PEX packaging, smoke coverage, and command-surface docs. Agent review
  found no command-surface issues; semantic review found private-comment leak
  and visible metadata risks plus title/confirmation edge cases, all fixed
  before commit.
- 2026-05-12: Implemented Slice 5 packet and wave preparation:
  `prepare-supervisor-report-packets` creates compact role packets under
  `work/supervisor_report_packets/`, reusing shared `PacketRole`, materiality,
  current-evidence, quantitative-handoff, late-communication, generated-role
  pruning, and Omen advisory sections. `supervisor_report` now has profile
  scoped materiality under `work/review_materiality/supervisor_report/`, so it
  does not clobber supervisor-feedback or opponent-review materiality. Review
  wave gates cover trace, draft, and final report; the final wave requires the
  independent `work/reviews/supervisor_report_review.json` approval record, not
  only reviewed Markdown shape. Agent review found and prompted fixes for final
  approval gating, optional prior-feedback labeling, and profile-scoped
  materiality. Omen passed as developer hygiene with grade A / overall score
  90.88 and existing shared-module hotspot warnings.

## Decision Log

- Supervisor reports are a separate workflow branch, not an extension of
  `outputs/feedback_student.md`.
- Supervisor input is authoritative for activity, independence, consultation,
  communication, preparedness, finishing process, grade/points calibration, and
  private student comment intent.
- Prior feedback is optional secondary evidence. It may improve process
  assessment when it shows concrete response to feedback, but absence or weak
  evidence is not negative evidence.
- A reviewed Markdown draft is not the final IS boundary. `ready_for_is`
  additionally requires explicit supervisor confirmation bound to the reviewed
  artifact hash.
- Use a trace-to-draft pattern similar to opponent reports because it keeps
  official report fields, evidence, manual checks, and hashes explicit.
- Historical supervisor reports should calibrate style and strictness only after
  explicit private workflow setup; they are not required for normal supervisor
  report generation.

## Final Audit

Not run yet. Fill before archiving:

- commands run
- skipped checks and reasons
- private pilot limitations
- residual TODO transfers
- archive commit
