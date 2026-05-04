# diplomky_v2 Agent Instructions

This repository is a workflow layer for supervising and reviewing BP/DP theses. It is not an application. Keep the system simple: use project instructions, skills, plain Markdown artifacts, and small helper scripts only when they remove repeated manual work.

## Core Rules

- Work in one mode only: `DEEP`. Do not ask the user to choose FAST/STANDARD/DEEP.
- Case data lives under `cases/`. The directory is intentionally gitignored except for `cases/README.md`.
- Never move student PDFs, source zips, extracted text, code submissions, private notes, or generated case outputs into tracked paths.
- Do not preserve backward compatibility with older `~/code/diplomky` workflows unless the user explicitly asks.
- Avoid workaround thinking. If the workflow is too complicated, simplify the workflow rather than adding fallback layers.
- Preserve `README.md` as the human/operator-facing chat-first entrypoint. Its top path should explain what a supervisor or opponent writes to the agent, include concise prompt examples, and keep script/skill internals as lower-level reference. Do not let it regress into a script-first runbook; move detailed procedures into skills, templates, or focused docs.
- Pipeline and helper-script extensions must be general and context-aware. Do not encode one real thesis, domain, dataset, concrete metric value, filename, or expected conclusion as an active workflow rule. When a case exposes a useful pattern, generalize it into evidence classes, configurable reviewer prompts, or cross-case checks, and apply the interpretation in the context of the current assignment, thesis phase, artifacts, and claims.
- Do not pretend to have checked anything that was not available in the inputs. Mark indirect conclusions as estimates, risks, or items for manual verification.
- Important negative claims must cite evidence: a chapter/section/page, a file/path/function, a README/config/test, a missing artifact, or a concrete mismatch.
- Quantitative, evaluation, experiment, metric, performance, and result claims require semantic sanity review: check unit/scale, baseline, practical magnitude, reproducibility, and whether the thesis interpretation is proportionate to the values.
- Treat the submitted thesis PDF as the authoritative rendered thesis artifact. Do not run LaTeX/Overleaf builds by default; use source zips for diff/search/evidence. Compile only when the user explicitly asks, or when no rendered PDF is available and the limitation is stated.
- Before generating supervisor feedback, require assignment, deadline, and reviewer-profile context with `scripts/check-supervisor-ready <case-id> [round-id]`. If it fails, stop and ask for the missing assignment, academic year, work type, deadline override, or valid reviewer profile.
- Before generating opponent materials, require assignment and reviewer-profile context with `scripts/check-round-ready <case-id> [round-id]`. Supervisor deadline calibration does not apply to opponent reports.
- Supervisor feedback, opponent materials, opponent-report review, revision diff, code consistency, code quality, and literature/citation review are multi-agent workflows. If the user has not explicitly authorized agent use in the current request, stop before producing or revising sendable/final artifacts and ask for explicit permission to use agents. Once authorized, use role-split agents and give them enough time.

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
- `.agents/skills/thesis-literature-citation-review/SKILL.md` for cited-literature relevance, source availability, and citation-support checks.

When a round contains code, supervisor feedback and opponent materials must use both `thesis-code-consistency` and `thesis-code-quality-review`, or explicitly state why one of them could not be performed from the available inputs.

Code artifacts include source directories and archives copied into `inputs/`. After agent use is explicitly authorized, make code inspectable under the ignored round workspace, typically `work/code/`, before delegating to read-only reviewer agents. If authorization is missing, stop before generating any agent-dependent final artifact and ask for it.

Keep this `AGENTS.md` short. Put long task procedures into skills or templates.
When changing workflow docs or skills, scan `WORKFLOW_MEMORY.md` for reusable
lessons and promote active rules into the appropriate workflow file instead of
treating memory as a second instruction system.

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

When the user explicitly authorizes agents, give them enough time. If authorization is missing, ask once and wait; do not begin the parallel review or generate a sendable/final artifact. For thesis/code reviews, split work by role rather than by arbitrary files:

- text structure and assignment coverage,
- code/reproducibility and text-code consistency,
- code quality/design and reviewer-facing implementation evidence,
- literature/citation relevance, source availability, and claim support,
- evidence and claim calibration,
- synthesis into the final Markdown artifact.

The final output must integrate findings into the requested artifact, not just list reviewer comments.

## Generated Artifact Review Loop

Any generated Markdown artifact under `outputs/` that is sendable to a student/opponent context, or used as final operator evidence, must pass an explicitly authorized independent agent review loop. If the user has not authorized agents in the current request, ask for authorization and stop before writing or revising the final artifact. The loop terminates only when a different explicitly authorized reviewer agent checks the draft or evidence and either writes the reviewed target artifact or explicitly approves it. Material edits after that review reopen the draft state.

Dedicated review loops:

- supervisor feedback: first draft in `work/feedback_student_draft.md`, then `thesis-supervisor-feedback-review` writes reviewed `outputs/feedback_student.md`;
- opponent materials: first draft in `work/oponent_podklady_draft.md` or `outputs/oponent_podklady.md`, then `thesis-opponent-materials-review` writes reviewed `outputs/oponent_podklady_revidovane.md`;
- opponent report review: this is itself a review of a human draft; if an agent also rewrites the report text, run a fresh review pass before treating that rewrite as sendable.

Internal evidence artifacts such as `outputs/revision_diff.md`, `outputs/code_consistency.md`, `outputs/code_quality_review.md`, and `outputs/literature_citation_review.md` must be reviewed before they are relied on as final standalone evidence. A downstream synthesis review certifies only the findings it uses in supervisor feedback or opponent materials; it does not automatically mark the whole evidence artifact final. For standalone final use, a separate evidence-calibration reviewer must check the artifact and the review verdict must be recorded in the artifact, the provenance manifest, or the final response. Record any exception or unavailable review explicitly.

## Output Conventions

Default outputs go into the active round:

- supervisor feedback: `outputs/feedback_student.md`
- supervisor feedback draft for agent-generated first passes: `work/feedback_student_draft.md`
- revision comparison: `outputs/revision_diff.md`
- code consistency check: `outputs/code_consistency.md`
- code quality/design review: `outputs/code_quality_review.md`
- literature/citation review: `outputs/literature_citation_review.md`
- opponent materials: `outputs/oponent_podklady.md`
- reviewed opponent materials: `outputs/oponent_podklady_revidovane.md`
- opponent materials draft for agent-generated first passes: `work/oponent_podklady_draft.md`
- opponent report review: `outputs/feedback_k_posudku.md`

Standalone code consistency, code quality, and literature/citation outputs are internal/operator evidence unless the user explicitly asks to send them. Student-facing feedback should contain only selected, phase-appropriate action items.

Student-facing supervisor feedback must respect `Student feedback language` from `case.md`: default `cs` with Czech diacritics, or explicit `en`. Do not infer feedback language from the thesis language in intake notes.

Before closing a task, run relevant lightweight checks such as `git status --short --untracked-files=all`, `scripts/check-private`, `scripts/check-scripts`, and `git diff --check`. When changing deterministic checkers, run their smoke scripts too. Before sending student-facing supervisor feedback, also run `scripts/check-feedback-language <case-id> [round-id]` and `scripts/check-feedback-output <case-id> [round-id]`. Before relying on reviewed opponent materials, run `scripts/check-opponent-materials <case-id> [round-id]`.
