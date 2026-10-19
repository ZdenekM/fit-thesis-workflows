# Closed Slices

### Slice A - Requested workflow authorizes its agents

Status: done
Proposed commit message: Remove redundant per-request role-agent consent gates
Why: A workflow request should not stop for an extra phrase that adds no scope or evidence.
Expected paths: `AGENTS.md`, `README.md`, `.agents/skills/*/SKILL.md`, `docs/agent-scheduling.md`, `docs/operator-reference.md`, `docs/workflow-command-surface.md`, `docs/historical-opponent-calibration.md`, `docs/supervisor-report-calibration.md`, `src/thesis_review_workflow/cli/{prepare_supervisor_report_packets,prepare_review_round,review_round_closeout,opponent_preflight}.py`, `src/thesis_review_workflow/supervisor_report_packets.py`, `src/thesis_review_workflow/cli/{check_assignment_coverage,check_evidence_presence,check_evaluation_claims,check_opponent_calibration_case,check_theses_checker_summary}.py`, `src/thesis_review_workflow/external_opponent_feedback.py`, `tests/{test_supervisor_report_packets,test_review_pipeline_orchestration,test_review_round_closeout,test_workflow_core_helpers}.py`, `.claude/commands/plan-continue.md`, and `scripts/smoke-supervisor-report-packets`.
Tasks: Replace separate-consent instructions with explicit standing delegation instructions for requested workflows; remove obsolete CLI flags and authorization-only packet parameters/fields; allow normal packet generation and closeout refresh without consent flags; keep actual readiness, independent review and source permissions. Inventory exact active occurrences before edits and sweep again afterwards.
Out of scope: Removing human confirmation of report contents or publication, source licensing/access restrictions, submitted-code execution approval, or semantic provenance validation.
Verification: `pants test tests/test_supervisor_report_packets.py tests/test_review_pipeline_orchestration.py tests/test_review_round_closeout.py tests/test_workflow_core_helpers.py`; `scripts/smoke-supervisor-report-packets`, `scripts/smoke-evidence-presence`, `scripts/smoke-assignment-coverage`, `scripts/smoke-evaluation-claims`, `scripts/smoke-opponent-calibration-case`; `scripts/check-private`; `scripts/check-scripts`; `git diff --check`; exact and semantic discovery sweeps of active instruction surfaces.

### Slice B - Available semantic models and accurate Codex settings

Status: done
Proposed commit message: Refresh Codex reviewer models and configuration contracts
Why: Unsupported model pins break required review before any evidence is produced, and stale settings can misrepresent runtime protections.
Expected paths: `AGENTS.md`, `.codex/config.toml`, `.codex/agents/*.toml`, `src/thesis_review_workflow/review_packets.py`, `tests/test_agent_profile_contracts.py`, `src/thesis_review_workflow/{supervisor_packets,opponent_packets,supervisor_report_packets}.py`, `tests/{test_opponent_packets,test_supervisor_packets}.py` and `scripts/smoke-{supervisor,opponent,supervisor-report}-packets`, `docs/agent-scheduling.md`, `docs/agent-workflow.md`, `docs/agent-profile-matrix.md`, `.agents/skills/*/SKILL.md`.
Tasks: Pin semantic roles and generated packet guidance to verified `gpt-6-astra`/`xhigh`, and mechanical helpers to available `gpt-6-luna`/`high`; remove duplicated model literals from skills in favor of the scheduling contract; apply only configuration changes supported by installed-runtime evidence or a documented canonical alias; correct claims about inherited permissions; preserve role routing and the concurrency limit. Review the complete diff independently and resolve findings.
Out of scope: Global/default parent model changes, Claude tier changes, larger provider migrations, higher concurrency, or new compatibility layers.
Verification: `pants test tests/test_agent_profile_contracts.py tests/test_opponent_packets.py tests/test_supervisor_packets.py`; TOML parsing and local `codex app-server --stdio` initialization plus `config/read` (no inference); `python3 tests/test_plan_contract.py`; required lightweight checks; scoped Omen during implementation and `pants run scripts:omen` at closeout. A new session may be required to reload custom roles; do not claim the current session reloaded them.
