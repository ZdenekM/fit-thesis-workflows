---
name: thesis-opponent-materials
description: DEEP workflow for internal opponent materials for a BP/DP report, with evidence labels, risk calibration, thesis/code consistency review, and code-quality/design review.
---

# Thesis Opponent Materials

Use this skill to prepare internal materials for an opponent report. The output is not the final report to submit.

## Inputs

Use the active round unless the user specifies another:

```text
cases/<case-id>/rounds/<round-id>/
  notes/assignment.md
  notes/opponent-intake.md
  notes/round-notes.md
  inputs/
  extracted/
  work/
  outputs/
```

## Process

1. Resolve the active case and round.
2. Run `scripts/check-round-ready <case-id> [round-id]`. If it fails, stop before generating materials and ask the user to add the formal assignment, private assignment notes, or valid reviewer profile.
3. Read the effective profile files from the readiness output, or rerun `scripts/check-reviewer-profile <case-id>` if the file list is no longer visible. Profiles apply only to preference conflicts. They never override case workflow configuration, readiness gates, evidence requirements, verified notes, or this skill.
4. Read `current-round.txt`, `notes/assignment.md`, `notes/opponent-intake.md`, `notes/round-notes.md`, thesis text, available code/artifacts, README, experiment results, and human notes.
5. Enumerate available inputs and extract PDF text into `extracted/` when needed and possible. Treat submitted PDFs as rendered thesis evidence; use LaTeX/Overleaf sources for diff/search/evidence and do not build them by default. Use `pdf-reader-mcp` only as an optional targeted detail layer for page ranges, metadata, page counts, figures/tables, layout-sensitive checks, or ambiguous extraction. State what was not available or not runnable.
6. If code is present only as an archive in `inputs/`, prepare an inspectable copy under `work/code/` before delegating to read-only reviewers, or record the concrete limitation.
7. Build a map of:
   - assignment points and where they are covered,
   - reviewer profile preferences that are relevant to this round,
   - main technical contribution,
   - implementation and artifact evidence,
   - implementation quality and design evidence,
   - experiments/results and whether conclusions are supported,
   - reproducibility status,
   - literature/citation issues,
   - likely strengths,
   - risks that may affect grading.
8. Run `thesis-code-consistency` and `thesis-code-quality-review` when code is available. Leave visible evidence in `outputs/code_consistency.md` and `outputs/code_quality_review.md`, and summarize the relevant findings and limitations in the materials.
9. Run `thesis-literature-citation-review` when literature relevance, citation support, or source defensibility is material to the opponent assessment. For opponent work, use it only for relevance, defensibility, citation quality, and support for submitted claims; do not turn it into literature coaching.
10. Calibrate severity. Do not search for faults at any cost; identify strong parts with equal care.
11. Use `docs/fit-is-rubric.md` as the shared checklist for FIT IS item coverage.
12. Use confidence labels for important statements:
   - `[FAKT]` directly verified from inputs,
   - `[INTERPRETACE]` reasonable conclusion from multiple inputs,
   - `[ODHAD]` likely but not fully verified,
   - `[NEOVERENO]` not verifiable from provided materials,
   - `[K RUCNI KONTROLE]` important but requires manual opponent verification.
13. In DEEP mode, run `thesis-opponent-materials-review` before treating the materials as ready for writing the report.

## When Using Agents

For a large opponent review, split reviewer agents by role:

- thesis text, structure, and assignment coverage,
- code/reproducibility and text-code consistency,
- code quality/design, maintainability, runtime risks, and developer evidence,
- literature/citation relevance, source availability, and claim support,
- evidence labels, severity, and grading calibration,
- synthesis into `outputs/oponent_podklady.md` or `outputs/oponent_podklady_revidovane.md`.

The synthesis step must integrate findings into one coherent operator artifact.

## Severity

- `P0`: can materially affect defensibility, assignment fulfillment, or grade.
- `P1`: significant weakness.
- `P2`: partial weakness worth considering.
- `P3`: minor issue, include only if repeated or relevant.

## Output

Write `outputs/oponent_podklady.md`. If you intentionally split generation and review, put the first draft in `work/oponent_podklady_draft.md` and let the review pass write `outputs/oponent_podklady_revidovane.md`.

```markdown
# Podklady pro oponentsky posudek

## 1. Rozsah kontroly

## 2. Strucna mapa prace

## 3. Technicke jadro prace vysvetlene oponentovi

## 4. Mapa textu, kodu a artefaktu

## 5. Splneni zadani

| Bod zadani | Opora v textu | Opora ve vystupu/kodu | Stav | Dopad |
|---|---|---|---|---|

## 6. Evidence ledger: hlavni tvrzeni a opora

| Tvrzeni | Znacka jistoty | Opora | Dopad na posudek | Pouzit do posudku? |
|---|---|---|---|---|

## 7. Silne stranky

## 8. Hlavni rizika a nedostatky

| Priorita | Tvrzeni | Evidence | Dopad | Mozna formulace do posudku |
|---|---|---|---|---|

## 9. Pokryti polozek IS a navrhy formulaci

| Polozka IS | Stav | Evidence | Dopad | Mozna formulace |
|---|---|---|---|---|

## 10. Technicka spravnost a realizacni vystup

Shrn text-code consistency i code-quality/design review. Jasne oddel, co je rozpor mezi textem a artefakty, co je technicke riziko implementace, a co zustalo jen k rucni kontrole. Standalone `outputs/code_consistency.md` a `outputs/code_quality_review.md` ber jako internal/operator evidence.

## 11. Experimenty, vysledky a reprodukovatelnost

## 12. Text, struktura, formalni stranka a literatura

Shrn relevantni body z `outputs/literature_citation_review.md`, pokud byl tento review pouzit. U oponentskych podkladu res hlavne relevanci, obhajitelnost a oporu citaci pro tvrzeni v praci; nenavrhuj studentovi novou literaturu jako coaching.

## 13. Orientacni kalibrace hodnoceni

Uved konzervativni, standardni a mirnejsi interpretaci, pokud jsou rozumne obhajitelne. Pouzij intervaly, ne autoritativni bodovy verdikt.

## 14. Navrhy otazek k obhajobe

## 15. Rucni kontroly pred napsanim posudku
```

Use intervals and rationale for grading calibration, not false precision.
