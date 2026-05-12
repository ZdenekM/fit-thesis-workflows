"""Single source of truth for known round output artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OutputArtifactSpec:
    filename: str
    artifact_type: str
    skills: tuple[str, ...]
    review_scope: str
    label: str
    internal_evidence: bool = False
    explicit_internal_review: bool = False
    closeout_independent_review_required: bool = False
    final_output: bool = False
    review_basis_candidates: tuple[str, ...] = ()

    @property
    def output_path(self) -> str:
        return f"outputs/{self.filename}"


OUTPUT_ARTIFACTS: dict[str, OutputArtifactSpec] = {
    "feedback_student.md": OutputArtifactSpec(
        filename="feedback_student.md",
        artifact_type="supervisor_feedback",
        skills=("thesis-supervisor-feedback", "thesis-supervisor-feedback-review"),
        review_scope="sendable_final",
        label="supervisor feedback",
        final_output=True,
        review_basis_candidates=("work/feedback_student_draft.md",),
    ),
    "vedouci_posudek_revidovany.md": OutputArtifactSpec(
        filename="vedouci_posudek_revidovany.md",
        artifact_type="supervisor_report_reviewed",
        skills=("thesis-supervisor-report", "thesis-supervisor-report-review"),
        review_scope="sendable_final",
        label="reviewed supervisor report",
        final_output=True,
        review_basis_candidates=("work/vedouci_posudek_draft.md",),
    ),
    "revision_diff.md": OutputArtifactSpec(
        filename="revision_diff.md",
        artifact_type="revision_diff",
        skills=("thesis-revision-diff",),
        review_scope="internal_only",
        label="revision diff",
        internal_evidence=True,
    ),
    "github_code_intake.md": OutputArtifactSpec(
        filename="github_code_intake.md",
        artifact_type="github_code_intake",
        skills=("thesis-github-code-intake",),
        review_scope="internal_only",
        label="GitHub code intake",
        internal_evidence=True,
    ),
    "code_consistency.md": OutputArtifactSpec(
        filename="code_consistency.md",
        artifact_type="code_consistency",
        skills=("thesis-code-consistency",),
        review_scope="internal_only",
        label="text-code consistency",
        internal_evidence=True,
    ),
    "code_quality_review.md": OutputArtifactSpec(
        filename="code_quality_review.md",
        artifact_type="code_quality_review",
        skills=("thesis-code-quality-review",),
        review_scope="internal_only",
        label="code quality/design review",
        internal_evidence=True,
    ),
    "literature_citation_review.md": OutputArtifactSpec(
        filename="literature_citation_review.md",
        artifact_type="literature_citation_review",
        skills=("thesis-literature-citation-review",),
        review_scope="internal_only",
        label="literature/citation review",
        internal_evidence=True,
    ),
    "figure_media_review.md": OutputArtifactSpec(
        filename="figure_media_review.md",
        artifact_type="figure_media_review",
        skills=("thesis-figure-media-review",),
        review_scope="internal_only",
        label="figure/media review",
        internal_evidence=True,
    ),
    "typography_formal_review.md": OutputArtifactSpec(
        filename="typography_formal_review.md",
        artifact_type="typography_formal_review",
        skills=("thesis-typography-formal-review",),
        review_scope="internal_only",
        label="typography/formal review",
        internal_evidence=True,
    ),
    "oponent_podklady.md": OutputArtifactSpec(
        filename="oponent_podklady.md",
        artifact_type="opponent_materials_draft",
        skills=("thesis-opponent-materials",),
        review_scope="draft_only",
        label="opponent materials draft",
    ),
    "oponent_podklady_revidovane.md": OutputArtifactSpec(
        filename="oponent_podklady_revidovane.md",
        artifact_type="opponent_materials_reviewed",
        skills=("thesis-opponent-materials", "thesis-opponent-materials-review"),
        review_scope="standalone_final",
        label="reviewed opponent materials",
        final_output=True,
        review_basis_candidates=("work/oponent_podklady_draft.md",),
    ),
    "feedback_k_posudku.md": OutputArtifactSpec(
        filename="feedback_k_posudku.md",
        artifact_type="opponent_report_review",
        skills=("thesis-opponent-report-review",),
        review_scope="standalone_final",
        label="opponent report review",
        final_output=True,
        review_basis_candidates=("work/oponent_posudek_draft.md", "work/muj_posudek_draft.md"),
    ),
    "reference_report_comparison.md": OutputArtifactSpec(
        filename="reference_report_comparison.md",
        artifact_type="reference_report_comparison",
        skills=("historical-opponent-calibration",),
        review_scope="internal_only",
        label="reference report comparison",
        internal_evidence=True,
        explicit_internal_review=True,
        closeout_independent_review_required=True,
    ),
    "opponent_reading_packet.md": OutputArtifactSpec(
        filename="opponent_reading_packet.md",
        artifact_type="opponent_reading_packet",
        skills=("historical-opponent-calibration",),
        review_scope="internal_only",
        label="opponent reading packet",
        internal_evidence=True,
        explicit_internal_review=True,
        closeout_independent_review_required=True,
    ),
    "reviewer_calibration_profile.md": OutputArtifactSpec(
        filename="reviewer_calibration_profile.md",
        artifact_type="opponent_reviewer_calibration_profile",
        skills=("historical-opponent-calibration",),
        review_scope="internal_only",
        label="reviewer calibration profile",
        internal_evidence=True,
        explicit_internal_review=True,
    ),
    "demo_artifacts_review.md": OutputArtifactSpec(
        filename="demo_artifacts_review.md",
        artifact_type="demo_artifacts_review",
        skills=(),
        review_scope="internal_only",
        label="demo artifact review",
        internal_evidence=True,
    ),
    "pr_contribution_review.md": OutputArtifactSpec(
        filename="pr_contribution_review.md",
        artifact_type="pr_contribution_review",
        skills=("thesis-github-code-intake",),
        review_scope="internal_only",
        label="PR contribution review",
        internal_evidence=True,
    ),
}


def output_spec(filename_or_path: str) -> OutputArtifactSpec | None:
    return OUTPUT_ARTIFACTS.get(Path(filename_or_path).name)


def output_defaults(filename_or_path: str) -> tuple[str, list[str], str]:
    spec = output_spec(filename_or_path)
    if spec is None:
        return "generated_markdown", [], "internal_only"
    return spec.artifact_type, list(spec.skills), spec.review_scope


def known_output_labels() -> dict[str, str]:
    return {filename: spec.label for filename, spec in OUTPUT_ARTIFACTS.items()}


def internal_evidence_filenames() -> set[str]:
    return {filename for filename, spec in OUTPUT_ARTIFACTS.items() if spec.internal_evidence}


def explicit_internal_review_filenames() -> set[str]:
    return {filename for filename, spec in OUTPUT_ARTIFACTS.items() if spec.explicit_internal_review}


def closeout_independent_review_required_paths() -> set[str]:
    return {spec.output_path for spec in OUTPUT_ARTIFACTS.values() if spec.closeout_independent_review_required}


def final_output_paths() -> set[str]:
    return {spec.output_path for spec in OUTPUT_ARTIFACTS.values() if spec.final_output}


def opponent_final_output_paths() -> set[str]:
    return {
        spec.output_path
        for spec in OUTPUT_ARTIFACTS.values()
        if spec.artifact_type in {"opponent_materials_reviewed", "opponent_report_review"}
    }


def final_output_filenames() -> set[str]:
    return {spec.filename for spec in OUTPUT_ARTIFACTS.values() if spec.final_output}


def review_basis_candidates(output_path: str) -> tuple[str, ...]:
    spec = output_spec(output_path)
    return spec.review_basis_candidates if spec is not None else ()
