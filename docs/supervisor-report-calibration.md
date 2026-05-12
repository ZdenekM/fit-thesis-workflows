# Supervisor Report Calibration

Historical supervisor reports are private style calibration evidence for formal
supervisor reports. They are never evidence about the current student.

Use the workflow only after explicit agent authorization. Keep historical
reports, extracted text, case analyses, generated calibration profiles, and
reviews under ignored `cases/`.

## Artifacts

Private calibration case rounds use supervisor-specific names:

- `work/calibration/supervisor_report/historical_case_analyses/<id>.json`
- `outputs/supervisor_report_calibration_profile.md`
- `work/calibration/supervisor_report/profile.json`
- `work/calibration/supervisor_report/checklist.json`
- `work/calibration/supervisor_report/profile_history.jsonl`
- `work/calibration/supervisor_report/profile_change_log.md`
- `work/calibration/supervisor_report/profile_review.md`

Current-case use is optional and recorded as either:

- `work/supervisor_report_calibration_use.json`
- `work/supervisor_report_calibration_advisory.json`

## Rules

- Use at least two historical supervisor report analyses before synthesizing a
  profile.
- Bind profile Markdown, profile manifest, checklist, history, review, and
  source analyses by path and SHA-256.
- Run an independent anti-overfit review and register the Markdown profile in
  `work/review_manifest.json`.
- Use calibration only for tone, length, wording, and strictness calibration.
  It must not replace supervisor input, current thesis/code evidence, or the
  final grade/points judgment.
- If applicability is weak, stale, missing, or declined by the operator, record
  an advisory instead of using the profile.

## Check

Run:

```bash
scripts/check-supervisor-report-calibration-profile <calibration-case-id> [round-id]
```

On Windows operator checkouts, run the packaged
`dist\workflow-tools\bin\check-supervisor-report-calibration-profile.cmd` or
`.ps1` launcher.
