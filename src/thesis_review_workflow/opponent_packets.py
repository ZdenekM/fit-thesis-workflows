"""Role-specific packet generation for opponent-review agents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from thesis_review_workflow.structured_evidence import (
    STRUCTURED_EVIDENCE_SCHEMAS,
    validate_structured_evidence_artifact,
)

PACKET_DIR_REL = Path("work/opponent_packets")
SCHEMA_VERSION = "opponent-review-packet-v1"


@dataclass(frozen=True)
class PacketRole:
    key: str
    title: str
    skill: str
    expected_output: str
    mission: str
    focus: tuple[str, ...]
    role_inputs: tuple[str, ...]
    constraints: tuple[str, ...]


CASE_INPUTS = ("case.md",)
BASE_INPUTS = (
    "notes/assignment.md",
    "notes/opponent-intake.md",
    "notes/round-notes.md",
)
PROFILE_INPUTS = (
    "profiles/default.md",
    "profiles/local/default.md",
)
ADVISORY_ARTIFACTS = (
    "work/assignment_coverage_agent.json",
    "work/evidence_requirements.json",
    "work/code_reproducibility.json",
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
COMMON_CONSTRAINTS = (
    "Use only round-relative paths in notes and outputs.",
    "State missing, unavailable, or uninspected evidence as a limitation; do not infer failure from absence.",
    "Use confidence labels for important claims: [FAKT], [INTERPRETACE], [ODHAD], [NEOVERENO], [K RUCNI KONTROLE].",
    "Do not move private case inputs, generated outputs, or submitted code into tracked repository paths.",
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
        ),
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
            "outputs/code_consistency.md",
            "outputs/code_quality_review.md",
            "outputs/figure_media_review.md",
            "outputs/literature_citation_review.md",
            "outputs/typography_formal_review.md",
        ),
        constraints=(
            "Do not manufacture certainty; lower confidence or mark manual checks when evidence is incomplete.",
            "Keep grading calibration as intervals and rationale, not precise point verdicts.",
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
    ),
)


def rel_status(
    round_dir: Path,
    rel_path: str,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
) -> str:
    path = round_dir / rel_path
    if not path.exists():
        return "missing"
    if rel_path in STRUCTURED_EVIDENCE_SCHEMAS:
        errors = validate_structured_evidence_artifact(round_dir, rel_path, case_id=case_id, round_id=round_id)
        if errors:
            return "invalid"
    return "present"


def existing_paths(
    round_dir: Path,
    rel_paths: tuple[str, ...],
    *,
    case_id: str | None = None,
    round_id: str | None = None,
) -> list[str]:
    return [
        rel_path
        for rel_path in rel_paths
        if rel_status(round_dir, rel_path, case_id=case_id, round_id=round_id) == "present"
    ]


def top_level_paths(round_dir: Path, rel_dir: str, *, limit: int = 12) -> list[str]:
    directory = round_dir / rel_dir
    if not directory.is_dir():
        return []
    paths = sorted(path for path in directory.iterdir() if path.is_file() or (path.is_dir() and not path.is_symlink()))
    rendered: list[str] = []
    for path in paths[:limit]:
        suffix = "/" if path.is_dir() else ""
        rendered.append(f"{rel_dir}/{path.name}{suffix}")
    return rendered


def extracted_text_paths(round_dir: Path, *, limit: int = 8) -> list[str]:
    extracted = round_dir / "extracted"
    if not extracted.is_dir():
        return []
    paths = sorted(path for path in extracted.rglob("*.txt") if path.is_file())
    return [path.relative_to(round_dir).as_posix() for path in paths[:limit]]


def path_list(lines: list[str]) -> str:
    if not lines:
        return "- none detected\n"
    return "".join(f"- `{line}`\n" for line in lines)


def status_list(
    round_dir: Path,
    paths: tuple[str, ...],
    *,
    case_id: str | None = None,
    round_id: str | None = None,
) -> str:
    return "".join(
        f"- `{rel_path}` ({rel_status(round_dir, rel_path, case_id=case_id, round_id=round_id)})\n"
        for rel_path in paths
    )


def render_packet(case_id: str, round_id: str, generated_at: str, round_dir: Path, role: PacketRole) -> str:
    case_dir = round_dir.parents[1]
    repo_root = round_dir.parents[3]
    inputs = top_level_paths(round_dir, "inputs")
    notes = top_level_paths(round_dir, "notes")
    extracted = extracted_text_paths(round_dir)
    role_existing = existing_paths(round_dir, role.role_inputs, case_id=case_id, round_id=round_id)
    advisory_existing = existing_paths(round_dir, ADVISORY_ARTIFACTS, case_id=case_id, round_id=round_id)
    role_constraints = COMMON_CONSTRAINTS + role.constraints

    return "\n".join(
        [
            f"# Opponent Reviewer Packet: {role.title}",
            "",
            f"Schema version: `{SCHEMA_VERSION}`",
            f"Case: `{case_id}`",
            f"Round: `{round_id}`",
            f"Generated at: `{generated_at}`",
            f"Role key: `{role.key}`",
            f"Skill: `{role.skill}`",
            f"Expected output: `{role.expected_output}`",
            "",
            "## Mission",
            "",
            role.mission,
            "",
            "## Focus",
            "",
            path_list(list(role.focus)).replace("`", ""),
            "## Required Base Inputs",
            "",
            status_list(case_dir, CASE_INPUTS),
            status_list(round_dir, BASE_INPUTS),
            "## Reviewer Profile Inputs",
            "",
            status_list(repo_root, PROFILE_INPUTS),
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
            "## Constraints",
            "",
            path_list(list(role_constraints)).replace("`", ""),
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
    written: list[Path] = []
    for role in PACKET_ROLES:
        path = packet_dir / f"{role.key}.md"
        path.write_text(render_packet(case_id, round_id, generated_at, round_dir, role), encoding="utf-8")
        written.append(path)
    return written
