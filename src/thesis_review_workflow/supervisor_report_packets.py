"""Role-specific packet generation for formal supervisor-report agents."""

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
    hash_status_list,
    materiality_next_actions_section,
    omen_advisory_section,
    path_list,
    prune_inactive_packets,
    REPORT_CALIBRATION_BASIS_REL,
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

PACKET_DIR_REL = Path("work/supervisor_report_packets")
SCHEMA_VERSION = "supervisor-report-packet-v1"
BASE_INPUTS = (
    "notes/assignment.md",
    "notes/supervisor-report-operator-input.md",
)
OPTIONAL_PRIOR_FEEDBACK_INPUTS = (
    "work/supervisor_report_feedback_history.json",
    "outputs/revision_diff.md",
)
REPORT_ARTIFACTS = (
    "work/supervisor_report_trace.json",
    "work/vedouci_posudek_draft.md",
    "outputs/vedouci_posudek_revidovany.md",
    "work/supervisor_report_confirmation.json",
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
    THESES_SIMILARITY_INTAKE_REL,
    THESES_SIMILARITY_ASSESSMENT_REL,
    THESES_SIMILARITY_REVIEW_REL,
    "outputs/revision_diff.md",
    *REPORT_ARTIFACTS,
)
OUTPUT_CONTRACTS: dict[str, dict[str, tuple[str, ...]]] = {
    "code_consistency": {
        "outputs": ("outputs/code_consistency.md",),
        "shape": (
            "Markdown headings: # Soulad textu s kodem; Rozsah kontroly; Podporena tvrzeni; "
            "Nejasna nebo neoverena tvrzeni; Mozne rozpory textu a kodu; Reprodukovatelnost; "
            "README / Artefakty / Odevzdani; Review Status; Synthesis Handoff; Rucni kontroly.",
        ),
        "validators": ("scripts/check-code-consistency --require-synthesis-handoff {case_id} {round_id}",),
    },
    "code_quality": {
        "outputs": ("outputs/code_quality_review.md",),
        "shape": (
            "Markdown headings: # Internal Code Quality Review; Rozsah kontroly; Technicky prehled implementace; "
            "Silne technicke stranky; Hlavni technicka rizika; Architektura a modularita; Runtime, validace "
            "a chybove stavy; Testy, smoke testy a reprodukovatelnost; README, build a vyvojarska "
            "dokumentace; Komentare, citelnost a udrzovatelnost; Review Status; Synthesis Handoff; "
            "Rucni kontroly.",
        ),
        "validators": ("scripts/check-code-quality-review --require-synthesis-handoff {case_id} {round_id}",),
    },
    "quantitative_claims": {
        "outputs": ("work/quantitative_claims.json",),
        "shape": ("JSON schema: quantitative-claims-v1; required top-level claims list and source_refs/hash binding.",),
        "validators": ("scripts/check-evaluation-claims {case_id} {round_id}",),
    },
    "theses_similarity": {
        "outputs": (THESES_SIMILARITY_ASSESSMENT_REL, THESES_SIMILARITY_REVIEW_REL),
        "shape": (
            "Assessment JSON schema: theses-similarity-assessment-v1. Review Markdown headings: "
            "# Theses.cz Similarity Review; Review Scope; Imported Report; Structural Findings; "
            "Contextual Assessment; Repeated-Submission / Self-Overlap Check; Downstream Use; "
            "Synthesis Handoff; Review Status.",
        ),
        "validators": ("scripts/check-theses-similarity-report {case_id} {round_id}",),
    },
    "report_review": {
        "outputs": ("outputs/vedouci_posudek_revidovany.md", "work/reviews/supervisor_report_review.json"),
        "shape": (
            "Reviewed report headings: # Posudek vedouciho; Informace k zadani; Prace s literaturou; "
            "Aktivita behem reseni, konzultace, komunikace; Aktivita pri dokoncovani; Publikacni cinnost, "
            "oceneni; Celkove hodnoceni with Znamka/Body; Komentar pro studenta. Approval JSON must be "
            "written with profile supervisor-report and bind the draft and reviewed report hashes.",
        ),
        "validators": (
            "scripts/check-supervisor-report --require-reviewed {case_id} {round_id}",
            "scripts/check-review-wave --workflow supervisor_report --wave final {case_id} {round_id}",
        ),
    },
}

PACKET_ROLES = (
    PacketRole(
        key="trace",
        title="Supervisor Report Trace",
        skill="thesis-supervisor-report",
        expected_output="work/supervisor_report_trace.json",
        mission=(
            "Build the structured supervisor-report trace from authoritative supervisor input, current evidence, "
            "and optional prior-feedback evidence."
        ),
        focus=(
            "FIT IS field coverage and official/private boundary",
            "supervisor-input refs for activity, independence, consultations, finishing, grade, and student comment",
            "optional prior-feedback evidence only when hash-bound and probative",
            "uncertainty and manual checks that must survive into the draft or confirmation",
        ),
        role_inputs=(
            "notes/supervisor-report-operator-input.md",
            "work/supervisor_report_feedback_history.json",
            "outputs/revision_diff.md",
            "work/current_evidence_snapshot.json",
            "outputs/code_consistency.md",
            "outputs/code_quality_review.md",
        ),
        constraints=(
            "The supervisor's explicit input is authoritative for process, collaboration, grade, points, and private "
            "student-comment intent.",
            "Do not infer responsiveness from raw feedback text; use only structured feedback-history evidence.",
            "Write the trace only to work/supervisor_report_trace.json, then run check-review-wave for the trace wave.",
        ),
    ),
    PacketRole(
        key="code_consistency",
        title="Text-Code Consistency And Reproducibility",
        skill="thesis-code-consistency",
        expected_output="outputs/code_consistency.md",
        mission="Check whether thesis claims are supported by submitted code and reproducibility artifacts.",
        focus=(
            "implemented-feature claims relevant to supervisor satisfaction with results",
            "reproducibility or submitted-source limitations",
            "code-backed evidence that can support grade/points calibration",
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
            "implementation quality that affects supervisor satisfaction and grade calibration",
            "maintainability, error handling, test evidence, and documentation",
            "risks that should be worded as limitations rather than unsupported criticism",
        ),
        role_inputs=(
            "work/code_workspace.md",
            "work/serena_roots.json",
            "work/code_reproducibility.json",
            "outputs/github_code_intake.md",
        ),
        constraints=(
            "Separate implementation quality from thesis text-code mismatch.",
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
        mission="Review visual/demo evidence that may affect result claims or supervisor satisfaction.",
        focus=(
            "visual support for result and functionality claims",
            "manual checks for screenshots, diagrams, presentations, or demos",
            "evidence boundaries that should be cautious in the formal report",
        ),
        role_inputs=(
            "work/media_presence_inventory.jsonl",
            "work/figure_media/visual_inventory.jsonl",
            "outputs/figure_media_review.md",
            "outputs/revision_diff.md",
        ),
        constraints=("Do not treat inventoried-only media as visually verified evidence.",),
        activation="existing_artifact",
        activation_paths=("work/review_materiality/supervisor_report/figure_media.json",),
        activation_workflow_profile="supervisor_report",
    ),
    PacketRole(
        key="literature_citation",
        title="Literature And Citation Evidence",
        skill="thesis-literature-citation-review",
        expected_output="outputs/literature_citation_review.md",
        mission="Check source-use evidence relevant to the supervisor-report literature field.",
        focus=(
            "student activity in finding and using study materials",
            "source relevance and availability limitations",
            "wording support for the official Práce s literaturou field",
        ),
        role_inputs=(
            "outputs/literature_citation_review.md",
            "outputs/revision_diff.md",
        ),
        constraints=("Do not replace the supervisor's process assessment with citation-count judgments.",),
        activation="existing_artifact",
        activation_paths=("work/review_materiality/supervisor_report/literature_citation.json",),
        activation_workflow_profile="supervisor_report",
    ),
    PacketRole(
        key="typography_formal",
        title="Typography And Formal Presentation",
        skill="thesis-typography-formal-review",
        expected_output="outputs/typography_formal_review.md",
        mission="Summarize final formal-presentation evidence that may affect overall assessment wording.",
        focus=(
            "repeated formal or typography risks",
            "language and presentation limitations",
            "only findings material to the formal supervisor report",
        ),
        role_inputs=(
            "outputs/typography_formal_review.md",
            "outputs/revision_diff.md",
        ),
        constraints=("Summarize repeated patterns; do not create a typo inventory for the report.",),
        activation="existing_artifact",
        activation_paths=("work/review_materiality/supervisor_report/typography_formal.json",),
        activation_workflow_profile="supervisor_report",
    ),
    PacketRole(
        key="quantitative_claims",
        title="Quantitative Claims Review",
        skill="thesis-quantitative-claims-review",
        expected_output="work/quantitative_claims.json",
        mission="Sanity-check metric/result claims before they affect report wording, grade, or points.",
        focus=(
            "unit and scale interpretation",
            "baseline and practical magnitude",
            "reproducibility context",
            "overclaim risk in final report wording",
        ),
        role_inputs=(
            "work/quantitative_claims.json",
            "work/review_materiality/supervisor_report/index.json",
            "work/code_reproducibility.json",
            "outputs/code_consistency.md",
            "outputs/figure_media_review.md",
        ),
        constraints=(
            "Write or update only the structured work/quantitative_claims.json contract.",
            "Do not infer metric meaning from deterministic raw-text matching.",
        ),
        activation="existing_artifact_or_next_action",
        activation_paths=("work/quantitative_claims.json",),
        activation_workflow_profile="supervisor_report",
    ),
    PacketRole(
        key="theses_similarity",
        title="Theses.cz Similarity Report Review",
        skill="thesis-theses-similarity-review",
        expected_output=THESES_SIMILARITY_REVIEW_REL,
        mission="Interpret imported Theses.cz similarity evidence before it affects formal supervisor-report wording.",
        focus=(
            "external matches and unresolved concerns",
            "repeated-submission self-overlap in case history",
            "whether resolved or no-concern results should remain silent",
            "formal-report wording boundaries for any unresolved issue",
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
            "Do not infer plagiarism, authorship, or grading impact from a similarity percentage.",
            "Keep no-concern and resolved findings silent in formal report prose unless the supervisor explicitly "
            "needs an institutional note.",
            "Use cautious wording for unresolved concerns and preserve manual-check limitations.",
        ),
        activation="existing_artifact_or_next_action",
        activation_paths=(THESES_SIMILARITY_REVIEW_REL,),
        activation_workflow_profile="supervisor_report",
    ),
    PacketRole(
        key="current_evidence_snapshot",
        title="Current Evidence Snapshot",
        skill="mechanical-validator-backed-helper",
        expected_output="work/current_evidence_snapshot.json",
        mission="Capture drift-prone evidence identity, hashes, freshness notes, and limitations for the report.",
        focus=(
            "current code and GitHub intake identity",
            "reviewed evidence hashes",
            "freshness limitations that the report must preserve",
        ),
        role_inputs=(
            "work/current_evidence_snapshot.json",
            "outputs/github_code_intake.md",
            "work/review_manifest.json",
            "work/supervisor_report_trace.json",
        ),
        constraints=("Do not make semantic quality claims; record structured state and explicit limitations only.",),
        model=MECHANICAL_MODEL,
        reasoning=MECHANICAL_REASONING,
        model_note=(
            "Mechanical helper role; Spark is acceptable only because downstream semantic roles consume validated "
            "state."
        ),
    ),
    PacketRole(
        key="report_review",
        title="Supervisor Report Independent Review",
        skill="thesis-supervisor-report-review",
        expected_output="outputs/vedouci_posudek_revidovany.md and work/reviews/supervisor_report_review.json",
        mission="Review and harden the supervisor-report draft into the reviewed Markdown report.",
        focus=(
            "evidence support and cautious wording",
            "grade/points consistency",
            "official/private section boundary",
            "missing confirmation items before IS readiness",
        ),
        role_inputs=(
            "work/vedouci_posudek_draft.md",
            "work/supervisor_report_trace.json",
        ),
        constraints=(
            "Write the reviewed Markdown and a pass-only approval record at "
            "work/reviews/supervisor_report_review.json.",
            "Do not treat the reviewed Markdown as ready for IS without supervisor_report_confirmation.json.",
            "Material edits after review reopen the artifact as draft.",
        ),
        activation="existing_artifact",
        activation_paths=("work/vedouci_posudek_draft.md",),
    ),
)


def current_evidence_snapshot_section(round_dir: Path) -> str:
    rel_path = "work/current_evidence_snapshot.json"
    digest = sha256_file(round_dir / rel_path)
    if digest:
        detail = f"`{rel_path}` (sha256={digest})"
    else:
        detail = f"`{rel_path}` missing; treat snapshot freshness as unavailable and surface that limitation."
    return "\n".join(["## Current Evidence Snapshot", "", f"- {detail}", ""])


def output_contract_section(role: PacketRole, *, case_id: str, round_id: str) -> str:
    contract = OUTPUT_CONTRACTS.get(role.key)
    if contract is None:
        return "\n".join(
            [
                "## Expected Output Contract",
                "",
                f"- Output path: `{role.expected_output}`",
                "- Validator: use the role skill and relevant review-wave/check-manifest gates.",
                "",
            ]
        )
    outputs = contract["outputs"]
    shape = contract["shape"]
    validators = contract["validators"]
    rendered_validators = [validator.format(case_id=case_id, round_id=round_id) for validator in validators]
    return "\n".join(
        [
            "## Expected Output Contract",
            "",
            "Output files:",
            path_list([str(item) for item in outputs]).rstrip(),
            "",
            "Required shape:",
            text_list([str(item) for item in shape]).rstrip(),
            "",
            "Validator commands:",
            path_list(rendered_validators).rstrip(),
            "",
        ]
    )


def render_packet(
    case_id: str,
    round_id: str,
    generated_at: str,
    round_dir: Path,
    role: PacketRole,
    *,
    agent_authorization: str,
) -> str:
    role_existing = existing_paths(
        round_dir,
        role.role_inputs,
        case_id=case_id,
        round_id=round_id,
        materiality_workflow_profile="supervisor_report",
    )
    active_packets = generated_role_paths(PACKET_ROLES, round_dir, case_id=case_id, round_id=round_id)
    role_constraints = COMMON_CONSTRAINTS + role.constraints
    optional_sections = [
        submission_bundle_visibility_section(round_dir),
        materiality_next_actions_section(
            round_dir,
            case_id=case_id,
            round_id=round_id,
            workflow_profile="supervisor_report",
        ),
        reusable_handoff_refs_section(
            round_dir,
            case_id=case_id,
            round_id=round_id,
            exclude_refs=(REPORT_CALIBRATION_BASIS_REL,),
        ),
    ]
    if role.key == "code_quality":
        optional_sections.append(omen_advisory_section(round_dir))
    common_briefing_sha = sha256_file(round_dir / COMMON_BRIEFING_REL) or "missing"

    return "\n".join(
        [
            f"# Supervisor Report Packet: {role.title}",
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
            f"Agent authorization: `{agent_authorization}`",
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
            "## Optional Prior Feedback Evidence",
            "",
            "Prior feedback is secondary evidence. Missing or inconclusive feedback is a limitation, not negative "
            "evidence.",
            "",
            status_list(round_dir, OPTIONAL_PRIOR_FEEDBACK_INPUTS, case_id=case_id, round_id=round_id),
            "## Supervisor Report Artifacts",
            "",
            hash_status_list(round_dir, REPORT_ARTIFACTS, case_id=case_id, round_id=round_id),
            current_evidence_snapshot_section(round_dir),
            "## Role-Specific Artifacts",
            "",
            status_list(round_dir, role.role_inputs, case_id=case_id, round_id=round_id),
            output_contract_section(role, case_id=case_id, round_id=round_id),
            "## Missing Role Inputs To Treat As Limitations",
            "",
            path_list([rel_path for rel_path in role.role_inputs if rel_path not in role_existing]),
            "## Evidence Policy",
            "",
            "- Supervisor input is authoritative for activity, independence, consultation, communication, final-phase "
            "work, grade/points calibration, and the private student comment.",
            "- Prior feedback can support process assessment only when structured feedback-history evidence shows a "
            "concrete response to feedback.",
            "- Absence or inconclusive feedback is not negative evidence.",
            "",
            "## Open Full Artifacts Only If Needed",
            "",
            "- Start from the common briefing, current context handoffs, structured trace fields, hashes, and "
            "synthesis handoffs when available.",
            "- Open full evidence artifacts for important wording, grade/points, contradiction, or manual-check "
            "claims.",
            "",
            "## Constraints",
            "",
            text_list(list(role_constraints)),
            *optional_sections,
            "## Review Handoff",
            "",
            "- Return concise findings with evidence anchors, limitations, and any required trace/report edits.",
            "- Do not paste raw packet boilerplate into the supervisor report.",
            "",
        ]
    )


def generate_packets(
    case_id: str,
    round_id: str,
    generated_at: str,
    round_dir: Path,
    *,
    agent_authorization: str = "direct-call-not-verified",
) -> list[Path]:
    packet_dir = round_dir / PACKET_DIR_REL
    packet_dir.mkdir(parents=True, exist_ok=True)
    write_common_briefing(case_id, round_id, generated_at, round_dir, workflow_profile="supervisor_report")
    prune_inactive_packets(packet_dir, PACKET_ROLES, round_dir, case_id=case_id, round_id=round_id)
    written: list[Path] = []
    for role in PACKET_ROLES:
        if not role_is_active(round_dir, role, case_id=case_id, round_id=round_id):
            continue
        path = packet_dir / f"{role.key}.md"
        write_text_if_changed(
            path,
            render_packet(
                case_id,
                round_id,
                generated_at,
                round_dir,
                role,
                agent_authorization=agent_authorization,
            ),
        )
        written.append(path)
    return written
