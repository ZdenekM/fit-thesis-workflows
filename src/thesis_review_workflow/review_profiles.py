"""Workflow-profile registry for review-pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from thesis_review_workflow.paths import is_safe_round_relative_path


@dataclass(frozen=True, slots=True)
class WorkflowReviewProfile:
    """Case-neutral contract for one operator-visible review workflow surface."""

    profile_id: str
    workflow_profile: str
    operator_surface: str
    final_artifact: str
    approval_record: str
    draft_artifacts: tuple[str, ...]
    final_review_role: str
    required_role_coverage: tuple[str, ...]
    optional_role_coverage: tuple[str, ...]
    readiness_gates: tuple[str, ...]
    closeout_gates: tuple[str, ...]
    readiness_wording: str
    materiality_profile: str | None = None
    wave_workflow: str | None = None
    code_bearing_roles: tuple[str, ...] = ("code_consistency", "code_quality")

    @property
    def effective_materiality_profile(self) -> str | None:
        return self.materiality_profile or self.workflow_profile

    @property
    def effective_wave_workflow(self) -> str:
        return self.wave_workflow or self.workflow_profile


OPTIONAL_EVIDENCE_ROLES = (
    "revision_diff",
    "github_intake",
    "quantitative_claims",
    "figure_media",
    "literature_citation",
    "typography_formal",
    "theses_similarity",
)

COMMON_CLOSEOUT_GATES = (
    "init-review-manifest --run-checks",
    "check-agent-coverage",
    "check-review-manifest --require-complete",
    "check-private",
    "check-scripts",
    "git diff --check",
)


WORKFLOW_REVIEW_PROFILES: tuple[WorkflowReviewProfile, ...] = (
    WorkflowReviewProfile(
        profile_id="supervisor_feedback",
        workflow_profile="supervisor_feedback",
        operator_surface="supervisor_feedback",
        materiality_profile="supervisor_feedback",
        final_artifact="outputs/feedback_student.md",
        draft_artifacts=("work/feedback_student_draft.md",),
        approval_record="work/reviews/supervisor_feedback_review.json",
        final_review_role="supervisor_feedback_review",
        required_role_coverage=("supervisor_feedback_review",),
        optional_role_coverage=OPTIONAL_EVIDENCE_ROLES,
        readiness_gates=("check-supervisor-ready",),
        closeout_gates=(
            "check-supervisor-ready",
            *COMMON_CLOSEOUT_GATES,
            "check-feedback-language",
            "check-feedback-output",
        ),
        readiness_wording=(
            "student-facing supervisor feedback is ready after independent review and feedback gates pass"
        ),
    ),
    WorkflowReviewProfile(
        profile_id="supervisor_report",
        workflow_profile="supervisor_report",
        operator_surface="supervisor_report",
        materiality_profile="supervisor_report",
        final_artifact="outputs/vedouci_posudek_revidovany.md",
        draft_artifacts=("work/vedouci_posudek_draft.md",),
        approval_record="work/reviews/supervisor_report_review.json",
        final_review_role="supervisor_report_review",
        required_role_coverage=("supervisor_report_review",),
        optional_role_coverage=OPTIONAL_EVIDENCE_ROLES,
        readiness_gates=("check-supervisor-report-ready",),
        closeout_gates=(
            "check-supervisor-report-ready",
            *COMMON_CLOSEOUT_GATES,
            "check-supervisor-report",
            "confirm-supervisor-report",
        ),
        readiness_wording=(
            "formal supervisor report is ready only after review, confirmation, and supervisor-report gates pass"
        ),
    ),
    WorkflowReviewProfile(
        profile_id="opponent_review",
        workflow_profile="opponent_review",
        operator_surface="opponent_review",
        materiality_profile="opponent_review",
        wave_workflow="opponent_materials",
        final_artifact="outputs/oponent_podklady_revidovane.md",
        draft_artifacts=("work/oponent_podklady_draft.md", "outputs/oponent_podklady.md"),
        approval_record="work/reviews/opponent_materials_review.json",
        final_review_role="opponent_materials_review",
        required_role_coverage=("opponent_materials_review",),
        optional_role_coverage=OPTIONAL_EVIDENCE_ROLES,
        readiness_gates=("check-round-ready",),
        closeout_gates=(
            "check-round-ready",
            *COMMON_CLOSEOUT_GATES,
            "check-opponent-materials",
            "check-opponent-report --mode canonical",
        ),
        readiness_wording=(
            "opponent materials are ready after reviewed materials, opponent trace gates, and applicable "
            "report-calibration gates pass"
        ),
    ),
    WorkflowReviewProfile(
        profile_id="opponent_materials",
        workflow_profile="opponent_review",
        operator_surface="opponent_materials",
        materiality_profile="opponent_review",
        wave_workflow="opponent_materials",
        final_artifact="outputs/oponent_podklady_revidovane.md",
        draft_artifacts=("work/oponent_podklady_draft.md", "outputs/oponent_podklady.md"),
        approval_record="work/reviews/opponent_materials_review.json",
        final_review_role="opponent_materials_review",
        required_role_coverage=("opponent_materials_review",),
        optional_role_coverage=OPTIONAL_EVIDENCE_ROLES,
        readiness_gates=("check-round-ready",),
        closeout_gates=(
            "check-round-ready",
            *COMMON_CLOSEOUT_GATES,
            "check-opponent-materials",
            "check-opponent-report --mode canonical",
        ),
        readiness_wording=(
            "opponent-materials operator surface maps to the canonical opponent_review profile, including "
            "applicable report-calibration gates before trace/report use"
        ),
    ),
    WorkflowReviewProfile(
        profile_id="opponent_report_review",
        workflow_profile="opponent_report_review",
        operator_surface="opponent_report_review",
        materiality_profile="opponent_review",
        final_artifact="outputs/feedback_k_posudku.md",
        draft_artifacts=(
            "outputs/oponent_posudek_navrh.md",
            "work/oponent_posudek_draft.md",
        ),
        approval_record="work/reviews/opponent_report_review.json",
        final_review_role="opponent_report_review",
        required_role_coverage=("opponent_report_review",),
        optional_role_coverage=OPTIONAL_EVIDENCE_ROLES,
        readiness_gates=(
            "check-opponent-report --mode canonical",
            "check-opponent-report --mode clean --path outputs/oponent_posudek_navrh.md",
        ),
        closeout_gates=(
            "check-opponent-report --mode canonical",
            "check-opponent-report --mode clean --path outputs/oponent_posudek_navrh.md",
            *COMMON_CLOSEOUT_GATES,
        ),
        readiness_wording=(
            "opponent report review is ready after report-review approval, opponent-report gates, and any "
            "applicable report-calibration gate pass"
        ),
    ),
)


def workflow_review_profiles() -> tuple[WorkflowReviewProfile, ...]:
    return WORKFLOW_REVIEW_PROFILES


def profiles_by_id() -> dict[str, WorkflowReviewProfile]:
    return {profile.profile_id: profile for profile in WORKFLOW_REVIEW_PROFILES}


def get_workflow_review_profile(profile_id: str) -> WorkflowReviewProfile:
    try:
        return profiles_by_id()[profile_id]
    except KeyError as exc:
        available = ", ".join(sorted(profiles_by_id()))
        raise ValueError(f"unknown workflow review profile {profile_id!r}; available: {available}") from exc


def canonical_workflow_profiles() -> set[str]:
    return {profile.workflow_profile for profile in WORKFLOW_REVIEW_PROFILES}


def validate_workflow_profile_registry() -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for profile in WORKFLOW_REVIEW_PROFILES:
        if profile.profile_id in seen:
            errors.append(f"{profile.profile_id}: duplicate workflow review profile")
        seen.add(profile.profile_id)
        for label, rel_path in (
            ("final_artifact", profile.final_artifact),
            ("approval_record", profile.approval_record),
            *[(f"draft_artifacts[{index}]", path) for index, path in enumerate(profile.draft_artifacts, start=1)],
        ):
            if not is_safe_round_relative_path(rel_path):
                errors.append(f"{profile.profile_id}: {label} must be round-relative: {rel_path}")
        if not profile.required_role_coverage:
            errors.append(f"{profile.profile_id}: required_role_coverage must not be empty")
        if "code_consistency" not in profile.code_bearing_roles or "code_quality" not in profile.code_bearing_roles:
            errors.append(f"{profile.profile_id}: code-bearing roles must include code consistency and code quality")
    return errors
