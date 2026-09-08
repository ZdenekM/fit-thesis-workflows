---
name: thesis-assignment-review
description: Independent review of one authored assignment variant together with its student brief, checking assessability, the open-solution-space boundary, byte-identical shared material across variants, and unresolved values, and recording a bundle-binding approval.
---

# Thesis Assignment Review

Command routing: treat `scripts/<tool>` examples below as logical workflow
command names. On Windows, use the packaged
`dist\workflow-tools\bin\<tool>.cmd` or `.ps1` launcher from `README.md`; do
not run or click extensionless `scripts/<tool>` files.

Use this skill as the required independent review of one variant bundle before
that variant's assignment may be published to FIT IS or its brief sent to a
student. `docs/assignment-authoring.md` is the contract; do not re-decide the
rules it owns.

You must be a different agent than the one that authored the bundle.

## Scope: One Variant, Both Artifacts

One role holds the assignment AND its brief. The brief restates its variant's
point count and semestral obligation, so adding a point to the assignment
stales the brief silently, and only a reader of both catches it. Do not split
this into two reviews.

## Inputs

Case-relative; a topic case has no rounds.

```text
case.md
notes/topic_intake.md
notes/student_brief.md
outputs/assignment_formal_<variant>.md
outputs/student_brief_<variant>.md
```

Tracked, repository-relative:

```text
profiles/default.md                    ## Assignment Authoring Style, layer 2
profiles/local/<profile-id>.md         when case.md selects one, layer 3
docs/assignment-authoring.md
templates/assignment-formal.md
```

Read the style layers before reviewing, not after: layer 2 is the standard this
review applies, and layer 3 tells you which of the author's choices are that
supervisor's declared preference rather than a defect. If the selected profile
is missing or unreadable, say so and review against layer 2 alone.

Also read every OTHER variant's `outputs/assignment_formal_*.md` in the same
case: shared material is checked across variants, not within one.

## What To Check

1. **The layer-2 base, item by item.** Walk
   `profiles/default.md` `## Assignment Authoring Style` and check each
   institutional-norm item against this variant: imperative second-person
   plural, a survey or familiarization point first, a presentation deliverable
   last, the semestral-requirement field filled, real literature entries with
   verifiable identifiers, and a point count read as a loose bound that says
   nothing about work type or scope adequacy. Do not treat this list as
   satisfied because the points read well.
2. **Assessability.** Could this repository's own opponent pipeline evaluate a
   finished thesis against each point a year from now? An activity with no
   success criterion is the recurring corpus weakness.
3. **Open solution space.** A point may leave the method, algorithm, dataset or
   application domain to the student, and that is institutional norm. Do NOT
   push an open point toward specifying the solution. Flag only openness with
   no stated criterion the choice can be judged against.
4. **Shared material is byte-identical.** Literature entries and any other
   material the intake authors once must appear character for character the
   same in every variant that uses them, and the brief projections must carry
   the shared body verbatim.
5. **The intake reached the bundle where it was meant to.** Byte-identical
   projections and matching point counts can both pass while a criterion was
   simply dropped, so check the intake's three-way split by hand: every
   criterion under `### Interpretation For The Student` appears in the brief,
   every one under `### Assessable As An Assignment Point` is covered by a
   point of this variant or is explicitly deferred to the other variant, and
   nothing under `### Rationale Only` became an obligation in either artifact.
6. **Coupling.** The brief's point count, milestones and semestral obligation
   match its own variant's assignment.
7. **Form.** One language rendering per document, the FIT IS field set and
   order from `templates/assignment-formal.md`, the semestral-requirement field
   filled.
8. **Unresolved values.** Any unresolved marker in the value position is a
   publication blocker; name each one.
9. **Layer discipline.** No supervision convention or personal phrasing in
   `notes/topic_intake.md`, and no factual field value taken from a profile.
   Provenance of a value cannot be read off the finished bundle: report a
   suspicious value as unverified provenance for the operator to confirm, never
   as a passed check.

## Outputs

```text
work/reviews/assignment_review_<variant>.md
work/reviews/assignment_approval_<variant>.json
```

The findings artifact is internal operator evidence, never sent.

This role does NOT write a revised assignment. A human transcribes the
assignment into FIT IS, and a machine-revised second copy would leave two
candidate texts for one IS entry. Report findings; the authoring parent applies
them.

The approval record binds the whole bundle, because the outward-facing action
is publishing a bundle rather than a file. Build it with
`thesis_review_workflow.assignment_bundle::build_bundle_approval_payload`
rather than by hand; it is `assignment-bundle-approval-v1` and carries:

```text
schema_version, case_id, variant
files[]                    one {path, sha256} per bundle file, all four
author_agent               who authored the bundle
reviewer_agent             you; must differ from author_agent
reviewer_role, human_reviewer
verdict                    approved/pass only
blocking_findings_count    0; a record with blockers is not an approval
checks_observed, limitations, timestamp, notes
```

Records are pass-only. A review with blocking findings produces the findings
artifact and NO approval; do not write a record with a negative verdict or a
nonzero blocking count, and note that
`scripts/check-assignment-bundle` rejects both on read regardless of how the
record was produced.

Independence is judged on this record: `author_agent` must differ from
`reviewer_agent`. There is no round manifest behind a topic case, so the record
is self-attesting about its author — traceability, not authentication. Take the
author identity from the parent's handover as recorded in your findings
artifact, and if it was not supplied, say so as a limitation instead of
inventing one.

`scripts/check-assignment-bundle <case-id> <variant>` validates the record, and
refuses to consider it at all until `scripts/check-assignment-draft` passes.

## Stop Conditions

- You authored or materially edited any artifact in the bundle: stop, say so.
- No agent authorization in the current request: stop and ask.
- Approving is not publishing. Publication to FIT IS and sending the brief stay
  with the operator.

## Return Contract

- paths written, or the concrete reason nothing was written,
- verdict per variant,
- blocking findings, separated from improvements,
- unresolved values found,
- which style layers were actually read, and layer 2 applied item by item,
- limitations and manual checks, including any provenance you could not verify.
