---
name: thesis-typography-formal-review
description: Internal BP/DP evidence workflow for late-stage typography and formal-presentation checks, language-calibrated for Czech/Slovak and English theses, with student-facing synthesis as action guidance rather than an audit list.
---

# Thesis Typography/Formal Review

Use this skill when supervisor feedback, opponent materials, or a standalone
operator check needs late-stage evidence about typographic and formal
presentation issues. The output is internal/operator evidence by default, not a
student-facing list of all errors.

## Inputs

Use the active round unless the user specifies another:

```text
cases/<case-id>/case.md
cases/<case-id>/rounds/<round-id>/
  extracted/
  work/thesis-source/
  outputs/
```

`Thesis language: cs/sk/en/auto` may be configured in `case.md`, with
`notes/round-notes.md` used only for round-local structured metadata when
`case.md` is absent or set to `auto`. It describes the thesis text language and
does not control `Student feedback language`.

## Process

1. Confirm that the user explicitly authorized agent use when this review will
   produce final standalone evidence or feed supervisor/opponent artifacts. If
   authorization is missing, stop before writing or relying on a final artifact.
2. Resolve the active case and round. For supervisor/student-facing use, run
   `scripts/check-supervisor-ready <case-id> [round-id]`; for opponent/internal
   use, run `scripts/check-round-ready <case-id> [round-id]`.
3. Treat the submitted PDF text extract as the rendered source of truth. If a
   PDF exists but no extract is available, use `scripts/extract-pdf-text` first.
   Use LaTeX/Overleaf sources only for repair hints and exact source search; do
   not build LaTeX or mutate student sources by default.
4. Run `scripts/check-typography-formal <case-id> [round-id]`. Treat warnings as
   reviewer prompts, not automatic findings.
5. Calibrate by thesis language:
   - `cs` or `sk`: check short Czech/Slovak prepositions/conjunctions at rendered line
     ends, LaTeX `~`/`vlna` hints, punctuation spacing, bracket spacing,
     dash/hyphen usage, and leftover placeholders. Preserve Slovak metadata as
     `sk`; do not relabel the thesis as Czech just because the rule family is
     shared.
   - `en`: do not apply Czech `vlna` line-break rules; focus on punctuation,
     bracket spacing, dash/hyphen usage, quote consistency where visible, and
     leftover placeholders. Prefer normal editor/Overleaf spell and grammar
     tooling plus manual final proofread.
6. Summarize repeated patterns, counts, representative examples, recommended
   repair workflow, and limitations. Do not enumerate every line-level issue.
7. For supervisor feedback, include only phase-appropriate action guidance. A
   good student-facing form is: "V práci se opakovaně objevuje typografický
   problém X; spusťte nástroj/postup Y a výsledek ručně zkontrolujte."
8. Do not let typography outrank assignment fulfillment, technical truth,
   results, reproducibility, missing artifacts, or defense readiness.
9. After writing `outputs/typography_formal_review.md`, run
   `scripts/check-typography-formal --require-output <case-id> [round-id]`
   again and make sure the artifact reflects either the warnings or an explicit
   limitation.
10. Run `scripts/init-review-manifest --run-checks <case-id> [round-id]` and record whether
   the typography/formal evidence is standalone final evidence or only covered by
   downstream supervisor/opponent synthesis. Before relying on it, run
   `scripts/check-review-manifest --require-complete <case-id> [round-id]`.

## When To Use

Use this review in `predfinalni verze`, `finalni kontrola`, final sprint, or
when the user explicitly asks for formal/typography control. In early drafts,
mention only severe readability problems or defer typography to later.

## Review Loop

When this artifact is generated as standalone output, it is draft evidence until
a different explicitly authorized reviewer agent checks it. If agent
authorization is missing, ask before marking or relying on it as final
standalone evidence. A downstream synthesis review certifies only the findings
it uses, not the whole standalone artifact.

## Output

Write `outputs/typography_formal_review.md`:

```markdown
# Typography/Formal Review

## Review Scope

## Thesis Language

## Deterministic Checker Findings

| Pattern | Language mode | Count | Representative examples | Recommended repair |
|---|---|---:|---|---|

## Source-Level Hints

## Student-Facing Synthesis

## Downstream Use

## Review Status

## Manual Checks
```

This artifact is internal/operator evidence. Supervisor feedback and opponent
materials should use only selected, phase-appropriate synthesis. Do not expose a
long checklist of line-level typography findings to the student unless the user
explicitly asks for a detailed audit.
