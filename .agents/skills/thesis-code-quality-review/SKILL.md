---
name: thesis-code-quality-review
description: Review BP/DP submitted code for architecture, design quality, maintainability, runtime risks, documentation, and smoke-test readiness, separate from thesis-text versus code consistency.
---

# Thesis Code Quality Review

Use this skill when a thesis round contains implementation artifacts and you need to assess whether the implementation is technically well engineered and defensible.

This is not the text-code consistency check. Use `thesis-code-consistency` for whether thesis claims match code, README, configs, tests, and results. Use this skill for the quality of the implementation itself.

## Inputs

Use the active round unless the user specifies another:

```text
cases/<case-id>/current-round.txt
cases/<case-id>/rounds/<round-id>/
  notes/
  inputs/
  extracted/
  work/
  outputs/
```

Prefer unpacked code under `work/code/` when available. Archives in `inputs/` count as code. GitHub repo/PR snapshots imported by `thesis-github-code-intake` also count as code evidence, but PR-mode review must stay scoped to student-owned diffs and contribution areas. After agent use is authorized, the main workflow should run `scripts/prepare-code-workspace <case-id> [round-id]` or otherwise unpack/import code into `work/code/` before delegating to read-only reviewers. If the code cannot be unpacked or inspected, state that concrete limitation instead of inventing findings.

## Process

1. Resolve the active case and round.
2. Confirm that the user explicitly authorized agent use in the current request when this review will produce final standalone evidence or feed supervisor/opponent artifacts. If explicit authorization is missing, stop before writing the artifact and ask the user to authorize agents.
3. Enumerate available code artifacts, GitHub intake evidence, README/developer docs, dependency files, configs, tests, experiment scripts, generated/bundled assets, and thesis text that explains implementation choices.
4. If code is present only as an archive, run `scripts/prepare-code-workspace <case-id> [round-id]` when the current task permits writing ignored case workspace evidence. Use `work/code_workspace.md` and `work/serena_roots.json` as orientation aids; activate Serena only on one listed code root at a time. For Python and other supported language roots, prefer Serena symbol overview, definition, and reference tools for non-trivial architecture and maintainability inspection before falling back to broad file reads. Use `--refresh` only after confirming the whole ignored `work/code/` workspace can be rebuilt, because it removes manually imported code roots too. If GitHub URL/PR evidence is present but not yet imported, run or request `thesis-github-code-intake` before judging code quality. If you are in a read-only reviewer agent, report the missing prepared workspace/evidence instead of silently skipping the review.
5. Identify the project type and framework conventions before judging design. Do not punish a small thesis prototype for not looking like a production service.
6. For upstream PR contribution mode, use upstream code as integration context and focus findings on changed files, tests/docs, PR review discussion, CI state, and declared thesis scope.
7. Inspect the main implementation paths and assess:
   - architecture/design fit for the assignment and chosen framework,
   - module boundaries, data model, naming, and cohesion,
   - maintainability and readability,
   - error handling, validation, state handling, async/concurrency/runtime risks,
   - testing strategy, smoke-test workflow, and reproducibility for a reviewer,
   - README/developer documentation and installation/build instructions,
   - whether comments explain non-obvious logic without replacing clear code.
8. Run only simple local checks when they are documented, bounded, and do not need missing external data, credentials, services, models, or long execution.
9. Classify findings by severity and phase. In early drafts, prefer design direction and test plan feedback. In final checks, focus on issues that affect defensibility, runtime correctness, reviewer confidence, or grading.

## Evidence Rules

- Cite concrete code paths, functions, configs, README sections, missing tests, or missing build instructions.
- Do not claim that code ran unless you actually ran a specific command.
- Do not treat "not runnable from available inputs" as "broken".
- Separate code quality from text-code mismatch. If the issue is mainly that the thesis overclaims what code shows, route it through `thesis-code-consistency`.
- For PR-based work, do not treat the whole upstream repository as the student's implementation. Cite PR changed files, contribution map, review comments, CI state, or specific checkout paths from `outputs/github_code_intake.md`.
- If both a submitted archive and GitHub evidence exist, use the submitted archive as authoritative unless case/round notes explicitly declare GitHub as the submitted source; if they were not compared, keep GitHub-only quality findings scoped as supplemental evidence.
- For README, reproducibility, and smoke-test evidence: `thesis-code-consistency` checks whether thesis claims are supported by artifacts; this skill checks whether the submitted implementation is reviewable and maintainable independent of thesis claims. Cross-reference only when the same evidence affects both.
- Avoid low-value style nits unless they are repeated, confuse the implementation, or affect maintainability.
- Do not reward noisy comments. Prefer clear code plus useful comments around non-obvious decisions.

## Severity

- `P0`: can affect assignment fulfillment, defensibility, core runtime correctness, submission completeness, or grade.
- `P1`: significant engineering weakness or reviewer-confidence risk.
- `P2`: useful maintainability, documentation, or testability improvement.
- `P3`: minor style/readability issue; include only if repeated or representative.

## Review Loop

When this artifact is generated as standalone output, it is draft evidence until a different explicitly authorized reviewer agent checks it. If agent authorization is missing, ask before marking or relying on it as final standalone evidence; if authorization is not granted, stop before final standalone use or before using the artifact in a sendable supervisor/opponent synthesis. A downstream synthesis review certifies only the findings it uses, not the whole standalone artifact.

After writing or revising `outputs/code_quality_review.md`, run `scripts/init-review-manifest --run-checks <case-id> [round-id]` and record whether the artifact is standalone final evidence or only covered by a downstream synthesis review. Before relying on it, run `scripts/check-review-manifest --require-complete <case-id> [round-id]`.

## Output

Write `outputs/code_quality_review.md` when used as a standalone artifact:

```markdown
# Internal Code Quality Review

## Rozsah kontroly

## Technicky prehled implementace

## Silne technicke stranky

## Hlavni technicka rizika

| Priorita | Oblast | Evidence v kodu | Dopad | Doporuceni |
|---|---|---|---|---|

## Architektura a modularita

## Runtime, validace a chybove stavy

## Testy, smoke testy a reprodukovatelnost

## README, build a vyvojarska dokumentace

## Komentare, citelnost a udrzovatelnost

## Review Status

## Rucni kontroly
```

This standalone artifact is internal/operator evidence, not student-facing output by default. For supervisor feedback, summarize only actionable, phase-appropriate findings in `outputs/feedback_student.md`. For opponent materials, use the review as internal evidence for realization quality, reproducibility, risk calibration, and fair defense questions.
