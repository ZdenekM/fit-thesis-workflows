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

The projection has a fixed shape, so a checker can compare it exactly instead
of inferring which text belongs to which variant:

```text
<title> - <variant>

<the ## Shared Brief body of notes/student_brief.md, verbatim>

<delta heading> - <variant>

<that variant's ### <variant> delta body, verbatim>
```

Both wrappers are language-bound, because the student reads them: `cs` uses
`# Úvodní podklad k tématu` and `## Specifika varianty`, `en` uses
`# Thesis Topic Brief` and `## For This Variant`. Neither is spelled like a
neutral source wrapper, so a wrong-language heading can be forbidden anywhere in
the document rather than only at the positions a wrapper may occupy.

Nothing else belongs in the file, the title line included: the checker compares
the WHOLE projection against that document, because an obligation written into
the title survived a comparison of the two bodies alone. One variant's delta may
also legitimately contain another's as a prefix, so the boundaries are marked
rather than guessed.

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

## Brief Language

A brief is the only student-facing artifact this workflow produces, so it
follows `Student feedback language` in `case.md` — never the thesis language,
and never the assignment's `Rendering:`. The field defaults to `cs`, and an
unsupported value is refused rather than defaulted.

That field selects the brief's heading set, and
`scripts/check-assignment-draft` applies the same three rules
`scripts/check-feedback-language` applies to student feedback: the required
headings of the declared language are present, no ASCII-folded spelling of a
Czech heading appears, and no heading of the other language appears. The third
rule is the one that catches a Czech brief carrying an English section copied
verbatim into its projection — the other two, and the whole-document comparison
above, all pass such a file.

The source and a projection have different required sets on purpose. The
source's `## Shared Brief`, `## Variant Delta` and `### <variant>` are neutral
authoring structure the student never sees; a projection carries the
language-bound title and delta heading instead.

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

## What Is Checked Deterministically

`scripts/check-assignment-draft <case-id> [variant]` decides everything about a
bundle that needs no judgment, so a review round is not spent counting fields:
the case kind, exactly one rendering block with its full FIT IS label sequence
in order, a numbered point inside the points section, a filled
semestral-requirement field, unresolved values, a usable variant identifier, and
each brief projection matching the canonical shape above exactly.

It also requires each **structural heading to occur exactly once** — the brief
source's and each projection's required headings, and the assignment's six
sections. Every other rule reads a document through its first match: the section
readers stop at the next heading, and the language check collects headings into a
set. So a file carrying its whole body twice satisfied the required set, the
forbidden set and the canonical projection comparison, because the projection was
generated from the first copy. That is not hypothetical — an edit anchored on a
string that also appeared in the operator note above `## Shared Brief` spliced the
body in twice and the whole check passed. Counting enumerated headings is
structural, not lexical: it never reads prose.

There is deliberately no separate cross-variant equality check. Every literature
bullet must equal an intake entry exactly, so two variants citing one work
necessarily cite it identically; requiring identical membership instead would
reject a DP that legitimately cites one more work than its BP.

Literature is checked by **provenance, not by wording**. Every literature
bullet must equal an entry the intake's `## Citable Artifacts` authored, every
such entry must carry an identifier that is not an unresolved value, and at
least one must exist. The one line allowed not to come from an entry is the one
declared in the intake's `Supplement line:` field — recognised because it was
declared, never because a checker matched its text. This matters because the
corpus placeholders (`Bude doplněno.`, `Dle doporučení vedoucího.`) are ordinary
Czech sentences, and `AGENTS.md` forbids a free-text heuristic from becoming a
gate.

Structural provenance proves an entry came from the intake. It never proves the
identifier resolves to a real work; that stays with the reviewer and the
operator.

What the checker deliberately does NOT decide: assessability, whether an open
point states a criterion the choice can be judged against, tone, topic quality,
and anything derived from point count. Those belong to
`.agents/skills/thesis-assignment-review/SKILL.md`.

## The Bundle Approval

`scripts/check-assignment-bundle <case-id> <variant>` is the gate before
publishing a variant to FIT IS or sending its brief. It refuses to look at an
approval until `scripts/check-assignment-draft` passes — an approval over a
structurally broken bundle reads as reviewed, which is worse than none — and
then validates `work/reviews/assignment_approval_<variant>.json` as
`assignment-bundle-approval-v1`. The reviewer's findings live beside it in
`work/reviews/assignment_review_<variant>.md`. The record requires:

- every one of the four bundle files bound by path and content hash, and no
  file outside the bundle;
- an approved verdict with `blocking_findings_count` zero, checked when the
  record is read and not only when it is built, because a record is a file
  anyone can write;
- `author_agent` different from `reviewer_agent`.

A hash mismatch is how "material edits after review reopen draft state" is
enforced: change any bound file and the check names it.

Two limits, stated rather than implied. Independence here rests on the record's
own `author_agent`: unlike a review round, a topic case has no
`work/review_manifest.json` recording who generated what, so the field is
traceability, not authentication. And `checks_observed`, `limitations` and
`timestamp` are audit metadata — they record what a reviewer said it did and
establish nothing about whether a semantic review happened. That is why the
operator reading stays part of the gate.

## Promotion Into A Thesis Case

`scripts/promote-assignment <topic-case-id> <variant> <target-case-id>
[round-id]` writes the approved variant into the target round's
`notes/assignment.md`, the artifact every other workflow measures the thesis
against. It refuses on four independent grounds, and passing three is not
enough:

- **Approval.** `scripts/check-assignment-bundle` must pass for that variant.
- **Issuance.** `--issued` is required, and it asserts something the approval
  does NOT: that this variant is the student's effective assignment and its
  brief was supplied. An approval says a variant may be published. Promoting on
  approval alone would have every later round grade the student against
  requirements they never received, and no readiness check can see the
  difference, because `check_round_ready` reads section content.
- **Target fitness.** The target must be a `thesis-review` case with a real
  round and a `Work type` matching the variant. `unknown` is refused too:
  promotion is the moment the work type is knowable.
- **Containment.** The resolved case must sit under the resolved `cases/` root.
  `.gitignore` protects the lexical path, so a `cases/<id>` linked to somewhere
  else would carry private content out of the protected tree while every other
  check passed.

`--replace` lifts exactly one refusal — an existing `notes/assignment.md`, which
a case may already have been reviewed against — and no other.

The generated file records `Assignment source:` with the topic, the variant and
the approval record's sha256, plus `Assignment source record:` naming the copy
of that record retained in the target round. The copy matters because there is
one approval path per variant: a later re-approval overwrites the record the
hash refers to, and a hash with nothing behind it is an identity, not an
archive. The promotion is also appended to the target round's operation log; the
topic case has no round and therefore no log of its own.

The brief projection becomes `## Private Assignment Notes For Student`, which is
what that section already means. Its headings are demoted on the way in:
`check_round_ready` ends a section at the next H2, and the projection carries
one, so a verbatim copy would cut the section in half.

## Case Doctor On A Topic Case

`scripts/case-doctor <topic-case-id>` reports the intake, the variants and each
variant's draft and bundle status, and runs no thesis gate. It branches before
the round resolution that otherwise fails immediately on a case with no
`current-round.txt`. It replaces no gate; it is a read-only snapshot.

## What This Workflow Does Not Decide

- It does not score topic quality, novelty, or difficulty. No deterministic
  check in this repository judges whether a topic is a good topic.
- It does not infer work type or scope adequacy from point count. The corpus
  shows five to seven points for both BP and DP.
- It does not modify any thesis readiness gate. `scripts/check-supervisor-ready`
  and `scripts/check-round-ready` are not part of authoring.
