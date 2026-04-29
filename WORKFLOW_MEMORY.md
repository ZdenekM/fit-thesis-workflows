# Workflow Memory

This file keeps durable workflow lessons, preferences, and rationale that are
useful when evolving the thesis-review workflow. It is not a case archive and
it is not a second instruction system.

Active rules belong in `AGENTS.md`, workflow procedures in `.agents/skills/`,
operator documentation in `README.md`, and future implementation work in
`TODO.md`. Case-specific notes belong under the ignored `cases/<case-id>/`
workspace.

## Rules For This File

- Do not include student names or identifiers, exact case IDs, exact round IDs,
  private thesis excerpts, private supervisor notes, local/workspace paths,
  source archive filenames, generated case outputs, or examples only meaningful
  for one real case.
- Keep entries short and reusable across cases.
- Mark whether a lesson is `candidate`, `promoted`, or `superseded`.
- When a lesson becomes an active rule, promote it into the relevant skill,
  README, AGENTS, template, or TODO item.
- Prefer updating an existing entry over adding near-duplicates.

## Durable Preferences

- Keep the operator workflow simple and conversational; hide packet-level or
  implementation detail unless it helps the current task.
- Keep `AGENTS.md` short. Put reusable procedures into skills, templates, or
  focused docs.
- Preserve repeated-round history and revision diffs as first-class workflow
  evidence.
- Keep real case data private by default; tracked workflow files must not
  contain student PDFs, source zips, extracted thesis text, code submissions, or
  generated case outputs.
- Student-facing feedback should be concrete, supportive, readable, and
  actionable for both student and supervisor.

## Lessons Learned

### 2026-04-29: Submitted PDF Is The Rendered Source Of Truth

Status: promoted

Use the submitted thesis PDF as the authoritative rendered artifact. Use
LaTeX/Overleaf source zips for text diffs, search, and precise evidence. Do not
build LaTeX by default because students often compile on Overleaf and local TeX
failures can reflect the review environment rather than the thesis source.

Promoted to: `AGENTS.md`, `README.md`, supervisor/opponent skills.

### 2026-04-29: Supervisor Notes Are Hypotheses

Status: promoted

Supervisor notes should guide what to verify, not supply text to paste into
student-facing feedback. For each note, verify available evidence, classify the
result privately, and write only the student-relevant synthesis into the final
feedback.

Promoted to: `templates/round-notes.md`, `thesis-supervisor-feedback`,
`thesis-supervisor-feedback-review`, `README.md`.

### 2026-04-29: Student-Facing Feedback Should Avoid Internal IDs

Status: promoted

Student-facing feedback can include a human-readable review date, but should
avoid exact case IDs, round IDs, workspace paths, internal artifact filenames,
and workflow mechanics unless the student needs them to act.

Promoted to: supervisor feedback skills.

### 2026-04-29: Reviewer Profiles Are Active Configuration

Status: promoted

Reviewer profiles capture stable personal preferences, but they are active
workflow configuration rather than workflow memory. Public defaults belong in
`profiles/default.md`; personal overrides stay ignored under `profiles/local/`.

Promoted to: `profiles/README.md`, `README.md`, profile checker, privacy guard.

### 2026-04-29: PDF Detail Layer Before Literature Review

Status: promoted

Keep `pdftotext -layout` as the stable case evidence path. Use `pdf-reader-mcp`
only as an optional targeted detail layer for page ranges, metadata, figures,
tables, layout-sensitive checks, and literature PDFs that need page-local
evidence.

Promoted to: `docs/pdf-detail-layer.md`, README, thesis skills.

## Candidate Improvements

- Add a final feedback output check for required sections, focused priorities,
  explicit scope, evidence for P0/P1 claims, language mode, and generic
  checklist phrasing.
