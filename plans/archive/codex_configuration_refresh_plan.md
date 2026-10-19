# Codex Configuration Refresh

Status: done
Created: 2026-10-19

## Start Here

Completed and independently reviewed. Required role agents no longer need a separate consent phrase. Codex model pins, aliases and inherited-permission documentation are current for the checked CLI/account. Historical plans, private cases and global configuration were not modified.

## Goal

Make the requested workflow sufficient authorization for its required role agents, and keep Codex reviewers on an available high-quality model with accurate configuration and documentation.

## Audit Base

- Initial tracked worktree is clean. Installed CLI is `codex-cli 0.163.0`.
- Active instructions repeat a separate agent-consent requirement across `AGENTS.md`, skills and operator docs. Supervisor-report packet preparation also enforces `--agents-authorized`, including orchestration and closeout.
- `.codex/agents/*.toml`, `review_packets.py` and contract tests pin `gpt-5.5`; a live role launch failed because that model was unsupported for this account. The current local model catalogue lists `gpt-6-astra` with `xhigh`, and a separate reviewer on that requested configuration completed successfully.
- Official OpenAI subagent documentation permits local delegation requested by applicable AGENTS/skill instructions. Official migration guidance and the installed OpenAI Docs resolver select `gpt-6-astra`; preserve `xhigh` semantic reasoning. Sources: https://learn.chatgpt.com/docs/agent-configuration/subagents and https://developers.openai.com/api/docs/guides/latest-model/gpt-6-astra.md.
- Required tools: local RAG queried for discovery, with an unrelated missing-root warning. Serena was absent from the exposed tool catalogue; direct MCP connection to the documented shared bridge repaired access, and scoped overview/body queries succeeded. Omen MCP produced no usable complexity measurements after absolute/relative scope attempts; `pants run scripts:omen -- complexity --focus src/thesis_review_workflow/cli/prepare_supervisor_report_packets.py` succeeded. `pants roots` confirmed the current build root.
- `WORKFLOW_MEMORY.md` was read; preserve independent review, privacy, case operation provenance and native-Windows command routing.

## Scope

Change active consent instructions, the directly enforcing CLI/packet code and tests, active model pins and their contract checks, and confirmed obsolete Codex settings. Keep existing role responsibilities, independent approval, privacy boundaries, source-reading permissions, submitted-code execution permission, external publication approval, low concurrency and Claude model choices.

Non-goals: provider architecture refactoring, changing grading/review content, migrating private cases or historical evidence, changing global Codex settings, increasing concurrency, or speculative hook/security rewrites. Retain generic structured provenance fields when they can truthfully record the requested workflow as their authorization basis; do not require a separate operator confirmation or invent one.

Assumptions/unknowns: current official documentation may describe a newer runtime than the installed CLI. Confirm supported role/config syntax before replacing working registration. Source-specific external-report restrictions are distinct from permission to spawn agents.

## Slices

### Slice A - Requested workflow authorizes its agents

Charter form: compacted
Landed: verified changes; commit and push authorized by the operator on 2026-10-19.
Removed the extra consent gate from active workflow instructions and packet/closeout commands while retaining independent review and source permissions.
Charter: `plans/archive/codex_configuration_refresh/closed-slices-2026-10-19.md`.
Decisions: `2026-10-19 - Slice A review and verification`.

### Slice B - Available semantic models and accurate Codex settings

Charter form: compacted
Landed: verified changes; commit and push authorized by the operator on 2026-10-19.
Updated semantic and mechanical model pins, canonical aliases and the documented permissions contract without changing parent defaults or concurrency.
Charter: `plans/archive/codex_configuration_refresh/closed-slices-2026-10-19.md`.
Decisions: `2026-10-19 - Slice B final review and closeout`.

## Progress

- Both slices are complete, verified and independently reviewed. The operator authorized commit and push on 2026-10-19; publication follows the final Git and lightweight checks.

## Decision Log

- 2026-10-19: The user authorized removal of the obsolete consent rule and a scoped Codex setup refresh. Keep source access, publication and independent review as separate contracts. No private case data enters this plan.
### 2026-10-19 - Slice A review and verification

Independent reviewer found no blockers and one prose-only correction (packet CLI prepares packets; parent launches agents), applied without another review round. Four targeted Pants test modules and five smoke scripts pass; readiness, independent review and source permissions remain.
- 2026-10-19: Independent plan review accepted both slices. Accepted implementation constraint: distinguish workflow `sandbox_mode` metadata from actual parent-inherited Codex permissions. Installed CLI still recognizes V1 depth and job-runtime settings, so documentation omission alone does not justify deleting them. Include the plan-continue prompt and directly affected checker messages in the active consent sweep. Existing semantic artifact `authorization_note` fields remain truthful workflow provenance, without a new operator-confirmation requirement.

### 2026-10-19 - Slice B final review and closeout

Independent review found zero blockers and requested no further changes. Profile pins, mechanical/semantic separation, inherited permissions, registry routing and active instruction closure were checked. The available account catalogue supports the selected model/effort pairs. No separate strict-validation success or hot reload of the existing session is claimed.

## Final Audit

- PASS: thirteen focused Pants test modules: agent-profile contracts, all three packet workflows, review pipeline orchestration, round closeout, workflow core helpers, external opponent feedback, Theses Checker summary, assignment coverage, evidence presence, evaluation claims helpers and opponent calibration.
- PASS: `pants lint` on the changed Python files (Black, isort, Flake8), after narrow formatting corrections required by the checks.
- PASS: `scripts/smoke-supervisor-report-packets`, `scripts/smoke-supervisor-packets`, `scripts/smoke-opponent-packets`, `scripts/smoke-evidence-presence`, `scripts/smoke-assignment-coverage`, `scripts/smoke-evaluation-claims`, `scripts/smoke-opponent-calibration-case`, `scripts/smoke-theses-checker-summary`.
- PASS: scoped Omen complexity check during implementation; full `pants run scripts:omen` passes all ratchets, score 90.484 (A). Coupling/smells graph components are explicitly not measured, not treated as proof of quality.
- PASS: `scripts/check-private`, `scripts/check-scripts`, `git diff --check`, `python3 tests/test_plan_contract.py`; exact active-surface sweep found no obsolete model pins or agent-consent flags. Semantic RAG discovery lagged the disk and was not used as a closure authority.
- PASS: parsed every role TOML and checked selected models/efforts against the current local catalogue. Normal `codex app-server --stdio` initialization and `config/read` returned canonical `hooks`, concurrency 2, all registered roles and preserved V1 settings. This local configuration read did not perform model inference.
- BLOCKED/outside scope: `codex app-server --strict-config --stdio` rejects existing global `features.rmcp_client`. Follow-up owner: operator machine configuration; remove or otherwise reconcile that obsolete global key before expecting strict whole-config validation. Global default `gpt-6.1-sol`/`high` was available and left unchanged.
- SKIPPED: `scripts/smoke-external-opponent-feedback` does not exist (attempt returned command-not-found); its targeted Python test module passed. No replacement smoke helper was added.
- Residual limits: this audit does not prove that the running session hot-reloaded role profiles, that accepted V1 job-runtime settings cap ordinary reviewer turns, or that command hooks run on native Windows. Do not report these as verified guarantees. Independent review requirements, source permissions, publication approval and low concurrency remain intact.
- Archived after independent plan, Slice A and final Slice B/integration review. No private case data, global configuration, Claude model defaults or Codex hook scripts were changed.
