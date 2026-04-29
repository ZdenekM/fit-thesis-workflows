# TODO

1. [x] Adopt `pdf-reader-mcp` as an optional PDF detail layer.
   - Document the Node.js 22+ requirement for the MCP server.
   - Add Codex setup notes, for example `codex mcp add pdf-reader -- npx @sylphx/pdf-reader-mcp`.
   - Update thesis skills to use the MCP for targeted page ranges, metadata, page counts, figures, and layout-sensitive PDF checks.
   - Keep `pdftotext -layout` as the default import/extraction path for stable case evidence.
   - Do not require OCR support for scanned PDFs in V1; expected thesis inputs are text-based PDFs.
2. [x] Add a literature/citation relevance workflow layer.
   - For a given case, collect cited literature from the thesis bibliography and try to download or resolve accessible PDFs/metadata when needed.
   - Record missing or inaccessible sources so the operator can provide them manually.
   - Verify whether cited sources are relevant to the claims, methods, technologies, or evaluation they support.
   - For supervisor feedback, suggest what else from the cited work could be useful for the student to use in the thesis.
   - For supervisor feedback, optionally suggest new relevant literature when the thesis has a clear literature gap.
   - For opponent workflows, limit this to relevance and defensibility checks of already cited sources; do not turn it into literature coaching.
   - Keep downloaded papers and derived evidence in the ignored case workspace, not in tracked repo paths.
3. [ ] Add a lightweight final feedback output check.
   - Add a helper script such as `scripts/check-feedback-output`.
   - Verify that student-facing feedback contains all required sections.
   - Keep the priority table focused by checking for a reasonable number of priority rows.
   - Require an explicit review scope and limitations section.
   - Require concrete evidence for P0/P1 claims.
   - Check the configured output language, including Czech diacritics for Czech student-facing feedback.
   - Require a real review date and reject placeholder dates such as `YYYY-MM-DD`.
   - Detect internal case IDs, exact round IDs, workspace paths, artifact filenames, or workflow mechanics leaking into student-facing text.
   - Detect empty, generic, or placeholder-like checklist items and phrases.
4. [ ] Add a case and round readiness/status doctor.
   - Add a helper script such as `scripts/case-doctor <case-id> [round-id]`.
   - Report the active round, reviewer profile, assignment readiness, deadline calibration, and configured student feedback language.
   - Report available thesis/code inputs, extracted text, previous feedback rounds, and current expected outputs.
   - Flag stale, missing, or inconsistent artifacts before a workflow starts.
   - Keep the command read-only and operator-facing; it should summarize state, not mutate the case workspace.
5. [ ] Keep `config/supervisor-deadlines.tsv` current for each academic year before the thesis season starts.
   - Treat this as recurring prerequisite maintenance for supervisor readiness, not optional workflow automation.
6. [ ] Add code workspace preparation automation.
   - Add a helper such as `scripts/prepare-code-workspace <case-id> [round-id]`.
   - Unpack submitted code archives into the ignored round workspace, typically `work/code/`.
   - Produce a compact inventory of source files, README/config/test files, dependency manifests, and likely project stack.
   - Suggest cheap smoke-test commands when they can be inferred from repository files.
   - Preserve the code consistency and code quality skills as the source of reviewer judgment.
7. [ ] Add optional literature-source collection automation.
   - Add a helper such as `scripts/collect-literature-sources` for DOI/arXiv/open metadata resolution.
   - Keep downloaded papers, metadata cache, and derived evidence inside the ignored case workspace.
   - Preserve the manual `thesis-literature-citation-review` workflow as the source of judgment.
8. [ ] Add a review evidence/provenance manifest.
   - Record which inputs, extracted artifacts, helper checks, skills, generating agent/role, and reviewer agent/role contributed to each generated review artifact.
   - Mark whether each generated `outputs/*.md` artifact passed an independent review loop before being used as final evidence or sendable feedback.
   - Capture explicit workflow limitations and unavailable evidence in one operator-facing place.
   - Keep the manifest in the ignored round workspace, for example under `work/`, unless it contains only generic non-case metadata.
   - Use the manifest to make repeated rounds easier to audit without copying internal workflow detail into student-facing feedback.
