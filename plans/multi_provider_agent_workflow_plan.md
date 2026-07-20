# Multi-Provider Agent Workflow Plan

Status: active
Created: 2026-07-20
Revised: 2026-07-20 (after Codex opponentura — verdict `changes_required`, all 8
findings accepted; see Codex Opponentura Log)
Branch: multi-provider-agent-workflow

Endpoint is **both tracks complete**. The canary (B1) is a decision *gate*, not
a scope cut: once one Claude role is proven end-to-end (write boundary,
concurrency, provenance, hooks), B2/B3 are mechanical follow-through.

## Goal

Make the *agent provider* pluggable across this repository, for two distinct
audiences, without weakening privacy, role separation, or review gates:

1. **Repo developer track** — the maintainer works primarily with Claude Code as
   parent/writer, and uses Codex as an independent read-only reviewer / plan
   critic at deliberate checkpoints (the Claude-parent / Codex-reviewer model
   already used in the maintainer's other repos).
2. **End-user (supervisor/opponent) track** — the thesis review pipeline can run
   with Codex agents, with Claude subagents, or with both (one provider
   generates, the other independently reviews), depending on which tools the
   operator has. Today the pipeline is hardwired to a Codex main session
   spawning `.codex/agents/*` sub-reviewers.

Desired end state: the *role* is the durable provider-neutral unit; each
provider is a thin adapter over one shared role-prompt body; the privacy and
independence guarantees hold identically regardless of provider; and every
supported parent→reviewer direction has a defined launch protocol, fail-closed
behavior, and provenance.

## Audit Base

Repo state used for this plan:

- Branch `main`, HEAD `b517f34`, working tree clean except `M .serena/project.yml`.
- Codex CLI present: `codex-cli 0.144.6` at `~/.local/bin/codex`. Codex plugin
  installed under `~/.claude/plugins`.
- No `.claude/` directory yet. The repo is Codex-native.

Key structural findings:

- `AGENTS.md` is the canonical, runtime-neutral instruction file (only 1 "Codex"
  mention). Claude does not import it yet (no `CLAUDE.md`).
- Skills live in provider-neutral `.agents/skills/*/SKILL.md` (19 skills),
  referenced from `AGENTS.md` **by path**, not as a provider-specific surface.
- `src/thesis_review_workflow/agent_profiles.py` is the structured source of
  truth for role routing. `AgentProfileRoute` is already provider-neutral in
  shape (`profile_id`, `sandbox_mode`, `owned_outputs`, `allowed_writes`,
  `required_validators`, review-separation fields) but has **no provider, model,
  or adapter-identity field**. The Codex coupling is that `profile_id` resolves
  through `.codex/config.toml` to a `.codex/agents/<profile>.toml`.
- There are **15** `.codex/agents/*.toml` role adapters (not 16). Each is a thin
  adapter: `description`, `model = "gpt-5.5"`, `model_reasoning_effort`,
  `sandbox_mode`, `approval_policy`, and a `developer_instructions` prose block
  (Role / Goal / Allowed writes / Constraints / Return contract). The *prose
  body* is provider-neutral; the *metadata* (model name, approval policy) is
  Codex-specific.
- `.codex/config.toml` sets `agents.max_threads = 2`, `agents.max_depth = 1`,
  `agents.job_max_runtime_seconds = 3600`.
- `src/thesis_review_workflow/review_pipeline_orchestration.py` produces a
  provider-neutral **role plan** and validates it (records carry
  `agent_profile_id`, not a provider or runner). It does **not** spawn agents —
  spawning is done by the parent session. Wave chunking is **global at 2**.
- `src/thesis_review_workflow/review_approvals.py` enforces reviewer/generator
  independence by **literal agent-name inequality** (`generator_agent ==
  reviewer_agent`, excluding `manual`/`not_recorded`). No provider identity is
  recorded anywhere in manifest/approval/coverage/role-plan records.
- Model/provider assumptions are hardcoded well beyond `.codex/`: **14 skills**
  embed a "pinned to `gpt-5.5`/`xhigh` in the current repo-local Codex profile"
  block, and `src/thesis_review_workflow/review_packets.py` embeds the same
  `gpt-5.5` default model note. Generalizing the end-user track means touching
  these, not only `.codex/`.
- `.codex/hooks.json` + `.codex/hooks/*.py` use the **same hook JSON contract
  Claude Code uses**. Both scripts were exercised with synthetic payloads and
  behave; the schema is compatible for `SessionStart` and `PreToolUse`. But the
  wiring uses `python3 "$(git rev-parse --show-toplevel)/..."` and POSIX
  `shlex`, and only guards the `Bash` matcher.
- `tests/test_agent_profile_contracts.py` and
  `tests/test_workflow_python_contracts.py` enforce exact Codex adapter metadata
  and prompt contents, and that every registry `profile_id` has a tracked
  `.codex/agents/*` config.
- `README.md` is already provider-neutral operator prose (0 "Codex" mentions).

Windows is a supported operator platform (AGENTS.md:12): helpers need a
Python/Pants/PEX or native `.cmd`/`.ps1` surface; native Windows has no process
sandbox and no `git rev-parse` shell-substitution guarantee.

## Verified Provider Mechanics (from opponentura)

- Claude Code project hooks accept the existing hook-output JSON for both
  `SessionStart` and `PreToolUse`. Gaps are **activation, Windows portability,
  and tool coverage**, not the schema.
- Claude Code can spawn **nested** subagents (since v2.1.172, max depth 5).
  Therefore: (a) gate on a minimum Claude version, and (b) reviewer adapters
  must **not** receive the `Agent` tool, or a Claude reviewer could spawn its own
  workers outside the wave schedule.
- Claude tool frontmatter controls *which* tools a subagent has, but does **not**
  scope `Edit`/`Write`/`Bash` to a role's `owned_outputs`. Claude's Bash sandbox
  normally permits writes throughout the working dir, and native Windows has no
  sandbox. So "workspace-write → owned-outputs allowlist" is not a free
  translation; it needs explicit enforcement.
- Claude agent files use YAML frontmatter with Claude model aliases/IDs or
  `inherit`; names cannot be raw underscore profile IDs; `gpt-5.5` is invalid.

## Provider Execution Matrix (MVP)

Only these parent→reviewer directions are supported initially; every other
combination is rejected with a clear message (never a silent no-review):

| Parent (writer/orchestrator) | Reviewer roles | Launch protocol |
|---|---|---|
| Codex | Codex `.codex/agents/*` | existing multi-agent path (unchanged) |
| Claude | Claude `.claude/agents/*` | Claude `Agent` spawn by the parent session |
| Claude | Codex (single bridge) | one mandatory `codex exec` wrapper (dev-track bridge, reused) |
| `both` | generate with parent, review with the other | **sequential**, one coordinator owns both launches |

Not in MVP: Codex parent spawning Claude reviewers; case-level free provider
configuration; four concurrent cross-provider agents. Each supported edge must
define invocation, result transport, timeout, nonzero-exit behavior, and an
"unavailable vs empty-review" distinction, and must have a smoke test before it
is offered to operators.

## Provenance & Independence Contract

Provider identity becomes part of the evidence contract, not just profile
metadata. Role-plan, manifest, and approval records gain at least:
`requested_provider`, `actual_provider`, `adapter_id`, `run_id`. Independence is
then judged on (provider, adapter, run), not only on agent-name string
inequality. For `both`, validators require the expected provider *set* and
reject a missing, substituted, or unverifiable run. This closes the gap where a
substituted second Codex run currently passes the `generator != reviewer` check.

## Concurrency & Nesting

One **global** maximum of 2 live spawned reviewer agents across all providers
(matching the existing global-2 wave chunking and Codex `max_threads=2`); `both`
mode does not become 2-per-provider. Cross-provider generate/review runs
sequentially unless a single coordinator demonstrably enforces the shared
semaphore. Generated reviewer adapters explicitly **disallow the `Agent` tool**.

## Enforcement (privacy & write boundary)

The privacy boundary must not depend on the provider. Design (not a claimed free
translation):

- Read-only roles get no write/shell tools.
- Write-capable roles either (1) use a single controlled output-writing tool and
  omit general `Write`/`Edit`/`Bash`, or (2) rely on a **provider-aware
  `PreToolUse` guard** that intercepts `Edit`/`Write`/`NotebookEdit`/shell and
  resolves the target path against the active role's `owned_outputs`, denying
  writes elsewhere (tracked sources, sibling role outputs, protected `cases/`,
  symlink escapes).
- Hook wiring uses `${CLAUDE_PROJECT_DIR}` + a native/packaged launcher instead
  of `git rev-parse` shell substitution, and capability detection **fails** if
  required hooks are inactive/unapproved rather than declaring the provider
  available.

## Layering (target)

```text
Role contract (durable, provider-neutral)
├── agent_profiles.py           # + provider dimension, adapter identity (no model leak)
├── .agents/skills/<skill>/     # procedure (generalize the 14 "gpt-5.5/Codex profile" blocks)
└── .agents/roles/<role>.md     # NEW: the shared prompt BODY only (Role/Goal/Allowed writes/Constraints/Return)

Provider adapters (thin, explicit metadata per provider)
├── .codex/agents/<role>.toml   # AUTHORITATIVE during MVP; not regenerated yet
└── .claude/agents/<role>.md    # NEW: YAML frontmatter (Claude name/model/tools/permissions) + shared body

Selection + provenance + concurrency + enforcement  (sections above)

Instruction entry points
├── AGENTS.md   (canonical, unchanged in substance)
├── CLAUDE.md   NEW: @AGENTS.md + minimal Claude notes
└── README.md   provider-neutral + short "which tool" note
```

## Scope

In scope: `CLAUDE.md` import; Claude hook wiring; provider dimension +
provenance in the registry/records; a **canary** shared prompt body + one Claude
reviewer adapter with real enforcement smokes; the provider execution matrix and
its supported launch bridges; generalized scheduling/matrix docs and the 14
skill model-notes; contract tests extended to the Claude surface; a single
mandatory dev-track Codex-review command surface; smoke tests for every
supported edge.

Out of scope / deferred: regenerating all 15 `.codex/agents/*.toml` from a
generator (optional future cleanup, not required for pluggability); Codex parent
→ Claude reviewer; native `/`-invocable Claude skill packaging; case-level free
provider config; two writers on one branch; any auto-apply review loop;
unattended push/merge/release/hardware; changing DEEP-only policy.

## Slices

Track A (developer, small, ships independently). Track B (end-user
provider-neutrality) is **canary-first** per opponentura finding 7.

### A1 — Claude developer entry point

Status: done (files; live fresh-session import smoke pending maintainer).
Paths: `CLAUDE.md` (`@AGENTS.md` + minimal notes),
`docs/agent-workflow.md` (both tracks, provider model). Verify: `git diff
--check`, `scripts/check-private`, `scripts/check-scripts`. Smoke: fresh Claude
session lists loaded instructions and confirms the `AGENTS.md` import.

### A2 — Provider-agnostic enforcement wiring for Claude (POSIX)

Status: done. Scope: wire `.claude/settings.json` (SessionStart +
PreToolUse:Bash) to the existing `.codex/hooks/*.py` via `${CLAUDE_PROJECT_DIR}`,
fail **closed** (`|| exit 2`) so an erroring/missing guard blocks rather than
silently allows, and gitignore `.claude/settings.local.json`. Acceptance (met):
synthetic payloads through the *wired command* show deny for `git add
cases/...`, allow (exit 0) for a tracked path, `additionalContext` for
SessionStart, and exit 2 on guard error; `scripts/check-private`,
`scripts/check-scripts`, `git diff --check` pass.

Explicitly deferred out of A2 (named owners, so A2 is honestly complete for its
scope):

- Native-Windows Claude hook launcher (`.cmd`/`.ps1`) → end-user track, since
  Windows is the operator platform (dráha B), not the Linux dev track.
- Live fresh-Claude-session activation smoke (both events) → maintainer to
  confirm on next session; no Claude executable in the review environment.
- Fail-closed *capability detection* when a project hook is untrusted/disabled
  (distinct from the active-guard `|| exit 2` fix) → slice B3.

### A3 — Mandatory dev-track Codex-review command surface

Status: done. Delivered `scripts/agent-review`: one command surface fixing repo
root, working-tree/base target (`--staged`/`--base`), `--ephemeral`,
`--sandbox read-only`, `approval_policy = never`, prompt-template version
(`agent-review/v1`), `--output` artifact, `--timeout`, and nonzero-exit
propagation (exit 3 if `codex` missing — no silent skip). Registered in
`scripts/BUILD` shell_sources as a dev tool, deliberately NOT in
`WORKFLOW_COMMAND_MODULES` and NOT Windows-packaged (operators do not review
repo diffs). Adjudication vocabulary documented in `docs/agent-workflow.md`.
Smoke = dogfood: this slice was itself reviewed via `scripts/agent-review
--staged`. Paths: `scripts/agent-review`, `scripts/BUILD`,
`docs/agent-workflow.md`, `CLAUDE.md`.

### B0 — Registry provider dimension (declarative; no execution)

Status: planned. Scope reduced from the original bundle: add only the
declarative provider dimension the canary needs, and defer the provenance-record
schema + gate rewire to B3 (below), where execution actually populates provider
identity. Rationale: adding `requested/actual_provider`/`adapter_id`/`run_id` to
the safety-critical review-approval/manifest gate *now* would create dormant,
unexercised schema fields on the most sensitive path; sequencing them to where
they are produced is safer and testable.

Paths: `agent_profiles.py` (add a `providers: tuple[str, ...]` field per route,
default `("codex",)`, plus a `SUPPORTED_PROVIDERS` constant and a
claude-capable lookup — no model value leaked into the neutral layer);
`tests/test_agent_profile_contracts.py` (assert every `profile` route lists a
non-empty provider set ⊆ supported and currently includes `codex`; and — the
drift guard for B1 — any route listing `claude` MUST have a matching
`.claude/agents/<role>.md`). No role lists `claude` until B1 adds its adapter.
Verify: `pants test tests/test_agent_profile_contracts.py
tests/test_workflow_python_contracts.py`, `pants check`, `git diff --check`.

### B0-provenance (folded into B3) — provider identity in review records

The opponentura F2 provenance contract (`requested_provider`,
`actual_provider`, `adapter_id`, `run_id` in `generated_record` /
`build_review_approval_payload`, and a provider-aware independence gate) lands in
B3, when provider selection/execution actually writes those fields. Until then
the existing name-based independence gate stays in force (it never gets weaker).

### B1 — Single-role canary (the gate for everything after)

Status: planned. Pick one role (e.g. `thesis_code_quality_reviewer`). Steps:
(1) extract its prompt BODY to `.agents/roles/<role>.md`; (2) add a test
asserting the existing `.codex/agents/<role>.toml` `developer_instructions`
equals the fragment (Codex TOMLs stay authoritative, unchanged); (3) hand-write
one `.claude/agents/<role>.md` with valid Claude frontmatter (Claude name, model
tier or `inherit`, tools with **no `Agent`**, permissions), body = fragment;
(4) run real Claude smokes: write to owned output (allowed), sibling output /
tracked source / protected `cases/` path / shell redirection / symlink traversal
(all denied). Independent-review separation for the canary uses the **existing
name-based gate** (the code-quality role is an evidence-producer reviewed by a
different agent) — provider-aware provenance (F2) is *not* required here and
lands in B3, so the canary stays focused on the write-boundary/concurrency/hook
unknowns. Only expand to remaining roles after this passes. Verify: the smoke
matrix above + `pants test` + `scripts/check-private`.

### B2 — Roll out remaining Claude reviewer adapters

Status: planned. Repeat B1's proven pattern for the other spawnable roles;
generalize the 14 skill "Model And Reasoning" blocks and
`review_packets.py` model note to "strongest model of the active provider" with
per-provider pins. Update `docs/agent-profile-matrix.md` (Claude adapter column).
Verify: contract tests, `pants test tests::`, `scripts/check-scripts`.

### B3 — Provider selection, capability detection, scheduling docs

Status: planned. Implement the Provider Execution Matrix selection + capability
detection (fail-closed), the global-2 concurrency rule across providers, and the
`both` sequential cross-provider pattern. **Also owns the folded-in provenance
work**: add `requested_provider`/`actual_provider`/`adapter_id`/`run_id` to
`generated_record` / `build_review_approval_payload` and make the independence
gate provider-aware (reject substitution; require the provider set for `both`),
now that execution populates those fields. Generalize `docs/agent-scheduling.md`
("main session (Codex or Claude)"), README "which tool" note, min-Claude-version
gate. Optional readiness `scripts/check-*`. Verify: two-role synthetic wave under
`provider=claude`, then `provider=both`; confirm global-2, independence +
provenance, and clear failure when a provider is unavailable.

### B4 (optional, deferred) — Generator that also renders `.codex/*.toml`

Only if churn is justified after the Claude surface is proven. Until then Codex
TOMLs remain hand-authoritative.

## Progress

- 2026-07-20: Plan created, then revised after Codex read-only opponentura
  (verdict `changes_required`). All 8 findings accepted; three factual claims
  independently verified (15 not 16 TOMLs; orchestration records
  `agent_profile_id` with no provider/runner and does not spawn; independence is
  literal name inequality in `review_approvals.py`).
- 2026-07-20: Implementation started on branch `multi-provider-agent-workflow`.
  A1 files added (`CLAUDE.md` importing `AGENTS.md`, `docs/agent-workflow.md`).
  Lightweight checks passed (`git diff --check`, `scripts/check-private`,
  `scripts/check-scripts`). Codex slice-review of A1 returned `changes_required`
  (2×P1, 3×P2), all overclaiming/wording: docs described A2/A3/B capabilities in
  present tense and used "spawned reviewer agents" instead of the contract's
  "spawned workflow agents". All accepted and fixed; import syntax, no
  duplication, and scope were confirmed clean. Live fresh-Claude-session import
  smoke is left for the maintainer to confirm (no Claude executable in the
  review environment).
- 2026-07-20: A2 wired `.claude/settings.json` (SessionStart + PreToolUse:Bash)
  to the existing `.codex/hooks/*.py` scripts using `${CLAUDE_PROJECT_DIR}`
  (F6). `.claude/settings.local.json` gitignored. Smoke verified the *decision*,
  not just JSON output: the wired PreToolUse command denies `git add cases/...`,
  allows `git add CLAUDE.md` (exit 0), and SessionStart emits `additionalContext`.
  Native-Windows launcher, live-session hook activation, and fail-closed
  capability detection recorded as open limitations (B3 / end-user track). The
  broader Edit/Write/shell write-boundary guard remains F3/B1.
- 2026-07-20: Codex slice-review of A2 returned `changes_required` (1×P1, 1×P2).
  P1 (accepted, security): the PreToolUse guard failed *open* on runtime error
  (Claude Code treats PreToolUse exit codes other than 2 as non-blocking), so a
  missing `python3` or a guard exception would silently allow `git add
  cases/...`. Fixed by appending `|| exit 2` to the wired command; verified
  malformed stdin → exit 2 while deny/allow still exit 0. P2 (accepted): A2 was
  marked done while its text still listed Windows/live-session as pending —
  rescoped A2 to POSIX wiring + fail-closed and moved the rest to named owners.
  Schema, matchers, `${CLAUDE_PROJECT_DIR}`, unchanged Codex setup, and
  shared/local split were confirmed correct.

- 2026-07-20: A3 delivered `scripts/agent-review` and was reviewed by dogfood
  (`scripts/agent-review --staged` reviewing itself), which also proves the
  bridge works. Codex returned `changes_required` (1×P1, 3×P2, 1×P3), all
  accepted: (P1) exit 0 didn't prove a review existed → now captures `-o` to a
  temp file and fails closed (exit 4) unless non-empty with a verdict; (P2)
  ambient stdin could alter/stall the prompt → run with `</dev/null`; (P2) a
  Linux-only script was presented as unconditionally mandatory → scoped as a
  POSIX dev helper with the plugin / documented `codex exec` as the Windows
  path (contract stays mandatory, the script does not); (P2) `--timeout 0`
  disabled the timeout → validated as a positive integer; (P3) "cannot modify
  the working tree" was false for `--output` → wording clarified.
- 2026-07-20: Round-2 dogfood confirmed the stdin/timeout/failure-propagation
  fixes and found one more P1: the fail-closed grep was too permissive
  ("Verdict: inconclusive" or a stray "tests pass" would satisfy the gate).
  Fixed: the prompt now requires an explicit final `Verdict: <value>` line, and
  the validator requires the allowed token tied to the `verdict` label
  (markdown-tolerant). Self-verified deterministically over 7 cases (valid incl.
  markdown pass; inconclusive/tests-pass/no-verdict/empty fail closed); the
  two-round cross-provider ceiling was reached, so this last tiny fix was
  validated locally rather than with a third Codex round.

- 2026-07-20: B0 scope split (see slice notes): implemented only the
  declarative provider dimension. Added `Provider`/`SUPPORTED_PROVIDERS` and a
  `providers` field (default `("codex",)`) to `AgentProfileRoute`/`_route`, plus
  `providers_for_profile` and `claude_capable_profile_ids` helpers. Three new
  contract tests: valid provider sets (codex-capable, ⊆ supported), the
  canary drift guard (a `claude` route requires `.claude/agents/<role>.md`), and
  the lookup helper. No role lists `claude` yet. The provenance-record schema +
  provider-aware independence gate (F2) were deferred to B3 to avoid dormant,
  unexercised fields on the safety-critical review gate. Green: the two contract
  tests, `test_agent_coverage.py`, `pants check/lint/fmt` on the touched files.
- 2026-07-20: Codex review of B0 (`changes_required`, 1×P1, 1×P2, 1×P3), all
  accepted. P1: B1's acceptance still named provenance, contradicting the
  B0→B3 provenance split → reworded B1 to use the existing name-based
  independence gate for the canary (provenance stays in B3). P2: non-`profile`
  routes inherited `providers=("codex",)` → `_route` now forces `()` for
  non-profile routes, with a new invariant test. P3: stale docs status row and
  opponentura F2 line → split/corrected. Codex explicitly cleared the
  dataclass-construction compat, the missing-adapter drift guard, and the
  underscore→hyphen basename convention.

## Decision Log

- 2026-07-20: The *role* is the durable unit; providers are thin adapters over
  one shared prompt BODY. Reject hand-maintained parallel prompt files and a
  large new orchestration framework.
- 2026-07-20: Reuse the existing hook scripts for Claude, but wire them with
  `${CLAUDE_PROJECT_DIR}` + native launcher and make capability detection
  fail-closed (opponentura F6).
- 2026-07-20: Canary-first (F7): keep all 15 `.codex/agents/*.toml`
  authoritative and unchanged during MVP; prove one Claude role end-to-end
  before rollout; a dual-format generator is optional future cleanup, not
  required for pluggability.
- 2026-07-20: One global max of 2 spawned agents across providers; reviewer
  adapters disallow the `Agent` tool; `both` runs sequentially (F5).
- 2026-07-20: Provider identity enters the evidence contract; independence is
  judged on provider+adapter+run, not agent-name strings (F2).
- 2026-07-20: Claude write boundary is enforced explicitly (controlled write
  tool or provider-aware PreToolUse guard), not assumed from tool frontmatter
  (F3).

## Decisions Needing Operator Input

1. Build ambition: DECIDED — do both tracks fully, but sequence A1–A3 + B0 + B1
   as a de-risking gate, then finish B2 + B3 as mechanical follow-through.
2. Claude write-boundary mechanism: controlled single write tool vs
   provider-aware PreToolUse guard (F3). Recommend the guard — it reuses the
   existing hook pattern and covers shell/symlink escapes.
3. Whether `both` cross-provider review is default for high-risk end-user
   artifacts or explicit opt-in.
4. Confirm the maintainer's other-repo model = Claude parent + Codex stop-time
   review gate, so the dev track (A3) matches it.

## Codex Opponentura Log

- 2026-07-20, read-only `codex exec` plan critique. Verdict `changes_required`,
  0×P0, 7×P1, 1×P2, made no file changes. Findings and adjudication:
  - F1 provider execution matrix undefined — **accepted** → added Provider
    Execution Matrix (MVP).
  - F2 provenance can't prove provider — **accepted** (verified) → Provenance &
    Independence Contract; provenance-record schema + provider-aware gate land
    in B3 (where execution populates provider identity), not B0.
  - F3 sandbox translation not enforceable — **accepted** → Enforcement section,
    B1 smoke matrix.
  - F4 adapter metadata not 1:1; 15 not 16 TOMLs — **accepted** (verified) →
    share prompt body only; explicit per-provider metadata; count corrected.
  - F5 concurrency/nesting violates global contract — **accepted** (verified) →
    Concurrency & Nesting section; disallow `Agent` tool; global-2.
  - F6 hook install not portable/sufficient — **accepted** → `${CLAUDE_PROJECT_DIR}`,
    native launcher, real session smokes, Windows check, fail-closed detection.
  - F7 generator sequencing exposes all Codex adapters first — **accepted** →
    re-sequenced to canary-first (B1); TOMLs stay authoritative; generator
    deferred to optional B4.
  - F8 (P2) dev bridge optional where it must be contractual — **accepted** →
    A3 is now one mandatory command surface with a full contract.
- Raw output preserved (untrusted artifact, not executed) in the session
  scratchpad; no commands emitted by the reviewer were run.

## Final Audit

Not run yet. Implementation in progress on `multi-provider-agent-workflow`
(canary-first: A1–A3 + B0 + B1, then B2 + B3). Per-slice Codex reviews are
recorded in Progress. Operator decisions #2–#4 are still open but do not block
A1–A3.
