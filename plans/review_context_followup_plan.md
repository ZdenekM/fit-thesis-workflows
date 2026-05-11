# Review Context Follow-Up Plan

Status: planned
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
- centralize output artifact metadata if the new helpers would otherwise extend
  the existing duplication;
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
- Approval helper output is a provenance convenience, not a substitute for the
  independent reviewer actually reading the artifact.
- Materiality remains advisory for optional roles. A materiality decision may
  activate packets or next-action prompts; it must not become a semantic verdict.
- Omen remains developer/reviewer evidence for code-quality review, not an
  operator closeout prerequisite.

## Slices

### Slice 1 - Plan Review And Artifact Registry Audit

- Status: pending
- Proposed commit message: `docs(workflow): plan review context follow-up`
- Expected paths:
  - `plans/review_context_followup_plan.md`
  - `TODO.md`
  - `src/thesis_review_workflow/review_manifest.py`
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
- Tasks:
  - Review this plan with agents before implementation.
  - Decide whether output artifact metadata should be centralized before adding
    more artifact types.
  - If centralization is needed, define a shared registry used by manifest
    initialization and incremental registration.
  - Keep the existing supervisor closeout plan as the command-bundle owner.
- Verification:
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 2 - Current Evidence Snapshot Authoring

- Status: pending
- Proposed commit message: `feat(workflow): add current evidence snapshot helper`
- Expected paths:
  - `src/thesis_review_workflow/structured_evidence.py`
  - `src/thesis_review_workflow/cli/update_current_evidence_snapshot.py`
  - `src/thesis_review_workflow/commands.py`
  - `scripts/update-current-evidence-snapshot`
  - `scripts/BUILD`
  - `tests/test_structured_evidence.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-current-evidence-snapshot`
- Tasks:
  - Add a helper that writes `work/current_evidence_snapshot.json` from explicit
    round-relative source refs and known structured inputs such as GitHub intake,
    late notes, existing reviewed outputs, report trace, and approval records.
  - Hash-bind every source ref and reject unsafe paths.
  - Add an update mode that preserves still-current entries and removes stale
    entries only when the operator or calling command requests refresh.
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

- Status: pending
- Proposed commit message: `feat(workflow): route materiality next actions`
- Expected paths:
  - `src/thesis_review_workflow/review_materiality.py`
  - `src/thesis_review_workflow/supervisor_packets.py`
  - `src/thesis_review_workflow/opponent_packets.py`
  - `.agents/skills/thesis-supervisor-feedback/SKILL.md`
  - `.agents/skills/thesis-opponent-materials/SKILL.md`
  - `README.md`
  - `tests/test_review_materiality.py`
  - `tests/test_supervisor_packets.py`
  - `tests/test_opponent_packets.py`
- Tasks:
  - Make `github_intake` materiality surface a concrete next action when GitHub
    evidence exists but `outputs/github_code_intake.md` is missing or stale.
  - Make `quantitative_claims` materiality surface a concrete next action when
    quantitative review is material but `work/quantitative_claims.json` is
    missing or stale.
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

- Status: pending
- Proposed commit message: `feat(workflow): add review approval writer`
- Expected paths:
  - `src/thesis_review_workflow/review_approvals.py`
  - `src/thesis_review_workflow/cli/write_review_approval.py`
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
  - Support canonical profiles for supervisor feedback, opponent materials, and
    opponent report review, plus an explicit custom mode for standalone final
    evidence.
  - Require reviewer role, reviewer agent or human identifier, verdict,
    blocking finding count, observed checks, limitations, and timestamp.
  - Reject `approved/pass` with non-zero blocking findings.
  - Validate the written record immediately with the existing approval validator.
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

- Status: pending
- Proposed commit message: `docs(workflow): add quantitative claims review contract`
- Expected paths:
  - `.agents/skills/thesis-quantitative-claims-review/SKILL.md`
  - `.agents/skills/thesis-supervisor-feedback/SKILL.md`
  - `.agents/skills/thesis-opponent-materials/SKILL.md`
  - `README.md`
  - `src/thesis_review_workflow/cli/check_evaluation_claims.py`
  - `tests/test_structured_evidence.py`
- Tasks:
  - Add a repo-local skill or template that tells a quantitative reviewer how to
    author `work/quantitative_claims.json`.
  - Keep the review semantic and evidence-bound: units, scale, baseline,
    sample size, practical magnitude, reproducibility, and overclaim risk.
  - Ensure synthesis packets consume the compact quantitative handoff rather
    than rereading full result sections.
  - Avoid making deterministic checks infer metric meaning from raw text.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_structured_evidence.py`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 6 - Documentation, TODO Reconciliation, And Archive

- Status: pending
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

## Decision Log

- 2026-05-11: Do not create a second supervisor closeout plan. Execute
  `plans/supervisor_workflow_closeout_plan.md` for supervisor preflight/closeout
  commands.
- 2026-05-11: Keep video/demo deep media intake in TODO for now. It is
  important, but broader than this follow-up's context-friction scope.
- 2026-05-11: Treat approval-record writing as a convenience around an actual
  independent review, not as proof that a review happened.

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

Not run yet. Before archiving this plan, record:

- implementation slices completed or explicitly deferred;
- agent-review findings and fixes;
- exact commands run for each slice;
- whether supervisor closeout consumed the new helper outputs;
- whether opponent closeout consumed the new helper outputs;
- residual risks around stale snapshots, materiality false negatives, manual
  exceptions, and Windows command-surface coverage.
