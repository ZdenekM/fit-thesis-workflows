# Free Text Structured Evidence Plan

Status: active
Created: 2026-05-07

## Goal

Replace the remaining workflow places where deterministic code interprets raw
prose with explicit agent-produced structured artifacts. Deterministic helpers
may validate schemas, paths, hashes, manifests, known metadata labels, URLs, and
other structural data. They must not infer semantic review conclusions from
free-form thesis, feedback, or evidence text.

This plan implements the P0 TODO item from `TODO.md` and closes the active
follow-up in `docs/raw-text-processing-audit.md`.

## Audit Base

Current audit findings:

- `docs/raw-text-processing-audit.md` identifies the remaining semantic raw-text
  detectors and calls for `work/quantitative_claims.json`,
  `work/evidence_requirements.json`, `work/assignment_coverage_agent.json`, and
  explicit opponent-report trace data.
- `TODO.md` tracks the P0 item to replace the remaining free-text semantic
  detectors with agent-created structured artifacts.
- `src/thesis_review_workflow/cli/check_assignment_coverage.py` originally built
  semantic coverage from assignment and generated Markdown text; Slice 2A
  replaces it with structured artifact validation.
- `src/thesis_review_workflow/cli/check_evidence_presence.py` originally built
  semantic evidence-presence findings from extracted text; Slice 2B replaces it
  with validation of `work/evidence_requirements.json`. Its suffix/path-only
  `work/media_presence_inventory.jsonl` output is structural and remains valid.
- `src/thesis_review_workflow/cli/check_evaluation_claims.py` originally
  scanned extracted thesis text for quantitative/evaluation claims; Slice 2C
  replaces it with validation of `work/quantitative_claims.json`.
- `src/thesis_review_workflow/cli/draft_opponent_report.py` currently maps IS
  item formulations, risks, questions, and uncertainty from reviewed Markdown
  materials and has fallback section prose.
- `src/thesis_review_workflow/cli/check_opponent_report.py` currently compares
  free-form report/material text for uncertainty carry-over.

Commands already run while creating the plan:

```bash
git status --short --untracked-files=all
git diff --check
scripts/check-private
rg --files scripts | rg 'smoke-package-workflow-tools|package-workflow-tools|smoke-opponent-report|check-scripts'
```

Notes:

- This repository does not currently provide `scripts/plan_lint.py`. Plan
  validation is by the contract in `plans/README.md` plus `git diff --check`,
  `scripts/check-private`, and `scripts/check-scripts`.
- Omen is exposed as `pants run :omen`.
- Changed operator command surfaces must keep
  `src/thesis_review_workflow/commands.py`, `scripts/BUILD`, PEX targets, and
  `scripts/smoke-package-workflow-tools` green.

## Scope

In scope:

- `scripts/check-assignment-coverage`
- `scripts/check-evidence-presence`
- `scripts/check-evaluation-claims`
- `scripts/draft-opponent-report`
- `scripts/check-opponent-report`
- `src/thesis_review_workflow/work_artifacts.py`
- manifest/work-artifact validation for the new structured files
- tests and smoke checks for the migrated contracts
- workflow docs and skills that currently tell agents/operators to rely on the
  retired helper behavior

Non-goals:

- private case data under `cases/`
- compatibility with the older `~/code/diplomky` workflow
- broad redesign of generated opponent materials beyond the minimum structured
  evidence contracts needed here
- automatic generation of the semantic artifacts by deterministic helper code

Allowed structural routing:

- file/path/suffix checks, manifest references, hashes, schema names, section
  identifiers, table column names, reviewer-profile metadata, explicit
  placeholders, and URLs
- matching a configured marker or known label when it is a workflow command or
  metadata field, not an inferred semantic conclusion

Forbidden in workflow code:

- `if text contains X => conclusion Y`
- regex/token checks over thesis prose to infer missing evaluation, assignment
  coverage, uncertainty handling, grading, methodology quality, or evidence
  sufficiency
- deterministic summarization of free-form report/materials text into semantic
  review judgments

## Artifact Contract

The canonical V1 artifacts live in the ignored active round workspace under
`work/`. They are authored by an explicitly authorized agent workflow or by a
human reviewer using the same schema; deterministic code only validates and
consumes them.

Agent-produced structured evidence may be created only after explicit agent
authorization in the current request and only in `DEEP` mode. Deterministic
helpers must never spawn agents or infer that authorization exists; they only
consume existing artifacts.

Common required fields for all V1 JSON artifacts:

- `schema_version`
- `case_id`
- `round_id`
- `generated_at`
- `producer_type`: `agent` or `human`
- `producer_role`
- `producer_agent`: string or `null`
- `source_refs`
- `limitations`
- `authorization_note` for agent-authored artifacts or `human_reviewer_note`
  for human-authored artifacts

All `*_refs` values are round-relative POSIX paths under `inputs/`,
`extracted/`, `notes/`, `work/`, or `outputs/`. Validators reject absolute paths,
`..`, backslashes, drive letters, UNC paths, and missing files unless a field is
explicitly typed as unavailable. Tracked fixtures must never contain real case
data.

Deterministic checks fail only for missing artifacts, invalid schema, stale
hashes, unsafe refs, impossible enum values, or incomplete required fields.
Valid semantic values such as `missing`, `weak`, `needs_context`, `covered`, or
`requires_reviewer_verification: true` are reported as reviewer prompts and may
be consumed by authorized review/synthesis agents. They must not be converted
into deterministic quality verdicts, grading, readiness, or feedback wording.

Implementation API target:

```python
validate_structured_evidence_artifact(
    round_dir: Path,
    rel_path: Path,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
) -> list[str]
```

Work-artifact integration target:

- add new entries to `KNOWN_JSON_ARTIFACT_SCHEMAS`
- add new entries to `JSON_ARTIFACT_REQUIRED_FIELDS`
- add new entries to `EXPLICIT_WORK_ARTIFACTS`
- validate nested refs and enums through the new structured-evidence API
- update `tests/test_work_artifacts.py`
- update manifest helper tests where the collected work-artifact allowlist is
  asserted

Retirement rule:

- `work/assignment_coverage_map.json` and `work/evidence_presence.json` are
  retired in the same slices that migrate their producing helpers. They are not
  kept as compatibility adapters.
- `work/media_presence_inventory.jsonl` remains a structural suffix/path
  inventory. Assignment-derived conclusions such as missing videos, missing demo
  data, or weak experiment evidence move into `work/evidence_requirements.json`.

### `work/assignment_coverage_agent.json`

Schema version: `assignment-coverage-agent-v1`

Purpose: structured mapping from assignment requirements to thesis/code
evidence.

Enums:

- `coverage.status`: `covered`, `partially_covered`, `not_covered`,
  `not_verifiable`

Minimum shape:

```json
{
  "schema_version": "assignment-coverage-agent-v1",
  "case_id": "case-id",
  "round_id": "round-id",
  "generated_at": "2026-05-07T00:00:00Z",
  "producer_type": "agent",
  "producer_role": "assignment-coverage-reviewer",
  "producer_agent": "agent-id-or-name",
  "authorization_note": "Current request explicitly authorized agents.",
  "source_refs": ["notes/assignment.md", "extracted/thesis.txt"],
  "assignment_points": [
    {
      "point_id": "A1",
      "summary": "Requirement in reviewer language.",
      "source_refs": ["notes/assignment.md"],
      "coverage": {
        "status": "covered",
        "evidence_refs": ["extracted/thesis.txt"],
        "limitations": [],
        "requires_reviewer_verification": false
      }
    }
  ],
  "limitations": []
}
```

### `work/evidence_requirements.json`

Schema version: `evidence-requirements-v1`

Purpose: structured list of evidence required by the current review context and
whether each requirement is present, weak, missing, not applicable, or not
verifiable.

Enums:

- `requirements[].category`: `media`, `evaluation_data`, `evaluation_script`,
  `code_reproducibility`, `dataset`, `method_description`, `assignment_source`,
  `other`
- `requirements[].state`: `present`, `weak`, `missing`, `not_applicable`,
  `not_verifiable`

Minimum shape:

```json
{
  "schema_version": "evidence-requirements-v1",
  "case_id": "case-id",
  "round_id": "round-id",
  "generated_at": "2026-05-07T00:00:00Z",
  "producer_type": "agent",
  "producer_role": "evidence-requirements-reviewer",
  "producer_agent": "agent-id-or-name",
  "authorization_note": "Current request explicitly authorized agents.",
  "source_refs": ["notes/assignment.md", "inputs/results.csv"],
  "requirements": [
    {
      "requirement_id": "E1",
      "category": "evaluation_data",
      "state": "present",
      "request": "What evidence is needed and why.",
      "evidence_refs": ["inputs/results.csv"],
      "requires_reviewer_verification": false
    }
  ],
  "limitations": []
}
```

### `work/quantitative_claims.json`

Schema version: `quantitative-claims-v1`

Purpose: structured semantic sanity review of quantitative, metric,
performance, and experiment claims.

Enums:

- `claims[].kind`: `metric`, `experiment`, `performance`, `scale`, `count`,
  `statistic`, `other`
- `claims[].status`: `plausible`, `needs_context`, `unsupported`,
  `inconsistent`, `not_verifiable`
- `claims[].baseline_status`: `stated`, `missing`, `not_applicable`,
  `not_verifiable`
- `claims[].practical_context`: `sufficient`, `weak`, `missing`,
  `not_applicable`, `not_verifiable`

Minimum shape:

```json
{
  "schema_version": "quantitative-claims-v1",
  "case_id": "case-id",
  "round_id": "round-id",
  "generated_at": "2026-05-07T00:00:00Z",
  "producer_type": "agent",
  "producer_role": "quantitative-claims-reviewer",
  "producer_agent": "agent-id-or-name",
  "authorization_note": "Current request explicitly authorized agents.",
  "source_refs": ["extracted/thesis.txt"],
  "claims": [
    {
      "claim_id": "Q1",
      "summary": "Claim in reviewer language.",
      "kind": "metric",
      "status": "needs_context",
      "unit": "%",
      "baseline_status": "stated",
      "practical_context": "weak",
      "reproducibility_refs": [],
      "evidence_refs": ["extracted/thesis.txt"],
      "requires_reviewer_verification": true
    }
  ],
  "limitations": []
}
```

### `work/opponent_report_trace.json`

Schema version: `opponent-report-trace-v1`

Purpose: structured trace between reviewed opponent materials, required IS
sections, known uncertainties, and the generated opponent-report draft. This
replaces deterministic token matching between free-form materials and report
text.

Required source binding:

- `source_materials_path`: `outputs/oponent_podklady_revidovane.md`
- `source_materials_sha256`: current hash of the reviewed materials
- `trace_review_status`: `accepted`
- `reviewer_role`
- `reviewed_at`
- `trace_generated_from`: list of round-relative evidence refs

Required `is_items[].item_id` values:

- `assignment_difficulty`
- `assignment_fulfillment`
- `technical_report_scope`
- `technical_report_presentation`
- `technical_report_formal_level`
- `literature_work`
- `implementation_output`
- `result_usability`
- `overall_assessment`

`draft-opponent-report` must fail if any required trace item is missing. It must
not synthesize fallback prose for missing section formulations.

Minimum shape:

```json
{
  "schema_version": "opponent-report-trace-v1",
  "case_id": "case-id",
  "round_id": "round-id",
  "generated_at": "2026-05-07T00:00:00Z",
  "producer_type": "agent",
  "producer_role": "opponent-report-trace-reviewer",
  "producer_agent": "agent-id-or-name",
  "authorization_note": "Current request explicitly authorized agents.",
  "source_refs": ["outputs/oponent_podklady_revidovane.md"],
  "source_materials_path": "outputs/oponent_podklady_revidovane.md",
  "source_materials_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "trace_review_status": "accepted",
  "reviewer_role": "independent-opponent-report-trace-reviewer",
  "reviewed_at": "2026-05-07T00:00:00Z",
  "trace_generated_from": ["outputs/oponent_podklady_revidovane.md"],
  "is_items": [
    {
      "item_id": "technical_report_presentation",
      "title": "Prezentační úroveň technické zprávy",
      "formulation": "Draft-ready formulation.",
      "evidence_refs": ["outputs/oponent_podklady_revidovane.md"]
    }
  ],
  "defense_questions": [
    {
      "question_id": "D1",
      "question": "Question prepared for the defense?",
      "evidence_refs": ["outputs/oponent_podklady_revidovane.md"]
    }
  ],
  "pre_submission_checks": [
    {
      "check_id": "C1",
      "instruction": "Manual calibration instruction.",
      "evidence_refs": ["outputs/oponent_podklady_revidovane.md"]
    }
  ],
  "uncertainty_items": [
    {
      "claim_id": "U1",
      "summary": "Uncertainty that must be preserved in the report.",
      "handling_instruction": "How the draft/report should carry this uncertainty.",
      "source_refs": ["outputs/oponent_podklady_revidovane.md"],
      "target_section_ids": ["overall_assessment"],
      "report_refs": ["work/oponent_posudek_draft.md"],
      "status": "carried_to_report"
    }
  ],
  "limitations": []
}
```

`draft-opponent-report` embeds `source_trace_path`,
`source_trace_sha256`, `source_materials_path`, and
`source_materials_sha256` metadata in the draft. `check-opponent-report`
validates those hashes, validates the trace schema, checks required structural
headings and calibration fields, and does not scan free-form materials/report
text for semantic uncertainty carry-over.

## Slices

### Slice 1: Plan Review and Artifact Validators

Status: done

Actions:

- Review this plan with role-split agents:
  - workflow/provenance reviewer
  - code-contract and migration reviewer
- Patch the plan with actionable findings before implementation.
- Add `src/thesis_review_workflow/structured_evidence.py`.
- Integrate new artifacts in `src/thesis_review_workflow/work_artifacts.py`.
- Add/update `tests/test_structured_evidence.py`,
  `tests/test_work_artifacts.py`, and manifest helper tests if allowlisted
  work artifacts are asserted there.

Verification:

```bash
pants fmt src/thesis_review_workflow/structured_evidence.py src/thesis_review_workflow/work_artifacts.py tests/test_structured_evidence.py tests/test_work_artifacts.py
pants lint src/thesis_review_workflow/structured_evidence.py src/thesis_review_workflow/work_artifacts.py tests/test_structured_evidence.py tests/test_work_artifacts.py
pants check src/thesis_review_workflow/structured_evidence.py src/thesis_review_workflow/work_artifacts.py tests/test_structured_evidence.py tests/test_work_artifacts.py
pants test tests/test_structured_evidence.py tests/test_work_artifacts.py
pants run :omen
scripts/check-private
scripts/check-scripts
git diff --check
```

Commit target:

- `feat(workflow): add structured evidence contracts`

### Slice 2A: Assignment Coverage Contract

Status: done

Actions:

- Change `check-assignment-coverage` to require and validate
  `work/assignment_coverage_agent.json`.
- Remove generation of `work/assignment_coverage_map.json`.
- Remove retired assignment-coverage parser code/tests when no longer
  referenced.
- Update opponent preflight, packets, skills, docs, and smoke coverage in the
  same commit so agents/operators are told to produce the new artifact before
  running the check.

Verification:

```bash
pants fmt src/thesis_review_workflow/cli/check_assignment_coverage.py src/thesis_review_workflow/opponent_packets.py tests::
pants lint src/thesis_review_workflow/cli/check_assignment_coverage.py src/thesis_review_workflow/opponent_packets.py tests::
pants check src/thesis_review_workflow/cli/check_assignment_coverage.py src/thesis_review_workflow/opponent_packets.py tests::
pants test tests/test_assignment_coverage.py tests/test_work_artifacts.py tests/test_workflow_python_contracts.py
scripts/smoke-assignment-coverage
scripts/smoke-package-workflow-tools
pants run :omen
scripts/check-private
scripts/check-scripts
git diff --check
```

Commit target:

- `refactor(workflow): require structured assignment coverage`

### Slice 2B: Evidence Requirements Contract

Status: done

Actions:

- Change `check-evidence-presence` to require and validate
  `work/evidence_requirements.json`.
- Remove generation of semantic `work/evidence_presence.json`.
- Keep suffix/path-only `work/media_presence_inventory.jsonl` as structural
  inventory.
- Remove retired evidence-presence parser code/tests when no longer referenced.
- Update opponent preflight, packets, skills, docs, and smoke coverage in the
  same commit.

Verification:

```bash
pants fmt src/thesis_review_workflow/cli/check_evidence_presence.py src/thesis_review_workflow/opponent_packets.py tests::
pants lint src/thesis_review_workflow/cli/check_evidence_presence.py src/thesis_review_workflow/opponent_packets.py tests::
pants check src/thesis_review_workflow/cli/check_evidence_presence.py src/thesis_review_workflow/opponent_packets.py tests::
pants test tests/test_evidence_presence.py tests/test_work_artifacts.py tests/test_workflow_python_contracts.py
scripts/smoke-evidence-presence
scripts/smoke-package-workflow-tools
pants run :omen
scripts/check-private
scripts/check-scripts
git diff --check
```

Commit target:

- `refactor(workflow): require structured evidence requirements`

### Slice 2C: Quantitative Claims Contract

Status: done

Actions:

- Change `check-evaluation-claims` to require and validate
  `work/quantitative_claims.json`.
- Remove regex-based quantitative/evaluation claim scanning.
- Remove retired evaluation-claims parser code/tests when no longer referenced.
- Update skills, docs, and smoke coverage in the same commit.

Verification:

```bash
pants fmt src/thesis_review_workflow/cli/check_evaluation_claims.py tests::
pants lint src/thesis_review_workflow/cli/check_evaluation_claims.py tests::
pants check src/thesis_review_workflow/cli/check_evaluation_claims.py tests::
pants test tests/test_evaluation_claims_helpers.py tests/test_work_artifacts.py tests/test_workflow_python_contracts.py
scripts/smoke-evaluation-claims
scripts/smoke-package-workflow-tools
pants run :omen
scripts/check-private
scripts/check-scripts
git diff --check
```

Commit target:

- `refactor(workflow): require structured quantitative claims`

### Slice 3: Opponent Report Trace Contract

Status: done

Actions:

- Change `draft-opponent-report` to consume `work/opponent_report_trace.json`
  for IS-item formulations, defense questions, pre-submission checks, and
  uncertainty handling.
- Fail when the trace is missing, stale, unreviewed, incomplete, or invalid.
- Remove fallback section prose.
- Change `check-opponent-report` to validate trace/material hashes and
  structural report shape without semantic text matching.
- Update relevant tests, smoke coverage, skills, and docs in the same commit.

Verification:

```bash
pants fmt src/thesis_review_workflow/cli/draft_opponent_report.py src/thesis_review_workflow/cli/check_opponent_report.py tests::
pants lint src/thesis_review_workflow/cli/draft_opponent_report.py src/thesis_review_workflow/cli/check_opponent_report.py tests::
pants check src/thesis_review_workflow/cli/draft_opponent_report.py src/thesis_review_workflow/cli/check_opponent_report.py tests::
pants test tests/test_opponent_report.py tests/test_workflow_python_contracts.py
scripts/smoke-opponent-report
scripts/smoke-package-workflow-tools
pants run :omen
scripts/check-private
scripts/check-scripts
git diff --check
```

Commit target:

- `refactor(workflow): require structured opponent report trace`

### Slice 4: Workflow Surfaces and Closeout

Status: pending

Actions:

- Update `docs/raw-text-processing-audit.md` with retired code paths and any
  residual allowed structural routing.
- Remove the completed P0 item from `TODO.md`.
- Run closeout hygiene.
- Archive this plan after all slices are committed.

Verification:

```bash
pants fmt ::
pants lint src/thesis_review_workflow:: tests:: scripts::
pants check src/thesis_review_workflow:: tests:: scripts::
pants test tests::
scripts/check-private
scripts/check-scripts
scripts/smoke-package-workflow-tools
git diff --check
git status --short --untracked-files=all
```

Commit target:

- `docs(workflow): document structured evidence migration`

## Progress

- 2026-05-07: plan created and reviewed by two agents.
- 2026-05-07: reviewer findings incorporated into the plan before
  implementation.
- 2026-05-07: Slice 1 implemented structured-evidence validators, registered
  the four V1 artifacts in work-artifact collection, added regression coverage
  for schema enums, ref safety, agent identity, and opponent-trace hash binding,
  and passed independent agent review after fixing unsafe path dereferencing.
- 2026-05-07: Slice 2A migrated `scripts/check-assignment-coverage` to validate
  `work/assignment_coverage_agent.json`, removed the raw token-overlap parser,
  removed the retired `work/assignment_coverage_map.json` allowlist, adjusted
  packets/preflight/docs/smokes, and passed agent review after clarifying that
  assignment coverage is produced by text/assignment agents after preflight.
- 2026-05-07: Slice 2B migrated `scripts/check-evidence-presence` to validate
  `work/evidence_requirements.json`, removed semantic evidence-presence
  generation and parser code, kept `work/media_presence_inventory.jsonl` as a
  structural suffix/path inventory, updated packets/preflight/docs/smokes, and
  passed agent re-review after fixing draft-report validation, stale inventory,
  unreadable-artifact handling, and preflight reporting.
- 2026-05-07: Slice 2C migrated `scripts/check-evaluation-claims` to validate
  `work/quantitative_claims.json`, removed the regex/table/unit parser module,
  updated repo-local skills/docs/smokes, required per-claim evidence anchors,
  and passed agent re-review after fixing stale skill instructions.
- 2026-05-07: Slice 3 migrated `scripts/draft-opponent-report` and
  `scripts/check-opponent-report` to the reviewed
  `work/opponent_report_trace.json` contract, removed reviewed-materials token
  matching and fallback report prose, made closeout/manifest/case-doctor require
  the trace, tightened trace evidence anchors and uncertainty handling, and
  passed agent re-review after fixing stale helper-check targets, schema
  ambiguity, and residual tone regex gating.
- Current slice: Slice 4 pending.

## Decision Log

- Use new canonical artifacts instead of compatibility adapters for
  `work/assignment_coverage_map.json` and `work/evidence_presence.json`.
- Keep `work/media_presence_inventory.jsonl` because it is structural
  suffix/path evidence, not a semantic conclusion.
- Split the helper migration into three commits so each helper, tests, smoke,
  preflight/packet references, and workflow docs move together.
- Require reviewed and hash-bound `work/opponent_report_trace.json` before
  `draft-opponent-report` can generate report prose.
- Do not add deterministic LLM/agent spawning to helper scripts. Agents create
  artifacts only through explicitly authorized workflow execution.

## Final Audit

Not run yet. Fill before archiving:

- commands run
- skipped checks and reasons
- residual risks or TODO transfers
- archive commit

## Review Discipline

Each implementation slice gets an independent agent review before commit. Agent
findings are either fixed in the slice or recorded as explicit follow-up only if
they are outside this plan's scope.

Pants commands are run sequentially. Do not run concurrent Pants invocations.

Use Serena for non-trivial Python navigation and `pants run :omen` for
development hygiene on touched Python files.
