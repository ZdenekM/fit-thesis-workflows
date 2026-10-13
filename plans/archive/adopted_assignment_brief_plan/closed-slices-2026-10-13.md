# Closed Slices - Adopted Assignment Brief Plan

Full charters moved verbatim from `plans/adopted_assignment_brief_plan.md`.

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
