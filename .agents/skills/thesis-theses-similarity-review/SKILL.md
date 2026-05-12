---
name: thesis-theses-similarity-review
description: Internal BP/DP evidence workflow for interpreting imported Theses.cz similarity reports in case context, including repeated-submission self-overlap and suspicious or unresolved matches.
---

# Thesis Theses.cz Similarity Review

Command routing: treat `scripts/<tool>` examples below as logical workflow
command names. On Windows, use the packaged
`dist\workflow-tools\bin\<tool>.cmd` or `.ps1` launcher from `README.md`; do
not run or click extensionless `scripts/<tool>` files.

Use this skill when a round contains an imported Theses.cz similarity report and
supervisor feedback, a supervisor report, opponent materials, or standalone
operator evidence need a contextual interpretation. The report is private
internal evidence. A clean or resolved report normally stays silent downstream.

## Inputs

Use the active round unless the user specifies another:

```text
cases/<case-id>/rounds/<round-id>/
  inputs/theses_similarity/report.pdf
  extracted/theses_similarity/report.txt
  work/theses_similarity/intake.json
  work/theses_similarity/assessment.json
  work/theses_similarity/review_draft.md
  outputs/theses_similarity_review.md
  extracted/thesis.txt
  notes/
  outputs/revision_diff.md
```

Also inspect previous rounds when the report may match an earlier submission of
the same student. Use `outputs/revision_diff.md` or equivalent previous-round
evidence for claims about what changed; do not use a similarity percentage as a
revision-diff metric.

## Process

1. Confirm explicit agent authorization before writing or relying on
   `outputs/theses_similarity_review.md` for final standalone evidence or
   downstream supervisor/opponent synthesis.
2. Resolve the active case and round. Run
   `scripts/check-theses-similarity-report <case-id> [round-id]`. If it fails,
   repair the import/evidence shape or record a typed limitation before
   synthesis.
3. Read `work/theses_similarity/intake.json` first. Use the PDF/text only for
   targeted verification of report structure, source rows, matched-passage
   anchors, and extraction limitations.
4. Read the current thesis PDF extract, assignment, round notes, and previous
   rounds as needed. For self-overlap, check whether the source is an earlier
   version of the same student's work and whether case history supports that.
5. Write or update `work/theses_similarity/assessment.json` using schema
   `theses-similarity-assessment-v1`. Each judgment must be anchored to source
   IDs, passage refs, basis refs, evidence refs, confidence, limitations, and a
   synthesis action.
6. Write `outputs/theses_similarity_review.md` as internal/operator evidence
   with a `## Synthesis Handoff` section. Keep raw report URLs, hashes, local
   paths, and source internals out of downstream-facing prose.
7. Run `scripts/check-theses-similarity-report <case-id> [round-id]` again.
8. Run `scripts/init-review-manifest --run-checks <case-id> [round-id]`. If the
   artifact is standalone final evidence, run an independent evidence
   calibration pass and write
   `scripts/write-review-approval --profile theses-similarity-review <case-id> [round-id]`.
   If it is covered by supervisor/opponent synthesis, record the used findings
   and evidence hash in the manifest.

## Free-Text Boundary

The deterministic import parses bounded report structure only. It does not
decide plagiarism, misconduct, authorship, grading impact, or report wording.
Semantic interpretation belongs to this authorized review and must be recorded
as anchored structured evidence.

Do not infer concern from a percentage alone. Do not classify self-overlap as
suspicious merely because it is high. Treat high similarity to an earlier
submission by the same student as a contextual self-revision candidate.

## Judgment Categories

Use only the categories accepted by `theses-similarity-assessment-v1`:

- `no_material_concern`
- `self_revision_overlap_expected`
- `self_revision_overlap_unverified`
- `external_match_needs_review`
- `external_match_resolved_as_standard_or_common_material`
- `external_match_resolved_as_cited_and_proportionate`
- `external_match_cited_but_still_needs_review`
- `external_match_unresolved`
- `report_unusable_or_incomplete`

Default downstream routing:

- `silent`: clean reports, expected self-revision overlap, and resolved
  standard/common/cited matches.
- `manual_check`: unverified self-overlap, cited-but-still-material matches,
  unusable reports, or evidence gaps.
- `surface`: reviewed unresolved external concerns or institutional wording
  needs.

## Synthesis Handoff

The handoff must say:

- workflow/audience;
- whether synthesis should stay silent;
- any material concern that may be surfaced;
- exact evidence anchors for surfaced concerns;
- wording boundaries and do-not-overstate notes;
- self-overlap status and previous-round evidence used;
- limitations and manual checks.

Supervisor feedback should mention similarity only when it creates a concrete
student action or unresolved submission risk. Supervisor reports and opponent
materials may surface reviewed unresolved concerns, but must avoid plagiarism or
authorship wording unless the reviewed evidence supports that narrow statement.

## Review Loop

`outputs/theses_similarity_review.md` is internal evidence. If used as final
standalone evidence, it needs an independent explicitly authorized reviewer. The
approval record uses `work/reviews/theses_similarity_review.json` through the
canonical `theses-similarity-review` approval profile. Material edits after the
approval reopen draft state.

A downstream synthesis review certifies only the similarity findings it uses. It
does not make the whole standalone artifact reviewed.

## Agent Final Response Contract

When acting as a workflow agent, write full evidence content to the owned round
files and keep the chat final response compact. Do not paste full Markdown
artifacts that are already on disk.

Return only:

- files written or changed;
- top 3-5 findings, verdicts, or risks;
- commands/checks run;
- explicit limitations;
- whether expected output validation passed.

The main session must verify file claims with expected-output checks before
relying on them.

## Model And Reasoning

Use the strongest available model with high reasoning effort for semantic
review of similarity matches and downstream wording. In the current Codex setup,
use `gpt-5.5` with `xhigh` reasoning when exposed. Mechanical parsing and helper
checks may use cheaper models only when validator-backed and consumed by this
semantic pass.

## Output

Write `outputs/theses_similarity_review.md`:

```markdown
# Theses.cz Similarity Review

## Review Scope

## Imported Report

## Structural Findings

## Contextual Assessment

| Judgment | Source IDs | Category | Synthesis action | Evidence | Limitations |
|---|---|---|---|---|---|

## Repeated-Submission / Self-Overlap Check

## Downstream Use

## Synthesis Handoff

- Workflow/audience:
- Use in synthesis:
- Stay silent when:
- Surface only when:
- P0/P1 anchors:
- Do not overstate:
- Limitations/manual checks:

## Review Status
```

The reviewed assessment JSON lives at `work/theses_similarity/assessment.json`.
