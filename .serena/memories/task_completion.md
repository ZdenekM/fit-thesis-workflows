# Task Completion

- Before closeout for repo/tooling edits, run at least `git status --short --untracked-files=all`, `git diff --check`, `scripts/check-private`, and `scripts/check-scripts` unless the task is explicitly read-only.
- For Python/workflow code changes, run focused Pants gates over changed targets: `pants fmt`, `pants lint`, `pants check`, and focused `pants test` as risk warrants. Serialize Pants invocations.
- When changing deterministic checkers or workflow helpers, run the matching smoke script(s) from `scripts/smoke-*`.
- For larger repo-tooling changes, consider dev-only hygiene from `docs/dev-hygiene.md`: `pants run :vulture`, `pants run :jscpd`, `pants run :omen`.
- For case artifact changes, refresh/validate provenance with manifest and role-coverage commands required by AGENTS.md and the relevant skill.
- Never close a case/workflow task with private data staged into tracked paths; `cases/` must remain ignored except `cases/README.md`.
- If a required tool/role/review wave is unavailable, record the limitation where the workflow expects it and stop before synthesis/commit unless the operator explicitly accepts the scoped limitation.
