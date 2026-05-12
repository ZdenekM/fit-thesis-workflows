# Theses Similarity Report Pipeline Plan

Status: active
Created: 2026-05-12

## Goal

Add an optional, private Theses.cz similarity-report intake and review path for
supervisor and opponent workflows. The workflow should let an operator attach
the post-submission report to a round, preserve the report and its extraction in
the ignored case workspace, produce structured internal evidence when agents are
authorized, and surface only material suspicious or unresolved matches into
supervisor/opponent artifacts.

## Audit Base

Local untracked Theses.cz PDF examples were inspected with `pdfinfo` and
`pdftotext -layout`. The example files were not copied into the repository and
their case details must not be encoded into tracked workflow files.

Structural observations from the examples:

- The report PDFs are text-extractable A4 PDFs generated from the Theses.cz
  report template.
- The first page contains a compared-document summary and an overall similarity
  value.
- The next section lists source documents with source type, title/source name,
  URL-like report link, changed/downloaded date, word count, and similarity
  value.
- Later pages show marked similar passages in the checked document, with source
  numbers linking back to the source-document list.
- The inspected examples confirm that the report exposes overall and per-source
  percentages, but this plan derives no normal range, concern threshold, or
  misconduct signal from sample percentages. Percentages are structural
  descriptors only until interpreted in case context by an authorized reviewer.
- Repeated-submission reports can show very high similarity to an earlier
  version of the same student's work. This is not a plagiarism conclusion by
  itself; it is often expected self-overlap and can also be useful internal
  evidence of how much text changed between attempts.
- The report is time-sensitive, so the workflow must preserve the original PDF,
  extraction time, report generation time when available, and hashes instead of
  assuming a later online view will match the stored report.

Relevant current workflow contracts:

- Private case artifacts belong under `cases/<case-id>/rounds/<round-id>/`.
- Operator workflow commands need Python CLI modules, POSIX wrappers, Pants PEX
  packaging, and generated Windows `.cmd`/`.ps1` launchers.
- Deterministic code must not infer semantic quality, plagiarism, authorship, or
  grading decisions from free-form thesis/report text. It may parse bounded
  structural labels from known report templates and validate explicit structured
  artifacts.
- Generated/internal evidence used as standalone final evidence or as input to a
  sendable/final synthesis must follow the existing agent authorization,
  provenance, role coverage, review manifest, and stale-hash rules.
- In supervisor/opponent reports, absence of a concern should normally stay
  silent. Suspicious or unresolved matches should be investigated and then
  either resolved internally or surfaced carefully in the relevant artifact.

## Scope

In scope:

- Add a private round-local location for Theses.cz report PDFs and extracted
  text.
- Add an explicit import command, not filename-based detection.
- Add a deterministic structural parser/validator for the report template.
- Add a structured assessment contract for human/agent relevance judgments.
- Add internal Markdown evidence `outputs/theses_similarity_review.md`.
- Add manifest, role-coverage, packet, README, skill, and closeout integration
  so supervisor/opponent workflows can consume the evidence consistently.
- Add privacy-guard coverage for new Theses.cz paths and fixture rules so real
  report text cannot leak into tracked test data.
- Add anonymized synthetic fixtures and tests; do not use real reports as
  tracked fixtures.
- Handle repeated-submission self-overlap as a first-class assessment category,
  not as an exception path or hard-coded threshold.

Out of scope:

- Automatically deciding plagiarism, misconduct, grading impact, or report
  wording from a similarity percentage.
- Adding external Theses.cz online scraping or live report refresh.
- Copying real report PDFs, extracted report text, student names, URLs, or
  case-specific match details into tracked repository files.
- Backward compatibility with older `~/code/diplomky` workflows.
- Making the Theses.cz report mandatory for supervisor or opponent workflows.
- Mentioning a clean report in supervisor/opponent prose merely to prove that
  the check happened.

## Evidence Model

Use explicit round-local paths:

- `inputs/theses_similarity/report.pdf` for the imported report PDF.
- `extracted/theses_similarity/report.txt` for the `pdftotext -layout`
  extraction.
- `work/theses_similarity/intake.json` for deterministic structural extraction,
  hashes, and parser limitations.
- `work/theses_similarity/assessment.json` for human/agent relevance judgments.
- `work/theses_similarity/review_draft.md` for generated draft evidence when a
  reviewer loop is needed.
- `outputs/theses_similarity_review.md` for internal evidence. It is final only
  in the scope recorded by the manifest: either covered by a downstream
  synthesis review with `used_findings`, evidence hash, and limitations, or
  standalone-approved through `work/reviews/theses_similarity_review.json`.

The deterministic intake JSON should include:

- schema version, case ID, round ID, producer command, and timestamps;
- report PDF path/hash and extracted text path/hash;
- page count and report generation/evaluation timestamp when parsed from known
  labels;
- compared-document metadata parsed from bounded report structure, plus a
  structural `current_submission_link` field recording whether the report is
  explicitly matched, unverified, or mismatched against the current round inputs;
- source-document entries with rank, source type, title/source name, URL text,
  changed/downloaded date text, word-count text, raw similarity text, normalized
  numeric value where possible, and source line/page references;
- `matched_passages` records with source IDs/ranks, report page/line references,
  checked-document page/line/span references when extractable, extraction
  limitations, and optional private excerpt hashes. These are structural anchors,
  not semantic interpretation.
- parser confidence and limitations, especially when the report template or text
  extraction differs from the known shape.

The assessment JSON should be produced only by an explicitly authorized agent or
human reviewer when it will feed final artifacts. Define
`theses-similarity-assessment-v1` with `case_id`, `round_id`, `generated_at`,
`producer_type`, `producer_role`, `producer_agent`, `authorization_note`,
`source_refs`, `source_sha256`, `limitations`, `current_submission_match`, and
`judgments[]`. Each judgment must include source IDs, passage refs, basis refs,
category, rationale, confidence, evidence refs, synthesis action (`silent`,
`surface`, or `manual_check`), and reviewer-verification requirement. Whole
report conclusions may only summarize anchored item-level assessments.

Typed judgment categories include:

- `no_material_concern`;
- `self_revision_overlap_expected`;
- `self_revision_overlap_unverified`;
- `external_match_needs_review`;
- `external_match_resolved_as_standard_or_common_material`;
- `external_match_resolved_as_cited_and_proportionate`;
- `external_match_cited_but_still_needs_review`;
- `external_match_unresolved`;
- `report_unusable_or_incomplete`.

Materiality routing:

| Category | Default synthesis action |
| --- | --- |
| `no_material_concern` | Stay internal and silent in supervisor/opponent prose. |
| `self_revision_overlap_expected` | Stay internal by default; surface only when useful for a precise resubmission-change discussion. |
| `external_match_resolved_as_standard_or_common_material` | Stay internal by default. |
| `external_match_resolved_as_cited_and_proportionate` | Stay internal by default. |
| `self_revision_overlap_unverified` | Create a materiality `next_action` until resolved or recorded as a typed limitation. |
| `external_match_needs_review` | Create a materiality `next_action`; do not synthesize final wording until resolved or limited. |
| `external_match_cited_but_still_needs_review` | Create a materiality `next_action`; citation alone is not resolution. |
| `external_match_unresolved` | Surface carefully in opponent/supervisor evidence or require manual decision before final wording. |
| `report_unusable_or_incomplete` | Record limitation; surface only if the missing/unusable report itself is material. |

Repeated-submission handling:

- Treat high similarity to an earlier version of the same student's work as a
  self-revision candidate requiring contextual confirmation from case history,
  previous-round artifacts, assignment/defense notes, or operator notes.
- Do not classify self-overlap as suspicious solely from a high percentage.
- Use self-overlap as a qualitative signal. Quantified or strong claims about
  how much changed require `outputs/revision_diff.md` or equivalent
  previous-round evidence, not the Theses.cz percentage alone.
- Surface the issue in supervisor/opponent prose only if it remains suspicious,
  unresolved, required by institutional wording, or useful for a precise
  discussion of resubmission changes.

## Slices

### Slice 1 - Schema And Plan Review

- Status: done
- Proposed commit message: `docs(workflow): plan theses similarity report intake`
- Expected paths:
  - `plans/theses_similarity_report_pipeline_plan.md`
  - `src/thesis_review_workflow/theses_similarity.py`
  - `src/thesis_review_workflow/structured_evidence.py`
  - `src/thesis_review_workflow/cli/check_private.py`
  - `tests/test_theses_similarity.py`
  - `tests/test_check_private.py`
- Tasks:
  - Use the completed 2026-05-12 multi-agent plan review as baseline; rerun
    plan review if implementation materially changes the contract.
  - Define dataclasses or typed dictionaries for deterministic intake and a
    structured `theses-similarity-assessment-v1` reviewer assessment.
  - Encode parser output as structural evidence only; no percentage thresholds,
    plagiarism conclusions, or route decisions.
  - Add anonymized fixtures as Python literals or through a narrow synthetic
    fixture allowlist; do not add real report-like `.txt` files with names,
    URLs, titles, or match text.
  - Extend privacy checks so Theses.cz report PDFs, extracted report text,
    `work/theses_similarity/*.json`, and `outputs/theses_similarity_review.md`
    cannot appear outside ignored case workspaces.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_theses_similarity.py tests/test_check_private.py`
  - `scripts/smoke-private`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 2 - Explicit Report Import Command

- Status: done
- Proposed commit message: `feat(workflow): import theses similarity reports`
- Expected paths:
  - `scripts/import-theses-report`
  - `scripts/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/import_theses_report.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `tests/test_import_theses_report.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-import-theses-report`
- Tasks:
  - Add `scripts/import-theses-report <case-id> [round-id] REPORT.pdf`.
  - Copy the PDF to `inputs/theses_similarity/report.pdf` and fail clearly if a
    report already exists unless an explicit replace mode is added and tested.
  - Extract text to `extracted/theses_similarity/report.txt` through the same
    Poppler path and ignored-path safety contract used for thesis PDFs.
  - Write `work/theses_similarity/intake.json` with file hashes, page count,
    extraction command, structural parser output, current-submission link status,
    source rows, and matched-passage anchors.
  - Keep Windows path handling, non-ASCII filenames, and case-insensitive target
    collisions in tests.
  - Package the command through the standard workflow-tool surface.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_import_theses_report.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-import-theses-report`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 3 - Structural Validator And Manifest Hooks

- Status: done
- Proposed commit message: `feat(workflow): validate theses similarity evidence`
- Expected paths:
  - `scripts/check-theses-similarity-report`
  - `scripts/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/check_theses_similarity_report.py`
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `src/thesis_review_workflow/work_artifacts.py`
  - `src/thesis_review_workflow/artifact_registry.py`
  - `src/thesis_review_workflow/review_approvals.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `tests/test_theses_similarity.py`
  - `tests/test_review_manifest_helpers.py`
  - `tests/test_review_approvals.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-theses-similarity-report`
- Tasks:
  - Add a validator that checks presence, path safety, schema version, hashes,
    extraction freshness, and required structural fields.
  - Validate `work/theses_similarity/assessment.json` structurally when present,
    without requiring it for every round.
  - Register `outputs/theses_similarity_review.md` as internal/operator
    evidence with an explicit `OutputArtifactSpec`.
  - Register `work/theses_similarity/intake.json`,
    `work/theses_similarity/assessment.json`, `work/theses_similarity/review_draft.md`,
    and `work/reviews/theses_similarity_review.json` as supporting work artifacts
    or approval records as appropriate.
  - Add the helper check to `init-review-manifest` and enforce it through
    `check-review-manifest` when any Theses.cz similarity evidence is present:
    raw imported report/extraction, intake, assessment, draft review, final
    review output, or approval record. This deliberately catches partial manual
    imports and stale reconstructed workspaces, while the helper target set
    excludes the approval record so final approval does not have to approve
    itself.
  - Add standalone review-approval support for `outputs/theses_similarity_review.md`
    when it is used as final standalone evidence; otherwise manifest it as
    `covered_by_synthesis` with explicit `used_findings`.
  - Keep the validator free of plagiarism thresholds and semantic route
    decisions.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_theses_similarity.py tests/test_review_manifest_helpers.py tests/test_review_approvals.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-theses-similarity-report`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 4 - Review Skill And Agent Coverage

- Status: pending
- Proposed commit message: `feat(workflow): review theses similarity reports`
- Expected paths:
  - `AGENTS.md`
  - `.agents/skills/thesis-theses-similarity-review/SKILL.md`
  - `.agents/skills/thesis-supervisor-feedback/SKILL.md`
  - `.agents/skills/thesis-supervisor-feedback-review/SKILL.md`
  - `.agents/skills/thesis-supervisor-report/SKILL.md`
  - `.agents/skills/thesis-supervisor-report-review/SKILL.md`
  - `.agents/skills/thesis-opponent-materials/SKILL.md`
  - `.agents/skills/thesis-opponent-materials-review/SKILL.md`
  - `src/thesis_review_workflow/agent_coverage.py`
  - `src/thesis_review_workflow/review_materiality.py`
  - `src/thesis_review_workflow/review_wave_gate.py`
  - `src/thesis_review_workflow/supervisor_packets.py`
  - `src/thesis_review_workflow/supervisor_report_packets.py`
  - `src/thesis_review_workflow/opponent_packets.py`
  - `tests/test_agent_coverage.py`
  - `tests/test_review_materiality.py`
  - `tests/test_review_wave_gate.py`
  - `tests/test_supervisor_packets.py`
  - `tests/test_supervisor_report_packets.py`
  - `tests/test_opponent_packets.py`
- Tasks:
  - Add a repo-local skill for interpreting the report in case context.
  - Require explicit agent authorization before producing
    `outputs/theses_similarity_review.md` for final standalone use or before
    relying on it in supervisor/opponent synthesis.
  - Add the new skill and output/work artifact paths to `AGENTS.md` routing and
    output conventions without expanding it into a procedure.
  - Add a `theses_similarity` materiality role for `supervisor_feedback`,
    `supervisor_report`, and `opponent_review`; imported reports or intake JSON
    create a `next_action` until `outputs/theses_similarity_review.md` exists or
    a typed limitation is accepted.
  - Add role coverage when a Theses.cz report is present and a final/synthesis
    artifact will be generated; allow only typed limitations for unavailable,
    unusable, or out-of-scope reports.
  - Add wave-gate expectations so synthesis does not run before unresolved
    similarity-report `next_actions` are closed.
  - Add role packets that pass the intake JSON, report extraction reference,
    current thesis PDF/extraction references, previous-round references when
    present, and assignment/report context into supervisor-feedback,
    supervisor-report, and opponent-review waves.
  - Make downstream synthesis default to silence when the review finds no
    material concern.
  - Update independent review skills to verify similarity-derived wording,
    enforce clean-report silence, remove report URLs/source internals/hashes from
    sendable prose, and reject plagiarism/authorship wording unless a reviewed
    unresolved concern supports it.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_agent_coverage.py tests/test_review_materiality.py tests/test_review_wave_gate.py tests/test_supervisor_packets.py tests/test_supervisor_report_packets.py tests/test_opponent_packets.py`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 5 - Operator Docs And Closeout Integration

- Status: pending
- Proposed commit message: `docs(workflow): document theses similarity reports`
- Expected paths:
  - `AGENTS.md`
  - `README.md`
  - `docs/agent-scheduling.md`
  - `docs/opponent-review-workflow.md`
  - `templates/round-notes.md`
  - `TODO.md`
  - `plans/theses_similarity_report_pipeline_plan.md`
- Tasks:
  - Update the chat-first README examples to mention optional Theses.cz report
    attachment after system submission.
  - Add `outputs/theses_similarity_review.md` and
    `work/theses_similarity/intake.json`, `work/theses_similarity/assessment.json`,
    and `work/reviews/theses_similarity_review.json` to the output/reference list.
  - Document the default no-mention policy for clean reports and the required
    investigation path for suspicious or unresolved matches.
  - Add the role to agent scheduling without increasing default concurrency.
  - After implementation, delete the `TODO.md` Theses.cz item; if residual work
    remains, add a new open bullet with only the remaining scope, not completed
    history.
- Verification:
  - `pants fmt ::`
  - `pants lint ::`
  - `pants check ::`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

## Progress

- 2026-05-12: Planned from local untracked PDF examples. No real report content
  or file names were added to tracked files.
- 2026-05-12: Reviewed with two read-only agents. Findings were folded into the
  evidence schema, review/approval semantics, materiality routing, privacy
  guard, AGENTS routing, packet integration, and verification commands.
- 2026-05-12: Slice 1 started. Implementing structural parser/schema validation,
  synthetic tests, and privacy guard coverage.
- 2026-05-12: Slice 1 implemented and reviewed. Added structural parsing,
  `theses-similarity-assessment-v1` validation, privacy guard coverage, and
  synthetic tests; reviewer findings tightened hash-bound judgment refs,
  passage anchors, materiality invariants, and numeric marker parsing.
- 2026-05-12: Slice 2 started. Implementing the explicit import command,
  workflow-tool packaging surface, and synthetic smoke coverage.
- 2026-05-12: Slice 2 implemented and reviewed with two agents. Added
  `import-theses-report`, PEX/launcher packaging, synthetic import smoke, and
  tests for non-ASCII source filenames, explicit round selection,
  case-insensitive collisions, symlink path escape refusal, sanitized `pdfinfo`
  limitations, duplicate imports, and cleanup after extraction/publish failures.
  Reviewer findings fixed symlink escape protection, publish cleanup,
  sanitized `pdfinfo` limitation text, and parent-component case-fold collision
  detection. Verification passed: `pants fmt ::`, `pants lint
  src/thesis_review_workflow:: tests:: scripts::`, `pants check
  src/thesis_review_workflow:: tests:: scripts::`, `pants test
  tests/test_import_theses_report.py tests/test_workflow_python_contracts.py`,
  `scripts/smoke-import-theses-report`,
  `scripts/smoke-package-workflow-tools`, `scripts/check-private`,
  `scripts/check-scripts`, and `git diff --check`.
- 2026-05-12: Slice 3 implemented and reviewed with two agents. Added
  `check-theses-similarity-report`, manifest helper hooks, output/work artifact
  registration, review-approval profile, and synthetic validator smoke. Reviewer
  findings fixed stale intake detection against the extracted report text, draft
  privacy scanning, smoke parser coverage, approval helper targets, and
  reviewer-role independence. Verification passed: `pants fmt ::`, `pants lint
  src/thesis_review_workflow:: tests:: scripts::`, `pants check
  src/thesis_review_workflow:: tests:: scripts::`, `pants test
  tests/test_theses_similarity.py tests/test_review_manifest_helpers.py
  tests/test_review_approvals.py tests/test_workflow_python_contracts.py
  tests/test_work_artifacts.py`, `scripts/smoke-theses-similarity-report`,
  `scripts/smoke-review-manifest`, `scripts/smoke-package-workflow-tools`,
  `scripts/check-private`, `scripts/check-scripts`, and `git diff --check`.

## Decision Log

- Use an explicit import command rather than filename-based classification so
  deterministic code never guesses that an arbitrary PDF is a Theses.cz report.
- Store the report as private case evidence. Tracked repository files may contain
  schemas, synthetic fixtures, and workflow rules only.
- Treat repeated-submission self-overlap as a normal contextual category. The
  review may use it to reason about revision extent, but it is not a misconduct
  finding by itself.
- Keep clean reports silent in supervisor/opponent prose. The pipeline records
  internal evidence and provenance; final wording only changes when the report
  creates a material concern, unresolved issue, or explicit institutional need.
- Do not use Theses.cz percentages as revision-diff metrics. They may point to
  self-overlap worth checking, but quantified change claims require revision-diff
  evidence or equivalent previous-round evidence.

## Final Audit

Not started. Before archiving, record the final implementation commits, all
verification commands, skipped checks, native Windows evidence status for the
new packaged commands, and any residual TODO items.
