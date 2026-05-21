"""Shared coverage contract for silent Theses.cz similarity evidence."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

from thesis_review_workflow.structured_evidence import validate_structured_evidence_artifact
from thesis_review_workflow.theses_similarity import (
    SIMILARITY_UNRESOLVED_CATEGORIES,
    THESES_SIMILARITY_ASSESSMENT_REL,
    THESES_SIMILARITY_SILENT_USED_FINDINGS,
)

REVIEW_MANIFEST_REL = "work/review_manifest.json"
SYNTHESIS_ARTIFACT_BY_WORKFLOW = {
    "supervisor_feedback": "outputs/feedback_student.md",
    "supervisor_report": "outputs/vedouci_posudek_revidovany.md",
    "opponent_review": "outputs/oponent_podklady_revidovane.md",
}
REVIEWED_MANIFEST_STATUSES = {"reviewed", "reviewed_with_notes"}
SILENT_THESES_SIMILARITY_SYNTHESIS_WORKFLOWS = {"supervisor_report", "opponent_review"}
SILENT_THESES_SIMILARITY_SYNTHESIS_ARTIFACTS = frozenset(
    SYNTHESIS_ARTIFACT_BY_WORKFLOW[workflow] for workflow in SILENT_THESES_SIMILARITY_SYNTHESIS_WORKFLOWS
)


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json_object(path: Path) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def manifest_artifacts_by_path(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for collection in ("artifacts", "supporting_work_artifacts"):
        records = manifest.get(collection)
        if not isinstance(records, list):
            continue
        for record in records:
            if isinstance(record, dict) and isinstance(record.get("path"), str):
                artifacts.setdefault(record["path"], record)
    return artifacts


def artifact_current_hash(round_dir: Path, artifact: dict[str, Any], artifact_path: str) -> str | None:
    path = round_dir / artifact_path
    if not path.is_file():
        return None
    current_hash = sha256_file(path)
    recorded_hash = artifact.get("artifact_sha256")
    if isinstance(recorded_hash, str) and recorded_hash != current_hash:
        return None
    return current_hash


def load_current_theses_similarity_assessment(
    round_dir: Path,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
) -> dict[str, Any] | None:
    errors = validate_structured_evidence_artifact(
        round_dir,
        THESES_SIMILARITY_ASSESSMENT_REL,
        case_id=case_id,
        round_id=round_id,
        require_existing_refs=True,
    )
    if errors:
        return None
    return load_json_object(round_dir / THESES_SIMILARITY_ASSESSMENT_REL)


def theses_similarity_assessment_is_silent_no_concern(payload: dict[str, Any]) -> bool:
    judgments = payload.get("judgments")
    if not isinstance(judgments, list) or not judgments:
        return False
    for judgment in judgments:
        if not isinstance(judgment, dict):
            return False
        category = judgment.get("category")
        if category in SIMILARITY_UNRESOLVED_CATEGORIES:
            return False
        if judgment.get("synthesis_action") != "silent":
            return False
        if judgment.get("requires_reviewer_verification") is not False:
            return False
    return True


def _allowed_synthesis_paths(
    *,
    workflow_profile: str | None,
    allowed_synthesis_paths: Iterable[str] | None,
) -> set[str]:
    if workflow_profile is not None:
        if workflow_profile not in SILENT_THESES_SIMILARITY_SYNTHESIS_WORKFLOWS:
            return set()
        return {SYNTHESIS_ARTIFACT_BY_WORKFLOW[workflow_profile]}
    if allowed_synthesis_paths is None:
        return set(SILENT_THESES_SIMILARITY_SYNTHESIS_ARTIFACTS)
    return set(allowed_synthesis_paths) & set(SILENT_THESES_SIMILARITY_SYNTHESIS_ARTIFACTS)


def synthesis_artifact_review_current(
    round_dir: Path,
    artifacts_by_path: dict[str, dict[str, Any]],
    synthesis_path: str,
) -> bool:
    synthesis = artifacts_by_path.get(synthesis_path)
    if synthesis is None:
        return False
    current_hash = artifact_current_hash(round_dir, synthesis, synthesis_path)
    if current_hash is None:
        return False
    review = synthesis.get("independent_review")
    if not isinstance(review, dict):
        return False
    return review.get("status") in REVIEWED_MANIFEST_STATUSES and review.get("reviewed_hash") == current_hash


def theses_similarity_silent_internal_evidence_satisfied(
    round_dir: Path,
    manifest: dict[str, Any] | None = None,
    *,
    workflow_profile: str | None = None,
    allowed_synthesis_paths: Iterable[str] | None = None,
    case_id: str | None = None,
    round_id: str | None = None,
) -> bool:
    allowed_paths = _allowed_synthesis_paths(
        workflow_profile=workflow_profile,
        allowed_synthesis_paths=allowed_synthesis_paths,
    )
    if not allowed_paths:
        return False
    assessment = load_current_theses_similarity_assessment(round_dir, case_id=case_id, round_id=round_id)
    if assessment is None or not theses_similarity_assessment_is_silent_no_concern(assessment):
        return False

    resolved_manifest = manifest
    if resolved_manifest is None:
        resolved_manifest = load_json_object(round_dir / REVIEW_MANIFEST_REL)
    if resolved_manifest is None:
        return False

    artifacts = manifest_artifacts_by_path(resolved_manifest)
    artifact = artifacts.get(THESES_SIMILARITY_ASSESSMENT_REL)
    if artifact is None:
        return False
    current_hash = artifact_current_hash(round_dir, artifact, THESES_SIMILARITY_ASSESSMENT_REL)
    if current_hash is None:
        return False
    if artifact.get("review_scope") != "covered_by_synthesis":
        return False

    review = artifact.get("independent_review")
    if not isinstance(review, dict):
        return False
    covered_by = review.get("covered_by_artifact")
    if covered_by not in allowed_paths:
        return False
    if review.get("status") != "not_required":
        return False
    if review.get("used_findings") != THESES_SIMILARITY_SILENT_USED_FINDINGS:
        return False
    if review.get("evidence_hash") != current_hash:
        return False
    return synthesis_artifact_review_current(round_dir, artifacts, covered_by)
