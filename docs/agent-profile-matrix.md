# Codex Agent Role Profile Matrix

This matrix maps repo-local workflow skills to Codex agent role profiles. It is
about `.codex/agents/*` role profiles, not case `Reviewer profile:` preference
files. Keep the detailed workflow procedure in `.agents/skills/*/SKILL.md`; this
page records routing, sandbox, output ownership, and review separation.

The structured source of truth is
`src/thesis_review_workflow/agent_profiles.py`. Update that registry first, then
keep this table synchronized.

This matrix is not the workflow-profile registry. Workflow profiles such as
`supervisor_feedback`, `supervisor_report`, `opponent_review`,
`opponent_materials`, and `opponent_report_review` are registered in
`src/thesis_review_workflow/review_profiles.py`; this page only maps the
spawned Codex role profiles used by those workflows.

Profile terms are intentionally separate:

- workflow profiles select the case workflow and closeout surface;
- wave workflows and materiality profiles decide which role evidence is needed;
- Codex agent profiles select the spawned reviewer role from `.codex/agents/`;
- reviewer preference profiles calibrate personal style and assessment
  preferences for the current supervisor or opponent.

The V1 `work/report_calibration_basis.json` application contract is scoped to
opponent reports only (`calibration_scope: opponent_report`). Supervisor report
workflows continue to use their supervisor-report trace, confirmation, review,
and optional supervisor-report calibration artifacts; do not route the
opponent-report `check-report-calibration` gate into supervisor report
closeout until a separate convergence slice explicitly changes that contract.

Role skills should point here instead of redefining those categories.

Command routing: `scripts/<tool>` examples in this document are Linux/dev
shorthand and logical workflow command names. On Windows, package the workflow
tools first and use `dist\workflow-tools\bin\<tool>.cmd` or the matching
PowerShell launcher; do not run or click extensionless `scripts/<tool>` files.

## Routing Matrix

| Skill or source | Status | Codex agent role profile | Kind | Sandbox | Owned outputs / allowed writes | Review separation | Validators |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `AGENTS.md:text-structure-assignment-coverage` | `profile` | `thesis_text_reviewer` | evidence-producer | workspace-write | `work/supervisor_packets/text_assignment_findings.md`, `work/opponent_packets/text_structure_assignment_findings.md` | downstream synthesis decides use | none |
| `thesis-code-consistency` | `profile` | `thesis_code_consistency_reviewer` | evidence-producer | workspace-write | `outputs/code_consistency.md` | standalone review by `thesis_evidence_calibrator`, or downstream synthesis review for used findings | `scripts/check-code-consistency` |
| `thesis-code-quality-review` | `profile` | `thesis_code_quality_reviewer` | evidence-producer | workspace-write | `outputs/code_quality_review.md` | standalone review by `thesis_evidence_calibrator`, or downstream synthesis review for used findings | `scripts/check-code-quality-review` |
| `thesis-quantitative-claims-review` | `profile` | `thesis_quantitative_claims_reviewer` | evidence-producer | workspace-write | `work/quantitative_claims.json` | standalone review by `thesis_evidence_calibrator`, or downstream synthesis review for used findings | `scripts/check-evaluation-claims` |
| `thesis-github-code-intake` | `profile` | `thesis_github_code_intake_reviewer` | evidence-producer | workspace-write | `inputs/github/**`, `work/github/**`, `outputs/github_code_intake.md`; no upstream writes | standalone review by `thesis_evidence_calibrator`, or downstream synthesis review for used findings | `scripts/import-github-code` |
| `thesis-revision-diff` | `profile` | `thesis_revision_diff_reviewer` | evidence-producer | workspace-write | `outputs/revision_diff.md` | standalone review by `thesis_evidence_calibrator`, or downstream synthesis review for used findings | `scripts/check-revision-diff` |
| `thesis-figure-media-review` | `profile` | `thesis_figure_media_reviewer` | evidence-producer | workspace-write | `work/figure_media/visual_inventory.jsonl`, `outputs/figure_media_review.md` | standalone review by `thesis_evidence_calibrator`, or downstream synthesis review for used findings | `scripts/check-figure-media-review` |
| `thesis-literature-citation-review` | `profile` | `thesis_literature_citation_reviewer` | evidence-producer | workspace-write | `work/literature/source_acquisition.json`, `outputs/literature_citation_review.md` | standalone review by `thesis_evidence_calibrator`, or downstream synthesis review for used findings | `scripts/check-literature-citation-review` |
| `thesis-typography-formal-review` | `profile` | `thesis_typography_formal_reviewer` | evidence-producer | workspace-write | `outputs/typography_formal_review.md` | standalone review by `thesis_evidence_calibrator`, or downstream synthesis review for used findings | `scripts/check-typography-formal` |
| `thesis-theses-similarity-review` | `profile` | `thesis_theses_similarity_reviewer` | evidence-producer | workspace-write | `work/theses_similarity/intake.json`, `work/theses_similarity/assessment.json`, `work/theses_similarity/review_draft.md`, `outputs/theses_similarity_review.md`; standalone approval records are written only after independent review | standalone review by `thesis_evidence_calibrator`, or downstream synthesis review for non-standalone internal use | `scripts/check-theses-similarity-report` |
| `thesis-supervisor-feedback` | `parent-owned` | none | parent-orchestration | parent-orchestration | `work/feedback_student_draft.md` | sendable review by `thesis_supervisor_feedback_reviewer` | `scripts/check-review-wave --workflow supervisor_feedback --wave draft`, `scripts/check-feedback-output`, `scripts/check-feedback-language` |
| `thesis-supervisor-feedback-review` | `profile` | `thesis_supervisor_feedback_reviewer` | final-reviewer | workspace-write | `outputs/feedback_student.md`, `work/reviews/supervisor_feedback_review.json` | must be different from the feedback generator | `scripts/check-feedback-output`, `scripts/check-feedback-language` |
| `thesis-supervisor-report` | `parent-owned` | none | parent-orchestration | parent-orchestration | `work/supervisor_report_trace.json`, `work/vedouci_posudek_draft.md` | formal review by `thesis_supervisor_report_reviewer` | `scripts/check-supervisor-report-ready`, `scripts/check-review-wave --workflow supervisor_report --wave draft` |
| `thesis-supervisor-report-review` | `profile` | `thesis_supervisor_report_reviewer` | final-reviewer | workspace-write | `outputs/vedouci_posudek_revidovany.md`, `work/reviews/supervisor_report_review.json` | must be different from the report generator/finalizer | `scripts/check-supervisor-report` |
| `thesis-supervisor-opponent-feedback-learning` | `parent-owned` | none | parent-orchestration | parent-orchestration | `work/external_opponent_report_intake.json`, `work/external_opponent_feedback_findings.json`, `work/supervisor_learning_candidates.json`, `outputs/external_opponent_feedback_analysis.md` | independent review by `thesis_evidence_calibrator` before the analysis becomes durable operator evidence | `scripts/check-external-opponent-feedback --require-analysis` |
| `thesis-opponent-materials` | `parent-owned` | none | parent-orchestration | parent-orchestration | `work/oponent_podklady_draft.md`, `outputs/oponent_podklady.md` | reviewed materials by `thesis_opponent_materials_reviewer` | `scripts/check-review-wave --workflow opponent_materials --wave draft` |
| `thesis-opponent-materials-review` | `profile` | `thesis_opponent_materials_reviewer` | final-reviewer | workspace-write | `outputs/oponent_podklady_revidovane.md`, `work/opponent_report_trace.json`, `work/reviews/opponent_materials_review.json` | must be different from the materials generator | `scripts/check-opponent-materials`, `scripts/check-opponent-report --mode canonical` |
| `thesis-opponent-report-review` | `profile` | `thesis_opponent_report_reviewer` | final-reviewer | workspace-write | `outputs/feedback_k_posudku.md`, `work/reviews/opponent_report_review.json` | fresh review is required after material rewrites; review basis is normally `outputs/oponent_posudek_navrh.md`; approval checks use mode-specific helper IDs, never generic `check-opponent-report` | `scripts/check-review-wave --workflow opponent_report --wave draft`, `scripts/check-opponent-report --mode canonical`, `scripts/export-opponent-report`, `scripts/check-opponent-report --mode clean`, conditional `scripts/check-report-calibration` for calibration-bound report basis or typed no-applicable-calibration limitation |
| `AGENTS.md:standalone-evidence-calibration` | `profile` | `thesis_evidence_calibrator` | calibrator | workspace-write | `work/supervisor_packets/evidence_calibration_findings.md`, `work/opponent_packets/evidence_calibration_findings.md`, `work/reviews/external_opponent_feedback_review.json`; reviewer verdict remains chat-only unless a workflow asks for the sidecar or approval record | cannot review its own generated evidence | none |
| `historical-opponent-calibration` | `deferred` | none | generator | not-spawned | none in this profile registry | private calibration workflow; no durable spawned role yet | `scripts/check-opponent-calibration-profile` when the workflow is run |
| `historical-supervisor-report-calibration` | `deferred` | none | generator | not-spawned | none in this profile registry | private calibration workflow; no durable spawned role yet | `scripts/check-supervisor-report-calibration-profile` when the workflow is run |

## Routing Decisions

- Packet-scoped text/assignment and evidence-calibration findings are
  role-owned sidecars when their packet roles are active. They are not parent
  filler artifacts.
- Theses.cz no-concern evidence may be registered as the validated structured
  assessment JSON and then covered by a reviewed synthesis manifest with the
  `silent_internal_evidence:no_material_concern` marker. That path does not
  require `outputs/theses_similarity_review.md` unless the assessment records a
  non-silent or reviewer-verification concern.

- `profile` means a stable `.codex/agents/*` profile either exists or is planned
  in the current rollout.
- `parent-owned` means the main agent owns orchestration or synthesis and the
  independent review profile is named separately.
- `deferred` means no durable spawned profile is added yet because the role is a
  private calibration workflow without a stable repeated spawned boundary.
- Evidence producers cannot mark the same standalone evidence artifact reviewed
  for final standalone use. Use `thesis_evidence_calibrator` or a more specific
  final-review profile, unless a typed limitation records why the artifact is
  not treated as final standalone evidence.
