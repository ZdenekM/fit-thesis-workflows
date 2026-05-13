---
name: thesis-supervisor-report
description: DEEP workflow for drafting the formal BP/DP supervisor report for FIT IS from supervisor input, current thesis/code evidence, optional prior-feedback evidence, and reviewer profile style.
---

# Thesis Supervisor Report

Command routing: treat `scripts/<tool>` examples below as logical workflow
command names. On Windows, use the packaged
`dist\workflow-tools\bin\<tool>.cmd` or `.ps1` launcher from `README.md`; do
not run or click extensionless `scripts/<tool>` files.

Use this skill when the supervisor wants a reviewed draft of the formal
supervisor report (`posudek vedouciho`) for FIT IS. This is not student-facing
iteration feedback.

## Inputs

Required active-round inputs:

```text
notes/assignment.md
notes/supervisor-report-operator-input.md
```

Optional inputs:

```text
notes/previous-feedback-index.md
work/supervisor_report_feedback_history.json
```

Generated outputs:

```text
work/supervisor_report_trace.json
work/vedouci_posudek_draft.md
outputs/vedouci_posudek_revidovany.md
```

`notes/supervisor-report-operator-input.md` is authoritative for student
activity, independence, consultation, communication, preparedness, completion
timing, grade/points calibration, and the private student comment. If the
supervisor does not know a dimension, the intake must say that explicitly.

## Process

1. Resolve the active case and round.
2. Confirm explicit agent authorization in the current request before drafting
   or revising a report. This workflow requires role-split agents and an
   independent review pass.
3. Run `scripts/check-supervisor-report-ready <case-id> [round-id]`. If it
   fails, stop before generating a trace, draft, or reviewed output and ask for
   the missing assignment, deadline/profile context, or supervisor-report
   intake fields.
4. Read the effective reviewer profile. Profile style guides wording only; it
   cannot override supervisor input, current-case evidence, privacy, readiness
   gates, or unchecked-work limitations.
5. Inventory current thesis/code evidence, but start from
   `work/common_briefing.json`, current-evidence snapshots, materiality
   decisions, reusable evidence artifacts, and `work/context/claim_review_basis.json`
   when present. Open full thesis, code, source zips, README, result, or note
   artifacts only for the report field being drafted when a claim is missing an
   anchor, contradicted, P0/P1 or grade-impacting, challenged, changed since the
   current evidence snapshot, or not resolvable from capsules. Use the submitted
   PDF as the authoritative rendered thesis artifact. Use source zips and code
   for search, diffs, reproducibility, and evidence.
6. If previous supervisor feedback exists, use it only as optional secondary
   evidence. It may support responsiveness when later artifacts show concrete
   response to prior feedback. If feedback is absent, stale, incomparable, or
   inconclusive, record that limitation and rely on supervisor input.
7. When code is present, use both `thesis-code-consistency` and
   `thesis-code-quality-review`, or record a typed limitation explaining why one
   could not be performed.
8. Before spawning role agents, reuse the shared current-evidence,
   materiality, packet, reuse-index, claim-basis, and wave-gate pattern for the
   `supervisor_report` workflow when available. Consume compact packet handoffs
   and `## Synthesis Handoff` sections first; open full artifacts only for
   material verification, contradiction checks, missing anchors, or reviewer
   challenges. This routing does not waive code roles, independent review, report
   confirmation, or manifest gates.
9. When metrics, user studies, experiments, figures, literature, GitHub PRs,
   imported Theses.cz similarity reports, or final typography are material to
   the report, use the same specialist workflows as supervisor feedback and
   opponent materials. Clean or resolved similarity-report findings should stay
   silent in formal prose unless the supervisor explicitly needs an
   institutional note.
10. Write or update `work/supervisor_report_trace.json` with field-level
   evidence refs, supervisor-input refs, optional feedback-history status,
   grade/points state, uncertainty, manual checks, and limitations.
11. Generate or update `work/vedouci_posudek_draft.md`. Keep the official report
    fields separate from `Komentar pro studenta`, which is visible only to the
    student in IS and is not part of the printed official report.
12. Run an independent reviewer using `thesis-supervisor-report-review`. The
    reviewed draft goes to `outputs/vedouci_posudek_revidovany.md`.
13. Treat the reviewed Markdown as a draft for the human supervisor until
    `work/supervisor_report_confirmation.json` confirms grade, points, official
    text, and private student comment for IS entry.

## FIT IS Fields

Cover these sections:

- `Informace k zadani`
- `Prace s literaturou`
- `Aktivita behem reseni, konzultace, komunikace`
- `Aktivita pri dokoncovani`
- `Publikacni cinnost, oceneni`
- `Celkove hodnoceni`: grade `A-F`, points `0-100`, and official free text
- `Komentar pro studenta`: non-printed private student comment

## Evidence Rules

- Do not infer student activity, independence, preparedness, communication, or
  deadline behavior from indirect artifacts when supervisor input is missing.
- Do not treat absence of prior feedback as negative evidence.
- Do not copy student-facing feedback into the report without adapting it to the
  official FIT IS fields and current grade/points calibration.
- Do not name publications, awards, open-source release, external impact, or
  assignment non-fulfillment without current evidence or supervisor input.
- In routine cases with no publication or award evidence, do not turn that
  absence into report prose. If the required report field must be non-empty, use
  a neutral one-line comment rather than explicitly saying that publications or
  awards are absent.
- Do not use plagiarism/authorship wording from a similarity report unless
  `outputs/theses_similarity_review.md` records a reviewed unresolved concern
  that supports that narrow statement.
- Keep internal paths, hashes, packet names, review state, and local workspace
  details out of official prose.

## Style

Use the effective reviewer profile's `Supervisor Report Style` section when it
exists. Default shape is compact Czech supervisor voice: one short paragraph per
field, clear assignment/result/process calibration, concise literature and
only evidence-bearing publication/open-source remarks, and a proportionate
overall assessment.

## Agent Final Response Contract

When acting as a workflow agent, write the full trace, draft, or reviewed report
to the owned round files. Keep the chat final response compact:

- files written or changed;
- top 3-5 findings, verdicts, or risks;
- commands/checks run;
- explicit limitations;
- whether expected output validation passed.

Do not paste full Markdown artifacts that are already on disk.

## Model And Reasoning

Use the strongest available model with high reasoning effort for semantic
reading, grading calibration, synthesis, and reviewed wording. Mechanical helper
summaries may use cheaper models only when validator-backed and consumed by a
high-reasoning semantic pass.

## Output

Draft: `work/vedouci_posudek_draft.md`

Reviewed output: `outputs/vedouci_posudek_revidovany.md`
