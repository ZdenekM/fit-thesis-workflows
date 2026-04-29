---
name: thesis-supervisor-feedback-review
description: Critical second pass over generated student-facing BP/DP supervisor feedback, verifying P0/P1 claims against available inputs and producing the final sendable Markdown.
---

# Thesis Supervisor Feedback Review

Use this skill after a first version of supervisor feedback exists. The goal is not to add more critique; the goal is to make the feedback fair, evidence-backed, phase-appropriate, concise, and sendable.

## Inputs

Use the active round:

```text
cases/<case-id>/rounds/<round-id>/
  notes/assignment.md
  work/feedback_student_draft.md
  outputs/feedback_student.md
  notes/
  inputs/
  extracted/
```

If both `work/feedback_student_draft.md` and `outputs/feedback_student.md` exist, review the draft unless the user explicitly says the output file is the draft.

## Review Checks

1. Run `scripts/check-supervisor-ready <case-id> [round-id]`. If it fails, stop and ask for the missing assignment/deadline context instead of reviewing/generating the final output.
2. Re-check every P0/P1 claim against available assignment context, supervisor deadline context, thesis text, code, README, LaTeX sources, previous feedback, code-consistency evidence, code-quality/design evidence, and notes.
3. Remove or soften claims that are speculative, not evidenced, too absolute, or not useful for the current phase.
4. Merge duplicates and remove low-impact details that distract from the next iteration.
5. Verify that previous feedback is not repeated after it has been addressed.
6. Check that text-code mismatch claims cite both the thesis-side and code-side evidence.
7. Check that code-quality/design claims cite concrete code paths, configs, README/build docs, tests, or missing artifacts, and are not just style preferences.
8. If code exists, verify that both code-consistency and code-quality/design review are visibly evidenced by standalone internal artifacts or by an explicit `Rozsah kontroly` entry naming inspected paths and limitations. If not, repair the output or state the limitation.
9. Keep at most 8 priority rows, ideally 3-6.
10. Preserve concrete positives and a motivating but direct tone.
11. Make the final checklist specific to this thesis and phase, not generic.
12. Verify that priority and tone match the time remaining until the recommended finish and official deadline.
13. Respect the supervisor's declared "do not reopen now" boundary unless ignoring it would risk assignment fulfillment, technical truth, submission, or defense.

## Priority Calibration

- `P0`: can affect assignment fulfillment, defensibility, technical truth, submission readiness, or the student's next step.
- `P1`: materially improves the current iteration.
- `P2`: useful only if it is sensible to touch now.

If a priority does not pass that test, downgrade it, merge it, move it to the checklist, or remove it.

## Output

Write the final sendable Markdown to `outputs/feedback_student.md`. Do not write a separate audit unless the user asks for one.

The final document must retain the supervisor-feedback structure:

```markdown
# Zpetna vazba k aktualni verzi prace

## Kratke celkove shrnuti
## Rozsah kontroly
## Odhad faze prace a doporucene zamereni
## Co se od minule posunulo
## Co je na praci uz dobre
## Nejvyssi priority pro aktualni iteraci
## Splneni zadani
## Pripominky k textu prace
## Soulad textu s kodem
## Co z minule zpetne vazby zustava
## Doporuceny plan dalsich uprav
## Checklist pro aktualni fazi
```
