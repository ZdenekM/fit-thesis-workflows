---
name: thesis-figure-media-review
description: Internal BP/DP evidence workflow for reviewing thesis figures, tables, screenshots, result images, diagrams, and PDF-linked source figure assets, including reusable per-item visual descriptions and revision-to-revision changes.
---

# Thesis Figure/Media Review

Use this skill when supervisor feedback, opponent materials, revision diff, or a
standalone operator check needs evidence about visual elements in the submitted
thesis. The output is internal/operator evidence, not student-facing prose by
default.

## Inputs

Use the active round unless the user specifies another:

```text
cases/<case-id>/rounds/<round-id>/
  inputs/
  extracted/
  work/
    figure_media/
  outputs/
```

Relevant visual elements are numbered figures and tables, screenshots, result
images, diagrams, and thesis-source figure assets that are linked to the
rendered PDF. Ignore decorative logos, icons, and layout ornaments unless a
thesis claim depends on them.

## Process

1. Confirm that the user explicitly authorized agent use in the current request when this review will produce final standalone evidence or feed supervisor/opponent artifacts. If explicit authorization is missing, stop before writing the artifact and ask the user to authorize agents.
2. Resolve the active case and round. Record whether the review is for supervisor/student-facing downstream use, opponent/internal-only use, revision diff, or standalone operator evidence. For supervisor/student-facing use, run `scripts/check-supervisor-ready <case-id> [round-id]`; for opponent/internal-only use, run `scripts/check-round-ready <case-id> [round-id]`.
3. Treat the submitted PDF as the authoritative rendered artifact. Use `pdftotext -layout` extracts for stable text/caption evidence. Use `pdf-reader-mcp`, screenshots, crops, or other vision evidence only for targeted visual inspection. Use LaTeX/Overleaf/source assets as a precision layer for original image quality and provenance, never as a replacement for the final PDF.
4. Inventory relevant visual elements from the rendered PDF text, captions, list of figures/tables, nearby claims, and source assets. Write one JSON object per relevant item to `work/figure_media/visual_inventory.jsonl`.
5. Before expensive visual inspection, compute cheap cache metadata when available:
   - `source_asset_sha256` for a linked source asset,
   - `rendered_crop_sha256` for a PDF crop if this run created one,
   - `context_hash` from the normalized caption and relevant text mentions,
   - nearest previous-round inventory records from the same case.
6. Reuse `visual_description` only when a previous record for the same item has a matching source-asset or rendered-crop hash and the same `visual_analysis_version`. Record `visual_reused_from_round` and `visual_reuse_reason`.
7. For every relevant item, attempt to produce a reusable description:
   - `inventoried_only`: record the caption/nearby claim and explicitly state that visual content was not verified.
   - `pdf_inspected`: record what the item visually shows based on concrete PDF-detail or vision evidence.
   - `source_asset_checked`: record what the source asset shows and cite the PDF anchor that proves it appears in the rendered thesis.
   - `not_available`: record why the item cannot be inspected.
8. Record `text_mentions` for material thesis references to the item. Each mention should include an anchor, a short excerpt, and one role: `introduces`, `interprets`, `uses_as_evidence`, or `references_only`.
9. Record claim alignment between the visual content and the surrounding thesis claim:
   - `supports`,
   - `partially_supports`,
   - `does_not_support`,
   - `not_verifiable`.
   Use `not_verifiable` when the item is only `inventoried_only` or `not_available`. Do not use `supports`, `partially_supports`, or `does_not_support` unless the item is `pdf_inspected` or `source_asset_checked`.
10. Reuse `claim_alignment` only when the previous record has a matching visual hash, matching `context_hash`, and the same `claim_alignment_version`. If the caption, nearby text, or mention role changed, reuse the visual description if the hash allows it, but redo claim alignment.
11. Do not make visual-content claims unless the item status is `pdf_inspected` or `source_asset_checked`. Text-only inventory can support "caption says" findings, not "the figure shows" findings.
12. Compare against previous rounds in the same case. Prefer the nearest previous `work/figure_media/visual_inventory.jsonl`; also read prior `outputs/figure_media_review.md` when the JSONL is missing. Classify changes as `added`, `removed`, `caption_changed`, `visual_content_changed`, `claim_alignment_changed`, `unchanged`, or `not_comparable`.
13. Route related issues into existing checks:
   - result graphs and metric tables -> quantitative-claims review that writes `work/quantitative_claims.json`, followed by `scripts/check-evaluation-claims <case-id> [round-id]`,
   - screenshots or UI figures claiming implemented behavior -> `thesis-code-consistency`,
   - implementation/UI figures relevant to maintainability or reviewability -> `thesis-code-quality-review`,
   - copied/adapted figures and attribution/source support -> `thesis-literature-citation-review`.
14. Do not run graph/table quality checks such as axis-label, unit, legend, scale, or readability audits as part of this iteration. If those concerns are obvious, record them as manual checks or route result claims to evaluation-claim review.
15. Summarize only actionable findings into supervisor feedback or opponent materials. Keep the reusable inventory, context table, and cache details internal.
16. After writing `outputs/figure_media_review.md` and `work/figure_media/visual_inventory.jsonl`, run `scripts/check-figure-media-review <case-id> [round-id]`. Fix hard failures before relying on the artifact. Treat warnings as operator prompts and either address them or record the limitation.
17. Run `scripts/init-review-manifest --run-checks <case-id> [round-id]` and record whether the figure/media evidence is standalone final evidence or only covered by downstream supervisor/opponent synthesis. Before relying on it, run `scripts/check-review-manifest --require-complete <case-id> [round-id]`.

## Inventory JSONL

Each line in `work/figure_media/visual_inventory.jsonl` is a JSON object with
these fields:

```json
{
  "item_id": "fig-3-2",
  "type": "figure",
  "pdf_anchor": "PDF p. 18, Figure 3.2",
  "caption_or_nearby_claim": "Caption or nearby thesis claim.",
  "source_asset_path": "work/thesis-source/figures/example.png",
  "inspection_status": "pdf_inspected",
  "visual_description": "Short reusable description.",
  "limitations": "None, or what could not be verified.",
  "downstream_relevance": "Why this matters for supervisor/opponent/revision use.",
  "previous_round_change": "caption_changed",
  "source_asset_sha256": "optional SHA-256 digest",
  "rendered_crop_sha256": "optional SHA-256 digest",
  "visual_analysis_version": "figure-media-visual-v1",
  "visual_reused_from_round": "optional previous round id",
  "visual_reuse_reason": "matching_source_asset_sha256",
  "text_mentions": [
    {
      "anchor": "PDF p. 18, paragraph before Figure 3.2",
      "excerpt": "Nearby text claim.",
      "role": "uses_as_evidence"
    }
  ],
  "context_hash": "optional SHA-256 digest",
  "claim_alignment": "partially_supports",
  "claim_alignment_rationale": "Short explanation.",
  "claim_alignment_version": "figure-media-claim-v1",
  "claim_alignment_reused_from_round": "optional previous round id"
}
```

Use an empty string for unavailable optional path fields. `previous_round_change`
may be omitted when no previous round exists. Current V1 versions are
`figure-media-visual-v1` and `figure-media-claim-v1`.

## Review Loop

When this artifact is generated as standalone output, it is draft evidence until
a different explicitly authorized reviewer agent checks it. If agent
authorization is missing, ask before marking or relying on it as final
standalone evidence. A downstream synthesis review certifies only the findings
it uses, not the whole standalone artifact.

## Output

Write `outputs/figure_media_review.md`:

```markdown
# Figure/Media Review

## Review Scope

## Visual Inventory

| Item | Type | PDF anchor | Inspection status | Description |
|---|---|---|---|---|

## Inspected Figures And Tables

## Changes Since Previous Round

## Context And Claim Alignment

| Item | Text role | Claim alignment | Reuse status | Action |
|---|---|---|---|---|

## Findings

| Priority | Item | Inspection status | Claim | Evidence | Downstream use |
|---|---|---|---|---|---|

## Downstream Use

## Review Status

## Manual Checks
```

This artifact is internal/operator evidence. Supervisor feedback and opponent
materials may summarize only selected, phase-appropriate and evidence-backed
findings. Do not copy cache fields into student-facing or opponent-facing prose;
use them only to justify whether visual and claim-alignment analysis was reused.
