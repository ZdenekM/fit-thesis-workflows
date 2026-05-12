"""Role-specific packet generation for supervisor-feedback agents."""

from __future__ import annotations

from pathlib import Path

from thesis_review_workflow.review_packets import (
    CASE_INPUTS,
    COMMON_CONSTRAINTS,
    MECHANICAL_MODEL,
    MECHANICAL_REASONING,
    PROFILE_INPUTS,
    PacketRole,
    current_evidence_snapshot_section,
    existing_paths,
    extracted_text_paths,
    first_nonempty_lines,
    generated_role_paths,
    late_communications_section,
    materiality_next_actions_section,
    omen_advisory_section,
    path_list,
    previous_feedback_index,
    prune_inactive_packets,
    quantitative_claims_handoff_section,
    role_is_active,
    status_list,
    text_list,
    top_level_paths,
)

PACKET_DIR_REL = Path("work/supervisor_packets")
SCHEMA_VERSION = "supervisor-feedback-packet-v1"
BASE_INPUTS = (
    "notes/assignment.md",
    "notes/round-notes.md",
    "outputs/revision_diff.md",
)
ADVISORY_ARTIFACTS = (
    "work/current_evidence_snapshot.json",
    "work/assignment_coverage_agent.json",
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
    "outputs/revision_diff.md",
)

PACKET_ROLES = (
    PacketRole(
        key="text_assignment",
        title="Text And Assignment Coverage",
        skill="thesis-supervisor-feedback",
        expected_output="work/supervisor_packets/text_assignment_findings.md",
        mission=(
            "Assess thesis structure, assignment coverage, contribution clarity, and phase-fit for student feedback."
        ),
        focus=(
            "assignment coverage and missing submission evidence",
            "thesis structure and reader orientation",
            "contribution clarity",
            "student-facing priority of remaining work",
        ),
        role_inputs=(
            "notes/assignment.md",
            "outputs/revision_diff.md",
            "work/assignment_coverage_agent.json",
        ),
        constraints=(
            "Translate findings into actions the student can still take in the current phase.",
            "Do not repeat prior feedback mechanically; use revision diff or previous feedback index when available.",
        ),
    ),
    PacketRole(
        key="code_consistency",
        title="Text-Code Consistency And Reproducibility",
        skill="thesis-code-consistency",
        expected_output="outputs/code_consistency.md",
        mission=(
            "Check whether thesis claims are supported by submitted code, README, configs, tests, and result artifacts."
        ),
        focus=(
            "implemented-feature claims",
            "metric and experiment claims that depend on code or data",
            "static reproducibility classification",
            "student-facing fixes for unsupported claims",
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
            "Use Omen MCP as advisory static-analysis evidence when available, never as an operator prerequisite.",
        ),
        activation="code",
    ),
    PacketRole(
        key="figure_media",
        title="Figure And Media Evidence",
        skill="thesis-figure-media-review",
        expected_output="outputs/figure_media_review.md",
        mission=(
            "Inspect figure, table, screenshot, result-image, diagram, and media evidence that affects student "
            "feedback."
        ),
        focus=(
            "visual evidence for result and functionality claims",
            "caption and nearby-text claim alignment",
            "presentation video/demo evidence boundaries",
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
            "Convert visual issues into the smallest useful student action.",
        ),
        activation="existing_artifact",
        activation_paths=("work/review_materiality/supervisor_feedback/figure_media.json",),
        activation_workflow_profile="supervisor_feedback",
    ),
    PacketRole(
        key="literature_citation",
        title="Literature And Citation Evidence",
        skill="thesis-literature-citation-review",
        expected_output="outputs/literature_citation_review.md",
        mission="Check cited literature relevance, source availability, and claim support for student feedback.",
        focus=(
            "unsupported literature-backed claims",
            "missing or inaccessible sources",
            "relevance of cited sources to thesis contribution",
            "phase-appropriate literature fixes",
        ),
        role_inputs=(
            "outputs/literature_citation_review.md",
            "outputs/revision_diff.md",
        ),
        constraints=(
            "Suggest new literature only when it addresses a clear thesis gap.",
            "Keep citation feedback actionable and phase-appropriate.",
        ),
        activation="existing_artifact",
        activation_paths=("work/review_materiality/supervisor_feedback/literature_citation.json",),
        activation_workflow_profile="supervisor_feedback",
    ),
    PacketRole(
        key="typography_formal",
        title="Typography And Formal Presentation",
        skill="thesis-typography-formal-review",
        expected_output="outputs/typography_formal_review.md",
        mission="Assess repeated formal, typography, language, and presentation patterns relevant to student action.",
        focus=(
            "late-stage formal presentation risk",
            "language-calibrated repeated typography patterns",
            "readability and professional presentation",
            "manual checks for layout-sensitive evidence",
        ),
        role_inputs=(
            "outputs/typography_formal_review.md",
            "outputs/revision_diff.md",
        ),
        constraints=(
            "Summarize repeated patterns, not a line-by-line typo inventory.",
            "Prioritize issues that can still affect submission quality or opponent perception.",
        ),
        activation="existing_artifact",
        activation_paths=("work/review_materiality/supervisor_feedback/typography_formal.json",),
        activation_workflow_profile="supervisor_feedback",
    ),
    PacketRole(
        key="quantitative_claims",
        title="Quantitative Claims Review",
        skill="thesis-quantitative-claims-review",
        expected_output="work/quantitative_claims.json",
        mission=(
            "Sanity-check material quantitative, evaluation, experiment, metric, performance, and result claims "
            "before student-facing synthesis."
        ),
        focus=(
            "unit and scale interpretation",
            "baseline, comparator, sample-size, and practical-magnitude context",
            "reproducibility and evidence anchors",
            "overclaim risk and proportionate student action",
        ),
        role_inputs=(
            "work/quantitative_claims.json",
            "work/review_materiality/supervisor_feedback/index.json",
            "work/code_reproducibility.json",
            "outputs/code_consistency.md",
            "outputs/figure_media_review.md",
        ),
        constraints=(
            "Write or update only the structured `work/quantitative_claims.json` contract.",
            "Do not infer metric meaning from deterministic raw-text matching; use semantic review with evidence "
            "anchors.",
            "Keep wording proportionate: unsupported or context-poor numbers should become limitations or student "
            "actions.",
        ),
        activation="existing_artifact_or_next_action",
        activation_paths=("work/quantitative_claims.json",),
        activation_workflow_profile="supervisor_feedback",
    ),
    PacketRole(
        key="evidence_calibration",
        title="Evidence Labels And Student-Action Calibration",
        skill="thesis-supervisor-feedback-review",
        expected_output="work/supervisor_packets/evidence_calibration_findings.md",
        mission="Check whether evidence labels, severity, limitations, and student-action priority are fair.",
        focus=(
            "P0/P1 priority calibration",
            "confidence-label correctness",
            "action-budget realism",
            "limitations that must remain visible",
        ),
        role_inputs=(
            "work/quantitative_claims.json",
            "outputs/code_consistency.md",
            "outputs/code_quality_review.md",
            "outputs/figure_media_review.md",
            "outputs/literature_citation_review.md",
            "outputs/typography_formal_review.md",
        ),
        constraints=(
            "Do not manufacture certainty; lower confidence or mark manual checks when evidence is incomplete.",
            "Keep final-sprint feedback focused on actions with realistic payoff.",
        ),
        activation="existing_artifact",
        activation_paths=(
            "work/quantitative_claims.json",
            "outputs/code_consistency.md",
            "outputs/code_quality_review.md",
            "outputs/figure_media_review.md",
            "outputs/literature_citation_review.md",
            "outputs/typography_formal_review.md",
        ),
    ),
    PacketRole(
        key="current_evidence_snapshot",
        title="Current Evidence Snapshot",
        skill="mechanical-validator-backed-helper",
        expected_output="work/current_evidence_snapshot.json",
        mission=(
            "Capture drift-prone evidence identity, hashes, freshness notes, and limitations for supervisor feedback."
        ),
        focus=(
            "current code and GitHub intake identity",
            "targeted smoke-test or diagnostic notes",
            "late communications",
            "freshness limitations that feedback must preserve",
        ),
        role_inputs=(
            "work/current_evidence_snapshot.json",
            "outputs/github_code_intake.md",
            "work/review_manifest.json",
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
        title="Supervisor Feedback Synthesis",
        skill="thesis-supervisor-feedback",
        expected_output="work/feedback_student_draft.md",
        mission="Integrate role findings into a coherent student-facing supervisor feedback draft.",
        focus=(
            "minimal useful student actions",
            "assignment coverage and technical truth",
            "previous-feedback deltas",
            "phase and deadline calibration",
        ),
        role_inputs=ADVISORY_ARTIFACTS,
        constraints=(
            "Do not leave the operator with separate reviewer notes only.",
            "Write the draft to work/feedback_student_draft.md and run independent supervisor-feedback review before "
            "final output.",
        ),
        activation="existing_artifact",
        activation_paths=(
            "work/quantitative_claims.json",
            "outputs/code_consistency.md",
            "outputs/code_quality_review.md",
            "outputs/figure_media_review.md",
            "outputs/literature_citation_review.md",
            "outputs/typography_formal_review.md",
            "outputs/revision_diff.md",
        ),
    ),
    PacketRole(
        key="final_review",
        title="Supervisor Feedback Independent Review",
        skill="thesis-supervisor-feedback-review",
        expected_output="outputs/feedback_student.md",
        mission="Review and harden a supervisor feedback draft into final sendable Markdown.",
        focus=(
            "P0/P1 evidence support",
            "student-facing tone and actionability",
            "language setting",
            "stale or overconfident claims",
        ),
        role_inputs=(
            "work/feedback_student_draft.md",
            "work/reviews/feedback_student_review.json",
        ),
        constraints=(
            "Do not write final feedback without checking the current draft path.",
            "Material edits after review reopen the artifact as draft.",
        ),
        activation="check",
        activation_check=("check-review-wave", "--workflow", "supervisor_feedback", "--wave", "draft"),
    ),
)


def render_packet(
    case_id: str,
    round_id: str,
    generated_at: str,
    round_dir: Path,
    role: PacketRole,
    *,
    deadline_context: str,
) -> str:
    case_dir = round_dir.parents[1]
    repo_root = round_dir.parents[3]
    inputs = top_level_paths(round_dir, "inputs")
    notes = top_level_paths(round_dir, "notes")
    extracted = extracted_text_paths(round_dir)
    assignment_summary = first_nonempty_lines(round_dir / "notes" / "assignment.md")
    previous_feedback = previous_feedback_index(round_dir)
    role_existing = existing_paths(round_dir, role.role_inputs, case_id=case_id, round_id=round_id)
    advisory_existing = existing_paths(round_dir, ADVISORY_ARTIFACTS, case_id=case_id, round_id=round_id)
    role_constraints = COMMON_CONSTRAINTS + role.constraints
    active_packets = generated_role_paths(PACKET_ROLES, round_dir, case_id=case_id, round_id=round_id)
    optional_sections = [
        current_evidence_snapshot_section(round_dir, case_id=case_id, round_id=round_id),
        materiality_next_actions_section(
            round_dir,
            case_id=case_id,
            round_id=round_id,
            workflow_profile="supervisor_feedback",
        ),
        quantitative_claims_handoff_section(round_dir, case_id=case_id, round_id=round_id),
        late_communications_section(round_dir),
    ]
    if role.key == "code_quality":
        optional_sections.append(omen_advisory_section(round_dir))
    rendered_deadline = deadline_context.strip() or "Deadline context unresolved; run `scripts/supervisor-deadline`."

    return "\n".join(
        [
            f"# Supervisor Feedback Packet: {role.title}",
            "",
            f"Schema version: `{SCHEMA_VERSION}`",
            f"Case: `{case_id}`",
            f"Round: `{round_id}`",
            f"Generated at: `{generated_at}`",
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
            "## Required Base Inputs",
            "",
            status_list(case_dir, CASE_INPUTS),
            status_list(round_dir, BASE_INPUTS),
            "## Reviewer Profile Inputs",
            "",
            status_list(repo_root, PROFILE_INPUTS),
            "## Assignment Summary",
            "",
            text_list(assignment_summary),
            "## Supervisor Deadline Context",
            "",
            "```text",
            rendered_deadline,
            "```",
            "",
            "## Previous Feedback Index",
            "",
            text_list(previous_feedback),
            "## Prepared Code Roots",
            "",
            status_list(
                round_dir,
                ("work/code_workspace.md", "work/serena_roots.json", "work/code_reproducibility.json"),
                case_id=case_id,
                round_id=round_id,
            ),
            "## Available Round Inputs",
            "",
            path_list(inputs),
            "## Available Round Notes",
            "",
            path_list(notes),
            "## Extracted Thesis Text",
            "",
            path_list(extracted),
            "## Role-Specific Artifacts",
            "",
            status_list(round_dir, role.role_inputs, case_id=case_id, round_id=round_id),
            "## Existing Advisory Or Evidence Artifacts",
            "",
            path_list(advisory_existing),
            "## Missing Role Inputs To Treat As Limitations",
            "",
            path_list([rel_path for rel_path in role.role_inputs if rel_path not in role_existing]),
            "## Final-Sprint Action Budget",
            "",
            "- Use the deadline calibration above to keep feedback focused on blockers, assignment coverage, "
            "technical truth, and submission artifacts.",
            "- Prefer one concrete action over several low-level diagnostics unless the raw detail is needed for "
            "technical truth.",
            "",
            "## Open Full Artifacts Only If Needed",
            "",
            "- Start from `## Synthesis Handoff` sections when available.",
            "- Open full evidence artifacts for P0/P1 verification, contradictions, reviewer challenges, or "
            "technical-truth checks.",
            "",
            "## Constraints",
            "",
            text_list(list(role_constraints)),
            *optional_sections,
            "## Review Handoff",
            "",
            "- Return concise findings with evidence anchors, limitations, and the smallest useful student action.",
            "- Prefer tables only when they make coverage or severity easier to audit.",
            "- Do not paste raw packet boilerplate into student-facing feedback.",
            "",
        ]
    )


def generate_packets(
    case_id: str,
    round_id: str,
    generated_at: str,
    round_dir: Path,
    *,
    deadline_context: str,
) -> list[Path]:
    packet_dir = round_dir / PACKET_DIR_REL
    packet_dir.mkdir(parents=True, exist_ok=True)
    prune_inactive_packets(packet_dir, PACKET_ROLES, round_dir, case_id=case_id, round_id=round_id)
    written: list[Path] = []
    for role in PACKET_ROLES:
        if not role_is_active(round_dir, role, case_id=case_id, round_id=round_id):
            continue
        path = packet_dir / f"{role.key}.md"
        path.write_text(
            render_packet(
                case_id,
                round_id,
                generated_at,
                round_dir,
                role,
                deadline_context=deadline_context,
            ),
            encoding="utf-8",
        )
        written.append(path)
    return written
