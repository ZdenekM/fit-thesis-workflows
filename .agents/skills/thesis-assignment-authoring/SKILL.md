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
publishable in FIT IS. It is the only workflow in this repository that
PRODUCES an assignment; every other one measures a thesis against an existing
`notes/assignment.md`.

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

## Process

This is a parent-owned workflow: the main agent holds the operator dialogue
that produces the intake, then delegates review to a separate role. Confirm
explicit agent authorization in the current request before generating a
reviewable bundle.

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
   one variant's delta. Never author a second whole brief.
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

## Style Layers

Read the reviewer profile selected by `Reviewer profile:` in `case.md`. The
generic base in `profiles/default.md` `## Assignment Authoring Style` applies
always; a local profile's section refines it. Never copy a personal
supervision convention into `notes/topic_intake.md`, which is topic content
shared by every supervisor using this repository.

## Stop Conditions

- No agent authorization in the current request: stop and ask.
- The operator cannot supply a factual value and no source resolves it: mark
  it, do not guess, and carry it as a publication blocker.
- Publishing to FIT IS or sending a brief: not this skill's decision. The
  plan's acceptance criteria and the operator own it.

## Outputs

```text
notes/topic_intake.md
notes/student_brief.md
outputs/assignment_formal_<variant>.md
outputs/student_brief_<variant>.md
```
