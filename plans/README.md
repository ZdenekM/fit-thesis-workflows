# Plans

This directory holds file-based execution plans for non-trivial workflow and
tooling changes in this repository.

Plans are not a replacement for `TODO.md`. `TODO.md` is the durable open-work
index. A plan is the current execution contract for one larger change that needs
scope, sequencing, verification, and resume context.

## When To Use

Use a tracked plan when a repo change:

- spans multiple files or workflow contracts,
- should be split into commit-sized slices,
- depends on audit findings, tool output, or explicit validation commands,
- needs a reliable resume point after interruption,
- affects operator-visible workflow behavior, generated artifacts, or helper
  scripts.

Do not put private thesis or student case details in tracked plans. Case-specific
execution notes belong under ignored `cases/<case-id>/...`.

## Layout

- Active plans: `plans/*_plan.md`
- Archived plans: `plans/archive/*_plan.md`
- Planning contract: `plans/README.md`

Move a completed or superseded plan to `plans/archive/` after its final audit is
recorded and any residual work is either closed or copied into `TODO.md`.

## Plan Shape

Each active plan should contain:

- `Status`: `planned`, `active`, `blocked`, `done`, or `superseded`
- `Goal`: one concrete outcome
- `Audit Base`: current findings, exact commands, relevant paths, constraints
- `Scope` and `Non-goals`: what the plan will and will not touch
- `Slices`: commit-sized steps with expected paths and verification
- `Progress`: current slice state, updated as work proceeds
- `Decision Log`: meaningful sequencing or scope decisions
- `Final Audit`: commands run, skipped checks, residual risks, archive decision

Use exact paths and commands. Avoid placeholder tokens in active plans. If a
path is dynamic, record the command that resolves it.

## Execution Rules

- Keep slices reviewable and small enough to commit independently.
- Update `Progress` before moving to a new slice.
- Run Pants commands sequentially in this repository.
- Prefer Serena for non-trivial Python code navigation when the root is
  supported.
- Keep generated case outputs, submitted code, source zips, PDFs, and private
  notes out of tracked plans.
- For generated artifact workflows, the agent-review rules in `AGENTS.md` and
  the relevant skills still apply; a plan does not waive those gates.

## Lightweight Checks

After creating or materially changing a plan, run:

```bash
git diff --check
scripts/check-private
scripts/check-scripts
```

Run additional checks named in the plan when the touched surface requires them.
