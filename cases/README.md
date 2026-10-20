# Local Thesis Cases

This directory is for local thesis case data. Everything below this file is ignored by git.

Expected layout:

```text
cases/<case-id>/
  case.md
  current-round.txt
  rounds/
    <timestamp>-<label>/
      notes/
      inputs/
      extracted/
      work/
      outputs/
```

Before generating supervisor feedback or opponent materials, the round must include
`notes/assignment.md` with the formal assignment and private assignment notes. Check it with:

```bash
scripts/check-round-ready <case-id>
```

Before supervisor feedback, also check academic-year deadline calibration:

```bash
scripts/check-supervisor-ready <case-id>
```

Do not force-add case data unless you explicitly intend to put private student material into git history.

## Literature Library

`cases/_literature/` holds the papers an agent has read in full for any case. It is
ignored like the rest of `cases/`. There is one directory per source, so a later round,
another student's case or a reviewer reuses the reading instead of repeating it:

```text
cases/_literature/<first-author>-<year>-<short-title>/   lowercase ASCII, e.g. bobak-2020-temporally-stable-boundary-labeling
  source.json   title, authors, venue, year, doi, retrieved_from, retrieved_at,
                access (open | operator_supplied), version, paper_sha256
  paper.pdf     the copy that was read
  fulltext.txt  pdftotext -enc UTF-8 -layout paper.pdf; line anchors in notes.md point here
  notes.md      extraction: problem, approach, how it was evaluated, findings
                (including what did not work), and verified claims with line anchors
```

- Store only legal copies: open author, institution or project pages, arXiv, or
  publisher PDFs the operator supplied, which the operator can also drop straight into
  a source directory as `paper.pdf`.
- Keep `notes.md` case-neutral: no case IDs or student names. What a source means for
  one student's work belongs in that case's artifacts, which name the library slug.
- Before reading a source, look it up by DOI or title in the `source.json` files. Extend
  existing notes rather than rewriting them. A different version (preprint vs.
  published) goes into `version`.
- The parent session writes the library; reviewer roles read it. The library is a reuse
  cache, not round evidence: a validator that hashes evidence inside a round, such as
  `work/literature/` for literature/citation review, gets a copy from here.
