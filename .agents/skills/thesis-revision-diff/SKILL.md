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

1. Confirm that the user explicitly authorized agent use in the current request when this diff will be used as final standalone evidence or as input to sendable feedback. If explicit authorization is missing, stop before writing the artifact and ask the user to authorize agents.
2. Read both rounds' notes and outputs.
3. Compare thesis text extracts, LaTeX sources, code trees, README/configs, figure/media inventories, and generated outputs where available. Treat submitted PDFs as rendered artifacts; use LaTeX/Overleaf sources for diff/search/evidence and do not build them by default. Use `pdf-reader-mcp` only for targeted PDF detail checks such as page ranges, metadata, page counts, figures/tables, layout-sensitive changes, or ambiguous extraction.
4. Read old `outputs/feedback_student.md`.
5. Classify old feedback:
   - addressed,
   - partially addressed,
   - still relevant,
   - no longer relevant,
   - cannot verify from current inputs.
6. Identify new risks introduced by the current revision.
7. If both rounds have `work/figure_media/visual_inventory.jsonl` or the newer round has `outputs/figure_media_review.md`, use that evidence for figure/table/screenshot/result-image changes. Do not infer visual-content changes from captions alone; mark them as caption or claim-alignment changes unless figure/media review recorded `pdf_inspected` or `source_asset_checked` evidence.

Use structured tools when available: `diff`, `git diff --no-index`, file lists, README/config inspection, and targeted text search. Do not rely on vague impressions when files are available.

## Review Loop

When this artifact is generated as standalone output, it is draft evidence until a different explicitly authorized reviewer agent checks it. If agent authorization is missing, ask before marking or relying on it as final standalone evidence; if authorization is not granted, stop before final standalone use or before using the artifact in a sendable supervisor/opponent synthesis. A downstream synthesis review certifies only the findings it uses, not the whole standalone artifact.

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

## Figure / Media Changes

## New Risks

## Review Status

## Items Requiring Manual Check
```

Keep this as an internal operator artifact, not student-facing prose.
