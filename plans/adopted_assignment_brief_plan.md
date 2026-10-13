# Adopted Assignment Brief Plan

Status: in_progress
Created: 2026-10-13

## Start Here

Slice A (documentation) has landed. Next action: compact Slice A's charter into
`plans/archive/adopted_assignment_brief_plan/`, write nothing new into it, and
implement Slice B as chartered below. Read only this plan,
`docs/assignment-authoring.md` and the two skills Slice A names; nothing is
archived yet.

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

- Status: done
- Proposed commit message: Route every starting brief through a topic case, adopted assignments included
- Why: agents improvised two different paths for an assignment issued outside the
  pipeline; the one that bypasses the topic case produces an unchecked,
  unapproved, unrenderable brief.
- Expected paths: `docs/assignment-authoring.md`,
  `.agents/skills/thesis-assignment-authoring/SKILL.md`,
  `.agents/skills/thesis-assignment-review/SKILL.md`, `AGENTS.md`, `README.md`,
  `templates/topic-intake.md`, `templates/case-notes.md`,
  `docs/operator-reference.md`, `TODO.md`
- Tasks:
  - `docs/assignment-authoring.md`: new `## Adopting An Issued Assignment`
    after `## The Topic Case`: the topic case is opened for an assignment already
    issued in IS; the formal assignment is transcribed verbatim from the IS PDF
    kept in the topic case `inputs/`; only fields the operator may still edit in
    IS (typically `Literatura:`) are authored; the intake records the issued
    points as the assessable criteria and the supervisor's reading as the
    interpretation; `Student:` in the topic `case.md` is filled once the student
    is known, and `## The Topic Case`'s "no student" wording is reconciled with
    that.
  - Adopted intake minimum: `Variants:` names only the issued variant; the
    issued points as `### Assessable As An
    Assignment Point`, the supervisor's reading as `### Interpretation For The
    Student`, every literature entry the assignment will carry (issued or newly
    authored) as a citable artifact, `## Motivation` and `## Context And Starting
    Point` from the issued text and the operator.
  - Immutable content: a transcription or brief defect is fixed; a defect in an
    issued field the operator cannot edit in IS is reported as a limitation in the
    review, not re-authored. If such a field fails a deterministic gate of
    `scripts/check-assignment-draft`, the workflow stops and asks the operator;
    there is no override (an exception path would be a separate plan).
  - Two stopping points, kept apart: rendering the approved brief is a valid end
    of the preparation; `scripts/promote-assignment --issued` runs only after the
    operator confirms that the brief was delivered and that the IS assignment now
    matches the approved variant, and `--issued-note` records that date and state.
  - Existing thesis-round `notes/assignment.md` (every round has one from its
    template): before `--replace`, copy it to
    the round's `work/assignment_source/`, named like the approval copy promotion
    retains there (`assignment_promotion.py::RETAINED_APPROVAL_DIR`); pass `--replace`
    only once the operator confirms the promoted variant supersedes it (an
    unfilled template counts as superseded); after promotion, carry over any
    private notes and coverage hints it held that the new file lacks.
  - State there that a starting brief is never authored inside a thesis case.
  - Skill `thesis-assignment-authoring`: an adoption entry point naming the
    differences above; the review skill: an adopted variant's points are checked
    for verbatim transcription, not re-authored, and a defect in an issued field
    the operator cannot edit goes into the approval's `limitations`, never into
    its blocking findings.
  - `AGENTS.md` `## Skill Routing`: the authoring skill line covers a starting
    brief for an adopted assignment too.
  - `README.md` chat-first examples: one prompt for "student already has an
    issued assignment, prepare the starting brief".
  - `templates/topic-intake.md`: one line pointing at the adopted intake minimum.
  - `TODO.md`: delete the "Let the assignment review roles work on a
    thesis-review case round" item, resolved by this decision; leave the topic
    case creation item open and point the adoption section at it.
- Out of scope: any code change (topic case creation tooling stays in `TODO.md`);
  an exception path for issued content that fails a gate; Slice B's subsection
  contract.
- Verification: `pants test tests/test_assignment_authoring.py tests/test_plan_contract.py`;
  `scripts/check-private`; `git diff --check`.

### Slice B - Free subsections in the brief

- Status: planned
- Proposed commit message: Let a starting brief carry its own subsections under the fixed sections
- Why: a brief written after the first meeting needs room for case-specific
  material without breaking the fixed, checkable outline.
- Expected paths: `templates/student-brief.md`, `docs/assignment-authoring.md`,
  `src/thesis_review_workflow/assignment_draft.py`,
  `src/thesis_review_workflow/cli/check_assignment_draft.py`,
  `src/thesis_review_workflow/render/brief/filters/brief-blocks.lua`,
  `tests/test_assignment_draft.py`, `tests/test_brief_render.py`,
  `scripts/smoke-assignment-draft`, `scripts/smoke-render-brief`
- Tasks:
  - Contract: inside a content section, own subsections are `####`; a `###`
    heading in the shared body, in a delta body or in the projection that is not
    a content heading of the brief language (or, in the source, the `### <variant>`
    delta wrapper) is a structural finding naming `####` as the fix.
  - Layout: the filter renders headings of level 4 and deeper one level up, so a
    subsection sits under its lifted H2 section.
  - Tests for the finding (source and projection) and a smoke render containing a
    `####` subsection.
- Out of scope: changing the required content headings, their order, or the
  projection shape.
- Verification: `pants test tests/test_assignment_draft.py tests/test_brief_render.py`;
  `scripts/smoke-assignment-draft`; `scripts/smoke-render-brief`;
  `pants lint` and `pants check` on the touched Python files.

## Progress

- 2026-10-13: plan written; design review and narrow re-check done (see
  `## Decision Log`).
- 2026-10-13: Slice A done; Slice B next.

## Decision Log

- 2026-10-13 direction: the operator chose one path through a topic case over a
  render path for thesis cases (chat, 2026-10-13). Why: the starting brief is the
  same artifact for the student either way, and the topic path already carries
  structure checks, an approval bound by hash, rendering and promotion.

- 2026-10-13 design review (`scripts/agent-review --profile plan-critic`,
  verdict changes_required), all class (b), all accepted:
  - promotion could assert delivery before it happened
    (`promote_assignment.py::build_parser`, `--issued`) -> two stopping points
    in Slice A;
  - `--replace` would drop existing private notes and hints
    (`assignment_promotion.py`) -> snapshot and reconcile in Slice A;
  - adopted intake minimum and immutable-field stop condition undefined
    (`assignment_draft.py::assignment_findings`) -> defined in Slice A, no
    override. Residual risk: an issued assignment whose immutable fields fail a
    gate gets no rendered brief until a separate plan adds an exception path.
- 2026-10-13 narrow re-check of that fix batch (Claude Plan agent, read-only):
  B1 blocking, `Variants:` not restricted to the issued variant
  (`check_assignment_draft.py::check_case`, `templates/topic-intake.md`
  default `bp / dp`) -> one minimum item; N1 `--replace` criterion, N2
  `--issued` asserts the exact variant (`promote_assignment.py` `ISSUED_HELP`),
  N3 unnamed snapshot path, N4 immutable-field defect classification -> each a
  wording fix in Slice A. Stopping rule: B1 is a one-line fix to the minimum,
  so no third round; Slice A's own review covers the landed text.

- 2026-10-13 Slice A review (Claude Plan agent, read-only, `git diff HEAD`): no
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

## Final Audit

Not yet run.
