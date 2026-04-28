---
name: thesis-code-consistency
description: Check whether BP/DP thesis text claims are supported by the submitted code, README, configs, tests, experiments, and reproducibility artifacts.
---

# Thesis Code Consistency

Use this skill for code-aware checks inside supervisor feedback or opponent review.

## Process

1. Read `current-round.txt` if present and enumerate `inputs/`, `extracted/`, and code artifacts. If a PDF has no extracted text and `pdftotext` is available, run `scripts/extract-pdf-text` into the round's `extracted/` directory.
2. Identify thesis claims about:
   - implemented features,
   - architecture,
   - models/libraries/datasets,
   - experiments and metrics,
   - performance and accuracy,
   - deployment, reproducibility, and user-facing behavior.
3. Inspect code artifacts:
   - README and run instructions,
   - dependency files,
   - configs,
   - source tree structure,
   - tests,
   - experiment scripts,
   - notebooks,
   - result tables/logs,
   - licenses and third-party assets.
4. For each important claim, classify:
   - supported by code/artifacts,
   - plausible but not directly verified,
   - unclear,
   - contradicted by code/artifacts,
   - not checkable from available inputs.
5. Run only simple local smoke tests when they are clearly documented and do not need missing external data, models, credentials, or long execution.

## Evidence Rules

- Cite thesis location and code path together for mismatches.
- Do not treat "not checked" as "not working".
- Do not focus on style unless it affects reproducibility, comprehensibility, maintainability, licensing, or alignment with the thesis.
- If dependencies or data are missing, state that limitation and perform static review.
- For opponent work, do not turn missing run evidence into a claim that the implementation is non-functional.

## Output

Write `outputs/code_consistency.md` when used as a standalone artifact:

```markdown
# Soulad textu s kodem

## Rozsah kontroly

## Podporena tvrzeni

## Nejasna nebo neoverena tvrzeni

## Mozne rozpory textu a kodu

| Zavaznost | Tvrzeni v textu | Opora v textu | Opora v kodu | Problem | Doporuceni |
|---|---|---|---|---|---|

## Reprodukovatelnost

## README / Artefakty / Odevzdani

## Rucni kontroly
```

This artifact can be summarized into supervisor feedback or opponent materials.
