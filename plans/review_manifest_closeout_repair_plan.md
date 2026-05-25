# Review Manifest Closeout Repair Plan

Status: planned
Created: 2026-05-22

## Goal

Make review-round closeout deterministic after a reviewed report or feedback
artifact is legitimately changed, re-exported, and independently re-approved.

The target outcome is that the supported closeout command for a workflow profile
has one clear recovery path and can distinguish:

- stale semantic evidence that requires a role rerun or review delta,
- regenerable support metadata that should be refreshed automatically, and
- invalid workflow metadata that should be repaired by the responsible helper
instead of by manual JSON edits.

## Audit Base

This plan is based on a late opponent-report-review wording pass in which the
clean report proposal, canonical draft, operator notes, report trace hash, review
feedback, approval record, agent coverage, and review manifest were all updated
through the intended review/export/review path. The concrete case artifacts are
private and remain under ignored `cases/`; this plan records only case-neutral
workflow failures.

Observed failure classes:

- `scripts/check-review-wave --workflow opponent_report_review --wave final`
  passed after independent review and approval refresh, but
  `scripts/check-review-manifest --require-complete` still failed.
- `work/common_briefing.json` and `work/current_evidence_snapshot.json` behaved
  like independent stale evidence gates even though they are derived support
  surfaces for agent context and should be safely regenerable when the semantic
  artifact has already been re-reviewed.
- `scripts/refresh-round-hashes` correctly refused to refresh hashes for report
  text, reviewed outputs, traces, and role evidence artifacts, but there was no
  follow-up command that reconciled the derived support snapshots after a valid
  re-review.
- `work/review_manifest.json` still carried a legacy generic
  `check-opponent-report` reference. The current helper contract requires
  `check-opponent-report:canonical` and `check-opponent-report:clean`.
- The profile role plan reported stale or mismatched role profile identifiers
  for roles that are now owned by `docs/agent-profile-matrix.md` and
  `src/thesis_review_workflow/agent_profiles.py`.
- `work/literature/source_acquisition.json` recorded a generated role packet as
  a source ref. The validator correctly rejects role packets as primary evidence
  for literature-source acquisition.
- Because `outputs/literature_citation_review.md` existed, manifest closeout
  required `check-literature-citation-review` as a passed helper check. The
  check was not recorded as passed in the manifest.
- The failure report presented all stale support metadata, profile-plan drift,
  helper-check drift, and literature-source contract errors together. That made
  the operator-facing recovery path unclear.

Relevant tracked surfaces:

- `src/thesis_review_workflow/cli/check_review_manifest.py`
- `src/thesis_review_workflow/cli/init_review_manifest.py`
- `src/thesis_review_workflow/cli/review_round_closeout.py`
- `src/thesis_review_workflow/cli/refresh_round_hashes.py`
- `src/thesis_review_workflow/review_manifest.py`
- `src/thesis_review_workflow/review_packets.py`
- `src/thesis_review_workflow/review_pipeline_orchestration.py`
- `src/thesis_review_workflow/helper_checks.py`
- `src/thesis_review_workflow/agent_profiles.py`
- `docs/agent-profile-matrix.md`
- `docs/agent-scheduling.md`
- `docs/opponent-review-workflow.md`
- `docs/workflow-command-surface.md`
- `.agents/skills/thesis-opponent-report-review/SKILL.md`
- `.agents/skills/thesis-literature-citation-review/SKILL.md`
- `scripts/smoke-review-manifest`
- `scripts/smoke-opponent-report`
- `scripts/smoke-opponent-closeout`
- `scripts/smoke-refresh-round-hashes`
- `scripts/smoke-internal-evidence-validators`

Useful diagnostic commands:

```bash
scripts/check-review-manifest --require-complete <case-id> [round-id]
scripts/refresh-round-hashes <case-id> [round-id]
scripts/review-round-closeout --profile opponent_report_review <case-id> [round-id]
scripts/init-review-manifest --run-checks <case-id> [round-id]
scripts/check-review-wave --workflow opponent_report_review --wave final <case-id> [round-id]
```

The implementation must replace real case reproduction with synthetic smoke
fixtures. Private case data must not be copied into tracked tests or plans.

Boundary with `plans/token_efficiency_reuse_plan.md`:

- The token-efficiency plan already implemented broad reuse, helper-check reuse,
  and manifest refresh ordering. This plan does not reopen that general contract.
- This plan is limited to the remaining opponent-report-review closeout failure
  class: valid post-review report changes, re-export, independent re-approval,
  profile transition metadata, stale derived support snapshots, legacy helper
  refs still present in an old manifest, and literature source-acquisition refs.
- If a slice discovers that the general token-efficiency machinery already
  covers a failure class, the implementation should delete the duplicate work
  from this plan and record the existing recovery command instead of adding a
  second repair path.

## Scope

In scope:

- Make the manifest/closeout recovery model explicit and deterministic.
- Ensure `init-review-manifest` and manifest merge logic normalize legacy
  `check-opponent-report` references into mode-specific helper ids or remove
  stale legacy refs.
- Ensure artifact `check_refs` are regenerated from current helper checks rather
  than preserving ambiguous stale values.
- Make profile transition and role-plan refresh produce current profile role
  identifiers for the active workflow profile.
- Define when `common_briefing` and `current_evidence_snapshot` are derived
  caches and how closeout refreshes them after a valid semantic re-review.
- Prevent support snapshots from blocking closeout with stale hashes when the
  responsible final artifact and approval record are current.
- Keep semantic drift strict: report text, reviewed evidence, traces, points,
  grades, and findings still require role rerun, review delta, or independent
  review before closeout passes.
- Fix literature source-acquisition source refs so generated role packets are
  not treated as primary evidence.
- Make required helper checks, especially `check-literature-citation-review`,
  run and record passed status when their artifacts are present.
- Add regression coverage for a report wording change followed by export,
  independent review approval, manifest refresh, and closeout.
- Update docs and repo-local skills so agents use the repaired command path
  rather than manually repairing JSON hashes.

Out of scope:

- Changing grading semantics, review tone, point calibration, or report content
  policy.
- Backfilling or rewriting old private case outputs.
- Weakening `check-review-manifest --require-complete`.
- Accepting generated role packets as primary evidence just to make a check
  pass.
- Adding fallback compatibility for older `~/code/diplomky` workflows.
- Making thesis-case pipeline checks depend on Omen or other maintainer-only
  developer hygiene tools.

## Slices

### Slice 1 - Failure Taxonomy And Repro Fixture

- Status: pending
- Proposed commit message: `test(review): reproduce stale closeout provenance`
- Why: The repair needs a synthetic fixture that reproduces the actual failure
  class without private case data.
- Expected paths:
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-opponent-report`
  - `scripts/smoke-opponent-closeout`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `docs/opponent-review-workflow.md`
- Tasks:
  - Add or extend a synthetic opponent-report-review fixture that performs a
    valid report wording edit, re-export, approval refresh, and manifest refresh.
  - Assert that current behavior fails for the known classes: derived snapshot
    stale hashes, legacy generic check id, stale role profile ids, literature
    source-ref contract, and missing required helper-check record.
  - Classify each failure as semantic rerun, derived-cache refresh, metadata
    normalization, or source-contract repair.
  - Document the intended recovery model in the plan progress notes before code
    changes.
- Verification:
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-opponent-report`
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

### Slice 2 - Helper Check Id And Manifest Normalization

- Status: pending
- Proposed commit message: `fix(manifest): normalize opponent report helper refs`
- Why: Closeout cannot be deterministic while stale generic helper ids survive
  in artifact refs.
- Expected paths:
  - `src/thesis_review_workflow/helper_checks.py`
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `src/thesis_review_workflow/review_manifest.py`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `scripts/smoke-review-manifest`
- Tasks:
  - Ensure `init-review-manifest` drops or rewrites legacy
    `check-opponent-report` refs when rebuilding helper checks and artifact
    `check_refs`.
  - Make artifact `check_refs` a projection of current helper-check targets,
    not a sticky field copied from old manifest state.
  - Keep validation strict: handwritten new generic ids should still fail.
  - Add regression tests for old-manifest migration and current-manifest
    generation.
- Verification:
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-opponent-report`
  - `pants test tests/test_review_manifest_helpers.py tests/test_opponent_report.py`
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

### Slice 3 - Profile Role Plan Refresh

- Status: pending
- Proposed commit message: `fix(review): refresh role profiles during closeout`
- Why: A closeout profile should not fail because role-plan metadata still
  reflects a previous workflow profile after a valid profile transition.
- Expected paths:
  - `src/thesis_review_workflow/review_pipeline_orchestration.py`
  - `src/thesis_review_workflow/cli/review_round_closeout.py`
  - `src/thesis_review_workflow/agent_profiles.py`
  - `docs/agent-profile-matrix.md`
  - `scripts/smoke-opponent-closeout`
  - `scripts/smoke-agent-coverage`
- Tasks:
  - Audit expected role-profile ids against `docs/agent-profile-matrix.md`.
  - Ensure `prepare-review-round` and `review-round-closeout` either refresh
    stale role-plan state automatically for the requested profile or stop with
    one exact recovery command.
  - Add regression coverage for switching from an evidence/materials workflow
    to `opponent_report_review`.
  - Keep agent authorization semantics intact; do not silently spawn agents or
    claim semantic review happened.
- Verification:
  - `scripts/smoke-opponent-closeout`
  - `scripts/smoke-agent-coverage`
  - `pants test tests/test_review_pipeline_orchestration.py tests/test_review_round_closeout.py tests/test_agent_profile_contracts.py tests/test_agent_coverage.py`
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

### Slice 4 - Derived Snapshot And Common Briefing Contract

- Status: pending
- Proposed commit message: `fix(review): separate support snapshots from evidence gates`
- Why: `common_briefing` and `current_evidence_snapshot` should guide agents,
  not become a second approval system with stale copies of reviewed artefact
  hashes.
- Expected paths:
  - `src/thesis_review_workflow/review_packets.py`
  - `src/thesis_review_workflow/structured_evidence.py`
  - `src/thesis_review_workflow/cli/refresh_round_hashes.py`
  - `src/thesis_review_workflow/cli/review_round_closeout.py`
  - `src/thesis_review_workflow/cli/update_current_evidence_snapshot.py`
  - `docs/workflow-command-surface.md`
  - `docs/opponent-review-workflow.md`
  - `scripts/smoke-refresh-round-hashes`
  - `scripts/smoke-opponent-closeout`
- Tasks:
  - Define which records in support snapshots are strict semantic inputs and
    which are derived context references.
  - Make closeout refresh derived support metadata after approval records and
    final review wave have been refreshed.
  - Preserve strict blocking for unreviewed semantic changes to report text,
    reviewed outputs, traces, findings, points, grades, and private comments.
  - Change failure messages so support-cache drift points to the right recovery
    command, and semantic drift points to review delta or role rerun.
  - Add tests for operator-note-only changes, approval-record changes, and
    report-text changes after review.
- Verification:
  - `scripts/smoke-refresh-round-hashes`
  - `scripts/smoke-opponent-closeout`
  - `scripts/smoke-review-manifest`
  - `pants test tests/test_refresh_round_hashes.py tests/test_review_round_closeout.py tests/test_review_manifest_helpers.py`
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

### Slice 5 - Literature Source Acquisition Contract

- Status: pending
- Proposed commit message: `fix(literature): keep role packets out of source refs`
- Why: Literature source acquisition must cite primary case artifacts, stable
  notes, imported reports, or reviewed outputs, not generated packet prompts.
- Expected paths:
  - `src/thesis_review_workflow/literature_source_acquisition.py`
  - `src/thesis_review_workflow/semantic_source_refs.py`
  - `src/thesis_review_workflow/cli/check_literature_citation_review.py`
  - `.agents/skills/thesis-literature-citation-review/SKILL.md`
  - `docs/agent-profile-matrix.md`
  - `scripts/smoke-internal-evidence-validators`
  - `scripts/smoke-opponent-report`
- Tasks:
  - Find the generator or helper path that writes
    `work/literature/source_acquisition.json`.
  - Change it to record only accepted source-ref classes.
  - Keep the validator strict so packet prompts remain rejected.
  - Ensure `init-review-manifest --run-checks` records
    `check-literature-citation-review` as passed when
    `outputs/literature_citation_review.md` exists and the artifact is valid.
  - Add a negative test for packet refs and a positive test for reviewed output
    or stable note refs.
- Verification:
  - `scripts/check-literature-citation-review <synthetic-case> [round-id]`
  - `scripts/smoke-internal-evidence-validators`
  - `scripts/smoke-opponent-report`
  - `pants test tests/test_literature_citation_checker.py tests/test_review_manifest_helpers.py`
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

### Slice 6 - End-To-End Closeout Recovery

- Status: pending
- Proposed commit message: `test(review): cover opponent report reapproval closeout`
- Why: The repaired pieces must work together through the operator-facing
  command path.
- Expected paths:
  - `scripts/smoke-opponent-closeout`
  - `scripts/smoke-opponent-report`
  - `scripts/smoke-review-manifest`
  - `docs/opponent-review-workflow.md`
  - `docs/workflow-command-surface.md`
  - `.agents/skills/thesis-opponent-report-review/SKILL.md`
- Tasks:
  - Add an end-to-end smoke where a clean opponent report is reviewed, then
    changed materially enough to require re-export/re-review, then approved.
  - Verify `scripts/review-round-closeout --profile opponent_report_review`
    reaches a clean manifest closeout without manual JSON edits.
  - Verify the first failure shown by closeout is actionable if a semantic
    change is made after approval.
  - Update docs/skill instructions to name the single supported recovery path.
- Verification:
  - `scripts/review-round-closeout --profile opponent_report_review <synthetic-case> [round-id]`
  - `scripts/smoke-opponent-closeout`
  - `scripts/smoke-opponent-report`
  - `scripts/smoke-review-manifest`
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

## Progress

- 2026-05-22: Plan created from a real opponent-report-review closeout failure
  class. No implementation started.

## Decision Log

- Keep `check-review-manifest --require-complete` strict. The problem is not
  that the gate is too strong; the problem is that its recovery path currently
  conflates derived-cache refresh, metadata migration, and semantic rerun.
- Do not repair real private case JSON by hand as the primary solution. Use the
  real failure only as diagnostic input, then capture the behavior with
  synthetic smokes.
- Treat `common_briefing` and `current_evidence_snapshot` as support surfaces.
  They may block closeout when invalid, but the supported repair must be a
  deterministic refresh or an explicit semantic rerun, not ad hoc hash editing.
- Keep generated role packets out of evidence source refs. They are prompts or
  handoff context, not primary evidence.

## Final Audit

Not started.

Expected final closeout for this plan:

```bash
scripts/smoke-review-manifest
scripts/smoke-opponent-report
scripts/smoke-opponent-closeout
scripts/smoke-refresh-round-hashes
scripts/smoke-internal-evidence-validators
git diff --check
scripts/check-private
scripts/check-scripts
```

If Python workflow code changes materially, add targeted Pants tests and run
Pants sequentially. If the touched surface is broad enough for repo hygiene,
also run the relevant dev hygiene targets from `docs/dev-hygiene.md`.
