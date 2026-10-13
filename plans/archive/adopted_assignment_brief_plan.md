# Adopted Assignment Brief Plan

Status: done
Created: 2026-10-13

## Start Here

Done and archived. Both slices landed; residual work is in `TODO.md`. Nothing
here governs pending work.

## Goal

A student's starting brief has one path, whether the assignment was authored in
this pipeline or adopted already issued: a topic case, the bundle review and
approval, `scripts/render-brief`, and `scripts/promote-assignment` into the
thesis case.

## Audit Base

- Two topic cases already adopted an issued assignment ad hoc: their
  `case.md` `Important constraints:` say the IS points are transcribed verbatim
  from the IS PDF and only `Literatura:` is authored; one was promoted into its
  thesis case. Nothing in `docs/assignment-authoring.md`, the
  `thesis-assignment-authoring` or `thesis-assignment-review` skills, or
  `AGENTS.md` names this path (`rg -n -i "adopt|already issued|transcrib"` over
  those files finds only the review skill's unrelated "A human transcribes").
- Four thesis cases instead wrote `rounds/<kickoff>/outputs/student_brief.md`
  inside the thesis case: an internal header, a `---` line, then the student text.
  That path has no skill, no structural check, no approval record, and
  `render-brief` refuses it (`src/thesis_review_workflow/brief_render.py::require_topic_case`).
- Those briefs were written after a first meeting and use extra sections
  (scenarios, what to agree on, further reading). The brief contract enforces the
  required content headings, the forbidden-language bases and uniqueness
  (`src/thesis_review_workflow/cli/check_assignment_draft.py::language_findings`)
  but neither forbids nor defines other headings. The layout filter
  `src/thesis_review_workflow/render/brief/filters/brief-blocks.lua` lifts only
  the content `###` headings to H2, so any other heading keeps its level.
- `TODO.md` item "Let the assignment review roles work on a thesis-review case
  round" asks exactly the question this plan answers (second shape or one path);
  the item "Give a topic-proposal case real tooling." records the friction of
  opening a topic case from an issued PDF (`scripts/new-case` writes only
  thesis-review cases; `scripts/extract-pdf-text` writes only into a round).
- `scripts/promote-assignment --issued` asserts the variant is the student's
  effective assignment AND its brief was supplied
  (`src/thesis_review_workflow/cli/promote_assignment.py::build_parser`);
  `--replace` overwrites the whole thesis-round `notes/assignment.md`, private
  notes and coverage hints included
  (`src/thesis_review_workflow/assignment_promotion.py`).
- The draft gate requires a filled semestral requirement and intake-backed
  literature with resolved identifiers
  (`src/thesis_review_workflow/assignment_draft.py::assignment_findings`).
- No existing topic brief projection carries a heading outside the required set
  (`grep -n "^###\? \|^####" cases/topic-*/outputs/student_brief_*.md`, run
  2026-10-13).

## Scope

In scope: the adoption entry in the authoring workflow, routing that sends every
starting brief through it, and a defined place for free subsections inside the
brief contract.

Not in scope: migrating or re-rendering the four existing thesis-case kickoff
briefs (the operator declined backfill on 2026-10-13); a second render path for
thesis cases; changing the bundle approval schema, promotion, or any thesis
readiness gate; judging assignment quality of an adopted topic.

## Slices

### Slice A - Adoption as an entry to the authoring workflow

Charter form: compacted
Landed: e01ca5d
Documented `## Adopting An Issued Assignment` in `docs/assignment-authoring.md`,
the adoption entry in both assignment skills, the `AGENTS.md` routing and a
README example; removed the resolved review-roles item from `TODO.md`.
Full charter: `plans/archive/adopted_assignment_brief_plan/closed-slices-2026-10-13.md`.
Decisions: `2026-10-13 - Design review`, `2026-10-13 - Design re-check`,
`2026-10-13 - Slice A review`

### Slice B - Free subsections in the brief

- Status: done
- Proposed commit message: Let a starting brief carry its own subsections under the fixed sections
- Why: a brief written after the first meeting needs room for case-specific
  material without breaking the fixed, checkable outline.
- Expected paths: `templates/student-brief.md`, `docs/assignment-authoring.md`,
  `.agents/skills/thesis-assignment-authoring/SKILL.md`,
  `src/thesis_review_workflow/assignment_draft.py`,
  `src/thesis_review_workflow/cli/check_assignment_draft.py`,
  `src/thesis_review_workflow/render/brief/filters/brief-blocks.lua`,
  `tests/test_assignment_draft.py`, `scripts/smoke-render-brief`
- Tasks:
  - Contract: inside a content section or a delta, own subsections are `####`;
    a `###` heading (a bare `###` included) in the shared body, in a delta body or
    in the projection that is not a content heading of the brief language (or, in
    the source under `## Variant Delta`, the wrapper of a declared variant) is a
    structural finding naming `####` as the fix.
  - Layout: the filter renders headings of level 4 and deeper one level up, so a
    subsection sits under its lifted H2 section.
  - Tests for the finding (shared body, source delta, bare marker, no double
    report with the forbidden rule), a passing `####` in a delta, and a smoke
    render asserting a nested outline entry.
- Out of scope: changing the required content headings, their order, or the
  projection shape.
- Verification: `pants test tests/test_assignment_draft.py tests/test_brief_render.py
  tests/test_assignment_authoring.py tests/test_assignment_bundle.py
  tests/test_assignment_promotion.py`; `scripts/smoke-assignment-draft`;
  `scripts/smoke-render-brief` after `scripts/package-workflow-tools`;
  `scripts/check-assignment-draft` on every topic case under `cases/`;
  `pants lint` and `pants check` on the touched Python files.

## Progress

- 2026-10-13: plan written; design review and narrow re-check done (see
  `## Decision Log`).
- 2026-10-13: Slice A done.
- 2026-10-13: Slice B done; plan closed and archived.

## Decision Log

### 2026-10-13 - Direction

The operator chose one path through a topic case over a
render path for thesis cases (chat, 2026-10-13). Why: the starting brief is the
same artifact for the student either way, and the topic path already carries
structure checks, an approval bound by hash, rendering and promotion.

### 2026-10-13 - Design review

`scripts/agent-review --profile plan-critic`,
verdict changes_required, all class (b), all accepted:
- promotion could assert delivery before it happened
  (`promote_assignment.py::build_parser`, `--issued`) -> two stopping points
  in Slice A;
- `--replace` would drop existing private notes and hints
  (`assignment_promotion.py`) -> snapshot and reconcile in Slice A;
- adopted intake minimum and immutable-field stop condition undefined
  (`assignment_draft.py::assignment_findings`) -> defined in Slice A, no
  override. Residual risk: an issued assignment whose immutable fields fail a
  gate gets no rendered brief until a separate plan adds an exception path.

### 2026-10-13 - Design re-check

Narrow re-check of the design-review fix batch (Claude Plan agent, read-only):
B1 blocking, `Variants:` not restricted to the issued variant
(`check_assignment_draft.py::check_case`, `templates/topic-intake.md`
default `bp / dp`) -> one minimum item; N1 `--replace` criterion, N2
`--issued` asserts the exact variant (`promote_assignment.py` `ISSUED_HELP`),
N3 unnamed snapshot path, N4 immutable-field defect classification -> each a
wording fix in Slice A. Stopping rule: B1 is a one-line fix to the minimum,
so no third round; Slice A's own review covers the landed text.

### 2026-10-13 - Slice A review

Claude Plan agent, read-only, `git diff HEAD`: no
blocking findings except `templates/case-notes.md` still saying `Student` stays
empty -> reworded and added to Expected paths. Non-blocking, all applied: an
explicit `Important constraints:` statement as the adopted marker item 9 keys
on; the IS PDF in the review skill's inputs and stated as unbound by the
approval; Claude reviewer records issued-field limitations in its findings;
"verbatim" means field values inside the template structure; first-meeting
material stays in existing sections until Slice B; render on the operator's
request; README asks only for literature to add to IS and names both promotion
conditions. Skipped: a pointer in `templates/assignment.md` (still right for
cases without a starting brief).

### 2026-10-13 - Slice B review

Claude Plan agent, read-only: B1 blocking, any one-word `###` under
`## Variant Delta` passed as a wrapper and cut the delta body
(`assignment_draft.py::_delta_body` stop pattern) -> wrappers are now the
declared variants (`check_case` passes `variants`), test
`test_an_extra_section_heading_inside_a_source_delta_fails`. Applied
non-blocking: bare `###`, the stated reason (`###` is reserved for the
outline), template/doc wording for deltas, smoke regex escaping and the `-`
outline marker, four tests. Not taken: fenced-code false positives (the
forbidden and required rules share that blind spot), a `##` inside the shared
body and `####` before the first section (pre-existing, outside the `###`
rule), Lua headings nested in lists or divs.

### 2026-10-13 - Slice B cross-provider review

`scripts/agent-review` (Codex), verdict changes_required, both class (b),
both accepted: a tab after `###` escaped the rule while `_delta_body` still cut
the delta -> `SECTION_HEADING_RE` accepts any whitespace, test
`test_a_tab_separated_section_heading_in_a_source_delta_fails`; a `###` line in
fenced code blocked a valid brief -> `_outside_fences`, test
`test_a_section_marker_inside_fenced_code_is_not_a_heading`. Fixes are covered
by those tests; no further round (one cross-provider round per the contract).

## Final Audit

- Ran: `pants test tests/test_assignment_draft.py tests/test_brief_render.py
  tests/test_assignment_bundle.py tests/test_assignment_promotion.py
  tests/test_assignment_authoring.py tests/test_plan_contract.py`;
  `pants lint` and `pants check` on the touched Python files;
  `scripts/smoke-assignment-draft`; `scripts/smoke-render-brief` after
  `scripts/package-workflow-tools`; `scripts/check-assignment-draft` on all three
  topic cases under `cases/`; `pants run scripts:omen -- complexity --focus
  src/thesis_review_workflow/assignment_draft.py` (ratchets pass);
  `scripts/check-private`; `scripts/check-scripts`; `git diff --check`.
- Skipped: a native Windows run (the change adds no path, subprocess or
  encoding behaviour; the Lua filter and smoke are platform-neutral apart from
  the POSIX smoke wrapper itself).
- Residual risks: an issued assignment whose immutable fields fail a gate has
  no exception path (`2026-10-13 - Design review`); a `##` heading inside the
  shared body still truncates it silently and topic-case creation is still
  manual, both in `TODO.md`.
- Archive decision: archived, both slices done.
