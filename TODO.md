# TODO

- [ ] Add thesis figure/media review workflow layer.
   - Add `.agents/skills/thesis-figure-media-review/SKILL.md` as an
   internal/operator evidence workflow.
   - Inventory rendered-thesis figures, tables, screenshots, result images,
   diagrams, and thesis-source figure assets referenced by the PDF.
   - Keep external poster/video/demo-package material in the separate demo
   artifact review unless the thesis text directly relies on it as evidence.
   - For thesis figures, compare visual content with caption, nearby text, result claims,
   and source files where available.
   - Check caption self-containment, readability, axes/units/legends, referenced-from-text
   status, copied/adapted-source attribution, raster/vector suitability, and obvious
   compression/readability issues.
   - For result graphs, verify baseline/comparator, metric direction, practical magnitude,
   and whether the textual interpretation is proportionate to what the figure shows.
   - For screenshots and UI figures, distinguish implemented functionality, mockups, and
   illustrative images.
   - Write operator evidence to outputs/figure_media_review.md and summarize only
   actionable findings into supervisor feedback or opponent materials.
   - Use PDF detail/vision checks only for targeted figure inspection; record which figures
   were actually inspected and which were only inventoried.
   - Do not make visual-content claims unless a concrete PDF-detail or vision
   check was actually performed.
   - Route result graphs to evaluation-claim sanity review, functionality
   screenshots to code consistency/code quality review, and copied/adapted
   figures to literature/citation review where relevant.
   - During implementation, update skill routing, output conventions,
   README/operator docs, generated-artifact review-loop wording, and privacy
   guards for `outputs/figure_media_review.md`.
   - Keep extracted images/crops/media notes under ignored case workspace paths.
- [ ] Add a review evidence/provenance manifest.
   - Record which inputs, extracted artifacts, helper checks, skills, generating agent/role, and reviewer agent/role contributed to each generated review artifact.
   - Mark whether each generated `outputs/*.md` artifact passed an independent review loop before being used as final evidence or sendable feedback.
   - Capture explicit workflow limitations and unavailable evidence in one operator-facing place.
   - Keep the manifest in the ignored round workspace, for example under `work/`, unless it contains only generic non-case metadata.
   - Use the manifest to make repeated rounds easier to audit without copying internal workflow detail into student-facing feedback.
- [ ] Add an opponent report composition bridge.
   - Add a narrow workflow or helper that turns `outputs/oponent_podklady_revidovane.md` into a draft report structured by FIT IS fields.
   - Preserve `thesis-opponent-materials` as the evidence source and `thesis-opponent-report-review` as the final report review pass.
   - Keep the generated report draft separate from internal evidence, for example under `work/` until reviewed.
   - Require the bridge to preserve uncertainty labels and manual-check caveats instead of turning them into unsupported final claims.
   - Avoid coaching-style student feedback language; output should be opponent-report wording for the evaluator.
- [ ] Add optional historical reference-report comparison for pipeline calibration.
   - When a previous human opponent report is provided, compare it only after `outputs/oponent_podklady_revidovane.md` exists.
   - Write an operator-only artifact such as `outputs/reference_report_comparison.md`.
   - Compare judgment shape, assignment-fulfillment concerns, literature/code/reproducibility findings, grading interval, and missed manual checks.
   - Explicitly record that the historical report is calibration evidence, not primary evidence for the generated review.
- [ ] Add demo artifact review for opponent workflows.
   - Add an optional `outputs/demo_artifacts_review.md` or equivalent operator artifact.
   - Inventory poster, video, presentation, screenshots, notebooks, result images, and generated media from the submitted package.
   - Distinguish file existence from content actually opened, played, or inspected.
   - Record whether demo artifacts show the developed solution, only general principles, or cannot be assessed from available inputs.
   - Keep heavyweight media inspection optional and scoped; do not unpack large archives blindly.
- [ ] Add a case and round readiness/status doctor.
   - Add a helper script such as `scripts/case-doctor <case-id> [round-id]`.
   - Report the active round, reviewer profile, assignment readiness, deadline calibration, and configured student feedback language.
   - Report available thesis/code inputs, extracted text, previous feedback rounds, current expected outputs, and demo/media artifacts.
   - Include a compact inventory of PDFs, page/text extraction status, archives, likely code roots, README/config/test files, and large package contents.
   - Flag stale, missing, or inconsistent artifacts before a workflow starts.
   - Keep the command read-only and operator-facing; it should summarize state, not mutate the case workspace.
- [ ] Keep `config/supervisor-deadlines.tsv` current for each academic year before the thesis season starts.
   - Treat this as recurring prerequisite maintenance for supervisor readiness, not optional workflow automation.
- [ ] Add code workspace preparation automation.
   - Add a helper such as `scripts/prepare-code-workspace <case-id> [round-id]`.
   - Unpack submitted code archives into the ignored round workspace, typically `work/code/`.
   - Produce a compact inventory of source files, README/config/test files, dependency manifests, and likely project stack.
   - Suggest cheap smoke-test commands when they can be inferred from repository files.
   - Preserve the code consistency and code quality skills as the source of reviewer judgment.
- [ ] Add optional literature-source collection automation.
   - Add a helper such as `scripts/collect-literature-sources` for DOI/arXiv/open metadata resolution.
   - Keep downloaded papers, metadata cache, and derived evidence inside the ignored case workspace.
   - Preserve the manual `thesis-literature-citation-review` workflow as the source of judgment.
