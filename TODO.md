# TODO

## P0 - Workflow Reliability

- [ ] Add native Windows runtime proof for packaged workflow launchers.
   - Keep Python as the primary command surface for workflow helpers; POSIX `scripts/*` wrappers may remain convenience entrypoints only.
   - `scripts/smoke-package-workflow-tools` proves structural generation and POSIX launcher runtime in this Linux checkout; add a real Windows cmd, PowerShell, or CI run before claiming native Windows runtime proof.
   - New or changed operator workflow commands must keep the command-surface contract in `docs/workflow-command-surface.md`: Python CLI, Pants/PEX target, generated `.cmd`/`.ps1` launchers, and targeted test or smoke coverage.
- [ ] Continue deterministic tests as workflow validators and helper contracts grow.
   - The highest-risk reliability helpers now have focused pytest coverage; keep adding pure tests for new validators, manifest/coverage rules, and planned case-format or supervisor-closeout helpers.
   - Keep large end-to-end smoke scripts available for operator confidence, but do not make every heavy smoke part of the default fast gate.
   - Every new helper must land with focused anonymized fixtures under tracked fixture paths; never copy real `cases/` artifacts into test data.
- [ ] Replace remaining free-form text semantic detectors with agent-produced structured evidence.
   - Free-form thesis, README, notes, generated prose, and code text should be interpreted by an explicitly authorized agent/LLM workflow, then stored as structured artifacts with evidence anchors.
   - Deterministic helpers may parse metadata labels, Markdown sections/tables, paths, file suffixes, placeholders, privacy leaks, command output markers, and schema fields; they should not infer semantic meaning from raw text.
   - Current advisory or free-text-derived parts to retire or wrap with structured agent artifacts include `scripts/check-evaluation-claims`, `scripts/check-evidence-presence`, `scripts/check-assignment-coverage`, `scripts/draft-opponent-report`, and `scripts/check-opponent-report`.
   - Explicit URL and marker detection in `scripts/opponent-preflight` and `scripts/check-tooling` may remain structural evidence routing, but should move to structured metadata if the notes format becomes more formal.
   - Until replaced, free-text-derived helper output must remain warning/advisory only and must be treated as prompts for agent/human verification, not as readiness gates or findings; structural schema, path, hash, placeholder, and privacy checks may remain hard gates.
- [ ] Implement the read-only case-data contract and migration dry-run from `plans/case_format_migration_contract_plan.md`.
   - Treat `cases/<case-id>/` layout, `case.md` metadata fields, round layout, manifests, coverage files, and reusable JSONL evidence as operator data contracts used by more than one person.
   - Start with `layout_current`, `review_ready`, and `provenance_ready` diagnostics before any write or bulk migration mode.
   - Prefer explicit migrations over long-lived compatibility branches in workflow code: normal scripts should target the current case format, while old formats are handled by migration tools and clear "needs migration" diagnostics.
   - Add a case format/version marker, or a deterministic format detector if explicit versioning is not yet present, and make `scripts/case-doctor` report current format, target format, and required migrations.
   - Add read-only diagnostics first: `scripts/check-case-format` and `scripts/migrate-case --dry-run`; defer write or bulk migration until dry-run behavior is reviewed.
   - Before landing a breaking structure change, add or update an anonymized fixture case for the old format, a smoke test proving migration to the new format, and closeout checks proving existing current-format cases still pass.
   - Document the migration in `README.md` or a focused workflow doc when it affects operators; do not silently change required case structure in a way that breaks existing local cases.
- [ ] Add reviewed write and bulk case migration controls after dry-run behavior is stable.
   - Add write-mode `scripts/migrate-case` and bulk `scripts/migrate-cases` only after the dry-run contract is reviewed against real operator needs.
   - Include `--backup`, `--case`, `--all`, and `--from/--to` style controls with explicit idempotence tests.
   - Preserve private inputs by default, avoid rewriting large binary/source artifacts unless explicitly required, and write an operator log under the ignored case workspace.
- [ ] Implement the supervisor-feedback preflight and closeout bundle from `plans/supervisor_workflow_closeout_plan.md`.
   - Preflight should run readiness checks, `scripts/case-doctor`, code workspace preparation when code exists, assignment/metadata sanity checks, and early evidence-presence checks.
   - Closeout should run manifest initialization/update, agent coverage, feedback language/output checks, private-data checks, script checks, and whitespace/diff hygiene.
   - Keep the bundle transparent: print the exact underlying checks and their pass/fail status.
- [ ] Keep `config/supervisor-deadlines.tsv` current for each academic year before the thesis season starts.
   - Treat this as recurring prerequisite maintenance for supervisor readiness, not optional workflow automation.

## P1 - Evidence Coverage

- [ ] Add a student-code sandbox workflow before running submitted code.
   - Keep the default code-review mode static/read-only; executing student code must be an explicit sandboxed step with recorded scope.
   - Add a helper such as `scripts/code-sandbox` with modes for environment inspection, case-local Python venv/uv setup, and rootless container runs.
   - Store all dependency installs, caches, run logs, command transcripts, and generated files under the ignored round workspace, for example `work/sandbox/`.
   - For Python-only dependency checks, prefer a case-local venv/uv environment with `UV_CACHE_DIR`/`PIP_CACHE_DIR` inside the round workspace; classify missing or ambiguous setup as reproducibility evidence, not as implementation failure.
   - For executing unknown code, prefer rootless Podman/Docker with submitted sources mounted read-only, a separate writable run directory, non-root user, no host home, no Docker socket, no network by default, and resource/time limits.
   - Split dependency installation from execution: setup may allow network only when explicitly requested, while actual review runs should be network-off unless the assignment makes network access material.
   - Write a reusable `work/code_environment.md` or structured JSON summary that downstream code-quality and code-consistency reviewers can cite.
- [ ] Add an evidence-resolved wording pass for student-facing feedback.
   - Before writing conditional phrases such as "if the thesis/README mentions X", search the rendered PDF, README, code, tests, configs, and available notes for whether X is actually present.
   - Prefer concrete statements such as "the README mentions automated tests, but does not describe the dev/test setup" over instructions that make the student or supervisor re-check the source material.
   - Keep conditional wording only when the available evidence is genuinely missing, contradictory, or outside the provided inputs, and state that limitation explicitly.
   - Add a reviewer check that flags avoidable conditional wording in P0/P1 items and asks the synthesis/review agent to resolve it from evidence before finalizing.
- [ ] Extend visual/media intake beyond the V1 evidence-presence inventory.
   - Inventory PDF figures/tables, source image assets, screenshots, videos, notebooks, posters, and presentations in operator-only work artifacts.
   - Distinguish rendered-PDF evidence from source-asset evidence and record whether media content was actually inspected.
   - Route unresolved visual interpretation or result-graph quality issues to the figure/media and evaluation-claim review paths.
- [ ] Add video/demo artifact intake and lightweight review workflow for supervisor and opponent cases.
   - Detect assignment-required video/demo artifacts from `notes/assignment.md`, assignment PDFs, and submitted inputs; classify each artifact as required, optional, missing, present-uninspected, metadata-checked, sampled, fully watched, or not playable.
   - Add a cheap first pass for video files: file hash, duration, codec, audio presence, resolution/aspect ratio, sampled thumbnails, black-bar/crop/aspect anomalies, and obvious unreadable/silent/corrupt media signals.
   - Store reusable operator evidence in a structured artifact such as `work/media/video_inventory.jsonl` plus sampled frames under `work/media/`, and summarize reviewable conclusions in `outputs/demo_artifacts_review.md` when the demo is material.
   - Review content only as deeply as needed: sample representative timestamps by default, watch the full video only when it is short, assignment-critical, or samples reveal ambiguity; record the inspection depth explicitly.
   - Record whether the artifact shows the developed solution, only slides/general principles, setup/build/run evidence, user-test/results evidence, or cannot be assessed from available inputs.
   - Route findings into student-facing feedback or opponent materials only when actionable: missing/difficult-to-find artifact, poor export/aspect/readability/audio, mismatch with thesis claims, or missing evidence for assignment point "video".
   - Keep heavyweight media inspection optional and scoped; do not unpack large archives blindly, and do not make visual/audio content claims from mere file existence or metadata.
- [ ] Add figure/media graph and table quality checks.
   - Add figure/table quality checks for axes, units, legends, captions, source/data provenance, readability, scale, time range, and whether the text interpretation is stronger than the visual evidence.
   - For result graphs and metric tables, route unresolved quality or interpretation issues to evaluation-claim review instead of treating visual inspection as proof of metric validity.
   - Surface only actionable synthesis into supervisor/opponent feedback, such as missing axis labels, unsupported graph interpretation, or placeholder table values.

## P2 - Later Automation

- [ ] Add optional historical reference-report comparison for pipeline calibration.
   - When a previous human opponent report is provided, compare it only after `outputs/oponent_podklady_revidovane.md` exists.
   - Write an operator-only artifact such as `outputs/reference_report_comparison.md`.
   - Compare judgment shape, assignment-fulfillment concerns, literature/code/reproducibility findings, grading interval, and missed manual checks.
   - Explicitly record that the historical report is calibration evidence, not primary evidence for the generated review.
- [ ] Add advanced typography/formal review automation after V1 proves useful.
   - Use precise PDF layout evidence such as `pdftotext -bbox` or `pdf-reader-mcp` for exact rendered line positions instead of relying only on `pdftotext -layout`.
   - Offer LaTeX patch suggestions only when explicitly requested; keep the default workflow read-only and student-owned.
   - Consider local LanguageTool/Vale-style grammar and prose linting for Czech and English after the narrow typography workflow stays stable.
   - Add deeper style checks for units, percentages, abbreviations, quote consistency, and anglicisms only where they can be calibrated by thesis language and phase.
- [ ] Expand GitHub code intake beyond the light V1.
   - Add manifest-driven import from `inputs/github/code-manifest.yml` with multiple repositories, multiple PRs, and explicit PR relations such as independent, depends-on, follow-up, split-from, and supersedes.
   - Add a dedicated `outputs/pr_contribution_review.md` workflow for deeper upstream PR contribution analysis after `outputs/github_code_intake.md` proves useful.
   - Prefer GitHub MCP/App structured reads for resolved review-thread state, linked issues, and richer CI/action metadata when available; keep `gh` as deterministic export fallback.
   - Add base/head/merge workspace views for each PR and compare submitted archives against GitHub snapshots when both are available.
   - Auto-slice large PRs by commits, directories, APIs, tests, docs, generated files, and runtime subsystems, but keep upstream baseline separate from student-owned changes.
   - Add a focused validator for `outputs/github_code_intake.md` once the evidence shape stabilizes.
- [ ] Add optional literature-source collection automation.
   - Add a helper such as `scripts/collect-literature-sources` for DOI/arXiv/open metadata resolution.
   - Evaluate GROBID-style PDF reference extraction for bibliography/source maps, but keep extraction confidence explicit.
   - Query public metadata APIs such as Crossref and OpenAlex for DOI/source metadata, citation availability, retraction/open-access signals, and source disambiguation.
   - Consider Zotero-compatible import/export formats such as BibTeX/RIS/CSL JSON for operator handoff.
   - Keep downloaded papers, metadata cache, and derived evidence inside the ignored case workspace.
   - Preserve the manual `thesis-literature-citation-review` workflow as the source of judgment.
