---
name: thesis-literature-citation-review
description: Review BP/DP cited literature for relevance, claim support, accessible source evidence, and defensible use in supervisor or opponent workflows.
---

# Thesis Literature Citation Review

Command routing: treat `scripts/<tool>` examples below as logical workflow
command names. On Windows, use the packaged
`dist\workflow-tools\bin\<tool>.cmd` or `.ps1` launcher from `README.md`; do
not run or click extensionless `scripts/<tool>` files.

Use this skill when a supervisor or opponent workflow needs a deeper look at
whether cited literature is relevant and used defensibly. The output is
internal/operator evidence, not student-facing prose by default.

## Inputs

Use the active round unless the user specifies another:

```text
cases/<case-id>/rounds/<round-id>/
  notes/assignment.md
  notes/supervisor-intake.md or notes/opponent-intake.md
  notes/round-notes.md
  inputs/
  extracted/
  work/
  outputs/
```

Use the submitted thesis PDF text as the authoritative rendered evidence for
what the thesis actually cites and claims. Use LaTeX sources and `.bib` files to
resolve citation keys, metadata, exact snippets, or mismatches against the
rendered PDF. Mark `.bib` entries that do not appear in the submitted PDF as
source-only, not as cited thesis literature. Also use assignment notes, reviewer
profile preferences, and any user-provided source PDFs. Publicly accessible
paper PDFs and metadata may be saved only inside the ignored round workspace,
for example `work/literature/`.

## Process

1. Confirm that the user explicitly authorized agent use in the current request when this review will produce final standalone evidence or feed supervisor/opponent artifacts. If explicit authorization is missing, stop before writing the artifact and ask the user to authorize agents.
2. Resolve the active case and round. Record whether the review is for supervisor/student-facing downstream use, opponent/internal-only use, or a standalone operator check. For supervisor/student-facing use, run `scripts/check-supervisor-ready <case-id> [round-id]` unless fresh output from that command is already in context. For opponent/internal-only use, run `scripts/check-round-ready <case-id> [round-id]`.
3. Start from role packets, current-evidence snapshots, reuse-index decisions, and existing literature/citation evidence when present. Collect bibliography entries and in-text citations from the submitted PDF text first. Use `.bib` files and LaTeX sources to resolve keys, metadata, and exact source locations, or to flag source/PDF mismatches. Keep a source map from citation key or title to thesis locations and claims it appears to support.
4. Triage citations before external lookup. Select only key or suspicious items: sources central to the assignment, thesis method, thesis conclusions, or report-grade claims; citations with metadata/title-claim mismatch; sources used for contested quantitative or state-of-the-art claims; and thin or inaccessible entries that materially affect a finding. Do not attempt to download every bibliography item by default.
5. For the selected items, resolve sources using legal/public metadata and PDFs where available. Use available web/search/download tooling for this step when the environment permits it; if network or tooling is unavailable, record that as a blocked acquisition limitation for the selected citation. Prefer DOI, arXiv, publisher pages, project pages, open repositories, and user-provided PDFs. Do not bypass paywalls or imply access to unavailable sources.
6. Record the triage and source-resolution evidence in `work/literature/source_acquisition.json` using schema version `literature-source-acquisition-v1`. The artifact must include `source_refs` and matching `source_sha256` hashes for the thesis/bibliography inputs used for triage. Do not cite generated role packets or aggregate current-evidence snapshots as source refs; packets are handoff prompts, and snapshots can create hash cycles. Each citation record must state whether it was selected, why, thesis refs, source attempts, acquisition status, cached local refs under `work/literature/` when a PDF/full text was read, and what claim support was checked. If no citation is selected, record `no_selected_sources_rationale`; a blanket "no local PDFs were available" limitation is not enough.
7. For PDFs, use `pdftotext` extracts as the default evidence. Use `pdf-reader-mcp` only for targeted metadata, page ranges, page counts, figures/tables, equations, or layout-sensitive checks; if unavailable, record the limitation.
8. Classify each important citation:
   - relevant and used appropriately,
   - relevant but underused or weakly connected to the thesis claim,
   - only partially relevant,
   - bibliographic/metadata issue,
   - inaccessible or not verifiable from current inputs,
   - potentially missing literature area.
9. For supervisor mode, suggest better use of already cited work and, only when there is a clear gap, candidate new literature areas or sources. Keep suggestions actionable and phase-appropriate.
10. For opponent mode, limit conclusions to relevance, defensibility, citation quality, and support for claims already made. Do not coach the student toward new literature except as a reportable missing-area risk.
11. Keep downloaded PDFs, metadata cache, and working notes inside `work/literature/` or another ignored case path.

## Evidence Rules

- Important negative claims must cite thesis location plus source evidence or missing-source evidence.
- Do not claim to have read a source when only metadata or an abstract was available.
- Do not equate inaccessible with irrelevant.
- Do not leave source acquisition as manual work for selected key/suspicious citations unless access is blocked, the operator disables external lookup, or the limitation is explicitly recorded in `work/literature/source_acquisition.json`.
- Do not treat literature freshness as a problem unless the field, assignment, or thesis claim makes it material.
- When recommending new literature in supervisor mode, explain the thesis gap it would address.
- When summarizing into student-facing feedback, include only phase-appropriate action items and avoid exposing internal download/cache paths.

## Review Loop

When this artifact is generated as standalone output, it is draft evidence until a different explicitly authorized reviewer agent checks it. If agent authorization is missing, ask before marking or relying on it as final standalone evidence; if authorization is not granted, stop before final standalone use or before using the artifact in a sendable supervisor/opponent synthesis. A downstream synthesis review certifies only the findings it uses, not the whole standalone artifact.

After writing or revising `outputs/literature_citation_review.md`, register the
artifact through the current `work/review_role_plan.json` preset when available,
usually with `scripts/register-review-artifact <case-id> <round-id>
outputs/literature_citation_review.md --role literature_citation`, including
source refs, checks, limitations, and downstream synthesis use. Then run
`scripts/init-review-manifest --run-checks <case-id> [round-id]` and record
whether the artifact is standalone final evidence or only covered by a
downstream synthesis review. Before relying on it, run
`scripts/check-literature-citation-review <case-id> [round-id]` and
`scripts/check-review-manifest --require-complete <case-id> [round-id]`.

## Agent Final Response Contract

When acting as a workflow agent, write full evidence content to the owned round
file and keep the chat final response compact. Do not paste full Markdown
artifacts that are already on disk.

Use the default handoff shape in `docs/agent-scheduling.md#subagent-handoffs`,
plus any role-specific validation status, owned output paths, and limitations
that affect parent verification.

## Model And Reasoning

Use the strongest available model with high reasoning effort for this semantic
workflow. Use the strongest available tier of whichever provider runs this role, at `xhigh` effort (Codex adapter: `gpt-5.5`; Claude adapter where available: `opus`); see `docs/agent-scheduling.md`. Packet prompts generated for this skill must carry the
same requirement. Do not downshift to a low-cost model (Codex Spark or a small Claude tier) for the
first or only pass over source relevance, claim support, missing-source risk,
or downstream synthesis recommendations. Mechanical helper summaries may use
cheaper models only when validator-backed and consumed by a high-reasoning
semantic pass.

## Output

Write `outputs/literature_citation_review.md`:

```markdown
# Literature And Citation Review

## Review Scope

Mention `work/literature/source_acquisition.json`, including how many
citations were selected for targeted lookup and whether any selected source was
blocked by paywall, absence, or operator-disabled external lookup.

## Bibliography Source Map

| Citation | Thesis location / claim supported | Source status | Notes |
|---|---|---|---|

## Relevant And Well Used Sources

## Underused Or Weakly Connected Sources

| Priority | Citation | Thesis claim or section | Evidence | Recommendation |
|---|---|---|---|---|

## Missing Or Inaccessible Sources

| Citation / area | Status | What is needed | Impact |
|---|---|---|---|

## Candidate Literature Improvements

Use this section only for supervisor mode or when an opponent needs to record a
missing-area risk. Separate new-source suggestions from already-cited-source
relevance checks.

## Synthesis Handoff

- Workflow/audience:
- Use in synthesis:
- Do not overstate:
- P0/P1 anchors:
- Limitations/manual checks:
- Calibration:
- Supervisor action / opponent impact:

## Review Status

## Manual Checks
```

This artifact is internal/operator evidence. Supervisor feedback may summarize
only actionable, phase-appropriate items. Opponent materials may use it for
fairness, relevance, defensibility, and citation-quality calibration.
