# Workflow Reliability Contract Plan

Status: done
Created: 2026-05-06

## Goal

Execute the first reliability-contract hardening wave: platform-neutral command
surface classification, deterministic helper-test coverage, explicit guardrails
against brittle content heuristics, and a focused typography language-resolution
fix.

This plan should make the workflow safer to extend repeatedly before separate
follow-up plans introduce case-format migrations, supervisor closeout bundles, or
heavier P1/P2 capabilities such as sandboxed student-code execution, video/demo
review, expanded GitHub intake, or literature-source collection.

## Audit Base

Source of candidates: `TODO.md` on 2026-05-06 after the opponent-review value
plan was archived.

Selected P0 TODO items:

| Rank | TODO item | Why it matters | First-wave decision |
|---:|---|---|---|
| 1 | Case-data contract and migration workflow | Most helpers assume the same `cases/<case-id>/rounds/<round-id>/...` shape. The repo needs explicit diagnostics before more workflows depend on the layout. | defer to follow-up plan; audit only |
| 2 | Native Windows workflow compatibility | Operators should not need Bash/WSL for direct workflow helpers. New and existing operator surfaces need packaged launchers or explicit dev-only classification. | include |
| 3 | Deterministic tests for remaining helper contracts | Shell smokes are useful but too coarse for fast confidence in validators, manifest rules, and case-format contracts. | include |
| 4 | Supervisor-feedback preflight and closeout bundle | Opponent workflows now have a clearer preflight/closeout path; supervisor feedback should get the same transparent guard rails. | defer to follow-up plan |
| 5 | Thesis-language resolution in typography/formal checks | A narrow correctness fix prevents Czech/Slovak/English typography rules from being driven by feedback-language metadata. | include |
| 6 | Supervisor deadlines recurring maintenance | Important operational reminder, but it requires current academic-year policy data rather than workflow code. | defer as recurring data maintenance |

Current relevant surfaces:

- `scripts/package-workflow-tools`, `scripts/package-workflow-tools.cmd`, and
  `scripts/package-workflow-tools.ps1` package workflow tools into
  `dist/workflow-tools/bin/`.
- `scripts/BUILD` uses `pex_binary(tags=["workflow-tool"])` as the packaged
  command contract.
- `src/thesis_review_workflow/commands.py` maps logical `scripts/<tool>` names
  to Python CLI modules.
- `scripts/case-doctor` summarizes round state but does not currently report an
  explicit case-format version or migration state.
- `scripts/check-supervisor-ready`, `scripts/check-feedback-language`, and
  `scripts/check-feedback-output` are the current supervisor-facing gates.
- `scripts/opponent-preflight` and `scripts/opponent-closeout` provide the
  strongest existing model for transparent preflight/closeout bundles.
- `scripts/check-typography-formal` already has a smoke suite for thesis-language
  modes, but the TODO records a remaining resolution bug to audit and fix.
- Baseline command-surface audit on 2026-05-06 found 61 executable files under
  `scripts/`, 35 entries in `WORKFLOW_COMMAND_MODULES`, and 35 packaged
  `workflow-tool` PEX targets. `scripts/package-workflow-tools` is a packaging
  bootstrap command, not itself a packaged workflow tool.
- `scripts/smoke-package-workflow-tools` proves structural launcher generation
  and runs POSIX launchers in this Linux checkout; it does not prove native
  Windows runtime execution of generated `.cmd` or `.ps1` launchers.

Constraints:

- Keep `README.md` chat-first. Put procedural detail into focused docs, skills,
  or scripts rather than moving the README top path toward a script runbook.
- Treat `scripts/<tool>` as logical workflow command names. POSIX wrappers may
  exist on Linux; native Windows operators must be able to use packaged `.cmd`
  or `.ps1` launchers.
- Do not introduce WSL-only assumptions.
- Keep all private case inputs, generated outputs, PDFs, code submissions, and
  notes under ignored `cases/`.
- Tracked tests must use anonymized synthetic fixtures only.
- Do not introduce content-substring heuristics that infer review conclusions
  from raw thesis/code text. Workflow decisions must use structured metadata,
  documented parsers, typed evidence classes, explicit operator configuration,
  or reviewer prompts that require evidence verification. Bounded string
  matching is acceptable only for structural parsing such as known metadata
  labels, command markers, file extensions, section headings, or placeholder
  detection.
- Prefer explicit migrations over long-lived compatibility branches in normal
  workflow code.
- Do not preserve compatibility with older `~/code/diplomky` workflows unless
  explicitly requested.
- Run Pants commands sequentially.
- Use Serena for non-trivial Python navigation when practical.
- Use `pants run :omen` as developer-hygiene signal on larger implementation
  slices and final closeout. Do not add Omen to case pipeline gates.

## Scope

In scope:

- inventorying operator versus dev-only command surfaces;
- documenting and testing the command categories for normal packaged workflow
  tools, packaging bootstrap commands, development smokes, and dev-hygiene
  targets;
- adding deterministic tests for helpers and validators still covered mainly by
  shell smokes;
- auditing current case-layout and migration assumptions enough to write a
  follow-up case-format/migration plan;
- auditing supervisor preflight/closeout requirements enough to write a follow-up
  supervisor workflow plan;
- fixing thesis-language resolution in typography/formal checks;
- updating README, skills, docs, packaging, and TODO only where needed for the
  completed reliability work.

Out of scope:

- defining the case-format V1 implementation;
- adding `scripts/check-case-format`;
- adding `scripts/migrate-case` or `scripts/migrate-cases`;
- changing `case-doctor` case-format output beyond audit notes;
- implementing supervisor preflight or supervisor closeout commands;
- executing submitted student code;
- sandbox/container workflow for student code;
- video/demo artifact review;
- figure/media graph/table quality automation;
- historical reference-report comparison;
- expanded GitHub intake;
- literature-source collection automation;
- advanced typography engines such as `pdftotext -bbox`, LanguageTool, or Vale;
- changing grading, scoring, or feedback content policy;
- migrating real private cases during implementation;
- inventing or updating academic-year deadline data without a verified source.

## Wave Boundaries

This active plan is Wave 1 only.

Wave 1, implemented here:

- command-surface classification and packaging-contract tests;
- deterministic-test backlog reduction for the highest-risk helper contracts;
- tracked heuristic audit and guardrails;
- typography thesis-language resolution;
- follow-up plans or TODO entries for case-format/migration and supervisor
  preflight/closeout.

Wave 2, deferred:

- `check-case-format`;
- V1 case-format detector or marker;
- `case-doctor` format diagnostics;
- `migrate-case --dry-run` and any later write/bulk migration semantics.

Wave 3, deferred:

- `supervisor-preflight`;
- `supervisor-closeout`;
- exact supervisor hard/warn gate behavior once the manifest and case-format
  contracts are stable.

Stop conditions:

- If the Slice 1 heuristic audit finds raw thesis/code text substring matching
  that drives grading, feedback wording, evidence conclusions, migration
  decisions, or required role gates without structured evidence or explicit
  operator configuration, stop and redesign before implementing later slices.
- If actual native Windows runtime verification is required, record it as manual
  or CI evidence. Linux launcher generation checks alone are structural coverage.

## Heuristic Audit Seed

The Slice 1 audit must start with at least these known matchers:

| Occurrence | Input | Decision affected | Initial classification | Required action |
|---|---|---|---|---|
| `src/thesis_review_workflow/case_doctor_summary.py` PDF/extract name matching | file names | pairing PDFs with extracted text | structural parsing | keep only as advisory matching; tests must show it does not infer review content |
| `src/thesis_review_workflow/cli/check_tooling.py` PDF/code/GitHub relevance matching | file names and round notes | tooling warnings and GitHub relevance | structural/evidence routing | document as routing; hard gates need explicit URL/evidence markers |
| `src/thesis_review_workflow/agent_coverage.py` code/literature/media triggers | paths, manifest records, limited archive inspection | required reviewer roles | configurable evidence routing candidate | redesign if any raw content substring alone creates a required role |
| `src/thesis_review_workflow/assignment_coverage.py` token overlap | assignment text and generated outputs | advisory coverage state | heuristic-like advisory | ensure output says candidate/advisory and requires reviewer verification |
| `src/thesis_review_workflow/evidence_presence.py` and `check_evaluation_claims.py` metric/media regexes | extracted text and paths | warnings and evidence requests | reviewer-prompt warning | keep warnings non-final; no grading/review conclusion from regex alone |
| `src/thesis_review_workflow/cli/opponent_preflight.py` GitHub URL detection | round notes | GitHub intake gate | structural URL detection | require explicit URL or out-of-scope marker; do not infer contribution quality |

## Slices

### Slice 1 - Plan Review And Reliability Baseline

- Status: pending
- Proposed commit message: `docs(workflow): plan reliability contract work`
- Why: The plan touches command routing, case data, supervisor workflow, tests,
  and docs. It needs a reviewed baseline before implementation.
- Expected paths:
  - `AGENTS.md`
  - `plans/workflow_reliability_contract_plan.md`
  - `TODO.md`
- Tasks:
  - Review this plan with role-split agents before implementation.
  - Inventory remaining TODO items and explicitly keep P1/P2 automation outside
    this plan.
  - Run a current command-surface audit: list POSIX wrappers, Python CLIs,
    `WORKFLOW_COMMAND_MODULES`, `scripts/BUILD` workflow-tool targets, and
    packaged launcher coverage.
  - Run a current deterministic-test audit: identify helper contracts covered
    only by shell smokes.
  - Audit existing reliability helpers for content-substring shortcuts and
    classify each occurrence as structural parsing, configurable evidence
    routing, or a heuristic that must be redesigned before this plan proceeds.
  - Record scope cuts needed to keep this plan reliability-focused.
- Verification:
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

### Slice 2 - Command Surface Inventory And Windows Contract

- Status: pending
- Proposed commit message: `docs(workflow): classify workflow command surfaces`
- Why: Before changing launchers, the repo needs a clear distinction between
  operator workflow commands and developer-only smoke/maintenance helpers.
- TODO source:
  - `TODO.md` P0 native Windows workflow compatibility
  - `TODO.md` P0 deterministic helper contracts
- Expected paths:
  - `README.md`
  - `docs/workflow-command-surface.md`
  - `scripts/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/cli/package_workflow_tools.py`
  - `tests/test_check_scripts_contracts.py`
  - `scripts/smoke-package-workflow-tools`
- Tasks:
  - Define command categories: operator workflow tool, generated/package-only
    helper, packaging bootstrap command, developer smoke, and dev hygiene
    target.
  - Assert that operator workflow tools have a Python CLI module,
    `WORKFLOW_COMMAND_MODULES` entry, POSIX wrapper, Python source target,
    `WORKFLOW_CLI_RUNTIME_DEPS` coverage where needed, `pex_binary` target with
    `tags=["workflow-tool"]`, `output_path="workflow-tools/pex/<tool>"`,
    packaged `.cmd`/`.ps1` launchers, and at least one targeted smoke or
    deterministic test.
  - Treat `scripts/package-workflow-tools` and its `.cmd`/`.ps1` launchers as a
    packaging bootstrap surface that must invoke
    `thesis_review_workflow.cli.package_workflow_tools`, but is intentionally
    absent from `WORKFLOW_COMMAND_MODULES` and packaged `workflow-tool` PEX
    targets.
  - Compare all command registries: executable POSIX wrapper, CLI module file,
    `src/thesis_review_workflow/cli/BUILD`, `WORKFLOW_COMMAND_MODULES`,
    `WORKFLOW_CLI_RUNTIME_DEPS`, `scripts/BUILD` `pex_binary` `output_path`,
    and generated package launcher output.
  - Mark shell-only smoke scripts as development checks, not operator entrypoints.
  - Add tests that fail when a workflow-tool target is missing from the command
    module map or package smoke coverage.
  - Keep `scripts/smoke-package-workflow-tools` phrased as structural generated
    launcher coverage plus POSIX runtime proof in this Linux checkout. Do not
    claim native Windows runtime proof unless a Windows shell/CI run actually
    executed generated `.cmd` or `.ps1` launchers.
  - Keep README top path concise and link details from a focused doc.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_check_scripts_contracts.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 3 - Deterministic Helper-Test Backlog

- Status: pending
- Proposed commit message: `test(workflow): cover remaining helper contracts`
- Why: This slice should reduce reliance on large shell smokes by extracting
  pure helper behavior into fast pytest coverage.
- TODO source:
  - `TODO.md` P0 deterministic tests for remaining workflow validators and
    helper contracts
- Expected paths:
  - `tests/test_workflow_core_helpers.py`
  - `tests/test_review_manifest_helpers.py`
  - `tests/test_case_doctor_summary.py`
  - `tests/test_workflow_python_contracts.py`
  - `src/thesis_review_workflow/*`
  - `src/thesis_review_workflow/cli/*`
  - targeted smoke scripts only when command behavior changes
- Tasks:
  - From the Slice 1 audit, choose the highest-risk helper contracts still
    covered only by shell smoke.
  - Add anonymized pytest fixtures for path validation, manifest/coverage edge
    cases, command-surface contracts, and Markdown shape checks where missing.
  - Add regression coverage around any heuristic-like parsing kept by the plan,
    proving that it is structural/configurable and does not infer a review
    conclusion from raw text alone.
  - Prefer extracting pure helper functions over asserting against long shell
    output.
  - Keep heavy shell smokes as operator confidence checks, not the only
    regression coverage.
  - Update `TODO.md` only for the exact deterministic-test gaps closed by this
    slice.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests::`
  - targeted smoke scripts named by the audit
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 4 - Typography Thesis-Language Resolution

- Status: pending
- Proposed commit message: `fix(workflow): resolve thesis language for typography checks`
- Why: Typography/formal checks must be calibrated by thesis language, not by
  student feedback language or free-form intake wording.
- TODO source:
  - `TODO.md` P0 thesis-language resolution in typography/formal checks
- Expected paths:
  - `src/thesis_review_workflow/metadata.py`
  - `src/thesis_review_workflow/cli/check_typography_formal.py`
  - `tests/test_workflow_core_helpers.py`
  - `scripts/smoke-typography-formal`
  - `README.md`
  - `.agents/skills/thesis-typography-formal-review/SKILL.md`
- Tasks:
  - Define one metadata helper that returns both displayed thesis language and
    rule family, for example `sk` displayed as `sk` with Czech/Slovak rule
    family.
  - Prefer `Thesis language` from `case.md`, then a documented structured round
    thesis-language metadata field.
  - Do not infer thesis language from `Student feedback language`.
  - Do not infer thesis language from free-form `supervisor-intake.md` or
    `opponent-intake.md` language hints.
  - Treat `sk` as language-compatible with Czech/Slovak typography rules while
    preserving displayed metadata as `sk`.
  - Add focused pytest coverage for the metadata helper.
  - Add a smoke case with `Thesis language: sk` and
    `Student feedback language: cs`.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_workflow_core_helpers.py`
  - `scripts/smoke-typography-formal`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 5 - Documentation, Follow-Up Plans, TODO Reconciliation, And Archive

- Status: pending
- Proposed commit message: `docs(workflow): close reliability contract plan`
- Why: The P0 TODO section should reflect exactly what was completed, what was
  narrowed, and what still needs its own future plan.
- Expected paths:
  - `plans/workflow_reliability_contract_plan.md`
  - `TODO.md`
  - `README.md`
  - `docs/workflow-command-surface.md`
  - `plans/case_format_migration_contract_plan.md`
  - `plans/supervisor_workflow_closeout_plan.md`
  - `plans/archive/workflow_reliability_contract_plan.md`
- Tasks:
  - Reconcile completed TODO bullets and preserve only real remaining work.
  - Create or update a follow-up plan for case-format/migration work. It must
    include `layout_current`, `review_ready`, and `provenance_ready` contract
    levels; `check-case-format`; `case-doctor` format diagnostics; and a
    read-only `migrate-case --dry-run` before any write/bulk migration.
  - Create or update a follow-up plan for supervisor preflight/closeout. It must
    explicitly hard-fail on `scripts/check-supervisor-ready`,
    `scripts/init-review-manifest --run-checks`, manifest completeness via
    `scripts/check-review-manifest --require-complete`, required agent coverage
    via `scripts/check-agent-coverage` when coverage is required, feedback
    language/output, and repo hygiene; `case-doctor` remains diagnostic unless
    it identifies required missing inputs.
  - Keep supervisor deadline maintenance as a recurring data task unless a
    verified deadline source was updated during this plan.
  - Record deferred follow-up candidates: student-code sandbox, visual/media
    expansion, video/demo review, graph/table checks, historical report
    comparison, advanced typography, expanded GitHub intake, and literature
    source automation.
  - Run final developer hygiene including Omen and record the result as
    developer evidence, not a case-pipeline gate.
  - Archive this plan under `plans/archive/` after final audit.
- Verification:
  - `pants fmt ::`
  - `pants lint ::`
  - `pants check ::`
  - `pants test tests::`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/smoke-typography-formal`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git status --short --untracked-files=all`
  - `pants run :omen`
  - `git diff --check`

## Deferred TODO Items

These TODO items are intentionally outside this reliability-contract plan:

- Case-format/migration implementation: this plan audits the contract and writes
  a follow-up plan, but defers `check-case-format`, `case-doctor` format
  diagnostics, `layout_current`, `review_ready`, and `provenance_ready`
  readiness levels, and
  `migrate-case`/`migrate-cases` implementation.
- Migration residual controls: `--dry-run`, `--backup`, `--case`, `--all`,
  `--from/--to`, idempotence checks, ignored-workspace operator logs, old-format
  fixtures, and write/bulk migration modes remain open until the migration plan
  implements them.
- Supervisor preflight/closeout implementation: this plan audits hard/warn gate
  semantics and writes a follow-up plan, but defers the actual
  `supervisor-preflight` and `supervisor-closeout` command surface.
- Student-code sandbox workflow: important, but it changes the safety model by
  executing submitted code and needs its own security/process plan.
- Evidence-resolved wording pass for student-facing feedback: useful after the
  supervisor closeout surface is in place.
- Visual/media intake expansion, video/demo review, and graph/table quality
  checks: evidence automation, not base workflow reliability.
- Historical reference-report comparison: calibration feature after opponent
  materials are stable.
- Advanced typography automation: keep the current plan to language-resolution
  correctness, not deeper PDF/layout/prose engines.
- Expanded GitHub intake: larger source-control evidence workflow.
- Literature-source collection automation: separate metadata/download workflow
  with its own cache and privacy boundaries.

## Progress

- Slice 1: completed - plan reviewed with three agents, review findings folded
  back into scope and follow-up requirements
- Slice 2: completed - command surface documented, registry contract tests added,
  packaging smoke boundary reviewed
- Slice 3: completed - deterministic tests added for structural/advisory
  heuristics and duplicate PDF/extract matching removed
- Slice 4: completed - typography language resolver now separates displayed
  thesis language from rule family and ignores free-form intake metadata
- Slice 5: completed - follow-up plans created, TODO reconciled, final hygiene
  run, and archive prepared

## Decision Log

- 2026-05-06: Scoped this plan to P0 workflow reliability. P1/P2 evidence and
  automation work stays deferred so the repository first gets stronger command
  and test contracts, plus reviewed follow-up plans for case-format and
  supervisor closeout contracts.
- 2026-05-06: Kept student-code sandbox execution out of this plan because it
  changes the safety model and should not be mixed into case-format or Windows
  command-surface hardening.
- 2026-05-06: Treated supervisor deadline maintenance as recurring data upkeep,
  not code work, unless implementation later verifies and updates a concrete
  academic-year source.

## Final Audit

Completed on 2026-05-06 and archived under `plans/archive/`.

Slice 5 final checks passed:

- 2026-05-06: agent review found missing explicit supervisor assignment/evidence
  diagnostics and migration dry-run/source-format boundaries; follow-up plans
  and TODO were updated
- 2026-05-06: agent re-review found only missing `git status` and
  `WORKFLOW_MEMORY.md` intake entries; plans were updated
- 2026-05-06: `pants fmt ::` passed
- 2026-05-06: `pants lint ::` passed
- 2026-05-06: `pants check ::` passed
- 2026-05-06: `pants test tests::` passed
- 2026-05-06: `scripts/smoke-package-workflow-tools` passed
- 2026-05-06: `scripts/smoke-typography-formal` passed
- 2026-05-06: `scripts/check-private` passed
- 2026-05-06: `scripts/check-scripts` passed
- 2026-05-06: `git status --short --untracked-files=all` showed only planned
  tracked plan/TODO changes
- 2026-05-06: `pants run :omen` passed with grade A, score 92.09, 6 critical
  hotspots, and 6 high hotspots
- 2026-05-06: `git diff --check` passed

Residual work after archive:

- native Windows runtime proof for packaged launchers remains open in `TODO.md`;
- case-format/migration implementation is planned in
  `plans/case_format_migration_contract_plan.md`;
- write/bulk migration remains a separate TODO after dry-run behavior is stable;
- supervisor preflight/closeout implementation is planned in
  `plans/supervisor_workflow_closeout_plan.md`;
- recurring supervisor deadline maintenance remains open;
- Omen hotspots remain developer-hygiene backlog, not thesis case-pipeline
  gates.

Prior slice evidence:

Plan-preparation checks:

- 2026-05-06: `git diff --check` passed

Slice 4 checks:

- 2026-05-06: agent review found one edge case where invalid `case.md` language
  could be overridden by `round-notes.md`; resolver and regression test were
  updated
- 2026-05-06: agent re-review confirmed the invalid-case metadata edge case was
  fixed
- 2026-05-06: `pants fmt ::` passed after formatting
- 2026-05-06: `pants lint src/thesis_review_workflow:: tests:: scripts::`
  passed
- 2026-05-06: `pants check src/thesis_review_workflow:: tests:: scripts::`
  passed
- 2026-05-06: `pants test tests/test_workflow_core_helpers.py` passed
- 2026-05-06: `scripts/smoke-typography-formal` passed
- 2026-05-06: `scripts/check-private` passed
- 2026-05-06: `scripts/check-scripts` passed
- 2026-05-06: `git diff --check` passed

Slice 3 checks:

- 2026-05-06: explorer audit recommended deterministic tests for
  `matching_extract`, assignment coverage token matching, evidence-presence
  artifact routing, and agent coverage archive triggers
- 2026-05-06: agent review found no blocking findings; non-blocking duplicate
  `check_tooling` PDF/extract matcher was removed by reusing the case-doctor
  matcher
- 2026-05-06: `pants fmt ::` passed
- 2026-05-06: `pants lint src/thesis_review_workflow:: tests:: scripts::`
  passed
- 2026-05-06: `pants check src/thesis_review_workflow:: tests:: scripts::`
  passed
- 2026-05-06: `pants test tests::` passed
- 2026-05-06: `scripts/smoke-assignment-coverage` passed
- 2026-05-06: `scripts/smoke-evidence-presence` passed
- 2026-05-06: `scripts/smoke-case-doctor` passed
- 2026-05-06: `scripts/smoke-agent-coverage` passed
- 2026-05-06: `scripts/smoke-tooling` passed
- 2026-05-06: `scripts/check-private` passed
- 2026-05-06: `scripts/check-scripts` passed
- 2026-05-06: `git diff --check` passed
- 2026-05-06: `scripts/check-private` passed
- 2026-05-06: `scripts/check-scripts` passed

Slice 2 checks:

- 2026-05-06: agent review of command-surface/Windows contract found no
  blocking findings
- 2026-05-06: agent review of docs/test maintainability found two findings;
  plan evidence and package-smoke coverage test were updated before commit
- 2026-05-06: `pants fmt ::` passed after formatting
- 2026-05-06: `pants lint src/thesis_review_workflow:: tests:: scripts::`
  passed
- 2026-05-06: `pants check src/thesis_review_workflow:: tests:: scripts::`
  passed
- 2026-05-06: `pants test tests/test_check_scripts_contracts.py
  tests/test_workflow_python_contracts.py` passed
- 2026-05-06: `scripts/smoke-package-workflow-tools` passed
- 2026-05-06: `scripts/check-private` passed
- 2026-05-06: `scripts/check-scripts` passed
- 2026-05-06: `git diff --check` passed
