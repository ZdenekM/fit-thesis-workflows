"""Round-local work artifact contracts used by review provenance."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.claim_review_basis import (
    CLAIM_REVIEW_BASIS_REL,
    CLAIM_REVIEW_BASIS_SCHEMA,
    validate_claim_review_basis_payload,
)
from thesis_review_workflow.code_quality_omen import (
    CODE_QUALITY_OMEN_REL,
    CODE_QUALITY_OMEN_SCHEMA,
    validate_code_quality_omen_payload,
)
from thesis_review_workflow.evidence_capsules import (
    EVIDENCE_CAPSULE_SCHEMA,
    EVIDENCE_CAPSULES_REL,
    validate_evidence_capsules_payload,
)
from thesis_review_workflow.literature_source_acquisition import (
    SOURCE_ACQUISITION_REL,
    SOURCE_ACQUISITION_SCHEMA,
    validate_source_acquisition_payload,
)
from thesis_review_workflow.opponent_calibration import (
    is_opponent_calibration_artifact,
    validate_opponent_calibration_artifact,
)
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.report_calibration import (
    REPORT_CALIBRATION_BASIS_REL,
    REPORT_CALIBRATION_BASIS_SCHEMA,
    is_report_calibration_basis_path,
    validate_report_calibration_artifact,
    validate_report_calibration_payload,
)
from thesis_review_workflow.review_approvals import is_review_approval_path, validate_review_approval_artifact
from thesis_review_workflow.review_delta import is_review_delta_artifact, validate_review_delta_record
from thesis_review_workflow.review_packets import (
    COMMON_BRIEFING_REL,
    COMMON_BRIEFING_SCHEMA_VERSION,
    validate_common_briefing_payload,
)
from thesis_review_workflow.review_pipeline_orchestration import (
    REVIEW_ROLE_PLAN_REL,
    REVIEW_ROLE_PLAN_SCHEMA,
    REVIEW_RUN_TRACE_REL,
    REVIEW_RUN_TRACE_SCHEMA,
    validate_review_role_plan_payload,
    validate_review_run_trace_payload,
)
from thesis_review_workflow.structured_evidence import STRUCTURED_EVIDENCE_SCHEMAS, validate_structured_evidence_payload
from thesis_review_workflow.submission_bundle import (
    SUBMISSION_BUNDLE_INVENTORY_REL,
    SUBMISSION_BUNDLE_INVENTORY_SCHEMA,
    SUBMISSION_BUNDLE_INVENTORY_SUMMARY_REL,
    SUBMISSION_BUNDLE_MATERIALIZATION_REL,
    SUBMISSION_BUNDLE_MATERIALIZATION_SCHEMA,
    validate_submission_bundle_materialization_payload,
)
from thesis_review_workflow.submitted_report_deltas import (
    is_submitted_report_delta_artifact,
    validate_opponent_submitted_report_deltas,
)
from thesis_review_workflow.submitted_reports import is_submitted_report_artifact, validate_submitted_report_record
from thesis_review_workflow.supervisor_report_calibration import (
    is_supervisor_report_calibration_artifact,
    validate_supervisor_report_calibration_artifact,
)
from thesis_review_workflow.theses_checker_summary import (
    THESES_CHECKER_SUMMARY_REL,
    THESES_CHECKER_SUMMARY_SCHEMA,
    validate_theses_checker_summary_payload,
)
from thesis_review_workflow.theses_similarity import (
    THESES_SIMILARITY_ASSESSMENT_REL,
    THESES_SIMILARITY_ASSESSMENT_SCHEMA,
    THESES_SIMILARITY_INTAKE_REL,
    THESES_SIMILARITY_INTAKE_SCHEMA,
    THESES_SIMILARITY_REVIEW_DRAFT_REL,
)

KNOWN_JSON_ARTIFACT_SCHEMAS: dict[str, set[str]] = {
    "work/assignment_coverage_agent.json": {"assignment-coverage-agent-v1"},
    "work/evidence_requirements.json": {"evidence-requirements-v1"},
    "work/quantitative_claims.json": {"quantitative-claims-v1"},
    "work/opponent_report_trace.json": {"opponent-report-trace-v2"},
    "work/supervisor_report_feedback_history.json": {"supervisor-report-feedback-history-v1"},
    "work/supervisor_report_trace.json": {"supervisor-report-trace-v1"},
    "work/supervisor_report_confirmation.json": {"supervisor-report-confirmation-v1"},
    "work/current_evidence_snapshot.json": {"current-evidence-snapshot-v1"},
    "work/code_reproducibility.json": {"code-reproducibility-v1"},
    CODE_QUALITY_OMEN_REL: {CODE_QUALITY_OMEN_SCHEMA},
    SOURCE_ACQUISITION_REL: {SOURCE_ACQUISITION_SCHEMA},
    "work/github-intake/snapshot-manifest.json": {"github-snapshot-manifest-v1"},
    "work/reuse/reuse_index.json": {"round-reuse-index-v1"},
    REVIEW_RUN_TRACE_REL: {REVIEW_RUN_TRACE_SCHEMA},
    REVIEW_ROLE_PLAN_REL: {REVIEW_ROLE_PLAN_SCHEMA},
    COMMON_BRIEFING_REL: {COMMON_BRIEFING_SCHEMA_VERSION},
    EVIDENCE_CAPSULES_REL: {EVIDENCE_CAPSULE_SCHEMA},
    CLAIM_REVIEW_BASIS_REL: {CLAIM_REVIEW_BASIS_SCHEMA},
    REPORT_CALIBRATION_BASIS_REL: {REPORT_CALIBRATION_BASIS_SCHEMA},
    THESES_SIMILARITY_INTAKE_REL: {THESES_SIMILARITY_INTAKE_SCHEMA},
    THESES_SIMILARITY_ASSESSMENT_REL: {THESES_SIMILARITY_ASSESSMENT_SCHEMA},
    THESES_CHECKER_SUMMARY_REL: {THESES_CHECKER_SUMMARY_SCHEMA},
    SUBMISSION_BUNDLE_INVENTORY_REL: {SUBMISSION_BUNDLE_INVENTORY_SCHEMA},
    SUBMISSION_BUNDLE_MATERIALIZATION_REL: {SUBMISSION_BUNDLE_MATERIALIZATION_SCHEMA},
}

JSON_ARTIFACT_REQUIRED_FIELDS: dict[str, dict[str, type | tuple[type, ...]]] = {
    "work/assignment_coverage_agent.json": {"assignment_points": list},
    "work/evidence_requirements.json": {"requirements": list},
    "work/quantitative_claims.json": {"claims": list},
    "work/opponent_report_trace.json": {"is_items": list, "defense_questions": list, "uncertainty_items": list},
    "work/supervisor_report_feedback_history.json": {"evidence_items": list},
    "work/supervisor_report_trace.json": {"report_fields": list, "uncertainty_items": list, "manual_checks": list},
    "work/supervisor_report_confirmation.json": {"ready_for_is": bool},
    "work/current_evidence_snapshot.json": {"items": list},
    "work/code_reproducibility.json": {"classification": str},
    CODE_QUALITY_OMEN_REL: {"tool": str, "status": str, "invocation": dict, "summary": dict},
    SOURCE_ACQUISITION_REL: {
        "source_resolution_policy": str,
        "target_selection_policy": dict,
        "source_sha256": dict,
        "citations": list,
    },
    "work/github-intake/snapshot-manifest.json": {"repositories": list, "pull_requests": list},
    "work/reuse/reuse_index.json": {"current_source_fingerprints": list, "decisions": list},
    REVIEW_RUN_TRACE_REL: {"events": list, "workflow_profile": str, "operator_surface": str},
    REVIEW_ROLE_PLAN_REL: {"role_states": list, "wave_schedule": list, "code_bearing_contract": dict},
    COMMON_BRIEFING_REL: {"common_inputs": list, "context_handoffs": list},
    EVIDENCE_CAPSULES_REL: {"capsules": list},
    CLAIM_REVIEW_BASIS_REL: {"claims": list},
    REPORT_CALIBRATION_BASIS_REL: {
        "profile_sources": list,
        "applied_preferences": list,
        "expected_report_controls": dict,
    },
    SUBMISSION_BUNDLE_INVENTORY_REL: {"source_bundles": list, "candidates": list, "skipped_entries": list},
    SUBMISSION_BUNDLE_MATERIALIZATION_REL: {"materializations": list},
    THESES_SIMILARITY_INTAKE_REL: {
        "report_pdf": dict,
        "extracted_text": dict,
        "current_submission_link": str,
        "source_documents": list,
        "matched_passages": list,
    },
    THESES_SIMILARITY_ASSESSMENT_REL: {"judgments": list},
    THESES_CHECKER_SUMMARY_REL: {"source_artifact": dict, "normostrany": (int, float), "status": str},
}

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

EXPLICIT_WORK_ARTIFACTS = (
    "work/feedback_student_draft.md",
    "work/oponent_podklady_draft.md",
    "work/oponent_posudek_draft.md",
    "work/vedouci_posudek_draft.md",
    "work/code_workspace.md",
    "work/serena_roots.json",
    "work/agent_coverage.json",
    "work/code/.prepare-code-workspace-manifest.json",
    CODE_QUALITY_OMEN_REL,
    "work/code_quality_omen.md",
    "work/github-intake/snapshot-manifest.json",
    "work/reuse/reuse_index.json",
    REVIEW_RUN_TRACE_REL,
    REVIEW_ROLE_PLAN_REL,
    COMMON_BRIEFING_REL,
    EVIDENCE_CAPSULES_REL,
    CLAIM_REVIEW_BASIS_REL,
    REPORT_CALIBRATION_BASIS_REL,
    SUBMISSION_BUNDLE_INVENTORY_REL,
    SUBMISSION_BUNDLE_INVENTORY_SUMMARY_REL,
    SUBMISSION_BUNDLE_MATERIALIZATION_REL,
    "work/figure_media/visual_inventory.jsonl",
    "work/assignment_coverage_agent.json",
    "work/evidence_requirements.json",
    "work/quantitative_claims.json",
    "work/opponent_report_trace.json",
    "work/supervisor_report_feedback_history.json",
    "work/supervisor_report_trace.json",
    "work/supervisor_report_confirmation.json",
    "work/supervisor_report_calibration_use.json",
    "work/supervisor_report_calibration_advisory.json",
    "work/current_evidence_snapshot.json",
    "work/opponent_calibration_use.json",
    "work/opponent_calibration_advisory.json",
    "work/opponent_report_revision_request.json",
    "work/opponent_calibration_refresh_eligibility.json",
    THESES_CHECKER_SUMMARY_REL,
    "work/code_reproducibility.json",
    SOURCE_ACQUISITION_REL,
    "work/media_presence_inventory.jsonl",
    THESES_SIMILARITY_INTAKE_REL,
    THESES_SIMILARITY_ASSESSMENT_REL,
    THESES_SIMILARITY_REVIEW_DRAFT_REL,
)

WORK_ARTIFACT_GLOBS = (
    "work/agent_*.md",
    "work/opponent_packets/*.md",
    "work/supervisor_packets/*.md",
    "work/supervisor_report_packets/*.md",
    "work/review_materiality/*.json",
    "work/review_artifacts/*.json",
    "work/review_deltas/*.json",
    "work/review_deltas/*-before.*",
    "work/reviews/*.json",
    "work/submitted_reports/*.json",
    "work/opponent_report_revision_sources/*",
    "work/opponent_calibration_refresh_sources/*",
    "work/calibration/*.json",
    "work/calibration/*.jsonl",
    "work/calibration/*.md",
    "work/calibration/supervisor_report/*.json",
    "work/calibration/supervisor_report/*.jsonl",
    "work/calibration/supervisor_report/*.md",
    "work/calibration/supervisor_report/historical_case_analyses/*.json",
    "work/calibration/supervisor_report/profile_versions/*.md",
    "work/calibration/historical_case_analyses/*.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".zip", ".tar", ".gz", ".tgz", ".7z"}:
        return "archive"
    if suffix in {".md", ".txt"}:
        return "text"
    if suffix in {".json", ".jsonl", ".yml", ".yaml", ".toml"}:
        return "structured_data"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        return "image"
    return "file"


def round_relative(round_dir: Path, path: Path) -> str:
    return path.relative_to(round_dir).as_posix()


def work_artifact_record(round_dir: Path, path: Path) -> dict[str, str]:
    rel_path = round_relative(round_dir, path)
    record = {
        "path": rel_path,
        "kind": artifact_kind(path),
        "artifact_sha256": sha256_file(path),
    }
    schema_version = None
    if (
        rel_path in KNOWN_JSON_ARTIFACT_SCHEMAS
        or is_opponent_calibration_artifact(rel_path)
        or is_supervisor_report_calibration_artifact(rel_path)
    ):
        schema_version = json_schema_version(path)
    if schema_version:
        record["schema_version"] = schema_version
    record.update(json_producer_fields(path))
    return record


def json_producer_fields(path: Path) -> dict[str, str]:
    if path.suffix.lower() != ".json":
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(loaded, dict):
        return {}
    fields: dict[str, str] = {}
    for source, target in (
        ("producer", "producer"),
        ("producer_role", "producer_role"),
        ("producer_agent", "producer_agent"),
        ("producer_type", "producer_type"),
    ):
        value = loaded.get(source)
        if isinstance(value, str) and value.strip():
            fields[target] = value.strip()
    if fields.get("producer_type") == "human" and "producer_agent" not in fields:
        fields["producer_agent"] = "human_reviewer"
    return fields


def json_schema_version(path: Path) -> str | None:
    try:
        if path.suffix.lower() == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                loaded = json.loads(line)
                if not isinstance(loaded, dict):
                    return None
                schema_version = loaded.get("schema_version")
                return schema_version if isinstance(schema_version, str) else None
            return None
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    schema_version = loaded.get("schema_version")
    return schema_version if isinstance(schema_version, str) else None


def collect_supporting_work_artifacts(round_dir: Path) -> list[dict[str, str]]:
    work = round_dir / "work"
    if not work.is_dir():
        return []

    paths: list[Path] = []
    for rel_path in EXPLICIT_WORK_ARTIFACTS:
        path = round_dir / rel_path
        if path.is_file():
            paths.append(path)
    for pattern in WORK_ARTIFACT_GLOBS:
        paths.extend(path for path in sorted(round_dir.glob(pattern)) if path.is_file())

    github_intake = work / "github-intake"
    if github_intake.is_dir():
        paths.extend(path for path in sorted(github_intake.rglob("*")) if path.is_file())

    seen: set[str] = set()
    records: list[dict[str, str]] = []
    for path in sorted(paths):
        rel_path = round_relative(round_dir, path)
        if rel_path in seen:
            continue
        seen.add(rel_path)
        records.append(work_artifact_record(round_dir, path))
    return records


def validate_supporting_work_artifacts(
    records: Any,
    round_dir: Path,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
) -> list[str]:
    if not isinstance(records, list):
        return []
    errors: list[str] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            continue
        rel_path = record.get("path")
        if not isinstance(rel_path, str):
            continue
        if not is_safe_round_relative_path(rel_path):
            errors.append(f"supporting_work_artifacts item {index}: path must be relative inside the round")
            continue
        path = round_dir / rel_path
        if not path.is_file():
            errors.append(f"supporting_work_artifacts item {index}: referenced file is missing: {rel_path}")
            continue
        recorded_hash = record.get("artifact_sha256")
        if not isinstance(recorded_hash, str) or not SHA256_RE.fullmatch(recorded_hash):
            errors.append(f"supporting_work_artifacts item {index}: artifact_sha256 must be a 64-character hex string")
        elif recorded_hash != sha256_file(path):
            errors.append(f"supporting_work_artifacts item {index}: artifact_sha256 is stale for {rel_path}")
        expected_schemas = KNOWN_JSON_ARTIFACT_SCHEMAS.get(rel_path)
        if expected_schemas:
            validate_json_work_artifact(path, rel_path, expected_schemas, round_dir, case_id, round_id, errors)
        elif is_review_approval_path(rel_path):
            errors.extend(
                validate_review_approval_artifact(
                    round_dir,
                    rel_path,
                    case_id=case_id,
                    round_id=round_id,
                )
            )
        elif is_review_delta_artifact(rel_path):
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{rel_path}: invalid JSON: {exc.msg}")
            else:
                errors.extend(
                    validate_review_delta_record(
                        loaded,
                        round_dir=round_dir,
                        case_id=case_id,
                        round_id=round_id,
                        rel_path=rel_path,
                    )
                )
        elif is_submitted_report_artifact(rel_path):
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{rel_path}: invalid JSON: {exc.msg}")
            else:
                errors.extend(
                    validate_submitted_report_record(
                        loaded,
                        round_dir=round_dir,
                        case_id=case_id,
                        round_id=round_id,
                        rel_path=rel_path,
                    )
                )
        elif is_submitted_report_delta_artifact(rel_path):
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{rel_path}: invalid JSON: {exc.msg}")
            else:
                errors.extend(
                    validate_opponent_submitted_report_deltas(
                        loaded,
                        round_dir=round_dir,
                        case_id=case_id,
                        round_id=round_id,
                        rel_path=rel_path,
                    )
                )
        elif is_opponent_calibration_artifact(rel_path):
            errors.extend(
                validate_opponent_calibration_artifact(
                    round_dir,
                    rel_path,
                    case_id=case_id,
                    round_id=round_id,
                )
            )
        elif is_supervisor_report_calibration_artifact(rel_path):
            errors.extend(
                validate_supervisor_report_calibration_artifact(
                    round_dir,
                    rel_path,
                    case_id=case_id,
                    round_id=round_id,
                )
            )
        elif is_report_calibration_basis_path(rel_path):
            errors.extend(
                validate_report_calibration_artifact(
                    round_dir,
                    rel_path,
                    case_id=case_id,
                    round_id=round_id,
                )
            )
    return errors


def validate_json_work_artifact(
    path: Path,
    rel_path: str,
    expected_schemas: set[str],
    round_dir: Path,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{rel_path}: invalid JSON: {exc.msg}")
        return
    if not isinstance(loaded, dict):
        errors.append(f"{rel_path}: JSON work artifact must be an object")
        return
    schema_version = loaded.get("schema_version")
    if schema_version not in expected_schemas:
        expected = ", ".join(sorted(expected_schemas))
        errors.append(f"{rel_path}: schema_version must be {expected}")
    if case_id is not None and loaded.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and loaded.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    for field in ("generated_at",):
        if not isinstance(loaded.get(field), str) or not loaded[field]:
            errors.append(f"{rel_path}: missing {field}")
    for field, expected_type in JSON_ARTIFACT_REQUIRED_FIELDS.get(rel_path, {}).items():
        if not isinstance(loaded.get(field), expected_type):
            errors.append(f"{rel_path}: {field} must be {_type_label(expected_type)}")
    if rel_path in STRUCTURED_EVIDENCE_SCHEMAS:
        errors.extend(
            validate_structured_evidence_payload(
                loaded,
                rel_path,
                round_dir=round_dir,
                case_id=case_id,
                round_id=round_id,
            )
        )
    elif rel_path == COMMON_BRIEFING_REL:
        errors.extend(
            validate_common_briefing_payload(
                loaded,
                rel_path,
                round_dir=round_dir,
                case_id=case_id,
                round_id=round_id,
            )
        )
    elif rel_path == EVIDENCE_CAPSULES_REL:
        errors.extend(
            validate_evidence_capsules_payload(
                loaded,
                rel_path,
                round_dir=round_dir,
                case_id=case_id,
                round_id=round_id,
            )
        )
    elif rel_path == CLAIM_REVIEW_BASIS_REL:
        errors.extend(
            validate_claim_review_basis_payload(
                loaded,
                rel_path,
                round_dir=round_dir,
                case_id=case_id,
                round_id=round_id,
            )
        )
    elif rel_path == REPORT_CALIBRATION_BASIS_REL:
        errors.extend(
            validate_report_calibration_payload(
                loaded,
                rel_path,
                round_dir=round_dir,
                case_id=case_id,
                round_id=round_id,
            )
        )
    elif rel_path == REVIEW_RUN_TRACE_REL:
        errors.extend(validate_review_run_trace_payload(loaded))
    elif rel_path == REVIEW_ROLE_PLAN_REL:
        errors.extend(validate_review_role_plan_payload(loaded, round_dir=round_dir))
    elif rel_path == CODE_QUALITY_OMEN_REL:
        errors.extend(
            validate_code_quality_omen_payload(
                loaded,
                rel_path,
                round_dir=round_dir,
                case_id=case_id,
                round_id=round_id,
            )
        )
    elif rel_path == SOURCE_ACQUISITION_REL:
        errors.extend(
            validate_source_acquisition_payload(
                loaded,
                rel_path,
                round_dir=round_dir,
                case_id=case_id,
                round_id=round_id,
            )
        )
    elif rel_path == THESES_CHECKER_SUMMARY_REL:
        errors.extend(
            validate_theses_checker_summary_payload(
                loaded,
                rel_path,
                round_dir=round_dir,
                case_id=case_id,
                round_id=round_id,
            )
        )
    elif rel_path == SUBMISSION_BUNDLE_MATERIALIZATION_REL:
        errors.extend(
            validate_submission_bundle_materialization_payload(
                loaded,
                rel_path,
                round_dir=round_dir,
                case_id=case_id,
                round_id=round_id,
            )
        )


def _type_label(expected_type: type | tuple[type, ...]) -> str:
    if isinstance(expected_type, tuple):
        return " or ".join(item.__name__ for item in expected_type)
    return expected_type.__name__
