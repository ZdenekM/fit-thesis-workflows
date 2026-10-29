# Formal Assignment

One file per topic variant, the artifact transcribed into FIT IS. The field
order below is the FIT IS form itself, not a style preference: keep it.

The form exists in a Czech and an English rendering, and no document is
bilingual internally — there is no English title field inside a Czech document
and no Czech title inside an English one. Set `Rendering:`, then **delete the
rendering block you are not using**.

`Rendering:` stands for the CZ/EN switch at the very end of the FIT IS form. It
follows the thesis language: `cs` for a Czech thesis, `en` for an English one.
There is no Slovak rendering; a Slovak thesis keeps a Czech or an English
assignment.

The points are a numbered list of tasks with no further explanation.
Motivation, context and interpretation belong in the FIT IS field `Komentář k
zadání (netiskne se)`, which this template does not carry, or in the student
brief.

Write every field value, point and literature entry on one line, without hard
wrapping: the operator pastes them into FIT IS, which keeps every line break.
Copy the entries in the topic intake's `## Citable Artifacts` unwrapped too,
since they are copied here byte-identically.

Filing into FIT IS. The numbers in `### Assignment Points` and the `- ` markers
in `### Literature` belong to this Markdown file, not to the IS fields. Paste
the points without their numbers and format them with the editor's
numbered-list button; paste the literature entries without the leading `- `
and format them with its bullet-list button. Points pasted with their numbers
print as plain text, not as a list, and the head of department returns such an
assignment. Set the CZ/EN switch at the end of the form to `Rendering:` and
fill the fields in that language. Fill the semestral field,
`Body požadované pro udělení zápočtu za první semestr`, printed as
`Při obhajobě semestrální části projektu je požadováno:` or
`Requirements for the semestral defence:`, and tick `Zobrazit studentům`.
Then export the assignment PDF from FIT IS and confirm it fits on one page; if
it does not, shorten the points or the literature and put the full version
into `Komentář k zadání (netiskne se)`. `profiles/default.md`
`## Assignment Authoring Style` holds the rules behind these steps.

Phrase every assignment point in the imperative second-person plural
(`Navrhněte`, `Implementujte`, `Design`, `Implement`). A point may leave the
choice of method, algorithm, dataset or application domain to the student; what
it must not leave open is the criterion that choice will be judged against.

Every literature entry comes from `## Citable Artifacts` in the topic intake and
must appear byte-identically in every variant of this topic that uses it. A
supplement line such as `Dále dle pokynů vedoucího.` may follow real entries; it
may not be the whole content.

Where a factual value could not be verified from a source, write the unresolved
marker in its place instead of guessing — the value position, never the
surrounding prose. See `docs/assignment-authoring.md` `## Unresolved Values`.

Topic id:
Variant: bp / dp
Rendering: cs / en

## Czech Rendering

### Header

Zadání bakalářské práce

Zadání diplomové práce

### Metadata

Ústav:
Student:
Program:
Specializace:
Název:
Kategorie:
Akademický rok:

`Specializace:` appears in a diplomová práce only. `Student:` and `Program:`
stay empty while the topic is unassigned.

### Assignment Points

Zadání:

1.

### Literature

Literatura:

-

### Semestral Defence Requirement

Při obhajobě semestrální části projektu je požadováno:

### Footer

Podrobné závazné pokyny pro vypracování práce viz
https://www.fit.vut.cz/study/theses/

Vedoucí práce:
Vedoucí ústavu:
Datum zadání:
Termín pro odevzdání:
Datum schválení:

## English Rendering

### Header

Bachelor's Thesis Assignment

Master's Thesis Assignment

### Metadata

Institut:
Student:
Programme:
Specialization:
Title:
Category:
Academic year:

`Specialization:` appears in a master's thesis only. `Institut:` is the label
the English form actually uses. `Student:` and `Programme:` stay empty while the
topic is unassigned.

### Assignment Points

Assignment:

1.

### Literature

Literature:

-

### Semestral Defence Requirement

Requirements for the semestral defence:

### Footer

Detailed formal requirements can be found at
https://www.fit.vut.cz/study/theses/

Supervisor:
Head of Department:
Beginning of work:
Submission deadline:
Approval date:
