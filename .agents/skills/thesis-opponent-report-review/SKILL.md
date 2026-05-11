---
name: thesis-opponent-report-review
description: Review a drafted opponent report for fairness, evidence, tone, IS-item coverage, point/comment consistency, and defensibility before submission.
---

# Thesis Opponent Report Review

Use this skill after the user has drafted their own opponent report, or after
`scripts/draft-opponent-report` has produced an internal bridge draft from
reviewed opponent materials, `work/opponent_report_trace.json`, and a human has
calibrated it.

## Inputs

Expected files in the active round:

```text
outputs/oponent_podklady.md
outputs/oponent_podklady_revidovane.md
notes/opponent-report-review-intake.md
work/oponent_posudek_draft.md
work/opponent_report_trace.json
work/muj_posudek_draft.md
```

If `work/oponent_posudek_draft.md` exists, treat it as the generated report draft
to review unless the user provides a newer human draft elsewhere. A generated
draft is not sendable by itself: it must contain concrete points and grade, must
match the current `work/opponent_report_trace.json` and
`outputs/oponent_podklady_revidovane.md` hashes, and must pass
`scripts/check-opponent-report <case-id> [round-id]`. If the draft is elsewhere,
`scripts/check-opponent-report --path <round-relative-path> <case-id> [round-id]`
is an ad hoc draft-shape check only; opponent closeout and manifest helper
provenance track the canonical generated draft path `work/oponent_posudek_draft.md`.

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
8. Whether selected rewrites would improve fairness, precision, or tone without rewriting the whole report.

Do not soften the report automatically. The goal is accuracy, fairness, evidence, and consistency.

When reviewing `work/oponent_posudek_draft.md`, first run
`scripts/check-opponent-report <case-id> [round-id]`. Treat failures as draft
issues to fix or explicitly return to the user before IS submission. Do not
review an uncalibrated helper draft as if it were a final human report.

When evidence artifacts include `## Synthesis Handoff`, use that handoff as the
first entrypoint for report risk, suggested rewrite, confidence/limitation, and
point/grade consistency impact. Open the full evidence only for material
verification, contradiction checks, or contested report wording.

## Review Loop

This skill is the independent review pass for a human-drafted opponent report. If agent authorization is missing, ask before writing final sendable review feedback or rewriting the report. If an agent later rewrites the report text itself, run this review again with a different explicitly authorized reviewer agent before treating the report as sendable.

After writing or revising `outputs/feedback_k_posudku.md`, run `scripts/init-review-manifest --run-checks <case-id> [round-id]`, record the reviewer role and reviewed hash in `work/review_manifest.json`, then run `scripts/check-review-manifest --require-complete <case-id> [round-id]`.

## Agent Final Response Contract

When acting as a workflow agent, write full review feedback or report rewrites
to the owned round files and keep the chat final response compact. Do not paste
full Markdown artifacts that are already on disk.

Return only:

- files written or changed;
- top 3-5 findings, verdicts, or risks;
- commands/checks run;
- explicit limitations;
- whether expected output validation passed.

The main session must verify file claims with expected-output checks before
relying on them.

## Model And Reasoning

Use the strongest available model with high reasoning effort for this semantic
review workflow. In the current Codex setup, use `gpt-5.5` with `xhigh`
reasoning when that choice is exposed. Packet prompts generated for this skill
must carry the same requirement. Do not downshift to Spark or another low-cost
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

## 8. Co v posudku chybi

## 9. Otazky k obhajobe

## 10. Prioritni upravy pred odevzdanim

## 11. Cilene navrhy preformulovani

## 12. Finalni checklist pred vlozenim do IS
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

Verdict categories:

- `pouzitelny po drobnych upravach`
- `pouzitelny po vyznamnejsich upravach`
- `pred odevzdanim nutne prepracovat`
