---
name: thesis-revision-diff
description: Compare two thesis/code rounds in a case and report what changed, what prior feedback was addressed, and what remains.
---

# Thesis Revision Diff

Use this skill when the task is to understand progress between rounds or prepare the previous-feedback section for supervisor feedback.

## Inputs

Use two rounds from the same case:

```text
cases/<case-id>/rounds/<old-round>/
cases/<case-id>/rounds/<new-round>/
```

If the user does not name rounds, compare the newest round with the previous one.

## Process

1. Read both rounds' notes and outputs.
2. Compare thesis text extracts, LaTeX sources, code trees, README/configs, and generated outputs where available.
3. Read old `outputs/feedback_student.md`.
4. Classify old feedback:
   - addressed,
   - partially addressed,
   - still relevant,
   - no longer relevant,
   - cannot verify from current inputs.
5. Identify new risks introduced by the current revision.

Use structured tools when available: `diff`, `git diff --no-index`, file lists, README/config inspection, and targeted text search. Do not rely on vague impressions when files are available.

## Output

Write `outputs/revision_diff.md` in the newer round:

```markdown
# Revision Diff

## Compared Rounds

## High-Level Progress

## Previous Feedback Status

| Prior feedback | Status | Evidence | Follow-up |
|---|---|---|---|

## Thesis Text Changes

## Code / Artifact Changes

## New Risks

## Items Requiring Manual Check
```

Keep this as an internal operator artifact, not student-facing prose.
