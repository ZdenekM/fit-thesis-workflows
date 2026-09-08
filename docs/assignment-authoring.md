# Assignment Authoring

This document is the operator contract for turning an unstructured topic idea
into a publishable FIT IS assignment and a brief the student can start from.
Everything else in this repository measures a thesis *against* an assignment;
this is the one workflow that produces one.

Because `notes/assignment.md` is what `scripts/check-assignment-coverage`,
supervisor feedback, opponent materials, and the `Rozsah splneni pozadavku
zadani` rubric item in `docs/fit-is-rubric.md` all resolve against, the
governing question for a newly authored assignment is: *could this repository's
own opponent pipeline evaluate a finished thesis against it.* An assignment
point that is not verifiable returns a year later as an ungradable fulfillment
claim.

## The Topic Case

Assignment authoring happens in its own case under ignored `cases/`, marked by
`Case kind: topic-proposal` in `case.md`. `Case kind` defaults to
`thesis-review` when the field is absent, so existing cases are unaffected. A
topic-proposal case has no student, no work type, and no deadline; the thesis
readiness gates do not apply to it and are not run against it.

The accepted values live once in
`thesis_review_workflow.metadata::CASE_KINDS`, read through
`thesis_review_workflow.metadata::case_kind`.

## The Variant Bundle

A topic carries N assignment variants — today `bp` and `dp`. The variant is a
first-class identifier, not a filename suffix. Per topic there is one intake;
per variant there is one assignment, one brief, one approval record, and one
promotion.

```text
cases/<topic-case-id>/
  case.md                                  Case kind: topic-proposal
  notes/topic_intake.md                    source, from templates/topic-intake.md
  notes/student_brief.md                   source, from templates/student-brief.md
  outputs/assignment_formal_<variant>.md   from templates/assignment-formal.md
  outputs/student_brief_<variant>.md       projection of notes/student_brief.md
```

Two of these are per-topic SOURCES and are never sent anywhere: the intake and
the brief source. The outputs are per-variant. An assignment is authored
directly as an output, one file per variant, because the whole document differs.
A brief is not: `outputs/student_brief_<variant>.md` is a **projection** of
`notes/student_brief.md` — its shared body verbatim, plus that one variant's
delta, and nothing of the other variant. Authoring two whole briefs is the
drift this shape exists to prevent; in the probe roughly 85% of two briefs for
one topic was identical text.

Artifact names are language-neutral because both artifacts have a configurable
output language, so a Czech filename would misname the English case.

Shared material is authored once in the intake and must appear byte-identically
in every variant that uses it — literature entries above all. In the corpus, one
BP/DP pair sharing three literature entries cited two of them differently
between the variants; a variant-aware structure is what makes that mechanically
checkable.

`Depends on topic:` in the intake means another topic must exist or be taken
first. It is *not* the same as sibling exclusion: two topics offered in the same
round that a student must not take together are recorded under
`### Sibling Topics This One Excludes`. The distinction matters because a
dependency is a supervision risk while an exclusion is an offering rule.

## Three Style Layers

Only the first layer is fixed.

1. **School form** — the FIT IS field set and its order, in both the Czech and
   the English rendering. Tracked in `templates/assignment-formal.md`. Not a
   preference.
2. **Generic quality base** — `## Assignment Authoring Style` in
   `profiles/default.md`. Derived from what a cross-supervisor corpus attests
   as institutional norm plus documented FIT rules, never from one supervisor.
3. **Personal style** — the same section in an ignored
   `profiles/local/<profile-id>.md`: wording, literature-entry conventions,
   semester-requirement phrasing, BP/DP variant construction, preferred
   categories, and the supervision conventions rendered into a brief. Absent
   section means the generic base applies unchanged.

`profiles/README.md` `## Assignment Authoring Boundary` owns the rule for what
may enter the tracked default. Factual field values are case data, never
profile content.

## Where A Success Criterion Lands

A criterion for what would make the finished work good has three possible
homes, and choosing between them is the authoring decision this workflow exists
to make explicit.

- **An assignment point.** The criterion can be phrased so that a supervisor or
  opponent could later evaluate fulfillment against it.
- **Intake rationale.** The criterion explains why the topic is worth doing but
  is not assessable as written. It stays in the intake as the author's
  reasoning and becomes an obligation nowhere.
- **Brief interpretation.** The criterion is something the student must
  understand to read the assignment correctly, but no assignment point can
  carry it in the form the school form allows.

The third home is why **a brief is not derived from its assignment**. In the
probe that produced this contract, the criterion "a zero count of out-of-seam
edits is not the success condition; a complete and justified enumeration is"
fit the intake as rationale and the brief as interpretation, and fit no
assignment point's style at all. A workflow that generated the brief from the
assignment would have lost it.

The brief is nonetheless coupled to its variant's assignment: it restates the
point count and the semestral obligation, so adding a point to an assignment
stales its brief. That coupling is why one reviewer role holds both artifacts.

## Open Solution Space Versus Assessability

These two pull against each other and the resolution is fixed in layer 2.

A point may name the goal and leave the choice of method, algorithm, dataset or
application domain to the student. That is institutional norm, attested across
supervisors, and it has a cost reason that holds for anyone at this faculty: an
approved assignment is expensive to amend, so an open point survives a change of
direction that a specified one would not. It also leaves the student room for
own initiative.

So openness is never flagged as a defect, and a reviewer must not push an open
point toward specifying the solution. What is flagged is openness with **no
stated criterion the choice can be judged against**. `Vyberte vhodnou metodu`
alone is weak; the same point plus the criteria the selection will be judged by
is assessable while staying open.

## Unresolved Values

An agent must never invent a factual value — an identifier, a date, an academic
year. Where a value could not be verified from a source, write the literal token
`UNRESOLVED:` followed by what is missing, **in the value position**.

The value position is what makes the marker mechanically detectable, and it is
the whole rule: a line counts as unresolved when, after an optional `- ` bullet
and an optional `Label: ` prefix, its content begins with `UNRESOLVED:`. A
mention of the token anywhere else on a line — in instructions, in a code span,
mid-sentence — is prose about the marker and is not one.

```text
Identifier: 10.1109/RO-MAN.2019.8956307      resolved
Identifier: UNRESOLVED: no DOI on the publisher page      unresolved
- UNRESOLVED: academic year not confirmed by the operator      unresolved
Use `UNRESOLVED:` when a value cannot be verified.      prose, not a marker
```

That rule is `thesis_review_workflow.metadata::UNRESOLVED_VALUE_RE`, read
through `thesis_review_workflow.metadata::unresolved_values`. The templates
therefore keep their own instructions about the marker without ever tripping it,
and the checker in the later slice consumes the same rule rather than
re-deriving one.

The marker is a **publication blocker**: an unresolved value anywhere in a
variant's bundle means that bundle may not be published to FIT IS and its brief
may not be sent.

`UNRESOLVED:` is distinct from the `TODO:` markers used elsewhere in
`templates/`. `TODO:` marks a slot the operator has still to fill in; only
`UNRESOLVED:` records that a specific fact was looked for, not found, and must
not be guessed.

## What This Workflow Does Not Decide

- It does not score topic quality, novelty, or difficulty. No deterministic
  check in this repository judges whether a topic is a good topic.
- It does not infer work type or scope adequacy from point count. The corpus
  shows five to seven points for both BP and DP.
- It does not modify any thesis readiness gate. `scripts/check-supervisor-ready`
  and `scripts/check-round-ready` are not part of authoring.
