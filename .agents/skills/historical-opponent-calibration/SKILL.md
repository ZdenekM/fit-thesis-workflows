---
name: historical-opponent-calibration
description: Private DEEP workflow for analyzing historical opponent reports and synthesizing a Markdown-first reviewer calibration profile.
---

# Historical Opponent Calibration

Command routing: treat `scripts/<tool>` examples below as logical workflow
command names. On Windows, use the packaged
`dist\workflow-tools\bin\<tool>.cmd` or `.ps1` launcher from `README.md`; do
not run or click extensionless `scripts/<tool>` files.

Use this skill only after the user explicitly authorizes agents in the current
request. Historical reports, theses, code, notes, generated case analyses,
profiles, checklists, and reviews stay under ignored `cases/`.

## Workflow

1. Resolve the private calibration case and round.
2. Confirm explicit current-request authorization. If missing, stop before
   reading historical materials or writing semantic artifacts.
3. For each historical case under `inputs/historical_cases/<id>/`, an authorized
   agent reads the private materials and writes
   `work/calibration/historical_case_analyses/<id>.json`.
4. Run `scripts/check-opponent-calibration-case <calibration-case-id> [round-id]`.
5. After at least two historical analyses pass, synthesize the authoritative
   narrative profile in `outputs/reviewer_calibration_profile.md`.
6. Write only machine-checkable metadata to
   `work/calibration/reviewer_calibration_profile.json`: profile path/hash,
   version, previous hash, source analyses, applicability, confidence by
   dimension, limitations, and do-not-use boundaries.
7. Write reusable evidence-class review prompts to
   `work/calibration/reviewer_checklist.json`.
8. Append the version entry to
   `work/calibration/reviewer_calibration_profile_history.jsonl`.
9. Record the human-readable version summary in
   `work/calibration/reviewer_profile_change_log.md`.
10. Run an independent anti-overfit/profile reviewer and record the review in
   `work/calibration/profile_review.md`.
11. Register `outputs/reviewer_calibration_profile.md` in
    `work/review_manifest.json` with reviewed hash, generator, reviewer,
    source analysis refs, and limitations.
12. Run `scripts/check-opponent-calibration-profile <calibration-case-id> [round-id]`.

## Current Case Use

After reviewed opponent materials and an accepted `work/opponent_report_trace.json`
exist, use the private profile only through the current-case contract:

1. Record selected-profile use in `work/opponent_calibration_use.json`, or record
   non-use in `work/opponent_calibration_advisory.json`.
2. Write `outputs/reference_report_comparison.md` as operator-only internal
   evidence comparing the current materials and trace with the selected profile.
   Treat historical reports as calibration context, never as evidence about the
   current student.
3. Write `outputs/opponent_reading_packet.md` after the comparison. Use a stable
   order: supported findings, uncertainties, evaluation axes, point/grade
   tension, profile differences, defense questions, and manual checks.
4. Run an independent anti-overfit review before either Markdown output can
   influence trace edits or a draft report.
5. Register both outputs in `work/review_manifest.json` with generator,
   independent reviewer, reviewed hash, current source hashes, evidence refs, and
   limitations. Then run `scripts/check-review-manifest --require-complete
   <case-id> [round-id]`.
6. After the operator reads the packet and draft, store the free-form operator
   notes in `notes/opponent-report-operator-feedback.md`.
7. An explicitly authorized agent, or a human reviewer, normalizes those notes
   into `work/opponent_report_revision_request.json`. Use only typed feedback
   categories: `evidence_request`, `grading_calibration`, `tone_style`,
   `missing_check`, `factual_correction`, `wording_preference`,
   `defense_question`, or `scope_limitation`.
8. Bind the revision request by path and SHA-256 to the operator feedback,
   reviewed materials, pre-revision trace snapshot, pre-revision draft snapshot,
   calibration-use or advisory artifact, reference comparison, and reading
   packet. Store the snapshots under `work/opponent_report_revision_sources/`.
   Do not revise the trace from unstructured notes directly.
9. When applying the revision request, an authorized agent or human reviewer
   updates `work/opponent_report_trace.json` and records `calibration_context`
   with path/SHA-256 bindings to the selected calibration-use or advisory
   artifact, `outputs/reference_report_comparison.md`,
   `outputs/opponent_reading_packet.md`, and
   `work/opponent_report_revision_request.json`.
10. Regenerate `work/oponent_posudek_draft.md` with
    `scripts/draft-opponent-report --force <case-id> [round-id]`, then run
    `scripts/check-opponent-report --mode canonical <case-id> [round-id]` and
    `scripts/export-opponent-report <case-id> [round-id]` after human
    calibration.
11. Refresh `work/review_manifest.json`, run required coverage/manifest checks,
    and run an independent opponent-report review before treating the clean
    proposal as sendable.
12. After the report is human-finalized and independently reviewed, the operator
    may mark it for a future calibration refresh by writing
    `work/opponent_calibration_refresh_eligibility.json`. The marker binds the
    finalized materials, accepted trace, finalized draft, opponent-report review,
    finalization manifest snapshot at
    `work/opponent_calibration_refresh_sources/review_manifest.json`, and
    operator approval by SHA-256. It must say that profile update has not started
    and that no automatic profile update or automatic copy was performed. Capture
    the manifest snapshot before the eligibility marker itself is collected into
    the active manifest.

## Refresh

To add a new historical case or a newly finalized opponent report, repeat the
historical case analysis step for the new case, then synthesize a new profile
version. A refresh must keep all prior `source_case_refs`, set
`profile_previous_sha256` to the previous versioned Markdown snapshot hash, add
`work/calibration/profile_versions/v<version>.md`, append a new history line
with `previous_history_entry_sha256` instead of rewriting the JSONL file, update
`reviewer_profile_change_log.md`, and record structured operator approval
before the refreshed profile becomes the default calibration profile.

The refresh-eligibility marker is only a private queue entry. It never replaces
the later historical-case analysis, independent profile review, append-only
history entry, or explicit default-profile approval.

## Boundaries

- The profile is calibration context, not evidence about a new student's work.
- Historical calibration never replaces the normal `Reviewer profile` readiness
  gate in `case.md`.
- Deterministic helpers must not infer reviewer style from raw historical report
  text. They validate schemas, paths, hashes, and review state only.
- Avoid long verbatim excerpts from historical reports.
- Current-case use is recorded in `work/opponent_calibration_use.json` only
  after reviewed opponent materials and an accepted report trace exist; absence
  or non-use is recorded as non-blocking `work/opponent_calibration_advisory.json`.
- Historical calibration must never satisfy the normal `Reviewer profile` gate.
- Before drafting an opponent report, refresh or remove any stale current-case
  calibration use/advisory artifact; the draft helper treats a recorded but
  invalid calibration context as a blocking provenance error.
- `outputs/reference_report_comparison.md` and
  `outputs/opponent_reading_packet.md` are internal evidence for the operator.
  They need independent review metadata and current reviewed hashes in
  `work/review_manifest.json` before they influence a report trace or draft.
- `work/opponent_report_revision_request.json` is the structured handoff from
  operator notes to later trace revision. Deterministic code may validate its
  schema, categories, paths, hashes, and source refs, but not infer meaning from
  `notes/opponent-report-operator-feedback.md`.
- `work/opponent_report_trace.json` may include `calibration_context` after a
  calibrated or operator-feedback-driven revision. That context is a source
  binding record: it validates hashes of the exact calibration and revision
  artifacts used, without reinterpreting their free text or recursively
  requiring those input artifacts to bind the newly revised trace.
- `work/opponent_calibration_refresh_eligibility.json` may mark a finalized case
  for later profile refresh, but it must not copy private data or update the
  reviewer profile by itself.
