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
from thesis_review_workflow.helper_checks import helper_check_id_error
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
from thesis_review_workflow.submission_bundle import SUBMISSION_BUNDLE_MATERIALIZATION_REL
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
INPUT_DEPENDENCY_PREFIXES = ("notes/", "inputs/", "extracted/")
EVIDENCE_DEPENDENCY_PREFIXES = ("work/", "outputs/")
HANDOFF_DEPENDENCY_REFS = {
    COMMON_BRIEFING_REL,
    "work/review_run_trace.json",
    "work/review_role_plan.json",
}
HANDOFF_DEPENDENCY_PREFIXES = (
    "work/opponent_packets/",
    "work/supervisor_packets/",
    "work/supervisor_report_packets/",
)
REGISTRATION_SIDECAR_SCHEMA = "review-artifact-registration-v1"
REGISTRATION_SIDECAR_GLOB = "work/review_artifacts/*.json"
REGISTRATION_ROLE_OVERRIDES = {
    "outputs/vedouci_posudek_revidovany.md": "thesis-supervisor-report-review",
    "work/quantitative_claims.json": "thesis-quantitative-claims-review",
    "work/supervisor_report_trace.json": "thesis-supervisor-report",
    "work/opponent_report_trace.json": "thesis-opponent-materials",
    "work/feedback_student_draft.md": "thesis-supervisor-feedback",
    "work/vedouci_posudek_draft.md": "thesis-supervisor-report",
    "work/oponent_podklady_draft.md": "thesis-opponent-materials",
    "work/oponent_posudek_draft.md": "thesis-opponent-report-review",
}


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


def dependency_ref_kind(ref: str) -> str:
    if ref in HANDOFF_DEPENDENCY_REFS or ref.startswith(HANDOFF_DEPENDENCY_PREFIXES):
        return "handoff"
    if ref.startswith(INPUT_DEPENDENCY_PREFIXES):
        return "input"
    if ref.startswith(EVIDENCE_DEPENDENCY_PREFIXES):
        return "evidence"
    return "unknown"


def classify_dependency_refs(refs: list[str]) -> tuple[list[str], list[str], list[str], list[str]]:
    input_refs: list[str] = []
    evidence_refs: list[str] = []
    handoff_refs: list[str] = []
    unknown_refs: list[str] = []
    for ref in refs:
        kind = dependency_ref_kind(ref)
        if kind == "input":
            input_refs.append(ref)
        elif kind == "evidence":
            evidence_refs.append(ref)
        elif kind == "handoff":
            handoff_refs.append(ref)
        else:
            unknown_refs.append(ref)
    return input_refs, evidence_refs, handoff_refs, unknown_refs


def validate_dependency_ref_classification(
    *,
    field: str,
    refs: list[str],
    allow_override: bool,
) -> list[str]:
    if allow_override:
        return []
    expected_kind = (
        "input"
        if field == "input_refs"
        else "evidence" if field == "evidence_refs" else "handoff" if field == "handoff_refs" else None
    )
    if expected_kind is None:
        return []
    errors: list[str] = []
    for ref in refs:
        kind = dependency_ref_kind(ref)
        if kind != "unknown" and kind != expected_kind:
            target = "--input-ref" if kind == "input" else "--handoff-ref" if kind == "handoff" else "--evidence-ref"
            errors.append(
                f"{field}: {ref} is a {kind} dependency by path; use {target} or pass "
                "--allow-ref-class-override with an explicit rationale in --notes"
            )
    return errors


def validate_round_rel_values(label: str, values: list[str], *, allow_checks: bool = False) -> None:
    for value in values:
        if allow_checks and value.startswith("check-"):
            if not CHECK_ID_RE.fullmatch(value):
                raise ValueError(f"{label} contains an invalid check id")
            issue = helper_check_id_error(value)
            if issue:
                raise ValueError(f"{label} contains invalid helper check id {value}: {issue}")
            continue
        if not is_safe_round_relative_path(value):
            raise ValueError(f"{label} must contain only safe round-relative paths or check ids")


def output_defaults(rel_path: str) -> tuple[str, list[str], str]:
    return registry_output_defaults(rel_path)


def registration_defaults(
    artifact_path: str,
    *,
    feeds: list[str],
    role: str | None = None,
    review_scope: str | None = None,
    review_status: str | None = None,
) -> dict[str, str | None]:
    spec = output_spec(artifact_path)
    default_role = REGISTRATION_ROLE_OVERRIDES.get(artifact_path)
    if default_role is None and spec is not None and spec.skills:
        default_role = spec.skills[0]
    if default_role is None:
        default_role = "not_recorded"

    resolved_scope = review_scope
    if resolved_scope is None and spec is not None:
        if spec.internal_evidence and feeds:
            resolved_scope = "covered_by_synthesis"
        else:
            resolved_scope = spec.review_scope
    if resolved_scope is None and artifact_path in REGISTRATION_ROLE_OVERRIDES:
        resolved_scope = "covered_by_synthesis" if feeds else "internal_only"

    resolved_status = review_status
    if resolved_status is None:
        resolved_status = "not_required" if resolved_scope == "covered_by_synthesis" else "not_recorded"

    return {
        "role": role or default_role,
        "review_scope": resolved_scope,
        "review_status": resolved_status,
    }


def generated_record(role: str, agent: str, contribution: str, notes: str, provider: str = "") -> dict[str, str]:
    record = {
        "role": role or "not_recorded",
        "agent": agent or "not_recorded",
        "contribution": contribution or "generation",
        "notes": notes,
    }
    # Provider provenance is additive: recorded only when known, so legacy
    # (Codex-era) records keep their exact shape. Independence checks treat a
    # recorded provider that differs from the reviewer's as genuinely
    # independent; see review_approvals.reviewer_matches_generator.
    if provider:
        record["provider"] = provider
    return record


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


def submission_bundle_materialized_refs(round_dir: Path) -> set[str]:
    path = round_dir / SUBMISSION_BUNDLE_MATERIALIZATION_REL
    if not path.is_file():
        return set()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(loaded, dict) or not isinstance(loaded.get("materializations"), list):
        return set()
    refs: set[str] = set()
    for item in loaded["materializations"]:
        if not isinstance(item, dict):
            continue
        ref = item.get("materialized_ref")
        if isinstance(ref, str) and ref.startswith("inputs/") and is_safe_round_relative_path(ref):
            refs.add(ref)
    return refs


def prepared_code_refs_from_sources(round_dir: Path, source_refs: set[str]) -> set[str]:
    manifest = load_round_json(round_dir, "work/code/.prepare-code-workspace-manifest.json")
    if manifest is None:
        return set()
    sources = manifest.get("sources")
    if not isinstance(sources, dict):
        return set()
    refs: set[str] = set()
    for source_ref, source in sources.items():
        if not isinstance(source_ref, str) or source_ref not in source_refs or not isinstance(source, dict):
            continue
        refs.add(source_ref)
        target = source.get("target")
        if isinstance(target, str) and is_safe_round_relative_path(target):
            refs.add(target)
    return refs


def submission_bundle_materialization_dependency_refs(round_dir: Path, refs: list[str]) -> list[str]:
    materialized_refs = submission_bundle_materialized_refs(round_dir)
    if not materialized_refs or not (round_dir / SUBMISSION_BUNDLE_MATERIALIZATION_REL).is_file():
        return []
    ref_set = {ref for ref in refs if isinstance(ref, str)}
    if ref_set & materialized_refs:
        return [SUBMISSION_BUNDLE_MATERIALIZATION_REL]
    code_workspace_refs = {
        "work/code_workspace.md",
        "work/serena_roots.json",
        "work/code/.prepare-code-workspace-manifest.json",
        "work/code_reproducibility.json",
    }
    prepared_refs = prepared_code_refs_from_sources(round_dir, materialized_refs)
    if ref_set & (code_workspace_refs | prepared_refs):
        return [SUBMISSION_BUNDLE_MATERIALIZATION_REL]
    return []


def packet_dependency_refs(round_dir: Path, artifact_type: str) -> list[str]:
    packet_dirs = {
        "supervisor_feedback": "work/supervisor_packets",
        "supervisor_report_reviewed": "work/supervisor_report_packets",
        "opponent_materials_reviewed": "work/opponent_packets",
        "opponent_report_review": "work/opponent_packets",
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
) -> tuple[list[str], list[str], list[str]]:
    path = artifact.get("path")
    if not isinstance(path, str):
        return [], [], []
    artifact_type = str(artifact.get("artifact_type") or output_defaults(path)[0])
    spec = output_spec(path)
    input_refs: list[str] = []
    evidence_refs: list[str] = []
    handoff_refs: list[str] = []
    if artifact.get("dependency_refs_source") == REGISTERED_DEPENDENCY_REFS_SOURCE:
        input_refs.extend(_string_list(artifact.get("input_refs")))
        evidence_refs.extend(_string_list(artifact.get("evidence_refs")))
        handoff_refs.extend(_string_list(artifact.get("handoff_refs")))

    if spec and spec.final_output:
        claim_inputs, claim_evidence = claim_basis_dependency_refs(round_dir, artifact_path=path, artifact=artifact)
        input_refs.extend(claim_inputs)
        evidence_refs.extend(claim_evidence)
        handoff_refs.extend(packet_dependency_refs(round_dir, artifact_type))

    reuse_inputs, reuse_evidence = reuse_index_dependency_refs(round_dir, artifact_type)
    input_refs.extend(reuse_inputs)
    evidence_refs.extend(reuse_evidence)

    review = artifact.get("independent_review")
    if isinstance(review, dict):
        append_ref(evidence_refs, review.get("review_basis_path"))
    evidence_refs.extend(
        submission_bundle_materialization_dependency_refs(
            round_dir,
            [*input_refs, *evidence_refs, *handoff_refs],
        )
    )
    return append_unique([], input_refs), append_unique([], evidence_refs), append_unique([], handoff_refs)


def apply_artifact_dependency_refs(manifest: dict[str, Any], round_dir: Path) -> None:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        input_refs, evidence_refs, handoff_refs = artifact_dependency_refs(manifest, artifact, round_dir)
        if artifact.get("dependency_refs_source") == REGISTERED_DEPENDENCY_REFS_SOURCE:
            artifact["input_refs"] = append_unique(artifact.get("input_refs"), input_refs)
            artifact["evidence_refs"] = append_unique(artifact.get("evidence_refs"), evidence_refs)
            artifact["handoff_refs"] = append_unique(artifact.get("handoff_refs"), handoff_refs)
        else:
            artifact["input_refs"] = input_refs
            artifact["evidence_refs"] = evidence_refs
            artifact["handoff_refs"] = handoff_refs
            artifact["dependency_refs_source"] = GENERATED_DEPENDENCY_REFS_SOURCE
        source_refs: list[str] = []
        for field in ("input_refs", "evidence_refs"):
            values = artifact.get(field)
            if isinstance(values, list):
                source_refs.extend(ref for ref in values if isinstance(ref, str))
        if source_refs:
            artifact["source_sha256"] = source_hashes(round_dir, append_unique([], source_refs))
        else:
            artifact.pop("source_sha256", None)


def registered_supporting_work_refs(record: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for field in ("input_refs", "evidence_refs"):
        values = record.get(field)
        if isinstance(values, list):
            refs.extend(ref for ref in values if isinstance(ref, str))
    source_sha256 = record.get("source_sha256")
    if isinstance(source_sha256, dict):
        refs.extend(ref for ref in source_sha256 if isinstance(ref, str))
    return append_unique([], refs)


def apply_supporting_work_dependency_refs(manifest: dict[str, Any], round_dir: Path) -> None:
    records = manifest.get("supporting_work_artifacts")
    if not isinstance(records, list):
        return
    for record in records:
        if not isinstance(record, dict):
            continue
        refs = registered_supporting_work_refs(record)
        dependency_refs = submission_bundle_materialization_dependency_refs(round_dir, refs)
        if dependency_refs:
            input_refs, evidence_refs = split_dependency_refs([*refs, *dependency_refs])
            record["input_refs"] = append_unique(record.get("input_refs"), input_refs)
            record["evidence_refs"] = append_unique(record.get("evidence_refs"), evidence_refs)
        source_refs = append_unique(
            [], _string_list(record.get("input_refs")) + _string_list(record.get("evidence_refs"))
        )
        if source_refs:
            record["source_sha256"] = source_hashes(round_dir, source_refs)


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
    handoff_refs: list[str] | None = None,
    check_refs: list[str],
    used_findings: str,
    review_basis_path: str,
    notes: str,
    provider: str = "",
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
        generated_record(role, agent, contribution, notes, provider=provider),
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
    existing["feeds"] = append_unique(existing.get("feeds"), feeds)
    existing["input_refs"] = append_unique(existing.get("input_refs"), input_refs)
    existing["evidence_refs"] = append_unique(existing.get("evidence_refs"), evidence_refs)
    if handoff_refs:
        existing["handoff_refs"] = append_unique(existing.get("handoff_refs"), handoff_refs)
    if input_refs or evidence_refs:
        existing["dependency_refs_source"] = REGISTERED_DEPENDENCY_REFS_SOURCE
    existing["check_refs"] = append_unique(existing.get("check_refs"), check_refs)
    source_refs = append_unique([], existing["input_refs"] + existing["evidence_refs"])
    if source_refs:
        existing["source_sha256"] = source_hashes(round_dir, source_refs)
    else:
        existing.pop("source_sha256", None)
    if notes:
        existing["notes"] = notes


def append_unique_generated(values: Any, addition: dict[str, str]) -> list[dict[str, str]]:
    result = [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []
    # Provider is part of the identity so a same-agent record from a different
    # provider is preserved as a distinct entry (not collapsed into a stale one).
    key = (addition["role"], addition["agent"], addition["contribution"], addition.get("provider", ""))
    if not any(
        (item.get("role"), item.get("agent"), item.get("contribution"), item.get("provider", "")) == key
        for item in result
    ):
        result.append(addition)
    return result


def upsert_work_artifact(
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
    handoff_refs: list[str] | None = None,
    input_refs: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    check_refs: list[str] | None = None,
    used_findings: str = "",
    review_basis_path: str = "",
    notes: str,
    provider: str = "",
) -> None:
    path = validate_artifact_rel_path(rel_path, round_dir)
    current_hash = sha256_file(path)
    input_refs = input_refs or []
    evidence_refs = evidence_refs or []
    check_refs = check_refs or []
    records = manifest.setdefault("supporting_work_artifacts", [])
    existing = next((item for item in records if isinstance(item, dict) and item.get("path") == rel_path), None)
    if existing is None:
        existing = {"path": rel_path, "kind": artifact_kind(path)}
        records.append(existing)
    existing["artifact_sha256"] = current_hash
    existing["role"] = role or existing.get("role") or "not_recorded"
    existing["agent"] = agent or existing.get("agent") or "not_recorded"
    existing["review_scope"] = review_scope or existing.get("review_scope") or "internal_only"
    if role and role != "not_recorded":
        existing["skills"] = append_unique(existing.get("skills"), [role])
    existing["generated_by"] = append_unique_generated(
        existing.get("generated_by"),
        generated_record(role, agent, contribution, notes, provider=provider),
    )
    covered_by = feeds[0] if existing["review_scope"] == "covered_by_synthesis" and feeds else ""
    reviewed_hash = current_hash if review_status in {"reviewed", "reviewed_with_notes"} else ""
    evidence_hash = current_hash if existing["review_scope"] == "covered_by_synthesis" else ""
    review_basis_sha256 = ""
    if review_basis_path:
        basis_path = validate_artifact_rel_path(review_basis_path, round_dir)
        review_basis_sha256 = sha256_file(basis_path)
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
    existing["feeds"] = append_unique(existing.get("feeds"), feeds)
    existing["input_refs"] = append_unique(existing.get("input_refs"), input_refs)
    existing["evidence_refs"] = append_unique(existing.get("evidence_refs"), evidence_refs)
    if handoff_refs:
        existing["handoff_refs"] = append_unique(existing.get("handoff_refs"), handoff_refs)
    existing["check_refs"] = append_unique(existing.get("check_refs"), check_refs)
    source_refs = append_unique([], existing["input_refs"] + existing["evidence_refs"])
    if source_refs:
        existing["source_sha256"] = source_hashes(round_dir, source_refs)
    else:
        existing.pop("source_sha256", None)
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
    handoff_refs: list[str] | None = None,
    check_refs: list[str],
    used_findings: str,
    review_basis_path: str,
    notes: str,
    provider: str = "",
) -> None:
    validate_round_rel_values("feeds", feeds)
    validate_round_rel_values("input refs", input_refs)
    validate_round_rel_values("evidence refs", evidence_refs)
    validate_round_rel_values("handoff refs", handoff_refs or [])
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
            handoff_refs=handoff_refs,
            check_refs=check_refs,
            used_findings=used_findings,
            review_basis_path=review_basis_path,
            notes=notes,
            provider=provider,
        )
        return
    upsert_work_artifact(
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
        handoff_refs=handoff_refs,
        input_refs=input_refs,
        evidence_refs=evidence_refs,
        check_refs=check_refs,
        used_findings=used_findings,
        review_basis_path=review_basis_path,
        notes=notes,
        provider=provider,
    )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def apply_artifact_registration_sidecars(manifest: dict[str, Any], round_dir: Path) -> None:
    for path in sorted(round_dir.glob(REGISTRATION_SIDECAR_GLOB)):
        loaded = load_round_json(round_dir, path.relative_to(round_dir).as_posix())
        if loaded is None:
            raise ValueError(f"{path.relative_to(round_dir).as_posix()}: invalid review artifact registration sidecar")
        if loaded.get("schema_version") != REGISTRATION_SIDECAR_SCHEMA:
            raise ValueError(
                f"{path.relative_to(round_dir).as_posix()}: schema_version must be {REGISTRATION_SIDECAR_SCHEMA}"
            )
        artifact_path = loaded.get("artifact_path")
        if not isinstance(artifact_path, str) or not artifact_path:
            raise ValueError(f"{path.relative_to(round_dir).as_posix()}: artifact_path must be a non-empty string")
        feeds = _string_list(loaded.get("feeds"))
        defaults = registration_defaults(
            artifact_path,
            feeds=feeds,
            role=loaded.get("role") if isinstance(loaded.get("role"), str) else None,
            review_scope=loaded.get("review_scope") if isinstance(loaded.get("review_scope"), str) else None,
            review_status=loaded.get("review_status") if isinstance(loaded.get("review_status"), str) else None,
        )
        register_artifact(
            manifest,
            round_dir,
            artifact_path,
            role=str(defaults["role"] or "not_recorded"),
            agent=str(loaded.get("agent") or "not_recorded"),
            contribution=str(loaded.get("contribution") or "generation"),
            review_scope=defaults["review_scope"] if isinstance(defaults["review_scope"], str) else None,
            review_status=str(defaults["review_status"] or "not_recorded"),
            reviewer_role=str(loaded.get("reviewer_role") or "not_recorded"),
            reviewer_agent=str(loaded.get("reviewer_agent") or "not_recorded"),
            reviewed_at=str(loaded.get("reviewed_at") or ""),
            limitation=_string_list(loaded.get("limitations")),
            feeds=feeds,
            input_refs=_string_list(loaded.get("input_refs")),
            evidence_refs=_string_list(loaded.get("evidence_refs")),
            handoff_refs=_string_list(loaded.get("handoff_refs")),
            check_refs=_string_list(loaded.get("check_refs")),
            used_findings=str(loaded.get("used_findings") or ""),
            review_basis_path=str(loaded.get("review_basis_path") or ""),
            notes=str(loaded.get("notes") or ""),
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
        generated_by = artifact.get("generated_by")
        has_recorded_generator = False
        if isinstance(generated_by, list):
            for item in generated_by:
                if not isinstance(item, dict):
                    continue
                role = str(item.get("role") or "").strip()
                agent = str(item.get("agent") or "").strip()
                if role and role != "not_recorded" and agent and agent != "not_recorded":
                    has_recorded_generator = True
                    break
        if not has_recorded_generator:
            artifact["generated_by"] = [
                {
                    "role": str(payload.get("reviewer_role") or "not_recorded"),
                    "agent": str(payload.get("reviewer_agent") or "manual"),
                    "contribution": "final_review",
                    "notes": f"Imported from structured approval record `{approval_rel_path}`.",
                }
            ]
        artifact["independent_review"] = review_record_from_approval(payload, approval_rel_path)
        limitations = artifact.get("limitations")
        existing_limitations = (
            [item for item in limitations if isinstance(item, str)] if isinstance(limitations, list) else []
        )
        artifact["limitations"] = append_unique(existing_limitations, string_list(payload.get("limitations")))


def merge_supporting_work_artifacts(
    existing_records: Any,
    generated_records: list[dict[str, str]],
    *,
    round_dir: Path | None = None,
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
            for key in (
                "role",
                "agent",
                "review_scope",
                "limitations",
                "feeds",
                "notes",
                "skills",
                "generated_by",
                "independent_review",
                "input_refs",
                "evidence_refs",
                "handoff_refs",
                "check_refs",
                "source_sha256",
            ):
                if key in previous and key not in generated:
                    preserved[key] = previous[key]
            if round_dir is not None and isinstance(preserved.get("handoff_refs"), list):
                preserved["handoff_refs"] = existing_round_refs(round_dir, preserved["handoff_refs"])
            merged.append(preserved)
        else:
            merged.append(generated)
        merged_paths.add(generated["path"])
    for path, previous in sorted(existing_by_path.items()):
        if not isinstance(path, str):
            continue
        if path not in merged_paths:
            if round_dir is not None:
                if not is_safe_round_relative_path(path):
                    continue
                previous_path = round_dir / path
                if not previous_path.is_file():
                    continue
                previous = {
                    **previous,
                    "kind": artifact_kind(previous_path),
                    "artifact_sha256": sha256_file(previous_path),
                }
                if isinstance(previous.get("handoff_refs"), list):
                    previous["handoff_refs"] = existing_round_refs(round_dir, previous["handoff_refs"])
            merged.append(previous)
    return merged


def existing_round_refs(round_dir: Path, refs: Any) -> list[str]:
    if not isinstance(refs, list):
        return []
    existing: list[str] = []
    for ref in refs:
        if isinstance(ref, str) and is_safe_round_relative_path(ref) and (round_dir / ref).is_file():
            existing.append(ref)
    return existing
