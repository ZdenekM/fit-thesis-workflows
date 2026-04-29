# TODO

1. [ ] Adopt `pdf-reader-mcp` as an optional PDF detail layer.
   - Upgrade or provide Node.js 22+ for the MCP server.
   - Add Codex setup notes, for example `codex mcp add pdf-reader -- npx @sylphx/pdf-reader-mcp`.
   - Update thesis skills to use the MCP for targeted page ranges, metadata, page counts, figures, and layout-sensitive PDF checks.
   - Keep `pdftotext -layout` as the default import/extraction path for stable case evidence.
   - Do not require OCR support for scanned PDFs in V1; expected thesis inputs are text-based PDFs.
2. [ ] Keep `config/supervisor-deadlines.tsv` current for each academic year before the thesis season starts.
3. [x] Add an explicit code quality/design review layer for thesis submissions.
   - Cover architecture/design fit, maintainability, module boundaries, naming, error handling, async/runtime risks, and code smells.
   - Check whether comments are helpful and sufficient without rewarding noisy comments.
   - Review README/developer documentation, installation instructions, reproducibility notes, and expected test/smoke-test workflow.
   - Keep this distinct from syntax checks and thesis-code consistency: it should answer whether the implementation is well engineered, not only whether it exists and matches the text.
   - Surface the result in supervisor feedback when useful, and in opponent materials as internal evidence when relevant.
4. [x] Add an output-language setting for generated student feedback.
   - Default student-facing supervisor feedback to Czech with diacritics.
   - Support an explicit English mode for cases where English feedback is preferable.
   - Do not add Slovak as a generated-feedback mode for now; supervisor review/editing should stay comfortable for the Czech-speaking operator.
   - Update templates and skills so ASCII-only repo hygiene does not leak into student-facing Markdown outputs.
5. [ ] Add a lightweight final feedback output check.
   - Add a helper script such as `scripts/check-feedback-output`.
   - Verify that student-facing feedback contains all required sections.
   - Keep the priority table focused by checking for a reasonable number of priority rows.
   - Require an explicit review scope and limitations section.
   - Require concrete evidence for P0/P1 claims.
   - Check the configured output language, including Czech diacritics for Czech student-facing feedback.
   - Detect empty, generic, or placeholder-like checklist items and phrases.
