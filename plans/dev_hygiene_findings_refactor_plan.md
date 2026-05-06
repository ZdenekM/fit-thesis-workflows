# Dev Hygiene Findings Refactor Plan

Status: active
Created: 2026-05-06

## Goal

Turn the first `vulture`, `jscpd`, and `omen` baseline into a small refactoring
series that reduces repeated validator/helper code without changing thesis case
pipeline behavior.

## Audit Base

Commands run on 2026-05-06:

```bash
pants run :vulture
pants run :jscpd
pants run :omen
```

Current findings:

- `pants run :vulture` passed with no reported unused-code items.
- `pants run :jscpd` passed under the configured threshold, but found 14 Python
  clones: 429 duplicated lines out of 10833 total lines, or 3.96%.
- `pants run :omen` reported grade A, overall score 91.04, no deadcode, no
  smells, and no dependency cycles.
- Omen critical hotspots:
  - `src/thesis_review_workflow/cli/case_doctor.py`
  - `src/thesis_review_workflow/cli/import_github_code.py`
  - `src/thesis_review_workflow/cli/check_evaluation_claims.py`
- Omen high hotspots:
  - `src/thesis_review_workflow/cli/check_figure_media_review.py`
  - `src/thesis_review_workflow/cli/bootstrap_case.py`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `src/thesis_review_workflow/cli/check_opponent_materials.py`
- The clearest jscpd clone families are:
  - repeated CLI repo-root, case-id, round-id, and manifest loading helpers,
  - repeated Markdown section/table parsing and placeholder checks across
    output validators,
  - repeated opponent-materials/report/manifest closeout helpers.

Constraints:

- These tools are development hygiene only. Do not make them part of thesis case
  pipeline closeout unless a later decision changes that explicitly.
- Preserve current workflow behavior unless a slice calls out a deliberate
  validator contract change.
- Keep helper APIs small and named after workflow concepts, not after tool
  findings.
- Do not add backwards-compatibility layers for older `~/code/diplomky`
  workflows.
- Keep Windows operator support intact: operator-facing helpers need Python,
  Pants/PEX, or native launcher surfaces.
- Use Serena for non-trivial Python navigation when practical.
- Run Pants commands sequentially.

## Scope

In scope:

- shared Python helper extraction under `src/thesis_review_workflow/`,
- focused updates to validator/checker CLI modules,
- focused tests or smoke-script updates needed to preserve behavior,
- documentation/TODO cleanup after the refactor baseline improves.

Out of scope:

- changing generated thesis-review artifact formats for aesthetic reasons,
- making `vulture`, `jscpd`, or `omen` blocking pipeline gates,
- broad rewrite of every CLI helper,
- case-specific data, submitted code, PDFs, source zips, or generated outputs.

## Slices

### Slice 1 - Shared CLI And Round Resolution Helpers

- Status: pending
- Proposed commit message: `refactor(workflow): share cli round resolution helpers`
- Why: Many checkers duplicate repo-root lookup, ID validation, current-round
  resolution, and manifest path handling before doing their real validation.
- Expected paths:
  - `src/thesis_review_workflow/cases.py`
  - `src/thesis_review_workflow/ids.py`
  - `src/thesis_review_workflow/cli/check_agent_coverage.py`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `src/thesis_review_workflow/cli/check_opponent_report.py`
  - `src/thesis_review_workflow/cli/draft_opponent_report.py`
  - `tests/`
- Tasks:
  - Reuse existing `cases.py` and `ids.py` helpers before adding a new helper.
  - Extract only the repeated round/manifest mechanics that have one clear
    contract.
  - Keep checker-specific error wording where it materially helps operators.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `scripts/smoke-agent-coverage`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-opponent-report`
  - `pants run :jscpd`

### Slice 2 - Shared Markdown Validator Primitives

- Status: pending
- Proposed commit message: `refactor(workflow): share markdown validator primitives`
- Why: The largest clone family is repeated Markdown section/table/placeholder
  parsing in output validators.
- Expected paths:
  - `src/thesis_review_workflow/`
  - `src/thesis_review_workflow/cli/check_feedback_output.py`
  - `src/thesis_review_workflow/cli/check_figure_media_review.py`
  - `src/thesis_review_workflow/cli/check_opponent_materials.py`
  - `src/thesis_review_workflow/cli/check_typography_formal.py`
  - `src/thesis_review_workflow/cli/check_evaluation_claims.py`
  - `tests/`
- Tasks:
  - Introduce one small shared module for Markdown normalization, section
    extraction, table parsing, delimiter-row checks, and placeholder detection.
  - Keep domain-specific required headings, table schemas, and evidence rules in
    each checker.
  - Add tests for the shared parsing edge cases before moving multiple checkers.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `scripts/smoke-feedback-output`
  - `scripts/smoke-figure-media-review`
  - `scripts/smoke-opponent-materials`
  - `scripts/smoke-typography-formal`
  - `scripts/smoke-evaluation-claims`
  - `pants run :jscpd`

### Slice 3 - Hotspot Decomposition Without Behavior Drift

- Status: pending
- Proposed commit message: `refactor(workflow): split high-churn checker logic`
- Why: Omen flags `case_doctor.py`, `import_github_code.py`, and
  `check_evaluation_claims.py` as critical hotspots. They should be easier to
  test and review before more workflow automation grows around them.
- Expected paths:
  - `src/thesis_review_workflow/cli/case_doctor.py`
  - `src/thesis_review_workflow/cli/import_github_code.py`
  - `src/thesis_review_workflow/cli/check_evaluation_claims.py`
  - `src/thesis_review_workflow/`
  - `tests/`
- Tasks:
  - Identify pure classification/rendering blocks that can move into small
    helpers with direct tests.
  - Keep subprocess and filesystem side effects at the CLI boundary.
  - Avoid extracting abstractions that only hide a single call site.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `scripts/smoke-case-doctor`
  - `scripts/smoke-github-code-intake`
  - `scripts/smoke-evaluation-claims`
  - `pants run :omen`

### Slice 4 - Hygiene Baseline Closeout

- Status: pending
- Proposed commit message: `docs(workflow): record dev hygiene refactor baseline`
- Why: The hygiene tools should produce an actionable baseline, not a one-off
  report. Closeout should show whether the duplicated-line and hotspot signals
  improved and what remains.
- Expected paths:
  - `plans/dev_hygiene_findings_refactor_plan.md`
  - `docs/dev-hygiene.md`
  - `TODO.md`
- Tasks:
  - Rerun the three dev-hygiene targets after slices 1-3.
  - Record final jscpd duplication percentage, Omen score/hotspots, and vulture
    result in the plan final audit.
  - Move completed work out of `TODO.md`; add only residual open work that still
    has a clear next step.
  - Move this plan to `plans/archive/` when done or mark it superseded if a
    narrower follow-up plan replaces it.
- Verification:
  - `pants run :vulture`
  - `pants run :jscpd`
  - `pants run :omen`
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

## Progress

- Slice 1: pending - shared CLI and round resolution helpers
- Slice 2: pending - shared Markdown validator primitives
- Slice 3: pending - hotspot decomposition without behavior drift
- Slice 4: pending - hygiene baseline closeout

## Decision Log

- 2026-05-06: Keep `vulture`, `jscpd`, and `omen` as development hygiene tools,
  not thesis case pipeline gates.
- 2026-05-06: Start with repeated validator mechanics before touching broader
  workflow behavior, because jscpd points to concrete duplication and vulture is
  already clean.

## Final Audit

Not run yet. This plan is active.
