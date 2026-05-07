---
name: historical-opponent-calibration
description: Private DEEP workflow for analyzing historical opponent reports and synthesizing a Markdown-first reviewer calibration profile.
---

# Historical Opponent Calibration

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

## Refresh

To add a new historical case or a newly finalized opponent report, repeat the
historical case analysis step for the new case, then synthesize a new profile
version. A refresh must keep all prior `source_case_refs`, set
`profile_previous_sha256` to the previous versioned Markdown snapshot hash, add
`work/calibration/profile_versions/v<version>.md`, append a new history line
with `previous_history_entry_sha256` instead of rewriting the JSONL file, update
`reviewer_profile_change_log.md`, and record structured operator approval
before the refreshed profile becomes the default calibration profile.

## Boundaries

- The profile is calibration context, not evidence about a new student's work.
- Historical calibration never replaces the normal `Reviewer profile` readiness
  gate in `case.md`.
- Deterministic helpers must not infer reviewer style from raw historical report
  text. They validate schemas, paths, hashes, and review state only.
- Avoid long verbatim excerpts from historical reports.
