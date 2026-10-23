# Local RAG Usage

Local RAG is an **optional maintainer environment**, not part of the operator
workflow. Operators - on Windows, or on any machine without the maintainer's
local setup - do not have it, and nothing in the workflow may depend on it.
Without it, use `rg` plus targeted reads; every rule below about what the index
may hold still applies to whoever runs one.

If a shared local index is available over MCP, it is the discovery layer for
Markdown-heavy repository knowledge. Use it to find candidate files and sections
before spending context on broad reads, and whenever you do not yet know which
file or section answers a question. It is also where long Markdown goes instead
of Serena; Serena stays for code symbols.

The contract this document relies on:

- `query_documents(query, limit, scope)` - semantic search. It returns up to
  `limit` results, each a pointer with `filePath` and the matching text; `scope`
  is an optional absolute path prefix that narrows results. Latency is around a
  second.
- Search is **semantic only**. It does not reliably find exact IDs, paths,
  script names, or identifiers; use `rg` for those.
- Read-only helpers: `status` (index health and ingest queue), `list_documents`
  (what the index holds, narrowed with a `filter` on `uri`), and
  `get_document_section` (one section of an indexed document).
- There are no agent-facing ingest, sync, or delete operations, and agents must
  not look for any.

## Intended Uses

- Historical orientation across `docs/`, `plans/`, `.agents/skills/`,
  templates, reviewer profiles, `WORKFLOW_MEMORY.md`, `TODO.md`, and Markdown
  outputs under ignored case workspaces.
- Cross-repository documentation search, when the local index also covers
  other explicitly approved curated roots.
- Re-finding prior decisions, workflow rules, calibration notes, review output
  shapes, and repeated methodology discussions.

## Safe Ingest Scope

**Agents do not ingest.** The index is machine-level state that refreshes
itself outside any agent's run, typically within a few minutes of a file
change. Never ingest, sync, or delete index content, by any tool. If a query
returns nothing for content you can see on disk, either the case mirror's
allowlist does not name that file (intentionally unindexed, see below) or the
index is stale for it - `status` shows a growing queue or failed jobs: report
which, and fall back to `rg`. Do not fix it by ingesting.

Case data reaches the index only through `cases/_rag/`, an allowlisted copy of
case Markdown that a periodic job keeps current by running
`scripts/refresh-rag-case-mirror` (`src/thesis_review_workflow/rag_case_mirror.py`
holds the allowlist). The index's configured roots name `cases/_rag`, never
`cases`: the mirror's allowlist, not an exclude list, is the boundary. A
`cases/` root once indexed thesis PDFs, extracted text, submitted code and
sources, which buried the notes and outputs that make RAG useful for case work. A hit at `cases/_rag/<path>` is a pointer to
`cases/<path>`; open and cite the original, never the mirror copy. A file the
allowlist does not name stays out of the index, so a new Markdown artifact kind
that should be searchable needs a rule there.

The scope rules below are the **operator's** contract for what the shared index
is allowed to contain. They stay here because they define the privacy boundary
that retrieved chunks inherit, and because an agent that notices a violation
must be able to name it.

- Prefer curated Markdown ingest over raw directory ingest. Never configure
  `cases/` itself as a root: a raw `cases/` root also sees thesis PDFs,
  extracted text, prepared submitted-code roots and vendor/source
  documentation, and only the mirror's allowlist keeps them out.
- `BASE_DIRS` (the index's configured roots) is machine-level configuration,
  not a per-repo setting. It is only a reachability boundary; it is not a file-level
  allowlist and does not by itself exclude unsafe subpaths. For case data it
  names only the `cases/_rag/` mirror.
- The mirror carries these classes: `case.md`, `notes/` (Markdown and text),
  `outputs/` Markdown, top-level `work/*.md` except mechanical inventories,
  role-owned `work/*_packets/*_findings.md` (not the packet prompts),
  `work/reviews/`, `work/literature/`, `work/submitted_reports/`,
  `work/calibration/`, `work/github-intake/contribution-map.md`, and from the
  literature library only `cases/_literature/*/notes.md`.
- Case `inputs/` are not mirrored. Next to prior feedback they hold what students
  submitted, and nothing structural tells the two apart; prior feedback reaches
  the index from the earlier round's `outputs/`. Historical calibration
  snapshots under `inputs/historical_cases/**` duplicate live cases and stay out.
  For GitHub intake, the curated summaries `outputs/github_code_intake.md` and
  `work/github-intake/contribution-map.md` are indexed; raw `inputs/github/**`
  snapshots never are.
- Do not bulk-ingest these case paths: `cases/**/work/code/**`,
  `cases/**/work/submission_bundle/**`, unpacked source submissions,
  raw GitHub diffs, patches, review comment dumps, check logs, checkout
  metadata, dependency/vendor trees, generated build folders, package caches,
  virtual environments, Unity `Library`, extracted thesis text under
  `cases/**/extracted/**`, third-party documentation copied as part of a
  submitted codebase, or the papers' full texts and PDFs under
  `cases/_literature/**` (`fulltext.txt`, `paper.pdf`).
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
4. Use the hit's text, or `get_document_section` for its section, only to
   decide whether the source is worth opening. Raise `limit` when triaging a
   broad question; a small `limit` can hide the second relevant document.
5. Open the source artifact with normal tools and verify the exact claim.
6. Synthesize from verified sources, not from retrieved snippets alone.

### Two Sweeps For A Wording Or Vocabulary Check

When the question is "does this word, phrase or turn of phrase appear anywhere
it should not", run **both** searches and take the verdict from the exact one.

1. Exact, on the **stem**: `rg`/`grep` for the shortest invariant part. Current
   with the disk, and the only search that can prove a zero.
2. Semantic: a local RAG query for the concept. Catches the inflected or
   paraphrased forms an exact search cannot match.
3. Conclude from (1). Use (2) only to widen where to look.

Neither alone is enough, and the reason is not redundancy — they fail
differently. An exact search fails on Czech declension: in the first real topic
case, five occurrences of `katedry` were fixed by a `katedr` sweep and the sixth,
the locative `na katedře`, survived it, because `ř` is not `r`. A local RAG query
returned that exact sentence as its top hit. Embeddings do not care about the
ending.

The converse failure is worse, so never invert the order: the index refreshes
asynchronously, so it answers from whatever it held at its last refresh. In the
same case, under an earlier refresh schedule, it kept serving the offending
sentence for twenty minutes after the sentence was deleted; a faster refresh
shortens that window but never closes it. RAG can tell you where to look; it cannot tell you that
you are done.

Also note that `rg` honours `.gitignore`, so a sweep from a repository root
silently skips all of `cases/` and returns a reassuring zero that says nothing
about a case. Sweep a case by explicit path, or use `grep`, which does not read
`.gitignore`.

## Boundaries

- For exact code behavior, identifiers, and implementation changes in this
  repository's own source, Serena comes first (`get_symbols_overview`, then
  `find_symbol`, then `find_referencing_symbols`), with `rg` for discovery and
  Omen and tests alongside. For submitted code under `cases/**`, use `rg` and
  direct source reads. See `docs/serena-code-navigation.md`.
- For thesis claims, negative findings, grading/report calibration, and
  student-facing feedback, RAG can help locate sources but cannot be the sole
  basis of the claim.
- Refreshing the index after Markdown changes happens outside the agent's run,
  not on demand. Recent edits may therefore not be searchable yet; when that
  matters, use `rg` for the current state of a file and say that the index may
  lag.
