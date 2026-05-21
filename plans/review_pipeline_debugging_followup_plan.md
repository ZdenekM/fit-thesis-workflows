# Review Pipeline Debugging Follow-Up Plan

Status: active
Created: 2026-05-21
Reviewed: 2026-05-21

## Goal

Make the optimized review pipeline easier to debug without weakening review
gates. This V1 focuses on one concrete outcome: stale or contradictory
review-pipeline state must be reported through deterministic, acyclic,
operator-actionable contracts.

The plan is case-neutral. It records workflow behavior, source-binding rules,
diagnostics, fixtures, and command contracts only. Private student facts,
generated case outputs, PDFs, source archives, videos, and report wording stay
under ignored `cases/`.

## Audit Base

This plan follows recurring friction observed while closing reviewed opponent
materials and opponent-report review outputs:

- Generated role packets and aggregate snapshots were sometimes treated as
  long-lived evidence sources, which made otherwise unchanged structured
  artifacts stale after packet or snapshot regeneration.
- Materiality indexes could contain a current decision and an unresolved next
  action for the same role, so the visible blocker did not identify the root
  cause.
- Present no-concern Theses.cz evidence could be reported like missing evidence
  before reviewed synthesis existed, even though the strict final gate should
  remain later in the workflow.
- Role-plan and manifest coverage sometimes required parent-authored filler or
  manual dual registration for silent/internal evidence surfaces.
- Opponent-report approval and manifest checks depended on exact helper-check
  IDs, but generic check refs could be recorded and fail only at closeout.
- Refresh helpers correctly refused to rehash semantic role outputs, but support
  artifact churn still left no bounded recovery path or first-failure summary.
- Long closeout or prepare runs lacked enough progress output to show the active
  profile, helper command, and first actionable failure.

Existing related contracts:

- `plans/archive/review_pipeline_optimization_plan.md` is the completed
  optimized orchestration baseline. This plan records only current gaps that
  remain after that baseline.
- `plans/token_efficiency_reuse_plan.md` owns broad context reuse and evidence
  capsule work. This plan must not reimplement those reuse contracts.
- `TODO.md` already owns broader student-code sandboxing, video/demo intake,
  figure/media expansion, and literature-source automation. This V1 does not
  implement those tracks.

## Scope

In scope for V1:

- Acyclic source-binding rules for long-lived structured evidence.
- Generated-packet and aggregate-snapshot source-ref rejection where those refs
  would cause mechanical stale hashes without adding primary evidence.
- Materiality-state wording and consistency checks for present-but-not-yet-
  synthesis-covered evidence.
- Role-owned coverage and registration presets for silent/internal evidence
  surfaces, without parent-authored filler artifacts.
- Opponent-report helper-check ID validation, calibration applicability, and
  stale review-feedback diagnostics.
- Deterministic support-artifact refresh and review-delta provenance guards that
  do not rehash semantic findings.
- Closeout first-failure reporting, logical recovery commands, and bounded
  progress output.
- Documentation of file-oriented agent progress using existing durable surfaces.

Out of scope for V1:

- Running submitted code by default.
- Deep video/demo inspection and media content review.
- Large submitted-bundle inventory promotion and late evidence-requirements
  materiality expansion. Those remain follow-up work tied to the existing media,
  demo, and evidence-coverage TODO items.
- Reworking all supervisor workflows unless the touched helper code is already
  shared and tests cover the shared behavior.
- Adding compatibility layers for older `~/code/diplomky` workflows.
- Backfilling historical private cases.

## Global Execution Rules

- Before Python workflow edits in each slice, use Serena on the scoped module or
  test file and record the observed result in Progress.
- For material Python workflow changes, attempt Omen MCP on the touched module
  or package during implementation. For larger code slices, run `pants run
  :omen` for reproducible closeout, or record the exact typed limitation.
- Final test evidence uses Pants. Direct `python -m pytest` may be used only as
  exploratory debugging and is not final slice evidence.
- Run Pants commands sequentially.
- Every slice runs `scripts/check-private`, `scripts/check-scripts`, and
  `git diff --check` before commit.
- Any new logical workflow command or operator-visible command mode must update
  `WORKFLOW_COMMAND_MODULES`, CLI targets, `scripts/BUILD`, package coverage,
  launcher expectations, and focused command-surface tests.
- Operator-facing diagnostics print logical workflow command names. Windows
  guidance must point operators to packaged `.cmd`/`.ps1` launchers instead of
  extensionless `scripts/<tool>` files.
- Tests and smokes use generated synthetic fixtures only. Do not copy real
  `cases/` PDFs, source zips, media, extracted text, generated outputs, or
  private notes into tracked fixtures.
- Deterministic helpers may validate structured paths, hashes, enums, schemas,
  check IDs, source classes, and typed limitations. They must not infer that a
  semantic conclusion is unchanged from free text. Semantic unchangedness
  requires a fresh role artifact/review, a structured human/agent no-change
  record, or a typed limitation.

## Execution Order

The dependency order is source and state model first, then downstream operator
diagnostics:

1. Source-binding hygiene and cyclic-source rejection.
2. Materiality state consistency and draft/reviewed boundary wording.
3. Role-owned coverage and silent/internal evidence registration.
4. Opponent-report approval, calibration applicability, and check-ref contract.
5. Deterministic support refresh and review-delta provenance.
6. Closeout and agent-progress observability.

## Slices

### Slice 1 - Structured Source-Binding Hygiene

Current contract delta:

- Existing validators catch stale hashes, but the source class contract still
  allows generated packets or aggregate snapshots to appear in long-lived
  role-owned semantic evidence.
- The target contract is acyclic: role evidence cites primary inputs, stable
  notes, imported reports, or reviewed role outputs, not the packet that
  instructed the role or an aggregate snapshot that includes the role output.

Expected paths:

- `src/thesis_review_workflow/literature_source_acquisition.py`
- `src/thesis_review_workflow/theses_similarity.py`
- `src/thesis_review_workflow/structured_evidence.py`
- `src/thesis_review_workflow/cli/check_literature_citation_review.py`
- `src/thesis_review_workflow/cli/check_theses_similarity_report.py`
- `.agents/skills/thesis-literature-citation-review/SKILL.md`
- `.agents/skills/thesis-theses-similarity-review/SKILL.md`
- `tests/test_literature_citation_checker.py`
- `tests/test_theses_similarity.py`

Work:

- Reject generated packet refs such as `work/opponent_packets/*.md` and
  `work/supervisor_packets/*.md` in long-lived structured evidence.
- Reject role-owned semantic evidence source refs to aggregate snapshots that
  already include that same role evidence, especially
  `work/current_evidence_snapshot.json`.
- Keep deterministic checks structural: do not refresh or reinterpret semantic
  findings.
- Update role instructions so source acquisition and similarity assessments cite
  rendered thesis text, assignment notes, source archives, imported reports, or
  reviewed outputs instead of generated packets.
- Add synthetic tests for packet regeneration and source/snapshot cycles.

Verification:

```bash
scripts/check-private
scripts/check-scripts
git diff --check
pants test tests/test_literature_citation_checker.py tests/test_theses_similarity.py
pants check src/thesis_review_workflow:: tests::
pants lint src/thesis_review_workflow:: tests::
pants run :omen
```

### Slice 2 - Materiality State Consistency

Current contract delta:

- Materiality already writes decisions and next actions, but contradictory
  indexes and present-but-waiting evidence can surface as misleading missing
  evidence.
- The target contract keeps draft gates permissive for present no-concern
  evidence that is waiting for independent reviewed synthesis, while final
  reviewed-wave and manifest gates stay strict.

Expected paths:

- `src/thesis_review_workflow/review_materiality.py`
- `src/thesis_review_workflow/review_wave_gate.py`
- `src/thesis_review_workflow/review_pipeline_orchestration.py`
- `tests/test_review_materiality.py`
- `tests/test_review_wave_gate.py`
- `tests/test_review_pipeline_orchestration.py`

Work:

- Model operator-visible states such as `missing_artifact`,
  `validator_failed`, `present_not_synthesis_covered`,
  `silent_no_concern_waiting_for_reviewed_synthesis`,
  `current_synthesis_covered_artifact`, and `typed_limitation`.
- Add a checker diagnostic when `decisions[]` and `next_actions[]` contradict
  each other for the same role.
- Make draft-wave diagnostics distinguish present no-concern evidence from
  missing evidence.
- Preserve strict final reviewed-wave and manifest coverage.

Verification:

```bash
scripts/check-private
scripts/check-scripts
git diff --check
scripts/smoke-opponent-materials
pants test tests/test_review_materiality.py tests/test_review_wave_gate.py tests/test_review_pipeline_orchestration.py
pants check src/thesis_review_workflow:: tests::
pants lint src/thesis_review_workflow:: tests::
pants run :omen
```

### Slice 3 - Role-Owned Coverage And Silent Evidence Registration

Current contract delta:

- Role-plan closeout can require evidence for synthesis-adjacent or silent
  evidence surfaces, but the normal path should not require late parent-authored
  filler files.
- The target contract either registers validated structured artifacts directly
  or requires explicit role-owned sidecars with documented ownership.

Expected paths:

- `src/thesis_review_workflow/agent_profiles.py`
- `src/thesis_review_workflow/opponent_packets.py`
- `src/thesis_review_workflow/review_manifest.py`
- `src/thesis_review_workflow/review_pipeline_orchestration.py`
- `docs/agent-profile-matrix.md`
- `.agents/skills/thesis-opponent-materials/SKILL.md`
- `.agents/skills/thesis-opponent-materials-review/SKILL.md`
- `tests/test_agent_coverage.py`
- `tests/test_review_manifest_helpers.py`
- `tests/test_review_pipeline_orchestration.py`

Work:

- Decide and encode whether `text_structure_assignment`,
  `evidence_calibration`, and synthesis-side roles are satisfied by role-owned
  sidecars or by validated structured artifacts plus reviewed synthesis.
- Add registration presets for silent/internal evidence roles whose materiality
  JSON and agent-coverage Markdown outputs differ.
- Keep profile matrix, structured profile registry, packets, manifest
  registration, and wave gates aligned.
- Add synthetic tests proving the normal path does not need parent-authored
  filler artifacts.

Verification:

```bash
scripts/check-private
scripts/check-scripts
git diff --check
scripts/smoke-opponent-materials
scripts/smoke-review-round-closeout
pants test tests/test_agent_coverage.py tests/test_review_manifest_helpers.py tests/test_review_pipeline_orchestration.py
pants check src/thesis_review_workflow:: tests::
pants lint src/thesis_review_workflow:: tests::
pants run :omen
```

### Slice 4 - Opponent Report Approval And Calibration Contract

Current contract delta:

- Report-review approval already records observed checks, but generic check refs
  and missing calibration applicability can fail late.
- The target contract rejects or normalizes report helper-check refs before
  closeout and makes stale review feedback explicit after report edits.

Expected paths:

- `src/thesis_review_workflow/review_approvals.py`
- `src/thesis_review_workflow/review_manifest.py`
- `src/thesis_review_workflow/review_wave_gate.py`
- `src/thesis_review_workflow/cli/check_report_calibration.py`
- `src/thesis_review_workflow/cli/init_review_manifest.py`
- `src/thesis_review_workflow/cli/register_review_artifact.py`
- `.agents/skills/thesis-opponent-report-review/SKILL.md`
- `docs/agent-profile-matrix.md`
- `docs/opponent-review-workflow.md`
- `tests/test_review_approvals.py`
- `tests/test_review_manifest_helpers.py`
- `tests/test_review_wave_gate.py`
- `tests/test_report_calibration.py`

Work:

- Validate report-related `--check-ref` values against known manifest helper
  check IDs. Generic `check-opponent-report` must be rejected or mapped only when
  the artifact role and mode are unambiguous from structured inputs.
- Surface exact required helper-check IDs before `write-review-approval`.
- Treat material report edits as invalidating both the approval record and
  `outputs/feedback_k_posudku.md` until fresh independent review exists.
- Make `check-report-calibration` explicitly not applicable when the calibration
  basis is intentionally absent and a validated trace limitation records that
  state; keep it strict when the basis is present or bound.
- Keep the report-review skill, profile matrix, registry, manifest, and wave
  gates synchronized.

Verification:

```bash
scripts/check-private
scripts/check-scripts
git diff --check
scripts/smoke-review-approval
scripts/smoke-register-review-artifact
scripts/smoke-report-calibration
scripts/smoke-review-manifest
pants test tests/test_review_approvals.py tests/test_review_manifest_helpers.py tests/test_review_wave_gate.py tests/test_report_calibration.py
pants check src/thesis_review_workflow:: tests::
pants lint src/thesis_review_workflow:: tests::
pants run :omen
```

### Slice 5 - Deterministic Support Refresh And Review-Delta Provenance

Current contract delta:

- `refresh-round-hashes` is a deterministic maintenance surface, but support
  artifact churn and review-delta source cycles still need bounded diagnostics.
- The target contract refreshes only non-semantic support metadata and rejects
  circular or unstable provenance for semantic deltas.

Expected paths:

- `src/thesis_review_workflow/cli/refresh_round_hashes.py`
- `src/thesis_review_workflow/review_delta.py`
- `src/thesis_review_workflow/review_materiality.py`
- `src/thesis_review_workflow/review_manifest.py`
- `docs/opponent-review-workflow.md`
- `docs/workflow-command-surface.md`
- `tests/test_refresh_round_hashes.py`
- `tests/test_review_delta.py`
- `tests/test_review_materiality.py`
- `tests/test_review_manifest_helpers.py`

Work:

- Preserve the rule that refresh helpers do not rewrite role findings, report
  text, grades, verdicts, private comments, approval records, or review deltas.
- Add bounded support refresh or exact recovery diagnostics for mutable support
  artifacts such as common briefing and current-evidence snapshot when they are
  safe to rebuild from current structured inputs.
- Reject review-delta records that cite the trace/report artifact they update as
  evidence for the delta itself.
- Avoid whole-note hashes for append-only operator notes when older deltas need
  stable provenance; use structured note snapshots or an explicit typed refresh
  contract.
- Add materiality-index consistency diagnostics that point at stale support
  state instead of misleading downstream role gaps.

Verification:

```bash
scripts/check-private
scripts/check-scripts
git diff --check
scripts/smoke-refresh-round-hashes
scripts/smoke-record-review-delta
pants test tests/test_refresh_round_hashes.py tests/test_review_delta.py tests/test_review_materiality.py tests/test_review_manifest_helpers.py
pants check src/thesis_review_workflow:: tests::
pants lint src/thesis_review_workflow:: tests::
pants run :omen
```

### Slice 6 - Closeout And Agent Progress Observability

Current contract delta:

- Closeout already runs the right families of checks, but repeated downstream
  failures can hide the first actionable failure and long nested helpers lack
  enough progress output.
- Agent scheduling already says to trust files and checkers over chat; V1 must
  bind recovery guidance to durable file surfaces instead of adding another
  chat-only rule.

Expected paths:

- `src/thesis_review_workflow/cli/review_round_closeout.py`
- `src/thesis_review_workflow/review_pipeline_orchestration.py`
- `docs/agent-scheduling.md`
- `docs/workflow-command-surface.md`
- repo-local generated-artifact review skills as needed
- `tests/test_review_round_closeout.py`
- `tests/test_review_pipeline_orchestration.py`

Work:

- Print the first failing gate, upstream/downstream classification, and a
  logical recovery command before detailed transcripts.
- Include active case/profile, current helper command, elapsed time, and current
  artifact/check in progress output without exposing private content.
- Ensure closeout interruption cleanup is process-tree aware on POSIX and
  Windows-aware in subprocess code paths; do not rely on WSL-only assumptions.
- Document file-oriented agent recovery through existing durable surfaces:
  expected output paths, `work/review_role_plan.json`, validators, and
  `work/operation_log.jsonl`.
- Add synthetic tests for first-failure precedence, repeated downstream
  failures, interrupted child helpers, and logical recovery command rendering.

Verification:

```bash
scripts/check-private
scripts/check-scripts
git diff --check
scripts/smoke-review-round-closeout
pants test tests/test_review_round_closeout.py tests/test_review_pipeline_orchestration.py
pants check src/thesis_review_workflow:: tests::
pants lint src/thesis_review_workflow:: tests::
pants run :omen
```

## Deferred Follow-Ups

These items are intentionally not part of V1 execution:

- Large submitted-bundle inventory limit promotion through `review-round-start`.
- Late materiality refresh after media/demo or quantitative evidence appears
  after parent-side preparation.
- First-class media/demo inspection beyond deterministic presence and synthetic
  fixture plumbing.
- Submitted-code sandbox execution.

Before archiving V1, either create focused follow-up plans for these items or
ensure the existing `TODO.md` items still name them accurately.

## Progress

| Slice | Status | Serena/Omen note | Verification note |
| --- | --- | --- | --- |
| Plan intake and current-diff review | done | Serena `initial_instructions` read; Serena scoped plan-heading search succeeded. Omen not applicable because the first commit changed docs/profile text only. | `scripts/check-private`, `scripts/check-scripts`, and `git diff --check` passed before commit `58ffbf5`. |
| Plan review repair | done | Serena scoped plan search used; no Python changes yet, so Omen not applicable. | `scripts/check-private`, `scripts/check-scripts`, and `git diff --check` passed. |
| Slice 1 | done | Serena inspected `structured_evidence.py`, `literature_source_acquisition.py`, and `theses_similarity.py`. Omen MCP returned zero files for scoped module/package paths but repo-root repomap worked and highlighted `structured_evidence.py`; reproducible `pants run :omen` passed with the existing grade-A baseline. | `scripts/check-private`, `scripts/check-scripts`, `git diff --check`, `pants test tests/test_literature_citation_checker.py tests/test_theses_similarity.py`, `pants check src/thesis_review_workflow:: tests::`, touched-file `pants fmt`/`pants lint`, and `pants run :omen` passed. Broad `pants lint src/thesis_review_workflow:: tests::` hit unrelated baseline formatter/lint changes outside Slice 1, so it was not used as slice evidence. |
| Slice 2 | done | Serena inspected `review_materiality.py` and `review_wave_gate.py`. Omen MCP returned zero files for the scoped module path but repo-root repomap worked; reproducible `pants run :omen` passed with grade A / 90.48 and existing hotspot baseline. | `scripts/check-private`, `scripts/check-scripts`, `git diff --check`, `scripts/smoke-opponent-materials`, `pants test tests/test_review_materiality.py tests/test_review_wave_gate.py tests/test_review_pipeline_orchestration.py`, `pants check src/thesis_review_workflow:: tests::`, touched-file `pants fmt`/`pants lint`, and `pants run :omen` passed. Broad `pants lint src/thesis_review_workflow:: tests::` again hit unrelated baseline formatter/lint changes outside Slice 2, so targeted lint is the slice evidence. |
| Slice 3 | pending | Record before commit. | Pending. |
| Slice 4 | pending | Record before commit. | Pending. |
| Slice 5 | pending | Record before commit. | Pending. |
| Slice 6 | pending | Record before commit. | Pending. |

## Decision Log

- 2026-05-21: Kept this as a separate active plan instead of reopening
  `plans/archive/review_pipeline_optimization_plan.md`; the archived plan is a
  completed baseline and this file covers follow-up debugging contracts.
- 2026-05-21: Agent review found the original draft too broad for one
  executable plan. Narrowed V1 to source-binding, materiality, approval,
  refresh/delta, role coverage, and closeout observability. Deferred
  large-bundle inventory and late evidence-requirements materiality work to
  follow-up planning/TODO.
- 2026-05-21: Reordered execution so closeout presentation lands after the
  state/source contracts it diagnoses.
- 2026-05-21: Final verification must use Pants, repo hygiene, and Omen where
  Python workflow code changes materially; direct pytest is exploratory only.
- 2026-05-21: Deterministic refresh helpers must not claim semantic
  unchangedness from free text or implicit rehashing.
- 2026-05-21: Operator-facing recovery commands must remain logical workflow
  command names and respect the packaged Windows launcher boundary.
- 2026-05-21: Slice 2 keeps silent no-concern Theses.cz assessments as a
  draft/trace waiting state only for synthesis workflows that can later bind
  reviewed manifest coverage; other workflows still require the role review or
  a typed limitation.

## Final Audit

Not run yet. Before archiving this plan, record:

```bash
scripts/check-private
scripts/check-scripts
git diff --check
pants fmt ::
pants lint src/thesis_review_workflow:: tests:: scripts::
pants check src/thesis_review_workflow:: tests:: scripts::
pants test tests/test_literature_citation_checker.py tests/test_theses_similarity.py tests/test_review_materiality.py tests/test_review_wave_gate.py tests/test_review_pipeline_orchestration.py tests/test_agent_coverage.py tests/test_review_manifest_helpers.py tests/test_review_approvals.py tests/test_report_calibration.py tests/test_refresh_round_hashes.py tests/test_review_delta.py tests/test_review_round_closeout.py
pants run :omen
```

Also record every slice-specific smoke command that was run, any skipped check
with a concrete limitation, final git status, and the archive or follow-up TODO
decision.
