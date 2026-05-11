# Review Context Follow-Up Plan

Status: completed
Created: 2026-05-11

## Goal

Remove the remaining high-friction context-efficiency gaps left after
`plans/archive/review_context_efficiency_plan.md`: drift-prone evidence should
have a deterministic snapshot authoring path, materiality decisions should lead
to concrete next actions, final-review approval records should not require
hand-written JSON, and quantitative claims should have a dedicated review
contract.

## Audit Base

The completed context-efficiency plan added synthesis handoffs, wave gates,
supervisor/opponent packets, materiality decisions, and structured approval
records. The final audit with agents found these remaining gaps:

- `work/current_evidence_snapshot.json` is validated and included in packets,
  but no command creates or refreshes it. Agents must still manually reconstruct
  drift-prone GitHub, external-link, late-note, report-trace, and reviewed-output
  freshness context.
- `scripts/check-review-materiality` can mark `github_intake` and
  `quantitative_claims` as material, but packet generation currently routes only
  figure/media, typography/formal, and literature optional packets.
- Final wave gates and closeout require `work/reviews/*_review.json`, but review
  agents or the main session still have to author that JSON manually.
- `work/quantitative_claims.json` is referenced by supervisor/opponent skills
  and validated by `scripts/check-evaluation-claims`, but there is no dedicated
  skill/template that tells a quantitative reviewer how to produce it.
- Output artifact metadata is duplicated between manifest helpers and already
  shows drift as new artifact types are added.
- Supervisor preflight/closeout remains the largest repeated-command gap, but
  it already has its own tracked plan:
  `plans/supervisor_workflow_closeout_plan.md`.
- Rich video/demo/media evidence intake remains valuable, but it is broader than
  this follow-up and stays in TODO unless the user asks to prioritize it.

## Scope

In scope:

- add a deterministic helper to create or refresh
  `work/current_evidence_snapshot.json` from structured, hash-bound inputs;
- make packet preparation and/or preflight surface concrete next actions when
  materiality says GitHub intake or quantitative claims are material;
- add a small review-approval authoring helper that writes
  `work/reviews/*_review.json` from round-relative artifact and review-basis
  paths;
- add a dedicated quantitative-claims skill/template for
  `work/quantitative_claims.json`;
- centralize output artifact metadata before adding more helper behavior;
- keep all generated artifacts under ignored round workspaces.

Out of scope:

- implementing `scripts/supervisor-preflight` or `scripts/supervisor-closeout`;
- deep video/demo inspection, thumbnails, codecs, or content review;
- running submitted student code;
- weakening role coverage, independent review, or DEEP-mode requirements;
- adding fallback compatibility for older `~/code/diplomky` workflows.

## Design Constraints

- Deterministic helpers must consume structured metadata, paths, manifests,
  hashes, validator outputs, and explicit operator/agent-authored artifacts.
  They must not infer semantic meaning from raw thesis, README, code, or note
  substrings.
- Snapshot and approval helpers should be Windows-aware Python CLI surfaces with
  packaged launchers, not POSIX-only scripts.
- New operator commands must satisfy the full workflow command surface:
  `WORKFLOW_COMMAND_MODULES`, `src/thesis_review_workflow/cli/BUILD`,
  `scripts/BUILD` runtime deps, `pex_binary(tags=["workflow-tool"])`, POSIX
  wrappers, and packaged `.cmd`/`.ps1` launchers.
- README edits must keep the top path chat-first. New helper commands belong
  under diagnostics, helper reference, or under-the-hood sections, not as the
  primary supervisor/opponent prompt path.
- Approval helper output is a provenance convenience, not a substitute for the
  independent reviewer actually reading the artifact.
- Materiality remains advisory for optional roles. A materiality decision may
  activate packets or next-action prompts; it must not become a semantic verdict.
- Omen remains developer/reviewer evidence for code-quality review, not an
  operator closeout prerequisite.

## Slices

### Slice 1 - Plan Review And Artifact Registry Audit

- Status: done
- Proposed commit message: `docs(workflow): plan review context follow-up`
- Expected paths:
  - `plans/review_context_followup_plan.md`
  - `TODO.md`
  - `src/thesis_review_workflow/artifact_registry.py`
  - `src/thesis_review_workflow/review_manifest.py`
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `src/thesis_review_workflow/case_doctor_summary.py`
  - `tests/test_review_manifest_helpers.py`
  - `tests/test_workflow_python_contracts.py`
- Tasks:
  - Review this plan with agents before implementation.
  - Create a shared output-artifact registry before adding more artifact types.
  - Make manifest initialization, incremental registration, manifest closeout,
    and case-doctor output summaries consume the shared registry.
  - Preserve current special cases: synthesis-covered internal evidence,
    calibrated internal evidence requiring independent review, final/sendable
    scopes, demo artifact review, and PR contribution review.
  - Add contract tests proving output types, scopes, skills, labels, and
    independent-review requirements are single-sourced.
  - Keep the existing supervisor closeout plan as the command-bundle owner.
- Verification:
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 2 - Current Evidence Snapshot Authoring

- Status: done
- Proposed commit message: `feat(workflow): add current evidence snapshot helper`
- Expected paths:
  - `src/thesis_review_workflow/structured_evidence.py`
  - `src/thesis_review_workflow/cli/update_current_evidence_snapshot.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `scripts/update-current-evidence-snapshot`
  - `scripts/BUILD`
  - `tests/test_structured_evidence.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-current-evidence-snapshot`
- Tasks:
  - Add a helper that writes `work/current_evidence_snapshot.json` from explicit
    round-relative file source refs and known structured inputs such as GitHub
    intake outputs, late notes, existing reviewed outputs, report trace, and
    approval records.
  - Hash-bind every file source ref and reject unsafe paths. Directory evidence
    must either expand to bounded per-file entries or use an explicit tree-hash
    schema added to the validator in this slice.
  - Recompute hashes/status for all known refs on every write. Preserve operator
    annotations and limitations, not stale `present` hashes. Changed files must
    become current with a new hash; missing files must become `missing`/`invalid`
    with the previous hash removed or moved to explicit notes.
  - Never semantically summarize free-form late notes; include only
    round-relative path, hash, status, freshness, and explicit operator/agent
    limitations.
  - Package the command for POSIX and generated Windows launchers.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_structured_evidence.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-current-evidence-snapshot`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 3 - Materiality To Action Bridge

- Status: done
- Proposed commit message: `feat(workflow): route materiality next actions`
- Expected paths:
  - `src/thesis_review_workflow/review_materiality.py`
  - `src/thesis_review_workflow/supervisor_packets.py`
  - `src/thesis_review_workflow/opponent_packets.py`
  - `src/thesis_review_workflow/review_packets.py`
  - `.agents/skills/thesis-supervisor-feedback/SKILL.md`
  - `.agents/skills/thesis-opponent-materials/SKILL.md`
  - `README.md`
  - `tests/test_review_materiality.py`
  - `tests/test_supervisor_packets.py`
  - `tests/test_opponent_packets.py`
- Tasks:
  - Add a durable materiality next-action contract, either as
    `work/review_materiality/next_actions.json` or as `next_actions[]` inside
    `work/review_materiality/index.json`.
  - Each next action must record role, workflow profile, required artifact path,
    source refs and hashes, missing/stale reason, command or skill to run,
    severity, and any typed limitation that resolves the action without the
    artifact.
  - Make `github_intake` materiality surface a concrete next action when GitHub
    evidence exists but `outputs/github_code_intake.md` is missing or stale by
    a validator-backed source-hash check.
  - Make `quantitative_claims` materiality surface a concrete next action when
    quantitative review is material but `work/quantitative_claims.json` is
    missing or stale.
  - Render unresolved next actions in supervisor and opponent packets.
  - Refuse final/synthesis wave readiness for unresolved material
    GitHub/quantitative actions unless a current artifact or typed limitation is
    recorded.
  - Decide whether these roles need generated packets or clearer packet-prep
    warnings; avoid optional packet sprawl if a next-action diagnostic is
    cleaner.
  - Document `scripts/check-review-materiality` in the operator and skill path
    without making it a semantic routing engine.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_review_materiality.py tests/test_supervisor_packets.py tests/test_opponent_packets.py`
  - `scripts/smoke-supervisor-packets`
  - `scripts/smoke-opponent-packets`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 4 - Review Approval Authoring Helper

- Status: done
- Proposed commit message: `feat(workflow): add review approval writer`
- Expected paths:
  - `src/thesis_review_workflow/review_approvals.py`
  - `src/thesis_review_workflow/cli/write_review_approval.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `scripts/write-review-approval`
  - `scripts/BUILD`
  - `tests/test_review_manifest_helpers.py`
  - `tests/test_review_wave_gate.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-review-approval`
- Tasks:
  - Add a helper that writes `work/reviews/<name>_review.json` for a reviewed
    artifact and exact review basis.
  - Support canonical pass-only profiles for supervisor feedback, opponent
    materials, and opponent report review, plus an explicit custom mode for
    standalone final evidence.
  - Hard-code canonical reviewed-artifact and review-basis paths/checks:
    supervisor `outputs/feedback_student.md` from
    `work/feedback_student_draft.md`; opponent materials
    `outputs/oponent_podklady_revidovane.md` from
    `work/oponent_podklady_draft.md` or `outputs/oponent_podklady.md`;
    opponent report review from the exact human/report draft used as basis.
  - Require reviewer role, reviewer agent or human identifier, verdict,
    blocking finding count, observed checks, limitations, and timestamp.
  - Include `schema_version`, `case_id`, and `round_id` in the written record.
  - Reject pass records with non-zero blocking findings; failed reviews should
    remain draft/review findings, not approval JSON.
  - Refuse approval if required observed checks are absent or stale when those
    check records exist, and refuse reviewer identity that matches the recorded
    generator identity for final/sendable artifacts.
  - Validate the written record immediately with the existing approval validator.
  - Smoke-test that `init-review-manifest` imports the record and registers it
    as supporting work.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_review_manifest_helpers.py tests/test_review_wave_gate.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-review-approval`
  - `scripts/smoke-review-wave`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 5 - Quantitative Claims Review Contract

- Status: done
- Proposed commit message: `docs(workflow): add quantitative claims review contract`
- Expected paths:
  - `.agents/skills/thesis-quantitative-claims-review/SKILL.md`
  - `.codex/agents/thesis-quantitative-claims-reviewer.toml`
  - `.codex/config.toml`
  - `BUILD`
  - `AGENTS.md`
  - `docs/agent-scheduling.md`
  - `.agents/skills/thesis-supervisor-feedback/SKILL.md`
  - `.agents/skills/thesis-opponent-materials/SKILL.md`
  - `README.md`
  - `src/thesis_review_workflow/agent_coverage.py`
  - `src/thesis_review_workflow/supervisor_packets.py`
  - `src/thesis_review_workflow/opponent_packets.py`
  - `src/thesis_review_workflow/review_packets.py`
  - `src/thesis_review_workflow/cli/check_evaluation_claims.py`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `src/thesis_review_workflow/work_artifacts.py`
  - `tests/test_structured_evidence.py`
  - `tests/test_evaluation_claims_helpers.py`
  - `tests/test_supervisor_packets.py`
  - `tests/test_opponent_packets.py`
  - `tests/test_review_manifest_helpers.py`
  - `tests/test_work_artifacts.py`
  - `tests/test_workflow_python_contracts.py`
  - `tests/BUILD`
- Tasks:
  - Add a repo-local skill or template that tells a quantitative reviewer how to
    author `work/quantitative_claims.json`.
  - Keep the review semantic and evidence-bound: units, scale, baseline,
    sample size, practical magnitude, reproducibility, and overclaim risk.
  - Require `gpt-5.5`/`xhigh` for the semantic quantitative reviewer.
  - Add the skill to repo skill routing and wave/agent scheduling guidance.
  - Ensure synthesis packets consume the compact quantitative handoff rather
    than rereading full result sections.
  - Make `work/quantitative_claims.json` required when quantitative materiality
    feeds a final/synthesis artifact unless a typed limitation resolves the
    next action.
  - Avoid making deterministic checks infer metric meaning from raw text.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_structured_evidence.py`
  - `pants test tests/test_evaluation_claims_helpers.py tests/test_supervisor_packets.py tests/test_opponent_packets.py`
  - `scripts/smoke-evaluation-claims`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 6 - Documentation, TODO Reconciliation, And Archive

- Status: done
- Proposed commit message: `docs(workflow): close review context follow-up`
- Expected paths:
  - `README.md`
  - `TODO.md`
  - `docs/agent-scheduling.md`
  - `docs/opponent-review-workflow.md`
  - `plans/review_context_followup_plan.md`
  - `plans/archive/review_context_followup_plan.md`
- Tasks:
  - Keep README chat-first; document new helpers only as operator-visible
    diagnostics or closeout conveniences.
  - Reconcile TODO by removing or narrowing items completed by this plan.
  - Run final hygiene and Omen.
  - Archive the plan after final audit.
- Verification:
  - `pants fmt ::`
  - `pants lint ::`
  - `pants check ::`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `pants run :omen`
  - `git diff --check`
  - `git status --short --untracked-files=all`

## Progress

- 2026-05-11: Created after completing and auditing
  `plans/archive/review_context_efficiency_plan.md`. Two audit agents and local review
  agreed that the largest remaining context-efficiency gaps are current-evidence
  snapshot authoring, materiality-to-action routing, manual approval-record
  authoring, quantitative-claims review authoring, and duplicated output
  artifact metadata.
- 2026-05-11: Started execution. Initial agent review found blockers in
  artifact registry centralization, command-surface coverage, materiality
  next-action durability, quantitative role routing, approval helper boundaries,
  snapshot refresh semantics, README placement, and missing plan closeout
  sections. Slice 1 is in progress.
- 2026-05-11: Slice 1 centralized output artifact metadata in
  `src/thesis_review_workflow/artifact_registry.py`, wired manifest
  initialization, incremental registration, manifest closeout, case-doctor
  summaries, and agent-coverage final-output sets to the registry, and added
  registry contract tests. Slice review found missing closeout metadata
  validation and missed coverage consumers; both were fixed.
- 2026-05-11: Slice 2 added `scripts/update-current-evidence-snapshot` with
  full workflow command/PEX coverage. The helper writes and validates
  `work/current_evidence_snapshot.json`, recomputes hashes on every run,
  preserves explicit annotations, carries deleted tracked refs as `missing`,
  records directory refs as `invalid` without hashing them, and rejects unsafe
  refs before reading. Slice review found dropped deleted refs, stale negative
  statuses, and unsafe builder hashing; all were fixed.
- 2026-05-11: Slice 3 added materiality `next_actions` into
  `work/review_materiality/index.json`, renders unresolved GitHub/quantitative
  actions in supervisor/opponent packets, and blocks synthesis/final waves when
  a mapped workflow lacks a current materiality index or has unresolved required
  actions. Slice review found stale stored next actions, weak source-freshness
  handling, missing-index bypass, hard routing from raw GitHub URLs in notes,
  and weak typed limitations; the implementation now re-evaluates actions from
  current artifacts/limitations, hash-binds decision sources, ignores raw note
  URLs for hard materiality, validates current snapshots when present, and
  requires a typed materiality limitation contract.
- 2026-05-11: Slice 4 added `scripts/write-review-approval`, full command/PEX
  routing, approval schema helpers, canonical pass-only profiles, tests, and a
  smoke that verifies `init-review-manifest` imports the record as supporting
  work. Slice review found self-certified required checks, drift from manifest
  check requirements, overridable canonical reviewer roles, and weak manifest
  import validation; the writer now requires manifest-backed passed helper
  checks with current target hashes, rejects canonical role overrides, and
  manifest import uses the stricter manifest-aware approval validator.
- 2026-05-11: Slice 5 added the `thesis-quantitative-claims-review` skill and
  `thesis_quantitative_claims_reviewer` profile pinned to `gpt-5.5`/`xhigh`,
  expanded the quantitative JSON schema to require unit, scale/sample context,
  practical magnitude, overclaim risk, baseline, practical context,
  reproducibility refs, and evidence anchors, and added compact quantitative
  handoff rendering to supervisor/opponent packets. Agent review found missing
  Codex profile registration, circular first-authoring packet activation, weak
  schema enforcement, human-producer coverage failure, and missing
  `check-evaluation-claims` manifest closeout coverage. The fixes register the
  profile, activate the quantitative packet from materiality next actions as
  well as existing artifacts, support human-produced handoffs in agent coverage,
  require `check-evaluation-claims` when `work/quantitative_claims.json` is
  recorded, and add Pants sandbox resources for `.codex` profile contract
  tests.

## Decision Log

- 2026-05-11: Do not create a second supervisor closeout plan. Execute
  `plans/supervisor_workflow_closeout_plan.md` for supervisor preflight/closeout
  commands.
- 2026-05-11: Keep video/demo deep media intake in TODO for now. It is
  important, but broader than this follow-up's context-friction scope.
- 2026-05-11: Treat approval-record writing as a convenience around an actual
  independent review, not as proof that a review happened.
- 2026-05-11: Artifact metadata centralization is mandatory in Slice 1 because
  output artifact metadata already drifted between manifest initialization,
  incremental registration, manifest closeout, and case-doctor summaries.
- 2026-05-11: Snapshot helpers must recompute current hashes on every write and
  preserve annotations only; stale `present` hashes are invalid by the existing
  validator.
- 2026-05-11: Materiality will use next-action diagnostics instead of adding
  GitHub and quantitative packet files by default.
- 2026-05-11: Approval records remain pass-only provenance records. Failed
  reviews stay as draft/review findings unless the schema is intentionally
  widened later.
- 2026-05-11: README helper documentation must stay below the chat-first quick
  path.
- 2026-05-11: Quantitative first authoring is driven by materiality
  `next_actions` plus the quantitative skill, not by deterministic prose scans.
  Once `work/quantitative_claims.json` exists, synthesis packets consume the
  compact structured handoff first.
- 2026-05-11: Slice 6 removed the completed follow-up item from `TODO.md`,
  documented `work/quantitative_claims.json` in the opponent workflow, ran final
  hygiene and Omen, and archived this completed plan.

## Risks

- A current-evidence snapshot can become a stale confidence source if the helper
  preserves entries too aggressively.
- Materiality next-action routing can accidentally become semantic inference if
  it reads raw thesis text instead of structured inputs.
- A review-approval writer can be misused as a rubber stamp unless it requires
  explicit reviewer identity, basis path, checks observed, limitations, and
  immediate validation.
- Quantitative review can overstate precision if the template encourages
  point-estimates instead of unit/baseline/reproducibility sanity checks.
- Centralizing output artifact metadata can create a large refactor; keep it
  small unless duplication blocks the helper implementation.

## Final Audit

Completed on 2026-05-11.

- Implementation slices completed: Slice 1 artifact registry, Slice 2 current
  evidence snapshot authoring, Slice 3 materiality next actions, Slice 4 review
  approval writer, Slice 5 quantitative claims review contract, and Slice 6
  documentation/TODO/archive. Nothing in this plan was explicitly deferred.
- Agent-review findings fixed:
  - Slice 1: closeout metadata validation and coverage registry consumers.
  - Slice 2: deleted refs, stale negative statuses, and unsafe snapshot hashing.
  - Slice 3: stale next actions, source freshness, missing-index bypass,
    raw-GitHub-URL routing, and weak typed limitations.
  - Slice 4: self-certified checks, manifest requirement drift, reviewer-role
    override, and weak manifest import validation.
  - Slice 5: missing Codex profile registration, circular first-authoring
    packet activation, shallow quantitative schema, human-producer coverage
    failure, missing `check-evaluation-claims` manifest coverage, and Pants
    sandbox resources for `.codex` profile tests.
- Slice-level verification included the targeted pytest/Pants/smoke/private
  checks listed in each slice, plus agent re-review before commits.
- Final commands run:
  - `pants fmt ::`
  - `pants lint ::`
  - `pants check ::`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `pants run :omen`
  - `git diff --check`
  - `git status --short --untracked-files=all`
- Omen evidence:
  - MCP `changes(count=5)` classified the quantitative Slice 5 commit as
    medium risk due to breadth and historically volatile workflow files; no
    concrete blocker was reported.
  - MCP `complexity(path=src/thesis_review_workflow, threshold=12)` and
    `deadcode(path=src/thesis_review_workflow)` returned no indexed items in
    this session.
  - `pants run :omen` completed with Grade A / Overall Score 91.16. It reported
    known code-health hotspots, especially `check_review_manifest.py`,
    `structured_evidence.py`, `init_review_manifest.py`, `review_materiality.py`,
    and `work_artifacts.py`, but no smells, no SATD, no critical issue count in
    the aggregate summary, and no slice-blocking failure.
- Supervisor closeout has not been implemented by this plan; it remains owned
  by `plans/supervisor_workflow_closeout_plan.md`. Supervisor packets and wave
  gates now consume current evidence snapshots, materiality next actions,
  review approvals, and quantitative claims handoffs.
- Opponent closeout and packets now consume the same helper outputs, and
  `docs/opponent-review-workflow.md` documents the quantitative claims handoff
  plus `check-evaluation-claims`.
- Residual risks:
  - current-evidence snapshots can still become stale if operators do not
    refresh them after late artifact edits;
  - materiality false negatives remain possible for prose-only claims, by
    design, and must be routed by semantic text/code/figure agents rather than
    deterministic raw-text scans;
  - manual typed exceptions remain a trust boundary and must stay explicit in
    `work/review_manifest.json`;
  - native Windows runtime proof remains open in `TODO.md` and was not solved by
    this context-efficiency plan.
