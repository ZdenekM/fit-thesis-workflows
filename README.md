# diplomky_v2

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
Pouzij skill thesis-supervisor-feedback pro cases/novak-bp-2026. Udelej i kriticky druhy pruchod podle thesis-supervisor-feedback-review a final uloz do aktualniho roundu.
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
  # includes Work type, Academic year, Deadline mode, and optional Deadline override
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

## Main Workflows

- `thesis-supervisor-feedback`: iterative student-facing feedback for a supervised BP/DP.
- `thesis-supervisor-feedback-review`: critical second pass before sending supervisor feedback.
- `thesis-revision-diff`: compare two rounds and identify what changed and what prior feedback remains.
- `thesis-code-consistency`: check whether thesis claims match code, README, tests, configs, and reproducibility evidence.
- `thesis-opponent-materials`: prepare internal materials for an opponent report.
- `thesis-opponent-materials-review`: review and harden generated opponent materials before writing the report.
- `thesis-opponent-report-review`: review your own draft opponent report for fairness, evidence, tone, and consistency.

The canonical workflow definitions live in `.agents/skills/*/SKILL.md`.

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
Pouzij thesis-supervisor-feedback pro cases/<case-id>. Projdi aktualni round, zohledni predchozi feedback, pouzij pripadne role text/code/evidence, udelej kriticky druhy pruchod a uloz final do outputs/feedback_student.md.
```

For the first opponent test, use:

```text
Pouzij thesis-opponent-materials pro cases/<case-id>, potom thesis-opponent-materials-review. Vystup uloz jako outputs/oponent_podklady_revidovane.md.
```

Before committing workflow changes, run:

```bash
scripts/check-private
```

## Codex Helpers

This repo also defines lightweight Codex helpers:

- `.codex/agents/*`: suggested read-only reviewer roles for thesis text, code consistency, and evidence calibration.
- `.codex/hooks.json`: session reminders and a privacy guard that blocks accidental `git add` of ignored case data.

## Privacy Check

Before committing workflow changes:

```bash
scripts/check-private
git status --short
```

Only workflow files should appear in git. Case contents under `cases/<case-id>/` must remain ignored.
