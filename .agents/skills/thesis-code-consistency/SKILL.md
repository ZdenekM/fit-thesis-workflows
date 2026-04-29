---
name: thesis-code-consistency
description: Check whether BP/DP thesis text claims are supported by the submitted code, README, configs, tests, experiments, and reproducibility artifacts; use thesis-code-quality-review for implementation design quality.
---

# Thesis Code Consistency

Use this skill for text-versus-code claim checks inside supervisor feedback or opponent review.

This skill answers whether the thesis says things that are supported by submitted artifacts. It does not answer whether the implementation is well engineered overall; use `thesis-code-quality-review` for architecture, maintainability, runtime risks, comments, developer documentation, and smoke-test readiness.

For README, reproducibility, and smoke-test evidence: this skill checks whether thesis claims are supported by artifacts; `thesis-code-quality-review` checks whether the submitted implementation is reviewable and maintainable independent of thesis claims. Cross-reference only when the same evidence affects both.

## Process

1. Read `current-round.txt` if present and enumerate `inputs/`, `extracted/`, and code artifacts. Treat submitted PDFs as rendered thesis evidence. If a PDF has no extracted text and `pdftotext` is available, run `scripts/extract-pdf-text` into the round's `extracted/` directory; do not build LaTeX/Overleaf sources by default. Use `pdf-reader-mcp` only for targeted page ranges, metadata, page counts, figures/tables, layout-sensitive checks, or ambiguous extraction.
2. Identify thesis claims about:
   - implemented features,
   - architecture, only where the text makes explicit architecture claims,
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
- Do not claim page/layout evidence unless `pdf-reader-mcp` or another concrete PDF-detail check was used; otherwise cite text-extract evidence.
- Do not treat "not checked" as "not working".
- Do not focus on style or broad design quality unless it affects reproducibility, licensing, or alignment with an explicit thesis claim. Route broader implementation-quality findings to `thesis-code-quality-review`.
- If dependencies or data are missing, state that limitation and perform static review.
- For opponent work, do not turn missing run evidence into a claim that the implementation is non-functional.

## Review Loop

When this artifact is generated as standalone output, it is draft evidence until a different reviewer agent or reviewer role checks it. For standalone final use, record the reviewer verdict in `## Review Status`, the provenance manifest, or the final response. When it is generated as input to supervisor feedback or opponent materials, the downstream synthesis review must re-check the important findings before using them; that certifies only the findings used in the synthesis, not the whole standalone artifact.

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

## Review Status

## Rucni kontroly
```

This artifact can be summarized into supervisor feedback or opponent materials.
