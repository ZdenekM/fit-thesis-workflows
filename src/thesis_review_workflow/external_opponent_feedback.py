"""Structural contracts for external opponent-report postmortem learning."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.review_approvals import validate_review_approval_payload

EXTERNAL_OPPONENT_REPORT_INTAKE_SCHEMA = "external-opponent-report-intake-v1"
EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_SCHEMA = "external-opponent-feedback-findings-v1"
SUPERVISOR_LEARNING_CANDIDATES_SCHEMA = "supervisor-learning-candidates-v1"

EXTERNAL_OPPONENT_REPORT_INTAKE_REL = "work/external_opponent_report_intake.json"
EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL = "work/external_opponent_feedback_findings.json"
SUPERVISOR_LEARNING_CANDIDATES_REL = "work/supervisor_learning_candidates.json"
EXTERNAL_OPPONENT_FEEDBACK_ANALYSIS_REL = "outputs/external_opponent_feedback_analysis.md"
EXTERNAL_OPPONENT_FEEDBACK_REVIEW_REL = "work/reviews/external_opponent_feedback_review.json"
EXTERNAL_OPPONENT_REPORT_SOURCE_PREFIX = "inputs/external_opponent_report/"
EXTERNAL_OPPONENT_REPORT_INTAKE_NOTE_REL = "notes/external-opponent-report-intake.md"
EXTERNAL_OPPONENT_FEEDBACK_WORKFLOW_PROFILE = "external_opponent_feedback_learning"
EXTERNAL_OPPONENT_FEEDBACK_REVIEWER_ROLE = "thesis_evidence_calibrator"
EXTERNAL_OPPONENT_FEEDBACK_REQUIRED_CHECK = "check-external-opponent-feedback"

EXTERNAL_OPPONENT_FEEDBACK_WORK_RELS = (
    EXTERNAL_OPPONENT_REPORT_INTAKE_REL,
    EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL,
    SUPERVISOR_LEARNING_CANDIDATES_REL,
)
EXTERNAL_OPPONENT_FEEDBACK_CHECK_RELS = (
    EXTERNAL_OPPONENT_REPORT_INTAKE_REL,
    EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL,
    SUPERVISOR_LEARNING_CANDIDATES_REL,
    EXTERNAL_OPPONENT_FEEDBACK_ANALYSIS_REL,
    EXTERNAL_OPPONENT_FEEDBACK_REVIEW_REL,
)
EXTERNAL_OPPONENT_FEEDBACK_REVIEW_BASIS_RELS = (
    SUPERVISOR_LEARNING_CANDIDATES_REL,
    EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL,
)

SOURCE_STATUSES = frozenset(
    {
        "draft_shared_for_consultation",
        "official_private_copy",
        "official_public",
        "unknown_or_restricted",
    }
)
WORKFLOW_LEARNING_PERMISSIONS = frozenset(
    {
        "allowed",
        "current_case_only",
        "archival_only",
        "unknown_or_restricted",
    }
)
FINDINGS_ALLOWED_PERMISSIONS = frozenset({"allowed", "current_case_only"})
GENERAL_PROMOTION_ALLOWED_PERMISSIONS = frozenset({"allowed"})
QUOTE_PERMISSIONS = frozenset(
    {
        "none",
        "short_private_excerpt_only",
        "public_source_rules_apply",
    }
)
INTENDED_USE_MODES = frozenset(
    {
        "current_case_followup",
        "supervisor_feedback_pipeline_learning",
        "supervisor_report_calibration_learning",
        "general_workflow_rule_candidate",
        "archival_only",
    }
)
SOURCE_REF_KINDS = frozenset({"report_pdf", "report_text", "public_url", "source_note"})
FINDING_CLASSIFICATIONS = frozenset(
    {
        "already_caught",
        "partially_caught",
        "missed_by_feedback",
        "not_available_at_feedback_time",
        "disputed_or_unverified",
        "case_specific_only",
        "not_actionable",
    }
)
AVAILABLE_AT_FEEDBACK_TIME_STATUSES = frozenset({"available", "partially_available", "not_available", "unknown"})
CONFIDENCE_VALUES = frozenset({"low", "medium", "high"})
PROMOTION_ROUTES = frozenset(
    {
        "case_only",
        "current_student_followup",
        "supervisor_profile",
        "workflow_docs_or_skill",
        "methodology_pipeline",
        "specialized_review_workflow",
        "todo_or_follow_up_plan",
        "discard",
    }
)
CASE_LOCAL_PROMOTION_ROUTES = frozenset({"case_only", "current_student_followup", "discard"})
CANDIDATE_STATUSES = frozenset({"proposed", "approved_for_promotion", "promoted", "deferred", "discarded"})
PROMOTION_TARGET_OWNERS = frozenset(
    {
        "case_notes",
        "current_student_followup",
        "supervisor_profile",
        "thesis-supervisor-feedback",
        "thesis-supervisor-report",
        "opponent_methodology_pipeline_plan",
        "thesis-code-consistency",
        "thesis-code-quality-review",
        "thesis-quantitative-claims-review",
        "thesis-literature-citation-review",
        "thesis-figure-media-review",
        "thesis-typography-formal-review",
        "thesis-theses-similarity-review",
        "thesis-github-code-intake",
        "TODO",
        "none",
    }
)
SPECIALIZED_PROMOTION_OWNERS = frozenset(
    {
        "thesis-code-consistency",
        "thesis-code-quality-review",
        "thesis-quantitative-claims-review",
        "thesis-literature-citation-review",
        "thesis-figure-media-review",
        "thesis-typography-formal-review",
        "thesis-theses-similarity-review",
        "thesis-github-code-intake",
    }
)
FORBIDDEN_RAW_TEXT_KEYS = frozenset(
    {
        "opponent_text",
        "opponent_excerpt",
        "opponent_quote",
        "quote",
        "quoted_text",
        "report_excerpt",
        "raw_opponent_text",
        "raw_report_text",
    }
)

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,80}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ABSOLUTE_PATH_RE = re.compile(r"(?<!\w)/(?:home|Users|tmp|var|workspace|mnt)/[^\s)\"']*")
WINDOWS_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s)\"']*")
PLACEHOLDER_RE = re.compile(r"^(?:TODO|TBD|FIXME|PLACEHOLDER|<[^>]+>|\\.\\.\\.)$", re.IGNORECASE)


def external_opponent_feedback_evidence_present(round_dir: Path) -> bool:
    source_root = round_dir / EXTERNAL_OPPONENT_REPORT_SOURCE_PREFIX
    if source_root.is_dir() and any(path.is_file() for path in source_root.rglob("*")):
        return True
    return any((round_dir / rel_path).exists() for rel_path in EXTERNAL_OPPONENT_FEEDBACK_CHECK_RELS)


def external_opponent_feedback_check_targets(round_dir: Path) -> list[str]:
    return [rel_path for rel_path in EXTERNAL_OPPONENT_FEEDBACK_CHECK_RELS if (round_dir / rel_path).is_file()]


def validate_external_opponent_feedback_round(
    round_dir: Path,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    require_analysis: bool = False,
) -> list[str]:
    errors: list[str] = []
    if not external_opponent_feedback_evidence_present(round_dir) and not require_analysis:
        return errors

    intake_path = round_dir / EXTERNAL_OPPONENT_REPORT_INTAKE_REL
    findings_path = round_dir / EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL
    candidates_path = round_dir / SUPERVISOR_LEARNING_CANDIDATES_REL
    analysis_path = round_dir / EXTERNAL_OPPONENT_FEEDBACK_ANALYSIS_REL
    review_path = round_dir / EXTERNAL_OPPONENT_FEEDBACK_REVIEW_REL

    if _source_root_has_files(round_dir) and not intake_path.is_file():
        errors.append(
            f"missing required external opponent-report intake artifact: {EXTERNAL_OPPONENT_REPORT_INTAKE_REL}"
        )
    if require_analysis:
        for rel_path in (
            EXTERNAL_OPPONENT_REPORT_INTAKE_REL,
            EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL,
            SUPERVISOR_LEARNING_CANDIDATES_REL,
            EXTERNAL_OPPONENT_FEEDBACK_ANALYSIS_REL,
            EXTERNAL_OPPONENT_FEEDBACK_REVIEW_REL,
        ):
            if not (round_dir / rel_path).is_file():
                errors.append(f"missing required external opponent-feedback analysis artifact: {rel_path}")

    for rel_path in EXTERNAL_OPPONENT_FEEDBACK_WORK_RELS:
        path = round_dir / rel_path
        if not path.is_file():
            continue
        loaded = _load_json_object(path, rel_path, errors)
        if loaded is not None:
            errors.extend(
                validate_external_opponent_feedback_payload(
                    loaded,
                    rel_path,
                    round_dir=round_dir,
                    case_id=case_id,
                    round_id=round_id,
                )
            )

    if findings_path.is_file() and not intake_path.is_file():
        errors.append(f"{EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL}: missing intake artifact")
    if candidates_path.is_file() and not findings_path.is_file():
        errors.append(f"{SUPERVISOR_LEARNING_CANDIDATES_REL}: missing findings artifact")

    if analysis_path.is_file():
        _validate_markdown_artifact(round_dir, EXTERNAL_OPPONENT_FEEDBACK_ANALYSIS_REL, errors)
        if not findings_path.is_file():
            errors.append(f"{EXTERNAL_OPPONENT_FEEDBACK_ANALYSIS_REL}: findings artifact is required")
        if not candidates_path.is_file():
            errors.append(f"{EXTERNAL_OPPONENT_FEEDBACK_ANALYSIS_REL}: learning candidates artifact is required")
        if not review_path.is_file():
            errors.append(f"{EXTERNAL_OPPONENT_FEEDBACK_ANALYSIS_REL}: review approval is required")
    if review_path.is_file():
        errors.extend(_validate_external_review_approval(round_dir, case_id, round_id))
    return errors


def validate_external_opponent_feedback_payload(
    loaded: dict[str, Any],
    rel_path: str,
    *,
    round_dir: Path,
    case_id: str | None = None,
    round_id: str | None = None,
) -> list[str]:
    errors: list[str] = []
    _reject_forbidden_raw_text_keys(loaded, rel_path, errors)
    if rel_path == EXTERNAL_OPPONENT_REPORT_INTAKE_REL:
        _validate_intake_payload(loaded, rel_path, round_dir, case_id, round_id, errors)
    elif rel_path == EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL:
        _validate_findings_payload(loaded, rel_path, round_dir, case_id, round_id, errors)
    elif rel_path == SUPERVISOR_LEARNING_CANDIDATES_REL:
        _validate_learning_candidates_payload(loaded, rel_path, round_dir, case_id, round_id, errors)
    else:
        errors.append(f"{rel_path}: unsupported external opponent-feedback artifact")
    return errors


def _source_root_has_files(round_dir: Path) -> bool:
    source_root = round_dir / EXTERNAL_OPPONENT_REPORT_SOURCE_PREFIX
    return source_root.is_dir() and any(path.is_file() for path in source_root.rglob("*"))


def _validate_intake_payload(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    _validate_common_fields(
        loaded,
        rel_path,
        EXTERNAL_OPPONENT_REPORT_INTAKE_SCHEMA,
        case_id,
        round_id,
        errors,
    )
    _require_enum(loaded.get("source_status"), SOURCE_STATUSES, f"{rel_path}: source_status", errors)
    permission = loaded.get("workflow_learning_permission")
    _require_enum(permission, WORKFLOW_LEARNING_PERMISSIONS, f"{rel_path}: workflow_learning_permission", errors)
    _require_enum(loaded.get("quote_permission"), QUOTE_PERMISSIONS, f"{rel_path}: quote_permission", errors)
    if not isinstance(loaded.get("agent_report_reading_authorized"), bool):
        errors.append(f"{rel_path}: agent_report_reading_authorized must be boolean")

    intended_uses = _require_string_list(loaded, "intended_uses", rel_path, errors)
    for index, value in enumerate(intended_uses, start=1):
        _require_enum(value, INTENDED_USE_MODES, f"{rel_path}: intended_uses item {index}", errors)
    if "archival_only" in intended_uses and len(set(intended_uses)) > 1:
        errors.append(f"{rel_path}: archival_only intended use must not be combined with other intended uses")
    if permission == "archival_only" and "archival_only" not in intended_uses:
        errors.append(f"{rel_path}: archival permission requires archival_only intended use")

    source_refs = loaded.get("source_refs")
    if not isinstance(source_refs, list):
        errors.append(f"{rel_path}: source_refs must be a list")
    else:
        ref_ids: set[str] = set()
        for index, item in enumerate(source_refs, start=1):
            prefix = f"{rel_path}: source_refs item {index}"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            ref_id = _require_identifier(item.get("ref_id"), f"{prefix}: ref_id", errors)
            if ref_id:
                if ref_id in ref_ids:
                    errors.append(f"{prefix}: duplicate ref_id {ref_id}")
                ref_ids.add(ref_id)
            _require_enum(item.get("kind"), SOURCE_REF_KINDS, f"{prefix}: kind", errors)
            path = item.get("path")
            if not isinstance(path, str):
                errors.append(f"{prefix}: path must be string")
            elif not path.startswith(EXTERNAL_OPPONENT_REPORT_SOURCE_PREFIX):
                errors.append(f"{prefix}: path must stay under {EXTERNAL_OPPONENT_REPORT_SOURCE_PREFIX}")
            else:
                _validate_hash_bound_path(round_dir, path, item.get("sha256"), prefix, errors)

    intake_note_ref = loaded.get("intake_note_ref")
    if intake_note_ref is not None:
        _validate_case_evidence_ref(
            intake_note_ref,
            f"{rel_path}: intake_note_ref",
            round_dir,
            errors,
            allowed_exact={EXTERNAL_OPPONENT_REPORT_INTAKE_NOTE_REL},
        )
    _validate_case_evidence_refs(
        loaded.get("comparison_basis_refs"), f"{rel_path}: comparison_basis_refs", round_dir, errors
    )
    _validate_case_evidence_refs(
        loaded.get("operator_context_refs"), f"{rel_path}: operator_context_refs", round_dir, errors
    )


def _validate_findings_payload(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    _validate_common_fields(
        loaded,
        rel_path,
        EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_SCHEMA,
        case_id,
        round_id,
        errors,
    )
    _validate_hash_ref_to_expected_path(
        loaded.get("intake_ref"),
        EXTERNAL_OPPONENT_REPORT_INTAKE_REL,
        f"{rel_path}: intake_ref",
        round_dir,
        errors,
    )
    intake = _load_peer_payload(round_dir, EXTERNAL_OPPONENT_REPORT_INTAKE_REL, errors)
    source_ref_ids: set[str] = set()
    if intake is not None:
        if intake.get("source_status") == "unknown_or_restricted":
            errors.append(f"{rel_path}: findings require a usable source_status in intake")
        permission = intake.get("workflow_learning_permission")
        if permission not in FINDINGS_ALLOWED_PERMISSIONS:
            errors.append(
                f"{rel_path}: findings require workflow_learning_permission allowed or current_case_only in intake"
            )
        if intake.get("agent_report_reading_authorized") is not True:
            errors.append(f"{rel_path}: intake must record current-request agent report-reading authorization")
        source_ref_ids = _source_ref_ids(intake)

    findings = loaded.get("findings")
    if not isinstance(findings, list):
        errors.append(f"{rel_path}: findings must be a list")
        return
    finding_ids: set[str] = set()
    for index, item in enumerate(findings, start=1):
        prefix = f"{rel_path}: findings item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        finding_id = _require_identifier(item.get("id"), f"{prefix}: id", errors)
        if finding_id:
            if finding_id in finding_ids:
                errors.append(f"{prefix}: duplicate id {finding_id}")
            finding_ids.add(finding_id)
        _require_enum(item.get("classification"), FINDING_CLASSIFICATIONS, f"{prefix}: classification", errors)
        _require_non_placeholder_string(item.get("summary"), f"{prefix}: summary", errors)
        _require_enum(
            item.get("available_at_feedback_time"),
            AVAILABLE_AT_FEEDBACK_TIME_STATUSES,
            f"{prefix}: available_at_feedback_time",
            errors,
        )
        _require_enum(item.get("confidence"), CONFIDENCE_VALUES, f"{prefix}: confidence", errors)
        promotion_route = item.get("promotion_route")
        if promotion_route is not None:
            _require_enum(promotion_route, PROMOTION_ROUTES, f"{prefix}: promotion_route", errors)
        _validate_report_locator_refs(
            item.get("opponent_report_refs"),
            f"{prefix}: opponent_report_refs",
            source_ref_ids,
            errors,
        )
        _validate_case_evidence_refs(item.get("comparison_refs"), f"{prefix}: comparison_refs", round_dir, errors)
        _validate_string_list(item.get("limitations"), f"{prefix}: limitations", errors, required=False)


def _validate_learning_candidates_payload(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    _validate_common_fields(
        loaded,
        rel_path,
        SUPERVISOR_LEARNING_CANDIDATES_SCHEMA,
        case_id,
        round_id,
        errors,
    )
    _validate_hash_ref_to_expected_path(
        loaded.get("findings_ref"),
        EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL,
        f"{rel_path}: findings_ref",
        round_dir,
        errors,
    )
    findings = _load_peer_payload(round_dir, EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL, errors)
    intake = _load_peer_payload(round_dir, EXTERNAL_OPPONENT_REPORT_INTAKE_REL, errors)
    finding_ids = _finding_ids(findings) if findings is not None else set()
    permission = intake.get("workflow_learning_permission") if isinstance(intake, dict) else None

    candidates = loaded.get("candidates")
    if not isinstance(candidates, list):
        errors.append(f"{rel_path}: candidates must be a list")
        return
    candidate_ids: set[str] = set()
    for index, item in enumerate(candidates, start=1):
        prefix = f"{rel_path}: candidates item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        candidate_id = _require_identifier(item.get("id"), f"{prefix}: id", errors)
        if candidate_id:
            if candidate_id in candidate_ids:
                errors.append(f"{prefix}: duplicate id {candidate_id}")
            candidate_ids.add(candidate_id)
        source_finding_ids = _require_string_list(item, "source_finding_ids", prefix, errors)
        if not source_finding_ids:
            errors.append(f"{prefix}: source_finding_ids must not be empty")
        for source_index, source_id in enumerate(source_finding_ids, start=1):
            if source_id not in finding_ids:
                errors.append(
                    f"{prefix}: source_finding_ids item {source_index} references unknown finding {source_id}"
                )
        route = item.get("promotion_route")
        _require_enum(route, PROMOTION_ROUTES, f"{prefix}: promotion_route", errors)
        _validate_permission_allows_route(permission, route, prefix, errors)
        owner = item.get("target_owner")
        _require_enum(owner, PROMOTION_TARGET_OWNERS, f"{prefix}: target_owner", errors)
        if route == "specialized_review_workflow" and owner not in SPECIALIZED_PROMOTION_OWNERS:
            errors.append(f"{prefix}: specialized_review_workflow requires a specialized target_owner")
        if route == "methodology_pipeline" and owner != "opponent_methodology_pipeline_plan":
            errors.append(f"{prefix}: methodology_pipeline requires target_owner opponent_methodology_pipeline_plan")
        _require_enum(item.get("status"), CANDIDATE_STATUSES, f"{prefix}: status", errors)
        _require_non_placeholder_string(item.get("summary"), f"{prefix}: summary", errors)
        if route not in CASE_LOCAL_PROMOTION_ROUTES:
            _require_non_placeholder_string(item.get("generalized_lesson"), f"{prefix}: generalized_lesson", errors)
        _validate_repo_target_refs(item.get("target_refs"), f"{prefix}: target_refs", errors)
        _validate_privacy_review(item.get("privacy_review"), prefix, route, errors)
        _validate_string_list(item.get("limitations"), f"{prefix}: limitations", errors, required=False)


def _validate_common_fields(
    loaded: dict[str, Any],
    rel_path: str,
    expected_schema: str,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    if loaded.get("schema_version") != expected_schema:
        errors.append(f"{rel_path}: schema_version must be {expected_schema}")
    if case_id is not None and loaded.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and loaded.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    for field in ("generated_at", "producer_role"):
        _require_non_placeholder_string(loaded.get(field), f"{rel_path}: {field}", errors)
    producer_type = loaded.get("producer_type")
    if producer_type not in {"agent", "human"}:
        errors.append(f"{rel_path}: producer_type must be agent or human")
    producer_agent = loaded.get("producer_agent")
    if producer_type == "agent":
        _require_non_placeholder_string(producer_agent, f"{rel_path}: producer_agent", errors)
        _require_non_placeholder_string(loaded.get("authorization_note"), f"{rel_path}: authorization_note", errors)
    elif producer_agent is not None and not isinstance(producer_agent, str):
        errors.append(f"{rel_path}: producer_agent must be string or null")
    if producer_type == "human":
        _require_non_placeholder_string(loaded.get("human_reviewer_note"), f"{rel_path}: human_reviewer_note", errors)
    _validate_string_list(loaded.get("limitations"), f"{rel_path}: limitations", errors, required=True)


def _source_ref_ids(intake: dict[str, Any]) -> set[str]:
    source_refs = intake.get("source_refs")
    if not isinstance(source_refs, list):
        return set()
    return {item["ref_id"] for item in source_refs if isinstance(item, dict) and isinstance(item.get("ref_id"), str)}


def _finding_ids(findings: dict[str, Any]) -> set[str]:
    items = findings.get("findings")
    if not isinstance(items, list):
        return set()
    return {item["id"] for item in items if isinstance(item, dict) and isinstance(item.get("id"), str)}


def _validate_permission_allows_route(permission: object, route: object, prefix: str, errors: list[str]) -> None:
    if route not in PROMOTION_ROUTES:
        return
    if permission not in FINDINGS_ALLOWED_PERMISSIONS:
        errors.append(f"{prefix}: promotion requires intake permission allowed or current_case_only")
        return
    if permission not in GENERAL_PROMOTION_ALLOWED_PERMISSIONS and route not in CASE_LOCAL_PROMOTION_ROUTES:
        errors.append(f"{prefix}: non-case-local promotion requires workflow_learning_permission allowed")


def _validate_report_locator_refs(value: Any, prefix: str, source_ref_ids: set[str], errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{prefix} must be a list")
        return
    for index, item in enumerate(value, start=1):
        item_prefix = f"{prefix} item {index}"
        if not isinstance(item, dict):
            errors.append(f"{item_prefix} must be an object")
            continue
        source_ref_id = item.get("source_ref_id")
        if not isinstance(source_ref_id, str) or not source_ref_id.strip():
            errors.append(f"{item_prefix}: source_ref_id must be string")
        elif source_ref_ids and source_ref_id not in source_ref_ids:
            errors.append(f"{item_prefix}: source_ref_id references unknown source ref {source_ref_id}")
        _require_non_placeholder_string(item.get("locator"), f"{item_prefix}: locator", errors)
        if "path" in item:
            errors.append(f"{item_prefix}: use source_ref_id instead of repeating source path")


def _validate_case_evidence_refs(value: Any, prefix: str, round_dir: Path, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        errors.append(f"{prefix} must be a list")
        return
    for index, item in enumerate(value, start=1):
        _validate_case_evidence_ref(item, f"{prefix} item {index}", round_dir, errors)


def _validate_case_evidence_ref(
    value: Any,
    prefix: str,
    round_dir: Path,
    errors: list[str],
    *,
    allowed_exact: set[str] | None = None,
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be an object")
        return
    path = value.get("path")
    if not isinstance(path, str):
        errors.append(f"{prefix}: path must be string")
        return
    if allowed_exact is not None and path not in allowed_exact:
        choices = ", ".join(sorted(allowed_exact))
        errors.append(f"{prefix}: path must be one of: {choices}")
        return
    if not is_safe_round_relative_path(path):
        errors.append(f"{prefix}: path must be relative inside the round")
        return
    if path.startswith(EXTERNAL_OPPONENT_REPORT_SOURCE_PREFIX):
        errors.append(f"{prefix}: external report sources must be referenced through source_refs")
        return
    if "sha256" in value:
        _validate_hash_bound_path(round_dir, path, value.get("sha256"), prefix, errors)
    elif not (round_dir / path).is_file():
        errors.append(f"{prefix}: referenced file is missing: {path}")
    locator = value.get("locator")
    if locator is not None:
        _require_non_placeholder_string(locator, f"{prefix}: locator", errors)


def _validate_hash_ref_to_expected_path(
    value: Any,
    expected_path: str,
    prefix: str,
    round_dir: Path,
    errors: list[str],
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be an object")
        return
    path = value.get("path")
    if path != expected_path:
        errors.append(f"{prefix}: path must be {expected_path}")
        return
    _validate_hash_bound_path(round_dir, expected_path, value.get("sha256"), prefix, errors)


def _validate_hash_bound_path(
    round_dir: Path,
    rel_path: str,
    recorded_hash: Any,
    prefix: str,
    errors: list[str],
) -> None:
    if not is_safe_round_relative_path(rel_path):
        errors.append(f"{prefix}: path must be relative inside the round")
        return
    path = round_dir / rel_path
    if not path.is_file():
        errors.append(f"{prefix}: referenced file is missing: {rel_path}")
        return
    if not isinstance(recorded_hash, str) or not SHA256_RE.fullmatch(recorded_hash):
        errors.append(f"{prefix}: sha256 must be a 64-character hex string")
        return
    if sha256_file(path) != recorded_hash:
        errors.append(f"{prefix}: sha256 is stale for {rel_path}")


def _validate_repo_target_refs(value: Any, prefix: str, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        errors.append(f"{prefix} must be a list")
        return
    for index, item in enumerate(value, start=1):
        item_prefix = f"{prefix} item {index}"
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{item_prefix} must be a non-empty string")
            continue
        if not is_safe_round_relative_path(item):
            errors.append(f"{item_prefix} must be a safe relative path")
        if item.startswith("cases/"):
            errors.append(f"{item_prefix} must not point into cases/")
        if item.startswith(EXTERNAL_OPPONENT_REPORT_SOURCE_PREFIX):
            errors.append(f"{item_prefix} must not point to external opponent-report source files")


def _validate_privacy_review(value: Any, prefix: str, route: object, errors: list[str]) -> None:
    if value is None:
        if route not in CASE_LOCAL_PROMOTION_ROUTES:
            errors.append(f"{prefix}: privacy_review is required for non-case-local promotion")
        return
    if not isinstance(value, dict):
        errors.append(f"{prefix}: privacy_review must be an object")
        return
    contains_private = value.get("contains_private_case_details")
    if not isinstance(contains_private, bool):
        errors.append(f"{prefix}: privacy_review.contains_private_case_details must be boolean")
    elif contains_private and route not in CASE_LOCAL_PROMOTION_ROUTES:
        errors.append(f"{prefix}: non-case-local promotion must not contain private case details")
    _validate_string_list(value.get("checked_for"), f"{prefix}: privacy_review.checked_for", errors, required=True)


def _validate_markdown_artifact(round_dir: Path, rel_path: str, errors: list[str]) -> None:
    path = round_dir / rel_path
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        errors.append(f"{rel_path}: output must not be empty")
    if ABSOLUTE_PATH_RE.search(text) or WINDOWS_PATH_RE.search(text):
        errors.append(f"{rel_path}: output contains an absolute filesystem path")
    if "cases/" in text:
        errors.append(f"{rel_path}: output contains an exact case workspace path")


def _validate_external_review_approval(round_dir: Path, case_id: str | None, round_id: str | None) -> list[str]:
    errors: list[str] = []
    payload = _load_json_object(
        round_dir / EXTERNAL_OPPONENT_FEEDBACK_REVIEW_REL, EXTERNAL_OPPONENT_FEEDBACK_REVIEW_REL, errors
    )
    if payload is None:
        return errors
    errors.extend(
        validate_review_approval_payload(
            payload,
            EXTERNAL_OPPONENT_FEEDBACK_REVIEW_REL,
            round_dir,
            case_id=case_id,
            round_id=round_id,
            reviewed_artifact_path=EXTERNAL_OPPONENT_FEEDBACK_ANALYSIS_REL,
        )
    )
    if payload.get("workflow_profile") != EXTERNAL_OPPONENT_FEEDBACK_WORKFLOW_PROFILE:
        errors.append(
            f"{EXTERNAL_OPPONENT_FEEDBACK_REVIEW_REL}: workflow_profile must be "
            f"{EXTERNAL_OPPONENT_FEEDBACK_WORKFLOW_PROFILE}"
        )
    if payload.get("reviewer_role") != EXTERNAL_OPPONENT_FEEDBACK_REVIEWER_ROLE:
        errors.append(
            f"{EXTERNAL_OPPONENT_FEEDBACK_REVIEW_REL}: reviewer_role must be "
            f"{EXTERNAL_OPPONENT_FEEDBACK_REVIEWER_ROLE}"
        )
    review_basis = payload.get("review_basis_path")
    if review_basis not in EXTERNAL_OPPONENT_FEEDBACK_REVIEW_BASIS_RELS:
        choices = ", ".join(EXTERNAL_OPPONENT_FEEDBACK_REVIEW_BASIS_RELS)
        errors.append(f"{EXTERNAL_OPPONENT_FEEDBACK_REVIEW_REL}: review_basis_path must be one of: {choices}")
    checks_observed = payload.get("checks_observed")
    if isinstance(checks_observed, list) and EXTERNAL_OPPONENT_FEEDBACK_REQUIRED_CHECK not in checks_observed:
        errors.append(
            f"{EXTERNAL_OPPONENT_FEEDBACK_REVIEW_REL}: missing required observed check: "
            f"{EXTERNAL_OPPONENT_FEEDBACK_REQUIRED_CHECK}"
        )
    return errors


def _load_peer_payload(round_dir: Path, rel_path: str, errors: list[str]) -> dict[str, Any] | None:
    path = round_dir / rel_path
    if not path.is_file():
        errors.append(f"{rel_path}: referenced peer artifact is missing")
        return None
    return _load_json_object(path, rel_path, errors)


def _load_json_object(path: Path, rel_path: str, errors: list[str]) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{rel_path}: invalid JSON: {exc.msg}")
        return None
    if not isinstance(loaded, dict):
        errors.append(f"{rel_path}: JSON artifact must be an object")
        return None
    return loaded


def _require_identifier(value: object, label: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        errors.append(f"{label} must be a lowercase identifier")
        return ""
    return value


def _require_enum(value: object, allowed: frozenset[str], label: str, errors: list[str]) -> None:
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        errors.append(f"{label} must be one of: {choices}")


def _require_non_placeholder_string(value: object, label: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return ""
    if PLACEHOLDER_RE.fullmatch(value.strip()):
        errors.append(f"{label} must not be a placeholder")
        return ""
    if "\n" in value:
        errors.append(f"{label} must be a single-line string")
        return ""
    return value


def _require_string_list(loaded: dict[str, Any], field: str, prefix: str, errors: list[str]) -> list[str]:
    value = loaded.get(field)
    item_prefix = f"{prefix}: {field}"
    if not isinstance(value, list):
        errors.append(f"{item_prefix} must be a list")
        return []
    strings: list[str] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{item_prefix} item {index} must be a non-empty string")
            continue
        strings.append(item)
    return strings


def _validate_string_list(value: Any, label: str, errors: list[str], *, required: bool) -> None:
    if value is None and not required:
        return
    if not isinstance(value, list):
        errors.append(f"{label} must be a list")
        return
    for index, item in enumerate(value, start=1):
        if not isinstance(item, str):
            errors.append(f"{label} item {index} must be a string")


def _reject_forbidden_raw_text_keys(value: Any, prefix: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key.lower() in FORBIDDEN_RAW_TEXT_KEYS:
                errors.append(f"{prefix}: raw opponent-report text field is not allowed: {key}")
            _reject_forbidden_raw_text_keys(item, prefix, errors)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden_raw_text_keys(item, prefix, errors)
