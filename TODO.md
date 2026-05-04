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
3. [x] Add a lightweight final feedback output check.
   - Add a helper script such as `scripts/check-feedback-output`.
   - Verify that student-facing feedback contains all required sections.
   - Keep the priority table focused by checking for a reasonable number of priority rows.
   - Require an explicit review scope and limitations section.
   - Require concrete evidence for P0/P1 claims.
   - Check the configured output language, including Czech diacritics for Czech student-facing feedback.
   - Require a real review date and reject placeholder dates such as `YYYY-MM-DD`.
   - Detect internal case IDs, exact round IDs, workspace paths, artifact filenames, or workflow mechanics leaking into student-facing text.
   - Detect empty, generic, or placeholder-like checklist items and phrases.
4. [x] Add a quantitative/evaluation claim sanity checker.
   - Add `scripts/check-evaluation-claims CASE_ID [ROUND_ID]` as a reviewer prompt, not a verdict engine.
   - Detect metric/result claims, measured values, metric tables, missing result data or calculation scripts, unclear units, missing baselines, weak practical effect sizes, and suspicious metric relationships.
   - Keep the checker general and context-aware; do not encode one thesis domain, dataset, metric value, filename, or expected conclusion as an active rule.
   - Treat warnings as inputs for agent/human calibration before supervisor or opponent synthesis.
   - Add smoke coverage with temporary ignored cases.
5. [x] Add a lightweight final opponent materials output check.
   - Add a helper script such as `scripts/check-opponent-materials CASE_ID [ROUND_ID]`.
   - Validate `outputs/oponent_podklady_revidovane.md`, not the first draft.
   - Require the expected reviewed-materials sections, review scope, limitations, assignment-fulfillment table, IS-item coverage, evidence ledger, grading calibration, defense questions, and manual checks.
   - Require P0/P1 findings and grade-impacting claims to include concrete evidence anchors and confidence labels.
   - Require grading calibration as a defensible interval, not a single false-precision point score.
   - Detect placeholders, empty/generic evidence, internal workflow leaks, exact case/round IDs, absolute paths, and draft artifact filenames.
   - Keep this as a deterministic final guard; it should not judge whether the opponent conclusions are substantively correct.
   - Add smoke coverage with temporary ignored cases and include the checker in documented opponent workflow closeout.
6. [ ] Add a review evidence/provenance manifest.
   - Record which inputs, extracted artifacts, helper checks, skills, generating agent/role, and reviewer agent/role contributed to each generated review artifact.
   - Mark whether each generated `outputs/*.md` artifact passed an independent review loop before being used as final evidence or sendable feedback.
   - Capture explicit workflow limitations and unavailable evidence in one operator-facing place.
   - Keep the manifest in the ignored round workspace, for example under `work/`, unless it contains only generic non-case metadata.
   - Use the manifest to make repeated rounds easier to audit without copying internal workflow detail into student-facing feedback.
7. [ ] Add an opponent report composition bridge.
   - Add a narrow workflow or helper that turns `outputs/oponent_podklady_revidovane.md` into a draft report structured by FIT IS fields.
   - Preserve `thesis-opponent-materials` as the evidence source and `thesis-opponent-report-review` as the final report review pass.
   - Keep the generated report draft separate from internal evidence, for example under `work/` until reviewed.
   - Require the bridge to preserve uncertainty labels and manual-check caveats instead of turning them into unsupported final claims.
   - Avoid coaching-style student feedback language; output should be opponent-report wording for the evaluator.
8. [ ] Add optional historical reference-report comparison for pipeline calibration.
   - When a previous human opponent report is provided, compare it only after `outputs/oponent_podklady_revidovane.md` exists.
   - Write an operator-only artifact such as `outputs/reference_report_comparison.md`.
   - Compare judgment shape, assignment-fulfillment concerns, literature/code/reproducibility findings, grading interval, and missed manual checks.
   - Explicitly record that the historical report is calibration evidence, not primary evidence for the generated review.
9. [ ] Add demo artifact review for opponent workflows.
   - Add an optional `outputs/demo_artifacts_review.md` or equivalent operator artifact.
   - Inventory poster, video, presentation, screenshots, notebooks, result images, and generated media from the submitted package.
   - Distinguish file existence from content actually opened, played, or inspected.
   - Record whether demo artifacts show the developed solution, only general principles, or cannot be assessed from available inputs.
   - Keep heavyweight media inspection optional and scoped; do not unpack large archives blindly.
10. [ ] Add a case and round readiness/status doctor.
   - Add a helper script such as `scripts/case-doctor <case-id> [round-id]`.
   - Report the active round, reviewer profile, assignment readiness, deadline calibration, and configured student feedback language.
   - Report available thesis/code inputs, extracted text, previous feedback rounds, current expected outputs, and demo/media artifacts.
   - Include a compact inventory of PDFs, page/text extraction status, archives, likely code roots, README/config/test files, and large package contents.
   - Flag stale, missing, or inconsistent artifacts before a workflow starts.
   - Keep the command read-only and operator-facing; it should summarize state, not mutate the case workspace.
11. [ ] Keep `config/supervisor-deadlines.tsv` current for each academic year before the thesis season starts.
   - Treat this as recurring prerequisite maintenance for supervisor readiness, not optional workflow automation.
12. [ ] Add code workspace preparation automation.
   - Add a helper such as `scripts/prepare-code-workspace <case-id> [round-id]`.
   - Unpack submitted code archives into the ignored round workspace, typically `work/code/`.
   - Produce a compact inventory of source files, README/config/test files, dependency manifests, and likely project stack.
   - Suggest cheap smoke-test commands when they can be inferred from repository files.
   - Preserve the code consistency and code quality skills as the source of reviewer judgment.
13. [ ] Add optional literature-source collection automation.
   - Add a helper such as `scripts/collect-literature-sources` for DOI/arXiv/open metadata resolution.
   - Keep downloaded papers, metadata cache, and derived evidence inside the ignored case workspace.
   - Preserve the manual `thesis-literature-citation-review` workflow as the source of judgment.
