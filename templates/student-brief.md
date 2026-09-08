# Student Brief

The starting brief a student receives with the assignment. This template is the
canonical per-topic SOURCE, kept at `notes/student_brief.md`: a shared body
authored once, plus one delta per variant. What a student receives is a
projection of it — `outputs/student_brief_<variant>.md`, the shared body plus
that one variant's delta and nothing else. The shared body reaches every
projection byte-identically, the same rule the intake's citable artifacts follow
into `Literatura:`. Never author two whole briefs.

Write the brief in the case's `Student feedback language` from `case.md` —
never the thesis language, and never the assignment's `Rendering:`. That field
also selects the heading set below: keep the Czech or the English content
headings and delete the other. The structural wrappers `## Shared Brief`,
`## Variant Delta` and `### <variant>` stay as they are in both languages,
because the student never sees them.

Where a factual value cannot be verified, write the unresolved marker in the
value position instead of guessing; it blocks sending. See
`docs/assignment-authoring.md` `## Unresolved Values`.

Topic id:
Variants: bp / dp

## Shared Brief

Variant-independent. If a sentence here would be true for only one variant, it
belongs in the delta instead.

Content headings, Czech (`Student feedback language: cs`):
`### Na čem práce staví`, `### Kde začít`, `### Jak budeme spolupracovat`,
`### Jak číst zadání`, `### Co do práce nepatří`.

Content headings, English (`Student feedback language: en`):
`### What The Work Builds On`, `### Where To Start`, `### Working Agreements`,
`### How To Read The Assignment`, `### What Is Out Of Scope`.

### What The Work Builds On

The platform, prior thesis, dataset, or deployment the student starts from, and
what state it is in.

### Where To Start

Reading order, the first thing to run, the first thing to change. Supervision
conventions of the kind that live in the reviewer profile's
`## Assignment Authoring Style` layer 3 are rendered here, not invented here.

### Working Agreements

How work is handed over and discussed, and what is expected between meetings.

### How To Read The Assignment

The interpretation the assignment points cannot carry — the criteria recorded
under `### Interpretation For The Student` in the topic intake. This section is
why a brief is not merely a restatement of the assignment.

### What Is Out Of Scope

The boundary from the intake, in the student's terms.

## Variant Delta

One block per variant offered. Everything here is variant-specific and must
stay consistent with that variant's assignment: if a point is added to the
assignment, this block changes with it.

The projection `outputs/student_brief_<variant>.md` has a fixed shape so it can
be compared exactly rather than guessed at: a title line, the `## Shared Brief`
body verbatim, then the variant delta heading followed by that variant's delta
body verbatim, and nothing else at all. Both of those headings are
language-bound, so the student never reads a wrapper in the wrong language:

- `cs`: `# Úvodní podklad k tématu - <variant>` and
  `## Specifika varianty - <variant>`
- `en`: `# Thesis Topic Brief - <variant>` and `## For This Variant - <variant>`

None of those is spelled like a neutral source wrapper. That is deliberate: it
lets the checker forbid a wrong-language heading anywhere in the document
instead of exempting titles, which once let `# Student Brief` sit inside a Czech
shared body and reach every projection.

### bp

Contribution framing:

Milestones:

-

Assessment and the semestral defence:

### dp

Contribution framing:

Milestones:

-

Assessment and the semestral defence:
