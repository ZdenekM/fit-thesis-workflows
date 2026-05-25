# Supervisor Opponent Feedback Learning Plan

Status: in_progress
Created: 2026-05-25

## Goal

Allow supervisor cases to ingest external opponent reports for theses the
operator supervised, compare justified opponent criticism with earlier
supervisor feedback and workflow evidence, and promote recurring missed checks
back into the supervisor-review pipeline.

This is a postmortem and workflow-learning loop. It is not the same as
historical opponent calibration, which uses reports written by the operator as
private calibration for future opponent work. Here the source is an external
opponent report about a student supervised by the operator.

The target outcome is:

- a private, case-local way to store draft, official, or public opponent reports;
- an authorized semantic analysis that classifies opponent findings as already
  caught, partially caught, missed, disputed, or not actionable from available
  evidence;
- a structured promotion decision that separates case-only notes, current-student
  follow-up, durable supervisor preferences, general workflow rules, and TODO or
  follow-up-plan work;
- no deterministic inference from raw opponent-report prose.

## Audit Base

Current relevant workflow state:

- Supervisor feedback is iterative and already reads prior
  `outputs/feedback_student.md` files in the same case.
- Formal supervisor reports and student-facing feedback already require
  explicit authorization before agent-produced sendable artifacts.
- Code-bearing supervisor workflows must use both code consistency and code
  quality review, or record a concrete limitation.
- Historical opponent calibration already has a private profile refresh workflow
  and an `opponent_calibration_refresh_eligibility.json` marker, but that route
  is scoped to reports written by the operator as an opponent.
- `templates/opponent-report-quality-feedback-intake.md` handles feedback on
  generated opponent-report drafts. It does not handle external opponent reports
  about supervised students.
- `plans/opponent_methodology_pipeline_plan.md` already owns generalized
  methodology, evaluation, evidence-mode, and operator-feedback promotion for
  opponent-report quality. This plan should route methodology-owned lessons
  there instead of duplicating them.
- `WORKFLOW_MEMORY.md` says recurring review patterns should be promoted after
  the current artifact is handled, at the narrowest durable layer.

Context reads and checks used when creating this plan:

```bash
sed -n '1,220p' .agents/skills/historical-opponent-calibration/SKILL.md
sed -n '1,220p' docs/agent-profile-matrix.md
sed -n '1,220p' plans/opponent_methodology_pipeline_plan.md
sed -n '1,180p' WORKFLOW_MEMORY.md
sed -n '1,260p' plans/archive/opponent_report_quality_learning_plan.md
sed -n '1,260p' docs/historical-opponent-calibration.md
sed -n '1,220p' templates/opponent-report-quality-feedback-intake.md
sed -n '1,130p' TODO.md
sed -n '1,220p' plans/README.md
sed -n '1,180p' README.md
```

Serena preflight and scoped use:

- `mcp__serena__.activate_project` activated `/home/zdenekm/code/diplomky_v2`.
- `mcp__serena__.initial_instructions` was read.
- `mcp__serena__.search_for_pattern` over workflow docs, plans, skills, and
  templates found existing calibration, operator-feedback, and report-quality
  surfaces. Result: the new loop should be supervisor-postmortem-specific and
  should not reuse the historical opponent profile refresh as a shortcut.

Constraints:

- All real opponent reports, extracted text, case analyses, and generated
  postmortem outputs stay under ignored `cases/`.
- Draft reports shared by an opponent before official submission must be marked
  with source status and use restrictions. They must not be copied into tracked
  docs or used as public evidence without an explicit permission/public-status
  record.
- Semantic interpretation of an opponent report requires explicit current-request
  authorization for agents or a human-authored structured artifact.
- Deterministic helpers may validate paths, hashes, allowed statuses, source
  bindings, and schema shape. They must not classify criticism as justified or
  missed by keyword matching.
- The workflow should finish or record the current-case postmortem before
  promoting a general rule. Do not promote one student's topic, metric, grade,
  point value, opponent wording, or case-specific conclusion.

## Scope

In scope:

- A case-local intake contract for external opponent reports attached to a
  supervised thesis case.
- Distinguishing source status:
  `draft_shared_for_consultation`, `official_private_copy`,
  `official_public`, and `unknown_or_restricted`.
- A private postmortem comparison against prior supervisor feedback, supervisor
  report evidence when present, revision diffs, thesis text, and code/review
  artifacts where relevant.
- A structured classification of opponent findings:
  `already_caught`, `partially_caught`, `missed_by_feedback`,
  `not_available_at_feedback_time`, `disputed_or_unverified`,
  `case_specific_only`, and `not_actionable`.
- Promotion routing to the narrowest durable owner:
  supervisor feedback skill, supervisor report skill, reviewer profile,
  methodology pipeline plan, code consistency, code quality, quantitative claims,
  literature/citation, figure/media, typography/formal, TODO, or no promotion.
- Future integration with supervisor feedback so recurring learned checks can be
  considered before new final-sprint feedback rounds.

Out of scope:

- Using an external opponent report as evidence about a different student's work.
- Automatically changing grades, reports, or student-facing feedback after an
  opponent report appears.
- Scraping public report repositories.
- Reimplementing historical opponent calibration or opponent-report draft
  quality learning.
- Storing real report excerpts in tracked fixtures, docs, plans, or tests.

## Proposed Case Layout

For a supervised case, store external opponent-report materials under the round
that represents the post-submission or defense-prep state:

```text
cases/<case-id>/
  rounds/
    <round-id>/
      notes/
        external-opponent-report-intake.md
      inputs/
        external_opponent_report/
          opponent-report.pdf
          opponent-report.txt
          public-url.txt
      work/
        external_opponent_report_intake.json
        external_opponent_feedback_findings.json
        supervisor_learning_candidates.json
      outputs/
        external_opponent_feedback_analysis.md
```

`inputs/external_opponent_report/` may contain the original PDF, exported text,
or a public URL record. The JSON intake binds the actual source paths and
hashes. The Markdown analysis is operator-only internal evidence and should be
registered and reviewed before it drives workflow promotion.

## Conceptual Contract

### Intake

The intake records:

- source status and whether the report may be used for workflow learning;
- whether the report is a draft, official private copy, or public artifact;
- paths and hashes for the report, extracted text, public URL, and any operator
  notes;
- whether the operator wants current-case follow-up, long-term learning, or both;
- whether agent use is authorized in the current request.

### Postmortem Analysis

An authorized agent or human reviewer compares opponent findings against:

- earlier `outputs/feedback_student.md` files in the case;
- revision diffs and current submitted thesis text;
- supervisor report evidence, if present;
- code consistency, code quality, quantitative, literature, figure/media,
  typography/formal, and Theses.cz evidence where present and relevant;
- operator notes about what was available at the time earlier feedback was
  written.

The analysis should answer:

- Which opponent criticisms appear justified by the submitted artifacts?
- Which of those had already been surfaced to the student?
- Which were absent from earlier feedback but could reasonably have been caught?
- Which were not available at the time, or depend on evidence the supervisor did
  not have?
- Which are case-specific and should not become workflow rules?
- Which recurring evidence class should be promoted?

### Promotion Decision

Each candidate lesson gets one primary route:

- `case_only`: useful for this student or defense prep only.
- `current_student_followup`: worth mentioning to the student after the report,
  if appropriate and permitted.
- `supervisor_profile`: durable private preference about strictness, emphasis,
  or wording.
- `workflow_docs_or_skill`: general workflow rule or prompt update.
- `methodology_pipeline`: method/evaluation/contribution-boundary item owned by
  `plans/opponent_methodology_pipeline_plan.md` or a later supervisor analogue.
- `specialized_review_workflow`: code consistency, code quality, quantitative,
  literature/citation, figure/media, typography/formal, Theses.cz, or GitHub
  intake.
- `todo_or_follow_up_plan`: useful but outside the current rollout.
- `discard`: unsupported, disputed, too case-specific, or already covered.

Promoted tracked wording must be abstract. It may name evidence classes and
review questions, not student identity, thesis topic, concrete metrics, grades,
or opponent-report text.

## Slices

### Slice 0 - Operator Contract And Template

Status: done

Expected paths:

- `README.md`
- `templates/external-opponent-report-intake.md`
- `plans/supervisor_opponent_feedback_learning_plan.md`
- `TODO.md`

Work:

- Add an operator-facing prompt example for adding an external opponent report
  to a supervised case.
- Add a case-local intake template with source status, permission, intended use,
  and private-data reminders.
- Track the larger implementation in TODO.

Verification:

```bash
git diff --check
scripts/check-private
scripts/check-scripts
```

### Slice 1 - Skill And Role Contract

Status: done

Expected paths:

- `AGENTS.md`
- `.agents/skills/thesis-supervisor-opponent-feedback-learning/SKILL.md`
- `.codex/agents/thesis-evidence-calibrator.toml`
- `src/thesis_review_workflow/agent_profiles.py`
- `docs/agent-profile-matrix.md`
- `docs/agent-scheduling.md` only if a new spawned role is introduced

Work:

- Define the DEEP workflow for external opponent-report postmortem analysis.
- Require explicit agent authorization before reading the opponent report or
  writing semantic findings.
- Reuse existing evidence roles where possible; add a new stable role only if
  parent orchestration cannot keep the boundary clean.
- Require independent review before `outputs/external_opponent_feedback_analysis.md`
  is treated as durable operator evidence.

Verification:

```bash
tests/test_agent_profile_contracts.py
git diff --check
scripts/check-private
scripts/check-scripts
```

### Slice 2 - Structured Artifacts And Validator

Status: done

Expected paths:

- `src/thesis_review_workflow/external_opponent_feedback.py`
- `src/thesis_review_workflow/cli/check_external_opponent_feedback.py`
- `src/thesis_review_workflow/commands.py`
- `src/thesis_review_workflow/helper_checks.py`
- `src/thesis_review_workflow/work_artifacts.py`
- `src/thesis_review_workflow/cli/BUILD`
- `src/thesis_review_workflow/cli/check_private.py`
- `scripts/BUILD`
- `scripts/check-external-opponent-feedback`
- `tests/test_external_opponent_feedback.py`
- `tests/test_check_private.py`

Work:

- Validate `work/external_opponent_report_intake.json`,
  `work/external_opponent_feedback_findings.json`, and
  `work/supervisor_learning_candidates.json` structurally.
- Validate status enums, source path safety, hashes, allowed promotion routes,
  current-case refs, and no obvious placeholders.
- Keep all semantic classification human/agent-authored.
- Add synthetic fixtures only.

Verification:

```bash
pants fmt src/thesis_review_workflow:: tests:: scripts::
pants lint src/thesis_review_workflow:: tests:: scripts::
pants check src/thesis_review_workflow:: tests:: scripts::
pants test tests/test_external_opponent_feedback.py
scripts/check-private
scripts/check-scripts
git diff --check
```

### Slice 3 - Supervisor Workflow Integration

Status: planned

Expected paths:

- `.agents/skills/thesis-supervisor-feedback/SKILL.md`
- `.agents/skills/thesis-supervisor-feedback-review/SKILL.md`
- `.agents/skills/thesis-supervisor-report/SKILL.md`
- `docs/operator-reference.md`
- `src/thesis_review_workflow/cli/case_doctor.py` if surfacing availability is useful

Work:

- Teach supervisor feedback and report workflows to notice reviewed postmortem
  learning artifacts in prior rounds without repeating old case-specific
  criticism mechanically.
- Surface a non-blocking `case-doctor` advisory when a case has an external
  opponent report intake but no reviewed postmortem analysis.
- Keep student-facing feedback phase-appropriate: learned patterns can improve
  checks, but prior external reports remain private context unless the operator
  explicitly asks to discuss them.

Verification:

```bash
pants test tests/test_case_doctor.py tests/test_supervisor_feedback_workflow.py
scripts/check-private
scripts/check-scripts
git diff --check
```

### Slice 4 - Promotion And Closeout

Status: planned

Expected paths:

- `docs/operator-reference.md`
- `.agents/skills/thesis-supervisor-opponent-feedback-learning/SKILL.md`
- `templates/external-opponent-report-intake.md`
- `WORKFLOW_MEMORY.md` only for durable lessons that are not yet promoted

Work:

- Add a closeout step that records whether each learning candidate was promoted,
  deferred, or discarded.
- Route durable personal preferences to ignored local reviewer profiles only
  after explicit operator approval.
- Route general workflow rules to skills/docs/templates/plans/TODO and mention
  the promotion in closeout.
- Ensure completed lessons are not left as duplicate active TODO entries.

Verification:

```bash
git diff --check
scripts/check-private
scripts/check-scripts
```

## Progress

- 2026-05-25: Plan created from operator request. Existing historical opponent
  calibration and opponent methodology plans were inspected and kept separate.
- 2026-05-25: Slice 0 operator contract scaffold added through README prompt,
  intake template, and TODO entry. Creation checks passed:
  `git diff --check`, `scripts/check-private`, `scripts/check-scripts`.
- 2026-05-25: Slice 1 agent/skill contract added. The new
  `thesis-supervisor-opponent-feedback-learning` skill is parent-orchestrated,
  requires explicit agent authorization before report-source reads or semantic
  findings, records independent evidence-calibrator review before durable
  analysis use, and is registered in `AGENTS.md`,
  `src/thesis_review_workflow/agent_profiles.py`, and
  `docs/agent-profile-matrix.md`. No new spawned role or scheduling rule was
  added.
- 2026-05-25: Slice 2 structured validator added for
  `work/external_opponent_report_intake.json`,
  `work/external_opponent_feedback_findings.json`, and
  `work/supervisor_learning_candidates.json`, with strict external-report
  source allowlisting under `inputs/external_opponent_report/`, hash-bound refs,
  enum checks, permission-aware promotion routing, forbidden raw-report text
  fields, review approval validation for
  `outputs/external_opponent_feedback_analysis.md`, POSIX/Pants/PEX command
  surface, and synthetic tests. Early checks passed:
  `pants test tests/test_external_opponent_feedback.py`,
  `pants check src/thesis_review_workflow:: tests/test_external_opponent_feedback.py tests/test_check_private.py scripts/check-external-opponent-feedback`,
  `pants test tests/test_agent_profile_contracts.py tests/test_check_private.py`,
  and `scripts/check-external-opponent-feedback --help`.
- 2026-05-25: Omen MCP was attempted on `src/thesis_review_workflow` and
  `src/thesis_review_workflow/work_artifacts.py`; both returned zero files for
  non-empty targets, so this is recorded as an MCP/path-handling blocker rather
  than code evidence. Use `pants run :omen` for reproducible closeout evidence.
- 2026-05-25: Post-implementation agent review findings were incorporated:
  metadata-only preflight now avoids semantic intake fields before
  authorization, `thesis_evidence_calibrator` owns
  `work/reviews/external_opponent_feedback_review.json`, durable validation is
  documented as `scripts/check-external-opponent-feedback --require-analysis`,
  `unknown_or_restricted` sources block findings, the require-analysis flag
  fails on an empty round, external approval records require the expected
  workflow profile/reviewer/check, and `inputs/external_opponent_report/` is
  treated as private regardless of file extension.

## Decision Log

- 2026-05-25: Treat external opponent reports for supervised theses as a
  supervisor-postmortem learning loop, not as opponent historical calibration.
- 2026-05-25: Store all real reports and analyses in ignored `cases/`; tracked
  artifacts contain only the case-neutral contract and synthetic future tests.
- 2026-05-25: Implement Slice 1 without a new stable spawned role. Parent
  orchestration owns synthesis, existing specialist roles provide fresh
  evidence when needed, and `thesis_evidence_calibrator` provides independent
  review separation.
- 2026-05-25: Deterministic validation for Slice 2 is limited to schema, enum,
  path, hash, placeholder, permission, review-record, and privacy-shape checks.
  It does not classify opponent criticism from raw prose.

## Final Audit

Not run yet. Slices 3 and 4 remain planned.
