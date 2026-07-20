---
name: thesis-opponent-report-review
description: Review a drafted opponent report for fairness, evidence, tone, IS-item coverage, point/comment consistency, and defensibility before submission.
---

# Thesis Opponent Report Review

Command routing: treat `scripts/<tool>` examples below as logical workflow
command names. On Windows, use the packaged
`dist\workflow-tools\bin\<tool>.cmd` or `.ps1` launcher from `README.md`; do
not run or click extensionless `scripts/<tool>` files.

Use this skill after the user has drafted their own opponent report, or after
`scripts/draft-opponent-report` has produced an internal bridge draft from
reviewed opponent materials, `work/opponent_report_trace.json`, and a human has
calibrated it, then `scripts/export-opponent-report` has produced the clean
IS-entry proposal.

## Inputs

Expected files in the active round:

```text
outputs/oponent_podklady.md
outputs/oponent_podklady_revidovane.md
outputs/oponent_posudek_navrh.md
notes/opponent-report-review-intake.md
work/oponent_posudek_draft.md
work/opponent_report_trace.json
work/report_calibration_basis.json
work/theses_checker_summary.json
```

If `outputs/oponent_posudek_navrh.md` exists, treat it as the primary report
text to review. If the user supplies a human report outside the canonical export
route, first copy or transform it into the canonical clean proposal path and run
the clean report check; do not keep a parallel report-basis path for approval.
When revising an exported proposal, write findings or a revision request first;
a parent agent or human must update the trace/canonical draft, rerun canonical
validation, export a new clean proposal, rerun clean validation, and then reopen
independent report review. `work/oponent_posudek_draft.md`
is the trace-bound canonical source: it must contain concrete points and grade, must match the current
`work/opponent_report_trace.json` and `outputs/oponent_podklady_revidovane.md`
hashes, and must pass `scripts/check-opponent-report --mode canonical <case-id>
[round-id]`. The clean proposal must be produced by
`scripts/export-opponent-report <case-id> [round-id]` and pass
`scripts/check-opponent-report --mode clean <case-id> [round-id]`. If the draft
is elsewhere, `scripts/check-opponent-report --mode canonical --path
<round-relative-path> <case-id> [round-id]` is an ad hoc draft-shape check only;
opponent closeout and manifest helper provenance track the canonical generated
draft path plus the clean proposal path.

## Process

Before reviewing or rewriting a sendable report, confirm that the user explicitly authorized agent use in the current request. This workflow requires an independent agent review. If explicit authorization is missing, stop and ask the user to authorize agents.

Review the report as a report, not as the student's thesis. Check:

1. Whether every important criticism is supported by evidence.
2. Whether factual, interpretive, and uncertain claims are phrased correctly.
3. Whether tone is professional, non-personal, and not unnecessarily harsh.
4. Whether the report distinguishes:
   - assignment difficulty versus solution quality,
   - assignment fulfillment versus presentation quality,
   - formal quality versus technical content,
   - implementation output versus its description,
   - literature work versus general writing quality,
   - unverifiability versus non-functionality.
5. Whether comments match points and the proposed grade.
6. Whether strong parts of the work are included where supported.
7. Whether defense questions are fair, answerable, and focused.
8. Whether the private student comment is present, useful, and clearly separated
   from the public report text. It should explain the grade, suggest defense
   preparation, and include practical future-work advice without adding new
   unsupported criticism or internal workflow details.
9. Whether the `## IS formulář (výběry a body)` section is present and matches
   the prose: assignment difficulty selection, assignment-fulfillment selection,
   technical-report-scope selection, and point values for presentation, formal
   quality, literature work, and implementation output.
10. When `work/report_calibration_basis.json` is present, whether the report
   applies the structured reviewer-profile and operator-calibration decisions:
   name which applied preferences affected the public report, check IS
   selections, grade/points, report length, defense-question count, and private
   comment against `expected_report_controls`, and state whether any profile
   preferences were intentionally not applied with current-case evidence or
   operator instruction.
11. Whether `work/opponent_report_trace.json` carries the report-quality
    controls needed for the clean proposal: assignment coverage, rubric
    alignment, checked scope, claim ledger, evidence-source matrix,
    Theses Checker or typed technical-report-scope basis, strength/grade
    tension, defense-question strategy, uncertainty, and materiality-bound
    contribution, scaling, citation, third-party/authorship, media, deployment,
    technical-difficulty, or result-usability refs when relevant.
12. Whether selected rewrites would improve fairness, precision, or tone without rewriting the whole report.
13. Whether report-facing prose leaks internal packet paths, manifest hashes,
    private URLs, raw PR metadata, review-thread details, local workspace paths,
    or generated-draft state. Remove those classes of internal evidence from the
    report text and convert them into evidence-backed conclusions, limitations,
    or manual checks.
14. Whether report-facing prose follows the opponent-facing boundary rather than
    carrying helper-draft habits: avoid evidence-acquisition status, automatic
    checker names, late-update wording, production-readiness as a default failure
    boundary, low-level code-review mechanics, and boilerplate repetition of form
    field names or thesis level when a concise substantive assessment is enough.
15. Whether defense questions are the best use of the defense slot: prefer
    conceptual, interpretive, or tradeoff-oriented questions tied to material
    uncertainties; use low-level command/configuration questions or "why was this
    not done" questions only when they are necessary to resolve a strong
    unresolved evidence problem.

Apply `docs/opponent-review-workflow.md#report-quality-controls` at the report
boundary. In this review skill, the role-specific obligation is to check that
the clean IS proposal is compact, fair, evidence-backed, aligned with points and
grade, free of internal audit detail, and consistent with the private student
comment and defense questions.

Do not soften the report automatically. The goal is accuracy, fairness, evidence, and consistency.

Before reviewing the report, first run `scripts/check-opponent-report --mode
canonical <case-id> [round-id]`, then `scripts/export-opponent-report <case-id>
[round-id]`, then `scripts/check-opponent-report --mode clean <case-id>
[round-id]`. If `work/report_calibration_basis.json` is present or the trace
binds it, also run `scripts/check-report-calibration <case-id> [round-id]`.
When the trace records a typed no-applicable-calibration limitation instead of a
basis, `scripts/check-report-calibration` is still the gate that validates that
limitation. Do not treat a profile-context-only state as calibrated.
Treat failures as draft/export/calibration issues to fix or explicitly return to
the user before IS submission. Do not review an uncalibrated helper draft as if
it were a final human report.

Separate prose-review findings from calibration-basis drift. A wording, tone, or
evidence-support problem belongs in the prose sections. A stale/missing
calibration basis, mismatched expected IS control, inconsistent points/grade,
wrong defense-question count, or unjustified non-application of a structured
preference must be reported as calibration-basis drift and should reopen the
calibration/report route rather than be treated as a local text edit.

Before reopening full evidence artifacts, start from `outputs/oponent_posudek_navrh.md`,
then the report-quality sections in `work/opponent_report_trace.json`, then any
available `## Synthesis Handoff` sections. Use the handoff as the first
entrypoint for report risk, suggested rewrite, confidence/limitation, and
point/grade consistency impact. Open the full evidence only for material
verification, contradiction checks, or contested report wording.

## Review Loop

This skill is the independent review pass for a human-drafted or exported opponent report. If agent authorization is missing, ask before writing final sendable review feedback. Reviewer agents should not directly edit `outputs/oponent_posudek_navrh.md` unless the parent explicitly assigns a rewrite artifact; the normal correction path is feedback or revision-request evidence, followed by parent/human updates to the canonical draft, re-export, and a fresh independent review. If an agent does rewrite report text itself, run this review again with a different explicitly authorized reviewer agent before treating the report as sendable.

After writing or revising `outputs/feedback_k_posudku.md`, use `scripts/write-review-approval --profile opponent-report-review` to write or update `work/reviews/opponent_report_review.json` with the workflow profile, reviewer role/agent, `verdict: approved`, `blocking_findings_count: 0`, the reviewed artifact path/hash, the review-basis path/hash, checks observed, limitations, and timestamp. The review basis must be the exact round-relative report text reviewed: normally `outputs/oponent_posudek_navrh.md`, or `work/oponent_posudek_draft.md` only before the clean proposal exists. Include `check-opponent-report:canonical`, `check-opponent-report:clean`, and `check-review-wave.opponent-report.draft` in observed checks when the clean proposal comes from the canonical draft; never record the ambiguous generic `check-opponent-report` ID. Include `check-report-calibration` as well when the reviewed basis is a report bound to `work/report_calibration_basis.json` or when the trace records a typed no-applicable-calibration limitation that `scripts/check-report-calibration` validates. Then run `scripts/init-review-manifest --run-checks <case-id> [round-id]`, record the reviewer role and reviewed hash in `work/review_manifest.json`, and run `scripts/check-review-manifest --require-complete <case-id> [round-id]`. If an operator changes or challenges the reviewed report feedback afterward, record a `work/review_deltas/*.json` entry with `scripts/record-review-delta --profile opponent_report_review`; material or evidence-challenge deltas reopen the independent review path before closeout can pass.

After actual IS submission, record the public PDF export with `scripts/record-submitted-opponent-report --pdf <pdf> --public-text-file <public-transcript.md> --recorded-by <name> <case-id> [round-id]`. The public transcript should preserve the clean-report Markdown sections; if omitted, the helper only attempts raw `pdftotext -layout` and must not treat an unparsed IS PDF layout as archive-ready. The command may write a non-archive-ready capture when public text differs from the reviewed clean proposal. If the difference is a bounded non-material IS-entry edit, record every changed public section with `scripts/record-submitted-report-delta`; changes to selectbox values, category points, overall points/grade, or defense questions reopen this review path instead of being accepted as archive drift. The private student comment remains bound to the reviewed clean proposal; do not infer it from the public PDF export.

Use `scripts/check-review-wave --workflow opponent_report --wave draft` for the
generated report draft, and `scripts/check-review-wave --workflow
opponent_report_review --wave final` after writing `outputs/feedback_k_posudku.md`.
If a wave, manifest, or approval check contradicts the agent's final message,
trust the checker and repair the draft, review output, or approval record before
treating the report review as usable.

## Agent Final Response Contract

When acting as a workflow agent, write full review feedback to the owned round
files and keep the chat final response compact. Do not paste full Markdown
artifacts that are already on disk. Do not invent a side path for report
rewrites; use the canonical/export route above unless the parent explicitly
assigns a bounded rewrite artifact.

Use the default handoff shape in `docs/agent-scheduling.md#subagent-handoffs`,
plus any role-specific validation status, owned output paths, and limitations
that affect parent verification.

## Model And Reasoning

Use the strongest available model with high reasoning effort for this semantic
review workflow. Use the strongest available tier of whichever provider runs this role, at `xhigh` effort (Codex adapter: `gpt-5.5`; Claude adapter where available: `opus`); see `docs/agent-scheduling.md`. Packet prompts generated for this skill
must carry the same requirement. Do not downshift to a low-cost model (Codex Spark or a small Claude tier) or another low-cost
model for the first or only pass over report drafts, reviewed materials,
opponent trace state, point/grade consistency, tone, fairness, or report
rewrites. Mechanical helper summaries may use cheaper models only when
validator-backed and consumed by a high-reasoning semantic pass.

## Output

Write `outputs/feedback_k_posudku.md`:

```markdown
# Zpetna vazba k navrhu oponentskeho posudku

## 1. Verdikt pouzitelnosti

## 2. Celkovy dojem

## 3. Nejvetsi rizika posudku

| Zavaznost | Misto v posudku | Riziko | Proc na tom zalezi | Doporuceni |
|---|---|---|---|---|

## 4. Podlozenost kritickych tvrzeni

| Tvrzeni v posudku | Stav podlozenosti | Riziko | Navrh upravy |
|---|---|---|---|

## 5. Primerenost tonu

| Puvodni formulace | Problem | Vecnejsi formulace |
|---|---|---|

## 6. Uplnost podle polozek IS

| Polozka IS | Stav pokryti | Co doplnit nebo upravit | Soulad s body |
|---|---|---|---|

## 7. Konzistence bodu, znamky a slovniho hodnoceni

## 8. Kontrola kalibracniho zakladu

Rozdelte sem tri otazky: ktere aplikovane preference ovlivnily verejny
posudek; zda vybery IS, znamka/body, delka posudku, otazky a neverejny komentar
odpovidaji `work/report_calibration_basis.json`; a ktere preference nebyly
aplikovany vcetne dolozeneho duvodu.

## 9. Co v posudku chybi

## 10. Otazky k obhajobe

## 11. Prioritni upravy pred odevzdanim

## 12. Cilene navrhy preformulovani

## 13. Finalni checklist pred vlozenim do IS
```

IS items to check:

- Narocnost zadani
- Rozsah splneni pozadavku zadani
- Rozsah technicke zpravy
- Prezentacni uroven technicke zpravy
- Formalni uprava technicke zpravy
- Prace s literaturou
- Realizacni vystup
- Vyuzitelnost vysledku
- Celkove hodnoceni
- Otazky k obhajobe
- IS formular vybery a body
- Neverejny komentar pro studenta

Verdict categories:

- `pouzitelny po drobnych upravach`
- `pouzitelny po vyznamnejsich upravach`
- `pred odevzdanim nutne prepracovat`
