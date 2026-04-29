# FIT Thesis Workflows

Minimal Codex-first workflow for BP/DP supervision and opponent work.

The repository stores workflow instructions, skills, templates, and tiny helper scripts. Real thesis data stays inside `cases/`, which is ignored by git.

## Quick Start

Create a local case:

```bash
scripts/new-case novak-bp-2026 BP first-review
```

Add another revision later:

```bash
scripts/import-round novak-bp-2026 second-review ~/Downloads/thesis.pdf ~/Downloads/student-code.zip
```

`import-round` copies inputs into the ignored case workspace and extracts PDF text into `extracted/` when `pdftotext` is available.

Treat the submitted PDF as the rendered thesis source of truth. LaTeX/Overleaf
source zips are useful for text diffs, search, and precise evidence, but the
workflow does not build them by default. Ask for a build only when you
explicitly want compile diagnostics or no rendered PDF is available.

For PDF details that plain text extraction cannot answer, optionally configure
`pdf-reader-mcp`:

```bash
codex mcp add pdf-reader -- npx @sylphx/pdf-reader-mcp
```

It requires Node.js 22 or newer. Keep `pdftotext -layout` as the default
case-evidence path; use the MCP only for targeted page ranges, metadata, page
counts, figures, tables, layout-sensitive checks, or ambiguous extraction.
See `docs/pdf-detail-layer.md`.

Before generating supervisor feedback or opponent materials, fill the assignment
context:

```text
cases/<case-id>/rounds/<round-id>/notes/assignment.md
```

For supervisor feedback, `check-supervisor-ready` is the gate. It verifies the
round assignment context and adds deadline calibration:

```bash
scripts/check-supervisor-ready <case-id>
scripts/supervisor-deadline <case-id>
```

For opponent materials or generic internal round checks, use `check-round-ready`.
It verifies the formal assignment and private assignment notes, but it does not
perform supervisor deadline calibration:

```bash
scripts/check-round-ready <case-id>
```

For deferred or August-defense cases, put the exact case-specific submission
date into `case.md` as `Deadline override: YYYY-MM-DD`.

Then work in chat/Codex by pointing the agent at the case and asking for the relevant artifact, for example:

```text
Pouzij skill thesis-supervisor-feedback pro cases/novak-bp-2026. Pri dostupnem kodu pouzij thesis-code-consistency i thesis-code-quality-review. Prvni agentni navrh uloz do work/feedback_student_draft.md; potom pouzij jineho reviewer agenta nebo reviewer roli s thesis-supervisor-feedback-review a teprve reviewed final uloz do outputs/feedback_student.md.
```

## Case Workspace

Case data is stored under:

```text
cases/<case-id>/
```

Each case can contain multiple rounds:

```text
cases/<case-id>/
  case.md
  # includes Work type, Academic year, Deadline mode, optional Deadline override,
  # Student feedback language: cs / en, and Reviewer profile
  current-round.txt
  rounds/
    20260428-1530-first-review/
      notes/
      inputs/
      extracted/
      work/
      outputs/
    20260510-1015-second-review/
      ...
```

For supervisor feedback, the current round must take previous feedback into account. Earlier `outputs/feedback_student.md` files are part of the input and should be used to avoid repeating resolved feedback.

Student-facing supervisor feedback uses `Student feedback language` from `case.md`. Missing or empty means `cs`, which requires Czech output with diacritics. Use `en` only when English feedback is preferable. `Jazyk prace` in intake notes describes the thesis language and does not control feedback language.

Reviewer preferences are selected by `Reviewer profile` in `case.md`. Missing
or empty means `default`. The public repository contains only the generic
`profiles/default.md`; personal profiles and local overrides belong exclusively
under ignored paths such as `profiles/local/default.md` or
`profiles/local/<profile-id>.md`. Use `Reviewer profile: local/<profile-id>` in
`case.md` only when that private file exists locally.

Profiles are preference layers, not hard workflow rules. They can shape tone,
priority count, strictness calibration, and domain emphasis, but they cannot
override privacy, evidence requirements, assignment/deadline gates, output
language checks, or the obligation to state what was not checked. Validate the
effective profile files with:

```bash
scripts/check-reviewer-profile <case-id>
```

Put supervisor observations for the current round into `notes/round-notes.md`
under `Supervisor Notes to Verify`. Treat them as hypotheses for Codex to
check, expand, or reject against the thesis and artifacts, not as text to copy
directly into `outputs/feedback_student.md`. Example: `For SUS and similar
averages, check whether the thesis should include standard deviation or
variance; if the questionnaire has useful free-text responses, consider short
anonymized quotes or a theme summary.`

## Main Workflows

- `thesis-supervisor-feedback`: iterative student-facing feedback for a supervised BP/DP.
- `thesis-supervisor-feedback-review`: critical second pass before sending supervisor feedback.
- `thesis-revision-diff`: compare two rounds and identify what changed and what prior feedback remains.
- `thesis-code-consistency`: check whether thesis claims match code, README, tests, configs, and reproducibility evidence.
- `thesis-code-quality-review`: review implementation quality, architecture/design, maintainability, runtime risks, developer documentation, and smoke-test readiness.
- `thesis-literature-citation-review`: review cited literature relevance, source availability, and whether citations support thesis claims.
- `thesis-opponent-materials`: prepare internal materials for an opponent report.
- `thesis-opponent-materials-review`: review and harden generated opponent materials before writing the report.
- `thesis-opponent-report-review`: review your own draft opponent report for fairness, evidence, tone, and consistency.

The canonical workflow definitions live in `.agents/skills/*/SKILL.md`.
Durable workflow lessons and rationale live in `WORKFLOW_MEMORY.md`; promote
anything operational from there into the relevant skill, template, README,
AGENTS, or TODO entry before relying on it as an active rule.

Agent-generated Markdown under `outputs/` is treated as ready only after an
independent review loop. The loop terminates when a different reviewer agent or
reviewer role checks the draft/evidence and writes or approves the reviewed
target artifact; later material edits reopen the draft state. Supervisor
feedback uses the `thesis-supervisor-feedback` ->
`thesis-supervisor-feedback-review` loop. Opponent materials use the
`thesis-opponent-materials` -> `thesis-opponent-materials-review` loop.
Internal evidence artifacts such as `outputs/revision_diff.md`,
`outputs/code_consistency.md`, `outputs/code_quality_review.md`, and
`outputs/literature_citation_review.md` are final standalone evidence only
after a separate evidence-calibration review or an explicit recorded verdict.
Downstream synthesis review certifies only the findings used in that synthesis.

When a round contains code, supervisor feedback and opponent materials must run both `thesis-code-consistency` and `thesis-code-quality-review`, or state why one of those checks could not be performed from the available inputs. Archives in `inputs/` count as code; make them inspectable under `work/code/` before delegating to read-only reviewers, or record the limitation. Standalone code-check artifacts such as `outputs/code_consistency.md` and `outputs/code_quality_review.md` are internal/operator evidence, not student-facing output by default.

For thesis text review, use the submitted PDF as the rendered artifact. Use
LaTeX sources for structural diffs and exact snippets, not as a build target by
default.

For literature-heavy checks, use `thesis-literature-citation-review`. It writes
`outputs/literature_citation_review.md` as internal evidence and stores any
downloaded papers or metadata cache only under the ignored case workspace.
Supervisor workflows may use it to suggest better use of already cited work or
new literature for a clear gap. Opponent workflows should use it only for
relevance, defensibility, and citation-quality checks of the submitted work.

## First Real Test

For the first supervised-thesis test:

```bash
scripts/new-case <case-id> BP first-review
scripts/import-round <case-id> first-materials /path/to/prace.pdf /path/to/code-or-zip
```

Then fill the most important fields:

```text
cases/<case-id>/case.md
cases/<case-id>/rounds/<round-id>/notes/assignment.md
cases/<case-id>/rounds/<round-id>/notes/supervisor-intake.md
cases/<case-id>/rounds/<round-id>/notes/round-notes.md
```

Put current supervisor hypotheses under `Supervisor Notes to Verify` in
`round-notes.md`; the skills verify and synthesize them before they reach
student-facing feedback.

Check readiness before asking Codex to generate the artifact:

```bash
scripts/check-supervisor-ready <case-id>
```

Use this prompt in Codex:

```text
Pouzij thesis-supervisor-feedback pro cases/<case-id>. Projdi aktualni round, zohledni predchozi feedback, pri dostupnem kodu pouzij thesis-code-consistency i thesis-code-quality-review. Prvni agentni navrh uloz do work/feedback_student_draft.md; potom pouzij jineho reviewer agenta nebo reviewer roli s thesis-supervisor-feedback-review a uloz reviewed final do outputs/feedback_student.md.
```

Before sending supervisor feedback, validate the configured output-language heading structure:

```bash
scripts/check-feedback-language <case-id>
```

This is a deterministic heading/structure guard. Still review the body text language, tone, and content manually before sending.

For the first opponent test, use:

```text
Pouzij thesis-opponent-materials pro cases/<case-id>, pri dostupnem kodu pouzij thesis-code-consistency i thesis-code-quality-review. Prvni agentni navrh uloz do work/oponent_podklady_draft.md; potom pouzij jineho reviewer agenta nebo reviewer roli s thesis-opponent-materials-review a uloz reviewed vystup jako outputs/oponent_podklady_revidovane.md.
```

Before committing workflow changes, run the lightweight hygiene checks relevant to the files touched:

```bash
git status --short --untracked-files=all
git diff --check
git diff --cached --check
scripts/check-private
scripts/check-scripts
```

When touching `.codex/agents/*.toml` or Python hooks, also parse the TOML and compile the hook files before committing.

## Codex Helpers

This repo also defines lightweight Codex helpers:

- `.codex/agents/*`: suggested read-only reviewer roles for thesis text, code consistency, code quality, and evidence calibration.
- `.codex/hooks.json`: session reminders and a privacy guard that blocks accidental `git add` of ignored case data.

## Privacy Check

Before committing workflow changes:

```bash
scripts/check-private
git status --short
```

Only workflow files should appear in git. Case contents under `cases/<case-id>/` must remain ignored.
