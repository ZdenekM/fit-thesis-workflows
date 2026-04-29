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

Before generating supervisor feedback or opponent materials, fill the assignment gate:

```text
cases/<case-id>/rounds/<round-id>/notes/assignment.md
```

The round is not ready until it contains the formal assignment and the private assignment notes given to the student:

```bash
scripts/check-round-ready <case-id>
```

Supervisor feedback also uses academic-year deadlines from
`config/supervisor-deadlines.tsv` to calibrate how much can realistically be
asked from the student:

```bash
scripts/check-supervisor-ready <case-id>
scripts/supervisor-deadline <case-id>
```

For deferred or August-defense cases, put the exact case-specific submission
date into `case.md` as `Deadline override: YYYY-MM-DD`.

Then work in chat/Codex by pointing the agent at the case and asking for the relevant artifact, for example:

```text
Pouzij skill thesis-supervisor-feedback pro cases/novak-bp-2026. Pri dostupnem kodu pouzij thesis-code-consistency i thesis-code-quality-review, udelej i kriticky druhy pruchod podle thesis-supervisor-feedback-review a final uloz do aktualniho roundu.
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
  # and Student feedback language: cs / en
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

## Main Workflows

- `thesis-supervisor-feedback`: iterative student-facing feedback for a supervised BP/DP.
- `thesis-supervisor-feedback-review`: critical second pass before sending supervisor feedback.
- `thesis-revision-diff`: compare two rounds and identify what changed and what prior feedback remains.
- `thesis-code-consistency`: check whether thesis claims match code, README, tests, configs, and reproducibility evidence.
- `thesis-code-quality-review`: review implementation quality, architecture/design, maintainability, runtime risks, developer documentation, and smoke-test readiness.
- `thesis-opponent-materials`: prepare internal materials for an opponent report.
- `thesis-opponent-materials-review`: review and harden generated opponent materials before writing the report.
- `thesis-opponent-report-review`: review your own draft opponent report for fairness, evidence, tone, and consistency.

The canonical workflow definitions live in `.agents/skills/*/SKILL.md`.

When a round contains code, supervisor feedback and opponent materials must run both `thesis-code-consistency` and `thesis-code-quality-review`, or state why one of those checks could not be performed from the available inputs. Archives in `inputs/` count as code; make them inspectable under `work/code/` before delegating to read-only reviewers, or record the limitation. Standalone code-check artifacts such as `outputs/code_consistency.md` and `outputs/code_quality_review.md` are internal/operator evidence, not student-facing output by default.

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

Check readiness before asking Codex to generate the artifact:

```bash
scripts/check-supervisor-ready <case-id>
```

Use this prompt in Codex:

```text
Pouzij thesis-supervisor-feedback pro cases/<case-id>. Projdi aktualni round, zohledni predchozi feedback, pri dostupnem kodu pouzij thesis-code-consistency i thesis-code-quality-review, udelej kriticky druhy pruchod a uloz final do outputs/feedback_student.md.
```

Before sending supervisor feedback, validate the configured output-language heading structure:

```bash
scripts/check-feedback-language <case-id>
```

This is a deterministic heading/structure guard. Still review the body text language, tone, and content manually before sending.

For the first opponent test, use:

```text
Pouzij thesis-opponent-materials pro cases/<case-id>, pri dostupnem kodu pouzij thesis-code-consistency i thesis-code-quality-review, potom thesis-opponent-materials-review. Vystup uloz jako outputs/oponent_podklady_revidovane.md.
```

Before committing workflow changes, run the lightweight hygiene checks relevant to the files touched:

```bash
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
