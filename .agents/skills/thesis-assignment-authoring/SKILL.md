---
name: thesis-assignment-authoring
description: Author a FIT IS assignment and a starting student brief for each variant of a new BP/DP topic, from an unstructured topic idea through a shared topic intake to a reviewable per-variant bundle.
---

# Thesis Assignment Authoring

Command routing: treat `scripts/<tool>` examples below as logical workflow
command names. On Windows, use the packaged
`dist\workflow-tools\bin\<tool>.cmd` or `.ps1` launcher from `README.md`; do
not run or click extensionless `scripts/<tool>` files.

Use this skill when a supervisor wants to turn a topic idea into something
publishable in FIT IS, AND when a student needs a starting brief for an
assignment that is already issued in IS (adopted from outside this pipeline,
often with the student already on it). It is the only workflow in this
repository that PRODUCES an assignment or a starting brief; every other one
measures a thesis against an existing `notes/assignment.md`. Never write a
starting brief inside a thesis case: route it through a topic case here, then
promote it.

`docs/assignment-authoring.md` is the contract this skill executes. Read it
first: it owns the topic case, the variant bundle, the three style layers,
where a success criterion lands, the open-solution-space rule, and the
unresolved-value marker. Do not restate those rules here or decide them again.

## Case Shape

Authoring happens in its own case with `Case kind: topic-proposal` in
`case.md`. A topic case has NO rounds, so every path below is case-relative,
not round-relative.

```text
cases/<topic-case-id>/
  case.md
  notes/topic_intake.md                    source, one per topic
  notes/student_brief.md                   source, one per topic
  outputs/assignment_formal_<variant>.md   one per variant
  outputs/student_brief_<variant>.md       projection of notes/student_brief.md
```

The thesis readiness gates do not apply. Do not run
`scripts/check-supervisor-ready` or `scripts/check-round-ready` here; they
answer questions a topic case has no student for.

## Adopted Assignment

`docs/assignment-authoring.md` `## Adopting An Issued Assignment` owns the
rules; in short:

- open a topic case for the issued assignment, put its IS PDF in `inputs/`,
  declare only the issued variant in `Variants:`, state in `Important
  constraints:` of `case.md` that the assignment is issued in FIT IS, which PDF
  holds it and which fields stay editable, and fill `Student:` once the student
  is known. Ask the operator which fields are still editable instead of
  assuming only `Literatura:` is; an assignment not yet approved in FIT IS may
  be editable as a whole;
- transcribe the issued points verbatim into
  `outputs/assignment_formal_<variant>.md` and author only what the operator
  can still edit in IS; a point the operator changes is named in `Important
  constraints:` and reviewed as authoring;
- fill the intake to its adopted minimum and write the brief for that student,
  including what a first meeting agreed, as `####` subsections of a content
  section or of the variant delta;
- if an issued field the operator cannot edit fails
  `scripts/check-assignment-draft`, stop and ask; there is no override;
- after approval, render with `scripts/render-brief` when the operator asks
  for the brief as a PDF, and stop there. Run
  `scripts/promote-assignment --issued` only when the operator confirms the
  brief was delivered and IS matches the approved variant, and snapshot and
  reconcile the thesis round's existing `notes/assignment.md` before
  `--replace`.

## Process

This is a parent-owned workflow: the main agent holds the operator dialogue that produces the intake, then delegates review to a separate role. A request for assignment authoring includes this independent review; no separate agent-use confirmation is needed.

1. **Intake first.** Fill `notes/topic_intake.md` from
   `templates/topic-intake.md` with the operator. Everything
   variant-independent is authored exactly once here: motivation, context,
   citable artifacts, success criteria, the boundary, and the sibling topics
   this one excludes.
2. **Resolve or mark, never guess.** Every identifier, date and academic year
   comes from a source the operator or a lookup supplies. Where one cannot be
   verified, write the unresolved marker in the value position. Inventing a DOI
   is the failure this rule exists to prevent.
3. **One assignment per variant.** Fill
   `outputs/assignment_formal_<variant>.md` from
   `templates/assignment-formal.md`, keeping one language rendering. Shared
   material — literature above all — is copied byte-identically from the
   intake into every variant that uses it. Variants differ by escalation
   points and by the semestral requirement, not by re-authored shared text.
4. **One brief source, N projections.** Fill `notes/student_brief.md` from
   `templates/student-brief.md`, then project
   `outputs/student_brief_<variant>.md` as the shared body verbatim plus that
   one variant's delta. Never author a second whole brief. Write it as a
   text for the student, following `docs/assignment-authoring.md`
   `## The Brief As A Text For The Student`.
5. **Check the coupling.** Each brief restates its variant's point count and
   semestral obligation. If a point is added to an assignment, its brief
   changes with it.
6. **Delegate the review.** Hand each variant's bundle to
   `.agents/skills/thesis-assignment-review/SKILL.md`, which must be a
   different agent than the one that authored it. Name your own agent identity
   in the handover and have the reviewer record it in
   `work/reviews/assignment_review_<variant>.md`: the approval is self-attesting
   about its author, so that line is the only trace of who wrote the bundle.
   Apply its findings, then request approval again — material edits after an
   approval reopen draft state, and
   `scripts/check-assignment-bundle` enforces that through the recorded hashes.

## Negative Claims From Discovery

A brief routinely says that something does not exist: no dataset, no prior
measurement, no tool that does X. Such a claim is only as wide as the searches
behind it, and discovery usually runs as several separate passes (literature,
platform/ecosystem, datasets) that each search differently. Before a negative
claim reaches the intake, a brief, or an assignment comment:

- Check it against every discovery artifact of the case, not only the one it
  came from. If any artifact records a counterexample, the claim is wrong as
  worded; narrow it to what the searches actually covered or name the
  counterexample.
- Word what survives as a scoped search result ("jsem nenašel", with the date
  and what was searched, including which research communities and application
  domains), never as a fact about the world.
- Hand the reviewers the full set of discovery artifacts, so they can run the
  same cross-check.

For literature discovery, `docs/assignment-authoring.md` `## Literature
Selection And Currency` also owns two rules that keep these passes from coming
back too narrow: search application domains, not only the originating community,
and ask the operator for publications about the platform the topic builds on.

Measured on a retrofit brief where the literature pass recorded "no public
NL-to-automation dataset beyond four tasks" while the parallel ecosystem scan
had downloaded a ~700-row one; the brief took the literature pass's wording
and both reviewers caught it.

## Style Layers

Read the reviewer profile selected by `Reviewer profile:` in `case.md`. The
generic base in `profiles/default.md` `## Assignment Authoring Style` applies
always; a local profile's section refines it. Never copy a personal
supervision convention into `notes/topic_intake.md`, which is topic content
shared by every supervisor using this repository.

## Stop Conditions

- The operator cannot supply a factual value and no source resolves it: mark
  it, do not guess, and carry it as a publication blocker.
- Publishing to FIT IS or sending a brief: not this skill's decision. The
  plan's acceptance criteria and the operator own it. When the operator asks
  for the brief as a PDF, render the approved variant with
  `scripts/render-brief <case-id> <variant>` and report the dated copy it
  prints as `For the student:` only when the command succeeded; rendering
  sends nothing.

## Outputs

```text
notes/topic_intake.md
notes/student_brief.md
outputs/assignment_formal_<variant>.md
outputs/student_brief_<variant>.md
```
