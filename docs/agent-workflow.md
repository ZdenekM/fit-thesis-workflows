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

The review *contract* is mandatory; `scripts/agent-review` is its POSIX
implementation (a Linux/dev maintainer tool; not part of the operator workflow
command surface and not packaged for Windows). On native Windows, a maintainer
uses the Codex plugin or invokes `codex exec` directly with the same posture.
The script runs Codex non-interactively with that fixed posture — repository
root, an explicit working-tree/base target, `--ephemeral`, `--sandbox
read-only`, `approval_policy = never`, a prompt-template version
(`agent-review/v1`), an optional `--output` artifact, a `--timeout`, and
nonzero-exit propagation (it exits non-zero rather than silently skipping if
`codex` is missing).

```bash
scripts/agent-review --staged                 # review staged changes
scripts/agent-review --base main               # review this branch vs main
scripts/agent-review --profile plan-critic plans/foo_plan.md   # extra focus text
```

Prefer this over ad-hoc `codex exec` so reviews share one target/sandbox/approval
contract. A plugin or IDE integration should call this surface rather than
becoming a second implementation.

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
  write-boundary guard for reviewer subagents (F3) lands with the canary (B1),
  below.

### Reviewer write boundary (B1)

`.claude/hooks/pre_tool_use_write_guard.py` is the authoritative reviewer
sandbox for Claude — it enforces the boundary Codex expresses via a role-scoped
`workspace-write` sandbox, and holds even if a shadowing same-name adapter
granted extra tools. It:

- acts **only** on spawned subagents, detected by the presence of `agent_id`
  (not `agent_type`, which `claude --agent` also sets on the main session), so
  the parent/main session and its normal edits are never constrained;
- applies only when the subagent's `agent_type` matches a reviewer role in
  `.claude/hooks/reviewer_write_policy.json`, which a contract test keeps in sync
  with the profile registry's `allowed_writes`;
- for a matched reviewer: allows `Read`/`Grep`/`Glob`; allows
  `Write`/`Edit`/`NotebookEdit` **only** to that role's exact owned outputs under
  `cases/<id>/rounds/<round>/` (siblings, other roles' outputs, `work/` records,
  tracked files, out-of-repo paths, and `..`/symlink escapes are denied); and
  denies every other tool (`Bash`, `Task`, `WebFetch`, ...) as a backstop to the
  adapter's own `tools` allowlist;
- fails closed: unparseable input, an unreadable policy, or a path-less write all
  deny, and the wiring adds `|| exit 2`.

**Platform:** these hooks call `python3` under a POSIX shell, so the Claude
reviewer path is Linux/macOS-only for now. On native Windows the `|| exit 2`
fail-closed rule would block the parent's own writes when `python3` is absent, so
Windows operators use the Codex path until the packaged native launcher lands
(end-user track / B3). Do not wire these hooks on native Windows yet.

**Model:** reviewer adapters set a strong model and high effort as their
*default* (`model: opus`, `effort: xhigh`) rather than `inherit`, mirroring the
Codex `gpt-5.5`/`xhigh` pin. Note this is the frontmatter default only —
environment (`CLAUDE_CODE_SUBAGENT_MODEL`) or per-invocation selection can
override it, so B3 validates the *effective* launched model/effort before
treating a Claude pass as a semantic review.

## Implementation status

This model is being rolled out incrementally under
`plans/multi_provider_agent_workflow_plan.md`.

| Capability | Status |
|---|---|
| `CLAUDE.md` importing `AGENTS.md` | files landed; live fresh-session import smoke to be confirmed by the maintainer |
| This document | landed |
| Provider-neutral privacy/session hooks wired for Claude (`.claude/settings.json`) | landed on POSIX; live-session confirmation + native-Windows launcher pending |
| Single mandatory Codex-review command surface (`scripts/agent-review`) | landed |
| Provider *dimension* in the role registry (declarative) | landed (slice B0) |
| Provider *provenance* in review records + provider-aware independence gate | planned (slice B3) |
| First Claude reviewer adapter + write-boundary guard (canary: `thesis-code-quality-reviewer`) | landed; live subagent write-boundary smoke pending maintainer |
| Remaining Claude reviewer adapters + skill model-note generalization | planned (slice B2) |
| Provider selection, capability detection, scheduling docs | planned (slice B3) |

Until a capability is marked landed, the repository runs on the existing
Codex-native path. Do not assume a planned capability is active.
