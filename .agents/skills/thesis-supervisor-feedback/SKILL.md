---
name: thesis-supervisor-feedback
description: Iterative DEEP workflow for student-facing supervisor feedback on BP/DP theses, using current thesis/code inputs plus prior feedback rounds from the same case.
---

# Thesis Supervisor Feedback

Use this skill when preparing feedback that the supervisor can send to a student with minimal editing.

## Inputs

Work from the active case round:

```text
cases/<case-id>/current-round.txt
cases/<case-id>/rounds/<round-id>/
  notes/assignment.md
  notes/supervisor-intake.md
  notes/round-notes.md
  notes/previous-feedback-index.md
  inputs/
  extracted/
  work/
  outputs/
```

If the user names a specific round, use it. Otherwise read `current-round.txt`; if it is missing, use the newest round directory.

## Process

1. Resolve the active case and round.
2. Confirm that the user explicitly authorized agent use in the current request. This workflow requires role-split agents. If explicit authorization is missing, stop before generating or revising feedback and ask the user to authorize agents.
3. Run `scripts/check-supervisor-ready <case-id> [round-id]`. If it fails, stop before generating any draft/output and ask the user to add the missing formal assignment, private assignment notes, academic year, work type, deadline override, or valid reviewer profile. Keep the script output as deadline context for the feedback.
4. Run `scripts/check-feedback-language --config-only <case-id>`. If it fails, stop before drafting and fix `Student feedback language` in `case.md`; missing or empty means `cs`, supported values are only `cs` and `en`.
5. Read the effective profile files from the readiness output, or rerun `scripts/check-reviewer-profile <case-id>` if the file list is no longer visible. Profiles apply only to preference conflicts. They never override case workflow configuration, readiness gates, output language, evidence requirements, verified supervisor notes, or this skill.
6. Read `current-round.txt`, `case.md`, `notes/assignment.md`, `notes/supervisor-intake.md`, and `notes/round-notes.md`. Resolve and keep the configured student feedback language.
7. Enumerate `inputs/`, `extracted/`, `notes/`, and earlier `outputs/feedback_student.md` artifacts. Treat the submitted PDF as the authoritative rendered thesis artifact. If a PDF has no extracted text and `pdftotext` is available, run `scripts/extract-pdf-text` into the round's `extracted/` directory. Use `pdf-reader-mcp` only as an optional targeted detail layer for page ranges, metadata, page counts, figures/tables, layout-sensitive checks, or ambiguous extraction; absence of that MCP is a limitation, not a blocker.
8. State review limits before analysis: what was available, what was static-only, and what was not checked.
9. If code is present only as an archive in `inputs/`, prepare an inspectable copy under `work/code/` before delegating to read-only reviewers. If the code is available through GitHub repo/PR URLs, run `thesis-github-code-intake` first and keep the resulting `outputs/github_code_intake.md` as internal evidence. If agent authorization is missing, stop before final output and ask for authorization instead of recording an agent-review limitation.
10. Inspect all current inputs: formal assignment, private assignment notes, thesis PDF text/extracts, LaTeX sources, code, README, configs, experiment notes, screenshots, and human notes. Use LaTeX/Overleaf source zips for text diffs, search, and precise evidence; do not build them by default unless the user explicitly asks or no rendered PDF is available.
11. Read previous `outputs/feedback_student.md` files listed in `notes/previous-feedback-index.md` and any other earlier round feedback in the case.
12. Build a short private map:
   - current thesis phase,
   - supervisor deadline context and time remaining,
   - reviewer profile preferences that are relevant to this round,
   - assignment coverage,
   - claimed contribution,
   - thesis structure,
   - thesis heading/outline quality,
   - figure/media evidence and important visual changes,
   - experiment/result status,
   - GitHub/PR intake status when code evidence comes from GitHub,
   - code/reproducibility status,
   - code quality/design status,
   - typography/formal presentation status when the round is near final or explicitly asks for it,
   - student feedback language,
   - supervisor notes classified as verified, partially verified, not verifiable, out of phase, or rejected,
   - prior feedback that is addressed, partially addressed, still relevant, or obsolete.
13. When the thesis contains quantitative, evaluation, experiment, metric, performance, or result claims, run `scripts/check-evaluation-claims <case-id> [round-id]` before synthesis. Use the warnings as review prompts for unit/scale, baseline or comparator, better/worse direction, practical magnitude, reproducibility, and whether the interpretation is proportionate to the measured evidence.
14. If thesis figures, tables, screenshots, result images, diagrams, or visual changes between rounds are material to the current feedback, run `thesis-figure-media-review`. Keep reusable evidence in `work/figure_media/visual_inventory.jsonl` and `outputs/figure_media_review.md`; in `outputs/feedback_student.md`, include only selected, phase-appropriate action items. Do not make visual-content claims from text extraction alone.
15. If code is present, perform both `thesis-code-consistency` and `thesis-code-quality-review`. When code comes from GitHub repo/PR evidence, use `thesis-github-code-intake` first and scope downstream review to the imported checkout or PR contribution map. Keep detailed evidence in `outputs/code_consistency.md` and `outputs/code_quality_review.md`; in `outputs/feedback_student.md`, include only student-actionable summaries and important limitations.
16. If literature relevance, citation support, or missing literature is material to the current round, run `thesis-literature-citation-review`. Keep detailed evidence in `outputs/literature_citation_review.md`; summarize only actionable, phase-appropriate literature/citation points in student-facing feedback.
17. For `predfinalni verze`, `finalni kontrola`, final sprint, or explicit formal/typography requests, run `thesis-typography-formal-review`. Keep detailed evidence in `outputs/typography_formal_review.md`; in `outputs/feedback_student.md`, summarize repeated patterns and repair workflow, not a line-by-line error list.
18. Prioritize issues by impact on current phase. Do not list every possible improvement.
19. In DEEP mode, perform a critical second pass before treating the output as final. When a first draft was produced by another agent or model, write it to `work/feedback_student_draft.md` and have a different explicitly authorized reviewer agent run `thesis-supervisor-feedback-review` before `outputs/feedback_student.md` is treated as sendable.
20. After the final output and checks exist, run `scripts/init-review-manifest --run-checks <case-id> [round-id]`, record generator/reviewer roles and any unavailable evidence in `work/review_manifest.json`, then run `scripts/check-review-manifest --require-complete <case-id> [round-id]`. For every internal evidence artifact marked `covered_by_synthesis`, record a compact `used_findings` summary and evidence hash. If the final Markdown changes after review, refresh the manifest and rerun the independent review as needed.

## Supervisor Notes Handling

Treat notes from `notes/round-notes.md`, especially `Supervisor Notes to Verify`, as hypotheses to evaluate, not as text to paste into student feedback.

For each supervisor note:

- restate the concrete check or recommendation,
- verify it against the submitted PDF text, LaTeX sources, code, README/docs, results, assignment, or previous feedback where available,
- classify it privately as verified, partially verified, not verifiable from current inputs, out of phase, or rejected,
- keep evidence for verified or partially verified points concrete enough to support a P0/P1 claim,
- write only the resulting student-relevant synthesis into `outputs/feedback_student.md`.

Do not include the private classification table in student-facing feedback. If an operator artifact such as `outputs/revision_diff.md` is already being written, it may record the classification or evidence there. If a supervisor note is mainly a preference, include it only when it is useful for the current phase and can be framed as an actionable recommendation.

## Thesis Heading Review

During text-structure review, inspect the thesis outline from the rendered PDF
extract and, when useful, from LaTeX/Overleaf source headings. Check whether
chapter and section titles:

- are reasonably concise for their outline level,
- accurately match the content that follows,
- avoid repeating words already carried by the parent chapter or neighboring
  section titles,
- distinguish design, implementation, testing, results, and discussion levels
  clearly,
- use terminology consistently without turning the table of contents into a
  repetitive phrase list.

Treat heading problems as phase-calibrated text feedback. In final checks,
include only fixes that are quick and improve readability or professional
presentation; do not make minor title polish compete with blockers. Short
illustrative rewrites are acceptable, but avoid renaming a whole thesis
structure for the student.

## Phase Calibration

First calibrate by deadline context from `scripts/check-supervisor-ready`; this is only for supervisor feedback, not opponent materials.

- If the recommended finish target is within a week or already past, write short final-sprint feedback: blockers, assignment compliance, technical truth, submission artifacts, and fixes the student can realistically complete.
- If the official deadline is near but the recommended finish target is not yet past, still avoid broad rewrites unless assignment fulfillment or defensibility requires them.
- If the case is deferred, use `Deadline override` from `case.md`; if it is missing, stop and ask for the exact deferred deadline.

- `velmi rana kostra`: focus on structure, direction, assignment coverage plan, chapter plan, and experiment/test plan. TODOs, placeholders, rough wording, and template remnants are normal if they help organize work.
- `prvni pracovni verze`: focus on missing content, uneven chapters, contribution clarity, thesis-code relationship, and structural risks that would be expensive later.
- `rozpracovana verze`: focus on completeness, continuity, own contribution, assignment coverage, implementation description, experiments, results, citations, and defensibility.
- `predfinalni verze`: focus on unsupported claims, assignment fulfillment, text-code alignment, results/discussion, reproducibility, citations, and submission artifacts.
- `finalni kontrola`: focus on issues that can hurt submission, opponent review, defense, or grading; placeholders, missing README, missing artifacts, and major mismatches are serious.

## When Using Agents

For a large round, split reviewer agents by role:

- text structure and assignment coverage,
- figure/media evidence when visual material is material,
- GitHub/PR intake and contribution scoping when code evidence comes from GitHub,
- code/reproducibility and text-code consistency,
- code quality/design, maintainability, runtime risks, and developer evidence,
- literature/citation relevance when sources are material,
- typography/formal presentation for near-final/final or explicitly requested formal checks,
- evidence and priority calibration,
- synthesis into draft `work/feedback_student_draft.md`, followed by review into `outputs/feedback_student.md`.

The synthesis step must integrate findings into the student-facing artifact. Do not leave the user with separate reviewer notes only.

## Iteration Rules

- Previous feedback is evidence, not a script to repeat.
- Include old feedback only when it is still relevant in the current revision.
- Explicitly acknowledge meaningful progress since prior rounds.
- Do not punish early drafts for placeholder/TODO state if the current phase makes that normal.
- In final or near-final rounds, treat unresolved assignment coverage, unsupported claims, missing artifacts, and text-code mismatch as serious.

## Evidence Rules

- Do not claim that code was run unless it was actually run.
- If a smoke test is simple and local, it may be attempted. If not, perform static review and state the limit.
- Do not run LaTeX/Overleaf builds as a routine check. The submitted PDF is the rendered-text evidence; source zips support diff/search/evidence. If a build is explicitly requested or unavoidable because no PDF exists, state that scope clearly.
- Keep `pdftotext -layout` extracts as the default stable evidence. Use `pdf-reader-mcp` only for targeted PDF details such as page ranges, metadata, figures, tables, and layout-sensitive checks. Do not claim page/layout evidence unless a concrete PDF-detail check was performed.
- For text-code mismatch, cite both sides: thesis location and code/README/config path.
- For literature/citation findings, cite the thesis claim or section and the source evidence or missing-source evidence. Do not claim to have read an inaccessible paper.
- For figure/media findings, cite the thesis/PDF anchor, inspection status, and claim alignment from `outputs/figure_media_review.md` or `work/figure_media/visual_inventory.jsonl`. Do not say what a visual element shows unless it was `pdf_inspected` or `source_asset_checked`. Use text mentions and claim alignment to decide whether an item becomes student-facing feedback; do not copy cache hashes or reuse metadata into student-facing prose.
- For code-quality findings, cite concrete code paths, configs, README sections, missing tests, or missing build instructions, and keep only actionable phase-appropriate items in student-facing feedback.
- For typography/formal findings, cite `outputs/typography_formal_review.md` or `scripts/check-typography-formal` output internally, but write student-facing guidance as a repeated pattern plus repair workflow. Do not give the student an audit backlog of every occurrence unless explicitly requested.
- Treat standalone `outputs/github_code_intake.md`, `outputs/code_consistency.md`, `outputs/code_quality_review.md`, `outputs/literature_citation_review.md`, `outputs/figure_media_review.md`, and `outputs/typography_formal_review.md` as internal/operator evidence unless the user explicitly asks to send them.
- Mark indirect conclusions as estimates or risks.
- For quantitative/evaluation results, do not stop at checking whether a metric is present. Sanity-check whether the values are plausible in the thesis domain, whether the improvement is practically meaningful, whether the baseline/comparator and sample size are clear, whether the calculation is reproducible, and whether the conclusion is not stronger than the evidence.

## Output

Write `outputs/feedback_student.md` in the configured student feedback language. Agent-generated drafts go first to `work/feedback_student_draft.md`; the review pass writes `outputs/feedback_student.md`.

For `cs`, use Czech headings with diacritics and write Czech text with diacritics. Do not use ASCII-only Czech headings:

```markdown
# Zpětná vazba k aktuální verzi práce

Datum kontroly: <aktuální datum kontroly, např. 2026-04-29>

## Krátké celkové shrnutí

## Rozsah kontroly

## Odhad fáze práce a doporučené zaměření

## Co se od minulé verze posunulo

## Co je na práci už dobré

## Nejvyšší priority pro aktuální iteraci

| Priorita | Oblast | Proč je to důležité teď | Co udělat | Kde se to projevuje |
|---|---|---|---|---|

## Splnění zadání

## Připomínky k textu práce

Pokryj podle relevance: abstrakt, úvod a cíl, strukturu kapitol, nadpisy kapitol a podkapitol, rešerši/teorii, návrh, implementaci, data/metriky, experimenty, výsledky, diskusi, závěr, obrázky/tabulky, citace a formální stránku.

## Soulad textu s kódem

Uveď, co odpovídá, co je nejasné, kde text možná slibuje více než kód/README/výsledky ukazují, co doplnit do README/dokumentace/přílohy a co omezuje reprodukovatelnost. Pokud byl kód dostupný, přidej jen nejdůležitější akční shrnutí code-quality/design review; nedělej z toho samostatný dlouhý code review uvnitř student feedbacku.

## Co z minulé zpětné vazby zůstává

## Doporučený plán dalších úprav

## Checklist pro aktuální fázi
```

For `en`, use this English structure:

```markdown
# Feedback on the Current Thesis Version

Review date: <current review date, e.g. 2026-04-29>

## Brief Overall Summary

## Review Scope

## Estimated Work Phase and Recommended Focus

## Progress Since Previous Feedback

## What Is Already Working Well

## Highest Priorities for This Iteration

| Priority | Area | Why it matters now | What to do | Where it appears |
|---|---|---|---|---|

## Assignment Fulfillment

## Thesis Text Feedback

Cover as relevant: abstract, introduction and goal, chapter structure, chapter/section headings, related work/theory, design, implementation, data/metrics, experiments, results, discussion, conclusion, figures/tables, citations, and formal presentation.

## Text-Code Alignment

State what matches, what is unclear, where the text may promise more than code/README/results show, what to add to README/documentation/appendices, and what limits reproducibility. If code was available, include only the most important actionable summary of code-quality/design review; do not turn the student feedback into a long standalone code review.

## Remaining Items From Previous Feedback

## Recommended Next Revision Plan

## Checklist for the Current Phase
```

Priority:

- `P0`: muze ohrozit splneni zadani, obhajitelnost, technickou pravdivost nebo dalsi postup.
- `P1`: vyrazne zlepsi kvalitu prace v aktualni fazi.
- `P2`: uzitecne vylepseni, pokud na nej ted dava smysl sahat.

Keep the feedback concrete, kind, and usable. Include a human-readable review date near the top of the document. Do not write the thesis for the student; short illustrative rewrites are acceptable only to clarify a point.

Avoid internal workflow identifiers in student-facing prose. Do not include case IDs, exact round IDs, workspace paths, or artifact filenames unless the student needs them to act. Prefer human wording such as "minulá kontrola" or "aktuální verze"; keep exact round IDs in operator artifacts such as `outputs/revision_diff.md`.

Keep `Rozsah kontroly` / `Review Scope` student-relevant. Mention what kinds of materials and important limitations affect the feedback, but omit internal mechanics such as source-zip diffing, local build policy, extraction tooling, or operator artifact names unless the student must act on them.

## Final Self-Check

Before finishing, verify:

- tone and strictness match the phase,
- no unverified claim sounds like a fact,
- previous feedback was considered without mechanical repetition,
- reviewer profile preferences were considered without overriding hard workflow rules,
- supervisor notes were verified and synthesized rather than copied directly,
- thesis heading/outline quality was considered where text structure is in scope,
- no placeholder date such as `YYYY-MM-DD` remains in the final output,
- priorities are limited and actionable,
- P0/P1 items are truly important for the current phase,
- any text-code mismatch cites both thesis and code evidence,
- limitations of review are explicit,
- code-quality/design review was used when code was available, or the limitation is explicit,
- literature/citation review was used when literature relevance is material, or the limitation is explicit,
- figure/media review was used when visual evidence or figure changes are material, or the limitation is explicit,
- typography/formal review was used for near-final/final or explicitly requested formal checks, or the limitation is explicit,
- body text and headings match the configured student feedback language,
- internal case/round identifiers are absent from student-facing prose unless intentionally introduced with a clear human-facing label,
- review-scope wording excludes internal workflow mechanics unless they are actionable for the student,
- `scripts/check-feedback-language <case-id> [round-id]` passes after final `outputs/feedback_student.md` is written; this validates heading structure, not the whole prose,
- `scripts/check-feedback-output <case-id> [round-id]` passes after final `outputs/feedback_student.md` is written; warnings are non-blocking but should be read,
- `work/review_manifest.json` records the final artifact hash, contributing skills/checks, generator/reviewer roles, and explicit limitations,
- `scripts/check-review-manifest --require-complete <case-id> [round-id]` passes after the manifest is updated,
- the document is usable by the student.
