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
2. Run `scripts/check-supervisor-ready <case-id> [round-id]`. If it fails, stop before generating any draft/output and ask the user to add the missing formal assignment, private assignment notes, academic year, work type, or deadline override. Keep the script output as deadline context for the feedback.
3. Read `current-round.txt`, `case.md`, `notes/assignment.md`, `notes/supervisor-intake.md`, and `notes/round-notes.md`.
4. Enumerate `inputs/`, `extracted/`, `notes/`, and earlier `outputs/feedback_student.md` artifacts. If a PDF has no extracted text and `pdftotext` is available, run `scripts/extract-pdf-text` into the round's `extracted/` directory.
5. State review limits before analysis: what was available, what was static-only, and what was not checked.
6. If code is present only as an archive in `inputs/`, prepare an inspectable copy under `work/code/` before delegating to read-only reviewers, or record the concrete limitation.
7. Inspect all current inputs: formal assignment, private assignment notes, thesis PDF text/extracts, LaTeX sources, code, README, configs, experiment notes, screenshots, and human notes.
8. Read previous `outputs/feedback_student.md` files listed in `notes/previous-feedback-index.md` and any other earlier round feedback in the case.
9. Build a short private map:
   - current thesis phase,
   - supervisor deadline context and time remaining,
   - assignment coverage,
   - claimed contribution,
   - thesis structure,
   - experiment/result status,
   - code/reproducibility status,
   - code quality/design status,
   - prior feedback that is addressed, partially addressed, still relevant, or obsolete.
10. If code is present, perform both `thesis-code-consistency` and `thesis-code-quality-review`. Leave visible evidence either as `outputs/code_consistency.md` and `outputs/code_quality_review.md`, or in `outputs/feedback_student.md` under `Rozsah kontroly` by naming inspected code paths and explicit limitations.
11. Prioritize issues by impact on current phase. Do not list every possible improvement.
12. In DEEP mode, perform a critical second pass before treating the output as final. Use `thesis-supervisor-feedback-review` when the first draft is substantial, high-stakes, or was produced by another agent.

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
- code/reproducibility and text-code consistency,
- code quality/design, maintainability, runtime risks, and developer evidence,
- evidence and priority calibration,
- synthesis into the final `outputs/feedback_student.md`.

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
- For text-code mismatch, cite both sides: thesis location and code/README/config path.
- For code-quality findings, cite concrete code paths, configs, README sections, missing tests, or missing build instructions, and keep only actionable phase-appropriate items in student-facing feedback.
- Treat standalone `outputs/code_consistency.md` and `outputs/code_quality_review.md` as internal/operator evidence unless the user explicitly asks to send them.
- Mark indirect conclusions as estimates or risks.

## Output

Write `outputs/feedback_student.md` with this structure. If you intentionally split generation and review, put the first draft in `work/feedback_student_draft.md` and let the review pass write `outputs/feedback_student.md`.

```markdown
# Zpetna vazba k aktualni verzi prace

## Kratke celkove shrnuti

## Rozsah kontroly

## Odhad faze prace a doporucene zamereni

## Co se od minule posunulo

## Co je na praci uz dobre

## Nejvyssi priority pro aktualni iteraci

| Priorita | Oblast | Proc je to dulezite ted | Co udelat | Kde se to projevuje |
|---|---|---|---|---|

## Splneni zadani

## Pripominky k textu prace

Pokryj podle relevance: abstrakt, uvod a cil, strukturu kapitol, resersi/teorii, navrh, implementaci, data/metriky, experimenty, vysledky, diskusi, zaver, obrazky/tabulky, citace a formalni stranku.

## Soulad textu s kodem

Uved, co odpovida, co je nejasne, kde text mozna slibuje vice nez kod/README/vysledky ukazuji, co doplnit do README/dokumentace/prilohy a co omezuje reprodukovatelnost. Pokud kod byl dostupny, pridej jen nejdulezitejsi akcni shrnuti code-quality/design review; nedelej z toho samostatny dlouhy code review uvnitr student feedbacku.

## Co z minule zpetne vazby zustava

## Doporuceny plan dalsich uprav

## Checklist pro aktualni fazi
```

Priority:

- `P0`: muze ohrozit splneni zadani, obhajitelnost, technickou pravdivost nebo dalsi postup.
- `P1`: vyrazne zlepsi kvalitu prace v aktualni fazi.
- `P2`: uzitecne vylepseni, pokud na nej ted dava smysl sahat.

Keep the feedback concrete, kind, and usable. Do not write the thesis for the student; short illustrative rewrites are acceptable only to clarify a point.

## Final Self-Check

Before finishing, verify:

- tone and strictness match the phase,
- no unverified claim sounds like a fact,
- previous feedback was considered without mechanical repetition,
- priorities are limited and actionable,
- P0/P1 items are truly important for the current phase,
- any text-code mismatch cites both thesis and code evidence,
- limitations of review are explicit,
- code-quality/design review was used when code was available, or the limitation is explicit,
- the document is usable by the student.
