# Review Workflow Follow-up Plan

Status: done

## Goal

Produce one compact, owner-aligned review-agent instruction surface by reducing
duplicated agent scheduling, handoff, and role-routing wording across existing
workflow docs and repo-local skills, without adding a new review mode, ledger,
or closeout owner.

## Audit Base

- `docs/agent-scheduling.md` already owns concurrency, wave sequencing,
  subagent handoff shape, role failure handling, and parent synthesis rules.
- `docs/agent-profile-matrix.md` already owns repo-local skill to Codex agent
  profile routing, allowed writes, review separation, and validators.
- `.agents/skills/*/SKILL.md` files already own role-specific procedure,
  evidence rules, output paths, and checker expectations.
- `AGENTS.md` should remain short and point to these owners instead of carrying
  repeated long-form workflow procedure.
- `scripts/check-review-wave` remains the wave-gate owner,
  `scripts/init-review-manifest` and `scripts/check-review-manifest` remain the
  manifest/provenance owners, `scripts/check-agent-coverage` remains the
  coverage owner, and `scripts/review-round-closeout` remains the shared final
  closeout owner. This plan must not create a replacement command.
- The implementation must not inspect real `cases/` content. Any examples or
  tests must use tracked anonymized fixtures or synthetic smoke cases only.

## Scope

- Audit repeated agent instructions in `AGENTS.md`, `docs/agent-scheduling.md`,
  `docs/agent-profile-matrix.md`, and repo-local thesis skills.
- Move reusable scheduling/handoff/role-routing wording to the existing owner
  doc or skill that already owns that concern.
- Replace duplicated active wording with short pointers where possible.
- Keep role-specific evidence contracts in the role skills and routing matrix.
- Add lightweight doc checks only if they prevent recurrence without becoming a
  new workflow gate.
- Before editing any skill in Slice 2, Slice 1 must enumerate the exact
  `.agents/skills/<skill>/SKILL.md` paths that actually contain duplicated
  active wording.

## Non-goals

- Do not change generated artifact semantics, case layout, review-manifest
  schema, coverage schema, or closeout behavior.
- Do not create a new shared review-agent contract document.
- Do not create `scripts/record-operator-note`,
  `scripts/check-calibration-governance`, a profile-update command, or any
  operator-note ledger.
- Do not edit reviewer profiles or private calibration artifacts.
- Do not change agent concurrency defaults unless the tracked config and
  `docs/agent-scheduling.md` are intentionally changed together.

## Slices

1. Instruction Duplication Audit
   - Inventory repeated scheduling, handoff, role-routing, evidence-review, and
     closeout wording across the scoped files.
   - Classify each duplicate by existing owner:
     `docs/agent-scheduling.md`, `docs/agent-profile-matrix.md`, role skill, or
     `AGENTS.md` pointer.
   - Verification: saved audit notes in this plan or a short tracked doc section
     cite exact paths and proposed owner for each material duplicate, including
     exact `.agents/skills/<skill>/SKILL.md` paths for any skill slated for
     Slice 2 edits.

2. Owner-Aligned Wording Consolidation
   - Edit only the owner docs/skills identified in Slice 1.
   - Remove or shorten duplicated active rules where the owner already states
     the contract.
   - Keep Windows command-surface wording in owner docs that mention logical
     `scripts/<tool>` commands.
   - Verification: `rg` checks show the main repeated phrases no longer appear
     as competing active rules in multiple places.

3. Lightweight Recurrence Guard
   - Add the smallest useful checker or owner-doc rule if the audit finds
     recurrence is likely.
   - Prefer extending `scripts/check-scripts` or an existing doc-check pattern
     over adding a new command.
   - Do not create a standalone maintainer checklist, shared instruction doc, or
     parallel review workflow path.
   - Verification: targeted test or smoke covers the guard if code changes are
     made; otherwise record why a manual checklist is enough.

4. Final Audit And Archive Decision
   - Run `git diff --check`, `scripts/check-private`, `scripts/check-scripts`,
     and any targeted tests from Slice 3.
   - Confirm no duplicated active instruction remains between this plan,
     `AGENTS.md`, `docs/agent-scheduling.md`, `docs/agent-profile-matrix.md`,
     and repo-local skills for the audited phrases.
   - Move this plan to `plans/archive/` after completion or copy residual open
     work into `TODO.md`.

## Slice 1 Duplication Audit

- `AGENTS.md` duplicates scheduling, role-failure, generated-artifact review,
  provenance, closeout, and output-path wording that already has narrower
  owners. Proposed owner: keep `AGENTS.md` as the short authorization and
  routing pointer; keep scheduling, handoff, role failure handling, wave gates,
  and parent synthesis in `docs/agent-scheduling.md`; keep role routing,
  allowed writes, review separation, and validators in
  `docs/agent-profile-matrix.md`; keep role-specific outputs and checker
  expectations in the skills.
- `thesis-supervisor-feedback` and `thesis-opponent-materials` repeat the
  scheduling default and wave/concurrency prose from `docs/agent-scheduling.md`.
  Proposed owner: `docs/agent-scheduling.md` owns concurrency and wave rules;
  each orchestration skill keeps only its role list and workflow-specific
  `scripts/check-review-wave` commands.
- Sixteen role skills repeat the same `Agent Final Response Contract` handoff
  list while changing only the owned artifact noun. Proposed owner:
  `docs/agent-scheduling.md` owns default chat handoff shape and parent
  synthesis; role skills keep only role-specific artifact writes, expected
  validation, and any special response additions.
- `thesis-code-consistency` and `thesis-code-quality-review` repeat the
  distinction among workflow profiles, materiality profiles, wave workflows,
  Codex agent profiles, and reviewer preference profiles. Proposed owner:
  `docs/agent-profile-matrix.md`; code skills keep a pointer only.
- Per-skill command-routing text is intentionally not slated for removal in
  Slice 2. It is a Windows command-surface warning enforced by
  `scripts/check-scripts`, not a competing review-agent scheduling or handoff
  rule.

Exact `.agents/skills/<skill>/SKILL.md` paths slated for Slice 2 edits:

- `.agents/skills/thesis-code-consistency/SKILL.md`
- `.agents/skills/thesis-code-quality-review/SKILL.md`
- `.agents/skills/thesis-figure-media-review/SKILL.md`
- `.agents/skills/thesis-github-code-intake/SKILL.md`
- `.agents/skills/thesis-literature-citation-review/SKILL.md`
- `.agents/skills/thesis-opponent-materials-review/SKILL.md`
- `.agents/skills/thesis-opponent-materials/SKILL.md`
- `.agents/skills/thesis-opponent-report-review/SKILL.md`
- `.agents/skills/thesis-quantitative-claims-review/SKILL.md`
- `.agents/skills/thesis-revision-diff/SKILL.md`
- `.agents/skills/thesis-supervisor-feedback-review/SKILL.md`
- `.agents/skills/thesis-supervisor-feedback/SKILL.md`
- `.agents/skills/thesis-supervisor-report-review/SKILL.md`
- `.agents/skills/thesis-supervisor-report/SKILL.md`
- `.agents/skills/thesis-theses-similarity-review/SKILL.md`
- `.agents/skills/thesis-typography-formal-review/SKILL.md`

## Progress

- 2026-05-19: Created from Slice 8 of
  `plans/submission_bundle_intake_plan.md`. Existing owners are
  `docs/agent-scheduling.md`, `docs/agent-profile-matrix.md`, repo-local role
  skills, and existing coverage/wave/manifest/closeout commands. No deferred
  implementation was started.
- 2026-05-19: Pre-implementation agent review completed. No blocker found; plan
  tightened Slice 3 to existing owners only and split wave, manifest,
  coverage, and closeout command ownership. Serena preflight succeeded for
  repo-local Python/Markdown work; scoped use observed
  `src/thesis_review_workflow/cli/check_scripts.py` owner symbols.
- 2026-05-19: Slice 1 in progress. Auditing repeated scheduling, handoff,
  role-routing, evidence-review, closeout, and Windows command-surface wording
  across owner docs and repo-local skills. No `cases/` content inspected.
- 2026-05-19: Slice 1 audit recorded above. Exact skill paths for Slice 2 are
  enumerated; command-routing warnings are intentionally preserved as the
  existing Windows command-surface contract.
- 2026-05-19: Slice 1 checks passed: `git diff --check`,
  `scripts/check-private`, `scripts/check-scripts`. Slice 1 agent review found
  no blocking issues and confirmed no private case data was inspected.
- 2026-05-19: Slice 2 in progress. Editing only `AGENTS.md`,
  `docs/agent-scheduling.md`, `docs/agent-profile-matrix.md`, and the exact
  skill paths enumerated in Slice 1.
- 2026-05-19: Slice 2 consolidation complete. Removed repeated handoff
  bullet-lists from role skills, moved profile terminology to
  `docs/agent-profile-matrix.md`, kept scheduling defaults in
  `docs/agent-scheduling.md`, and shortened `AGENTS.md` to owner pointers.
  Slice 2 reviewers found no privacy or Windows issues; ownership findings were
  fixed by genericizing AGENTS closeout guidance, naming
  `scripts/record-workflow-operation`, and pointing orchestration role-state
  semantics back to `docs/agent-scheduling.md`.
- 2026-05-19: Slice 2 checks passed after fixes: `git diff --check`,
  `scripts/check-private`, `scripts/check-scripts`, and
  targeted Pants tests for `tests/test_agent_profile_contracts.py` and
  `tests/test_check_scripts_contracts.py`.
- 2026-05-19: Slice 3 in progress. Recurrence guard will extend existing
  `scripts/check-scripts` and `tests/test_check_scripts_contracts.py`; Serena
  scoped use re-read `check_scripts.py` symbols before Python edits.
- 2026-05-19: Slice 3 complete. Existing `scripts/check-scripts` now rejects
  copied role-skill handoff lists, scheduling defaults, role-state semantics,
  and profile terminology that belong to `docs/agent-scheduling.md` or
  `docs/agent-profile-matrix.md`. Slice 3 reviewers found no blocking issues
  and confirmed no new command, instruction layer, review path, ledger, or
  closeout owner. Checks passed: `git diff --check`, `scripts/check-private`,
  `scripts/check-scripts`, `pants fmt`, `pants lint`, `pants check`, and
  `pants test tests/test_check_scripts_contracts.py`.

## Decision Log

- Start with review-agent instruction consolidation because it is adjacent to
  repeated multi-agent review work, has clear existing owners, and can reduce
  active instruction drift without touching private case data or workflow
  schemas.
- Defer calibration/profile governance, maintainer write-scope reporting, and
  iterative operator-note batching to `TODO.md` until they have a narrower owner
  and operator evidence.

## Final Audit

- Completed 2026-05-19 and archived under `plans/archive/` according to
  `plans/README.md`.
- Duplicate active instruction audit: targeted `rg` checks found no remaining
  copied role-skill handoff lists, scheduling defaults, generic role-state
  semantics, or profile terminology boundaries across `AGENTS.md`,
  `docs/agent-scheduling.md`, `docs/agent-profile-matrix.md`, repo-local
  skills, and this plan.
- Surface audit: no new shared review-agent contract doc, command,
  operator-note ledger, review mode, closeout owner, or parallel workflow path
  was added. No `cases/` files were read for implementation or included in any
  diff.
- Windows command surface: per-skill and owner-doc command-routing warnings
  remain enforced by `scripts/check-scripts`.
- Residual work: none for this plan. Existing unrelated `TODO.md` items remain
  open; no new follow-up was added.
- Final checks: `git diff --check`, `scripts/check-private`,
  `scripts/check-scripts`, targeted Pants `fmt`, `lint`, `check`, and
  `test tests/test_check_scripts_contracts.py`.
