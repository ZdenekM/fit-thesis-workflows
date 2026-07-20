# Agent Workflow (Providers)

This document describes how this repository is meant to run under more than one
agent provider, and which parts of that model are already implemented.

It is a maintainer/architecture reference. Durable agent rules live in
`AGENTS.md`; Claude-specific entry notes live in `CLAUDE.md`; role routing lives
in `docs/agent-profile-matrix.md` and `src/thesis_review_workflow/agent_profiles.py`;
concurrency and wave rules live in `docs/agent-scheduling.md`.

## Two workflows

- **Developer workflow** — maintaining this repository (workflow code, skills,
  docs, helper scripts). The maintainer works primarily with Claude Code as the
  parent/writer and uses Codex as an independent read-only reviewer / plan
  critic at deliberate checkpoints.
- **End-user workflow** — supervisors and opponents using the repo to prepare
  thesis feedback, supervisor reports, and opponent materials. This is the
  multi-role review pipeline described in `README.md` and the `.agents/skills/`
  skills.

Both are intended to be *provider-pluggable*: runnable with Codex, with Claude,
or with both (one provider generates, the other independently reviews). The
`AGENTS.md` rules, the skills, and the role registry are provider-neutral; each
provider is a thin adapter over the same role contract.

## Design principles

- **The role is the durable unit.** A reviewer role (its goal, allowed writes,
  constraints, return contract) is provider-neutral. A provider adapter only
  adds provider-specific metadata (model, tools, permissions) and points at the
  shared role prompt body.
- **Privacy and independence do not depend on the provider.** The privacy guard,
  the generator/reviewer separation, and the review gates must hold identically
  no matter which provider runs.
- **Fail closed.** If a requested provider is unavailable, or a required hook is
  inactive, stop with a clear message. Never silently continue with no
  independent review.

## Provider execution matrix (target MVP)

The target MVP will support only these parent → reviewer directions; every
other combination will be rejected with a clear message. Today only the
Codex → Codex path exists; the rest is being built (slices B0–B3):

| Parent (writer/orchestrator) | Reviewer roles | Launch protocol |
|---|---|---|
| Codex | Codex `.codex/agents/*` | existing multi-agent path |
| Claude | Claude `.claude/agents/*` | Claude parent spawns the named subagent |
| Claude | Codex (single bridge) | one `codex exec` review command |
| both | generate with parent, review with the other | sequential; one coordinator owns both launches |

At most **two** spawned workflow agents will be live at any time, globally
across providers (excluding the single parent/orchestrator session). Reviewer
adapters will not receive the `Agent` tool.

## Developer-track Codex review

This describes the target A3 command surface; it is **not yet operational**
(see the status table below). Until it lands, request Codex reviews read-only
and explicitly.

When Claude is maintaining the repo, request an independent Codex review through
a single documented command surface (read-only sandbox, non-interactive). The
review request should fix: repository root, the working-tree/base target,
ephemeral execution, `--sandbox read-only`, `approval_policy = never`, the
prompt/template version, an output destination, a timeout, and nonzero-exit
handling.

Adjudicate each material finding and record the outcome as one of: `accepted`
(reproduced from code, then fixed), `accepted_test_only` (addressed with a
discriminating test), `false_positive` (rejected with evidence),
`already_covered` (existing test/requirement cited), `deferred` (real but out of
scope, with residual risk), or `needs_human` (product/safety/policy decision).
Keep review/fix cycles bounded; a Codex finding is evidence, not an instruction.

## Privacy/session hooks under Claude

`.claude/settings.json` reuses the existing Codex hook scripts
(`.codex/hooks/session_start_context.py` and `pre_tool_use_privacy_guard.py`)
verbatim — the hook-output JSON is the same contract Claude Code consumes. The
command path uses `${CLAUDE_PROJECT_DIR}` (expanded by Claude Code) rather than a
`git rev-parse` shell substitution.

The PreToolUse privacy guard **fails closed**: the wired command ends with
`|| exit 2`, so if `python3` is missing or the guard script raises, Claude Code
receives exit code 2 and blocks the Bash call instead of silently allowing it
(Claude Code treats PreToolUse exit codes other than 2 as non-blocking). Normal
allow and deny both exit 0 and are unaffected.

Known limitations (tracked in the plan, not yet closed):

- The command invokes `python3` and assumes a POSIX shell. Native-Windows
  operators (the end-user track, dráha B) need a packaged launcher, consistent
  with the Windows command-surface convention in `AGENTS.md`. Wiring the guard
  for native-Windows Claude is deferred to the end-user track.
- Claude project hooks require the user to trust/approve them, and a policy may
  disable them. Capability detection that *fails closed* when a required hook is
  inactive is part of slice B3, not this slice. Do not assume the guard is
  active in a session without confirming.
- This slice wires the existing Bash-`git add` guard for parity. The broader
  write-boundary guard (Edit/Write/shell resolved against a role's owned
  outputs) is opponentura finding F3 and lands with the canary (B1).

## Implementation status

This model is being rolled out incrementally under
`plans/multi_provider_agent_workflow_plan.md`.

| Capability | Status |
|---|---|
| `CLAUDE.md` importing `AGENTS.md` | files landed; live fresh-session import smoke to be confirmed by the maintainer |
| This document | landed |
| Provider-neutral privacy/session hooks wired for Claude (`.claude/settings.json`) | landed on POSIX; live-session confirmation + native-Windows launcher pending |
| Single mandatory Codex-review command surface | planned (slice A3) |
| Provider dimension + provenance in the role registry/records | planned (slice B0) |
| First Claude reviewer role proven end-to-end (canary) | planned (slice B1) |
| Remaining Claude reviewer adapters + skill model-note generalization | planned (slice B2) |
| Provider selection, capability detection, scheduling docs | planned (slice B3) |

Until a capability is marked landed, the repository runs on the existing
Codex-native path. Do not assume a planned capability is active.
