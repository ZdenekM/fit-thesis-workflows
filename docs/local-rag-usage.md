# Local RAG Usage

`mcp-local-rag` is the discovery layer for Markdown-heavy repository knowledge.
Use it to find candidate files and sections before spending context on broad
reads, and whenever you do not yet know which file or section answers a
question. It is also where long Markdown goes instead of Serena; Serena stays
for code symbols.

It runs as **one shared server for the whole workstation**, a `systemd --user`
service on `http://127.0.0.1:8775/mcp`, holding one index and one embedding
model for every repository. Clients attach over HTTP at no extra memory cost.
Never add a stdio `local-rag` entry to a client config; that recreates the
per-client cost this arrangement exists to remove. Setup and rationale are in
`~/.claude/docs/mcp-bridges.md`.

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

**Agents do not ingest.** The index is machine-level state shared by every
session, refreshed outside any agent's run by a `systemd --user` timer. Never
call `ingest_file`, `ingest_data`, `sync_start`, or `delete_file`. If a query
returns nothing for content you can see on disk, the index is stale for that
file: report it and fall back to `rg`. Do not fix it by ingesting.

The scope rules below are the **operator's** contract for what the shared index
is allowed to contain. They stay here because they define the privacy boundary
that retrieved chunks inherit, and because an agent that notices a violation
must be able to name it.

- Prefer curated Markdown ingest over raw directory ingest. A raw ingest of
  `cases/` will also see prepared submitted-code roots and vendor/source
  documentation unless an exclude layer prevents it.
- `BASE_DIRS` is bridge-level machine configuration, not a per-repo setting. It
  is only a reachability boundary for MCP/CLI operations; it is not a file-level
  allowlist and does not by itself exclude unsafe subpaths. A broad configured
  root such as `cases/` is acceptable only when bulk ingest uses a separate
  curated file list or explicit safe subroots.
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
- If retrieved results reveal that excluded paths were indexed, stop relying on
  RAG for that area and report it to the operator with the offending paths. The
  remedy - purging those files, rebuilding the affected database, and rerunning
  the refresh with corrected scope - is an operator action on machine-level
  state, not something an agent performs.
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
- The vector database and model cache live outside every repository, as
  machine-level state. Do not copy indexed case text, retrieved private chunks,
  or database files into tracked paths.
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
  relevant review workflow, `rg`, Omen, PDF/text extraction tools, and direct
  source reads instead. Serena is not among them: `cases/**` is in
  `ignored_paths` in the tracked `.serena/project.yml`.
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

- For exact code behavior, identifiers, and implementation changes in this
  repository's own source, Serena comes first (`get_symbols_overview`, then
  `find_symbol`, then `find_referencing_symbols`), with `rg` for discovery and
  Omen and tests alongside. For submitted code under `cases/**`, use `rg` and
  direct source reads. See `docs/serena-code-navigation.md`.
- For thesis claims, negative findings, grading/report calibration, and
  student-facing feedback, RAG can help locate sources but cannot be the sole
  basis of the claim.
- Refreshing the index after substantial Markdown changes happens on the
  machine-level timer, not on demand. Recent edits may therefore not be
  searchable yet; when that matters, use `rg` for the current state of a file
  and say that the index may lag.
