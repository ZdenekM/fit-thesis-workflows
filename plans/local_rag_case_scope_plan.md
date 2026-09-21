# Local RAG Case Scope Plan

Status: planned
Created: 2026-09-21

## Goal

Replace the blanket exclusion of case content from the shared local-RAG index
with a per-class rule that records *why* each class is in or out, and make the
round under review searchable rather than permanently stale.

The current rule bans extracted thesis text outright. The operator's objection
is sound: a thesis is long prose that changes rarely, new revisions are added
while old ones freeze, and "which part of the thesis discusses X" is the exact
question the exact-search path answers badly. The classes lumped in with it —
prepared code workspaces, submission bundles, raw intake snapshots, similarity
reports — are not prose and do not share its argument.

## Audit Base

The rule lives in two places: `AGENTS.md` (the local RAG bullets) and
`docs/local-rag-usage.md` (`## Safe Ingest Scope`, `## Required Handling`). It
arrived in commit `180078e`, "Align MCP retrieval rules with the shared-bridge
setup". That commit's message explains the bridge topology change in detail and
records **no rationale for the content exclusions**; they appear as a list. The
absence of a recorded "why" is what this plan is really fixing — the policy was
reconstructed from scratch twice, once by the operator and once by an agent, in
a single session.

Observed state of the index, checked read-only through `list_files` and
`query_documents`:

- Classes the current rule excludes are present for at least one completed
  opponent round: the full extracted thesis text, the thesis PDF, an imported
  similarity report in both PDF and extracted form, and vendored third-party
  files from a prepared submitted-code workspace (a font licence, a toolkit
  changelog and licence, a project-version file).
- A newly created round had its extracted assignment text indexed within
  minutes by the refresh timer.
- Reported to the operator; no agent purge, ingest or sync was performed, per
  the standing rule.

Capability facts established in the same session, which the decision depends on:

- `query_documents` takes `scope` as an **optional caller-supplied filter**, not
  an authorization boundary. One index serves every configured repository on the
  workstation, so an unscoped query from an unrelated repository's session can
  return case content.
- `sync_start` accepts an **optional `path`** naming a file or directory inside a
  configured base directory and synchronizes only that subtree. A per-round
  refresh is therefore cheap and bounded; the staleness objection to indexing an
  active round is weaker than it first appeared.
- The refresh timer lag is real but small — measured at roughly twenty minutes
  for a file edited during the session, which is long enough for a semantic
  query to return a sentence that had already been deleted.

## Scope

In scope:

- A per-class decision for case content, each class carrying its rationale.
- Whether and how the round under review gets a scoped refresh, and whether the
  standing "agents never sync" invariant changes.
- Aligning `AGENTS.md` and `docs/local-rag-usage.md` with the decision.
- Naming what must happen to index entries that the decided policy excludes.

Out of scope:

- Any agent-run ingest, sync, purge or rebuild. Those stay operator actions on
  machine-level state.
- `BASE_DIRS` values and bridge configuration, which are machine-level and
  shared with other repositories.
- Serena's coverage of case content, which is settled separately and unchanged.
- The two-sweep vocabulary pattern, already landed in
  `docs/local-rag-usage.md`.

## Acceptance Contract

- Every class of case content is listed as indexed or excluded, and each entry
  states the reason in one sentence.
- The reason for excluding a class is a property of that class, not a
  restatement of the rule.
- An agent reading the tracked rules can tell, for any path under a case,
  which side it falls on without asking.
- The evidence-discipline rule survives whatever is decided: a retrieved chunk
  never becomes a citation in a finding about a thesis.

## Slices

### S1 — Decide the per-class policy and record the reason

Status: planned

Proposed commit message: `Say which case content the shared index may hold, and why`

Why: the current list has no recorded rationale, so it cannot be applied to a
class it does not name and cannot be revisited without re-deriving it.

Expected paths: `AGENTS.md`, `docs/local-rag-usage.md`

Tasks:

- Write the decided split as a table of classes, each with a one-sentence
  reason. The operator has agreed the shape: thesis prose in, non-prose and
  third-party content out.
- Record, for thesis text, the two costs that were weighed and why they were
  accepted: an unscoped query from another repository's session can reach it,
  and having it indexed creates a cheap path from chunk to finding that the
  review architecture exists to prevent.
- Record, for the similarity report, that it carries third-party texts received
  for one purpose — the strongest exclusion in the list and the one least
  dependent on the others.
- Record, for prepared code workspaces, that the objection is noise as much as
  privacy: what actually reached the index from one was vendored third-party
  documentation, not student work.
- State the evidence rule for thesis text explicitly at the point of decision,
  not only in the general handling section: a chunk has no page number, and a
  finding about a thesis cites a page or a section.

Out of scope: changing the index; deciding the refresh question, which is S2.

Verification: `pants test tests/test_plan_contract.py`; read the two documents
against each other for a class named in one and missing from the other.

### S2 — Give the round under review a bounded refresh

Status: planned

Proposed commit message: `Refresh the index for the round being reviewed`

Why: indexing thesis text is only useful if the active round is searchable, and
the active round is exactly the one the timer lags on.

Expected paths: `docs/local-rag-usage.md`, `AGENTS.md`, possibly a workflow
command under `scripts/` and its module under `src/thesis_review_workflow/cli/`

Tasks:

- Decide who triggers the scoped sync. Two candidates: the operator runs it
  after intake, or the intake command runs it for the round it just populated.
- If the command runs it, settle the consequence for the standing invariant.
  "Agents never sync" exists because the index is shared machine state and a
  full sync during a review wave is a resource event; a path-scoped sync of one
  round is neither. Decide whether the invariant becomes "agents never sync an
  unscoped path" or stays absolute with the operator holding the step.
- Keep the failure mode benign either way: a refresh that did not run must
  degrade to the current behaviour, never to a silent wrong answer.
- Record that a scoped sync reports a job id and is polled, so a caller can tell
  a slow sync from a failed one.

Out of scope: any unscoped sync; changing the timer.

Verification: with the decision applied, a file added to a round is retrievable
without waiting for the timer, and an unrelated base directory shows no change
in its indexed file count.

### S3 — Bring the existing index into line

Status: planned

Proposed commit message: `Record how the index is reconciled with the decided scope`

Why: the index already holds classes that the decided policy will exclude, and
the remedy is an operator action that should be written down before it is run.

Expected paths: `docs/local-rag-usage.md`

Tasks:

- List what the reconciliation has to remove once S1 is decided, by class
  rather than by case path, so the instruction stays case-neutral.
- Say how the result is verified read-only afterwards, using `list_files`
  against each excluded class.
- Note that purge and rebuild are operator actions on machine-level state, and
  that an agent that notices a violation reports the offending paths instead.
- Decide whether a periodic read-only check is worth having, and if so where it
  belongs — it cannot be a repository gate, because the index is not repository
  state.

Out of scope: performing the purge or rebuild.

Verification: after the operator's reconciliation, `list_files` scoped to a case
shows only classes the decided policy admits.

## Progress

Not started. The operator has agreed to the shape in S1 — narrow the exclusion
to non-prose and third-party classes, admit thesis prose — and raised the
on-demand sync that S2 exists to settle.

## Decision Log

- 2026-09-21 — The blanket exclusion is over-broad and will be narrowed rather
  than kept or dropped wholesale. Thesis prose has a real retrieval case that
  the other excluded classes do not share; lumping them together is what made
  the rule unarguable. Operator agreed in session.
- 2026-09-21 — Staleness is not a sufficient argument against indexing an active
  round. `sync_start` takes an optional path and syncs only that subtree, so a
  per-round refresh is bounded and cheap. This reopened a question the original
  rule had closed by assumption.
- 2026-09-21 — `scope` on a query is a filter, not a boundary. Any decision to
  index thesis text is therefore also a decision that an unscoped query from
  another repository's session may return it. If that is unacceptable, the
  remedy is a second index or a scoped bridge, which is machine-level and
  outside this plan.
- 2026-09-21 — The rule's missing rationale is the defect being fixed, not a
  documentation nicety. It was reconstructed twice in one session, once by the
  operator and once by an agent, which is the cost of a rule that records only
  its conclusion.

## Final Audit

Not reached.
