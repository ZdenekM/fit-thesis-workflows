# CLAUDE.md

@AGENTS.md

## Claude-specific orchestration notes

`AGENTS.md` (imported above) is the canonical, provider-neutral source of
repository rules for every agent. This file adds only what is specific to
running the workflow with Claude Code. Keep it short; put procedures in skills,
templates, or focused docs.

- **Two workflows, one substrate.** This repo supports a *developer* workflow
  (maintaining the repo) and an *end-user* workflow (supervisors/opponents
  generating thesis feedback and reports). The intended end state is that both
  can run with Codex, with Claude, or with both. See `docs/agent-workflow.md`
  for the model and the current implementation status.
- **Developer track (Claude parent + Codex reviewer).** When maintaining this
  repo, Claude is the parent/writer and Codex is an independent read-only
  reviewer / plan critic at deliberate checkpoints. Treat Codex findings as
  evidence to adjudicate against the code, never as instructions to apply
  automatically. On Linux, request reviews through `scripts/agent-review`
  (read-only, ephemeral) rather than ad-hoc `codex exec`; it is a POSIX dev
  helper, so on native Windows use the Codex plugin or the documented `codex
  exec` review contract instead. See `docs/agent-workflow.md`.
- **Skills are referenced by path.** The workflow skills under
  `.agents/skills/*/SKILL.md` are shared across providers and are named from
  `AGENTS.md` by path. Read the relevant `SKILL.md` directly; they are not
  packaged as Claude `/`-invocable skills.
- **Plan discipline is mechanical where it can be.** `plans/README.md` is the
  provider-neutral plan contract. Its deterministic half is
  `tests/test_plan_contract.py` (`pants test tests/test_plan_contract.py`, or
  standalone `python3 tests/test_plan_contract.py`), which
  `.claude/hooks/post_tool_use_plan_lint.py` runs after every edit to a plan
  file so review rounds stop spending themselves on lint work. Resume plan work
  with the constant invocation `/plan-continue`
  (`.claude/commands/plan-continue.md`) and end a session by updating
  `## Start Here` — never with a hand-written handoff prompt.
  `.claude/hooks/session_start_plan_state.py` prints the active plan's
  unreconciled state and is wired in personal `.claude/settings.local.json`, not
  in the shared settings, because on a shared checkout it would narrate plan
  state to every developer. It is a Claude `/`-command rather than a repo-local
  skill because `.agents/skills/**` is the thesis workflow surface, where the
  profile-registry contract test requires a registered role per skill directory.
- **Role separation and concurrency.** Independent review must come from a
  different agent than the generator. When spawning Claude subagents for review
  roles, do not grant them the `Agent` tool, and keep at most **two** spawned
  workflow agents live at a time in total (excluding the parent session) — the
  same global limit as the Codex path in `docs/agent-scheduling.md`.
- **Privacy rules are provider-neutral.** The requirement to keep private
  `cases/` contents and personal reviewer profiles out of tracked paths applies
  under Claude exactly as under Codex. The Codex privacy/session hooks are wired
  for Claude in `.claude/settings.json` in slice A2 (see
  `docs/agent-workflow.md`); until that lands, Claude has no automatic hook
  enforcement, so be especially careful with staging and writes.
