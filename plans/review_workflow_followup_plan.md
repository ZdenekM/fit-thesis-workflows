# Review Workflow Follow-up Plan

Status: planned

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
- `scripts/check-agent-coverage`, `scripts/check-review-wave`,
  `scripts/init-review-manifest`, and `scripts/review-round-closeout` remain
  the deterministic closeout and coverage owners. This plan must not create a
  replacement command.
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
   - Add the smallest useful checker or documented maintainer checklist if the
     audit finds recurrence is likely.
   - Prefer extending `scripts/check-scripts` or an existing doc-check pattern
     over adding a new command.
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

## Progress

- 2026-05-19: Created from Slice 8 of
  `plans/submission_bundle_intake_plan.md`. Existing owners are
  `docs/agent-scheduling.md`, `docs/agent-profile-matrix.md`, repo-local role
  skills, and existing coverage/wave/manifest/closeout commands. No deferred
  implementation was started.

## Decision Log

- Start with review-agent instruction consolidation because it is adjacent to
  repeated multi-agent review work, has clear existing owners, and can reduce
  active instruction drift without touching private case data or workflow
  schemas.
- Defer calibration/profile governance, maintainer write-scope reporting, and
  iterative operator-note batching to `TODO.md` until they have a narrower owner
  and operator evidence.

## Final Audit

Not started.
