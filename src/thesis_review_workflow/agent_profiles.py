"""Registry for repo-local thesis workflow Codex agent role profiles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

RouteStatus = Literal["profile", "parent-owned", "deferred"]
RoleKind = Literal[
    "generator",
    "evidence-producer",
    "standalone-evidence-reviewer",
    "final-reviewer",
    "calibrator",
    "parent-orchestration",
]
SandboxMode = Literal["read-only", "workspace-write", "parent-orchestration", "not-spawned"]


@dataclass(frozen=True, slots=True)
class AgentProfileRoute:
    """Case-neutral routing contract for one workflow role or skill."""

    role_source: str
    status: RouteStatus
    role_kind: RoleKind
    sandbox_mode: SandboxMode
    skill_id: str | None = None
    profile_id: str | None = None
    owned_outputs: tuple[str, ...] = ()
    allowed_writes: tuple[str, ...] = ()
    standalone_review_profile: str | None = None
    downstream_synthesis_review_allowed: bool = False
    independent_review_profile: str | None = None
    required_validators: tuple[str, ...] = ()
    rationale: str = ""


def _route(
    *,
    role_source: str,
    status: RouteStatus,
    role_kind: RoleKind,
    sandbox_mode: SandboxMode,
    skill_id: str | None = None,
    profile_id: str | None = None,
    owned_outputs: tuple[str, ...] = (),
    allowed_writes: tuple[str, ...] | None = None,
    standalone_review_profile: str | None = None,
    downstream_synthesis_review_allowed: bool = False,
    independent_review_profile: str | None = None,
    required_validators: tuple[str, ...] = (),
    rationale: str = "",
) -> AgentProfileRoute:
    writes = owned_outputs if allowed_writes is None else allowed_writes
    return AgentProfileRoute(
        role_source=role_source,
        status=status,
        role_kind=role_kind,
        sandbox_mode=sandbox_mode,
        skill_id=skill_id,
        profile_id=profile_id,
        owned_outputs=owned_outputs,
        allowed_writes=writes,
        standalone_review_profile=standalone_review_profile,
        downstream_synthesis_review_allowed=downstream_synthesis_review_allowed,
        independent_review_profile=independent_review_profile,
        required_validators=required_validators,
        rationale=rationale,
    )


AGENT_PROFILE_ROUTES: tuple[AgentProfileRoute, ...] = (
    _route(
        role_source="AGENTS.md:text-structure-assignment-coverage",
        status="profile",
        profile_id="thesis_text_reviewer",
        role_kind="evidence-producer",
        sandbox_mode="read-only",
        rationale="Text and assignment review is a durable role, but no dedicated repo-local skill owns it.",
    ),
    _route(
        role_source=".agents/skills/thesis-code-consistency/SKILL.md",
        skill_id="thesis-code-consistency",
        status="profile",
        profile_id="thesis_code_consistency_reviewer",
        role_kind="evidence-producer",
        sandbox_mode="workspace-write",
        owned_outputs=("outputs/code_consistency.md",),
        standalone_review_profile="thesis_evidence_calibrator",
        downstream_synthesis_review_allowed=True,
        required_validators=("scripts/check-code-consistency",),
    ),
    _route(
        role_source=".agents/skills/thesis-code-quality-review/SKILL.md",
        skill_id="thesis-code-quality-review",
        status="profile",
        profile_id="thesis_code_quality_reviewer",
        role_kind="evidence-producer",
        sandbox_mode="workspace-write",
        owned_outputs=("outputs/code_quality_review.md",),
        standalone_review_profile="thesis_evidence_calibrator",
        downstream_synthesis_review_allowed=True,
        required_validators=("scripts/check-code-quality-review",),
    ),
    _route(
        role_source=".agents/skills/thesis-quantitative-claims-review/SKILL.md",
        skill_id="thesis-quantitative-claims-review",
        status="profile",
        profile_id="thesis_quantitative_claims_reviewer",
        role_kind="evidence-producer",
        sandbox_mode="workspace-write",
        owned_outputs=("work/quantitative_claims.json",),
        standalone_review_profile="thesis_evidence_calibrator",
        downstream_synthesis_review_allowed=True,
        required_validators=("scripts/check-evaluation-claims",),
    ),
    _route(
        role_source=".agents/skills/thesis-github-code-intake/SKILL.md",
        skill_id="thesis-github-code-intake",
        status="profile",
        profile_id="thesis_github_code_intake_reviewer",
        role_kind="evidence-producer",
        sandbox_mode="workspace-write",
        owned_outputs=("outputs/github_code_intake.md",),
        allowed_writes=(
            "inputs/github/**",
            "work/github/**",
            "outputs/github_code_intake.md",
        ),
        standalone_review_profile="thesis_evidence_calibrator",
        downstream_synthesis_review_allowed=True,
        required_validators=("scripts/import-github-code",),
    ),
    _route(
        role_source=".agents/skills/thesis-revision-diff/SKILL.md",
        skill_id="thesis-revision-diff",
        status="profile",
        profile_id="thesis_revision_diff_reviewer",
        role_kind="evidence-producer",
        sandbox_mode="workspace-write",
        owned_outputs=("outputs/revision_diff.md",),
        standalone_review_profile="thesis_evidence_calibrator",
        downstream_synthesis_review_allowed=True,
        required_validators=("scripts/check-revision-diff",),
    ),
    _route(
        role_source=".agents/skills/thesis-figure-media-review/SKILL.md",
        skill_id="thesis-figure-media-review",
        status="profile",
        profile_id="thesis_figure_media_reviewer",
        role_kind="evidence-producer",
        sandbox_mode="workspace-write",
        owned_outputs=(
            "work/figure_media/visual_inventory.jsonl",
            "outputs/figure_media_review.md",
        ),
        standalone_review_profile="thesis_evidence_calibrator",
        downstream_synthesis_review_allowed=True,
        required_validators=("scripts/check-figure-media-review",),
    ),
    _route(
        role_source=".agents/skills/thesis-literature-citation-review/SKILL.md",
        skill_id="thesis-literature-citation-review",
        status="profile",
        profile_id="thesis_literature_citation_reviewer",
        role_kind="evidence-producer",
        sandbox_mode="workspace-write",
        owned_outputs=("outputs/literature_citation_review.md",),
        standalone_review_profile="thesis_evidence_calibrator",
        downstream_synthesis_review_allowed=True,
        rationale="No dedicated structural checker exists yet; review is bound through manifest evidence.",
    ),
    _route(
        role_source=".agents/skills/thesis-typography-formal-review/SKILL.md",
        skill_id="thesis-typography-formal-review",
        status="profile",
        profile_id="thesis_typography_formal_reviewer",
        role_kind="evidence-producer",
        sandbox_mode="workspace-write",
        owned_outputs=("outputs/typography_formal_review.md",),
        standalone_review_profile="thesis_evidence_calibrator",
        downstream_synthesis_review_allowed=True,
        required_validators=("scripts/check-typography-formal",),
    ),
    _route(
        role_source=".agents/skills/thesis-theses-similarity-review/SKILL.md",
        skill_id="thesis-theses-similarity-review",
        status="profile",
        profile_id="thesis_theses_similarity_reviewer",
        role_kind="evidence-producer",
        sandbox_mode="workspace-write",
        owned_outputs=(
            "work/theses_similarity/intake.json",
            "work/theses_similarity/assessment.json",
            "work/theses_similarity/review_draft.md",
            "outputs/theses_similarity_review.md",
        ),
        standalone_review_profile="thesis_evidence_calibrator",
        downstream_synthesis_review_allowed=True,
        required_validators=("scripts/check-theses-similarity-report",),
    ),
    _route(
        role_source=".agents/skills/thesis-supervisor-feedback/SKILL.md",
        skill_id="thesis-supervisor-feedback",
        status="parent-owned",
        role_kind="parent-orchestration",
        sandbox_mode="parent-orchestration",
        owned_outputs=("work/feedback_student_draft.md",),
        independent_review_profile="thesis_supervisor_feedback_reviewer",
        required_validators=(
            "scripts/check-review-wave --workflow supervisor_feedback --wave draft",
            "scripts/check-feedback-output",
            "scripts/check-feedback-language",
        ),
        rationale="The main agent owns synthesis; a separate profile owns the sendable feedback review.",
    ),
    _route(
        role_source=".agents/skills/thesis-supervisor-feedback-review/SKILL.md",
        skill_id="thesis-supervisor-feedback-review",
        status="profile",
        profile_id="thesis_supervisor_feedback_reviewer",
        role_kind="final-reviewer",
        sandbox_mode="workspace-write",
        owned_outputs=("outputs/feedback_student.md", "work/reviews/supervisor_feedback_review.json"),
        required_validators=("scripts/check-feedback-output", "scripts/check-feedback-language"),
    ),
    _route(
        role_source=".agents/skills/thesis-supervisor-report/SKILL.md",
        skill_id="thesis-supervisor-report",
        status="parent-owned",
        role_kind="parent-orchestration",
        sandbox_mode="parent-orchestration",
        owned_outputs=("work/supervisor_report_trace.json", "work/vedouci_posudek_draft.md"),
        independent_review_profile="thesis_supervisor_report_reviewer",
        required_validators=(
            "scripts/check-supervisor-report-ready",
            "scripts/check-review-wave --workflow supervisor_report --wave draft",
        ),
        rationale="The main agent owns trace and draft synthesis; a separate profile owns the formal review.",
    ),
    _route(
        role_source=".agents/skills/thesis-supervisor-report-review/SKILL.md",
        skill_id="thesis-supervisor-report-review",
        status="profile",
        profile_id="thesis_supervisor_report_reviewer",
        role_kind="final-reviewer",
        sandbox_mode="workspace-write",
        owned_outputs=(
            "outputs/vedouci_posudek_revidovany.md",
            "work/reviews/supervisor_report_review.json",
        ),
        required_validators=("scripts/check-supervisor-report",),
    ),
    _route(
        role_source=".agents/skills/thesis-opponent-materials/SKILL.md",
        skill_id="thesis-opponent-materials",
        status="parent-owned",
        role_kind="parent-orchestration",
        sandbox_mode="parent-orchestration",
        owned_outputs=("work/oponent_podklady_draft.md", "outputs/oponent_podklady.md"),
        independent_review_profile="thesis_opponent_materials_reviewer",
        required_validators=("scripts/check-review-wave --workflow opponent_materials --wave draft",),
        rationale="The main agent owns synthesis; reviewed materials and trace readiness use a dedicated profile.",
    ),
    _route(
        role_source=".agents/skills/thesis-opponent-materials-review/SKILL.md",
        skill_id="thesis-opponent-materials-review",
        status="profile",
        profile_id="thesis_opponent_materials_reviewer",
        role_kind="final-reviewer",
        sandbox_mode="workspace-write",
        owned_outputs=(
            "outputs/oponent_podklady_revidovane.md",
            "work/opponent_report_trace.json",
            "work/reviews/opponent_materials_review.json",
        ),
        required_validators=("scripts/check-opponent-materials", "scripts/check-opponent-report"),
    ),
    _route(
        role_source=".agents/skills/thesis-opponent-report-review/SKILL.md",
        skill_id="thesis-opponent-report-review",
        status="profile",
        profile_id="thesis_opponent_report_reviewer",
        role_kind="final-reviewer",
        sandbox_mode="workspace-write",
        owned_outputs=("outputs/feedback_k_posudku.md", "work/reviews/opponent_report_review.json"),
        required_validators=("scripts/check-opponent-report",),
    ),
    _route(
        role_source="AGENTS.md:standalone-evidence-calibration",
        status="profile",
        profile_id="thesis_evidence_calibrator",
        role_kind="calibrator",
        sandbox_mode="read-only",
        rationale=(
            "Generic independent calibration role for standalone evidence without a specific final-review profile."
        ),
    ),
    _route(
        role_source=".agents/skills/historical-opponent-calibration/SKILL.md",
        skill_id="historical-opponent-calibration",
        status="deferred",
        role_kind="generator",
        sandbox_mode="not-spawned",
        rationale=(
            "Private calibration workflow; no durable spawned role until repeat use proves a stable output boundary."
        ),
    ),
    _route(
        role_source=".agents/skills/historical-supervisor-report-calibration/SKILL.md",
        skill_id="historical-supervisor-report-calibration",
        status="deferred",
        role_kind="generator",
        sandbox_mode="not-spawned",
        rationale=(
            "Private calibration workflow; no durable spawned role until repeat use proves a stable output boundary."
        ),
    ),
)


def agent_profile_routes() -> tuple[AgentProfileRoute, ...]:
    return AGENT_PROFILE_ROUTES


def profile_routes() -> tuple[AgentProfileRoute, ...]:
    return tuple(route for route in AGENT_PROFILE_ROUTES if route.status == "profile")


def routes_by_skill_id() -> dict[str, AgentProfileRoute]:
    return {route.skill_id: route for route in AGENT_PROFILE_ROUTES if route.skill_id is not None}


def repo_local_skill_ids(root: Path) -> set[str]:
    skills_dir = root / ".agents" / "skills"
    if not skills_dir.is_dir():
        return set()
    return {path.parent.name for path in skills_dir.glob("*/SKILL.md")}
