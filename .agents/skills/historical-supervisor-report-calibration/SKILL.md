---
name: historical-supervisor-report-calibration
description: Private DEEP workflow for analyzing historical supervisor reports and synthesizing a Markdown-first supervisor-report calibration profile.
---

# Historical Supervisor Report Calibration

Command routing: treat `scripts/<tool>` examples below as logical workflow
command names. On Windows, use packaged
`dist\workflow-tools\bin\<tool>.cmd` or `.ps1` launchers; do not run or click extensionless `scripts/<tool>` files.

Use this skill only after the user explicitly authorizes agents in the current
request. Historical reports and generated calibration artifacts stay under
ignored `cases/`.

## Workflow

1. Resolve the private calibration case and round.
2. For each historical case under `inputs/historical_cases/<id>/`, an
   authorized agent writes
   `work/calibration/supervisor_report/historical_case_analyses/<id>.json`.
3. After at least two analyses pass, synthesize
   `outputs/supervisor_report_calibration_profile.md`.
4. Write machine-checkable metadata to
   `work/calibration/supervisor_report/profile.json`.
5. Write reusable checks to
   `work/calibration/supervisor_report/checklist.json`.
6. Append the version entry to
   `work/calibration/supervisor_report/profile_history.jsonl`.
7. Record changes in
   `work/calibration/supervisor_report/profile_change_log.md`.
8. Run an independent anti-overfit/profile review and record it in
   `work/calibration/supervisor_report/profile_review.md`.
9. Register `outputs/supervisor_report_calibration_profile.md` in
   `work/review_manifest.json` with reviewed hash, source analysis refs,
   limitations, generator, and reviewer.
10. Run
    `scripts/check-supervisor-report-calibration-profile <case-id> [round-id]`.

## Current Case Use

Record selected profile use in `work/supervisor_report_calibration_use.json`, or
record non-use in `work/supervisor_report_calibration_advisory.json`.

The profile may calibrate tone, length, wording, and strictness. It must never
replace current supervisor input, current thesis/code evidence, or the
supervisor's final grade/points decision.
