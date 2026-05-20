# Opponent Report Quality Feedback Intake

Use this template only to abstract already-handled feedback into case-neutral
workflow input. It is not a replacement path for concrete report corrections.
If feedback should change the current opponent report, first route it through
the existing ignored workflow path:

```text
notes/opponent-report-operator-feedback.md
  -> work/opponent_report_revision_request.json
  -> work/opponent_report_trace.json calibration_context
  -> regenerated canonical draft and clean export
  -> independent opponent-report review
```

Do not fill this tracked template with real student data. For concrete batches,
copy it to `cases/<case-id>/rounds/<round-id>/notes/` or another ignored private
workspace. Promote only abstracted recurring lessons into tracked workflow
files after the current case artifact has been repaired and reviewed.

## Source Status

- Feedback source:
- Date received:
- Reviewer/operator:
- Related workflow surface:
- Is this feedback about a concrete case? yes/no
- If yes, was the existing revision path completed or declared not applicable?
  yes/no/not applicable
- Ignored intake copy path:
- Are all private names, case ids, thesis topics, exact points, grades, source
  paths, and case-specific findings removed from tracked notes? yes/no

## Feedback Classification

Choose exactly one primary classification before promotion:

- Case-specific feedback: applies only to the current thesis/report.
- Durable private reviewer preference: belongs in an ignored
  `profiles/local/*` profile only after explicit operator approval.
- General workflow rule: may be promoted into a skill, doc, template, checker,
  profile default, or TODO.

Classification:
Reason:

## Routing Decision

Choose all that apply before any tracked promotion:

- Current-case report correction through
  `notes/opponent-report-operator-feedback.md` and
  `work/opponent_report_revision_request.json`.
- Current report calibration update through `work/report_calibration_basis.json`
  and trace `calibration_context`.
- Durable private reviewer preference for `profiles/local/*`, only after
  explicit operator approval.
- Historical calibration candidate handled by the private historical opponent
  calibration workflow.
- Public workflow rule, template, checker, or docs update.
- No durable promotion.

Routing:
Operator approval for private profile change:

## Case-Specific Details To Discard

List concrete details that must not be copied into tracked workflow files:

- Student identity, case id, round id:
- Thesis topic, domain, technologies, datasets, products, or platforms:
- Assignment wording or artifact names:
- Concrete measurements, participant counts, source citations, or screenshots:
- Points, grade, grade-boundary alternatives, or exact defense questions:
- Private report excerpts or local workspace paths:

## Abstract Recurring Pattern

State the reusable pattern without case facts:

- Pattern summary:
- Why it is likely to recur:
- Affected report areas:
- Evidence classes involved:
- Risk if workflow stays unchanged:

## Proposed Durable Layer

Select the narrowest useful layer. Do not create a new mechanism when an
existing skill, trace field, calibration basis, role-owned evidence output, or
checker can own the improvement.

- Repo-local skill:
- `docs/fit-is-rubric.md`:
- `docs/opponent-review-workflow.md`:
- `profiles/default.md` for generic public preferences only:
- Deterministic checker:
- Template:
- `TODO.md` for public workflow automation only:
- No tracked promotion:

Proposed layer:
Reason:

## Existing Owner Check

Before adding anything new, check whether the same concern is already owned by:

- `notes/opponent-report-operator-feedback.md`
- `work/opponent_report_revision_request.json`
- `work/opponent_report_trace.json` `calibration_context`
- `work/opponent_report_trace.json`
- `work/report_calibration_basis.json`
- `work/assignment_coverage_agent.json`
- `work/quantitative_claims.json`
- `work/context/claim_review_basis.json`
- `work/context/evidence_capsules.json`
- `work/evidence_requirements.json`
- `work/current_evidence_snapshot.json`
- `outputs/code_consistency.md`
- `outputs/code_quality_review.md`
- `outputs/literature_citation_review.md`
- `outputs/figure_media_review.md`
- `outputs/typography_formal_review.md`

Existing owner:
Required change to owner:

## Compactness Check

- Would the promoted rule increase public report length? yes/no
- Can the detail stay in internal evidence while the clean report keeps a short
  IS-field synthesis? yes/no
- If a trace/control field is proposed, is it limited to ids, safe refs, enums,
  one-line summaries, and wording mode rather than copying role evidence?
  yes/no

## Promotion Candidate

- Candidate wording or contract change:
- Evidence that the pattern is recurring:
- Checker or validation impact:
- Privacy risk:
- Report-length risk:
- Decision: promote / defer / discard
- Follow-up path:
