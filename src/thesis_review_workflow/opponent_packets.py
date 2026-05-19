"""Role-specific packet generation for opponent-review agents."""

from __future__ import annotations

from pathlib import Path

from thesis_review_workflow.review_packets import (
    COMMON_BRIEFING_REL,
    COMMON_CONSTRAINTS,
    MECHANICAL_MODEL,
    MECHANICAL_REASONING,
    PacketRole,
    existing_paths,
    generated_role_paths,
    materiality_next_actions_section,
    omen_advisory_section,
    path_list,
    prune_inactive_packets,
    reusable_handoff_refs_section,
    role_is_active,
    sha256_file,
    status_list,
    submission_bundle_visibility_section,
    text_list,
    write_common_briefing,
    write_text_if_changed,
)
from thesis_review_workflow.theses_similarity import (
    THESES_SIMILARITY_ASSESSMENT_REL,
    THESES_SIMILARITY_EXTRACTED_TEXT_REL,
    THESES_SIMILARITY_INTAKE_REL,
    THESES_SIMILARITY_REPORT_REL,
    THESES_SIMILARITY_REVIEW_REL,
)

PACKET_DIR_REL = Path("work/opponent_packets")
SCHEMA_VERSION = "opponent-review-packet-v1"
BASE_INPUTS = (
    "notes/assignment.md",
    "notes/opponent-intake.md",
    "notes/round-notes.md",
)
ADVISORY_ARTIFACTS = (
    "work/current_evidence_snapshot.json",
    "work/assignment_coverage_agent.json",
    "work/evidence_requirements.json",
    "work/code_reproducibility.json",
    "work/quantitative_claims.json",
    "work/media_presence_inventory.jsonl",
    "work/figure_media/visual_inventory.jsonl",
    "work/code_workspace.md",
    "work/serena_roots.json",
    "outputs/github_code_intake.md",
    "outputs/code_consistency.md",
    "outputs/code_quality_review.md",
    "outputs/literature_citation_review.md",
    "outputs/figure_media_review.md",
    "outputs/typography_formal_review.md",
    THESES_SIMILARITY_INTAKE_REL,
    THESES_SIMILARITY_ASSESSMENT_REL,
    THESES_SIMILARITY_REVIEW_REL,
    "outputs/revision_diff.md",
)

PACKET_ROLES = (
    PacketRole(
        key="text_structure_assignment",
        title="Text Structure And Assignment Coverage",
        skill="thesis-opponent-materials",
        expected_output="work/opponent_packets/text_structure_assignment_findings.md",
        mission=(
            "Assess rendered-thesis structure, assignment fulfillment, and IS-item relevance " "for opponent synthesis."
        ),
        focus=(
            "point-by-point assignment coverage",
            "chapter and section structure",
            "clarity of contribution and thesis map",
            "fair defense questions tied to assignment scope",
        ),
        role_inputs=(
            "work/assignment_coverage_agent.json",
            "outputs/revision_diff.md",
        ),
        constraints=(
            "Treat assignment coverage as advisory; final grade calibration remains with synthesis "
            "and the human opponent.",
            "Do not turn heading polish into a grade-impacting issue unless it materially harms orientation.",
        ),
    ),
    PacketRole(
        key="code_consistency",
        title="Text-Code Consistency And Reproducibility",
        skill="thesis-code-consistency",
        expected_output="outputs/code_consistency.md",
        mission=(
            "Check whether thesis claims are supported by submitted code, README, configs, tests, "
            "and result artifacts."
        ),
        focus=(
            "implemented-feature claims",
            "experiment and metric claims that depend on code or data",
            "static reproducibility classification",
            "missing or contradictory code evidence",
        ),
        role_inputs=(
            "work/code_workspace.md",
            "work/serena_roots.json",
            "work/code_reproducibility.json",
            "outputs/github_code_intake.md",
        ),
        constraints=(
            "Do not run submitted code unless the operator explicitly authorized that run.",
            "Use Serena on prepared code roots for non-trivial Python or supported-code inspection when available.",
        ),
        activation="code",
    ),
    PacketRole(
        key="code_quality",
        title="Code Quality And Design",
        skill="thesis-code-quality-review",
        expected_output="outputs/code_quality_review.md",
        mission="Assess implementation architecture, maintainability, runtime risks, tests, and developer evidence.",
        focus=(
            "architecture and module boundaries",
            "runtime validation and error handling",
            "test strategy and smoke-test readiness",
            "README/build/developer documentation",
        ),
        role_inputs=(
            "work/code_workspace.md",
            "work/serena_roots.json",
            "work/code_reproducibility.json",
            "outputs/github_code_intake.md",
        ),
        constraints=(
            "Separate implementation quality from thesis text-code mismatch.",
            "Do not punish a thesis prototype for not being a production system; calibrate to assignment scope.",
            "Use Omen advisory static-analysis evidence over prepared submitted-code roots when available; "
            "treat MCP zero-file results on non-empty roots as a tool/path limitation, never as an "
            "operator prerequisite.",
        ),
        activation="code",
    ),
    PacketRole(
        key="figure_media",
        title="Figure And Media Evidence",
        skill="thesis-figure-media-review",
        expected_output="outputs/figure_media_review.md",
        mission=(
            "Inspect figure, table, screenshot, result-image, diagram, and media evidence that "
            "affects opponent claims."
        ),
        focus=(
            "visual evidence for result and functionality claims",
            "caption and nearby-text claim alignment",
            "presence versus inspected visual content",
            "figure/media changes between rounds",
        ),
        role_inputs=(
            "work/media_presence_inventory.jsonl",
            "work/figure_media/visual_inventory.jsonl",
            "outputs/figure_media_review.md",
            "outputs/revision_diff.md",
        ),
        constraints=(
            "Do not treat inventoried-only media as visually verified evidence.",
            "Use PDF/source-asset inspection status when making visual-content claims.",
        ),
        activation="existing_artifact",
        activation_paths=("work/review_materiality/opponent_review/figure_media.json",),
        activation_workflow_profile="opponent_review",
    ),
    PacketRole(
        key="literature_citation",
        title="Literature And Citation Evidence",
        skill="thesis-literature-citation-review",
        expected_output="outputs/literature_citation_review.md",
        mission="Check literature relevance, source availability, citation support, and defensibility of cited claims.",
        focus=(
            "unsupported literature-backed claims",
            "missing or inaccessible sources",
            "citation relevance to assignment and contribution",
            "overstated novelty or state-of-the-art claims",
        ),
        role_inputs=(
            "outputs/literature_citation_review.md",
            "outputs/revision_diff.md",
        ),
        constraints=(
            "For opponent work, review relevance and defensibility; do not write supervisor-style literature coaching.",
            "State source-access limitations explicitly.",
        ),
        activation="existing_artifact",
        activation_paths=("work/review_materiality/opponent_review/literature_citation.json",),
        activation_workflow_profile="opponent_review",
    ),
    PacketRole(
        key="typography_formal",
        title="Typography And Formal Presentation",
        skill="thesis-typography-formal-review",
        expected_output="outputs/typography_formal_review.md",
        mission="Assess repeated formal, typography, language, and presentation patterns relevant to opponent wording.",
        focus=(
            "late-stage formal presentation risk",
            "language-calibrated repeated typography patterns",
            "thesis readability and professional presentation",
            "manual checks for layout-sensitive evidence",
        ),
        role_inputs=(
            "outputs/typography_formal_review.md",
            "outputs/revision_diff.md",
        ),
        constraints=(
            "Summarize repeated patterns, not a line-by-line typo inventory.",
            "Calibrate by thesis language and final-submission phase.",
        ),
        activation="existing_artifact",
        activation_paths=("work/review_materiality/opponent_review/typography_formal.json",),
        activation_workflow_profile="opponent_review",
    ),
    PacketRole(
        key="quantitative_claims",
        title="Quantitative Claims Review",
        skill="thesis-quantitative-claims-review",
        expected_output="work/quantitative_claims.json",
        mission=(
            "Sanity-check material quantitative, evaluation, experiment, metric, performance, and result claims "
            "before opponent-materials synthesis."
        ),
        focus=(
            "unit and scale interpretation",
            "baseline, comparator, sample-size, and practical-magnitude context",
            "reproducibility and evidence anchors",
            "overclaim risk and grade/report defensibility",
        ),
        role_inputs=(
            "work/quantitative_claims.json",
            "work/review_materiality/opponent_review/index.json",
            "work/evidence_requirements.json",
            "work/code_reproducibility.json",
            "outputs/code_consistency.md",
            "outputs/figure_media_review.md",
        ),
        constraints=(
            "Write or update only the structured `work/quantitative_claims.json` contract.",
            "Do not infer metric meaning from deterministic raw-text matching; use semantic review with evidence "
            "anchors.",
            "Keep opponent impact proportionate to the available baseline, reproducibility, and practical context.",
        ),
        activation="existing_artifact_or_next_action",
        activation_paths=("work/quantitative_claims.json",),
        activation_workflow_profile="opponent_review",
    ),
    PacketRole(
        key="theses_similarity",
        title="Theses.cz Similarity Report Review",
        skill="thesis-theses-similarity-review",
        expected_output=THESES_SIMILARITY_REVIEW_REL,
        mission="Interpret imported Theses.cz similarity-report evidence before opponent-materials synthesis.",
        focus=(
            "external matches that need opponent attention",
            "repeated-submission self-overlap versus unresolved suspicious overlap",
            "resolved findings that should stay internal",
            "careful opponent wording and defense-question impact for unresolved concerns",
        ),
        role_inputs=(
            THESES_SIMILARITY_REPORT_REL,
            THESES_SIMILARITY_EXTRACTED_TEXT_REL,
            THESES_SIMILARITY_INTAKE_REL,
            THESES_SIMILARITY_ASSESSMENT_REL,
            THESES_SIMILARITY_REVIEW_REL,
            "extracted/thesis.txt",
            "outputs/revision_diff.md",
        ),
        constraints=(
            "Do not infer plagiarism, authorship, or grade impact from a similarity percentage alone.",
            "Do not leak raw report URLs, source internals, hashes, or local paths into opponent-facing prose.",
            "Surface only reviewed unresolved/material concerns; keep no-concern or resolved matches silent.",
        ),
        activation="existing_artifact_or_next_action",
        activation_paths=(THESES_SIMILARITY_REVIEW_REL,),
        activation_workflow_profile="opponent_review",
    ),
    PacketRole(
        key="evidence_calibration",
        title="Evidence Labels And Severity Calibration",
        skill="thesis-opponent-materials-review",
        expected_output="work/opponent_packets/evidence_calibration_findings.md",
        mission=(
            "Check whether evidence labels, risk severity, strengths, limitations, and grading " "calibration are fair."
        ),
        focus=(
            "confidence-label correctness",
            "severity and grade-impact calibration",
            "strengths supported by evidence",
            "manual checks before writing the final report",
        ),
        role_inputs=(
            "work/assignment_coverage_agent.json",
            "work/evidence_requirements.json",
            "work/code_reproducibility.json",
            "work/quantitative_claims.json",
            "outputs/code_consistency.md",
            "outputs/code_quality_review.md",
            "outputs/figure_media_review.md",
            "outputs/literature_citation_review.md",
            "outputs/typography_formal_review.md",
            THESES_SIMILARITY_REVIEW_REL,
        ),
        constraints=(
            "Do not manufacture certainty; lower confidence or mark manual checks when evidence is incomplete.",
            "Keep grading calibration as intervals and rationale, not precise point verdicts.",
        ),
        activation="existing_artifact",
        activation_paths=(
            "work/quantitative_claims.json",
            "outputs/code_consistency.md",
            "outputs/code_quality_review.md",
            "outputs/figure_media_review.md",
            "outputs/literature_citation_review.md",
            "outputs/typography_formal_review.md",
            THESES_SIMILARITY_REVIEW_REL,
        ),
    ),
    PacketRole(
        key="current_evidence_snapshot",
        title="Current Evidence Snapshot",
        skill="mechanical-validator-backed-helper",
        expected_output="work/current_evidence_snapshot.json",
        mission="Capture drift-prone evidence identity, hashes, freshness notes, and limitations for opponent roles.",
        focus=(
            "current code and GitHub intake identity",
            "reviewed materials, trace, draft, and approval-record hashes",
            "late communications and targeted diagnostic notes",
            "freshness limitations that synthesis must preserve",
        ),
        role_inputs=(
            "work/current_evidence_snapshot.json",
            "outputs/github_code_intake.md",
            "work/review_manifest.json",
            "work/opponent_report_trace.json",
        ),
        constraints=(
            "Do not make semantic quality claims; record structured state and explicit limitations only.",
            "If freshness affects readiness, write or update a structured/hash-bound artifact before relying on it.",
        ),
        model=MECHANICAL_MODEL,
        reasoning=MECHANICAL_REASONING,
        model_note=(
            "Mechanical helper role; Spark is acceptable only because downstream semantic roles consume validated "
            "state."
        ),
    ),
    PacketRole(
        key="synthesis",
        title="Opponent Materials Synthesis",
        skill="thesis-opponent-materials",
        expected_output="work/oponent_podklady_draft.md",
        mission="Integrate role findings into coherent internal opponent materials for independent review.",
        focus=(
            "assignment fulfillment",
            "evidence ledger and IS-item coverage",
            "technical correctness and realization output",
            "balanced strengths, risks, defense questions, and grading calibration",
        ),
        role_inputs=ADVISORY_ARTIFACTS,
        constraints=(
            "Do not write the final IS-ready opponent report.",
            "Run an independent thesis-opponent-materials-review pass before treating materials as ready.",
        ),
        activation="existing_artifact",
        activation_paths=(
            "work/quantitative_claims.json",
            "outputs/code_consistency.md",
            "outputs/code_quality_review.md",
            "outputs/figure_media_review.md",
            "outputs/literature_citation_review.md",
            "outputs/typography_formal_review.md",
            THESES_SIMILARITY_REVIEW_REL,
            "outputs/revision_diff.md",
        ),
    ),
    PacketRole(
        key="materials_review",
        title="Opponent Materials Independent Review",
        skill="thesis-opponent-materials-review",
        expected_output="outputs/oponent_podklady_revidovane.md",
        mission="Review and harden drafted internal opponent materials before trace/report work.",
        focus=(
            "evidence-label correctness",
            "grade-impacting claim support",
            "confidence and limitation preservation",
            "reviewed-materials readiness for trace generation",
        ),
        role_inputs=(
            "work/oponent_podklady_draft.md",
            "outputs/oponent_podklady.md",
            "work/reviews/opponent_materials_review.json",
        ),
        constraints=(
            "Start from a non-empty draft/materials artifact that passed the relevant shape gate.",
            "Record or refresh a structured review record before downstream trace/report use.",
        ),
        activation="check",
        activation_check=("check-review-wave", "--workflow", "opponent_materials", "--wave", "draft"),
    ),
    PacketRole(
        key="report_trace",
        title="Opponent Report Trace",
        skill="mechanical-validator-backed-helper",
        expected_output="work/opponent_report_trace.json",
        mission="Prepare or refresh the structured opponent report trace from reviewed materials.",
        focus=(
            "reviewed-materials path and hash",
            "IS-item formulations",
            "defense questions",
            "uncertainty ledger and manual checks",
        ),
        role_inputs=(
            "outputs/oponent_podklady_revidovane.md",
            "work/reviews/opponent_materials_review.json",
            "work/opponent_report_trace.json",
        ),
        constraints=(
            "Packetization must not replace the trace with prose summaries.",
            "Do not treat a report draft as ready without current trace validation.",
        ),
        activation="check",
        activation_check=("check-review-wave", "--workflow", "opponent_materials", "--wave", "reviewed"),
        model=MECHANICAL_MODEL,
        reasoning=MECHANICAL_REASONING,
        model_note="Mechanical helper role; Spark is acceptable only for trace/status assembly checked by validators.",
    ),
    PacketRole(
        key="report_review",
        title="Opponent Report Review",
        skill="thesis-opponent-report-review",
        expected_output="outputs/feedback_k_posudku.md",
        mission="Review the clean IS-entry opponent-report proposal before IS submission.",
        focus=(
            "point/comment consistency",
            "evidence and tone defensibility",
            "manual checks before submission",
            "report rewrite suggestions only when needed",
        ),
        role_inputs=(
            "outputs/oponent_posudek_navrh.md",
            "work/oponent_posudek_draft.md",
            "work/opponent_report_trace.json",
            "work/reviews/opponent_report_review.json",
        ),
        constraints=(
            "Use `outputs/oponent_posudek_navrh.md` as the normal report-review basis; open the canonical "
            "draft only for trace/provenance checks.",
            "Do not review an uncalibrated helper draft as final human report text.",
            "If an agent rewrites report prose, run a fresh independent report review.",
        ),
        activation="check",
        activation_check=("check-review-wave", "--workflow", "opponent_report", "--wave", "draft"),
    ),
)


def render_packet(case_id: str, round_id: str, generated_at: str, round_dir: Path, role: PacketRole) -> str:
    role_existing = existing_paths(round_dir, role.role_inputs, case_id=case_id, round_id=round_id)
    role_constraints = COMMON_CONSTRAINTS + role.constraints
    active_packets = generated_role_paths(PACKET_ROLES, round_dir, case_id=case_id, round_id=round_id)
    optional_sections = [
        submission_bundle_visibility_section(round_dir),
        materiality_next_actions_section(
            round_dir,
            case_id=case_id,
            round_id=round_id,
            workflow_profile="opponent_review",
        ),
        reusable_handoff_refs_section(round_dir, case_id=case_id, round_id=round_id),
    ]
    if role.key == "code_quality":
        optional_sections.append(omen_advisory_section(round_dir))
    common_briefing_sha = sha256_file(round_dir / COMMON_BRIEFING_REL) or "missing"

    return "\n".join(
        [
            f"# Opponent Reviewer Packet: {role.title}",
            "",
            f"Schema version: `{SCHEMA_VERSION}`",
            f"Case: `{case_id}`",
            f"Round: `{round_id}`",
            f"Common briefing: `{COMMON_BRIEFING_REL}`",
            f"Common briefing sha256: `{common_briefing_sha}`",
            f"Role key: `{role.key}`",
            f"Skill: `{role.skill}`",
            f"Expected output: `{role.expected_output}`",
            f"Recommended model: `{role.model}`",
            f"Recommended reasoning: `{role.reasoning}`",
            f"Model note: {role.model_note}",
            "",
            "## Mission",
            "",
            role.mission,
            "",
            "## Focus",
            "",
            text_list(list(role.focus)),
            "## Active Packet Set",
            "",
            path_list(active_packets),
            "## Common Briefing",
            "",
            status_list(round_dir, (COMMON_BRIEFING_REL,), case_id=case_id, round_id=round_id),
            "Read the common briefing first for case/profile inputs, round inventory, extracted text refs, "
            "previous feedback refs, submitted-bundle inventory, current evidence snapshots, prepared code roots, "
            "materiality refs, and current context handoffs.",
            "",
            "## Role-Specific Artifacts",
            "",
            status_list(round_dir, role.role_inputs, case_id=case_id, round_id=round_id),
            "## Missing Role Inputs To Treat As Limitations",
            "",
            path_list([rel_path for rel_path in role.role_inputs if rel_path not in role_existing]),
            "## Opponent Report And IS Calibration",
            "",
            "- Preserve confidence labels and manual checks in any grade-impacting finding.",
            "- Use reviewed-materials and trace hashes from structured artifacts when report readiness depends on "
            "freshness.",
            "- Defense questions must point back to assignment, thesis, code, or reviewed-material evidence.",
            "",
            "## Open Full Artifacts Only If Needed",
            "",
            "- Start from the common briefing, current context handoffs, and `## Synthesis Handoff` sections when "
            "available.",
            "- Open full evidence artifacts for material verification, contradictions, confidence-label calibration, "
            "or reviewer challenges.",
            "",
            "## Constraints",
            "",
            text_list(list(role_constraints)),
            *optional_sections,
            "## Review Handoff",
            "",
            "- Return concise findings with evidence anchors and limitations.",
            "- Prefer tables only when they make coverage or severity easier to audit.",
            "- Keep the synthesis artifact coherent; do not paste raw packet boilerplate into final prose.",
            "",
        ]
    )


def generate_packets(case_id: str, round_id: str, generated_at: str, round_dir: Path) -> list[Path]:
    packet_dir = round_dir / PACKET_DIR_REL
    packet_dir.mkdir(parents=True, exist_ok=True)
    write_common_briefing(case_id, round_id, generated_at, round_dir)
    prune_inactive_packets(packet_dir, PACKET_ROLES, round_dir, case_id=case_id, round_id=round_id)
    written: list[Path] = []
    for role in PACKET_ROLES:
        if not role_is_active(round_dir, role, case_id=case_id, round_id=round_id):
            continue
        path = packet_dir / f"{role.key}.md"
        write_text_if_changed(path, render_packet(case_id, round_id, generated_at, round_dir, role))
        written.append(path)
    return written
