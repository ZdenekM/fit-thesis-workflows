"""Incremental helpers for round review provenance manifests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_registry import explicit_internal_review_filenames
from thesis_review_workflow.artifact_registry import output_defaults as registry_output_defaults
from thesis_review_workflow.artifact_registry import output_spec
from thesis_review_workflow.claim_review_basis import CLAIM_REVIEW_BASIS_REL
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.reuse import ArtifactRole
from thesis_review_workflow.review_approvals import (
    REVIEW_APPROVAL_GLOB,
    load_review_approval,
    review_record_from_approval,
    string_list,
    validate_review_approval_with_manifest,
)
from thesis_review_workflow.review_packets import COMMON_BRIEFING_REL
from thesis_review_workflow.work_artifacts import artifact_kind, sha256_file

MANIFEST_REL = Path("work/review_manifest.json")
SCHEMA_VERSION = "review-manifest-v1"
CHECK_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
REQUIRE_STANDALONE_REVIEW_FILENAMES = explicit_internal_review_filenames()
REUSE_INDEX_REL = "work/reuse/reuse_index.json"
REUSE_ARTIFACT_BY_TYPE = {
    "github_code_intake": ArtifactRole.GITHUB_CODE_INTAKE.value,
    "code_consistency": ArtifactRole.CODE_CONSISTENCY.value,
    "code_quality_review": ArtifactRole.CODE_QUALITY.value,
    "literature_citation_review": ArtifactRole.LITERATURE_CITATION.value,
    "figure_media_review": ArtifactRole.FIGURE_MEDIA.value,
    "typography_formal_review": ArtifactRole.TYPOGRAPHY_FORMAL.value,
    "theses_similarity_review": ArtifactRole.THESES_SIMILARITY.value,
    "supervisor_feedback": ArtifactRole.SUPERVISOR_FEEDBACK.value,
    "supervisor_report_reviewed": ArtifactRole.SUPERVISOR_REPORT.value,
    "opponent_materials_reviewed": ArtifactRole.OPPONENT_MATERIALS.value,
    "opponent_report_review": ArtifactRole.OPPONENT_REPORT_REVIEW.value,
}
REGISTERED_DEPENDENCY_REFS_SOURCE = "registered"
GENERATED_DEPENDENCY_REFS_SOURCE = "generated"


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return loaded


def write_manifest(path: Path, manifest: dict[str, Any], updated_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest["updated_at"] = updated_at
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def minimal_manifest(case_id: str, round_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "round_id": round_id,
        "updated_at": "",
        "manifest_path": MANIFEST_REL.as_posix(),
        "inputs": [],
        "extracted_artifacts": [],
        "notes": [],
        "supporting_work_artifacts": [],
        "helper_checks": [],
        "workflow_limitations": [],
        "artifacts": [],
    }


def ensure_manifest(manifest: dict[str, Any], case_id: str, round_id: str) -> dict[str, Any]:
    if not manifest:
        return minimal_manifest(case_id, round_id)
    manifest.setdefault("schema_version", SCHEMA_VERSION)
    manifest.setdefault("case_id", case_id)
    manifest.setdefault("round_id", round_id)
    manifest.setdefault("manifest_path", MANIFEST_REL.as_posix())
    for key in (
        "inputs",
        "extracted_artifacts",
        "notes",
        "supporting_work_artifacts",
        "helper_checks",
        "workflow_limitations",
        "artifacts",
    ):
        if not isinstance(manifest.get(key), list):
            manifest[key] = []
    return manifest


def validate_artifact_rel_path(rel_path: str, round_dir: Path) -> Path:
    if not is_safe_round_relative_path(rel_path):
        raise ValueError("artifact path must be a safe relative path inside the round")
    if not (rel_path.startswith("outputs/") or rel_path.startswith("work/")):
        raise ValueError("artifact path must be under outputs/ or work/")
    path = round_dir / rel_path
    if not path.is_file():
        raise ValueError(f"artifact file does not exist: {rel_path}")
    return path


def validate_round_rel_values(label: str, values: list[str], *, allow_checks: bool = False) -> None:
    for value in values:
        if allow_checks and value.startswith("check-"):
            if not CHECK_ID_RE.fullmatch(value):
                raise ValueError(f"{label} contains an invalid check id")
            continue
        if not is_safe_round_relative_path(value):
            raise ValueError(f"{label} must contain only safe round-relative paths or check ids")


def output_defaults(rel_path: str) -> tuple[str, list[str], str]:
    return registry_output_defaults(rel_path)


def generated_record(role: str, agent: str, contribution: str, notes: str) -> dict[str, str]:
    return {
        "role": role or "not_recorded",
        "agent": agent or "not_recorded",
        "contribution": contribution or "generation",
        "notes": notes,
    }


def review_record(
    *,
    status: str,
    reviewer_role: str,
    reviewer_agent: str,
    reviewed_at: str,
    reviewed_hash: str,
    covered_by: str,
    used_findings: str,
    exception: str,
    notes: str,
    evidence_hash: str = "",
    review_basis_path: str = "",
    review_basis_sha256: str = "",
) -> dict[str, str]:
    record = {
        "status": status or "not_recorded",
        "reviewer_role": reviewer_role or "not_recorded",
        "reviewer_agent": reviewer_agent or "not_recorded",
        "reviewed_at": reviewed_at,
        "reviewed_hash": reviewed_hash,
        "covered_by_artifact": covered_by,
        "used_findings": used_findings,
        "exception": exception,
        "notes": notes,
    }
    if evidence_hash:
        record["evidence_hash"] = evidence_hash
    if review_basis_path:
        record["review_basis_path"] = review_basis_path
    if review_basis_sha256:
        record["review_basis_sha256"] = review_basis_sha256
    return record


def append_unique(values: Any, additions: list[str]) -> list[str]:
    result = [item for item in values if isinstance(item, str)] if isinstance(values, list) else []
    for item in additions:
        if item and item not in result:
            result.append(item)
    return result


def source_hashes(round_dir: Path, refs: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for ref in refs:
        if not is_safe_round_relative_path(ref):
            continue
        path = round_dir / ref
        if path.is_file():
            hashes[ref] = sha256_file(path)
    return hashes


def append_ref(target: list[str], ref: Any) -> None:
    if isinstance(ref, str) and is_safe_round_relative_path(ref) and ref not in target:
        target.append(ref)


def split_dependency_refs(refs: list[str]) -> tuple[list[str], list[str]]:
    input_refs: list[str] = []
    evidence_refs: list[str] = []
    for ref in refs:
        if ref.startswith(("inputs/", "extracted/", "notes/")):
            append_ref(input_refs, ref)
        elif ref.startswith(("work/", "outputs/")):
            append_ref(evidence_refs, ref)
    return input_refs, evidence_refs


def load_round_json(round_dir: Path, rel_path: str) -> dict[str, Any] | None:
    path = round_dir / rel_path
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def claim_basis_applies_to_artifact(
    loaded: dict[str, Any],
    artifact_path: str,
    artifact: dict[str, Any] | None = None,
) -> bool:
    draft_ref = loaded.get("draft_ref")
    if not isinstance(draft_ref, str) or not draft_ref:
        return False
    candidates: list[str] = []
    if artifact is not None:
        review = artifact.get("independent_review")
        if isinstance(review, dict):
            review_basis_path = review.get("review_basis_path")
            if isinstance(review_basis_path, str) and review_basis_path:
                candidates.append(review_basis_path)
    spec = output_spec(artifact_path)
    if spec is not None:
        candidates.extend(spec.review_basis_candidates)
    return draft_ref in candidates


def claim_basis_dependency_refs(
    round_dir: Path,
    *,
    artifact_path: str | None = None,
    artifact: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    loaded = load_round_json(round_dir, CLAIM_REVIEW_BASIS_REL)
    if loaded is None:
        return [], []
    if artifact_path is not None and not claim_basis_applies_to_artifact(loaded, artifact_path, artifact):
        return [], []
    refs: list[str] = [CLAIM_REVIEW_BASIS_REL]
    append_ref(refs, loaded.get("draft_ref"))
    for ref in loaded.get("capsule_refs", []):
        append_ref(refs, ref)
    claims = loaded.get("claims")
    if isinstance(claims, list):
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            for field in ("evidence_refs", "capsule_refs"):
                for ref in claim.get(field, []):
                    append_ref(refs, ref)
            escalations = claim.get("raw_source_escalations")
            if isinstance(escalations, list):
                for escalation in escalations:
                    if not isinstance(escalation, dict):
                        continue
                    for ref in escalation.get("source_refs", []):
                        append_ref(refs, ref)
    return split_dependency_refs(refs)


def reuse_index_dependency_refs(round_dir: Path, artifact_type: str) -> tuple[list[str], list[str]]:
    artifact_role = REUSE_ARTIFACT_BY_TYPE.get(artifact_type)
    if artifact_role is None:
        return [], []
    loaded = load_round_json(round_dir, REUSE_INDEX_REL)
    if loaded is None:
        return [], []
    decisions = loaded.get("decisions")
    if isinstance(decisions, list):
        for decision in decisions:
            if not isinstance(decision, dict) or decision.get("artifact_role") != artifact_role:
                continue
            refs: list[str] = [REUSE_INDEX_REL]
            source_sha256 = decision.get("source_sha256")
            if isinstance(source_sha256, dict):
                for ref in source_sha256:
                    append_ref(refs, ref)
            return split_dependency_refs(refs)
    return [], []


def packet_dependency_refs(round_dir: Path, artifact_type: str) -> list[str]:
    packet_dirs = {
        "supervisor_feedback": "work/supervisor_packets",
        "supervisor_report_reviewed": "work/supervisor_report_packets",
        "opponent_materials_reviewed": "work/opponent_packets",
    }
    refs: list[str] = []
    if (round_dir / COMMON_BRIEFING_REL).is_file():
        refs.append(COMMON_BRIEFING_REL)
    packet_dir = packet_dirs.get(artifact_type)
    if packet_dir and (round_dir / packet_dir).is_dir():
        refs.extend(
            path.relative_to(round_dir).as_posix()
            for path in sorted((round_dir / packet_dir).glob("*.md"))
            if path.is_file()
        )
    return refs


def artifact_dependency_refs(
    manifest: dict[str, Any],
    artifact: dict[str, Any],
    round_dir: Path,
) -> tuple[list[str], list[str]]:
    path = artifact.get("path")
    if not isinstance(path, str):
        return [], []
    artifact_type = str(artifact.get("artifact_type") or output_defaults(path)[0])
    spec = output_spec(path)
    input_refs: list[str] = []
    evidence_refs: list[str] = []

    if spec and spec.final_output:
        claim_inputs, claim_evidence = claim_basis_dependency_refs(round_dir, artifact_path=path, artifact=artifact)
        input_refs.extend(claim_inputs)
        evidence_refs.extend(claim_evidence)
        evidence_refs.extend(packet_dependency_refs(round_dir, artifact_type))

    reuse_inputs, reuse_evidence = reuse_index_dependency_refs(round_dir, artifact_type)
    input_refs.extend(reuse_inputs)
    evidence_refs.extend(reuse_evidence)

    review = artifact.get("independent_review")
    if isinstance(review, dict):
        append_ref(evidence_refs, review.get("review_basis_path"))
    return append_unique([], input_refs), append_unique([], evidence_refs)


def apply_artifact_dependency_refs(manifest: dict[str, Any], round_dir: Path) -> None:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        input_refs, evidence_refs = artifact_dependency_refs(manifest, artifact, round_dir)
        if artifact.get("dependency_refs_source") == REGISTERED_DEPENDENCY_REFS_SOURCE:
            artifact["input_refs"] = append_unique(artifact.get("input_refs"), input_refs)
            artifact["evidence_refs"] = append_unique(artifact.get("evidence_refs"), evidence_refs)
        else:
            artifact["input_refs"] = input_refs
            artifact["evidence_refs"] = evidence_refs
            artifact["dependency_refs_source"] = GENERATED_DEPENDENCY_REFS_SOURCE
        source_refs: list[str] = []
        for field in ("input_refs", "evidence_refs"):
            values = artifact.get(field)
            if isinstance(values, list):
                source_refs.extend(ref for ref in values if isinstance(ref, str))
        if source_refs:
            artifact["source_sha256"] = source_hashes(round_dir, append_unique([], source_refs))


def upsert_output_artifact(
    manifest: dict[str, Any],
    round_dir: Path,
    rel_path: str,
    *,
    role: str,
    agent: str,
    contribution: str,
    review_scope: str | None,
    review_status: str,
    reviewer_role: str,
    reviewer_agent: str,
    reviewed_at: str,
    limitation: list[str],
    feeds: list[str],
    input_refs: list[str],
    evidence_refs: list[str],
    check_refs: list[str],
    used_findings: str,
    review_basis_path: str,
    notes: str,
) -> None:
    path = validate_artifact_rel_path(rel_path, round_dir)
    artifact_type, skills, default_scope = output_defaults(rel_path)
    current_hash = sha256_file(path)
    artifacts = manifest.setdefault("artifacts", [])
    existing = next(
        (item for item in artifacts if isinstance(item, dict) and item.get("path") == rel_path),
        None,
    )
    if existing is None:
        existing = {
            "path": rel_path,
            "artifact_type": artifact_type,
            "skills": skills,
            "generated_by": [],
            "helper_checks": [],
        }
        artifacts.append(existing)

    if Path(rel_path).name in REQUIRE_STANDALONE_REVIEW_FILENAMES:
        scope = "internal_only"
    else:
        scope = review_scope or str(existing.get("review_scope") or default_scope)
    covered_by = feeds[0] if scope == "covered_by_synthesis" and feeds else ""
    reviewed_hash = current_hash if review_status in {"reviewed", "reviewed_with_notes"} else ""
    evidence_hash = current_hash if scope == "covered_by_synthesis" else ""
    review_basis_sha256 = ""
    if review_basis_path:
        basis_path = validate_artifact_rel_path(review_basis_path, round_dir)
        review_basis_sha256 = sha256_file(basis_path)
    if output_spec(rel_path) is None:
        existing["artifact_type"] = existing.get("artifact_type") or artifact_type
        existing["skills"] = existing.get("skills") or skills
    else:
        existing["artifact_type"] = artifact_type
        existing["skills"] = skills
    existing["artifact_sha256"] = current_hash
    existing["review_scope"] = scope
    existing["generated_by"] = append_unique_generated(
        existing.get("generated_by"),
        generated_record(role, agent, contribution, notes),
    )
    existing["independent_review"] = review_record(
        status=review_status,
        reviewer_role=reviewer_role,
        reviewer_agent=reviewer_agent,
        reviewed_at=reviewed_at,
        reviewed_hash=reviewed_hash,
        covered_by=covered_by,
        used_findings=used_findings,
        exception="",
        notes=notes,
        evidence_hash=evidence_hash,
        review_basis_path=review_basis_path,
        review_basis_sha256=review_basis_sha256,
    )
    existing["limitations"] = append_unique(existing.get("limitations"), limitation)
    existing["input_refs"] = append_unique(existing.get("input_refs"), input_refs)
    existing["evidence_refs"] = append_unique(existing.get("evidence_refs"), evidence_refs + feeds)
    if input_refs or evidence_refs:
        existing["dependency_refs_source"] = REGISTERED_DEPENDENCY_REFS_SOURCE
    existing["check_refs"] = append_unique(existing.get("check_refs"), check_refs)
    source_refs = append_unique([], existing["input_refs"] + existing["evidence_refs"])
    if source_refs:
        existing["source_sha256"] = source_hashes(round_dir, source_refs)
    if notes:
        existing["notes"] = notes


def append_unique_generated(values: Any, addition: dict[str, str]) -> list[dict[str, str]]:
    result = [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []
    key = (addition["role"], addition["agent"], addition["contribution"])
    if not any((item.get("role"), item.get("agent"), item.get("contribution")) == key for item in result):
        result.append(addition)
    return result


def upsert_work_artifact(
    manifest: dict[str, Any],
    round_dir: Path,
    rel_path: str,
    *,
    role: str,
    agent: str,
    review_scope: str | None,
    limitation: list[str],
    feeds: list[str],
    notes: str,
) -> None:
    path = validate_artifact_rel_path(rel_path, round_dir)
    current_hash = sha256_file(path)
    records = manifest.setdefault("supporting_work_artifacts", [])
    existing = next((item for item in records if isinstance(item, dict) and item.get("path") == rel_path), None)
    if existing is None:
        existing = {"path": rel_path, "kind": artifact_kind(path)}
        records.append(existing)
    existing["artifact_sha256"] = current_hash
    existing["role"] = role or existing.get("role") or "not_recorded"
    existing["agent"] = agent or existing.get("agent") or "not_recorded"
    existing["review_scope"] = review_scope or existing.get("review_scope") or "internal_only"
    existing["limitations"] = append_unique(existing.get("limitations"), limitation)
    existing["feeds"] = append_unique(existing.get("feeds"), feeds)
    if notes:
        existing["notes"] = notes


def register_artifact(
    manifest: dict[str, Any],
    round_dir: Path,
    rel_path: str,
    *,
    role: str,
    agent: str,
    contribution: str,
    review_scope: str | None,
    review_status: str,
    reviewer_role: str,
    reviewer_agent: str,
    reviewed_at: str,
    limitation: list[str],
    feeds: list[str],
    input_refs: list[str],
    evidence_refs: list[str],
    check_refs: list[str],
    used_findings: str,
    review_basis_path: str,
    notes: str,
) -> None:
    validate_round_rel_values("feeds", feeds)
    validate_round_rel_values("input refs", input_refs)
    validate_round_rel_values("evidence refs", evidence_refs)
    validate_round_rel_values("check refs", check_refs, allow_checks=True)
    if rel_path.startswith("outputs/"):
        upsert_output_artifact(
            manifest,
            round_dir,
            rel_path,
            role=role,
            agent=agent,
            contribution=contribution,
            review_scope=review_scope,
            review_status=review_status,
            reviewer_role=reviewer_role,
            reviewer_agent=reviewer_agent,
            reviewed_at=reviewed_at,
            limitation=limitation,
            feeds=feeds,
            input_refs=input_refs,
            evidence_refs=evidence_refs,
            check_refs=check_refs,
            used_findings=used_findings,
            review_basis_path=review_basis_path,
            notes=notes,
        )
        return
    upsert_work_artifact(
        manifest,
        round_dir,
        rel_path,
        role=role,
        agent=agent,
        review_scope=review_scope,
        limitation=limitation,
        feeds=feeds,
        notes=notes,
    )


def apply_review_approval_records(manifest: dict[str, Any], round_dir: Path) -> None:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return
    case_id = manifest.get("case_id")
    round_id = manifest.get("round_id")
    by_reviewed_path: dict[str, tuple[str, dict[str, Any]]] = {}
    for approval_path in sorted(round_dir.glob(REVIEW_APPROVAL_GLOB)):
        rel_path = approval_path.relative_to(round_dir).as_posix()
        payload, load_errors = load_review_approval(round_dir, rel_path)
        if load_errors or payload is None:
            continue
        errors = validate_review_approval_with_manifest(
            payload,
            rel_path,
            round_dir,
            manifest=manifest,
            case_id=case_id if isinstance(case_id, str) else None,
            round_id=round_id if isinstance(round_id, str) else None,
        )
        if errors:
            continue
        reviewed_path = payload.get("reviewed_artifact_path")
        if isinstance(reviewed_path, str):
            by_reviewed_path[reviewed_path] = (rel_path, payload)

    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        artifact_path = artifact.get("path")
        if not isinstance(artifact_path, str):
            continue
        approval = by_reviewed_path.get(artifact_path)
        if approval is None:
            continue
        approval_rel_path, payload = approval
        artifact["independent_review"] = review_record_from_approval(payload, approval_rel_path)
        limitations = artifact.get("limitations")
        existing_limitations = (
            [item for item in limitations if isinstance(item, str)] if isinstance(limitations, list) else []
        )
        artifact["limitations"] = append_unique(existing_limitations, string_list(payload.get("limitations")))


def merge_supporting_work_artifacts(
    existing_records: Any,
    generated_records: list[dict[str, str]],
) -> list[dict[str, Any]]:
    existing_by_path = (
        {
            item.get("path"): item
            for item in existing_records
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
        if isinstance(existing_records, list)
        else {}
    )
    merged: list[dict[str, Any]] = []
    merged_paths: set[str] = set()
    for generated in generated_records:
        previous = existing_by_path.get(generated["path"])
        if isinstance(previous, dict):
            preserved = {**previous, **generated}
            for key in ("role", "agent", "review_scope", "limitations", "feeds", "notes"):
                if key in previous and key not in generated:
                    preserved[key] = previous[key]
            merged.append(preserved)
        else:
            merged.append(generated)
        merged_paths.add(generated["path"])
    for path, previous in sorted(existing_by_path.items()):
        if path not in merged_paths:
            merged.append(previous)
    return merged
