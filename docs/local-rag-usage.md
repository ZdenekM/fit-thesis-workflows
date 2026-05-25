# Local RAG Usage

`mcp-local-rag` is a local discovery layer for Markdown-heavy repository
knowledge. Use it to find candidate files and sections before spending context
on broad reads.

## Intended Uses

- Historical orientation across `docs/`, `plans/`, `.agents/skills/`,
  templates, reviewer profiles, `WORKFLOW_MEMORY.md`, `TODO.md`, and Markdown
  outputs under ignored case workspaces.
- Cross-repository documentation search over explicitly approved curated roots,
  for example selected docs, plans, skills, notes, and review artifacts in
  `diplomky_v2`, `shaas-suite`, and `MozartUserInterface`.
- Re-finding prior decisions, workflow rules, calibration notes, review output
  shapes, and repeated methodology discussions.

## Safe Ingest Scope

- Prefer curated Markdown ingest over raw directory ingest. A raw ingest of
  `cases/` will also see prepared submitted-code roots and vendor/source
  documentation unless an exclude layer prevents it.
- `BASE_DIRS` is only a reachability boundary for MCP/CLI operations; it is not
  a file-level allowlist and does not by itself exclude unsafe subpaths. A broad
  configured root such as `cases/` is acceptable only when bulk ingest uses a
  separate curated file list or explicit safe subroots.
- For `cases/`, ingest these Markdown classes: `case.md`, `notes/`,
  `outputs/`, reviewer profiles, `work/*_draft.md`, `work/*_summary.md`,
  packet summaries, operation summaries, and other operator-authored review
  evidence.
- Case `inputs/` need stricter handling: direct Markdown files such as prior
  feedback or operator-provided review notes may be useful, and historical
  calibration snapshots may be useful. For GitHub intake, prefer curated
  summaries such as `outputs/github_code_intake.md`, small metadata manifests,
  or review-oriented `work/github-intake/contribution-map.md`; do not bulk-ingest
  raw `inputs/github/**` snapshots.
- Do not bulk-ingest these case paths: `cases/**/work/code/**`,
  `cases/**/work/submission_bundle/**`, unpacked source submissions,
  raw GitHub diffs, patches, review comment dumps, check logs, checkout
  metadata, dependency/vendor trees, generated build folders, package caches,
  virtual environments, Unity `Library`, extracted thesis text under
  `cases/**/extracted/**`, or third-party documentation copied as part of a
  submitted codebase.
- Exclude very large mechanical inventories such as
  `work/submission_bundle_inventory.md`; they are useful as direct artifacts
  when needed, but they mostly add file-list noise to semantic search. Keep
  smaller review-oriented inventory summaries, such as GitHub intake
  contribution maps, when they are written as evidence rather than raw listings.
- If an accidental ingest includes excluded paths, purge those files from the
  vector database or rebuild the affected local database, rerun ingest with the
  corrected scope, and verify by path checks before relying on RAG results.
- Root-level Markdown files such as `AGENTS.md`, `README.md`, `TODO.md`, and
  `WORKFLOW_MEMORY.md` are useful, but top-level repository roots are not a safe
  bulk-ingest target when they contain build/cache/vendor directories. Include
  root-level Markdown only through curated ingest tooling or explicit one-file
  ingestion that does not make the whole repository root a RAG scan root.
- Do not point `BASE_DIRS` at copied tool or vendor repository roots just
  because they contain README files. For example, prefer curated research
  docs/plans over broad tool folders such as `research/tools/**`.

## Required Handling

- Treat RAG results as pointers, not evidence. Open the exact source file,
  rendered PDF text, extracted thesis text, code file, note, or generated
  artifact before using a retrieved claim.
- Cite authoritative paths, sections, pages, or line numbers in final outputs.
  Do not cite chunk IDs, scores, or RAG summaries as evidence.
- Keep the local vector database and model cache outside this repository. Do
  not copy indexed case text, retrieved private chunks, or database files into
  tracked paths.
- Keep configured roots focused on documentation, plans, skills, profiles,
  notes, cases, and review artifacts. Do not point local RAG at whole repository
  roots when that would pull in build outputs, package caches, virtual
  environments, Unity `Library`, or vendor documentation.
- For ignored thesis case workspaces, index case notes, assignments, reviewer
  profiles, generated Markdown outputs, curated GitHub intake summaries, and
  operator work summaries. Do not bulk-index prepared submitted-code roots such
  as `cases/**/work/code/**`, `cases/**/work/submission_bundle/**`, raw
  `cases/**/inputs/github/**` snapshots, nested non-evidence
  `cases/**/inputs/**` source trees, or extracted thesis text under
  `cases/**/extracted/**`; inspect submitted code and thesis text with the
  relevant review workflow, `rg`, Serena, Omen, PDF/text extraction tools, and
  direct source reads instead.
- Retrieved case text is private case data. It may guide local orientation, but
  tracked docs and workflow changes must remain case-neutral.
- Use required thesis-review skills, readiness checks, reviewer profiles,
  role-specific validators, and source artifacts for sendable or final review
  work. RAG does not replace those gates.

## Query Pattern

1. Query with the concept plus likely artifact class, for example
   `opponent calibration applied profile`, `feedback conditional wording`, or
   `figure media visual evidence`.
2. Prefer keyword-rich queries when looking for workflow terms, script names,
   section names, roles, or output paths.
3. Use RAG before broad file reads when exact `rg` search produces high-fanout
   narrative matches across many long Markdown docs, plans, or skills. Let RAG
   identify the most likely 1-2 source documents, then open those files
   directly.
4. Read neighboring chunks only to decide whether the source is worth opening.
5. Open the source artifact with normal tools and verify the exact claim.
6. Synthesize from verified sources, not from retrieved snippets alone.

## Boundaries

- For exact code behavior, identifiers, and implementation changes, prefer
  `rg`, Serena, Omen, tests, and direct source inspection.
- For thesis claims, negative findings, grading/report calibration, and
  student-facing feedback, RAG can help locate sources but cannot be the sole
  basis of the claim.
- Re-ingest or refresh relevant files after substantial Markdown changes or
  after new case outputs should become searchable.
