# Historical Opponent Calibration Plan

Status: active
Created: 2026-05-07

## Goal

Add a private historical-opponent-report calibration workflow in two layers:

1. analyze several historical opponent cases and synthesize a private reviewer
   calibration profile plus a reusable checklist of what this reviewer typically
   checks;
2. use that profile in new opponent cases to produce broader operator materials,
   a calibrated report draft, and an iterative revision loop driven by the
   operator's feedback.

This is not model fine-tuning. V1 is artifact-based calibration: explicitly
authorized agents read private historical cases, write a narrative private
reviewer profile plus structured companion artifacts with evidence anchors, and
later opponent workflows consume those artifacts as reviewer-profile context.

The reviewer profile is a living private artifact. After each newly completed
opponent case, the operator may add the final report and case context back into
the calibration workspace as another analyzed case, then refresh the profile and
checklist with provenance. Refreshes must preserve prior profile versions and
record what changed rather than silently overwriting the calibration baseline.

## Audit Base

Current relevant state:

- Historical/reference opponent reports are currently only a P2 TODO idea:
  optional `outputs/reference_report_comparison.md` after reviewed opponent
  materials exist.
- Case data under `cases/` is ignored and must stay private. Historical
  opponent reports, theses, source zips, notes, and generated calibration
  outputs must not be tracked.
- The current structured-evidence migration is complete. Deterministic helpers
  validate structured artifacts such as `work/assignment_coverage_agent.json`,
  `work/evidence_requirements.json`, `work/quantitative_claims.json`, and
  `work/opponent_report_trace.json`; they must not interpret raw report/thesis
  prose semantically.
- `scripts/draft-opponent-report` is a deterministic bridge from
  `work/opponent_report_trace.json` to `work/oponent_posudek_draft.md`. Style
  and judgment calibration must therefore happen before or around the trace,
  through authorized agents and structured artifacts.
- Existing opponent closeout gates validate reviewed materials, report trace,
  manifest, agent coverage, and any existing report draft.

Plan-creation checks:

```bash
git status --short --untracked-files=all
sed -n '1,220p' plans/README.md
sed -n '1,180p' TODO.md
sed -n '1,220p' docs/raw-text-processing-audit.md
```

## Scope

In scope:

- A private calibration workspace contract under ignored `cases/`.
- Structured schemas for historical case analyses, a reviewer calibration
  profile, and reviewer checklist prompts.
- Repo-local skill/doc updates for historical calibration and calibrated
  opponent-report drafting.
- A per-case workflow that uses the private profile after
  `outputs/oponent_podklady_revidovane.md` and `work/opponent_report_trace.json`
  exist.
- `outputs/reference_report_comparison.md` as an operator-only calibration
  artifact for a current case.
- An operator feedback loop where the reviewer writes requested changes/checks
  and an authorized agent revises the trace/draft with provenance.
- Synthetic tests/smokes only. Real historical reports remain private.

Non-goals:

- Training or fine-tuning a model.
- Adding real historical reports, real theses, real source zips, or private
  profile outputs to git.
- Treating historical reports as evidence about a new student's work.
- Deterministic keyword matching over historical or current free-form report
  text to infer style, severity, grading, or findings.
- Backward compatibility with older `~/code/diplomky` workflows.
- A large UI or database. Use private case files, skills, Markdown, and small
  helpers only where they remove repeated manual work.

## Privacy And Workspace Contract

Historical calibration data lives under an ignored calibration case, for example:

```text
cases/opponent-calibration-zm/
  case.md
  current-round.txt
  rounds/
    2026-05-07-historical-pilot/
      inputs/
        historical_cases/
          case-001/
            assignment.*
            thesis.*
            source-or-code.*
            opponent_report.md
            notes.md
          case-002/
            ...
      work/
        calibration/
          historical_case_analyses/
            case-001.json
            case-002.json
            case-003.json
          reviewer_calibration_profile.json
          reviewer_calibration_profile_history.jsonl
          reviewer_checklist.json
          reviewer_profile_change_log.md
          profile_review.md
      outputs/
        reviewer_calibration_profile.md
```

Rules:

- This whole workspace is private because `cases/` is ignored.
- Tracked docs and tests may contain only synthetic fixtures.
- If a reusable reviewer profile is exported outside a case, it must still live
  in an ignored path unless the user explicitly requests a sanitized public
  profile.
- Profile artifacts may summarize style, strictness, and checklist tendencies,
  but should avoid long verbatim excerpts from historical reports.

## Relationship To Reviewer Profiles

Historical opponent calibration is a supplemental, case-local advisory layer. It
does not replace the existing `Reviewer profile` field in `case.md`, and it must
not satisfy or bypass `scripts/check-reviewer-profile` or
`scripts/check-round-ready`.

Current opponent workflows continue to require the normal public/private
reviewer profile readiness contract. Historical calibration may be used only
after `work/opponent_calibration_use.json` records the selected private
calibration profile path, profile hash, checklist hash, scope, applicability,
limitations, and explicit operator approval. If no calibration profile exists,
`work/opponent_calibration_advisory.json` records the non-blocking suggestion
and the workflow proceeds without calibrated style/strictness guidance.

## Generated Artifact Review And Provenance

Markdown artifacts under `outputs/` that are produced by this workflow are
operator evidence. They must not be treated as reliable or used for downstream
drafting until provenance and review state are recorded.

Rules:

- `outputs/reviewer_calibration_profile.md`,
  `outputs/reference_report_comparison.md`, and
  `outputs/opponent_reading_packet.md` require review-manifest entries with
  generated-by records, independent review records, reviewed hashes, source
  refs, limitations, and stale-hash detection before downstream use.
- If an artifact shape is still experimental, write it under `work/` as a draft
  and do not register it as an `outputs/` artifact.
- When the artifact becomes a stable `outputs/` artifact, the same slice must
  update `review_manifest.OUTPUT_TYPES`, `init_review_manifest.OUTPUT_TYPES`,
  `INTERNAL_EVIDENCE`, private-artifact checks, case-doctor/output summaries
  where relevant, and agent-coverage inference if the artifact is final or
  feeds final drafting.
- Current-case comparison and reading-packet artifacts need an independent
  anti-overfit review before their profile-driven suggestions may influence the
  opponent report trace or draft.
- Material edits to a profile, comparison, reading packet, revision request, or
  trace reopen the review state and require refreshed hashes before closeout.

## Quality Controls

The calibration workflow must improve report usefulness without overfitting to
old reports. Add these controls before the profile can influence a current
opponent-report draft:

- Corpus coverage metadata: every historical case analysis records work type,
  approximate year, domain, artifact availability, code availability, grade/point
  band if available, and whether the case is strong, typical, weak, or
  atypical. This lets the profile report where it has evidence and where it is
  extrapolating.
- Applicability scoring: every current-case use of the profile records whether
  the current thesis resembles the private calibration corpus by work type,
  domain, artifact availability, code/reproducibility scope, result style, and
  expected grading band.
- Confidence by dimension: the profile and current-case comparison carry
  confidence separately for style, grading, severity, defense questions,
  evidence expectations, and checklist coverage.
- Anti-overfit review: an independent reviewer checks that calibrated wording
  and grading suggestions are supported by the current case, not merely by
  historical reviewer habits.
- Operator reading packet: the current-case workflow should produce a stable
  operator-facing packet before the final draft is treated as useful. The packet
  should include: what is well-supported, what is uncertain, major evaluation
  axes, suggested point/grade interval, differences from the reviewer profile,
  defense questions, and manual checks still worth doing.
- Soft calibration advisory: when no historical calibration profile is available,
  operator-facing commands may remind the opponent that adding historical
  reports improves style and grading calibration. This must be a non-blocking
  advisory, never a readiness gate or required input.
- Feedback taxonomy: operator feedback should be normalized into categories
  such as `evidence_request`, `grading_calibration`, `tone_style`,
  `missing_check`, `factual_correction`, `wording_preference`,
  `defense_question`, and `scope_limitation`.
- Private sentinel set: after the pilot, keep 2-3 private calibration cases as a
  non-tracked regression set for profile refreshes and prompt/workflow changes.
  Sentinel checks are private evaluations, not public fixtures.

## Artifact Contracts

All semantic artifacts below are authored by an explicitly authorized agent or
human reviewer. Deterministic code may validate schema, refs, hashes, and
completeness only.

Deterministic validators need both exact-path and path-classified artifact
support:

- exact paths for current-case artifacts such as
  `work/opponent_calibration_use.json`;
- wildcard/path-class contracts for
  `work/calibration/historical_case_analyses/<historical-case-id>.json`;
- JSONL line validation for
  `work/calibration/reviewer_calibration_profile_history.jsonl`;
- safe path-stem checks for historical case ids.

Common fields:

- `schema_version`
- `reviewer_profile_id`
- `case_id`
- `round_id`
- `generated_at`
- `producer_type`: `agent` or `human`
- `producer_role`
- `producer_agent`: string or `null`
- `source_refs`
- `limitations`
- `authorization_note` or `human_reviewer_note`

### `work/calibration/historical_case_analyses/<case>.json`

Schema version: `historical-opponent-case-analysis-v1`

Purpose: one structured analysis per historical case. The agent reads the
historical thesis/assignment/code/report and records how the reviewer judged the
case.

Minimum content:

- case metadata: work type, phase if known, approximate year if known, domain,
  grade/point band if available, artifact availability, code availability, and
  whether the case is strong, typical, weak, or atypical;
- report shape: section structure, length class, question style, grading style;
- judgment calibration: strictness, what moved the grade up/down, how
  uncertainty was handled;
- evidence habits: what the report relied on, what it left for manual check;
- recurring checks suggested by this case;
- evidence refs into private historical inputs;
- limitations for missing assignment/code/thesis evidence.

Path contract:

- `<case>` must be a safe id using the same conservative character set as case
  ids.
- The payload records the same id in `historical_case_id`.
- Source refs must stay round-relative and point only into private round
  `inputs/`, `extracted/`, `notes/`, `work/`, or `outputs/`.

### `outputs/reviewer_calibration_profile.md`

Purpose: authoritative private reviewer profile across historical cases.

This should be a readable agent-written Markdown document, not a table forced
into a rigid schema. It is the artifact an opponent can read and the context
that later authorized agents may use when drafting or calibrating opponent
materials. Deterministic helpers must not semantically parse the prose; they may
only validate structural presence, record hashes, and pass the profile to an
authorized agent workflow.

Recommended sections:

- reviewer stance and overall judgment style;
- recurring evidence expectations before making strong claims;
- recurring checks worth performing in new opponent reviews;
- severity calibration: what usually counts as major, moderate, or minor;
- grading and point-calibration habits, including how uncertainty is expressed;
- preferred defense-question style;
- tone, structure, concision, and wording preferences;
- cautions and `do_not_overfit` guidance;
- profile applicability and confidence by dimension;
- source-case anchors and limitations.

### `work/calibration/reviewer_calibration_profile.json`

Schema version: `opponent-reviewer-calibration-profile-v1`

Purpose: machine-checkable manifest for the Markdown reviewer profile.

The JSON companion should not try to represent the whole reviewer profile. It
keeps versioning, provenance, hashes, applicability metadata, confidence, and
limitations so deterministic helpers can validate and route the artifact without
interpreting free-form prose.

Minimum content:

- `profile_markdown_path`: path to `outputs/reviewer_calibration_profile.md`;
- `profile_markdown_sha256`: hash of the Markdown profile;
- `profile_applicability`: where the profile should be used confidently,
  cautiously, or not at all;
- `source_case_refs`: the historical analyses used;
- `profile_version`: monotonically increasing private profile version;
- `profile_previous_sha256`: previous profile hash or `null` for the first
  profile;
- `profile_change_summary`: what changed since the previous version;
- `confidence_by_dimension`: confidence for style, grading, severity,
  questions, evidence expectations, and checklist coverage;
- `do_not_use_for`: boundaries such as conclusions, grading, or wording that
  must still be derived from current-case evidence;
- `limitations`: corpus gaps and known risks.

### `work/calibration/reviewer_checklist.json`

Schema version: `opponent-reviewer-checklist-v1`

Purpose: reusable "what to check" prompts distilled from historical cases.

Checklist entries must be evidence-class based, not substring based. Examples:

- assignment fulfillment and explicit mapping to zadani;
- reproducibility evidence and code run instructions;
- experiment baseline/context/unit sanity;
- figure/table/result readability;
- literature relevance and whether citations support claims;
- clarity of own contribution versus library/tool usage;
- defense questions that clarify uncertain but material points.

### `work/calibration/reviewer_calibration_profile_history.jsonl`

Schema version per line: `opponent-reviewer-calibration-history-v1`

Purpose: append-only private history of profile refreshes. Each line records the
profile version, input case analyses, previous/current profile hashes, reviewer
agent, independent review status, and a short change summary.

### `work/calibration/reviewer_profile_change_log.md`

Purpose: human-readable private log of what changed after each new historical or
completed opponent case was incorporated.

### Current-case calibration artifacts

In a normal opponent case, after reviewed materials and trace exist:

- `work/opponent_calibration_use.json`: schema
  `opponent-calibration-use-v1`; selected private calibration profile id,
  manifest path/hash, Markdown profile path/hash, checklist path/hash, source
  reviewed-materials path/hash, source trace path/hash, scope, profile
  applicability assessment, confidence by dimension, limitations, operator
  approval, and approval note. This is supplemental context only and never
  replaces `Reviewer profile` readiness.
- `work/opponent_calibration_advisory.json`: schema
  `opponent-calibration-advisory-v1`; optional structural record that no
  profile was selected or available, why no profile was used, whether the
  non-blocking historical-report suggestion was shown, whether the operator
  chose to proceed without calibration, advisory timestamp, and limitations.
- `outputs/reference_report_comparison.md`: operator-only comparison between the
  current reviewed materials/trace/draft and the private reviewer profile. It
  should identify likely style/calibration differences, missing checks, grading
  tension, and suggested manual follow-ups. It is reviewed internal evidence and
  must have manifest source hashes for reviewed materials, trace, profile
  manifest, profile Markdown, checklist, and either calibration-use or advisory
  artifact.
- `outputs/opponent_reading_packet.md`: operator-facing packet that summarizes
  supported findings, uncertainties, grading tension, profile differences,
  defense questions, and manual checks in a stable reading order. It is reviewed
  internal evidence and must not be used to revise the trace until its reviewed
  hash is current.
- `notes/opponent-report-operator-feedback.md`: operator feedback after reading
  the broad materials and draft.
- `work/opponent_report_revision_request.json`: structured version of the
  operator feedback, created by an authorized agent or human reviewer, using the
  feedback taxonomy from this plan. Schema
  `opponent-report-revision-request-v1`; required fields include operator
  feedback path/hash, trace path/hash, reviewed-materials path/hash, selected
  calibration-use or advisory path/hash, comparison path/hash if present,
  reading-packet path/hash if present, typed feedback items, requested extra
  checks, limitations, and authorization or human-review note.
- updated `work/opponent_report_trace.json` and regenerated
  `work/oponent_posudek_draft.md`, with manifest evidence that the revision used
  the current operator feedback and current profile hash.

### Calibrated report trace bindings

When calibration or operator-feedback revision affects
`work/opponent_report_trace.json`, the trace gains an optional
`calibration_context` object. Validators must require it whenever the trace or
draft claims to have used historical calibration or operator feedback.

Minimum fields:

- `calibration_use_path` and `calibration_use_sha256`, or
  `calibration_advisory_path` and `calibration_advisory_sha256`;
- `reference_report_comparison_path` and
  `reference_report_comparison_sha256` when the comparison influenced the trace;
- `opponent_reading_packet_path` and `opponent_reading_packet_sha256` when the
  packet influenced the trace;
- `revision_request_path` and `revision_request_sha256` when operator feedback
  was applied;
- `anti_overfit_review_status`, reviewer role, reviewer agent or human note,
  reviewed hash, and limitations.

`scripts/check-opponent-report` must fail on stale or missing calibration
bindings whenever a calibrated trace/draft is used.

## Slices

### Slice 1: Calibration Workspace, Privacy, And Schema Contracts

Status: done

Actions:

- Define the private calibration workspace contract in a focused doc, likely
  `docs/historical-opponent-calibration.md`.
- Document the soft advisory shown when no historical profile exists: adding
  historical opponent reports is recommended for better calibration but must not
  be required for opponent materials, report traces, drafts, or closeout.
- Add schema names and validator stubs for calibration artifacts, including a
  path-classifier for `work/calibration/historical_case_analyses/*.json` and
  JSONL validation for `reviewer_calibration_profile_history.jsonl`.
- Register synthetic calibration artifacts in work-artifact collection only if
  they appear under ignored `work/calibration/`.
- Extend `scripts/check-private` and `scripts/smoke-private` coverage for
  reviewer calibration profiles, reading packets, calibration use/advisory JSON,
  profile history, revision requests, and operator feedback artifacts if they
  appear outside ignored `cases/`.
- Add tests with synthetic data for safe refs, required fields, producer
  metadata, no absolute paths, corpus coverage metadata, profile applicability,
  confidence-by-dimension, and profile hash binding.
- Record that historical calibration is supplemental and cannot replace
  `Reviewer profile` readiness.
- Update `TODO.md` to point the historical-reference P2 item to this plan.

Verification:

```bash
pants fmt src/thesis_review_workflow:: tests::
pants lint src/thesis_review_workflow:: tests::
pants check src/thesis_review_workflow:: tests::
pants test tests/test_opponent_calibration.py tests/test_work_artifacts.py tests/test_structured_evidence.py tests/test_workflow_python_contracts.py
scripts/smoke-private
scripts/check-private
scripts/check-scripts
git diff --check
```

Commit target:

- `feat(workflow): add opponent calibration artifact contracts`

### Slice 2: Historical Case Analysis Workflow

Status: pending

Actions:

- Add a repo-local skill or focused doc section for analyzing one historical
  case with agents.
- The agent reads one private historical case and writes
  `work/calibration/historical_case_analyses/<case>.json`.
- The case analysis records corpus coverage metadata so later profile synthesis
  can distinguish broad reviewer habits from narrow-case artifacts.
- Add the operator-facing validator command
  `scripts/check-opponent-calibration-case <calibration-case-id> [round-id]`.
  This requires `src/thesis_review_workflow/cli/check_opponent_calibration_case.py`,
  `src/thesis_review_workflow/commands.py`, `scripts/BUILD`, the POSIX wrapper,
  package-tool metadata, and generated `.cmd`/`.ps1` launchers through the
  existing package workflow.
- Add synthetic smoke coverage for a private-like calibration case fixture.
- Record that this workflow requires explicit current-request agent
  authorization. Without it, stop before reading private historical materials or
  writing semantic analysis artifacts.

Verification:

```bash
pants fmt src/thesis_review_workflow:: tests:: scripts::
pants lint src/thesis_review_workflow:: tests:: scripts::
pants check src/thesis_review_workflow:: tests:: scripts::
pants test tests/test_opponent_calibration.py tests/test_workflow_python_contracts.py
scripts/smoke-opponent-calibration-case
scripts/smoke-package-workflow-tools
scripts/check-private
scripts/check-scripts
git diff --check
```

Commit target:

- `feat(workflow): analyze historical opponent cases`

### Slice 3: Reviewer Profile And Checklist Synthesis

Status: pending

Actions:

- Add the synthesis workflow that consumes at least two historical case analyses
  and writes the Markdown-first `outputs/reviewer_calibration_profile.md`,
  `reviewer_calibration_profile.json` manifest, and `reviewer_checklist.json`.
- Write the first `reviewer_calibration_profile_history.jsonl` entry and
  `reviewer_profile_change_log.md`.
- Require an independent agent review of the synthesized profile before it is
  used in current cases.
- Make the profile carry limitations when the pilot corpus is small or skewed.
- Ensure checklist entries are phrased as evidence classes and review prompts,
  not deterministic routing rules.
- Include `profile_applicability` and `confidence_by_dimension` in the profile.
- Ensure deterministic code never derives semantic behavior from the Markdown
  profile text directly; it can validate the manifest and hand the profile to an
  authorized agent.
- Add an independent anti-overfit reviewer pass that checks whether the profile
  is phrased as calibration guidance rather than reusable conclusions.
- Register `outputs/reviewer_calibration_profile.md` in review-manifest metadata
  as reviewed internal evidence for the private calibration case.

Verification:

```bash
pants fmt src/thesis_review_workflow:: tests:: scripts::
pants lint src/thesis_review_workflow:: tests:: scripts::
pants check src/thesis_review_workflow:: tests:: scripts::
pants test tests/test_opponent_calibration.py tests/test_review_manifest_helpers.py
scripts/smoke-opponent-calibration-profile
scripts/smoke-package-workflow-tools
scripts/check-private
scripts/check-scripts
git diff --check
```

Commit target:

- `feat(workflow): synthesize opponent reviewer profile`

### Slice 4: Incremental Profile Refresh

Status: pending

Actions:

- Add a workflow for incorporating an additional historical case or a newly
  completed current opponent report into the private calibration corpus.
- The workflow creates a new
  `work/calibration/historical_case_analyses/<case>.json`, compares it against
  the current profile, and writes a new profile version only after independent
  review.
- Preserve the previous profile file hash in `profile_previous_sha256`, append a
  history entry, and update `reviewer_profile_change_log.md`.
- Require explicit operator approval before the refreshed profile becomes the
  default profile for future opponent cases.
- Add checks that fail if a profile refresh silently drops source case refs,
  overwrites history, or reuses a stale previous hash.
- Keep refresh commands operator-facing and Windows-aware if they are exposed as
  `scripts/*`; otherwise keep them as doc/skill procedures plus synthetic smoke
  helpers.

Verification:

```bash
pants fmt src/thesis_review_workflow:: tests:: scripts::
pants lint src/thesis_review_workflow:: tests:: scripts::
pants check src/thesis_review_workflow:: tests:: scripts::
pants test tests/test_opponent_calibration.py tests/test_work_artifacts.py
scripts/smoke-opponent-calibration-profile
scripts/smoke-package-workflow-tools
scripts/check-private
scripts/check-scripts
git diff --check
```

Commit target:

- `feat(workflow): refresh opponent reviewer calibration profile`

### Slice 5: Current-Case Calibration Selection Contracts

Status: pending

Actions:

- Add a workflow that can be run only after
  `outputs/oponent_podklady_revidovane.md` and
  `work/opponent_report_trace.json` exist.
- Add validators and tests for `work/opponent_calibration_use.json` and
  `work/opponent_calibration_advisory.json`, including source material/trace
  hashes, profile manifest/hash, checklist hash, operator approval, no-profile
  reason, applicability, confidence, and limitations.
- If no profile exists, write a non-blocking advisory record and continue with
  uncalibrated comparison/reading-packet language rather than failing.
- Compute and record profile applicability for the current case before using the
  profile for grading/style suggestions.
- Ensure the existing `Reviewer profile` readiness check still runs independently
  and historical calibration cannot satisfy it.
- Add stale-hash tests for selected profile/checklist/materials/trace bindings.

Verification:

```bash
pants fmt src/thesis_review_workflow:: tests:: scripts::
pants lint src/thesis_review_workflow:: tests:: scripts::
pants check src/thesis_review_workflow:: tests:: scripts::
pants test tests/test_opponent_calibration.py tests/test_structured_evidence.py tests/test_review_manifest_helpers.py
scripts/smoke-opponent-report
scripts/smoke-package-workflow-tools
scripts/check-private
scripts/check-scripts
git diff --check
```

Commit target:

- `feat(workflow): select opponent calibration context`

### Slice 6: Reference Comparison And Reading Packet

Status: pending

Actions:

- Write `outputs/reference_report_comparison.md` as an internal operator
  artifact comparing the current materials/trace/draft against the profile:
  judgment shape, likely missing checks, grading interval tension, wording
  style, and defense-question fit.
- Write `outputs/opponent_reading_packet.md` in a stable order: supported
  findings, uncertainties, main evaluation axes, suggested point/grade interval,
  differences from the profile, defense questions, and manual checks.
- Add an anti-overfit review that flags any profile-driven suggestion not
  supported by current-case evidence.
- Explicitly state that historical reports are calibration context, not primary
  evidence for the new case.
- Update `review_manifest.OUTPUT_TYPES`, `init_review_manifest.OUTPUT_TYPES`,
  `INTERNAL_EVIDENCE`, private-artifact checks, and case-doctor/output summaries
  for both Markdown outputs in the same slice that makes them stable.
- Require independent review records and current reviewed hashes before either
  output can influence report-trace revision.

Verification:

```bash
pants fmt src/thesis_review_workflow:: tests:: scripts::
pants lint src/thesis_review_workflow:: tests:: scripts::
pants check src/thesis_review_workflow:: tests:: scripts::
pants test tests/test_opponent_calibration.py tests/test_review_manifest_helpers.py
scripts/smoke-opponent-report
scripts/smoke-opponent-closeout
scripts/smoke-package-workflow-tools
scripts/check-private
scripts/check-scripts
git diff --check
```

Commit target:

- `feat(workflow): compare opponent materials with reviewer profile`

### Slice 7: Operator Feedback Revision Request

Status: pending

Actions:

- Define `notes/opponent-report-operator-feedback.md` as the operator handoff
  surface after reading the broad materials and draft.
- Add an authorized-agent workflow that turns operator feedback into
  `work/opponent_report_revision_request.json`.
- Normalize operator feedback into typed items:
  `evidence_request`, `grading_calibration`, `tone_style`, `missing_check`,
  `factual_correction`, `wording_preference`, `defense_question`, or
  `scope_limitation`.
- Bind the revision request to current operator feedback, reviewed materials,
  trace, calibration-use or advisory artifact, comparison, and reading packet by
  path and hash.
- Require explicit current-request agent authorization, or a human reviewer note,
  before writing the structured revision request.

Verification:

```bash
pants fmt src/thesis_review_workflow:: tests:: scripts::
pants lint src/thesis_review_workflow:: tests:: scripts::
pants check src/thesis_review_workflow:: tests:: scripts::
pants test tests/test_opponent_calibration.py tests/test_review_manifest_helpers.py
scripts/smoke-opponent-report
scripts/check-private
scripts/check-scripts
git diff --check
```

Commit target:

- `feat(workflow): structure opponent report revision requests`

### Slice 8: Calibrated Trace And Draft Binding

Status: pending

Actions:

- Let the agent update `work/opponent_report_trace.json` using current evidence,
  selected reviewer profile, `reference_report_comparison.md`, and operator
  feedback.
- Add optional `calibration_context` trace fields and validators for current
  calibration-use/advisory, comparison, reading packet, revision request, and
  anti-overfit review hashes.
- Regenerate `work/oponent_posudek_draft.md` through
  `scripts/draft-opponent-report`.
- Make `scripts/check-opponent-report` fail when a calibrated trace/draft has
  stale or missing calibration/feedback bindings.
- Ensure material trace edits reopen the review state and require
  `scripts/check-opponent-report`, manifest refresh, and independent report
  review when the result is treated as sendable.

Verification:

```bash
pants fmt src/thesis_review_workflow:: tests:: scripts::
pants lint src/thesis_review_workflow:: tests:: scripts::
pants check src/thesis_review_workflow:: tests:: scripts::
pants test tests/test_opponent_report.py tests/test_opponent_calibration.py tests/test_review_manifest_helpers.py
scripts/smoke-opponent-report
scripts/smoke-opponent-closeout
scripts/check-private
scripts/check-scripts
git diff --check
```

Commit target:

- `feat(workflow): bind calibrated opponent report drafts`

### Slice 9: Calibration Refresh Eligibility From Finalized Cases

Status: pending

Actions:

- After the report is finalized, allow the operator to mark the case as eligible
  for calibration refresh. This should copy only private case-local references
  into the ignored calibration workspace and must never auto-update the profile
  without explicit approval.
- Record eligibility as a private case-local marker with hashes of the finalized
  reviewed materials, final report draft/review, and operator approval.
- Keep export/copy helpers path-safe and Windows-aware if exposed as operator
  commands.

Verification:

```bash
pants fmt src/thesis_review_workflow:: tests:: scripts::
pants lint src/thesis_review_workflow:: tests:: scripts::
pants check src/thesis_review_workflow:: tests:: scripts::
pants test tests/test_opponent_calibration.py tests/test_review_manifest_helpers.py
scripts/smoke-opponent-report
scripts/smoke-opponent-closeout
scripts/smoke-package-workflow-tools
scripts/check-private
scripts/check-scripts
git diff --check
```

Commit target:

- `feat(workflow): mark finalized reports for calibration refresh`

### Slice 10: Private Pilot With Historical Reports

Status: pending

Actions:

- Confirm current-request authorization to use agents before reading private
  historical cases or writing semantic artifacts.
- User provides 2-3 historical opponent cases under the ignored calibration
  workspace.
- Run the historical case analysis workflow for each private case.
- Synthesize and review the private profile/checklist.
- Add one additional completed or historical case and refresh the profile to
  prove the incremental update path.
- Run one current or synthetic opponent case through the calibrated comparison
  and draft feedback loop.
- Select 2-3 private sentinel cases and record how to rerun them as a private
  regression check after future calibration/profile workflow changes.
- Capture only case-neutral lessons into tracked docs/TODO. Keep all historical
  case content and private profile output ignored.

Verification:

```bash
scripts/check-private
scripts/check-scripts
git diff --check
git status --short --untracked-files=all
```

Commit target:

- `docs(workflow): record opponent calibration pilot lessons`

## Progress

- 2026-05-07: plan created. Current state is planned; no implementation has
  started.
- 2026-05-07: agent plan review completed and findings repaired before
  implementation. Key repairs: Markdown-first profile manifest boundary,
  supplemental-not-readiness calibration profile semantics, generated-output
  review/provenance gates, path-classified calibration schemas, private-artifact
  coverage, Windows-aware command surface, and smaller current-case slices.
- 2026-05-07: Slice 1 started. Scope is limited to docs, schema validators,
  work-artifact registration, private-artifact checks, and synthetic tests.
- 2026-05-07: Slice 1 completed and agent-reviewed. Fixed review findings for
  JSONL provenance, case/round binding, historical-analysis source refs,
  non-string hash handling, dot-only ids, private smoke coverage, and jscpd
  duplication by sharing common artifact validation helpers. Verification:
  `pants fmt src/thesis_review_workflow:: tests::`, `pants lint
  src/thesis_review_workflow:: tests::`, `pants check
  src/thesis_review_workflow:: tests::`, targeted tests named in Slice 1,
  `scripts/smoke-private`, `scripts/check-private`, `scripts/check-scripts`,
  `git diff --check`, `pants run :vulture`, `pants run :jscpd`, and
  `pants run :omen`.

## Decision Log

- Use artifact-based calibration rather than model fine-tuning.
- Keep historical reports and synthesized private profiles under ignored
  `cases/`.
- Historical cases calibrate reviewer style, strictness, and checklist habits;
  they are not evidence about a new student's work.
- Profiles are versioned living artifacts. New cases may update the profile only
  through an explicit refresh workflow with previous/current hashes, history,
  independent review, and operator approval.
- Profile guidance must be applicability- and confidence-aware. If the current
  case is outside the calibration corpus, the pipeline should say so and use the
  profile lightly.
- Absence of a historical profile is never a blocker. The operator should see a
  clear recommendation to add historical reports for better calibration, but the
  normal opponent workflow remains usable without them.
- Use a separate anti-overfit review before profile-driven wording, grading, or
  checklist suggestions are relied on in a current case.
- The operator reading packet is a first-class output because usability depends
  on reviewing the evidence, uncertainty, grading tension, and manual checks
  before editing the final draft.
- Deterministic helpers may validate calibration artifact schemas and hashes,
  but semantic profile extraction and style calibration belong to explicitly
  authorized agents.
- Historical calibration is supplemental to the existing reviewer-profile
  readiness contract; it must not replace or satisfy `Reviewer profile` checks.
- Stable `outputs/` artifacts from this workflow need manifest/review/hash
  integration before downstream use. Experimental shapes belong under `work/`
  until the contract is stable.
- V1 should start with 2-3 historical cases. Broader automation waits until the
  pilot shows which differences matter.

## Final Audit

Not run yet. Fill before archiving:

- commands run
- skipped checks and reasons
- private pilot limitations
- residual TODO transfers
- archive commit
