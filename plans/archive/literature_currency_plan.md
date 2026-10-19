# Context-Aware Literature Currency

Status: done
Created: 2026-10-19

## Start Here

Documentation-only change; initial worktree was clean at `96f965b`.
The revised bibliography and its independent check are complete outside tracked files. Instructions passed independent diff review and all planned lightweight checks. Archive this completed plan; private source material and recommendations stay outside tracked files.

## Goal

Make future literature recommendations and citation reviews explicitly assess currency against a source's role and the pace of the relevant field.

## Audit Base

- `docs/assignment-authoring.md` governs assignment literature provenance but lacks a semantic currency check.
- `.agents/skills/thesis-literature-citation-review/SKILL.md` currently says freshness matters only when material, without requiring that assessment.
- `AGENTS.md` requires generalized workflow corrections after operator calibration and case-neutral tracked changes.
- Read `WORKFLOW_MEMORY.md`; its source-acquisition lessons support explicit access limits and evidence-bounded claims.
- Local RAG located the assignment-authoring literature contract; it also reports an unavailable configured root `~/code/shaas-suite/.agent/workflows`. No index mutation is authorized or needed.

## Scope

Affected paths: `AGENTS.md`, `docs/assignment-authoring.md`, `.agents/skills/thesis-assignment-review/SKILL.md`, `.agents/skills/thesis-literature-citation-review/SKILL.md`, and this plan.
No Python, schemas, templates, age thresholds, automatic lexical gates, profile changes, case setup, IS publication, or commits.
Assumption: currency is a semantic judgment, independent of whether a source is accessible in full. Publication year alone does not establish the period a review covers.

## Slices

### Slice 1 - Literature Currency Instructions

- Status: done
- Proposed commit message: Assess literature currency against source role and field
- Why: Verified identifiers and topical relevance alone do not establish that a recommended bibliography covers current capabilities or evidence.
- Expected paths: `AGENTS.md`, `docs/assignment-authoring.md`, `.agents/skills/thesis-assignment-review/SKILL.md`, `.agents/skills/thesis-literature-citation-review/SKILL.md`, `plans/literature_currency_plan.md` (archived at closeout).
- Tasks: Add one canonical semantic policy in the authoring contract, a concise AGENTS routing rule, and explicit reviewer checks. Require role-sensitive currency assessment, relevant newer-source comparison, review coverage dates when available, bounded older empirical conclusions, whole-list balance, and honest access limits. Preserve the value of foundational and methodological sources and the phase calibration of thesis reviews.
- Out of scope: Changing the full assignment workflow or its artifact contracts; requiring a complete thesis case for a chat-only bibliography request; choosing sources by age quotas.
- Verification: Independent charter and final diff review; `python3 /home/zdenekm/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/thesis-assignment-review`; same command for `.agents/skills/thesis-literature-citation-review`; `python3 tests/test_plan_contract.py`; `scripts/check-private`; `scripts/check-scripts`; `git diff --check`; `git status --short --untracked-files=all`.

## Progress

- Orientation, instruction audit, and independent charter review complete; no blocking findings.
- The requested bibliography correction and independent check finished before instruction edits.
- Canonical policy and routing implemented; independent final diff review approved with no findings.
- All planned lightweight checks passed; no follow-up work remains.
- Success: source selection explicitly assesses currency before recommendation, reviewers check it, and no rule rejects a source merely for its age or invents a current state-of-the-art claim from metadata.

## Decision Log

- 2026-10-19: Keep the correction in the existing authoring contract and route to it from AGENTS and the two review skills. This avoids another instruction layer or deterministic semantic detector.
- 2026-10-19: `currency_rules_review` approved the charter. Its two watchpoints were accepted: newer-source comparison is role-sensitive rather than exhaustive, and currency conclusions remain bounded by actual source access. Both are explicit in the canonical policy.
- 2026-10-19: The same independent reviewer approved the final instruction diff with no findings. Parent inspected the complete diff and confirmed that the change is case-neutral and documentation-only.

## Final Audit

Passed: both edited skills' `quick_validate.py` checks, `python3 tests/test_plan_contract.py`, `scripts/check-private`, `scripts/check-scripts`, `git diff --check`, and `git status --short --untracked-files=all` inspection. The final status must show only the four intended instruction files and the archived plan.

Skipped runtime tests, Serena, and Omen because only Markdown instructions changed; no deterministic checker or code changed. Residual risk: semantic instructions require judgment; validators check structure and hygiene rather than future source-selection quality. Completed plan moves to `plans/archive/literature_currency_plan.md`; no TODO item or commit is needed.
