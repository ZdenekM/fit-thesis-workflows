# Assignment IS Export Check Plan

Status: done
Created: 2026-10-29

## Start Here

State: done. Slice A (rules) landed in `30d09e2`, Slice B (the export
checker) in the commit that archived this plan. The head of department's first
round of rules landed in commit `3cf49aa`; this plan added the second round.

Next action: none. Open operator questions are case matters, not plan work.

## Goal

An assignment filed in FIT IS passes the head of department's approval check
the first time: the rules he announced for 2026/27 are written where authors
and reviewers read them, and the structural ones are checked deterministically
on the PDF that FIT IS exports, before the assignment is submitted for
approval.

## Audit Base

- The head of department's ÚPGM assignment check (2026-10) returned two
  assignments and circulated a list of recurring defects. One return was a
  title with an evaluative adjective; the other was points pasted into FIT IS
  as plain text `1. …` instead of a numbered list. Both cases are private and
  stay under `cases/`.
- The first round of his rules lives in `profiles/default.md`
  `## Assignment Authoring Style` ("What the head of department checks before
  approving") and is walked by `.agents/skills/thesis-assignment-review/SKILL.md`.
- `scripts/check-assignment-draft` checks the Markdown bundle, not what FIT IS
  stores. Nothing reads the exported PDF, which is the artifact the head of
  department actually sees.
- FIT IS exports one PDF per assignment. `pdftotext -layout` of it keeps the
  structure that matters: labels at column 0, a numbered list as numbers
  indented past the label with a hanging indent, literature as `•` items, one
  form feed per page. Measured on the operator's private exports: 36 September
  exports, two correct and one defective October re-export of one assignment,
  and one English export from 2025/26.
- The form's labels already have one source:
  `src/thesis_review_workflow/assignment_draft.py::RENDERINGS`, mirrored by
  `templates/assignment-formal.md`. `src/thesis_review_workflow/brief_render.py::TITLE_LABEL`
  duplicates the title label.
- Command contract: `docs/workflow-command-surface.md`
  `### Operator Workflow Tools`; model tool `check-assignment-draft`.

## Scope

In scope: the institutional rules in layer 2, the FIT IS filing procedure in
the formal template, the authoring contract and both assignment skills, and a
new operator tool `check-assignment-export` with its command-surface wiring and
tests.

Out of scope: any check of free-form wording (an evaluative title adjective is
a reading rule, per `AGENTS.md`); the FIT IS field `Komentář k zadání (netiskne
se)` as a workflow artifact (`TODO.md`); a check of the `Zobrazit studentům`
checkbox, which the export does not show; private case data in tracked files.

## Slices

### Slice A - Head-of-department rules for FIT IS filing

- Status: done (landed in `30d09e2`; the cross-provider round covered it with
  Slice B)
- Proposed commit message: Record the head of department's second round of assignment rules
- Why: the rules exist only in an e-mail; authors and reviewers read layer 2
  and the review skill.
- Expected paths: `profiles/default.md`, `templates/assignment-formal.md`,
  `docs/assignment-authoring.md`, `.agents/skills/thesis-assignment-review/SKILL.md`,
  `TODO.md`, `plans/assignment_is_export_check_plan.md`
- Tasks: extend "What the head of department checks before approving" with
  format in IS, one page, the CZ/EN switch, the semestral field and its
  exception, `Zobrazit studentům`, complete and current literature, no
  assignment given twice, and no evaluative title adjectives; add the
  currency calibration to `## Literature Selection And Currency`; walk the new
  items in the review skill, including a comparison with the supervisor's
  other active assignments; state the filing procedure in the template
  without asserting unverified editor behavior.
- Out of scope: anything that names `check-assignment-export` (Slice B).
- Verification: `pants test tests/test_assignment_authoring.py`,
  `python3 tests/test_plan_contract.py`, `scripts/check-private`,
  `scripts/check-scripts`, `git diff --check`.

### Slice B - check-assignment-export

- Status: done
- Proposed commit message: Check the assignment PDF exported from FIT IS before approval
- Why: the defect the head of department returned is invisible in the Markdown
  bundle and visible in the export.
- Expected paths: `src/thesis_review_workflow/assignment_export.py`,
  `src/thesis_review_workflow/assignment_draft.py`,
  `src/thesis_review_workflow/brief_render.py`,
  `src/thesis_review_workflow/cli/check_assignment_export.py`,
  `src/thesis_review_workflow/cli/BUILD`, `src/thesis_review_workflow/commands.py`,
  `scripts/check-assignment-export`, `scripts/BUILD`,
  `tests/test_assignment_export.py`, `tests/test_brief_render.py`,
  `profiles/default.md`, `docs/assignment-authoring.md`,
  `docs/workflow-command-surface.md`, `docs/operator-reference.md`,
  `templates/assignment-formal.md`, `.agents/skills/thesis-assignment-authoring/SKILL.md`,
  `.agents/skills/thesis-assignment-review/SKILL.md`, this plan (moved to
  `plans/archive/`)
- Tasks: a pure parser over `pdftotext -layout` text checking page count,
  header and `--language`, a non-empty title, the points as a real numbered
  list (indented past the label, hanging indent, no number alone on a line,
  consecutive numbering), literature as `•` items with indented continuation,
  and a filled semestral field unless `--allow-empty-semestral`; labels read
  from `RENDERINGS`, which gains the title label and the guidelines line; the
  CLI runs `pdftotext` per PDF; wiring per the command contract; synthetic
  layout-text tests; docs naming the tool.
- Out of scope: reading or judging wording; parsing the footer dates.
- Verification: `pants lint` and `pants check` on the changed Python files,
  `pants test tests/test_assignment_export.py`,
  `pants test tests/test_workflow_python_contracts.py`,
  `pants test tests/test_assignment_draft.py`,
  `pants test tests/test_brief_render.py`, `pants run scripts:omen --
  complexity --focus src/thesis_review_workflow/assignment_export.py`,
  `python3 tests/test_plan_contract.py`, `scripts/check-private`,
  `scripts/check-scripts`, `git diff --check`; a local run over the private
  exports described in `## Audit Base`, results recorded without case data.

## Progress

- 2026-10-29: plan created; Slice A started. Slice A reviewed once (internal
  Claude round); fixes applied; Slice B implementation started in parallel in
  files Slice A does not touch.
- 2026-10-29: Slice A committed (`30d09e2`). Slice B implemented: parser,
  CLI, wiring, tests, docs. Targeted Pants tests green; Omen advisory: the new
  module's worst function is 12 cyclomatic, repo ratchets pass. Local run over
  the private exports: all 36 September exports are one page, 22 fail (5 with
  no semestral field, 11 with a number alone on its line, 6 with literature
  outside a list); the defective October re-export fails (two pages, points at
  the margin); both corrected October exports and one English export pass.

## Decision Log

- 2026-10-29: Two slices, rules before the tool, so the rules commit names no
  command that does not exist yet. The filing procedure states only what the
  operator did to fix the returned assignment; whether the FIT IS editor turns
  pasted `- ` lines into bullets by itself is unconfirmed and stays out of the
  docs until the operator answers.
- 2026-10-29: Slice A review, one internal Claude round over the plan and the
  Slice A diff; nothing blocking. Accepted, class (b): the semestral field is in
  the bundle and checked by `scripts/check-assignment-draft`, so it left the
  "bundle cannot show" group and its exception applies only when filing for a
  known student; language and `Zobrazit studentům` were missing from the two
  rule groups; item 12 of the review skill now names its case selectors and
  defers to item 9 for issued fields. Accepted, class (c), fixed in place:
  wording nits, one-line IS labels, plan scope and verification. Process
  deviation recorded rather than repaired: Slice B code started before the
  Slice A commit, in files outside Slice A's paths, and its charter was read in
  this round (one prose finding) rather than in a separate charter review.
- 2026-10-29: Slice B shape. The command takes PDF paths, not a case id, so any
  export is checkable wherever it lies; `--language` stays optional for mixed
  batches and its absence is printed; there is no override, a failure is fixed
  in FIT IS. The header and the footer's opening line join `RENDERINGS`, and
  `brief_render.py::TITLE_LABEL` is removed in favour of `Rendering.title_label`.
- 2026-10-29: Slice B review, one internal Claude round; nothing blocking.
  Accepted, class (b): a marker typed into a list item (`1. 1.`, `• -`) passed,
  now a finding; an empty semestral field accepted under the flag is printed
  per file; only later labels end a field, so semestral text that starts like a
  label stays content; the header match collapses whitespace and reads `’` as
  `'`; text on a label's line is reported alone. Accepted, class (c): line
  lengths, messages, missing tests (header column, CRLF, empty labelled field),
  the review skill's `Zobrazit studentům` exception, doc placement. Rejected as
  out of scope: console encoding of the packaged Windows launchers, which
  predates this plan.
- 2026-10-29: Cross-provider round (`scripts/agent-review --base d4521d8
  --profile final-review`, over both slices): changes_required, three P2,
  all accepted as class (b). Exact column comparison could fail a correct
  export because `pdftotext` rounds positions; columns now compare with a
  tolerance of one (`assignment_export.py::COLUMN_TOLERANCE`). A bare bullet
  passed as a filled semestral field; a bare list marker is no value now
  (`assignment_export.py::_content`). The docs claimed sub-lists fail; they are
  now documented as not modelled and pinned by
  `test_a_sub_list_is_read_by_its_columns_only`. Each fix has a regression
  test; one narrow re-check of this batch only.

## Final Audit

Passed for Slice B on the final tree: `pants lint` (black, flake8, isort) and
`pants check` (mypy) on the changed source files; `pants test` for
`tests/test_assignment_export.py`, `tests/test_workflow_python_contracts.py`,
`tests/test_assignment_authoring.py`, `tests/test_assignment_draft.py`,
`tests/test_brief_render.py`, `tests/test_assignment_bundle.py`,
`tests/test_assignment_promotion.py` and `tests/test_plan_contract.py`;
`python3 tests/test_plan_contract.py`, `scripts/check-private`,
`scripts/check-scripts`, `git diff --check`. Omen advisory: worst function of
the new module 13 cyclomatic, repo ratchets pass. Slice A passed its own
verification before `30d09e2`.

Not clean, and predating this plan: `pants check` on the test files reports
missing `pytest` stubs in every test and an `arg-type` error in
`tests/test_assignment_bundle.py`; source files are clean. Native Windows
execution and packaged launchers were not run.

Local run over the private exports described in `## Audit Base`, unchanged
after every fix batch: 36 September exports, all one page, 22 fail (5 with no
semestral field, 11 with a number alone on its line, 6 with literature outside
a list); the defective October re-export fails (two pages, points at the
margin, lines that do not hang); both corrected October exports and one English
2025/26 export pass.

Reviews: Slice A one internal round; Slice B one internal round; one
cross-provider round over both slices; one narrow re-check of its fix batch,
which found nothing blocking and four nits, fixed in place.

Residual risks: the geometry limits stated in `docs/assignment-authoring.md`
`## Filing In FIT IS`; one English export measured; whether the FIT IS editor
turns pasted `- ` lines into bullets by itself is unconfirmed, so the template
prescribes the list buttons either way. No TODO item is opened. The plan moved
to `plans/archive/assignment_is_export_check_plan.md`.
