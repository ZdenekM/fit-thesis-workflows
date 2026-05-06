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
  clones: 429 duplicated lines out of 10941 Python lines, or 3.92% for Python
  after the dev-hygiene wrapper commit. Total duplicated lines were 3.91%.
- `pants run :omen` reported grade A, overall score 91.14, no deadcode, no
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
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
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

- Status: done
- Proposed commit message: `refactor(workflow): share cli round context helpers`
- Why: Many checkers duplicate repo-root lookup, ID validation, current-round
  resolution, and manifest path handling before doing their real validation.
- Expected paths:
  - `src/thesis_review_workflow/cli/context.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/cases.py`
  - `src/thesis_review_workflow/ids.py`
  - `src/thesis_review_workflow/cli/check_agent_coverage.py`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `src/thesis_review_workflow/cli/check_opponent_report.py`
  - `src/thesis_review_workflow/cli/draft_opponent_report.py`
  - `src/thesis_review_workflow/cli/opponent_closeout.py`
  - `tests/test_cli_context.py`
  - `tests/test_workflow_core_helpers.py`
- Tasks:
  - Add a CLI adapter module instead of directly swapping each checker to
    library exceptions. Preserve checker exit-code and operator-message
    contracts.
  - Reuse existing `cases.py` and `ids.py` helpers inside that adapter where
    their library messages fit the CLI contract.
  - Extract only repeated repo-root, id, round, and manifest mechanics that have
    one clear CLI contract.
  - Keep checker-specific error wording where it materially helps operators.
  - Cover `opponent_closeout.py` because it is part of the closeout clone family.
  - Add or update tests for invalid IDs, missing current rounds, missing cases,
    and manifest-loading failure shapes used by the migrated checkers.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests::`
  - `scripts/smoke-agent-coverage`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-opponent-report`
  - `scripts/smoke-opponent-closeout`
  - `scripts/smoke-package-workflow-tools`
  - `pants run :jscpd`

### Slice 2 - Shared Markdown Validator Primitives

- Status: done
- Proposed commit message: `refactor(workflow): share markdown validator primitives`
- Why: The largest clone family is repeated Markdown section/table/placeholder
  parsing in output validators.
- Expected paths:
  - `src/thesis_review_workflow/markdown_utils.py`
  - `src/thesis_review_workflow/BUILD`
  - `src/thesis_review_workflow/cli/check_feedback_output.py`
  - `src/thesis_review_workflow/cli/check_figure_media_review.py`
  - `src/thesis_review_workflow/cli/check_opponent_materials.py`
  - `src/thesis_review_workflow/cli/check_opponent_report.py`
  - `src/thesis_review_workflow/cli/draft_opponent_report.py`
  - `src/thesis_review_workflow/cli/check_typography_formal.py`
  - `tests/test_markdown_utils.py`
- Tasks:
  - Introduce one small shared module for mechanical Markdown section
    extraction, table splitting, delimiter-row checks, and table extraction.
  - Keep domain-specific required headings, table schemas, and evidence rules in
    each checker.
  - Keep normalization, placeholder regexes, wording, and severity policy owned
    by each checker. If a helper is useful for placeholder matching, it must
    accept checker-supplied patterns and return raw match data only.
  - Leave `check_evaluation_claims.py` placeholder policy checker-owned unless
    a purely mechanical Markdown helper is actually useful there.
  - Add tests for the shared parsing edge cases before moving multiple checkers.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests::`
  - `scripts/smoke-feedback-output`
  - `scripts/smoke-figure-media-review`
  - `scripts/smoke-opponent-materials`
  - `scripts/smoke-typography-formal`
  - `scripts/smoke-evaluation-claims`
  - `scripts/smoke-package-workflow-tools`
  - `pants run :jscpd`

### Slice 3 - Case Doctor Hotspot Decomposition

- Status: done
- Proposed commit message: `refactor(workflow): split case doctor rendering logic`
- Why: Omen flags `case_doctor.py` as a critical hotspot. Its output is a common
  orientation surface, so pure classification/rendering logic should be testable
  without changing the operator command behavior.
- Expected paths:
  - `src/thesis_review_workflow/cli/case_doctor.py`
  - `src/thesis_review_workflow/case_doctor_summary.py`
  - `tests/test_case_doctor_summary.py`
- Tasks:
  - Identify pure classification or summary-rendering blocks that can move into
    a small helper with direct tests.
  - Keep subprocess and filesystem side effects at the CLI boundary.
  - Avoid extracting abstractions that only hide a single call site.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests::`
  - `scripts/smoke-case-doctor`
  - `scripts/smoke-package-workflow-tools`
  - `pants run :omen`

### Slice 4 - GitHub Intake Hotspot Decomposition

- Status: done
- Proposed commit message: `refactor(workflow): split github intake classification`
- Why: Omen flags `import_github_code.py` as a critical hotspot. GitHub intake
  has external command and workspace side effects, so only pure classification,
  manifest, or rendering helpers should move.
- Expected paths:
  - `src/thesis_review_workflow/cli/import_github_code.py`
  - `src/thesis_review_workflow/github_intake.py`
  - `tests/test_github_intake.py`
- Tasks:
  - Extract only pure GitHub intake classification, path-shape, or manifest
    helpers that can be directly tested.
  - Keep `gh`, filesystem, and subprocess behavior at the CLI boundary.
  - Preserve current intake output shape.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests::`
  - `scripts/smoke-github-code-intake`
  - `scripts/smoke-package-workflow-tools`
  - `pants run :omen`

### Slice 5 - Evaluation Claims Hotspot Decomposition

- Status: pending
- Proposed commit message: `refactor(workflow): split evaluation claim helpers`
- Why: Omen flags `check_evaluation_claims.py` as a critical hotspot and jscpd
  reports overlap with typography/formal checks. The refactor should isolate
  reusable evidence/classification helpers while keeping metric and placeholder
  judgment in the checker.
- Expected paths:
  - `src/thesis_review_workflow/cli/check_evaluation_claims.py`
  - `src/thesis_review_workflow/evaluation_claims.py`
  - `tests/test_evaluation_claims_helpers.py`
- Tasks:
  - Extract pure quantitative-claim/evidence helpers that can be tested without
    a case workspace.
  - Keep placeholder regexes, severity wording, and thesis-specific evidence
    policy checker-owned unless a helper accepts checker-supplied patterns.
  - Preserve current validator output and exit-code behavior.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests::`
  - `scripts/smoke-evaluation-claims`
  - `scripts/smoke-package-workflow-tools`
  - `pants run :omen`

### Slice 6 - Hygiene Baseline Closeout

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
  - Rerun the three dev-hygiene targets after slices 1-5.
  - Record a before/after table for jscpd clone count, duplicated-line count,
    and duplicated-line percentage.
  - Record a before/after table for Omen score, critical/high hotspot counts,
    and named critical/high hotspot deltas.
  - Explain unchanged hotspots where churn dominates and remaining clones that
    are deliberately deferred.
  - Record the vulture result.
  - Move completed work out of `TODO.md`; add only residual open work that still
    has a clear next step.
  - Move this plan to `plans/archive/` when done or mark it superseded if a
    narrower follow-up plan replaces it.
- Verification:
  - `pants run :vulture`
  - `pants run :jscpd`
  - `pants run :omen`
  - `pants test tests::`
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `scripts/smoke-package-workflow-tools`

## Progress

- Slice 1: done - shared CLI and round resolution helpers
- Slice 2: done - shared Markdown validator primitives
- Slice 3: done - case doctor hotspot decomposition
- Slice 4: done - GitHub intake hotspot decomposition
- Slice 5: pending - evaluation claims hotspot decomposition
- Slice 6: pending - hygiene baseline closeout

## Decision Log

- 2026-05-06: Keep `vulture`, `jscpd`, and `omen` as development hygiene tools,
  not thesis case pipeline gates.
- 2026-05-06: Start with repeated validator mechanics before touching broader
  workflow behavior, because jscpd points to concrete duplication and vulture is
  already clean.
- 2026-05-06: Plan review split the broad hotspot slice into per-workflow
  commits and kept shared Markdown helpers mechanical only, because the
  validators own different normalization and placeholder-severity contracts.
- 2026-05-06: Slice 4 review accepted the residual Omen critical hotspot in
  `import_github_code.py` as remaining orchestration complexity, not a behavior
  regression; the extracted helper stays pure and the CLI keeps GitHub and
  filesystem side effects.

## Final Audit

Not run yet. This plan is active.
