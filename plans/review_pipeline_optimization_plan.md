# Review Pipeline Optimization Plan

Status: active
Created: 2026-05-15

Execution readiness: ready for autonomous, slice-by-slice implementation after
the 2026-05-15 multi-agent review closeout recorded in `Final Audit`. Start at
Slice 1. Do not run a separate open-ended "review the plan again" phase before
implementation; review findings from an explicitly authorized implementation
rollout should be folded into the current slice and `Progress` before moving on.

## Goal

Reduce elapsed time and manual bookkeeping for code-bearing thesis review rounds
while preserving the current evidence standard: role-split semantic review,
profile-specific independent review, case-private artifacts, and hash-bound
provenance.

The target is not a weaker review and not a single supervisor-feedback shortcut.
The target is a shared review-pipeline layer that can serve these workflow
profiles without duplicating orchestration logic:

- `supervisor_feedback`: iterative student-facing supervisor feedback;
- `supervisor_report`: formal supervisor report draft/review/confirmation;
- `opponent_review`: canonical materiality/provenance profile for internal
  opponent materials and report-trace readiness;
- `opponent_materials`: operator wave/skill surface for drafting and reviewing
  opponent materials, mapped to canonical profile `opponent_review`;
- `opponent_report_review`: review of a human or generated opponent-report
  draft;
- reusable internal evidence roles such as code consistency, code quality,
  figure/media, quantitative claims, literature/citation, typography/formal, and
  Theses.cz similarity review.

Each profile still owns its final artifact, tone, consumer, checks, and review
boundaries. The shared layer owns the predictable path:

- fresh-material expectations are captured as explicit typed operator/parent-agent
  input before deterministic commands run;
- current materials are confirmed before a round starts;
- required roles are known before agents are spawned;
- compact packets and current reusable evidence are prepared once;
- role outputs register generator, synthesis use, checks, and hashes as they are
  created;
- final manifest and role-coverage closeout validates in the normal path
  without manual JSON repair;
- repeated rounds use source fingerprints and prior reviewed outputs to avoid
  unnecessary full re-review;
- post-review operator corrections have a bounded delta path that reopens
  independent review only to the required scope and promotes durable generic
  lessons into the right workflow docs/skills.

Success for a comparable final code-bearing supervisor-feedback pilot round is a
normal elapsed time of about 25-35 minutes instead of roughly an hour, without
losing code consistency, code quality, quantitative, figure/media,
typography/formal, or independent final-review coverage when those roles are
material. Success for other profiles is measured by the same reduction in
manual reconciliation and repeated context opening, with profile-specific
readiness gates still passing.

## Audit Base

This plan follows a recent code-bearing final supervisor-feedback round and a
follow-up operator calibration pass on the same reviewed artifact. It records
only case-neutral workflow findings; private thesis facts, student names, PR
details, PDFs, and generated case outputs belong under ignored `cases/`, not in
this tracked plan.

Observed friction:

- The prompt described newly finished thesis material, but the workflow did not
  first verify that the active case had a matching newer PDF/source archive.
  Starting from stale copied artifacts caused avoidable rework.
- Required role coverage was discovered late. The figure/media role had to be
  run after the final feedback review because `check-agent-coverage` inferred it
  from available visual/media evidence only during closeout.
- Evidence artifacts were generated correctly, but their provenance metadata was
  not registered at creation time. `generated_by`, `used_findings`,
  synthesis-covered evidence hashes, and common-briefing hashes needed manual
  repair before `check-review-manifest --require-complete` could pass.
- Several agents reopened overlapping PDF, source, PR, and test context. The
  workflow had packets and snapshots, but not a single current role-wave plan
  that told each agent which compact evidence was authoritative and which full
  artifacts to open only on explicit triggers.
- Existing reuse infrastructure can reduce repeated work, but the workflow does
  not yet make "unchanged reusable", "changed delta required", "current reviewed
  evidence", and "fresh full role review" visible as an operator-facing round
  plan before agent work begins.
- Final closeout checks are individually good, but the normal path still
  required ad hoc sequencing and manual reconciliation across
  `work/review_manifest.json`, `work/agent_coverage.json`, role outputs, review
  approvals, helper checks, and common briefing records.
- A post-review operator correction required reopening the student-facing output,
  checking the correction against thesis/code evidence, rerunning independent
  review, and promoting a case-neutral lesson into instructions/skills. The
  workflow handled this manually, but it exposed a general need for a bounded
  `operator_delta` path across reviewed artifacts.
- The new lesson was not supervisor-feedback-specific: implementation
  readability, diagram-vs-prose guidance, and unit-vs-integration test-layer
  calibration affect student feedback, formal supervisor reports, opponent
  materials, and report-review preparation differently, but the intake,
  verification, review-reopen, and promotion mechanics are shared.
- Starting a formal supervisor-report round still required manual reconstruction
  of profile-specific intake. `import-round` created generic supervisor notes but
  not the required `notes/supervisor-report-operator-input.md`, even though
  `check-supervisor-report-ready` depends on that exact file and the template has
  a different source name.
- Supervisor-report trace validation rejected a manual-check reference to draft
  and reviewed outputs that the trace/draft workflow is about to create. This is
  correct for strict hash-bound evidence, but the normal path needs a clearer
  "expected future output" representation so parent agents do not debug schema
  mechanics during synthesis.
- After required role artifacts existed and their validators passed, supervisor
  report packet preparation still printed materiality next-action text that read
  like missing evidence because synthesis/manifest coverage had not yet recorded
  those artifacts. The operator-facing wording should distinguish "file missing",
  "validator failed", "not synthesis-covered", and "not standalone-reviewed".
- A Theses.cz assessment recorded the generated role packet as one of its own
  source refs. Because packets include common-briefing hashes and are regenerated
  late, this created an avoidable hash cycle during closeout. Agent-authored
  structured evidence should cite primary case artifacts and stable operator
  notes, not the generated packet that instructed the agent.
- An imported Nextcloud-style submission bundle was copied both as the parent
  container archive and as decomposed authoritative PDFs, code archives, APK, and
  media. Later code/materiality helpers then saw the parent archive as an
  extra large possible-code input and produced avoidable warnings. Round-start
  import needs a typed `container_bundle` or `reference_bundle` classification
  so decomposed child artifacts are authoritative while the parent bundle remains
  retained for provenance.
- Multiline CLI text passed to case bootstrap with escaped `\n` sequences was
  persisted literally in assignment metadata and had to be repaired manually.
  Round-start/bootstrap should normalize escaped newlines or prefer a
  `--*-file` input for multiline assignment summaries, then warn when literal
  backslash-newline text appears in structured notes.
- A figure/media review agent stalled before writing its required artifacts.
  The parent could recover with a narrow manual inventory, but the workflow had
  no artifact-progress deadline, role-specific recovery checklist, or validator
  handoff that preserved the independent-review boundary. Long-running role
  agents need progress expectations that are about durable files, not chat-only
  activity.
- Advisory static analysis can fail too quietly in case-local prepared code
  roots. In this run, Omen returned zero files/functions for relevant source
  roots; that should be recorded as `unsupported_or_uninformative` with scope
  and language context rather than looking like a successful empty analysis.
- Closeout provenance can still create hash cycles when a current-evidence
  snapshot records self-updating closeout artifacts such as the review manifest
  or agent coverage, while the common briefing and manifest also record the
  snapshot. The closeout path needs a stable evidence-snapshot source set or a
  two-phase generated-artifact classification so `check-review-manifest
  --require-complete` does not require manual ordering knowledge.
- Supervisor-feedback review approval naming was inconsistent across the
  pre-Slice-1 workflow surface: some code and tests used a feedback-student
  named review record, while the agent profile registry and matrix already used
  `work/reviews/supervisor_feedback_review.json`. Slice 1 chooses the
  profile-named path as canonical and updates the registry, wave gate, approval
  helpers, tests, smokes, docs, and TODO together; do not add an alias/fallback
  layer for the old path.

Current related implementation:

- `plans/supervisor_workflow_closeout_plan.md` already plans supervisor
  preflight and closeout command bundles. This plan supersedes that separate
  supervisor-only implementation path by making `review-round-start` and
  `review-round-closeout` the shared command owners; Slice 1 updates the older
  plan and `TODO.md` to reflect that decision before code work starts.
- `plans/token_efficiency_reuse_plan.md` has already implemented the reusable
  source-fingerprint, reuse-index, common-briefing, evidence-capsule,
  claim-basis, materiality coverage, manifest-dependency, submitted-report,
  report-amendment, helper-check ordering, and context-budget contracts. This
  plan consumes and extends those contracts; it must not reimplement parallel
  variants.
- `scripts/check-supervisor-ready`, `scripts/init-review-manifest --run-checks`,
  `scripts/check-agent-coverage`,
  `scripts/check-review-manifest --require-complete`,
  `scripts/check-feedback-language`, and `scripts/check-feedback-output` are the
  current hard gates for reviewed student-facing feedback.
- `scripts/register-review-artifact` can update manifest records, but its
  low-level interface is too manual for common review role outputs.
- `work/reviews/supervisor_feedback_review.json` is the canonical structured
  approval record for the independent supervisor-feedback review after Slice 1.
  Existing feedback-student-named approval-record references are treated as
  current debt to remove in the same slice, not as a second supported contract.
- Existing opponent workflow surfaces already have stronger packet and closeout
  coverage than supervisor feedback. This plan should reuse those contracts and
  fill shared gaps rather than invent a parallel opponent pipeline.
- `plans/token_efficiency_reuse_plan.md` and the archived
  `plans/archive/review_context_efficiency_plan.md` already establish the
  packet-first, materiality-aware, approval-record, and closeout-integration
  direction. This plan should turn those shared contracts into a round-level
  orchestration path, not re-litigate the context-efficiency design.
- `docs/agent-profile-matrix.md` and
  `src/thesis_review_workflow/agent_profiles.py` are the profile-routing source
  of truth for role ownership. Any new orchestration profile or role-state name
  must keep those files synchronized.

## Target Operator Path

For any supported review profile, the optimized path should be:

1. Start the round with `review-round-start`, passing the workflow profile plus
   explicit current materials such as PDF, source archive, submitted code
   archive, GitHub PR URL, Theses.cz report, or already reviewed report draft.
2. The parent agent or operator passes typed freshness intent such as
   `fresh_materials_expected=true`; deterministic commands do not parse raw chat
   prose to infer that intent. If the expected current materials are missing or
   older than the previous reviewed round, the start command stops before packet
   or role-plan preparation unless the operator explicitly asks for a typed
   provisional stale-artifact review.
3. The command imports/extracts materials, refreshes current evidence, imports
   GitHub snapshots when requested, prepares code workspaces when code evidence
   exists, writes `work/review_run_trace.json`, and prints the next deterministic
   command.
4. `prepare-review-round` writes `work/review_role_plan.json` with
   `workflow_profile`, `materiality_profile` where relevant, `final_artifact`,
   profile gates, role states, role packets, and wave schedule before any
   semantic reviewer is spawned. Coverage requirements are separate from
   fresh-review requirements.
5. The parent agent runs role agents in bounded waves from that plan. Each role
   writes its output and a small structured sidecar or manifest-registration
   record.
6. The parent synthesis writes the profile draft, records exactly which role
   findings were used, and invokes the profile-specific independent review pass.
7. If the operator later challenges or amends the reviewed wording, the pipeline
   records a bounded `operator_delta` with old/new hashes, affected claims,
   evidence needed, and the required review path. Case-specific fixes stay in the
   case; durable general lessons are promoted to skills/docs/TODO only after the
   current artifact is fixed and re-reviewed.
8. One closeout command consumes the role plan and manifest records, refreshes
   manifest/checks, validates required role outputs or typed limitations, final
   review, profile-specific output shape, private-path safety, script hygiene,
   and whitespace hygiene.
9. The final operator response can report passed gates and residual risks
   without mentioning manual manifest surgery.

## Scope

In scope:

- a case-neutral review round-start/orchestration command or command bundle with
  profile adapters for supervisor feedback, supervisor reports, canonical
  opponent review/materials, and opponent-report review;
- the explicit deterministic command boundary
  `review-round-start` -> `prepare-review-round` -> role waves ->
  `review-round-closeout`, with no hidden semantic-agent spawning from scripts;
- command-ownership reconciliation with the planned supervisor closeout bundle
  and the existing opponent preflight/closeout commands before adding generic
  dispatcher names;
- fresh-material checks for follow-up rounds where the operator says the student
  added, finished, or changed current materials;
- deterministic role-plan generation before agent spawning;
- integration with current evidence snapshots, materiality, reuse-index, and
  packet rendering;
- provenance registration presets for common review artifacts across profiles;
- manifest/common-briefing refresh ordering that prevents stale hash records
  after late role artifacts are created;
- closeout integration with existing or planned supervisor and opponent closeout
  commands;
- a bounded post-review operator-delta path for amendments, challenges, and
  durable lesson promotion after a reviewed artifact changes;
- tests and smoke fixtures using anonymized synthetic data only;
- README, skill, and TODO updates after behavior exists.

Out of scope:

- lowering the evidence bar for code-bearing review rounds;
- replacing the required independent review loop for
  sendable or final review artifacts;
- automatically running unknown student code, ROS, MoveIt, Docker, hardware, or
  external CI by default;
- making Omen or heavyweight static-analysis tools a required case-pipeline
  gate;
- embedding concrete private case facts, metric values, filenames, PR states, or
  student-specific lessons in tracked workflow rules;
- fully automating Codex subagent spawning from a script if the runtime does not
  expose a stable non-interactive agent API. Scripts may prepare role plans,
  packets, sidecar records, and exact operator instructions; agent execution can
  remain parent-agent orchestrated.
- collapsing profile semantics into one generic prose policy. Student-facing
  final-sprint action language, formal supervisor-report grading/IS wording, and
  opponent confidence/report-defensibility wording must remain profile-specific.

## Design Constraints

- Do not introduce brittle free-text heuristics over thesis/code prose. Freshness
  and role routing must use explicit operator inputs, file timestamps/hashes,
  structured case metadata, current-evidence snapshots, reuse indices,
  manifests, role plans, or agent-produced structured artifacts.
- Keep case data and generated outputs under ignored `cases/`.
- Keep Windows supported: operator-facing helpers need Python/Pants/PEX command
  surfaces and packaged `.cmd`/`.ps1` launchers.
- Run Pants commands sequentially.
- Prefer Serena for non-trivial Python navigation and edits.
- Keep active plans case-neutral. Any future pilot notes about a real case go
  under the ignored case workspace.
- Preserve the current bounded-agent-concurrency rule from `AGENTS.md` and
  `docs/agent-scheduling.md`.
- Treat `workflow_profile` as a typed orchestration contract, not as a display
  string and not as the same thing as a Codex agent role profile. Workflow
  profiles own final artifacts, approval records, role coverage, closeout gates,
  tone boundaries, and operator-visible readiness semantics. Agent role profiles
  in `src/thesis_review_workflow/agent_profiles.py` own spawned-role routing,
  sandbox, allowed writes, and validators.
- Keep canonical deterministic workflow-profile values aligned with current
  materiality/provenance registries: `supervisor_feedback`,
  `supervisor_report`, and `opponent_review`. `opponent_materials` remains a
  wave/skill/operator surface mapped to `opponent_review`; do not create a
  second materiality profile for it in this plan. `opponent_report_review` is a
  final-review workflow surface with approval semantics and either maps to
  `opponent_review` for inherited materiality context or explicitly records that
  no materiality profile applies.
- `work/review_role_plan.json` must record both `workflow_profile` and
  `materiality_profile` when they differ or when no materiality profile applies,
  so validators do not accidentally extend `review_materiality.WORKFLOW_PROFILES`
  with report-review-only values.
- Treat existing token-efficiency artifacts as dependencies:
  `work/common_briefing.json`, `work/reuse/reuse_index.json`,
  `work/context/evidence_capsules.json`,
  `work/context/claim_review_basis.json`, existing materiality decisions,
  review approvals, submitted-report records, report-amendment records, and
  context-budget reports.

## Slices

### Slice 1 - Command Ownership, Workflow Profiles, And Trace Schema

- Status: completed 2026-05-15
- Proposed commit message: `fix(workflow): align review profile contracts`
- Expected paths:
  - `plans/review_pipeline_optimization_plan.md`
  - `plans/supervisor_workflow_closeout_plan.md`
  - `TODO.md`
  - `docs/agent-profile-matrix.md`
  - `src/thesis_review_workflow/agent_profiles.py`
  - `src/thesis_review_workflow/agent_coverage.py`
  - `src/thesis_review_workflow/review_profiles.py`
  - `src/thesis_review_workflow/review_materiality.py`
  - `src/thesis_review_workflow/review_wave_gate.py`
  - `src/thesis_review_workflow/review_approvals.py`
  - `src/thesis_review_workflow/review_pipeline_orchestration.py`
  - `tests/test_agent_profile_contracts.py`
  - `tests/test_review_approvals.py`
  - `tests/test_review_wave_gate.py`
  - `tests/test_review_pipeline_orchestration.py`
  - `scripts/smoke-review-approval`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-review-wave`
- Tasks:
  - Add `src/thesis_review_workflow/review_profiles.py` as the workflow-profile
    registry consumed by orchestration: canonical `workflow_profile`, optional
    `materiality_profile`, operator surface name, final artifact, draft artifact,
    approval record, required/optional role coverage, closeout gates, and
    readiness wording.
  - Keep `src/thesis_review_workflow/agent_profiles.py` and
    `docs/agent-profile-matrix.md` as the spawned-agent role-routing source of
    truth. `review_profiles.py` may reference agent route ids, but must not
    derive workflow final-artifact semantics from the matrix table.
  - Canonicalize supervisor-feedback approval records to
    `work/reviews/supervisor_feedback_review.json` and update
    `review_wave_gate.py`, `review_approvals.py`, `agent_coverage.py`,
    `agent_profiles.py`, `docs/agent-profile-matrix.md`, smokes, tests, TODO,
    and this plan in one slice. Remove stale feedback-student-named approval
    references instead of supporting both names.
  - Keep canonical materiality/provenance profiles aligned with current
    validators: `supervisor_feedback`, `supervisor_report`, and
    `opponent_review`. Do not introduce a second `opponent_materials`
    materiality profile in this plan; a future migration would need its own
    explicit registry/validator/docs plan.
  - Make command ownership explicit: this plan owns generic
    `review-round-start` and `review-round-closeout`; existing
    `opponent-preflight`, `opponent-closeout`, and `supervisor-report-closeout`
    remain supported lower-level/profile commands only when the generic
    dispatcher delegates to them. The separate supervisor-only closeout plan is
    marked `superseded` by this generic plan, and any genuinely remaining
    supervisor-only diagnostic is copied into this plan or `TODO.md`.
  - Update `TODO.md` so the open supervisor-closeout item points to the chosen
    command owner instead of requiring a parallel supervisor command family.
  - Define a small timing/trace schema for `work/review_run_trace.json` with
    phases such as start, import, extraction, packet prep, role plan, role waves,
    synthesis, independent review, operator delta, manifest refresh, and
    closeout. Keep the trace case-private and hash/path oriented.
  - Add pure tests for workflow-profile registry invariants, agent-profile
    cross-links, trace shape, case-private path handling, approval-record naming,
    and the opponent-materials-to-`opponent_review` mapping.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_agent_profile_contracts.py tests/test_review_approvals.py tests/test_review_wave_gate.py tests/test_review_pipeline_orchestration.py`
  - `pants test tests/test_work_artifacts.py`
  - `scripts/smoke-review-approval`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-review-wave`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`
  - Result 2026-05-15: passed. `tests/test_work_artifacts.py` was added as an
    extra focused check because Slice 1 registered `work/review_run_trace.json`
    as a work artifact.

### Slice 2 - Round-Start Planner And Fresh-Material Contract

- Status: completed 2026-05-15
- Proposed commit message: `feat(workflow): plan review round start`
- Expected paths:
  - `src/thesis_review_workflow/review_pipeline_orchestration.py`
  - `src/thesis_review_workflow/review_materiality.py`
  - `src/thesis_review_workflow/review_profiles.py`
  - `tests/test_review_pipeline_orchestration.py`
- Tasks:
  - Implement a pure round-start planner, not the CLI yet. Inputs are explicit:
    case id, round id, canonical workflow profile, current PDF/source/code
    archive descriptors, GitHub URL or imported snapshot request, Theses.cz
    report descriptor, reviewed report draft descriptor, and whether fresh
    materials are expected.
  - Hard-fail when `fresh_materials_expected=true` but the active round has no
    matching newer or explicitly current artifacts, unless the operator selected
    a typed provisional stale-review mode. Do not infer freshness from raw prompt
    prose or thesis/code free text inside deterministic code; the parent agent
    or operator must translate chat intent into explicit planner inputs.
  - Reuse existing import/extract/GitHub/code-workspace helpers rather than
    duplicating their logic; the planner should return ordered actions such as
    import, extract, prepare code workspace, import GitHub snapshot, update
    current evidence, update reuse index, run readiness gate, and prepare role
    plan.
  - Encode profile readiness gate selection from the Slice 1 registry:
    `check-supervisor-ready` for `supervisor_feedback`, supervisor-report
    readiness/confirmation gates for `supervisor_report`, `check-round-ready`
    plus opponent-specific gates for `opponent_review`, and report-review gates
    for `opponent_report_review`.
  - Return the next deterministic command explicitly: after successful start the
    normal next action is `prepare-review-round`, not semantic agent spawning.
    The planner may expose a convenience flag later, but the baseline contract is
    the two-command boundary from the target path.
  - For profile-specific intakes, create or copy the exact required note files
    with the canonical target names, for example
    `notes/supervisor-report-operator-input.md` for `supervisor_report`, rather
    than leaving agents to discover template-name differences after import. This
    slice plans the action; Slice 3 performs the write.
  - Classify submission parent archives explicitly as `container_bundle` or
    `reference_bundle` when their contents are decomposed into authoritative
    PDF/source/code/media inputs. Retain the parent archive inside the ignored
    round for provenance, but keep code/materiality helpers from treating it as
    another independent code submission.
  - Normalize escaped newline sequences in CLI metadata fields, or require file
    inputs for multiline assignment summaries and private notes. This slice
    defines planner diagnostics for literal `\n`; Slice 3 exposes CLI behavior.
  - Add tests for fresh/current/stale cases, provisional stale-review mode,
    container/reference bundle classification, newline diagnostics, and profile
    gate selection.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_review_pipeline_orchestration.py`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`
  - Result 2026-05-15: passed.

### Slice 3 - Review Round Start Command

- Status: completed
- Proposed commit message: `feat(workflow): start review rounds`
- Expected paths:
  - `scripts/review-round-start`
  - `scripts/BUILD`
  - `docs/workflow-command-surface.md`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/review_round_start.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/review_pipeline_orchestration.py`
  - `src/thesis_review_workflow/review_profiles.py`
  - `tests/test_review_pipeline_orchestration.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-review-round-start`
- Tasks:
  - Expose the Slice 2 planner as `scripts/review-round-start`.
  - Support explicit profile and material inputs; for multiline assignment,
    intake, and private notes, prefer `--*-file` options and normalize literal
    escaped newlines only according to the planner contract.
  - Perform only deterministic round-start actions: create/copy required
    profile note files, call existing import/extract/GitHub/code-workspace
    helpers, update current evidence/reuse sidecars, and run the selected
    readiness gate. Do not spawn semantic agents from the script.
  - Write `work/review_run_trace.json` entries for started actions, skipped
    actions, blockers, readiness result, and next command. This command does
    not write `work/review_role_plan.json`; Slice 4 owns that output through
    `prepare-review-round`.
  - Keep all imported materials, logs, traces, and generated sidecars inside the
    ignored case round workspace.
  - Wire the command through the standard command surface, Pants/PEX packaging,
    generated launchers, and a smoke script with anonymized synthetic data.
  - Update `docs/workflow-command-surface.md` and workflow command-contract tests
    so the logical command, POSIX wrapper, PEX target, and generated `.cmd`/`.ps1`
    launchers stay aligned.
- Verification:
  - `pants fmt ::` - passed
  - `pants lint src/thesis_review_workflow:: tests:: scripts::` - passed
  - `pants check src/thesis_review_workflow:: tests:: scripts::` - passed
  - `pants test tests/test_review_pipeline_orchestration.py tests/test_workflow_python_contracts.py` - passed
  - `scripts/smoke-review-round-start` - passed
  - `scripts/smoke-package-workflow-tools` - passed
  - `scripts/check-private` - passed
  - `scripts/check-scripts` - passed
  - `git diff --check` - passed

### Slice 4 - Required Role Plan And Packet Wave Preparation

- Status: completed
- Proposed commit message: `feat(workflow): plan review role waves`
- Expected paths:
  - `scripts/prepare-review-round`
  - `scripts/BUILD`
  - `docs/workflow-command-surface.md`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/prepare_review_round.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/review_materiality.py`
  - `src/thesis_review_workflow/agent_coverage.py`
  - `src/thesis_review_workflow/review_packets.py`
  - `src/thesis_review_workflow/review_pipeline_orchestration.py`
  - `src/thesis_review_workflow/supervisor_packets.py`
  - `src/thesis_review_workflow/supervisor_report_packets.py`
  - `src/thesis_review_workflow/opponent_packets.py`
  - `tests/test_review_pipeline_orchestration.py`
  - `tests/test_supervisor_packets.py`
  - `tests/test_supervisor_report_packets.py`
  - `tests/test_opponent_packets.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-prepare-review-round`
- Tasks:
  - Generate `work/review_role_plan.json` after `review-round-start` and before
    semantic role agents are spawned.
  - Classify each role as `required_fresh`, `delta_review`,
    `reusable_current`, `blocked_with_typed_limitation`, or `not_material`.
    Reuse existing materiality, reuse-index, common-briefing, and claim-basis
    contracts; do not create a second role-activation model. The stored role-plan
    state must be a projection or crosswalk from existing materiality,
    agent-coverage, and reuse fields, with validator tests proving the mapping.
  - Base the role plan on current evidence, materiality, existing role outputs,
    reuse index, code/GitHub evidence, quantitative claims, visual/media
    evidence, Theses.cz similarity state, and final-output intent.
  - Prepare compact role packets from one stable common briefing plus
    role-specific deltas, output skeletons, validator commands, and full-artifact
    open triggers.
  - Include an explicit wave schedule that respects bounded agent concurrency
    from `docs/agent-scheduling.md`.
  - Add role-progress expectations that check durable artifacts or explicit
    blocker records, not chat-only activity. For media-heavy roles, generate a
    narrow recovery checklist that preserves the independent-review boundary.
  - Ensure text/assignment coverage, revision diff/history handling,
    figure/media, typography/formal, quantitative, code consistency, code
    quality, GitHub intake, literature/citation, and similarity roles have one
    explicit pre-synthesis state: scheduled, reused, blocked, or not material.
  - Preserve the code-bearing supervisor/opponent rule: when code evidence is
    present and the final artifact is supervisor feedback, supervisor report, or
    opponent materials, both code consistency and code quality must be
    scheduled, reused from current reviewed evidence, or blocked by a concrete
    typed limitation before synthesis.
  - Print materiality next actions with typed states such as `missing_artifact`,
    `invalid_artifact`, `present_but_not_synthesis_covered`, and
    `present_but_not_standalone_reviewed`.
  - Normalize advisory static-analysis outcomes into explicit states such as
    `available_with_findings`, `available_no_findings`,
    `unsupported_or_uninformative`, and `tool_unavailable`.
- Verification:
  - `pants fmt ::` - passed
  - `pants lint src/thesis_review_workflow:: tests:: scripts::` - passed
  - `pants check src/thesis_review_workflow:: tests:: scripts::` - passed
  - `pants test tests/test_review_pipeline_orchestration.py tests/test_supervisor_packets.py tests/test_supervisor_report_packets.py tests/test_opponent_packets.py tests/test_workflow_python_contracts.py` - passed
  - `pants test tests/test_work_artifacts.py` - passed
  - `scripts/smoke-review-round-start` - passed
  - `scripts/smoke-prepare-review-round` - passed
  - `scripts/smoke-supervisor-packets` - passed
  - `scripts/smoke-opponent-packets` - passed
  - `scripts/smoke-supervisor-report-packets` - passed
  - `scripts/smoke-package-workflow-tools` - passed
  - `scripts/check-private` - passed
  - `scripts/check-scripts` - passed
  - `git diff --check` - passed

### Slice 5 - Role Output Registration And Manifest Convergence

- Status: completed 2026-05-15
- Proposed commit message: `fix(workflow): register review role outputs`
- Expected paths:
  - `src/thesis_review_workflow/review_manifest.py`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `src/thesis_review_workflow/cli/register_review_artifact.py`
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `src/thesis_review_workflow/review_packets.py`
  - `src/thesis_review_workflow/review_pipeline_orchestration.py`
  - `src/thesis_review_workflow/review_profiles.py`
  - `src/thesis_review_workflow/structured_evidence.py`
  - `src/thesis_review_workflow/work_artifacts.py`
  - `scripts/smoke-register-review-artifact`
  - `tests/test_review_manifest_helpers.py`
  - `tests/test_review_pipeline_orchestration.py`
  - `tests/test_structured_evidence.py`
- Tasks:
  - Add presets or sidecar consumption for common review artifacts:
    `outputs/github_code_intake.md`, `outputs/code_consistency.md`,
    `outputs/code_quality_review.md`, `work/quantitative_claims.json`,
    `outputs/figure_media_review.md`, `outputs/typography_formal_review.md`,
    `outputs/literature_citation_review.md`,
    `outputs/theses_similarity_review.md`, supervisor-feedback drafts/finals,
    supervisor-report traces/drafts/reviewed reports, opponent-materials
    drafts/reviewed materials, opponent-report traces, and opponent-report
    review outputs.
  - Record generator role/agent, contribution, covered-by-synthesis target,
    `used_findings`, evidence hash, checks, and typed limitations without manual
    JSON edits.
  - Make common briefing and current evidence records refresh after late role
    artifacts are written, reusing the existing single-pass manifest ordering.
  - Prevent self-referential provenance loops: generated packets, common
    briefings, role plans, and traces may be listed as handoff context, but
    structured role evidence should cite primary case artifacts and stable notes
    as semantic `source_refs` unless the generated packet itself is the reviewed
    artifact.
  - Add a schema-level way to record expected future outputs in trace/manual-check
    records without requiring those files to exist before the draft/review step
    creates them, while keeping ordinary evidence refs strict and hash-bound.
  - Preserve independent-review boundaries: synthesis-covered internal evidence
    is not treated as standalone reviewed evidence unless separately reviewed.
  - Add regression tests that normal supported review profiles can run
    `init-review-manifest --run-checks`,
    `check-agent-coverage`, and
    `check-review-manifest --require-complete` without manual manifest surgery.
- Verification:
  - `pants fmt ::` - passed
  - `pants lint src/thesis_review_workflow:: tests::` - passed
  - `pants check src/thesis_review_workflow:: tests::` - passed
  - `pants test tests/test_review_manifest_helpers.py tests/test_review_pipeline_orchestration.py` - passed
  - `pants test tests/test_structured_evidence.py tests/test_work_artifacts.py tests/test_agent_coverage.py` - passed as additional focused coverage for expected-future refs, sidecar work artifacts, and role coverage records
  - `scripts/smoke-review-manifest` - passed
  - `scripts/smoke-register-review-artifact` - passed
  - `scripts/smoke-agent-coverage` - passed
  - `scripts/check-private` - passed
  - `scripts/check-scripts` - passed
  - `git diff --check` - passed

### Slice 6 - Profile Closeout Dispatcher

- Status: completed 2026-05-15
- Proposed commit message: `feat(workflow): close review rounds`
- Expected paths:
  - `scripts/review-round-closeout`
  - `scripts/BUILD`
  - `docs/workflow-command-surface.md`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/review_round_closeout.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/review_pipeline_orchestration.py`
  - `src/thesis_review_workflow/review_profiles.py`
  - `tests/test_review_pipeline_orchestration.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-opponent-closeout`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/smoke-review-round-closeout`
- Tasks:
  - Implement `scripts/review-round-closeout` from the Slice 1 profile registry.
    The dispatcher may delegate to existing `opponent-closeout` behavior for
    `opponent_review` and existing `supervisor-report-closeout` behavior for
    `supervisor_report`; it must not create competing profile-specific closeout
    policies.
  - For `supervisor_feedback`, this command satisfies the TODO-level supervisor
    closeout bundle superseded in Slice 1.
  - Run the required closeout sequence in one command, with profile-specific
    readiness, role-plan, wave, material-role, and output gates:
    `check-supervisor-ready`, `check-round-ready`, supervisor-report readiness
    or confirmation checks where applicable, `init-review-manifest --run-checks`,
    `check-review-wave`, `check-agent-coverage`,
    `check-review-manifest --require-complete`, `check-feedback-language`,
    `check-feedback-output`, `check-opponent-materials`,
    `check-opponent-report`, supervisor-report checks, `check-private`,
    `check-scripts`, and `git diff --check` according to profile.
  - Consume `work/review_role_plan.json` and fail if any role marked
    `required_fresh` or `delta_review` lacks a current output, selected
    validator/check result, reviewed reuse record, or typed limitation. This is
    where code consistency, code quality, quantitative, figure/media,
    typography/formal, literature/citation, Theses.cz similarity, revision diff,
    and text/assignment coverage obligations become closeout-visible.
  - Validate role-plan freshness against `work/review_run_trace.json`,
    manifest hashes, and final artifact approval records so regenerated packets
    or role outputs cannot silently leave closeout reading stale role states.
  - Print exact commands, pass/fail status, and the next missing action rather
    than raw logs.
  - Update run trace timings for closeout and final readiness.
  - Keep Omen and heavyweight developer hygiene advisory unless the operator is
    doing repo-tooling implementation work.
  - Wire the command through standard packaging and launcher coverage.
  - Update `docs/workflow-command-surface.md` and workflow command-contract tests
    for the generic command and any delegated profile commands.
- Verification:
  - `pants fmt ::` - passed
  - `pants lint src/thesis_review_workflow:: tests:: scripts::` - passed
  - `pants check src/thesis_review_workflow:: tests:: scripts::` - passed
  - `pants test tests/test_review_pipeline_orchestration.py tests/test_workflow_python_contracts.py` - passed
  - `scripts/smoke-review-round-closeout` - passed
  - `scripts/smoke-opponent-closeout` - passed
  - `scripts/smoke-supervisor-report` - passed
  - `scripts/smoke-package-workflow-tools` - passed
  - `scripts/check-private` - passed
  - `scripts/check-scripts` - passed
  - `git diff --check` - passed

### Slice 7 - Role-Plan Reuse Integration For Repeated Rounds

- Status: completed
- Proposed commit message: `feat(workflow): reuse review role plans`
- Expected paths:
  - `src/thesis_review_workflow/reuse.py`
  - `src/thesis_review_workflow/cli/update_round_reuse_index.py`
  - `src/thesis_review_workflow/review_materiality.py`
  - `src/thesis_review_workflow/agent_coverage.py`
  - `src/thesis_review_workflow/review_pipeline_orchestration.py`
  - `src/thesis_review_workflow/review_profiles.py`
  - `tests/test_reuse.py`
  - `tests/test_review_pipeline_orchestration.py`
- Tasks:
  - Connect `work/review_role_plan.json` to the existing reuse index and
    source-fingerprint model.
  - Allow the role plan to say "coverage required, satisfied by current reviewed
    evidence" or "delta review required" when current and prior source classes
    justify it.
  - Preserve hard fresh-review triggers for changed thesis sections, changed
    code/PR snapshots, changed quantitative evidence, new visual/media evidence,
    missing anchors, P0/P1 contradictions, reviewer challenge, or profile change
    that affects wording/report semantics.
  - Ensure reused evidence remains hash-bound and visibly tied to the final
    profile artifact that consumed it.
  - Keep cross-profile reuse conservative: a code-quality finding can be reused
    as evidence, but student-facing feedback, formal report wording, and
    opponent confidence labels still need profile-specific synthesis/review.
  - Treat existing `work/reuse/reuse_index.json` as the source of truth; do not
    introduce another reuse ledger.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_reuse.py tests/test_review_pipeline_orchestration.py`
  - `scripts/smoke-round-reuse-index`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 8 - Generic Operator Delta And Durable Lesson Promotion

- Status: pending
- Proposed commit message: `feat(workflow): handle reviewed artifact deltas`
- Expected paths:
  - `src/thesis_review_workflow/review_delta.py`
  - `src/thesis_review_workflow/cli/record_review_delta.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/amendments.py`
  - `src/thesis_review_workflow/supervisor_report.py`
  - `scripts/record-review-delta`
  - `scripts/BUILD`
  - `docs/workflow-command-surface.md`
  - `tests/test_review_delta.py`
  - `tests/test_report_amendments.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-record-review-delta`
- Tasks:
  - Add a structured `work/review_deltas/*.json` record for operator amendments
    and challenges after a reviewed artifact exists.
  - Classify each delta as `style_only`, `operator_preference`,
    `evidence_challenge`, `material_claim_delta`, or `general_workflow_lesson`.
  - Record previous/current artifact hashes, affected sections, evidence anchors
    to verify, whether profile-specific independent review is reopened, and what
    closeout gates must rerun.
  - For `general_workflow_lesson`, require a promotion target such as
    `AGENTS.md`, `.agents/skills/`, `README.md`, `TODO.md`, a tracked plan, or a
    private reviewer profile. Do not promote case-specific facts.
  - Generalize the existing supervisor-report amendment contract instead of
    creating a parallel report-amendment path. `record-report-amendment` may
    remain only as a thin profile-specific wrapper around the shared delta
    validator; the canonical new record shape lives under
    `work/review_deltas/*.json`.
  - Wire `record-review-delta` through `src/thesis_review_workflow/commands.py`,
    `scripts/BUILD`, PEX packaging, generated `.cmd`/`.ps1` launchers, command
    surface docs, and command-contract tests. `record-report-amendment` must
    delegate to the shared implementation or be explicitly retired in this slice.
  - Add tests that material deltas stale the prior approval, style/preference
    deltas still require an approval record or explicit typed exception, and
    closeout reports the exact next action rather than passing silently.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_review_delta.py tests/test_report_amendments.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-record-review-delta`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 9 - Documentation, Skills, TODO Reconciliation, And Archive

- Status: pending
- Proposed commit message: `docs(workflow): document optimized review pipeline`
- Expected paths:
  - `README.md`
  - `docs/agent-scheduling.md`
  - `docs/opponent-review-workflow.md`
  - `.agents/skills/thesis-supervisor-feedback/SKILL.md`
  - `.agents/skills/thesis-supervisor-feedback-review/SKILL.md`
  - `.agents/skills/thesis-supervisor-report/SKILL.md`
  - `.agents/skills/thesis-supervisor-report-review/SKILL.md`
  - `.agents/skills/thesis-opponent-materials/SKILL.md`
  - `.agents/skills/thesis-opponent-materials-review/SKILL.md`
  - `.agents/skills/thesis-opponent-report-review/SKILL.md`
  - `.agents/skills/thesis-github-code-intake/SKILL.md`
  - `.agents/skills/thesis-code-consistency/SKILL.md`
  - `.agents/skills/thesis-code-quality-review/SKILL.md`
  - `.agents/skills/thesis-figure-media-review/SKILL.md`
  - `.agents/skills/thesis-quantitative-claims-review/SKILL.md`
  - `.agents/skills/thesis-literature-citation-review/SKILL.md`
  - `.agents/skills/thesis-typography-formal-review/SKILL.md`
  - `.agents/skills/thesis-theses-similarity-review/SKILL.md`
  - `TODO.md`
  - `plans/review_pipeline_optimization_plan.md`
  - `plans/archive/review_pipeline_optimization_plan.md`
- Tasks:
  - Keep `README.md` chat-first: show what an operator asks the agent to do, and
    keep script details as lower-level reference.
  - Update supervisor and opponent skills so parent agents use the profile
    round-start role plan, artifact registration path, and operator-delta path by
    default.
  - Document the bounded-wave schedule, required role-plan states, and what is
    shared versus profile-specific.
  - Document that `review-round-start`/`review-round-closeout` are the generic
    orchestration commands, while existing profile-specific commands remain
    lower-level or delegated surfaces only where Slice 1 kept them.
  - Reconcile TODO only for work actually completed by this plan.
  - Record final audit commands, residual risks, achieved timing evidence, and
    archive the plan.
  - Run developer-hygiene checks as advisory repo-tooling evidence, not as
    thesis case-pipeline gates. If Omen is unavailable locally, record that
    limitation rather than blocking case workflow correctness.
- Verification:
  - `pants fmt ::`
  - `pants lint ::`
  - `pants check ::`
  - `pants test tests::`
  - `pants run :vulture`
  - `pants run :jscpd`
  - `pants run :omen` (advisory; record local-tool limitation if unavailable)
  - `scripts/smoke-review-round-start`
  - `scripts/smoke-prepare-review-round`
  - `scripts/smoke-review-round-closeout`
  - `scripts/smoke-record-review-delta`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git status --short --untracked-files=all`
  - `git diff --check`

## Progress

- 2026-05-15: Plan created from a case-neutral post-run pipeline review. No
  implementation has started.
- 2026-05-15: Generalized from a supervisor-feedback-only optimization plan to a
  shared review-pipeline plan with supervisor feedback as the first timing pilot.
  Added profile matrix, operator-delta, cross-profile role planning, closeout,
  reuse, and durable lesson-promotion scope.
- 2026-05-15: Added case-neutral lessons from an opponent-materials run:
  parent-container submission bundles need typed import classification,
  multiline bootstrap text needs newline normalization or file inputs,
  long-running role agents need artifact-progress/recovery expectations, and
  advisory static-analysis zero-result states need explicit limitation labels.
- 2026-05-15: Added a closeout provenance lesson from the same run: current
  evidence snapshots should not default to self-updating closeout artifacts such
  as review manifests and agent coverage, because that can create stale-hash
  cycles during manifest completeness validation.
- 2026-05-15: Hardened for autonomous execution. Removed the open-ended
  pre-implementation review slice, split round-start planning from command
  wiring, made `review-round-start` and `review-round-closeout` the shared
  command owners, mapped `opponent_materials` to canonical profile
  `opponent_review`, and narrowed reuse/operator-delta slices to extend current
  contracts instead of reimplementing them.
- 2026-05-15: Multi-agent plan review found remaining execution-contract gaps.
  Patched the plan to use a deterministic two-command start boundary
  (`review-round-start` then `prepare-review-round`), separate workflow profiles
  from Codex agent role profiles, canonicalize supervisor-feedback approval
  naming, include supervisor-report closeout delegation, require role-plan-driven
  material-role validators in closeout, add command-surface coverage for
  `record-review-delta`, and add final developer-hygiene evidence.
- 2026-05-15: Slice 1 completed. Added the workflow-profile registry and
  review-run trace schema, registered trace validation as a case-private work
  artifact, canonicalized supervisor-feedback approvals to
  `work/reviews/supervisor_feedback_review.json` across active code, tests,
  smokes, docs, skills, and TODO, and marked the older supervisor-only closeout
  plan superseded. Verification passed: `pants fmt ::`,
  `pants lint src/thesis_review_workflow:: tests::`,
  `pants check src/thesis_review_workflow:: tests::`,
  `pants test tests/test_agent_profile_contracts.py tests/test_review_approvals.py tests/test_review_wave_gate.py tests/test_review_pipeline_orchestration.py tests/test_work_artifacts.py`,
  `scripts/smoke-review-approval`, `scripts/smoke-review-manifest`,
  `scripts/smoke-review-wave`, `scripts/check-private`, `scripts/check-scripts`,
  and `git diff --check`.
  Residual risks: archived historical plans still mention the old approval name
  as history; generic round-start and closeout commands are not implemented
  until later slices.
- 2026-05-15: Slice 2 completed. Added the pure round-start planner with
  explicit material descriptors, fresh/current/stale/provisional-stale handling,
  profile readiness-gate selection, supervisor-report note planning,
  container/reference bundle classification, code-workspace/GitHub/current
  evidence/reuse/role-plan action planning, and literal escaped-newline
  diagnostics. Verification passed: `pants fmt ::`,
  `pants lint src/thesis_review_workflow:: tests::`,
  `pants check src/thesis_review_workflow:: tests::`,
  `pants test tests/test_review_pipeline_orchestration.py`,
  `scripts/check-private`, `scripts/check-scripts`, and `git diff --check`.
  Residual risks: the planner is intentionally pure and does not write
  `work/review_run_trace.json` or perform imports until Slice 3 exposes the CLI.
- 2026-05-15: Slice 3 completed. Added `review-round-start` as the shared
  deterministic round-start command, wired it through the logical command map,
  POSIX wrapper, Pants PEX target, packaged launcher contract, smoke coverage,
  and workflow command docs. The command accepts explicit workflow profiles and
  material descriptors, normalizes metadata-file/literal-newline inputs through
  the Slice 2 planner, writes `work/review_run_trace.json`, can execute the
  existing extract/GitHub/code-workspace/current-evidence/reuse/readiness helper
  steps, and records `prepare-review-round` only as the next planned boundary
  without writing `work/review_role_plan.json`. Verification passed:
  `pants fmt ::`,
  `pants lint src/thesis_review_workflow:: tests:: scripts::`,
  `pants check src/thesis_review_workflow:: tests:: scripts::`,
  `pants test tests/test_review_pipeline_orchestration.py tests/test_workflow_python_contracts.py`,
  `scripts/smoke-review-round-start`, `scripts/smoke-package-workflow-tools`,
  `scripts/check-private`, `scripts/check-scripts`, and `git diff --check`.
  Subagent patch review found that raw invalid material paths could leak into
  trace blocker notes; this was fixed by recording trace-safe typed blocker
  codes while keeping input-specific diagnostics on stderr.
  Residual risks: `review-round-start --dry-run` is only a deterministic preview
  for smoke/contract validation; actual role-plan writing remains intentionally
  deferred to Slice 4 through `prepare-review-round`.
- 2026-05-15: Slice 4 completed. Added `prepare-review-round` as the separate
  deterministic packet/role-plan boundary, delegating packet emission to the
  existing supervisor-feedback, supervisor-report, and opponent packet commands
  before writing `work/review_role_plan.json`. The role plan records workflow
  and materiality profiles, packet refs, source contracts, projected role
  states, bounded waves with max concurrency 2, role-progress artifact states,
  reuse-index and agent-coverage crosswalks, typed materiality next-action
  states, advisory Omen availability, and the code-bearing contract requiring
  both code consistency and code quality to be scheduled, reused, or covered by
  a typed limitation when code evidence is present. Verification passed:
  `pants fmt ::`,
  `pants lint src/thesis_review_workflow:: tests:: scripts::`,
  `pants check src/thesis_review_workflow:: tests:: scripts::`,
  `pants test tests/test_review_pipeline_orchestration.py tests/test_supervisor_packets.py tests/test_supervisor_report_packets.py tests/test_opponent_packets.py tests/test_workflow_python_contracts.py`,
  `pants test tests/test_work_artifacts.py`, `scripts/smoke-review-round-start`,
  `scripts/smoke-prepare-review-round`, `scripts/smoke-supervisor-packets`,
  `scripts/smoke-opponent-packets`, `scripts/smoke-supervisor-report-packets`,
  `scripts/smoke-package-workflow-tools`, `scripts/check-private`,
  `scripts/check-scripts`, and `git diff --check`. Subagent review findings were
  folded into the slice: the implementation delegates to existing packet
  generators instead of reimplementing activation, and the initially considered
  second limitation input surface was removed so typed limitations remain owned
  by existing manifest/materiality/agent-coverage records.
  Residual risks: role agents are still spawned by the parent agent, not by the
  deterministic command; manifest convergence for role outputs and closeout
  consumption of the role plan remain intentionally deferred to Slices 5 and 6.
- 2026-05-15: Slice 5 completed. Added manifest-sidecar consumption for
  `work/review_artifacts/*.json`, shared registration defaults for output and
  work role artifacts, `handoff_refs` for packets/common briefings/run
  traces/role plans, and richer work-artifact registration metadata for
  generator role, agent, contribution, covered-by-synthesis target,
  independent-review status, checks, limitations, and source hashes. Updated
  `register-review-artifact`, `init-review-manifest`, manifest validation,
  role-plan records, and smoke coverage so generated packet context is no
  longer treated as semantic evidence or included in `source_sha256`. Structured
  evidence now allows typed `expected_future_refs` without weakening ordinary
  evidence-ref existence checks, and current-evidence defaults no longer include
  self-updating closeout artifacts such as the manifest and agent coverage.
  Verification passed: `pants fmt ::`,
  `pants lint src/thesis_review_workflow:: tests::`,
  `pants check src/thesis_review_workflow:: tests::`,
  `pants test tests/test_review_manifest_helpers.py tests/test_review_pipeline_orchestration.py tests/test_structured_evidence.py tests/test_work_artifacts.py tests/test_agent_coverage.py`,
  `scripts/smoke-review-manifest`, `scripts/smoke-register-review-artifact`,
  `scripts/smoke-agent-coverage`, `scripts/check-private`,
  `scripts/check-scripts`, and `git diff --check`. Subagent review findings
  were folded into the slice: sidecars use shared registration defaults, role
  plans record canonical coverage roles and registration presets, packet/common
  briefing dependencies are modeled as handoffs, and final/synthesis `feeds`
  remain review-coverage metadata rather than hash-bound semantic sources.
  Residual risks: late role outputs can now register cleanly, but a single
  closeout command that refreshes role plan, manifest, coverage, and profile
  gates in the exact final order is still deferred to Slice 6.
- 2026-05-15: Slice 6 completed. Added the shared `review-round-closeout`
  command with POSIX wrapper, Python CLI, command map entry, Pants PEX target,
  generated-launcher contract coverage, command-surface docs, and synthetic
  smoke coverage. The dispatcher resolves workflow profiles from explicit input
  or private role/trace artifacts, runs profile readiness gates, refreshes
  manifest/materiality/coverage, validates `work/review_role_plan.json` before
  relying on scheduled roles, runs the final review wave for generic profiles,
  delegates supervisor-report and opponent-materials profile-specific checks to
  existing closeout commands, records closeout trace events, and reruns manifest
  completeness after trace updates. Subagent review findings were folded into
  the slice: required/delta role-plan states now require a registered
  manifest/agent-coverage-backed output or concrete typed limitation rather
  than raw file presence; trace appends reject case/round/profile mismatches;
  and closeout no longer writes a `passed` trace event before the first final
  post-trace manifest gates run. Verification passed: `pants fmt ::`,
  `pants lint src/thesis_review_workflow:: tests:: scripts::`,
  `pants check src/thesis_review_workflow:: tests:: scripts::`,
  `pants test tests/test_review_pipeline_orchestration.py tests/test_workflow_python_contracts.py`,
  `scripts/smoke-review-round-closeout`, `scripts/smoke-opponent-closeout`,
  `scripts/smoke-supervisor-report`, `scripts/smoke-package-workflow-tools`,
  `scripts/check-private`, `scripts/check-scripts`, and `git diff --check`.
  Residual risks: closeout still relies on parent-agent orchestration for actual
  role-agent execution; repeated-round reuse semantics and operator-delta
  reopening remain deferred to Slices 7 and 8.
- 2026-05-15: Slice 7 completed. Added a single reusable role-plan mapping from
  workflow roles to hash-bound artifact roles, extended `work/review_role_plan.json`
  reuse projections beyond code roles, and kept final synthesis/trace/review
  roles unmapped so profile-specific wording and confidence calibration still
  require their own workflow review. `work/reuse/reuse_index.json` remains the
  source of truth for source-fingerprint comparison and delta decisions, while
  `reusable_current` role-plan states now require current
  `work/agent_coverage.json` coverage satisfied by `current_reviewed_artifact`
  instead of trusting raw reuse-index data alone. Agent coverage validation uses
  the same mapping, so non-fresh coverage remains tied to reuse-index schema,
  current source hashes, and reviewed evidence; opponent `text_structure_assignment`
  maps to the assignment evidence contract. Verification passed: `pants fmt ::`,
  `pants lint src/thesis_review_workflow:: tests::`,
  `pants check src/thesis_review_workflow:: tests::`,
  `pants test tests/test_reuse.py tests/test_review_pipeline_orchestration.py`,
  additional regression coverage via
  `pants test tests/test_agent_coverage.py tests/test_workflow_python_contracts.py`,
  `scripts/smoke-round-reuse-index`, `scripts/check-private`,
  `scripts/check-scripts`, and `git diff --check`. Subagent review findings
  were folded into the slice: raw reuse-index `unchanged_reusable` no longer
  skips scheduling without agent coverage, and the opponent assignment role is
  included in the conservative evidence-role mapping.
  Residual risks: role-plan reuse still depends on `update-round-reuse-index`
  and manifest/coverage refreshes having run before planning; operator-delta
  reopening of previously reviewed artifacts remains deferred to Slice 8.

## Decision Log

- 2026-05-15: Keep this as an orchestration and provenance plan, not a semantic
  policy rewrite. The workflow should remain evidence-backed and role-split.
- 2026-05-15: Do not promise fully automated subagent execution from shell
  scripts. The practical command surface prepares materials, role plans,
  packets, sidecars, traces, and closeout; the parent agent remains responsible
  for semantic orchestration unless a stable non-interactive agent API is added
  later.
- 2026-05-15: Supersede `plans/supervisor_workflow_closeout_plan.md` with the
  shared `review-round-start` and `review-round-closeout` command surface.
  Consume `plans/token_efficiency_reuse_plan.md` as already-implemented
  dependency contracts, not as competing work to reimplement.
- 2026-05-15: Do not keep the plan scoped only to supervisor feedback. The
  observed friction is mostly shared across supervisor feedback, supervisor
  reports, opponent materials, and opponent-report review. Profile-specific
  final artifacts, tone, readiness gates, and review approval records remain
  typed adapters over a shared orchestration layer.
- 2026-05-15: Treat post-review operator corrections as first-class deltas. A
  correction may be case-specific, a durable reviewer preference, a material
  evidence challenge, or a general workflow lesson; each category needs a clear
  review/re-closeout path.
- 2026-05-15: Choose `work/reviews/supervisor_feedback_review.json` as the
  canonical supervisor-feedback approval record for the new optimized pipeline.
  Remove the previous feedback-student-named contract in Slice 1 rather than
  preserving it as an alias.
- 2026-05-15: Keep `review-round-start` and `prepare-review-round` separate
  deterministic commands. The start command imports, refreshes, gates, traces,
  and points to the next action; the prepare command writes the role plan,
  packets, wave schedule, and role-progress expectations.

## Final Audit

- 2026-05-15 multi-agent plan review: two read-only agents reviewed the plan.
  Findings were folded directly into this file rather than left as external
  commentary.
- `scripts/check-private`: passed.
- `scripts/check-scripts`: passed.
- `git diff --check`: passed for tracked changes in the dirty worktree.
- `git diff --no-index --check /dev/null plans/review_pipeline_optimization_plan.md`:
  passed for this currently untracked plan file.
- Residual risk: the plan intentionally changes the supervisor-feedback approval
  record contract to `work/reviews/supervisor_feedback_review.json`; Slice 1 must
  update all existing feedback-student-named approval references atomically and
  without compatibility aliases.
- Archive decision: keep active under `plans/` until Slice 9 completes.
