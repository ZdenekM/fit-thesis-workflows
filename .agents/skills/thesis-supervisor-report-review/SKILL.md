---
name: thesis-supervisor-report-review
description: Independent review pass for a drafted formal BP/DP supervisor report, checking evidence, tone, FIT IS field coverage, grade/points consistency, private-comment boundary, and readiness for supervisor confirmation.
---

# Thesis Supervisor Report Review

Command routing: treat `scripts/<tool>` examples below as logical workflow
command names. On Windows, use the packaged
`dist\workflow-tools\bin\<tool>.cmd` or `.ps1` launcher from `README.md`; do
not run or click extensionless `scripts/<tool>` files.

Use this skill as the required independent review for a supervisor-report draft
before `outputs/vedouci_posudek_revidovany.md` is treated as reviewed.

## Inputs

Required active-round inputs:

```text
notes/supervisor-report-operator-input.md
work/supervisor_report_trace.json
work/vedouci_posudek_draft.md
```

Optional inputs:

```text
work/supervisor_report_feedback_history.json
```

Generated outputs:

```text
outputs/vedouci_posudek_revidovany.md
work/reviews/supervisor_report_review.json
```

Boundary: `work/report_calibration_basis.json` is the current V1 application
contract for opponent reports only (`calibration_scope: opponent_report`).
Supervisor-report review must not require or interpret it. Review the
supervisor report through `work/supervisor_report_trace.json`, the draft and
reviewed report artifacts, `work/supervisor_report_confirmation.json` when
present, and optional supervisor-report calibration artifacts.

## Process

Before reviewing or rewriting a report, confirm explicit agent authorization in
the current request. This workflow requires an independent agent review.

Review the draft as a formal supervisor report, not as general student feedback:
start from `work/supervisor_report_trace.json`,
`work/context/claim_review_basis.json` when present, the draft review basis, and
current standalone evidence. Open full thesis/code/source artifacts only for
missing anchors, contradictions, P0/P1 or grade-impacting claims, reviewer
challenges, or wording that is not supported by the trace.

1. Check that every FIT IS field is present and written for the right audience.
2. Check that student activity, independence, communication, consultation,
   preparedness, and finishing timing are grounded in supervisor input or are
   explicitly limited.
3. Check that prior feedback is used only when revision evidence supports a
   concrete responsiveness claim.
4. Check that grade, points, and the official overall assessment are
   proportionate to each other.
5. Check that assignment fulfillment, result quality, literature work,
   publication/open-source claims, and serious reservations are supported by
   current-case evidence.
6. If the draft uses Theses.cz similarity-report evidence, verify that it is
   backed by `outputs/theses_similarity_review.md`, that clean/no-concern or
   resolved reports remain silent, and that plagiarism/authorship wording is
   absent unless a reviewed unresolved concern supports it.
7. Check that `Komentar pro studenta` is clearly separated from the official
   printed report fields.
8. Remove internal workflow language, packet names, local paths, hashes, raw
   similarity-report URLs/source internals, approval state, and unsupported
   claims from report-facing prose.
9. Preserve the supervisor's style preferences from the effective profile when
   they do not conflict with evidence or fairness.

Run `scripts/check-supervisor-report <case-id> [round-id]` before and after
material edits. During repository development before that command lands, do not
mark the review approved; record the missing checker as an implementation
blocker.

## Review Loop

Write the reviewed report to `outputs/vedouci_posudek_revidovany.md`. After
review, write or update `work/reviews/supervisor_report_review.json` through
`scripts/write-review-approval --profile supervisor-report`. The approval must
bind the reviewed output and `work/vedouci_posudek_draft.md` by hash and record
reviewer role, checks, limitations, and timestamp.

Material edits after review reopen draft state. The supervisor still must
confirm grade, points, official text, and private student comment in
`work/supervisor_report_confirmation.json` before the report is ready for IS.
Post-review operator corrections must be recorded as
`work/review_deltas/*.json` with `scripts/record-review-delta` instead of
manual hash edits. Use profile `supervisor_report`, the appropriate delta type,
a previous reviewed snapshot, affected sections, and evidence refs; material
claim or evidence-challenge deltas reopen this independent review path before
closeout can pass.

Supervisor-report review packets must list both owned outputs,
`outputs/vedouci_posudek_revidovany.md` and
`work/reviews/supervisor_report_review.json`, plus validator commands
`scripts/check-supervisor-report --require-reviewed <case-id> [round-id]` and
`scripts/check-review-wave --workflow supervisor_report --wave final <case-id>
[round-id]`. If that contract is absent, ask the parent session to regenerate
packets before reviewing.

After writing the reviewed output and approval record, ask the parent session to
refresh provenance with `scripts/init-review-manifest --run-checks <case-id>
[round-id]`. The report is still not ready for IS until the human supervisor
confirms it with `scripts/confirm-supervisor-report` and
`scripts/review-round-closeout --profile supervisor_report` passes.

## Agent Final Response Contract

Write full review output to the owned round files and keep the chat final
response compact. Use the default handoff shape in
`docs/agent-scheduling.md#subagent-handoffs`, plus the reviewed-output path,
approval-record path, checks run, limitations, and validation status. Do not
paste full Markdown artifacts that are already on disk.

## Model And Reasoning

Use the strongest available model with high reasoning effort for evidence,
grade/points consistency, tone, fairness, and report rewrites. Mechanical helper
summaries may use cheaper models only when validator-backed and consumed by a
high-reasoning semantic pass.

## Output

Write `outputs/vedouci_posudek_revidovany.md`:

```markdown
# Posudek vedoucího

## Informace k zadání

## Práce s literaturou

## Aktivita během řešení, konzultace, komunikace

## Aktivita při dokončování

## Publikační činnost, ocenění

## Celkové hodnocení

Známka:
Body:

## Komentář pro studenta
```

Verdict categories for review notes:

- `reviewed_no_blockers`
- `needs_minor_supervisor_calibration`
- `blocked_before_supervisor_confirmation`
