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
