---
name: thesis-supervisor-opponent-feedback-learning
description: DEEP postmortem workflow for learning from external opponent reports about theses the operator supervised, comparing opponent criticism with earlier supervisor feedback and routing durable lessons.
---

# Thesis Supervisor Opponent Feedback Learning

Command routing: treat `scripts/<tool>` examples below as logical workflow
command names. On Windows, use the packaged
`dist\workflow-tools\bin\<tool>.cmd` or `.ps1` launcher from `README.md`; do
not run or click extensionless `scripts/<tool>` files.

Use this skill when the operator has an external opponent report for a thesis
they supervised and wants a private postmortem that improves future supervisor
feedback or supervisor-report work. This workflow is about supervised-student
postmortem learning. Do not route it through historical opponent calibration,
which is for reports written by the operator as an opponent.

## Inputs

Work in the active case round unless the user names another round:

```text
cases/<case-id>/rounds/<round-id>/
  notes/external-opponent-report-intake.md
  inputs/external_opponent_report/
  work/external_opponent_report_intake.json
  work/external_opponent_feedback_findings.json
  work/supervisor_learning_candidates.json
  outputs/external_opponent_feedback_analysis.md
```

Also inspect earlier rounds in the same case for prior
`outputs/feedback_student.md`, `outputs/revision_diff.md`, supervisor-report
outputs, and reviewed specialist evidence such as code consistency, code
quality, quantitative claims, literature/citation, figure/media,
typography/formal, Theses.cz, and GitHub intake outputs when they exist.

## Authorization And Source Status

Before opening any file under `inputs/external_opponent_report/`, copied report
text, public-url record, or writing semantic findings, confirm that the current
user request explicitly authorizes agents to read the external report and
produce the postmortem analysis. If authorization is missing, stop after case
metadata and metadata-only intake preflight and ask for agent authorization.

Preflight may read `case.md`, `current-round.txt`, directory inventory, and
metadata-only fields from `work/external_opponent_report_intake.json` or the
`Source Status` and `Intended Use` sections of
`notes/external-opponent-report-intake.md` to determine whether a source exists,
its stated status, and permission. Do not read intake `Operator Context`,
`Comparison Basis`, `Promotion Decision Draft`, report-derived notes, or any
semantic criticism summaries before authorization. The semantic pass may proceed
only when `work/external_opponent_report_intake.json` records:

- one of the allowed source statuses:
  `draft_shared_for_consultation`, `official_private_copy`,
  `official_public`, or `unknown_or_restricted`;
- `workflow_learning_permission` compatible with the requested use;
- explicit `agent_report_reading_authorized: true`;
- hash-bound source refs under `inputs/external_opponent_report/`.

If the source is `unknown_or_restricted` or permission is archival-only, do not
read or summarize the report. Keep the artifact as stored evidence only, or ask
the operator for a clearer permission record.

## Process

1. Resolve case and round. Run
   `scripts/check-external-opponent-feedback <case-id> [round-id]` to validate
   the current structural state. If raw report files exist without intake,
   create or ask for the ignored case-local intake first.
2. Confirm current-request agent authorization before reading report sources or
   producing semantic classifications.
3. Read `work/external_opponent_report_intake.json` first. Use
   `notes/external-opponent-report-intake.md` only after authorization for
   operator context; it is not evidence for thesis-quality claims.
4. Open external report sources only as needed for the authorized comparison.
   Do not copy opponent-report excerpts into tracked paths, tests, templates, or
   plan files. In case-local artifacts, prefer locators over quotes unless the
   intake permits short private excerpts.
5. Compare report criticisms against prior supervisor feedback, revision diffs,
   current thesis/code evidence, supervisor-report artifacts, and specialist
   outputs that existed or were available at the relevant feedback time.
6. Write `work/external_opponent_feedback_findings.json` with
   `external-opponent-feedback-findings-v1`. Classification values are:
   `already_caught`, `partially_caught`, `missed_by_feedback`,
   `not_available_at_feedback_time`, `disputed_or_unverified`,
   `case_specific_only`, and `not_actionable`.
7. Write `work/supervisor_learning_candidates.json` with
   `supervisor-learning-candidates-v1`. Each candidate chooses the narrowest
   route: `case_only`, `current_student_followup`, `supervisor_profile`,
   `workflow_docs_or_skill`, `methodology_pipeline`,
   `specialized_review_workflow`, `todo_or_follow_up_plan`, or `discard`.
8. Draft `outputs/external_opponent_feedback_analysis.md` as private operator
   evidence. Keep it case-local and avoid raw report quotes unless the intake
   explicitly permits them. Tracked changes promoted from the analysis must be
   abstract evidence classes, not student identity, thesis topic, concrete
   metrics, grades, or opponent-report wording.
9. Run `scripts/check-external-opponent-feedback <case-id> [round-id]
   --require-analysis`.
10. Have a different explicitly authorized reviewer run an independent review
    before treating `outputs/external_opponent_feedback_analysis.md` as durable
    operator evidence. Record the approval in
    `work/reviews/external_opponent_feedback_review.json`, with
    `reviewed_artifact_path: outputs/external_opponent_feedback_analysis.md`,
    a hash-bound basis such as `work/supervisor_learning_candidates.json`, and
    `checks_observed` including `check-external-opponent-feedback`.
11. Only after the current-case artifact is handled, promote durable lessons to
    the owner named by `work/supervisor_learning_candidates.json`. Personal
    preferences go to the private reviewer profile after operator approval;
    general workflow rules go to skills/docs/templates/plans/TODO; methodology
    lessons route to `plans/opponent_methodology_pipeline_plan.md` or a future
    supervisor analogue.

## Deterministic Boundary

`scripts/check-external-opponent-feedback` validates JSON schemas, enums,
round-relative paths, source allowlists, hashes, review-record shape,
placeholders, and stale refs. It must not infer whether criticism is justified,
missed, important, or promotable from raw prose. Those labels are authored only
by an explicitly authorized human or semantic agent and then reviewed.

Source refs for the external report stay under
`inputs/external_opponent_report/`. Comparison refs can point to case-local
notes, work artifacts, or outputs, but exact source files must be opened before
claims are made. RAG chunks, aggregate packets, current-evidence snapshots, and
chat summaries are discovery aids only, not evidence citations.

## Promotion Routing

Use the narrowest durable route:

- `case_only`: useful for defense prep or this student's record only.
- `current_student_followup`: worth discussing with the student after the
  report, when appropriate and permitted.
- `supervisor_profile`: a durable private preference about strictness,
  emphasis, or wording.
- `workflow_docs_or_skill`: a general rule for supervisor feedback or
  supervisor-report skills.
- `methodology_pipeline`: methodology, evaluation, contribution-boundary, or
  evidence-mode lesson owned by the methodology plan.
- `specialized_review_workflow`: route to code consistency, code quality,
  quantitative claims, literature/citation, figure/media, typography/formal,
  Theses.cz, or GitHub intake.
- `todo_or_follow_up_plan`: useful but outside the current slice.
- `discard`: unsupported, disputed, too case-specific, or already covered.

## Review Loop

The parent session owns orchestration and synthesis for this skill; no new
stable spawned role is required. Use existing specialist roles for referenced
evidence when fresh semantic review is needed, and use
`thesis_evidence_calibrator` for the final approval pass. A substitute
independent reviewer requires an explicit operator decision or typed limitation.
The reviewer must not be the same agent that generated the postmortem findings
or analysis.

A material edit to `outputs/external_opponent_feedback_analysis.md`,
`work/external_opponent_feedback_findings.json`, or
`work/supervisor_learning_candidates.json` after approval reopens the review.
Refresh the approval record instead of manually adjusting hashes.

## Agent Final Response Contract

When acting as a workflow agent, write full evidence content to the owned
case-local files and keep the chat final response compact. Do not paste full
Markdown artifacts that are already on disk.

Use the default handoff shape in `docs/agent-scheduling.md#subagent-handoffs`,
plus validation status, written paths, permission limitations, and any promotion
routes that need parent action.

## Model And Reasoning

Use the strongest available model with high reasoning effort for semantic
comparison against opponent reports, prior supervisor feedback, thesis/code
evidence, and promotion decisions. Cheaper models are acceptable only for
mechanical helper checks that are validator-backed and reviewed by the semantic
pass.
