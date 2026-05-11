---
name: thesis-literature-citation-review
description: Review BP/DP cited literature for relevance, claim support, accessible source evidence, and defensible use in supervisor or opponent workflows.
---

# Thesis Literature Citation Review

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
3. Collect bibliography entries and in-text citations from the submitted PDF text first. Use `.bib` files and LaTeX sources to resolve keys, metadata, and exact source locations, or to flag source/PDF mismatches. Keep a source map from citation key or title to thesis locations and claims it appears to support.
4. Resolve sources using legal/public metadata and PDFs where available. Prefer DOI, arXiv, publisher pages, project pages, open repositories, and user-provided PDFs. Do not bypass paywalls or imply access to unavailable sources.
5. For PDFs, use `pdftotext` extracts as the default evidence. Use `pdf-reader-mcp` only for targeted metadata, page ranges, page counts, figures/tables, equations, or layout-sensitive checks; if unavailable, record the limitation.
6. Classify each important citation:
   - relevant and used appropriately,
   - relevant but underused or weakly connected to the thesis claim,
   - only partially relevant,
   - bibliographic/metadata issue,
   - inaccessible or not verifiable from current inputs,
   - potentially missing literature area.
7. For supervisor mode, suggest better use of already cited work and, only when there is a clear gap, candidate new literature areas or sources. Keep suggestions actionable and phase-appropriate.
8. For opponent mode, limit conclusions to relevance, defensibility, citation quality, and support for claims already made. Do not coach the student toward new literature except as a reportable missing-area risk.
9. Keep downloaded PDFs, metadata cache, and working notes inside `work/literature/` or another ignored case path.

## Evidence Rules

- Important negative claims must cite thesis location plus source evidence or missing-source evidence.
- Do not claim to have read a source when only metadata or an abstract was available.
- Do not equate inaccessible with irrelevant.
- Do not treat literature freshness as a problem unless the field, assignment, or thesis claim makes it material.
- When recommending new literature in supervisor mode, explain the thesis gap it would address.
- When summarizing into student-facing feedback, include only phase-appropriate action items and avoid exposing internal download/cache paths.

## Review Loop

When this artifact is generated as standalone output, it is draft evidence until a different explicitly authorized reviewer agent checks it. If agent authorization is missing, ask before marking or relying on it as final standalone evidence; if authorization is not granted, stop before final standalone use or before using the artifact in a sendable supervisor/opponent synthesis. A downstream synthesis review certifies only the findings it uses, not the whole standalone artifact.

After writing or revising `outputs/literature_citation_review.md`, run `scripts/init-review-manifest --run-checks <case-id> [round-id]` and record whether the artifact is standalone final evidence or only covered by a downstream synthesis review. Before relying on it, run `scripts/check-review-manifest --require-complete <case-id> [round-id]`.

## Agent Final Response Contract

When acting as a workflow agent, write full evidence content to the owned round
file and keep the chat final response compact. Do not paste full Markdown
artifacts that are already on disk.

Return only:

- files written or changed;
- top 3-5 findings, verdicts, or risks;
- commands/checks run;
- explicit limitations;
- whether expected output validation passed.

The main session must verify file claims with expected-output checks before
relying on them.

## Model And Reasoning

Use the strongest available model with high reasoning effort for this semantic
workflow. In the current Codex setup, use `gpt-5.5` with `xhigh` reasoning when
that choice is exposed. Packet prompts generated for this skill must carry the
same requirement. Do not downshift to Spark or another low-cost model for the
first or only pass over source relevance, claim support, missing-source risk,
or downstream synthesis recommendations. Mechanical helper summaries may use
cheaper models only when validator-backed and consumed by a high-reasoning
semantic pass.

## Output

Write `outputs/literature_citation_review.md`:

```markdown
# Literature And Citation Review

## Review Scope

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

## Review Status

## Manual Checks
```

This artifact is internal/operator evidence. Supervisor feedback may summarize
only actionable, phase-appropriate items. Opponent materials may use it for
fairness, relevance, defensibility, and citation-quality calibration.
