"""Pure reuse-decision model for round workflow artifacts.

This module is intentionally content-blind: callers pass explicit source
fingerprints and review/provenance state, and the helpers compare only structured
metadata. Free-form thesis/code interpretation belongs to reviewer workflows.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable, Self

from thesis_review_workflow.paths import is_safe_round_relative_path

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REUSE_INDEX_SCHEMA_VERSION = "round-reuse-index-v1"


class SourceClass(StrEnum):
    """Structured source categories that can affect reusable artifacts."""

    ASSIGNMENT = "assignment"
    THESIS_PDF = "thesis_pdf"
    THESIS_EXTRACT = "thesis_extract"
    THESIS_SOURCE = "thesis_source"
    SUBMITTED_CODE = "submitted_code"
    CODE_WORKSPACE = "code_workspace"
    GITHUB_SNAPSHOT = "github_snapshot"
    README_CONFIG = "readme_config"
    EXPERIMENT_RESULT = "experiment_result"
    MEDIA = "media"
    LITERATURE_SOURCE_MAP = "literature_source_map"
    THESES_SIMILARITY_REPORT = "theses_similarity_report"
    PREVIOUS_FEEDBACK = "previous_feedback"
    REVIEW_ARTIFACT = "review_artifact"
    REVIEW_APPROVAL = "review_approval"
    MATERIALITY_DECISION = "materiality_decision"
    OPERATOR_NOTE = "operator_note"
    REVIEWER_PROFILE = "reviewer_profile"
    GENERATED_PACKET = "generated_packet"
    SUBMITTED_REPORT = "submitted_report"
    OTHER = "other"


class ArtifactRole(StrEnum):
    """Artifact roles with known source dependency classes."""

    TEXT_ASSIGNMENT = "text_assignment"
    CODE_CONSISTENCY = "code_consistency"
    CODE_QUALITY = "code_quality"
    QUANTITATIVE_CLAIMS = "quantitative_claims"
    LITERATURE_CITATION = "literature_citation"
    FIGURE_MEDIA = "figure_media"
    TYPOGRAPHY_FORMAL = "typography_formal"
    THESES_SIMILARITY = "theses_similarity"
    GITHUB_CODE_INTAKE = "github_code_intake"
    REVISION_DIFF = "revision_diff"
    SUPERVISOR_FEEDBACK = "supervisor_feedback"
    SUPERVISOR_REPORT = "supervisor_report"
    OPPONENT_MATERIALS = "opponent_materials"
    OPPONENT_REPORT_REVIEW = "opponent_report_review"
    COMMON_BRIEFING = "common_briefing"
    ROLE_PACKET = "role_packet"


class ReuseStatus(StrEnum):
    UNCHANGED_REUSABLE = "unchanged_reusable"
    CHANGED_DELTA_REQUIRED = "changed_delta_required"
    STALE_OR_UNREVIEWED = "stale_or_unreviewed"
    NOT_COMPARABLE = "not_comparable"


class CoverageSatisfiedBy(StrEnum):
    CURRENT_REVIEWED_ARTIFACT = "current_reviewed_artifact"
    CURRENT_SYNTHESIS_COVERED_ARTIFACT = "current_synthesis_covered_artifact"
    CURRENT_HANDOFF = "current_handoff"
    SILENT_INTERNAL_EVIDENCE = "silent_internal_evidence"
    TYPED_NO_MATERIAL_ISSUE = "typed_no_material_issue"
    TYPED_LIMITATION = "typed_limitation"
    FRESH_ROLE_REVIEW = "fresh_role_review"
    NOT_SATISFIED = "not_satisfied"


class NextAction(StrEnum):
    REUSE_EXISTING_REVIEW = "reuse_existing_review"
    DELTA_REVIEW = "delta_review"
    FRESH_ROLE_REVIEW = "fresh_role_review"
    MANUAL_LIMITATION = "manual_limitation"
    NOT_COMPARABLE_BACKFILL = "not_comparable_backfill"


# Workflow role-plan roles that may be satisfied from hash-bound reuse evidence.
# This map intentionally covers standalone evidence roles only. Final synthesis,
# trace, and independent-review workflow roles stay profile-specific and must
# not be skipped from a same-named reusable final artifact.
ROLE_PLAN_REUSE_ARTIFACTS: dict[str, ArtifactRole] = {
    "text_assignment": ArtifactRole.TEXT_ASSIGNMENT,
    "text_structure_assignment": ArtifactRole.TEXT_ASSIGNMENT,
    "code_consistency": ArtifactRole.CODE_CONSISTENCY,
    "code_quality": ArtifactRole.CODE_QUALITY,
    "quantitative_claims": ArtifactRole.QUANTITATIVE_CLAIMS,
    "literature_citation": ArtifactRole.LITERATURE_CITATION,
    "figure_media": ArtifactRole.FIGURE_MEDIA,
    "typography_formal": ArtifactRole.TYPOGRAPHY_FORMAL,
    "theses_similarity": ArtifactRole.THESES_SIMILARITY,
    "github_intake": ArtifactRole.GITHUB_CODE_INTAKE,
}


def artifact_role_for_role_plan_role(role: str) -> ArtifactRole | None:
    """Return the reusable artifact role for a workflow role-plan role, if any."""

    return ROLE_PLAN_REUSE_ARTIFACTS.get(role)


FRESH_REVIEW_SATISFYING_COVERAGE = frozenset({CoverageSatisfiedBy.FRESH_ROLE_REVIEW})
REUSABLE_COVERAGE = frozenset(
    {
        CoverageSatisfiedBy.CURRENT_REVIEWED_ARTIFACT,
        CoverageSatisfiedBy.CURRENT_SYNTHESIS_COVERED_ARTIFACT,
        CoverageSatisfiedBy.CURRENT_HANDOFF,
        CoverageSatisfiedBy.SILENT_INTERNAL_EVIDENCE,
        CoverageSatisfiedBy.TYPED_NO_MATERIAL_ISSUE,
        CoverageSatisfiedBy.TYPED_LIMITATION,
    }
)


def coverage_satisfies_without_fresh_review(value: CoverageSatisfiedBy | str) -> bool:
    return coerce_coverage(value) in REUSABLE_COVERAGE


ROLE_SOURCE_DEPENDENCIES: dict[ArtifactRole, frozenset[SourceClass]] = {
    ArtifactRole.TEXT_ASSIGNMENT: frozenset(
        {
            SourceClass.ASSIGNMENT,
            SourceClass.THESIS_PDF,
            SourceClass.THESIS_EXTRACT,
            SourceClass.THESIS_SOURCE,
            SourceClass.PREVIOUS_FEEDBACK,
            SourceClass.OPERATOR_NOTE,
            SourceClass.REVIEWER_PROFILE,
        }
    ),
    ArtifactRole.CODE_CONSISTENCY: frozenset(
        {
            SourceClass.ASSIGNMENT,
            SourceClass.THESIS_PDF,
            SourceClass.THESIS_EXTRACT,
            SourceClass.THESIS_SOURCE,
            SourceClass.SUBMITTED_CODE,
            SourceClass.CODE_WORKSPACE,
            SourceClass.GITHUB_SNAPSHOT,
            SourceClass.README_CONFIG,
            SourceClass.EXPERIMENT_RESULT,
            SourceClass.OPERATOR_NOTE,
        }
    ),
    ArtifactRole.CODE_QUALITY: frozenset(
        {
            SourceClass.SUBMITTED_CODE,
            SourceClass.CODE_WORKSPACE,
            SourceClass.GITHUB_SNAPSHOT,
            SourceClass.README_CONFIG,
            SourceClass.EXPERIMENT_RESULT,
            SourceClass.OPERATOR_NOTE,
        }
    ),
    ArtifactRole.QUANTITATIVE_CLAIMS: frozenset(
        {
            SourceClass.THESIS_EXTRACT,
            SourceClass.THESIS_SOURCE,
            SourceClass.EXPERIMENT_RESULT,
            SourceClass.SUBMITTED_CODE,
            SourceClass.CODE_WORKSPACE,
            SourceClass.GITHUB_SNAPSHOT,
            SourceClass.OPERATOR_NOTE,
        }
    ),
    ArtifactRole.LITERATURE_CITATION: frozenset(
        {
            SourceClass.THESIS_PDF,
            SourceClass.THESIS_EXTRACT,
            SourceClass.THESIS_SOURCE,
            SourceClass.LITERATURE_SOURCE_MAP,
            SourceClass.OPERATOR_NOTE,
        }
    ),
    ArtifactRole.FIGURE_MEDIA: frozenset(
        {
            SourceClass.THESIS_PDF,
            SourceClass.THESIS_EXTRACT,
            SourceClass.THESIS_SOURCE,
            SourceClass.MEDIA,
            SourceClass.OPERATOR_NOTE,
        }
    ),
    ArtifactRole.TYPOGRAPHY_FORMAL: frozenset(
        {
            SourceClass.THESIS_PDF,
            SourceClass.THESIS_EXTRACT,
            SourceClass.THESIS_SOURCE,
            SourceClass.OPERATOR_NOTE,
        }
    ),
    ArtifactRole.THESES_SIMILARITY: frozenset(
        {
            SourceClass.THESIS_PDF,
            SourceClass.THESIS_EXTRACT,
            SourceClass.THESES_SIMILARITY_REPORT,
            SourceClass.OPERATOR_NOTE,
        }
    ),
    ArtifactRole.GITHUB_CODE_INTAKE: frozenset({SourceClass.GITHUB_SNAPSHOT, SourceClass.OPERATOR_NOTE}),
    ArtifactRole.REVISION_DIFF: frozenset(
        {
            SourceClass.ASSIGNMENT,
            SourceClass.THESIS_PDF,
            SourceClass.THESIS_EXTRACT,
            SourceClass.THESIS_SOURCE,
            SourceClass.SUBMITTED_CODE,
            SourceClass.CODE_WORKSPACE,
            SourceClass.GITHUB_SNAPSHOT,
            SourceClass.MEDIA,
            SourceClass.PREVIOUS_FEEDBACK,
            SourceClass.REVIEW_ARTIFACT,
            SourceClass.OPERATOR_NOTE,
        }
    ),
    ArtifactRole.SUPERVISOR_FEEDBACK: frozenset(
        {
            SourceClass.ASSIGNMENT,
            SourceClass.THESIS_PDF,
            SourceClass.THESIS_EXTRACT,
            SourceClass.THESIS_SOURCE,
            SourceClass.SUBMITTED_CODE,
            SourceClass.CODE_WORKSPACE,
            SourceClass.GITHUB_SNAPSHOT,
            SourceClass.README_CONFIG,
            SourceClass.EXPERIMENT_RESULT,
            SourceClass.MEDIA,
            SourceClass.PREVIOUS_FEEDBACK,
            SourceClass.REVIEW_ARTIFACT,
            SourceClass.REVIEW_APPROVAL,
            SourceClass.MATERIALITY_DECISION,
            SourceClass.OPERATOR_NOTE,
            SourceClass.REVIEWER_PROFILE,
        }
    ),
    ArtifactRole.SUPERVISOR_REPORT: frozenset(
        {
            SourceClass.ASSIGNMENT,
            SourceClass.THESIS_PDF,
            SourceClass.THESIS_EXTRACT,
            SourceClass.THESIS_SOURCE,
            SourceClass.SUBMITTED_CODE,
            SourceClass.CODE_WORKSPACE,
            SourceClass.GITHUB_SNAPSHOT,
            SourceClass.README_CONFIG,
            SourceClass.EXPERIMENT_RESULT,
            SourceClass.MEDIA,
            SourceClass.REVIEW_ARTIFACT,
            SourceClass.REVIEW_APPROVAL,
            SourceClass.MATERIALITY_DECISION,
            SourceClass.OPERATOR_NOTE,
            SourceClass.REVIEWER_PROFILE,
        }
    ),
    ArtifactRole.OPPONENT_MATERIALS: frozenset(
        {
            SourceClass.ASSIGNMENT,
            SourceClass.THESIS_PDF,
            SourceClass.THESIS_EXTRACT,
            SourceClass.THESIS_SOURCE,
            SourceClass.SUBMITTED_CODE,
            SourceClass.CODE_WORKSPACE,
            SourceClass.GITHUB_SNAPSHOT,
            SourceClass.README_CONFIG,
            SourceClass.EXPERIMENT_RESULT,
            SourceClass.MEDIA,
            SourceClass.LITERATURE_SOURCE_MAP,
            SourceClass.THESES_SIMILARITY_REPORT,
            SourceClass.REVIEW_ARTIFACT,
            SourceClass.REVIEW_APPROVAL,
            SourceClass.MATERIALITY_DECISION,
            SourceClass.OPERATOR_NOTE,
            SourceClass.REVIEWER_PROFILE,
        }
    ),
    ArtifactRole.OPPONENT_REPORT_REVIEW: frozenset(
        {
            SourceClass.REVIEW_ARTIFACT,
            SourceClass.REVIEW_APPROVAL,
            SourceClass.SUBMITTED_REPORT,
            SourceClass.OPERATOR_NOTE,
            SourceClass.REVIEWER_PROFILE,
        }
    ),
    ArtifactRole.COMMON_BRIEFING: frozenset(
        {
            SourceClass.ASSIGNMENT,
            SourceClass.THESIS_PDF,
            SourceClass.THESIS_EXTRACT,
            SourceClass.THESIS_SOURCE,
            SourceClass.SUBMITTED_CODE,
            SourceClass.CODE_WORKSPACE,
            SourceClass.GITHUB_SNAPSHOT,
            SourceClass.REVIEW_ARTIFACT,
            SourceClass.REVIEW_APPROVAL,
            SourceClass.MATERIALITY_DECISION,
            SourceClass.PREVIOUS_FEEDBACK,
            SourceClass.OPERATOR_NOTE,
            SourceClass.REVIEWER_PROFILE,
        }
    ),
    ArtifactRole.ROLE_PACKET: frozenset(
        {
            SourceClass.REVIEW_ARTIFACT,
            SourceClass.REVIEW_APPROVAL,
            SourceClass.MATERIALITY_DECISION,
            SourceClass.GENERATED_PACKET,
            SourceClass.OPERATOR_NOTE,
            SourceClass.REVIEWER_PROFILE,
        }
    ),
}


@dataclass(frozen=True)
class SourceFingerprint:
    """Hash identity for one structured source dependency."""

    source_ref: str
    source_class: SourceClass | str
    sha256: str | None
    available: bool = True
    schema_version: str = ""
    producer: str = ""

    def __post_init__(self) -> None:
        if not is_safe_round_relative_path(self.source_ref):
            raise ValueError(f"unsafe source_ref: {self.source_ref}")
        if not isinstance(self.source_class, SourceClass):
            object.__setattr__(self, "source_class", SourceClass(str(self.source_class)))
        if self.sha256 is not None and not SHA256_RE.fullmatch(self.sha256):
            raise ValueError(f"sha256 for {self.source_ref} must be a 64-character hex string")
        if not self.available and self.sha256 is not None:
            raise ValueError(f"unavailable source {self.source_ref} must not have sha256")

    @property
    def normalized_source_class(self) -> SourceClass:
        return coerce_source_class(self.source_class)

    @property
    def key(self) -> tuple[str, SourceClass]:
        return (self.source_ref, self.normalized_source_class)

    @property
    def comparable(self) -> bool:
        return self.available and self.sha256 is not None

    @property
    def state(self) -> str:
        if not self.available:
            return "missing"
        if self.sha256 is None:
            return "not_comparable"
        return "comparable"


@dataclass(frozen=True)
class SourceComparison:
    unchanged_refs: tuple[str, ...] = ()
    changed_refs: tuple[str, ...] = ()
    added_refs: tuple[str, ...] = ()
    removed_refs: tuple[str, ...] = ()
    missing_current_refs: tuple[str, ...] = ()
    not_comparable_refs: tuple[str, ...] = ()

    @property
    def has_missing_current(self) -> bool:
        return bool(self.missing_current_refs)

    @property
    def has_not_comparable(self) -> bool:
        return bool(self.not_comparable_refs)

    @property
    def has_changes(self) -> bool:
        return bool(self.changed_refs or self.added_refs or self.removed_refs)


@dataclass(frozen=True)
class ReuseDecision:
    artifact_role: ArtifactRole
    status: ReuseStatus
    fresh_semantic_review_required: bool
    coverage_satisfied_by: CoverageSatisfiedBy
    next_action: NextAction
    relevant_source_classes: tuple[SourceClass, ...]
    source_sha256: dict[str, str]
    unchanged_refs: tuple[str, ...] = ()
    changed_refs: tuple[str, ...] = ()
    added_refs: tuple[str, ...] = ()
    removed_refs: tuple[str, ...] = ()
    missing_current_refs: tuple[str, ...] = ()
    not_comparable_refs: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    @classmethod
    def from_comparison(
        cls,
        *,
        artifact_role: ArtifactRole | str,
        relevant_source_classes: Iterable[SourceClass],
        comparison: SourceComparison,
        current_sources: Iterable[SourceFingerprint],
        prior_review_current: bool,
        schema_compatible: bool,
        coverage_satisfied_by: CoverageSatisfiedBy | str,
        surrounding_context_changed: bool = False,
    ) -> Self:
        role = coerce_artifact_role(artifact_role)
        coverage = coerce_coverage(coverage_satisfied_by)
        source_hashes = source_hashes_by_ref(current_sources, set(relevant_source_classes))
        classes = tuple(sorted(set(relevant_source_classes), key=lambda item: item.value))
        if not source_hashes and not comparison.has_missing_current:
            return cls(
                artifact_role=role,
                status=ReuseStatus.NOT_COMPARABLE,
                fresh_semantic_review_required=True,
                coverage_satisfied_by=CoverageSatisfiedBy.NOT_SATISFIED,
                next_action=NextAction.NOT_COMPARABLE_BACKFILL,
                relevant_source_classes=classes,
                source_sha256=source_hashes,
                removed_refs=comparison.removed_refs,
                not_comparable_refs=comparison.not_comparable_refs,
                reasons=("no current role-relevant source fingerprints",),
            )
        if comparison.has_missing_current:
            return cls(
                artifact_role=role,
                status=ReuseStatus.STALE_OR_UNREVIEWED,
                fresh_semantic_review_required=True,
                coverage_satisfied_by=CoverageSatisfiedBy.NOT_SATISFIED,
                next_action=NextAction.MANUAL_LIMITATION,
                relevant_source_classes=classes,
                source_sha256=source_hashes,
                unchanged_refs=comparison.unchanged_refs,
                missing_current_refs=comparison.missing_current_refs,
                reasons=("current required source is missing",),
            )
        if comparison.has_not_comparable or not schema_compatible:
            reasons = ["source fingerprints are not comparable"] if comparison.has_not_comparable else []
            if not schema_compatible:
                reasons.append("producer schema is not compatible")
            return cls(
                artifact_role=role,
                status=ReuseStatus.NOT_COMPARABLE,
                fresh_semantic_review_required=True,
                coverage_satisfied_by=CoverageSatisfiedBy.NOT_SATISFIED,
                next_action=NextAction.NOT_COMPARABLE_BACKFILL,
                relevant_source_classes=classes,
                source_sha256=source_hashes,
                unchanged_refs=comparison.unchanged_refs,
                not_comparable_refs=comparison.not_comparable_refs,
                reasons=tuple(reasons),
            )
        if comparison.has_changes or surrounding_context_changed:
            reasons = ["role-relevant source changed"] if comparison.has_changes else []
            if surrounding_context_changed:
                reasons.append("surrounding context changed")
            return cls(
                artifact_role=role,
                status=ReuseStatus.CHANGED_DELTA_REQUIRED,
                fresh_semantic_review_required=True,
                coverage_satisfied_by=CoverageSatisfiedBy.NOT_SATISFIED,
                next_action=NextAction.DELTA_REVIEW,
                relevant_source_classes=classes,
                source_sha256=source_hashes,
                unchanged_refs=comparison.unchanged_refs,
                changed_refs=comparison.changed_refs,
                added_refs=comparison.added_refs,
                removed_refs=comparison.removed_refs,
                reasons=tuple(reasons),
            )
        if not prior_review_current or coverage == CoverageSatisfiedBy.NOT_SATISFIED:
            reasons = []
            if not prior_review_current:
                reasons.append("prior review is stale or absent")
            if coverage == CoverageSatisfiedBy.NOT_SATISFIED:
                reasons.append("required role coverage is not satisfied")
            return cls(
                artifact_role=role,
                status=ReuseStatus.STALE_OR_UNREVIEWED,
                fresh_semantic_review_required=True,
                coverage_satisfied_by=CoverageSatisfiedBy.NOT_SATISFIED,
                next_action=NextAction.FRESH_ROLE_REVIEW,
                relevant_source_classes=classes,
                source_sha256=source_hashes,
                unchanged_refs=comparison.unchanged_refs,
                reasons=tuple(reasons),
            )
        if coverage == CoverageSatisfiedBy.FRESH_ROLE_REVIEW:
            return cls(
                artifact_role=role,
                status=ReuseStatus.STALE_OR_UNREVIEWED,
                fresh_semantic_review_required=True,
                coverage_satisfied_by=CoverageSatisfiedBy.FRESH_ROLE_REVIEW,
                next_action=NextAction.FRESH_ROLE_REVIEW,
                relevant_source_classes=classes,
                source_sha256=source_hashes,
                unchanged_refs=comparison.unchanged_refs,
                reasons=("coverage requires a fresh role review",),
            )
        return cls(
            artifact_role=role,
            status=ReuseStatus.UNCHANGED_REUSABLE,
            fresh_semantic_review_required=False,
            coverage_satisfied_by=coverage,
            next_action=NextAction.REUSE_EXISTING_REVIEW,
            relevant_source_classes=classes,
            source_sha256=source_hashes,
            unchanged_refs=comparison.unchanged_refs,
            reasons=("role-relevant sources unchanged and reviewed coverage is current",),
        )


def coerce_source_class(value: SourceClass | str) -> SourceClass:
    if isinstance(value, SourceClass):
        return value
    return SourceClass(value)


def coerce_artifact_role(value: ArtifactRole | str) -> ArtifactRole:
    if isinstance(value, ArtifactRole):
        return value
    return ArtifactRole(value)


def coerce_coverage(value: CoverageSatisfiedBy | str) -> CoverageSatisfiedBy:
    if isinstance(value, CoverageSatisfiedBy):
        return value
    return CoverageSatisfiedBy(value)


def stable_json_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def source_fingerprint_to_record(source: SourceFingerprint) -> dict[str, object]:
    return {
        "source_ref": source.source_ref,
        "source_class": source.normalized_source_class.value,
        "sha256": source.sha256,
        "available": source.available,
        "state": source.state,
        "schema_version": source.schema_version,
        "producer": source.producer,
    }


def source_fingerprint_from_record(record: dict[str, Any]) -> SourceFingerprint:
    return SourceFingerprint(
        source_ref=str(record["source_ref"]),
        source_class=str(record["source_class"]),
        sha256=record.get("sha256") if isinstance(record.get("sha256"), str) else None,
        available=bool(record.get("available", True)),
        schema_version=str(record.get("schema_version") or ""),
        producer=str(record.get("producer") or ""),
    )


def reuse_decision_to_record(decision: ReuseDecision) -> dict[str, object]:
    return {
        "artifact_role": decision.artifact_role.value,
        "status": decision.status.value,
        "fresh_semantic_review_required": decision.fresh_semantic_review_required,
        "coverage_satisfied_by": decision.coverage_satisfied_by.value,
        "next_action": decision.next_action.value,
        "relevant_source_classes": [source_class.value for source_class in decision.relevant_source_classes],
        "source_sha256": decision.source_sha256,
        "unchanged_refs": list(decision.unchanged_refs),
        "changed_refs": list(decision.changed_refs),
        "added_refs": list(decision.added_refs),
        "removed_refs": list(decision.removed_refs),
        "missing_current_refs": list(decision.missing_current_refs),
        "not_comparable_refs": list(decision.not_comparable_refs),
        "reasons": list(decision.reasons),
    }


def source_classes_for_role(role: ArtifactRole | str) -> frozenset[SourceClass]:
    return ROLE_SOURCE_DEPENDENCIES[coerce_artifact_role(role)]


def relevant_sources(
    sources: Iterable[SourceFingerprint],
    role: ArtifactRole | str,
) -> tuple[SourceFingerprint, ...]:
    dependencies = source_classes_for_role(role)
    return tuple(source for source in sources if source.normalized_source_class in dependencies)


def source_hashes_by_ref(
    sources: Iterable[SourceFingerprint],
    relevant_source_classes: set[SourceClass],
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    seen: set[tuple[str, SourceClass]] = set()
    for source in sources:
        if source.normalized_source_class not in relevant_source_classes or source.sha256 is None:
            continue
        if source.key in seen:
            raise ValueError(
                f"duplicate source fingerprint: {source.source_ref} ({source.normalized_source_class.value})"
            )
        seen.add(source.key)
        existing = hashes.get(source.source_ref)
        if existing is not None and existing != source.sha256:
            raise ValueError(f"conflicting source hashes for {source.source_ref}")
        hashes[source.source_ref] = source.sha256
    return hashes


def compare_source_fingerprints(
    current_sources: Iterable[SourceFingerprint],
    prior_sources: Iterable[SourceFingerprint],
    *,
    role: ArtifactRole | str,
) -> SourceComparison:
    current = keyed_sources(relevant_sources(current_sources, role))
    prior = keyed_sources(relevant_sources(prior_sources, role))
    unchanged: list[str] = []
    changed: list[str] = []
    added: list[str] = []
    removed: list[str] = []
    missing_current: list[str] = []
    not_comparable: list[str] = []

    for key in sorted(current, key=lambda item: (item[1].value, item[0])):
        current_source = current[key]
        prior_source = prior.get(key)
        if not current_source.available:
            missing_current.append(current_source.source_ref)
            continue
        if not current_source.comparable:
            not_comparable.append(current_source.source_ref)
            continue
        if prior_source is None:
            added.append(current_source.source_ref)
            continue
        if not prior_source.available:
            not_comparable.append(current_source.source_ref)
            continue
        if not prior_source.comparable:
            not_comparable.append(current_source.source_ref)
            continue
        if current_source.sha256 == prior_source.sha256:
            unchanged.append(current_source.source_ref)
        else:
            changed.append(current_source.source_ref)

    for key in sorted(set(prior) - set(current), key=lambda item: (item[1].value, item[0])):
        prior_source = prior[key]
        removed.append(prior_source.source_ref)

    return SourceComparison(
        unchanged_refs=tuple(unchanged),
        changed_refs=tuple(changed),
        added_refs=tuple(added),
        removed_refs=tuple(removed),
        missing_current_refs=tuple(missing_current),
        not_comparable_refs=tuple(not_comparable),
    )


def keyed_sources(sources: Iterable[SourceFingerprint]) -> dict[tuple[str, SourceClass], SourceFingerprint]:
    result: dict[tuple[str, SourceClass], SourceFingerprint] = {}
    for source in sources:
        if source.key in result:
            raise ValueError(
                f"duplicate source fingerprint: {source.source_ref} ({source.normalized_source_class.value})"
            )
        result[source.key] = source
    return result


def decide_reuse(
    *,
    artifact_role: ArtifactRole | str,
    current_sources: Iterable[SourceFingerprint],
    prior_sources: Iterable[SourceFingerprint],
    prior_review_current: bool,
    schema_compatible: bool,
    coverage_satisfied_by: CoverageSatisfiedBy | str = CoverageSatisfiedBy.CURRENT_REVIEWED_ARTIFACT,
    surrounding_context_changed: bool = False,
) -> ReuseDecision:
    """Return a deterministic reuse decision for one artifact role."""

    current_tuple = tuple(current_sources)
    comparison = compare_source_fingerprints(current_tuple, tuple(prior_sources), role=artifact_role)
    return ReuseDecision.from_comparison(
        artifact_role=artifact_role,
        relevant_source_classes=source_classes_for_role(artifact_role),
        comparison=comparison,
        current_sources=current_tuple,
        prior_review_current=prior_review_current,
        schema_compatible=schema_compatible,
        coverage_satisfied_by=coverage_satisfied_by,
        surrounding_context_changed=surrounding_context_changed,
    )
