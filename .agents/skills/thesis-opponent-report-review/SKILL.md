---
name: thesis-opponent-report-review
description: Review a drafted opponent report for fairness, evidence, tone, IS-item coverage, point/comment consistency, and defensibility before submission.
---

# Thesis Opponent Report Review

Use this skill after the user has drafted their own opponent report.

## Inputs

Expected files in the active round:

```text
outputs/oponent_podklady.md
outputs/oponent_podklady_revidovane.md
notes/opponent-report-review-intake.md
work/muj_posudek_draft.md
```

If the draft is elsewhere, use the path provided by the user.

## Process

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
