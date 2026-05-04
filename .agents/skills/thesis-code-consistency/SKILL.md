---
name: thesis-code-consistency
description: Check whether BP/DP thesis text claims are supported by the submitted code, README, configs, tests, experiments, and reproducibility artifacts; use thesis-code-quality-review for implementation design quality.
---

# Thesis Code Consistency

Use this skill for text-versus-code claim checks inside supervisor feedback or opponent review.

This skill answers whether the thesis says things that are supported by submitted artifacts. It does not answer whether the implementation is well engineered overall; use `thesis-code-quality-review` for architecture, maintainability, runtime risks, comments, developer documentation, and smoke-test readiness.

For README, reproducibility, and smoke-test evidence: this skill checks whether thesis claims are supported by artifacts; `thesis-code-quality-review` checks whether the submitted implementation is reviewable and maintainable independent of thesis claims. Cross-reference only when the same evidence affects both.

## Process

1. Resolve the active case and round from the user's target or `current-round.txt`.
2. Confirm that the user explicitly authorized agent use in the current request when this check will produce final standalone evidence or feed supervisor/opponent artifacts. If explicit authorization is missing, stop before writing the artifact and ask the user to authorize agents.
3. Enumerate `inputs/`, `extracted/`, GitHub intake evidence, and code artifacts. Treat submitted PDFs as rendered thesis evidence. If a PDF has no extracted text and `pdftotext` is available, run `scripts/extract-pdf-text` into the round's `extracted/` directory; do not build LaTeX/Overleaf sources by default. Use `pdf-reader-mcp` only for targeted page ranges, metadata, page counts, figures/tables, layout-sensitive checks, or ambiguous extraction.
4. When the thesis contains quantitative, evaluation, experiment, metric, performance, or result claims, run `scripts/check-evaluation-claims <case-id> [round-id]` after thesis text extraction. Treat warnings as semantic-review prompts, not as automatic findings. For every warning that affects supervisor feedback or opponent materials, verify the claim against thesis text, code/notebooks/scripts, data, result exports, README instructions, and reproducibility evidence.
5. Identify thesis claims about:
   - implemented features,
   - architecture, only where the text makes explicit architecture claims,
   - models/libraries/datasets,
   - experiments and metrics,
   - performance and accuracy,
   - deployment, reproducibility, and user-facing behavior.
6. If code is present only as an archive or source directory in `inputs/`, run `scripts/prepare-code-workspace <case-id> [round-id]` when the current task permits writing ignored case workspace evidence. Use `work/code_workspace.md` and `work/serena_roots.json` as orientation aids; activate Serena only on one listed code root at a time. If you are in a read-only reviewer agent and the prepared workspace is missing, report that limitation instead of silently skipping code checks.
7. Inspect code artifacts:
   - `outputs/github_code_intake.md`, `inputs/github/`, and `work/github-intake/` when GitHub repo/PR intake was used,
   - `work/code_workspace.md`, `work/serena_roots.json`, and `work/code/` when submitted archives or source directories were prepared with `scripts/prepare-code-workspace`,
   - README and run instructions,
   - dependency files,
   - configs,
   - source tree structure,
   - tests,
   - experiment scripts,
   - notebooks,
   - result tables/logs,
   - licenses and third-party assets.
8. For PR-based contributions, distinguish upstream baseline from student-owned changes. Check whether the thesis clearly separates existing upstream functionality, reused libraries/modules, and the student's PR diff/commits/tests/docs.
9. For each important claim, classify:
   - supported by code/artifacts,
   - plausible but not directly verified,
   - unclear,
   - contradicted by code/artifacts,
   - not checkable from available inputs.
10. Run only simple local smoke tests when they are clearly documented and do not need missing external data, models, credentials, or long execution.

## Evidence Rules

- Cite thesis location and code path together for mismatches.
- Do not claim page/layout evidence unless `pdf-reader-mcp` or another concrete PDF-detail check was used; otherwise cite text-extract evidence.
- Do not treat "not checked" as "not working".
- Do not focus on style or broad design quality unless it affects reproducibility, licensing, or alignment with an explicit thesis claim. Route broader implementation-quality findings to `thesis-code-quality-review`.
- If dependencies or data are missing, state that limitation and perform static review.
- If GitHub PR comments, reviews, CI, head/base refs, or checkout evidence are unavailable, state the limitation instead of inferring contribution quality.
- If both a submitted archive and GitHub evidence exist, use the submitted archive as authoritative unless case/round notes explicitly declare GitHub as the submitted source; if they were not compared, state that limitation.
- For PR-based work, cite PR number/URL, changed files, commit/review evidence, and thesis text together; do not review the entire upstream project as student-authored code.
- For opponent work, do not turn missing run evidence into a claim that the implementation is non-functional.
- For quantitative/evaluation claims, check more than metric names: unit/scale, baseline or comparator, better/worse direction, sample size/date range, variance or uncertainty, practical magnitude in the domain, source data and calculation path, and whether the written conclusion is proportionate to the measured effect.

## Review Loop

When this artifact is generated as standalone output, it is draft evidence until a different explicitly authorized reviewer agent checks it. If agent authorization is missing, ask before marking or relying on it as final standalone evidence; if authorization is not granted, stop before final standalone use or before using the artifact in a sendable supervisor/opponent synthesis. A downstream synthesis review certifies only the findings it uses, not the whole standalone artifact.

After writing or revising `outputs/code_consistency.md`, run `scripts/init-review-manifest --run-checks <case-id> [round-id]` and record whether the artifact is standalone final evidence or only covered by a downstream synthesis review. Before relying on it, run `scripts/check-review-manifest --require-complete <case-id> [round-id]`.

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
