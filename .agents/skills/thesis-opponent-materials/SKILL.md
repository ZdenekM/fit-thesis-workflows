---
name: thesis-opponent-materials
description: DEEP workflow for internal opponent materials for a BP/DP report, with evidence labels, risk calibration, and thesis/code consistency review.
---

# Thesis Opponent Materials

Use this skill to prepare internal materials for an opponent report. The output is not the final report to submit.

## Inputs

Use the active round unless the user specifies another:

```text
cases/<case-id>/rounds/<round-id>/
  notes/assignment.md
  notes/opponent-intake.md
  inputs/
  extracted/
  outputs/
```

## Process

1. Resolve the active case and round.
2. Run `scripts/check-round-ready <case-id> [round-id]`. If it fails, stop before generating materials and ask the user to add the formal assignment and private assignment notes to `notes/assignment.md`.
3. Read `current-round.txt`, `notes/assignment.md`, `notes/opponent-intake.md`, `notes/round-notes.md`, thesis text, available code/artifacts, README, experiment results, and human notes.
4. Enumerate available inputs and extract PDF text into `extracted/` when needed and possible. State what was not available or not runnable.
5. Build a map of:
   - assignment points and where they are covered,
   - main technical contribution,
   - implementation and artifact evidence,
   - experiments/results and whether conclusions are supported,
   - reproducibility status,
   - literature/citation issues,
   - likely strengths,
   - risks that may affect grading.
6. Run `thesis-code-consistency` when code is available.
7. Calibrate severity. Do not search for faults at any cost; identify strong parts with equal care.
8. Use `docs/fit-is-rubric.md` as the shared checklist for FIT IS item coverage.
9. Use confidence labels for important statements:
   - `[FAKT]` directly verified from inputs,
   - `[INTERPRETACE]` reasonable conclusion from multiple inputs,
   - `[ODHAD]` likely but not fully verified,
   - `[NEOVERENO]` not verifiable from provided materials,
   - `[K RUCNI KONTROLE]` important but requires manual opponent verification.
10. In DEEP mode, run `thesis-opponent-materials-review` before treating the materials as ready for writing the report.

## When Using Agents

For a large opponent review, split reviewer agents by role:

- thesis text, structure, and assignment coverage,
- code/reproducibility and text-code consistency,
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

## 11. Experimenty, vysledky a reprodukovatelnost

## 12. Text, struktura, formalni stranka a literatura

## 13. Orientacni kalibrace hodnoceni

Uved konzervativni, standardni a mirnejsi interpretaci, pokud jsou rozumne obhajitelne. Pouzij intervaly, ne autoritativni bodovy verdikt.

## 14. Navrhy otazek k obhajobe

## 15. Rucni kontroly pred napsanim posudku
```

Use intervals and rationale for grading calibration, not false precision.
