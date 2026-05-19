# Suggested Commands

- `git status --short --untracked-files=all` - start/end dirty-worktree and privacy-aware status check.
- `git diff --check` - whitespace/conflict marker check before closeout.
- `scripts/check-private` - verify private case data did not leak into tracked paths.
- `scripts/check-scripts` - validate workflow script surface.
- `pants fmt <targets>` - format Python/shell targets touched by code changes.
- `pants lint <targets>` - lint touched Pants targets.
- `pants check <targets>` - typecheck touched Pants targets.
- `pants test <targets>` - run focused tests for changed behavior.
- `scripts/<smoke-name>` - run the relevant smoke script when changing a deterministic workflow helper or validator.
- `scripts/init-review-manifest --run-checks <case-id> [round-id]`, `scripts/check-agent-coverage <case-id> [round-id]`, and `scripts/check-review-manifest --require-complete <case-id> [round-id]` - case-work closeout when generated/reviewed artifacts are changed.
- `scripts/check-opponent-report --mode canonical <case-id> [round-id]`, `scripts/export-opponent-report <case-id> [round-id]`, and `scripts/check-opponent-report --mode clean <case-id> [round-id]` - opponent-report canonical/clean route.
- `pants run :omen` - repo developer Omen signal using `omen.toml`; intentionally ignores `cases/`.
