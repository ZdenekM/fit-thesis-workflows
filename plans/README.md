# Plans

This directory holds file-based execution plans for non-trivial workflow and
tooling changes in this repository.

Plans are not a replacement for `TODO.md`. `TODO.md` is the durable open-work
index. A plan is the current execution contract for one larger change that needs
scope, sequencing, verification, and resume context.

A plan is a working surface, not a ledger. Text that only records history
belongs in the archive; text that governs pending work must stay small enough
that staleness is visible and re-review is cheap. The rules below were adopted
2026-08-20 after a sibling repository running this same plan contract let one
active plan reach 5,040 lines and then spent four consecutive review rounds
correcting defects in the plan's own prose while the cheapest
information-producing action stayed unscheduled behind them. Each rule keeps its
measured reason, because rules without a reason are the first to be relaxed.

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
- Per-plan compaction artifacts: `plans/archive/<plan_stem>/` — closed slice
  charters, relocated `## Decision Log` entries, retained inventories
- Planning contract: `plans/README.md`
- Mechanical gate: `tests/test_plan_contract.py`

Move a completed or superseded plan to `plans/archive/` after its final audit is
recorded and any residual work is either closed or copied into `TODO.md`.

A generic `plans/PLAN.md` is not accepted. The gate discovers plans as
`plans/*_plan.md`, so a plan named outside that pattern would silently escape
every check below.

## Plan Shape

Each active plan contains, in this order:

- `# <Plan Title>` on the first line, then a `Status:` line — one of `planned`,
  `in_progress`, `blocked`, `done`, `superseded` — and an optional `Created:`
  line. `in_progress` replaces the earlier `active` spelling: the tracked plans,
  the gate, and the session-start hook all read `in_progress`.
- `## Start Here` — required while `Status: in_progress` (see below)
- `## Goal`: one concrete outcome
- `## Audit Base`: current findings, exact commands, relevant paths, constraints
- `## Scope`: what the plan will and will not touch, non-goals included
- `## Acceptance Contract`: only when the plan gates an irreversible or
  outward-facing action, and then between `## Scope` and `## Progress` — see
  `## Acceptance Contract Rules`
- `## Slices`: commit-sized steps, per `## Slice Charters`
- `## Progress`: current slice state, updated as work proceeds
- `## Decision Log`: meaningful sequencing or scope decisions
- `## Final Audit`: commands run, skipped checks, residual risks, archive
  decision

Additional `## ` sections between the required ones are fine — several plans
carry a conceptual contract, a proposed artifact shape, or residual risks — as
long as the required headings stay present and in this order.

Use exact paths and commands. Avoid placeholder tokens in active plans. If a
path is dynamic, record the command that resolves it.

## Start Here

`## Start Here` is the only orientation a fresh session should need before the
active slice. At most ~10 lines: the current state in one or two sentences, the
exact next action, and what a resuming session must NOT read, because closed
history lives in the archive.

Why: fresh sessions were burning their context reading a plan's whole history
before touching the active slice, and the plan already contained the two
sentences that would have replaced that reading.

## Slice Charters

A full `### Slice <id> - <Title>` charter uses this label set, one label per
line, as a bullet or a plain line — both dialects exist in this tree:

- `Status:` — `planned` (legacy synonym: `pending`), `in_progress`, `blocked`,
  `done`
- `Proposed commit message:`
- `Why:` — why this slice exists at all
- `Expected paths:` — exact files or explicit globs
- `Tasks:` — concrete edits, not themes such as "refactor the pipeline"
  (existing synonym in this tree: `Work:`)
- `Out of scope:` — the boundary this slice must not absorb
- `Verification:` — exact commands, conditional ones written with their trigger

Slice charters in the plans that predate this contract revision are
grandfathered by the gate with a per-plan record of exactly which labels they may
omit; every other rule here applies to them unchanged. A new plan gets no
exemption.

Further rules:

- Do not mark a slice `done` until its verification ran and the review
  obligations of `AGENTS.md` and the relevant skill are discharged. These are
  separate: a green verification block does not discharge a review.
- Before marking a slice `done`, bring its `Expected paths:`, `Tasks:`, and
  `Verification:` to the scope that actually landed. A slice may not close
  against commands written for work it no longer matches.
- If a slice is dropped, merged, or superseded, record that in `## Decision Log`
  in the same session.
- Scope a slice from measurement, not from reading. Why: every enumeration
  derived by reading a tree has been proved incomplete by the next review round.
- Do not state an enumeration's count as a contract in plan prose. If a slice
  must close a class, the authority is a mechanical check the slice delivers, and
  the plan's list is a starting set explicitly marked as not closed. Why: one
  class was believed complete at two, four, three, four and five instances in
  succession, each time by an instrument that had just been fixed.

## Charter Tiers And Compaction

- **Two charter tiers.** Only the slice being executed and the next slice may
  carry a full charter. Every later slice is a STUB: the `### Slice <id>`
  heading, a line `Charter form: stub`, an objective of at most ~3 lines, the
  boundary it must not absorb, and a pointer to what it serves — at most 12
  lines in total. The full charter is written just-in-time when the slice becomes
  next, and reviewed once before implementation. Why: detailed far-future
  charters are the text intervening work stales most often, and each staleness
  buys a review round.
- **Closed slices compact.** When a slice is marked `done`, first bring its
  charter to what actually landed, then — no later than the start of the next
  slice — move that full charter verbatim to
  `plans/archive/<plan_stem>/closed-slices-<date>.md` (append-only) and replace
  it inline with a COMPACTED record: the same heading, a line
  `Charter form: compacted`, a `Landed:` line with the commits, a one-line
  summary of what landed, and pointers to its `## Decision Log` entries. Keep the
  heading so existing references still resolve.
- **Decision Log relocation.** Entries that cover neither the current nor the
  immediately preceding slice may move verbatim to
  `plans/archive/<plan_stem>/decision-log-<range>.md`, each leaving a one-line
  summary plus the archive pointer inline. Relocation is content-preserving:
  nothing is re-adjudicated and nothing is reworded.
- **Size budget.** Target at most ~1,500 lines for a live plan. The gate
  enforces a per-plan line ratchet with deliberate headroom; lower a budget
  whenever compaction shrinks a plan, and raise one only with a
  `## Decision Log` entry saying why. A plan over its budget blocks starting a
  new slice until it is compacted.
- **Decision Log entry size.** An entry is the trigger, one line per adjudicated
  finding with its evidence pointer, the decision with its one-line why, and any
  residual risk. The gate caps an entry at 20 lines. Cite evidence that already
  lives in the repository — a path, a `path::symbol`, a test name, a commit, a
  helper command — instead of copying it inline. Why: in the sibling repository
  62% of one plan's lines were Decision Log, most of it evidence that already
  existed elsewhere in the tree.
- The one exception is the entry that gates an irreversible or outward-facing
  action (see `## Acceptance Contract Rules`): it may carry its full evidence
  inline, because that is the one place auditability outranks size. Its first
  line must contain `pre-send` or `pre-spend` so the gate can recognize it, and
  the gate allows at most one such entry per plan.

## Citation Discipline In Living Text

Everywhere outside `## Decision Log`, cite code as `path::symbol`, by exact test
name, or by logical workflow command name — never as `path:line`. Line anchors
are valid inside `## Decision Log` entries and archived artifacts, because both
are dated records against a stated tree.

Why: one plan's review rounds regenerated line-anchor drift findings every
round, because a single ~500-line insert re-anchored every citation below it.

The gate enforces this as a per-plan ratchet on line anchors in unfenced text
outside `## Decision Log`. New anchors in living text fail; removing anchors lets
the baseline drop.

## Plan-Change Review

A plan is an artifact that can be wrong on its own, independently of any code, so
plan text gets reviewed as plan text.

- **A new or materially rewritten slice charter is reviewed before its
  implementation starts** — not the code: is it scoped correctly, is its
  enumeration complete, are its stop conditions the right ones, is it sufficient
  for whatever it gates. Why: reviewing a charter costs one round, while
  reviewing an implementation that turns out to be the wrong shape costs a round
  plus a rewrite.
- **Prefer one design review before implementation over another defect review
  after it, at least once per plan.** Why: defect reviews read a diff and find
  instances, design reviews read the decisions and find scope errors, and a plan
  whose every round is a post-implementation defect review keeps discovering one
  more prerequisite per round.
- **Triage every accepted finding before it buys process.** Classify it as (a)
  protecting an irreversible or outward-facing action, (b) changing what gets
  built, or (c) plan-prose hygiene — citations, wording, structure, numbering.
  Only (a) and (b) can buy another round or a re-check; class (c) is fixed in the
  same commit. Why: one plan's review chains escalated on prose defects for a
  week, each round individually correct and the sum a circle.
- **Stopping rule.** A charter or amendment review chain is ONE round plus ONE
  narrow re-check, and the re-check is owed only when the fix batch contains
  class (a)/(b) findings. If that re-check still finds blocking (a)/(b)
  findings, the object is too big to review: SHRINK it — cut scope into its own
  slice, cut prose into pointers — instead of buying a third round. A third round
  on the same object needs the direction check below in writing plus explicit
  user approval. Why: four consecutive rounds each found real defects in what the
  previous round had produced, including a corrected enumeration that was itself
  wrong.
- **A fix written in response to a review is itself unreviewed.** Scope the
  narrow re-check to the last fix only, and forbid re-litigating adjudicated
  decisions in its prompt.
- **A slice splitting under review is a direction signal, not only a scoping
  fix.** Before the new charters are written, answer in `## Decision Log`: (i)
  what does the action this work gates actually need, (ii) would deleting the
  requirement be cheaper than satisfying it, (iii) what is the cheapest action
  that would produce new information. Why: two slices in one plan fissioned under
  review while the cheapest information-producing action — a free end-to-end
  probe — stayed unscheduled behind them.
- **Two corrections end prose authority.** An enumeration or measurement
  corrected twice in plan prose is not corrected a third time: either the
  mechanical instrument is built immediately and the prose demoted to a pointer
  at it, or the requirement is dropped.
- **Findings land as instruments, not prose.** The preferred fix for an accepted
  finding is, in order: a test or deterministic check; a code change; a one-line
  pointer in the plan. Amending plan prose is the last resort, because every
  amended paragraph is new unreviewed text that buys the next round.
- **Closure checks re-run over the whole artifact after every fix batch.** Why: a
  fix batch re-anchors and re-states text beyond the lines it touched, and one
  artifact's citations were corrected and re-broken repeatedly in a single
  session by batches that swept only the rows they had touched.
- Record each plan-change review in `## Decision Log` on the same terms as any
  other round: every finding adjudicated, and the reviewer treated as evidence to
  verify rather than instructions to apply.

## Acceptance Contract Rules

An `## Acceptance Contract` gates an action this repository cannot take back:
sending student-facing feedback, confirming a supervisor report for FIT IS,
submitting an opponent report, or a paid external provider run. Routine local
work — Pants runs, checkers, smoke scripts — is explicitly not in this class.

Why: one contract written before the architecture it gated existed accumulated
criteria whose evidence the runtime was never designed to produce, and four
consecutive rounds each found another unproducible reading and answered it by
chartering more evidence plumbing instead of re-deriving the contract.

- **Gate only what the gated action uniquely tests.** A criterion decidable
  deterministically belongs in the test suite or an existing checker command, not
  in the live contract.
- **Few and readable.** At most ~5 live criteria. Each is either an executable
  check — a named test or workflow command — or an explicitly declared
  reading over named retained artifacts at the moment of the action. Nothing in
  between; a criterion needing a bespoke reader built first belongs in the
  deterministic suite.
- **Cheapest probe first.** A plan whose end goal is such an action schedules the
  cheapest end-to-end approximation of it as soon as that is runnable, and
  re-runs it at slice boundaries. No slice may be chartered to produce evidence
  for a failure mode a free probe could first demonstrate or refute.
- **Re-derive, do not patch.** When the architecture under the contract changes,
  re-derive what the gated action needs instead of amending criteria whose
  premise has moved. A review pass that finds the contract asking for more than
  the action uniquely tests has standing authority to SHRINK it under these
  rules; only widening the contract, or a third review round, needs the user.

## Session Handoff

Execution spans sessions, and the plan is the only carrier between them. Why: the
alternative is a hand-written handoff prompt — a third living document beside the
plan and this contract, unreviewed, duplicating both, and only as good as the
session that wrote it.

- **Ending a session** means updating `## Start Here` (state, exact next action,
  open questions for the user), committing green work, and stopping. It does not
  mean writing a bespoke prompt for the next session.
- **Starting a session** uses the constant invocation: `/plan-continue` in Claude
  Code, or the sentence "Continue the active plan." for any agent, which resolves
  to `.claude/commands/plan-continue.md`. If a handoff needs more words than
  that, the defect is in `## Start Here`, not in the prompt.
- **Resume reconciliation.** Before any other work, derive the plan's last-touch
  commit (`git log -1 --format=%h -- <plan file>`), list
  `git log <that>..HEAD --oneline`, and fold anything unrecorded into
  `## Start Here` / `## Progress` first. Working on a tree the plan does not
  describe is the stale-charter failure in a fresher coat.
- **Lesson routing.** Experience compounds in the repository, never in prompts: a
  repeatable process rule goes to this file, `AGENTS.md`, or a skill; a
  mechanically checkable trap goes to `tests/test_plan_contract.py`, another
  test, or a hook; a plan-scoped fact or pin goes to a charter, the
  `## Acceptance Contract`, or `## Decision Log`; the next action goes to
  `## Start Here`. Nothing goes to a handoff prompt.

## Execution Rules

- Keep slices reviewable and small enough to commit independently.
- Update `## Progress` before moving to a new slice.
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
python3 tests/test_plan_contract.py
git diff --check
scripts/check-private
scripts/check-scripts
```

The plan contract also runs under Pants as
`pants test tests/test_plan_contract.py`, and a `PostToolUse` hook runs the
standalone form after every edit to a plan file. Run additional checks named in
the plan when the touched surface requires them.
