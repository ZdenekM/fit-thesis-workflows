# Raw Text Processing Audit

Date: 2026-05-07

## Goal

Clarify where deterministic workflow code still interprets free-form text and
where that should be replaced by agent-produced structured evidence.

General rule: agents/LLMs interpret free-form thesis, README, notes, generated
prose, and code text. Deterministic code consumes structured data, validates
schemas and provenance, parses known structural forms, and checks internal
workflow hygiene.

## Policy

Allowed deterministic parsing:

- structured metadata labels in `case.md`, round notes, manifests, TSV/JSON/YAML,
  and generated workflow artifacts;
- documented Markdown section headings, tables, list structure, and placeholder
  markers;
- explicit URLs and out-of-scope markers used only for evidence routing, such as
  GitHub intake hints in round notes;
- file names, suffixes, archive entries, command output markers, hashes, and
  path/privacy leak patterns;
- syntax-level or numeric sanity checks over already-structured values;
- advisory detectors that only produce prompts for agent/human verification.

Not allowed as new workflow behavior:

- keyword, regex, or token matching over raw thesis/code/README/notes/generated
  prose that directly creates a semantic finding;
- free-text matching that decides readiness, role routing, migration, report
  wording, feedback wording, grading, or artifact trust;
- domain-specific lexical rules that silently replace an agent review.

When semantic text understanding is needed, add or reuse an agent workflow that
writes a structured artifact with evidence anchors, then validate that artifact
deterministically.

## Audit Findings

### Keep As Structural Parsing

- `src/thesis_review_workflow/metadata.py`: parses known metadata labels and
  language values. This is structural.
- `src/thesis_review_workflow/case_doctor_summary.py`,
  `src/thesis_review_workflow/agent_coverage.py`, and
  `src/thesis_review_workflow/code_workspace.py`: classify paths, suffixes, and
  archive entries to route code/text/media preparation. These are structural
  routing hints, not semantic findings, but should stay conservative and
  overrideable through explicit metadata when that becomes available.
- `src/thesis_review_workflow/cli/opponent_preflight.py` and
  `src/thesis_review_workflow/cli/check_tooling.py`: detect explicit GitHub URLs
  and explicit out-of-scope markers in round notes. This is accepted as
  structural evidence routing because it points to a concrete external evidence
  source and requires either GitHub intake or an explicit operator marker; it
  must not infer contribution quality or code ownership from the URL text.
- `src/thesis_review_workflow/cli/check_feedback_output.py`,
  `src/thesis_review_workflow/cli/check_opponent_materials.py`,
  `src/thesis_review_workflow/cli/check_figure_media_review.py`, and
  `src/thesis_review_workflow/internal_evidence_validators.py`: validate
  generated artifacts for placeholders, required headings, privacy/path leaks,
  internal workflow terms, and schema-like evidence anchors. These are output
  hygiene checks, not thesis/code interpretation.
- `src/thesis_review_workflow/evaluation_claims.py`: table/number/unit parsing
  is acceptable only as numeric sanity scaffolding. Any interpretation of what a
  result means must stay agent/human-reviewed.

### Advisory Until Replaced

- `src/thesis_review_workflow/cli/check_evaluation_claims.py` and
  `src/thesis_review_workflow/evaluation_claims.py`: use metric/conclusion/unit
  regexes over extracted thesis text. The CLI already says it is a reviewer
  prompt, not a verdict engine. Keep it warning-only until an agent creates a
  structured quantitative-claims artifact.
- `src/thesis_review_workflow/cli/check_typography_formal.py`: uses some regexes
  over rendered thesis text for typography/formal warnings and may auto-detect a
  language family only when structured metadata is `auto` or missing. Keep
  explicit `Thesis language` metadata preferred, and keep rendered-text-derived
  checks warning-only.
- `src/thesis_review_workflow/evidence_presence.py`: detects media/demo and
  metric/evaluation language from assignment/extracted text/notes. This is useful
  as a prompt, but the recurring replacement should be structured evidence
  requirements produced by an agent from the assignment and case context.
- `src/thesis_review_workflow/assignment_coverage.py`: token-overlap coverage is
  advisory and can miss paraphrases or over-match shared vocabulary. Replace the
  semantic coverage state with an agent-authored assignment-coverage artifact;
  deterministic code can still validate schema and evidence anchors.
- `src/thesis_review_workflow/cli/draft_opponent_report.py`: maps reviewed
  materials to IS report items using normalized tokens. This should move toward
  explicit structured IS-item fields in reviewed opponent materials.
- `src/thesis_review_workflow/cli/check_opponent_report.py`: preserves
  uncertainty through token matching between reviewed materials and draft report.
  The audit demoted free-prose uncertainty wording checks to warnings. Replace
  these with a structured uncertainty ledger or reviewed-materials field consumed
  by the report checker.

### No Immediate Blocker Found

The audit did not find a deterministic helper that currently produces a final
grade, final feedback wording, final opponent finding, or case migration decision
solely from a free-text substring match. Explicit GitHub URL detection remains a
structural evidence-routing gate, not semantic text interpretation. Semantic
uncertainty-wording hard errors in `scripts/check-opponent-report` were
downgraded to warnings during the audit. The main residual risk is that several
useful warning/advisory tools still read raw text directly. `TODO.md` now tracks
their replacement with agent-produced structured evidence.

## Follow-Up Shape

A future implementation plan should introduce small structured artifacts before
retiring the advisory helpers:

- `work/quantitative_claims.json`: agent-extracted metric/result claims with
  evidence anchors, units, baselines, and limitations.
- `work/evidence_requirements.json`: agent-extracted required/present/missing
  evidence classes from assignment, notes, and inputs.
- `work/assignment_coverage_agent.json`: agent-verified coverage of assignment
  points in materials/drafts.
- explicit IS-item fields and uncertainty ledger in reviewed opponent materials.

Those artifacts can then be checked deterministically for schema, paths, hashes,
review status, and completeness.
