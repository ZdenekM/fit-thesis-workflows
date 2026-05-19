# Submission Bundle Intake Plan

Status: active

## Goal

Make the existing review-round workflow handle all-in-one submitted bundles,
especially ZIP archives downloaded from a faculty/operator handoff, without
manual extraction before role agents and deterministic helpers can see the
right evidence.

This plan must extend the current round lifecycle:

- `review-round-start` owns material registration and parent-bundle descriptors.
- `prepare-review-round` owns packet and role-plan preparation.
- `prepare-code-workspace` owns prepared submitted-code roots.
- `review-round-closeout` plus profile-specific closeout commands own final
  convergence.
- `record-review-delta` and `record-workflow-operation` own post-review deltas
  and operation history.

It must not create a parallel import path, parallel closeout path, parallel
operator-delta ledger, or parallel instruction system.

## Audit Base

- `scripts/review-round-start` already accepts parent-bundle descriptors through
  `--submission-bundle`, `--bundle-classification`, and `--bundle-child`.
  Recursive bundle intake should extend this boundary instead of adding another
  submission model.
- Final thesis materials are often handed over as one downloaded ZIP containing
  nested thesis sources, code archives, README files, executable artifacts, APKs,
  videos, or another wrapper directory/archive layer.
- `scripts/prepare-code-workspace` currently works from direct `inputs/`
  children. A large parent bundle can therefore be retained as possible code
  while the actual nested code archive remains invisible until manually
  extracted.
- Demo media, executables, README files, thesis-source archives, and formal
  assignment PDFs inside the same bundle are not visible enough to doctor,
  preflight, packet, and manifest surfaces until they are materialized or
  explicitly inventoried.
- Very large archives are too expensive to list during normal orientation. The
  workflow should record a bounded state such as `not_listed_due_to_size` with
  file size, hash, reason, and next action instead of treating the bundle as
  fully inspected or irrelevant.
- Bundle intake needs to distinguish "discovered in parent bundle" from
  "materialized as a direct round input and ready for downstream helpers".
- Formal assignment artifacts can be nested inside thesis-source folders. The
  readiness gates should be able to reference or materialize those PDFs without
  a manual unzip step, while still treating the rendered thesis PDF as the
  authoritative thesis artifact.
- Archive/code summaries should avoid overstating vendor, package sample,
  generated, or build-cache content. Unity and .NET-style submissions need
  distinct buckets for likely first-party roots, packages/samples, generated
  `bin`/`obj` artifacts, README candidates, and real test evidence.
- `prepare-code-workspace` and `case-doctor` contain overlapping artifact/code
  classification logic. Bundle intake should use shared pure helpers so those
  surfaces do not drift.
- Generic tooling summaries can disagree with specialized import helpers when
  an input PDF has a non-default extracted-text target, such as
  `inputs/theses_similarity/report.pdf` to
  `extracted/theses_similarity/report.txt`. Bundle visibility must reuse the
  same source-to-extract mapping.
- `prepare-review-round` must consume current materiality decisions before
  packet generation. Specialized evidence discovered by bundle intake, such as
  a Theses.cz report or nested assignment PDF, must not be omitted from role
  packets because another checker saw it first.
- Role-plan ownership must match Codex profile capabilities. A read-only role
  handoff must not count as completed role-owned output unless a supported
  parent/human materialization step records the actual artifact.
- Silent internal evidence needs provenance. If bundle-derived evidence is
  reviewed and intentionally not surfaced, the manifest still needs a structured
  covered/no-concern record so materiality does not keep reporting it as
  unresolved.
- `work/current_evidence_snapshot.json`, common briefing, role plans, and
  manifests can become stale after materializing bundle evidence. Recovery must
  extend existing refresh and closeout surfaces, not require hand-edited JSON.
- `review-round-closeout` and profile-specific closeout can disagree after
  reviewed materials already pass. Bundle-driven state changes should make
  missing synthesis/evidence-calibration coverage explicit before final review,
  or map reviewed-material approval to the role-plan states when that is the
  intended coverage.
- Optional bridge drafts for final reports are a separate workflow phase from
  reviewed materials. A generated draft awaiting points/grade/IS selections
  should not make the operator infer that previously reviewed materials became
  invalid.
- Closeout and operation-log writes can fail for operator-environment reasons,
  such as low disk space caused by regenerable caches. Long write-heavy phases
  need an early free-space preflight and safe cleanup guidance.
- `plans/archive/review_pipeline_optimization_plan.md` already established the
  shared lifecycle, `record-review-delta`, `review-round-closeout`, and
  container/reference bundle classification direction. This plan consumes and
  extends those contracts; it must not reimplement them.

## Scope

- Add shared deterministic bundle inventory helpers for nested archives and
  directories.
- Extend `review-round-start` so a parent submitted bundle can be retained once,
  classified as `container_bundle` or `reference_bundle`, inventoried, and tied
  to authoritative decomposed child refs.
- Add materialization support for selected nested candidates while preserving
  parent-bundle provenance and feeding existing direct-input workflows.
- Keep a schema-versioned inventory artifact with stable candidate ids,
  `source_bundle_ref`, `source_bundle_sha256`, `nested_path_chain`,
  `artifact_class`, `reason_codes`, `confidence`, `state`,
  `materialized_ref`, `limits`, and `next_action`.
- Provide deterministic next-action states such as `materialize_candidate`,
  `needs_operator_selection`, `not_listed_due_to_size`,
  `nested_archive_depth_limit`, `duplicate_candidate`, and
  `unsupported_archive_type`.
- Reuse one artifact/archive classification vocabulary across bundle inventory,
  `prepare-code-workspace`, `case-doctor`, preflight, packet summaries, and
  manifest registration.
- Surface discovered versus materialized states in doctor, preflight, packet,
  and operator summaries.
- Register bundle inventory and materialization manifests as provenance inputs
  for evidence artifacts that depend on nested code, media, executable
  artifacts, README files, assignment PDFs, or thesis sources.
- Support silent/no-concern bundle-derived evidence through the existing
  manifest/materiality model.
- Harden stale-state recovery by extending `update-current-evidence-snapshot`,
  `refresh-round-hashes`, `prepare-review-round`, `review-round-closeout`, or
  existing profile closeout commands. Do not add a new closeout owner.
- Add deterministic metadata for media and executable artifacts where cheap and
  safe: extension, size, hash, and optional duration/stream metadata without
  executing submitted code or semantically reviewing media content.

## Non-goals

- Do not inspect video content semantically.
- Do not run untrusted submitted code, executables, or APKs.
- Do not infer thesis quality, assignment fulfillment, plagiarism status, or
  evidence sufficiency from bundle structure.
- Do not preserve compatibility with older repository layouts unless this repo
  still actively supports them.
- Do not create a second bundle-intake model beside `review-round-start`.
- Do not create a new round-state or closeout command that duplicates
  `review-round-start`, `prepare-review-round`, `update-current-evidence-snapshot`,
  `refresh-round-hashes`, or `review-round-closeout`.
- Do not create a new operator-delta ledger. Iterative operator notes,
  post-review corrections, and workflow lessons belong to existing
  `record-review-delta` and `record-workflow-operation` contracts, or to a
  separate future plan that explicitly extends them.
- Do not create a new general review-agent instruction layer. Any later
  consolidation must replace or extend existing owners such as
  `docs/agent-scheduling.md`, `docs/agent-profile-matrix.md`, role skills, or
  `AGENTS.md`; it must not add another always-read rule source.
- Do not introduce operator/developer "modes" that affect review depth,
  readiness gates, role planning, or agent authorization. A future maintainer
  write-scope opt-in may control tracked-file edits only.
- Do not automatically edit reviewer profiles from case feedback. Profile
  adaptation and calibration promotion are deferred follow-up work unless they
  are expressed as extensions to the existing delta/promotion target contract.
- Do not require semantic LLM judgment inside deterministic bundle gates.
- Do not publish private case facts, student details, local paths, source
  snippets, or personal profile contents into tracked workflow files.

## Duplicate-Path Guardrails

- Before adding any command, identify the existing owner. If the behavior
  belongs to an existing owner, extend that owner or create a thin wrapper that
  delegates to it and records the same artifacts.
- `work/submission_bundle_inventory.json` is a routing and provenance artifact,
  not a semantic review artifact and not a second material registry.
- If `scripts/inventory-submission-bundle` is added, it is a diagnostic/helper
  surface over the same library that `review-round-start` uses. It must not
  become the normal intake owner.
- If `scripts/materialize-submission-bundle-candidate` is added, it is a
  candidate-selection helper over the existing round material model. It must
  write provenance and then hand control back to `review-round-start`,
  `prepare-code-workspace`, and `prepare-review-round`.
- Do not add `scripts/refresh-review-round-state`. The needed behavior belongs
  to targeted extensions of `update-current-evidence-snapshot`,
  `refresh-round-hashes`, `prepare-review-round`, `review-round-closeout`, and
  profile-specific closeout.
- Do not add `scripts/record-operator-note`, `scripts/process-operator-inbox`,
  `scripts/propose-profile-update`, or `scripts/check-calibration-governance`
  in this plan. If future work needs them, they must be in focused child plans
  and must extend `record-review-delta`, `record-workflow-operation`,
  existing profile storage, or existing docs instead of creating parallel
  ledgers.
- Any docs or skill edit must delete or replace superseded instructions in the
  old owner. Passing work is not just adding the new rule; it also proves the
  stale active rule was removed or explicitly archived.
- `WORKFLOW_MEMORY.md` remains rationale and lessons, not an active instruction
  source. Active rules belong in `AGENTS.md`, role skills, docs, templates,
  deterministic checkers, reviewer profiles, TODO, or a focused active plan.
- Child plans created from deferred items must supersede the corresponding
  parent text. The same active rule must not live in two active plans.

## Deferred Follow-up Candidates

These are intentionally not implementation slices in this plan:

- Review-agent instruction consolidation: audit duplicated boilerplate, but
  prefer compact extensions to `docs/agent-scheduling.md` and role skills over
  a new shared contract document. Role-specific evidence rules, output paths,
  validators, and review-loop rules stay in owning skills.
- Calibration/profile governance: extend the existing `record-review-delta`
  schema and promotion-target validation if needed. Candidate fields include
  `classification_reason`, `rejected_targets`, `privacy_review`, and
  `profile_proposal_ref`. Do not add a separate calibration ledger first.
- Maintainer write-scope and operator-safe issue reporting: model this as
  tracked-maintenance opt-in, not as a second review mode. Default colleague
  use should write case-local limitations or sanitized issue reports, while
  tracked fixes require explicit maintainer consent and `scripts/check-private`.
- Iterative operator-note batching: if needed, define a staging artifact that is
  non-authoritative while open. On freeze it should emit existing
  `work/review_deltas/*.json` records and operation-log events, then run normal
  closeout. It must not become a second approval/hash authority.
- Local profile audits: keep them private and opt-in. Redacted promotion
  candidates may be produced, but local profile checks must never become a
  tracked-plan or CI prerequisite.

The final slice of this plan may turn the highest-value deferred candidates
into one focused follow-up plan or explicit `TODO.md` entries. That slice is
planning-only: it must not implement deferred work and must remove or supersede
any duplicated active instructions it creates.

## Autonomous Execution Contract

- Execute this plan in commit-sized slices. After each completed slice, update
  `Progress`, run the slice checks plus baseline hygiene, review the diff, fix
  findings, and commit only that slice's intended files.
- At execution start, if this plan is still untracked, first create a plan-only
  tracking commit so resume state is not lost.
- Slice 0 must run before implementation. It reconfirms this plan is focused on
  bundle intake, moves any newly discovered non-bundle work to `TODO.md` or a
  focused child plan, and removes superseded active instructions.
- Tracked implementation work requires explicit maintainer consent. Operator
  case work may write ignored case/local artifacts only.
- Current-request agent authorization remains required before workflow agents
  generate or review sendable/final thesis artifacts. This plan does not waive
  that gate.
- Preserve private case data. Do not stage, force-add, quote, or summarize
  contents of `cases/`, submitted source, extracted thesis text, generated case
  outputs, or local/private profiles into tracked files.
- Prefer root-cause workflow convergence over compatibility layers. When two
  helpers disagree, converge them on a shared contract or source of truth.
- Every new operator-facing helper must follow `docs/workflow-command-surface.md`:
  Python CLI module, logical `scripts/<tool>` wrapper, command registry, Pants
  targets, packaged launchers, and focused tests/smokes. POSIX wrappers remain
  convenience entrypoints; Windows launchers must stay part of the contract.
- Before long-running closeout or write-heavy phases, run the planned free-space
  preflight so unattended execution fails early with recovery guidance.
- Stop on missing private materials, unsafe path/privacy leak, unresolved
  checker failure, blocked required role output, low disk space that prevents
  writes, or a workflow contract conflict requiring operator judgment.

## Slices

0. Plan normalization and stale-instruction cleanup
   - Re-read `plans/README.md`, `AGENTS.md`, `docs/workflow-command-surface.md`,
     `docs/agent-scheduling.md`, `docs/agent-profile-matrix.md`,
     `WORKFLOW_MEMORY.md`, `TODO.md`, and the related archived review-pipeline
     plans before code changes.
   - Confirm this active plan has one concrete outcome: submitted-bundle intake
     through the existing review-round lifecycle.
   - Move any non-bundle implementation work discovered during execution to
     `TODO.md` or a focused child plan. Remove or mark the superseded text in
     this plan so there are not two active sources.
   - Identify stale or contradictory active instructions before adding new ones.
     For every doc/skill edit later in the plan, record which old instruction is
     deleted, replaced, or intentionally retained.
   - Verification: `plans/README.md` contract review confirms one outcome,
     commit-sized slices, exact paths/commands, and no private case data.
   - Verification: plan-only commit records the normalized active plan before
     workflow code, docs, skills, or helper scripts change.

1. Existing lifecycle and classification drift fixes
   - Confirm the current `review-round-start --submission-bundle` descriptor
     fields and document how parent bundle classification, decomposed child
     refs, recursive inventory records, and materialization records map to the
     existing review-run trace.
   - Fix specialized PDF extract mapping before recursive bundle work. Shared
     tooling must recognize non-default mappings such as
     `inputs/theses_similarity/report.pdf` to
     `extracted/theses_similarity/report.txt`.
   - Make `prepare-review-round` consume or refresh the same materiality
     decisions as `check-review-materiality` for specialized imported evidence
     before packet generation.
   - Extract shared pure artifact/archive classification helpers from current
     `prepare-code-workspace` and `case-doctor` logic without behavior change.
   - Add or extend role-plan state checks so read-only role handoffs cannot be
     counted as completed role-owned writes without a writing-capable role or a
     recorded parent/human materialization step.
   - Verification: existing round-start bundle classification tests still pass.
   - Verification: focused specialized-PDF tests prove generic tooling, doctor,
     and specialized importer agree on extract targets.
   - Verification: shared classification tests cover .NET `obj`/`bin`, Unity
     packages/samples, real test paths, README candidates, and unsupported
     archive suffixes without semantic free-text inference.
   - Verification: role-plan negative test proves a read-only chat handoff is
     not counted as completed role-owned output.

2. Shared bundle inventory library
   - Add shared library code, likely
     `src/thesis_review_workflow/submission_bundle.py`, for bounded archive and
     directory inventory.
   - The library records nested artifact candidates, sizes, cheap hashes,
     archive nesting depth, skipped entries, unsupported archive types, and
     budget-limit states.
   - The library uses the shared classification vocabulary from Slice 1.
   - Write schema-versioned `work/submission_bundle_inventory.json` and a concise
     `work/submission_bundle_inventory.md` summary.
   - If a diagnostic CLI is useful, add
     `scripts/inventory-submission-bundle <case-id> [round-id] --bundle
     inputs/<bundle.zip>` as a wrapper over the shared library only. The normal
     intake owner remains `review-round-start`.
   - Verification: Nextcloud-style fixture with wrapper directory, nested code
     archive, thesis-source archive, README, APK placeholder, MP4 placeholder,
     and nested assignment PDF.
   - Verification: large-archive fixture records `not_listed_due_to_size` with
     hash/size/next action and does not classify absence of listed entries as
     absence of code.
   - Verification: zip-slip/path-collision rejection, unsupported archive type,
     UTF-8 filename handling, Windows-style paths/spaces, and stable candidate
     ids.

3. Round-start and materialization integration
   - Extend `review-round-start` to call the shared inventory library when
     `--submission-bundle` is present and to record parent bundle provenance in
     the existing review-run trace.
   - Materialize selected nested candidates through the existing round material
     model. If a helper command is added, for example
     `scripts/materialize-submission-bundle-candidate`, it must be a thin
     candidate-selection wrapper that writes provenance and then hands control
     back to `review-round-start`, `prepare-code-workspace`, and
     `prepare-review-round`.
   - Write a materialization manifest binding each direct `inputs/` artifact to
     original bundle path, nested member path, source hash, action, timestamp,
     collision-safe output path, and selected artifact class.
   - Support nested formal assignment PDFs by materializing them to a stable
     direct input or recording an explicit verified assignment-source reference
     accepted by readiness gates.
   - Preserve ambiguity. If multiple candidates of the same class exist, require
     explicit operator selection or stable disambiguated materialization, and
     mark the ambiguity for doctor/preflight.
   - Verification: bootstrap smoke creates prepared code roots from nested code
     while preserving the original parent bundle as provenance.
   - Verification: duplicate-candidate smoke exposes two possible source
     archives or README files and does not silently choose one.
   - Verification: all new command surfaces follow
     `docs/workflow-command-surface.md` and pass packaged-tool smoke.

4. Doctor, preflight, and packet visibility
   - Teach `case-doctor`, supervisor/opponent preflight, and packet generation
     to show discovered versus materialized bundle evidence.
   - Reuse artifact-specific PDF-to-extract mappings for nested/materialized
     artifacts.
   - Add packet references so role agents see the bundle inventory before
     opening raw archives.
   - Ensure packet generation consumes current materiality decisions for
     specialized imported evidence before declaring role-plan
     `materiality_next_actions` empty.
   - Surface first-party-looking code separately from package/sample/vendor,
     generated, and build-output code.
   - Verification: preflight and packet smokes show code/demo/executable
     evidence for the fixture.
   - Verification: specialized PDF fixture does not produce a false generic
     missing-extract diagnostic after its dedicated importer/checker passes.
   - Verification: imported similarity-report fixture makes
     `prepare-review-round --profile opponent_materials` agree with
     `scripts/check-review-materiality --workflow opponent_review`.
   - Verification: Unity-style and .NET-style fixtures keep samples/generated
     artifacts separate from first-party source and real tests.

5. Manifest and silent-evidence integration
   - Register bundle inventory and materialized nested artifacts as provenance
     inputs, not semantic review findings.
   - Register the materialization manifest as a source for downstream evidence
     artifacts that depend on extracted code, media, executables, README files,
     assignment PDFs, or thesis sources.
   - Extend existing manifest/materiality behavior so silent or no-concern
     bundle-derived evidence can be recorded as `covered_by_synthesis` with
     assessment artifact, covered-by artifact, evidence hash, and used-finding
     marker.
   - Extend `update-current-evidence-snapshot`, `refresh-round-hashes`,
     `prepare-review-round`, and `review-round-closeout` where needed so
     mid-round materialization refreshes deterministic state without
     hand-edited JSON.
   - Verification: manifest smoke records source hashes and limitations without
     requiring media extraction.
   - Verification: mid-round materialization smoke starts from an existing
     profile, materializes a nested artifact, reruns existing refresh/planning
     and closeout commands, and proves coverage/manifest checks pass without
     manual edits.
   - Verification: silent-evidence smoke registers a reviewed no-concern
     artifact and clears materiality next actions without surfacing that
     artifact in report prose.

6. Media and executable evidence ergonomics
   - Keep default intake non-executing and non-semantic.
   - Record cheap deterministic metadata for media and executable artifacts:
     extension, size, hash, and optional duration/stream metadata when available
     without decoding full content or running code.
   - Keep any visual/video observation artifact separate from bundle inventory
     and clearly mark it as operator/media-review evidence.
   - Verification: media fixture records deterministic metadata only by default.
   - Verification: optional media-observation smoke writes separate work
     artifacts and does not change bundle classification.

7. Existing closeout convergence hardening
   - Extend the existing closeout path so bundle-intake changes refresh current
     evidence snapshot, materiality decisions, common briefing, packets/role
     plan, review manifest, agent coverage, and profile final-wave checks in a
     stable order.
   - Distinguish semantic unresolved work from stale deterministic state. A
     stale snapshot hash or missing manifest registration for already-reviewed
     silent evidence should produce exact recovery actions.
   - Make approval refresh idempotent where existing helpers can recompute the
     same current review artifact and basis safely.
   - Align generic `review-round-closeout` and profile-specific closeout after
     bundle materialization. If profile-specific closeout passes, generic
     closeout should either already have matching role coverage or report the
     exact missing role packet before final review starts.
   - Split optional report-draft calibration status from reviewed-materials
     readiness. A draft awaiting human points/grade/IS selections should be
     reported as that, without invalidating green materials state.
   - Add a free-space preflight before write-heavy manifest, coverage, approval,
     and operation-log phases. Report affected filesystem and safe regenerable
     cache candidates without deleting anything automatically.
   - Verification: stale-snapshot smoke mutates a materialized artifact or
     approval record after profile preparation and proves existing closeout
     surfaces recover without manual JSON edits.
   - Verification: stale-approval smoke refreshes approval through the supported
     helper without deleting the old JSON by hand.
   - Verification: opponent-materials fixture proves generic and specialized
     closeout agree on synthesis/evidence-calibration coverage.
   - Verification: optional report-draft fixture reports human calibration
     requirements separately from materials readiness.
   - Verification: low-space unit test or smoke simulates insufficient free
     space for manifest or operation-log writes and produces clear recovery
     guidance.

8. Follow-up plan extraction
   - Review the `Deferred Follow-up Candidates`, final audit findings, operator
     pain observed during implementation, and any remaining TODO overlap after
     bundle intake is working.
   - Select only the highest-benefit next workflow improvement that is not part
     of bundle intake. Prefer one focused follow-up plan over several broad
     plans. Candidate themes are review-agent instruction consolidation,
     calibration/profile governance via `record-review-delta`, maintainer
     write-scope and sanitized issue reporting, or iterative operator-note
     batching.
   - Before creating the follow-up plan, identify the existing owner for each
     proposed behavior and record which commands/docs/skills would be extended.
     Reject any candidate whose first implementation step would create a
     parallel ledger, parallel closeout owner, or second review mode.
   - If a tracked follow-up plan is created, use a concrete path such as
     `plans/review_workflow_followup_plan.md` and give it one concrete outcome
     under the `plans/README.md` contract. If no candidate is mature enough,
     update `TODO.md` instead and explain why no active plan was created.
   - Ensure this parent plan no longer contains active implementation
     instructions for the extracted follow-up. Keep only a progress link,
     archive note, or TODO pointer.
   - Verification: `plans/README.md` contract review confirms the follow-up has
     one outcome, exact owner extensions, commit-sized slices, and no private
     data.
   - Verification: `rg` or equivalent check confirms no active rule is now
     duplicated between this plan, the follow-up plan, `TODO.md`, and existing
     workflow docs.
   - Verification: `git diff --check`, `scripts/check-private`, and
     `scripts/check-scripts`.

## Progress

- Planned after manual extraction was needed during opponent-materials intake
  from an all-in-one submitted bundle.
- Earlier drafting folded in adjacent review-agent, calibration, operator, and
  profile-adaptation ideas so unattended execution could address more workflow
  pain at once.
- Multi-agent plan review on 2026-05-19 found that the broad version had become
  an umbrella roadmap and risked adding duplicate command paths, duplicate
  instruction layers, and duplicate operator-delta state.
- Rewritten on 2026-05-19 as a focused submitted-bundle intake plan. Adjacent
  ideas now live only as deferred follow-up candidates and must extend existing
  owners such as `record-review-delta`, `record-workflow-operation`,
  `docs/agent-scheduling.md`, and `review-round-closeout`.
- Added a final planning-only slice to extract the most valuable deferred work
  after bundle intake completes, without making deferred governance/profile/
  operator-note work part of this active implementation scope.
- 2026-05-19: Plan-only tracking commit created before implementation:
  `96a78c2 docs(plan): track submission bundle intake plan`.
- 2026-05-19: Slice 0 started. Re-read `AGENTS.md`, `plans/README.md`,
  `docs/workflow-command-surface.md`, `docs/agent-scheduling.md`,
  `docs/agent-profile-matrix.md`, `WORKFLOW_MEMORY.md`, full `TODO.md`, this
  plan, and the archived review-pipeline optimization plan. Serena preflight
  succeeded for project `diplomky_v2`; repo Serena config ignores `cases/**`.
- 2026-05-19: Slice 0 audit found no active parallel bundle-intake owner.
  `plans/archive/review_pipeline_optimization_plan.md` is `done` and only
  records the parent-container bundle classification pain that this plan now
  extends. Active `plans/token_efficiency_reuse_plan.md`,
  `plans/case_format_migration_contract_plan.md`, and
  `plans/historical_opponent_calibration_plan.md` remain separate concerns.
  Deferred calibration/profile/operator-note items stay deferred and must not be
  implemented before Slice 8 follow-up extraction.
- 2026-05-19: Slice 0 stale-instruction check kept the existing owner map:
  bundle intake extends `review-round-start`, `prepare-review-round`,
  `prepare-code-workspace`, `review-round-closeout`, `record-review-delta`, and
  `record-workflow-operation`; no new closeout owner, operator-note ledger,
  review mode, or general instruction layer is introduced.
- 2026-05-19: Slice 0 reviewer found one stale superseded root-level plan.
  Moved `plans/supervisor_workflow_closeout_plan.md` to
  `plans/archive/supervisor_workflow_closeout_plan.md`; it remains superseded by
  the shared review-round lifecycle and is no longer an active-plan-directory
  instruction source.
- 2026-05-19: Slice 1 started. Scope is existing lifecycle/classification drift:
  shared artifact/archive classification, specialized PDF extract mapping,
  materiality refresh before packet planning, and role-plan write-ownership
  checks. No recursive inventory or materialization helpers are in scope for
  this slice.
- 2026-05-19: Slice 1 implemented shared structural classification in
  `artifact_classification.py` and routed `case-doctor`,
  `prepare-code-workspace`, and agent-coverage archive/code checks through it;
  added authoritative specialized PDF extract mapping for Theses.cz reports;
  made `prepare-review-round` refresh current evidence/materiality before packet
  generation after validating packet authorization; and tightened role-plan
  closeout so read-only handoff refs do not count as completed role-owned
  outputs.
- 2026-05-19: Slice 1 reviewer findings were fixed before commit: the new
  classification module is included in the slice, specialized PDF mappings are
  authoritative instead of heuristic fallbacks, supervisor-report authorization
  is checked before refresh side effects, and remaining archive/code detection
  in `agent_coverage.py` uses the shared helper module.
- 2026-05-19: Slice 1 checks passed: `pants fmt ::`, `pants lint
  src/thesis_review_workflow:: tests:: scripts::`, `pants check
  src/thesis_review_workflow:: tests:: scripts::`, `pants test
  tests/test_agent_coverage.py tests/test_case_doctor_summary.py
  tests/test_pdf_extracts.py tests/test_import_theses_report.py
  tests/test_review_pipeline_orchestration.py tests/test_round_reuse_index.py`,
  `scripts/smoke-import-theses-report`, `scripts/smoke-case-doctor`,
  `scripts/smoke-prepare-code-workspace`, `scripts/smoke-review-round-start`,
  `scripts/smoke-prepare-review-round`, `scripts/smoke-round-reuse-index`,
  `scripts/smoke-package-workflow-tools`, `git diff --check`,
  `scripts/check-private`, and `scripts/check-scripts`.
- 2026-05-19: Slice 2 started. Scope is a shared bounded bundle inventory
  library and diagnostic helper surface only. Normal intake ownership remains
  `review-round-start`; no materialization behavior is in scope for this slice.
  Serena scoped lookup confirmed `artifact_classification.classify_path_evidence`
  as the shared structural-classification entry point for bundle candidates.
- 2026-05-19: Slice 2 implemented `submission_bundle.py` as the bounded
  structural inventory owner for nested archives/directories, candidate ids,
  source hashes, limits, skipped entries, unsupported archives, size/depth limit
  states, duplicate/selection states, and `work/submission_bundle_inventory.*`
  outputs. Added diagnostic `scripts/inventory-submission-bundle` as a thin
  command-surface-compliant wrapper over that library; normal intake ownership
  still remains `review-round-start`.
- 2026-05-19: Slice 2 focused checks passed before reviewer handoff:
  `pants fmt ::`, `pants test tests/test_submission_bundle.py
  tests/test_workflow_python_contracts.py tests/test_work_artifacts.py`,
  `scripts/smoke-submission-bundle-inventory`, `pants lint
  src/thesis_review_workflow:: tests:: scripts::`, `pants check
  src/thesis_review_workflow:: tests:: scripts::`, and
  `scripts/smoke-package-workflow-tools`.
- 2026-05-19: Slice 2 reviewer findings were fixed before commit:
  generated/vendor/build-output paths keep precedence over executable/media
  artifact classes; diagnostic inventory is not auto-collected as manifest
  provenance until the later manifest slice; nested archive handling now uses
  one recursive bounded path with depth-limit records; directory bundle symlinks
  are skipped before hashing; archive reads have a total budget; Windows-invalid
  member names are rejected; and `next_action` no longer names a materialization
  helper before Slice 3.
- 2026-05-19: Slice 2 post-review checks passed: `pants lint
  src/thesis_review_workflow:: tests:: scripts::`, `pants check
  src/thesis_review_workflow:: tests:: scripts::`, `pants test
  tests/test_submission_bundle.py tests/test_case_doctor_summary.py
  tests/test_work_artifacts.py tests/test_workflow_python_contracts.py`,
  `scripts/smoke-submission-bundle-inventory`,
  `scripts/smoke-package-workflow-tools`, `git diff --check`,
  `scripts/check-private`, and `scripts/check-scripts`.
- 2026-05-19: Slice 3 started. Scope is round-start inventory ownership and
  selected-candidate materialization through direct `inputs/` artifacts with
  provenance. Serena scoped lookup confirmed `review_round_start.execute_action`
  as the existing deterministic action execution hook to extend. No doctor,
  packet, manifest silent-evidence, media-observation, or closeout convergence
  work is in scope for this slice.
- 2026-05-19: Slice 3 implemented `review-round-start` bundle inventory action
  over the Slice 2 library and added
  `scripts/materialize-submission-bundle-candidate` as a thin selected-candidate
  helper. Materialization writes a direct `inputs/` child, preserves ambiguity
  unless `--allow-ambiguous` is explicit, rejects unsafe output paths, updates
  the inventory `materialized_ref`, and records
  `work/submission_bundle_materialization.json` with source bundle, nested path,
  hashes, action, timestamp, output ref, and artifact class.
- 2026-05-19: Slice 3 focused checks passed before reviewer handoff:
  `pants test tests/test_submission_bundle.py
  tests/test_review_pipeline_orchestration.py tests/test_workflow_python_contracts.py`,
  `scripts/smoke-submission-bundle-materialization`,
  `scripts/smoke-review-round-start`, `scripts/smoke-submission-bundle-inventory`,
  `pants lint src/thesis_review_workflow:: tests:: scripts::`, `pants check
  src/thesis_review_workflow:: tests:: scripts::`, and
  `scripts/smoke-package-workflow-tools`.
- 2026-05-19: Slice 3 reviewer findings were fixed before commit:
  materialization smoke now reruns `review-round-start`, prepares code, and
  writes a role plan through `prepare-review-round`; round-start trace text
  names the internal owner instead of the diagnostic helper; materialization
  rejects diagnostic inventories not produced by `review-round-start`; nested
  assignment PDF materialization is covered; multiple submitted bundles are
  aggregated into one inventory action; explicit materialized output refs get
  Windows-portable validation; directory bundle materialization rejects symlink
  parent escapes; and the manifest test now covers source/action/timestamp/hash
  fields plus idempotent reuse and collision rejection.
- 2026-05-19: Slice 3 post-review checks passed: `pants fmt` on touched files,
  `pants lint src/thesis_review_workflow:: tests:: scripts::`, `pants check
  src/thesis_review_workflow:: tests:: scripts::`, `pants test
  tests/test_submission_bundle.py tests/test_review_pipeline_orchestration.py
  tests/test_workflow_python_contracts.py`,
  `scripts/smoke-submission-bundle-materialization`,
  `scripts/smoke-review-round-start`, `scripts/smoke-submission-bundle-inventory`,
  `scripts/smoke-package-workflow-tools`, `git diff --check`,
  `scripts/check-private`, and `scripts/check-scripts`.
- 2026-05-19: Slice 4 started. Scope is discovered/materialized bundle
  visibility in doctor, preflight, and role-packet surfaces. Serena scoped
  lookup confirmed `opponent_packets.generate_packets` as one packet-generation
  owner to extend. Manifest/silent-evidence registration, media observation,
  and closeout convergence remain out of scope until later slices.
- 2026-05-19: Slice 4 implemented shared bundle-visibility rendering over
  `work/submission_bundle_inventory.*` and
  `work/submission_bundle_materialization.json`. `case-doctor`,
  `check-supervisor-ready`, `opponent-preflight`, common briefing, and
  supervisor/opponent/supervisor-report packets now surface discovered versus
  materialized candidates, demo/media/executable candidates, and
  first-party-looking code separately from generated/build/sample/vendor
  summaries. Verification before agent review: `pants test
  tests/test_submission_bundle.py tests/test_opponent_packets.py
  tests/test_opponent_preflight.py tests/test_supervisor_packets.py
  tests/test_supervisor_report_packets.py tests/test_case_doctor_summary.py
  tests/test_review_pipeline_orchestration.py`, `pants lint
  src/thesis_review_workflow:: tests:: scripts::`, `pants check
  src/thesis_review_workflow:: tests:: scripts::`,
  `scripts/smoke-submission-bundle-materialization`, `scripts/smoke-case-doctor`,
  `scripts/smoke-opponent-preflight`, `scripts/smoke-supervisor-packets`,
  `scripts/smoke-supervisor-report-packets`, `scripts/smoke-prepare-review-round`,
  `scripts/smoke-import-theses-report`, `scripts/smoke-package-workflow-tools`,
  `git diff --check`, `scripts/check-private`, and `scripts/check-scripts`.
- 2026-05-19: Slice 4 agent review found that visibility must not treat
  diagnostic inventories as role-intake evidence, supervisor readiness should
  print bundle visibility before early gate failures, bounded/unsupported
  candidates need visible next actions, PDF candidates need expected extract
  refs, and first-party/generated buckets must come from structured summary
  fields. Fixed those findings and added focused tests for diagnostic inventory
  rejection, case/round identity checks, malformed summary tolerance,
  bounded/unsupported next actions, supervisor readiness output ordering, and
  supervisor/supervisor-report packet visibility. Re-ran `pants test
  tests/test_submission_bundle.py tests/test_opponent_packets.py
  tests/test_opponent_preflight.py tests/test_supervisor_packets.py
  tests/test_supervisor_report_packets.py tests/test_supervisor_ready.py
  tests/test_case_doctor_summary.py tests/test_review_pipeline_orchestration.py`,
  `scripts/smoke-submission-bundle-materialization`, `pants lint
  src/thesis_review_workflow:: tests:: scripts::`, `pants check
  src/thesis_review_workflow:: tests:: scripts::`, `scripts/smoke-case-doctor`,
  `scripts/smoke-opponent-preflight`, `scripts/smoke-supervisor-packets`,
  `scripts/smoke-supervisor-report-packets`, `scripts/smoke-prepare-review-round`,
  `scripts/smoke-import-theses-report`, and `scripts/smoke-package-workflow-tools`.
- 2026-05-19: Slice 5 started. Scope is manifest/supporting-work registration,
  source hashing for bundle-derived materialized inputs, current-evidence and
  refresh integration, and silent covered-by-synthesis materiality convergence.
  Serena scoped lookup confirmed `current_evidence_default_source_refs` and
  `collect_supporting_work_artifacts` as existing owners. Media metadata,
  free-space preflight, and closeout-order hardening remain out of scope until
  later slices.
- 2026-05-19: Slice 5 implemented provenance binding for bundle inventories and
  materialization manifests. `work_artifacts` now registers inventory and
  materialization outputs as supporting work, manifest refresh records
  materialization manifests and source hashes for downstream artifacts and
  supporting work that consume materialized inputs or code workspaces, materiality
  checks detect stale supporting-work source hashes, current-evidence defaults
  include bundle visibility refs, and `refresh-round-hashes` can refresh common
  briefing/role-plan hashes after verified materialized input changes. Shared
  `review-round-closeout` now owns the current-evidence refresh and delegates
  supervisor-report closeout with a skip flag to avoid duplicate refresh
  ownership. `smoke-supervisor-report` covers silent Theses.cz evidence through
  `register-review-artifact`, and bundle/closeout smokes cover mid-round
  materialization recovery.
- 2026-05-19: Slice 5 agent review found duplicate current-evidence refresh
  ownership, missing materialization provenance for `supporting_work_artifacts`,
  drift between refresh and manifest code-workspace refs, shallow
  materialization-manifest validation, and a closeout smoke that did not
  exercise post-prepare materialization. Fixed those findings by centralizing
  shared closeout refresh, extending supporting-work dependency injection,
  including code reproducibility refs, validating materialized/file/member
  hashes, and moving the closeout smoke materialization after role-plan
  preparation.
- 2026-05-19: Slice 5 checks passed after fixes: `pants test
  tests/test_submission_bundle.py tests/test_review_manifest_helpers.py
  tests/test_supervisor_report_closeout.py tests/test_review_round_closeout.py
  tests/test_review_materiality.py tests/test_refresh_round_hashes.py
  tests/test_structured_evidence.py`, `pants lint src/thesis_review_workflow::
  tests:: scripts::`, `pants check src/thesis_review_workflow:: tests::
  scripts::`, `scripts/smoke-supervisor-report`,
  `scripts/smoke-review-round-closeout`,
  `scripts/smoke-submission-bundle-materialization`,
  `scripts/smoke-refresh-round-hashes`, `scripts/smoke-review-manifest`,
  `scripts/smoke-package-workflow-tools`, `git diff --check`,
  `scripts/check-private`, and `scripts/check-scripts`.
- 2026-05-19: Slice 6 started. Scope is structural-only media/executable
  ergonomics: cheap deterministic extension/size/hash metadata in the existing
  bundle inventory and the existing media-presence work artifact. No submitted
  code execution, semantic video/image/audio inspection, new media-review
  command, or bundle-classification side path is in scope.
- 2026-05-19: Slice 6 implemented shared non-executing metadata for media and
  executable artifacts. Bundle candidates and `work/media_presence_inventory.jsonl`
  now record extension, size, hash when available, and explicit
  non-execution/non-semantic state; large bounded media candidates record that
  hashes were not collected instead of implying content absence. The media
  suffix taxonomy is shared through structural classification so nested bundle
  media and materialized media use the same metadata path. Active operator docs
  now describe media presence as path/suffix plus deterministic non-semantic
  metadata.
- 2026-05-19: Slice 6 agent review found no blocking duplicate workflow path, but
  requested proof that optional media observation stays separate from bundle
  classification, one shared media taxonomy, active doc updates, and reuse of an
  existing hash helper. Fixed those findings by adding a `visual_inventory.jsonl`
  smoke assertion that leaves `work/submission_bundle_inventory.json` unchanged,
  moving image/presentation/audio/video suffixes into the shared classifier,
  updating README/opponent workflow wording, and using the existing
  `artifact_validation.sha256_file`.
- 2026-05-19: Slice 6 checks passed after fixes: `pants fmt` on touched files,
  `pants test tests/test_submission_bundle.py tests/test_evidence_presence.py`,
  `pants lint src/thesis_review_workflow:: tests:: scripts::`, `pants check
  src/thesis_review_workflow:: tests:: scripts::`,
  `scripts/smoke-evidence-presence`,
  `scripts/smoke-submission-bundle-materialization`,
  `scripts/smoke-package-workflow-tools`, `git diff --check`,
  `scripts/check-private`, and `scripts/check-scripts`.
- 2026-05-19: Slice 7 started. Scope is hardening the existing
  `review-round-closeout` and delegated profile closeout path: stable refresh
  order, stale deterministic-state recovery messages, optional draft-calibration
  status separation, and an early free-space preflight. Serena scoped lookup
  confirmed `generic_closeout_steps` as the shared closeout owner and
  `check_opponent_report.check_text` as the existing report-draft calibration
  validator to extend. No new closeout command or parallel round-state refresh
  path is in scope.
- 2026-05-19: Slice 7 implemented convergence hardening in existing owners.
  `review-round-closeout` now runs the stable refresh sequence through readiness,
  current evidence, materiality, common briefing, role-plan refresh, manifest,
  role-plan closeout, review deltas, and profile gates. Existing profile closeout
  commands now share a free-space preflight, and direct write-heavy surfaces
  `init-review-manifest`, `write-review-approval`, and
  `record-workflow-operation` stop before writes when the preflight fails.
  Opponent materials closeout reports pending bridge-draft point/grade/IS
  calibration separately while strict canonical report checking still rejects
  explicit invalid values.
- 2026-05-19: Slice 7 agent review found that the first preflight draft only
  reported low space instead of stopping later write-heavy steps, direct
  manifest/approval write commands also needed the preflight, supervisor-report
  role-plan recovery wording lacked the full authorization command, pending
  opponent draft calibration was too broad for explicit invalid values, and docs
  still described the old strict opponent-closeout contract. Fixed each finding
  before commit.
- 2026-05-19: Slice 7 checks passed after fixes: `pants test
  tests/test_closeout_preflight.py tests/test_opponent_report.py
  tests/test_review_manifest_helpers.py tests/test_review_round_closeout.py
  tests/test_supervisor_report_closeout.py tests/test_review_approvals.py`,
  `scripts/smoke-review-round-closeout`, `scripts/smoke-opponent-closeout`,
  `scripts/smoke-supervisor-report`, `scripts/smoke-review-manifest`,
  `scripts/smoke-opponent-report`, `pants lint src/thesis_review_workflow::
  tests:: scripts::`, `pants check src/thesis_review_workflow:: tests::
  scripts::`, `scripts/smoke-package-workflow-tools`, `git diff --check`,
  `scripts/check-private`, and `scripts/check-scripts`.

## Decision Log

- Keep this active plan focused on submitted-bundle intake. Review-agent
  governance, calibration governance, operator maintainer write-scope, profile
  adaptation, and iterative operator-note batching are not implementation
  slices here.
- Recursive inventory and materialization extend the existing
  `review-round-start` parent-bundle/decomposed-child contract.
- `work/submission_bundle_inventory.json` is routing/provenance evidence, not
  semantic review evidence and not a second material registry.
- Do not add `scripts/refresh-review-round-state`. Stale-state recovery belongs
  to existing refresh, planning, and closeout surfaces.
- Do not add new operator-note or profile-update ledgers in this plan. Future
  batching/adaptation work must extend `record-review-delta`,
  `record-workflow-operation`, and existing profile storage.
- Shared review-agent instruction cleanup should reduce active rule locations,
  not add one. Any future consolidation should update existing docs/skills and
  remove superseded boilerplate.
- Deterministic bundle gates may classify artifact kinds and provenance, but
  must not infer thesis quality, runtime success, assignment fulfillment, or
  media semantics.
- Prefer one retained original bundle plus typed nested inventory over copying
  every large artifact by default.
- Preserve ambiguity. Duplicate candidates must stay visible until operator or
  explicit workflow selection resolves them.
- No-concern evidence should stay silent in public prose when appropriate; the
  manifest/materiality system should record coverage instead of forcing prose
  mentions.
- Follow-up extraction is allowed only as a final planning slice. It can create
  a focused next plan or TODO routing, but it cannot implement deferred work or
  leave the same active rule in two places.

## Final Audit

- Not started.
