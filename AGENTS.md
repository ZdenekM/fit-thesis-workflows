# diplomky_v2 Agent Instructions

This repository is a workflow layer for supervising and reviewing BP/DP theses. It is not an application. Keep the system simple: use project instructions, skills, plain Markdown artifacts, and small helper scripts only when they remove repeated manual work.

## Core Rules

- Work in one mode only: `DEEP`. Do not ask the user to choose FAST/STANDARD/DEEP.
- Case data lives under `cases/`. The directory is intentionally gitignored except for `cases/README.md`.
- Never move student PDFs, source zips, extracted text, code submissions, private notes, or generated case outputs into tracked paths.
- Do not preserve backward compatibility with older `~/code/diplomky` workflows unless the user explicitly asks.
- Avoid workaround thinking. If the workflow is too complicated, simplify the workflow rather than adding fallback layers.
- Do not pretend to have checked anything that was not available in the inputs. Mark indirect conclusions as estimates, risks, or items for manual verification.
- Important negative claims must cite evidence: a chapter/section/page, a file/path/function, a README/config/test, a missing artifact, or a concrete mismatch.
- Before generating supervisor feedback, require both assignment and deadline context with `scripts/check-supervisor-ready <case-id> [round-id]`. If it fails, stop and ask for the missing assignment, academic year, work type, or deadline override.
- Before generating opponent materials, require assignment context with `scripts/check-round-ready <case-id> [round-id]`. Supervisor deadline calibration does not apply to opponent reports.

## Skill Routing

Use these repo-local skills as the primary workflow definitions:

- `.agents/skills/thesis-supervisor-feedback/SKILL.md` for iterative student-facing supervisor feedback.
- `.agents/skills/thesis-supervisor-feedback-review/SKILL.md` for the required critical second pass before sending supervisor feedback.
- `.agents/skills/thesis-opponent-materials/SKILL.md` for internal opponent preparation materials.
- `.agents/skills/thesis-opponent-materials-review/SKILL.md` for reviewing and hardening generated opponent materials.
- `.agents/skills/thesis-opponent-report-review/SKILL.md` for reviewing a draft opponent report before submission.
- `.agents/skills/thesis-revision-diff/SKILL.md` for comparing thesis/code revisions and checking whether prior feedback was addressed.
- `.agents/skills/thesis-code-consistency/SKILL.md` for thesis-text versus code/reproducibility checks.
- `.agents/skills/thesis-code-quality-review/SKILL.md` for implementation quality, architecture/design, maintainability, runtime risks, and reviewer-facing developer evidence.

When a round contains code, supervisor feedback and opponent materials must use both `thesis-code-consistency` and `thesis-code-quality-review`, or explicitly state why one of them could not be performed from the available inputs.

Code artifacts include source directories and archives copied into `inputs/`. Before delegating to read-only reviewer agents, make the code inspectable under the ignored round workspace, typically `work/code/`, or record a concrete limitation in the final artifact.

Keep this `AGENTS.md` short. Put long task procedures into skills or templates.

## Case Layout

Use this shape for local work:

```text
cases/<case-id>/
  case.md
  current-round.txt
  rounds/
    <timestamp>-<label>/
      notes/
      inputs/
      extracted/
      work/
      outputs/
```

For iterative supervisor feedback, always inspect previous rounds in the same case before writing new feedback. Read earlier `outputs/feedback_student.md` files and distinguish:

- feedback already addressed,
- feedback partially addressed,
- feedback still relevant,
- new risks introduced by the current revision.

Do not repeat old feedback mechanically.

## Parallel Review

When the user asks to use agents, give them enough time. For large thesis/code reviews, split work by role rather than by arbitrary files:

- text structure and assignment coverage,
- code/reproducibility and text-code consistency,
- code quality/design and reviewer-facing implementation evidence,
- evidence and claim calibration,
- synthesis into the final Markdown artifact.

The final output must integrate findings into the requested artifact, not just list reviewer comments.

## Output Conventions

Default outputs go into the active round:

- supervisor feedback: `outputs/feedback_student.md`
- supervisor feedback draft, when a separate review pass is useful: `work/feedback_student_draft.md`
- revision comparison: `outputs/revision_diff.md`
- code consistency check: `outputs/code_consistency.md`
- code quality/design review: `outputs/code_quality_review.md`
- opponent materials: `outputs/oponent_podklady.md`
- reviewed opponent materials: `outputs/oponent_podklady_revidovane.md`
- opponent materials draft, when a separate review pass is useful: `work/oponent_podklady_draft.md`
- opponent report review: `outputs/feedback_k_posudku.md`

Standalone code consistency and code quality outputs are internal/operator evidence unless the user explicitly asks to send them. Student-facing feedback should contain only selected, phase-appropriate action items.

Before closing a task, run relevant lightweight checks such as `scripts/check-private`, `bash -n scripts/*`, and `git diff --check`.
