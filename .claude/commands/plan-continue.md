---
description: "Resume the active tracked plan from its Start Here section and execute exactly the next action"
---

# Continue The Active Plan

One job: resume the active tracked execution plan exactly where its `## Start Here` points, with no
hand-written handoff prompt. The plan is the only carrier of state between sessions; this invocation
adds no context of its own. Contract: `plans/README.md` `## Session Handoff`.

This is the constant session-boundary invocation. Any agent can reach the same procedure through the
sentence "Continue the active plan."

1. Read `plans/README.md` if this session has not yet, then the active plan with a READING BUDGET:
   `## Start Here`, `## Progress`, the active and next slice charters, the `## Acceptance Contract`
   when present, and the two most recent `## Decision Log` entries. Do NOT read compacted slice
   records, older Decision Log entries, or `plans/archive/**` unless a specific question forces it —
   that history is adjudicated, and re-reading it burns the context the active slice needs.
2. Find the active plan: the file carrying `Status: in_progress` among `plans/*_plan.md`. Exactly one
   is expected; on zero or several, stop and ask the operator which plan is active.
3. Reconcile per `## Session Handoff`: derive the plan's last-touch commit
   (`git log -1 --format=%h -- <plan file>`), list `git log <that>..HEAD --oneline`, and fold
   anything unrecorded into `## Start Here` / `## Progress` before any other work. The SessionStart
   plan-state hook prints this state when there is something to reconcile.
4. If the next action is a new or materially rewritten slice charter, review the charter before
   implementing it, and triage findings per `## Plan-Change Review` — one round plus at most one
   narrow re-check, then shrink the object rather than buying a third round.
5. Execute exactly the action `## Start Here` names — one slice or one pass, not more. Respect every
   stop condition in the charter and in `plans/README.md`. Decision points that belong to the
   operator (plan approval, anything sendable to a student or FIT IS, anything that spends money,
   agent authorization) end the turn with an explicit question, never with silence and never by
   proceeding.
6. End per `## Session Handoff`: update `## Start Here` (state, exact next action, open questions),
   run the plan gate and the repo's lightweight checks, commit green work, stop. Never write a
   bespoke handoff prompt for the next session.

```bash
python3 tests/test_plan_contract.py
git diff --check
scripts/check-private
scripts/check-scripts
```

Route every lesson learned on the way: a repeatable process rule into `plans/README.md`,
`AGENTS.md`, or a skill; a mechanically checkable trap into `tests/test_plan_contract.py`, another
test, or a hook; a plan-scoped fact into a charter or `## Decision Log`; the next action into
`## Start Here`. Nothing into a prompt.
