# TODO

1. [ ] Adopt `pdf-reader-mcp` as an optional PDF detail layer.
   - Upgrade or provide Node.js 22+ for the MCP server.
   - Add Codex setup notes, for example `codex mcp add pdf-reader -- npx @sylphx/pdf-reader-mcp`.
   - Update thesis skills to use the MCP for targeted page ranges, metadata, page counts, figures, and layout-sensitive PDF checks.
   - Keep `pdftotext -layout` as the default import/extraction path for stable case evidence.
   - Do not require OCR support for scanned PDFs in V1; expected thesis inputs are text-based PDFs.
2. [ ] Keep `config/supervisor-deadlines.tsv` current for each academic year before the thesis season starts.
3. [ ] Add a literature/citation relevance workflow layer.
   - For a given case, collect cited literature from the thesis bibliography and try to download or resolve accessible PDFs/metadata automatically.
   - Record missing or inaccessible sources so the operator can provide them manually.
   - Verify whether cited sources are relevant to the claims, methods, technologies, or evaluation they support.
   - For supervisor feedback, suggest what else from the cited work could be useful for the student to use in the thesis.
   - For supervisor feedback, optionally suggest new relevant literature when the thesis has a clear literature gap.
   - For opponent workflows, limit this to relevance and defensibility checks of already cited sources; do not turn it into literature coaching.
   - Keep downloaded papers and derived evidence in the ignored case workspace, not in tracked repo paths.
4. [ ] Add a lightweight final feedback output check.
   - Add a helper script such as `scripts/check-feedback-output`.
   - Verify that student-facing feedback contains all required sections.
   - Keep the priority table focused by checking for a reasonable number of priority rows.
   - Require an explicit review scope and limitations section.
   - Require concrete evidence for P0/P1 claims.
   - Check the configured output language, including Czech diacritics for Czech student-facing feedback.
   - Require a real review date and reject placeholder dates such as `YYYY-MM-DD`.
   - Detect internal case IDs, exact round IDs, workspace paths, artifact filenames, or workflow mechanics leaking into student-facing text.
   - Detect empty, generic, or placeholder-like checklist items and phrases.
