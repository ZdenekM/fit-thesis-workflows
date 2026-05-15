"""Structured post-review delta records for reviewed workflow artifacts."""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.review_profiles import get_workflow_review_profile

REVIEW_DELTA_SCHEMA = "review-delta-v1"
REVIEW_DELTA_DIR_REL = "work/review_deltas"
DELTA_TYPES = {
    "style_only",
    "operator_preference",
    "evidence_challenge",
    "material_claim_delta",
    "general_workflow_lesson",
}
MATERIAL_DELTA_TYPES = {"evidence_challenge", "material_claim_delta", "general_workflow_lesson"}
NON_MATERIAL_DELTA_TYPES = {"style_only", "operator_preference"}
TYPED_EXCEPTION_TYPES = {"approval_unavailable", "operator_explicit_exception", "style_only_no_visible_change"}
MAX_DIFF_LINES = 160
PROMOTION_TARGET_PREFIXES = (
    ".agents/skills/",
    "docs/",
    "plans/",
    "private-reviewer-profile:",
)
PROMOTION_TARGETS = {"AGENTS.md", "README.md", "TODO.md"}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "delta"


def review_delta_record_rel(generated_at: str, delta_type: str) -> str:
    return f"{REVIEW_DELTA_DIR_REL}/{slugify(generated_at)}-{delta_type}.json"


def review_delta_snapshot_rel(generated_at: str, delta_type: str, *, suffix: str = ".md") -> str:
    normalized_suffix = suffix if suffix.startswith(".") and "/" not in suffix and "\\" not in suffix else ".md"
    return f"{REVIEW_DELTA_DIR_REL}/{slugify(generated_at)}-{delta_type}-before{normalized_suffix}"


def is_review_delta_artifact(rel_path: str) -> bool:
    return rel_path.startswith(f"{REVIEW_DELTA_DIR_REL}/") and rel_path.endswith(".json")


def copy_previous_snapshot(source: Path, round_dir: Path, rel_path: str, *, force: bool = False) -> str:
    if not source.is_file():
        raise ValueError(f"previous artifact snapshot is not a file: {source}")
    target = round_dir / rel_path
    if target.exists() and not force:
        raise ValueError(f"refusing to overwrite existing delta snapshot without --force: {rel_path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return rel_path


def diff_lines(previous_text: str, current_text: str) -> list[str]:
    lines = list(
        difflib.unified_diff(
            previous_text.splitlines(),
            current_text.splitlines(),
            fromfile="previous",
            tofile="current",
            lineterm="",
        )
    )
    if len(lines) > MAX_DIFF_LINES:
        return [*lines[:MAX_DIFF_LINES], f"... truncated after {MAX_DIFF_LINES} diff lines"]
    return lines


def safe_refs(values: list[str] | tuple[str, ...]) -> list[str]:
    return [value for value in values if is_safe_round_relative_path(value)]


def require_safe_refs(values: list[str] | tuple[str, ...], *, field: str) -> list[str]:
    refs: list[str] = []
    for value in values:
        if not isinstance(value, str) or not is_safe_round_relative_path(value):
            raise ValueError(f"{field} must contain only safe round-relative paths")
        refs.append(value)
    return refs


def hash_refs(round_dir: Path, refs: list[str] | tuple[str, ...]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for ref in safe_refs(refs):
        path = round_dir / ref
        if path.is_file():
            hashes[ref] = sha256_file(path)
    return hashes


def workflow_wave(profile_id: str) -> tuple[str, str]:
    profile = get_workflow_review_profile(profile_id)
    if profile.effective_wave_workflow == "opponent_materials":
        return profile.effective_wave_workflow, "reviewed"
    return profile.effective_wave_workflow, "final"


def closeout_gates(profile_id: str, *, reopened: bool) -> list[str]:
    workflow, wave = workflow_wave(profile_id)
    gates = ["init-review-manifest --run-checks"]
    if reopened:
        gates.append(f"check-review-wave --workflow {workflow} --wave {wave}")
    gates.append(f"review-round-closeout --profile {profile_id}")
    return gates


def next_action(profile_id: str, *, delta_type: str, reopened: bool) -> str:
    if reopened:
        workflow, wave = workflow_wave(profile_id)
        return (
            f"rerun profile independent review with `check-review-wave --workflow {workflow} --wave {wave}`, "
            f"then `review-round-closeout --profile {profile_id}`"
        )
    return f"refresh manifest and rerun `review-round-closeout --profile {profile_id}`"


def approval_summary(round_dir: Path, approval_record_rel: str, current_artifact_rel: str) -> dict[str, object]:
    if not approval_record_rel:
        return {"approval_record_path": "", "approval_record_sha256": "", "approval_status": "missing"}
    if not is_safe_round_relative_path(approval_record_rel):
        return {"approval_record_path": approval_record_rel, "approval_record_sha256": "", "approval_status": "invalid"}
    path = round_dir / approval_record_rel
    if not path.is_file():
        return {"approval_record_path": approval_record_rel, "approval_record_sha256": "", "approval_status": "missing"}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"approval_record_path": approval_record_rel, "approval_record_sha256": "", "approval_status": "invalid"}
    if not isinstance(loaded, dict):
        return {"approval_record_path": approval_record_rel, "approval_record_sha256": "", "approval_status": "invalid"}
    current_hash = sha256_file(round_dir / current_artifact_rel) if (round_dir / current_artifact_rel).is_file() else ""
    reviewed_hash = loaded.get("reviewed_artifact_sha256")
    reviewed_path = loaded.get("reviewed_artifact_path")
    status = (
        "current"
        if reviewed_path == current_artifact_rel and reviewed_hash == current_hash
        else "stale_requires_review"
    )
    return {
        "approval_record_path": approval_record_rel,
        "approval_record_sha256": sha256_file(path),
        "approval_status": status,
        "approval_reviewed_artifact_sha256": reviewed_hash if isinstance(reviewed_hash, str) else "",
        "approval_timestamp": str(loaded.get("timestamp", "")),
    }


def typed_exception_payload(exception_type: str, rationale: str, approved_by: str) -> dict[str, str]:
    if not exception_type and not rationale:
        return {}
    return {
        "type": exception_type.strip(),
        "rationale": rationale.strip(),
        "approved_by": approved_by.strip(),
    }


def build_review_delta_payload(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    profile_id: str,
    delta_type: str,
    previous_snapshot_rel: str,
    current_artifact_rel: str,
    generated_at: str,
    rationale: str,
    affected_sections: list[str] | tuple[str, ...],
    evidence_refs: list[str] | tuple[str, ...] = (),
    approval_record_rel: str = "",
    typed_exception_type: str = "",
    typed_exception_rationale: str = "",
    approved_by: str = "",
    promotion_target: str = "",
) -> dict[str, Any]:
    if delta_type not in DELTA_TYPES:
        raise ValueError(f"delta_type must be one of {', '.join(sorted(DELTA_TYPES))}")
    if not rationale.strip():
        raise ValueError("--rationale is required for review deltas")
    if not is_safe_round_relative_path(previous_snapshot_rel) or not is_safe_round_relative_path(current_artifact_rel):
        raise ValueError("delta artifact paths must be safe round-relative paths")
    previous_path = round_dir / previous_snapshot_rel
    current_path = round_dir / current_artifact_rel
    if not previous_path.is_file():
        raise ValueError(f"missing previous delta snapshot: {previous_snapshot_rel}")
    if not current_path.is_file():
        raise ValueError(f"missing current artifact: {current_artifact_rel}")
    profile = get_workflow_review_profile(profile_id)
    previous_text = previous_path.read_text(encoding="utf-8", errors="replace")
    current_text = current_path.read_text(encoding="utf-8", errors="replace")
    evidence_ref_list = require_safe_refs(tuple(evidence_refs), field="evidence_refs")
    reopened = delta_type in MATERIAL_DELTA_TYPES
    approval = approval_summary(round_dir, approval_record_rel or profile.approval_record, current_artifact_rel)
    exception = typed_exception_payload(typed_exception_type, typed_exception_rationale, approved_by)
    payload: dict[str, Any] = {
        "schema_version": REVIEW_DELTA_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "profile_id": profile.profile_id,
        "workflow_profile": profile.workflow_profile,
        "generated_at": generated_at,
        "producer_type": "human",
        "producer_role": "record-review-delta",
        "producer_agent": None,
        "human_reviewer_note": rationale.strip(),
        "delta_type": delta_type,
        "status": "requires_independent_review" if reopened else "bounded_delta",
        "independent_review_reopened": reopened,
        "previous_artifact_path": previous_snapshot_rel,
        "previous_artifact_sha256": sha256_file(previous_path),
        "current_artifact_path": current_artifact_rel,
        "current_artifact_sha256": sha256_file(current_path),
        "affected_sections": [section for section in affected_sections if section.strip()],
        "evidence_refs": evidence_ref_list,
        "evidence_sha256": hash_refs(round_dir, evidence_ref_list),
        "typed_exception": exception,
        "promotion_target": promotion_target.strip(),
        "closeout_gates_to_rerun": closeout_gates(profile.profile_id, reopened=reopened),
        "next_action": next_action(profile.profile_id, delta_type=delta_type, reopened=reopened),
        "source_refs": [previous_snapshot_rel, current_artifact_rel, *evidence_ref_list],
        "source_sha256": hash_refs(round_dir, (previous_snapshot_rel, current_artifact_rel, *evidence_ref_list)),
        "previous_text_sha256": sha256_text(previous_text),
        "current_text_sha256": sha256_text(current_text),
        "compact_diff": diff_lines(previous_text, current_text),
        "limitations": [],
    }
    payload.update(approval)
    errors = validate_review_delta_record(payload, round_dir=round_dir)
    if errors:
        raise ValueError("\n".join(errors))
    return payload


def validate_review_delta_record(
    loaded: Any,
    *,
    round_dir: Path,
    case_id: str | None = None,
    round_id: str | None = None,
    profile_id: str | None = None,
    rel_path: str = "review delta",
) -> list[str]:
    errors: list[str] = []
    if not isinstance(loaded, dict):
        return [f"{rel_path}: review delta record must be an object"]
    if loaded.get("schema_version") != REVIEW_DELTA_SCHEMA:
        errors.append(f"{rel_path}: schema_version must be {REVIEW_DELTA_SCHEMA}")
    if case_id is not None and loaded.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and loaded.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    if profile_id is not None and loaded.get("profile_id") != profile_id:
        errors.append(f"{rel_path}: profile_id does not match requested profile")
    delta_type = loaded.get("delta_type")
    if delta_type not in DELTA_TYPES:
        errors.append(f"{rel_path}: delta_type must be one of {', '.join(sorted(DELTA_TYPES))}")
    reopened = loaded.get("independent_review_reopened")
    if not isinstance(reopened, bool):
        errors.append(f"{rel_path}: independent_review_reopened must be boolean")
    elif delta_type in MATERIAL_DELTA_TYPES and reopened is not True:
        errors.append(f"{rel_path}: {delta_type} must reopen independent review")
    elif delta_type in NON_MATERIAL_DELTA_TYPES and reopened is not False:
        errors.append(f"{rel_path}: {delta_type} must not silently reopen independent review")
    _validate_hash_bound_path(loaded, rel_path, round_dir, "previous_artifact_path", "previous_artifact_sha256", errors)
    current_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "current_artifact_path", "current_artifact_sha256", errors
    )
    _validate_evidence_refs(loaded, rel_path, round_dir, errors)
    if delta_type == "evidence_challenge" and not loaded.get("evidence_refs"):
        errors.append(f"{rel_path}: evidence_challenge requires at least one evidence_ref")
    _validate_string_list(loaded.get("affected_sections"), rel_path, "affected_sections", errors, require_nonempty=True)
    gates = loaded.get("closeout_gates_to_rerun")
    _validate_string_list(gates, rel_path, "closeout_gates_to_rerun", errors, require_nonempty=True)
    if not isinstance(loaded.get("next_action"), str) or not loaded.get("next_action", "").strip():
        errors.append(f"{rel_path}: next_action must be a non-empty string")
    profile_value = loaded.get("profile_id")
    if isinstance(profile_value, str) and delta_type in DELTA_TYPES and isinstance(reopened, bool):
        try:
            expected_gates = closeout_gates(profile_value, reopened=reopened)
            expected_next_action = next_action(profile_value, delta_type=delta_type, reopened=reopened)
        except ValueError as exc:
            errors.append(f"{rel_path}: {exc}")
        else:
            if gates != expected_gates:
                errors.append(f"{rel_path}: closeout_gates_to_rerun must match canonical profile delta gates")
            if loaded.get("next_action") != expected_next_action:
                errors.append(f"{rel_path}: next_action must match canonical profile delta action")
    else:
        errors.append(f"{rel_path}: profile_id must be a known workflow review profile")
    if delta_type == "general_workflow_lesson" and not valid_promotion_target(str(loaded.get("promotion_target", ""))):
        errors.append(f"{rel_path}: general_workflow_lesson requires a durable promotion_target")
    approval_status = loaded.get("approval_status")
    exception = loaded.get("typed_exception")
    has_exception = isinstance(exception, dict) and bool(exception)
    if delta_type in NON_MATERIAL_DELTA_TYPES:
        if approval_status != "current" and not has_exception:
            errors.append(f"{rel_path}: non-material delta requires current approval record or typed exception")
    if isinstance(exception, dict) and has_exception:
        _validate_typed_exception(exception, rel_path, errors)
    if current_path is not None:
        expected_current_hash = sha256_file(current_path)
        if loaded.get("current_text_sha256") != sha256_text(current_path.read_text(encoding="utf-8", errors="replace")):
            errors.append(f"{rel_path}: current_text_sha256 is stale")
        if approval_status == "current" and loaded.get("approval_reviewed_artifact_sha256") != expected_current_hash:
            errors.append(f"{rel_path}: approval reviewed hash does not match current artifact")
    if not isinstance(loaded.get("compact_diff"), list):
        errors.append(f"{rel_path}: compact_diff must be a list")
    return errors


def review_delta_closeout_errors(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    profile_id: str,
) -> list[str]:
    errors: list[str] = []
    for rel_path, payload in load_review_delta_records(round_dir):
        if isinstance(payload.get("profile_id"), str) and payload.get("profile_id") != profile_id:
            continue
        record_errors = validate_review_delta_record(
            payload,
            round_dir=round_dir,
            case_id=case_id,
            round_id=round_id,
            profile_id=profile_id,
            rel_path=rel_path,
        )
        errors.extend(record_errors)
        if record_errors:
            continue
        if payload.get("independent_review_reopened") is True and not current_approval_after_delta(round_dir, payload):
            errors.append(f"{rel_path}: {payload.get('next_action')}")
    return errors


def load_review_delta_records(round_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    directory = round_dir / REVIEW_DELTA_DIR_REL
    records: list[tuple[str, dict[str, Any]]] = []
    if not directory.is_dir():
        return records
    for path in sorted(directory.glob("*.json")):
        rel_path = path.relative_to(round_dir).as_posix()
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            records.append((rel_path, {"_load_error": "invalid_json"}))
            continue
        records.append((rel_path, loaded if isinstance(loaded, dict) else {"_load_error": "not_object"}))
    return records


def current_approval_after_delta(round_dir: Path, payload: dict[str, Any]) -> bool:
    approval_rel = payload.get("approval_record_path")
    current_rel = payload.get("current_artifact_path")
    if not isinstance(approval_rel, str) or not isinstance(current_rel, str):
        return False
    if not is_safe_round_relative_path(approval_rel) or not is_safe_round_relative_path(current_rel):
        return False
    approval_path = round_dir / approval_rel
    current_path = round_dir / current_rel
    if not approval_path.is_file() or not current_path.is_file():
        return False
    try:
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if not isinstance(approval, dict):
        return False
    if approval.get("reviewed_artifact_path") != current_rel:
        return False
    if approval.get("reviewed_artifact_sha256") != sha256_file(current_path):
        return False
    approval_timestamp = str(approval.get("timestamp", ""))
    delta_timestamp = str(payload.get("generated_at", ""))
    return bool(approval_timestamp and delta_timestamp and approval_timestamp > delta_timestamp)


def valid_promotion_target(value: str) -> bool:
    if value in PROMOTION_TARGETS:
        return True
    return any(value.startswith(prefix) for prefix in PROMOTION_TARGET_PREFIXES)


def _validate_hash_bound_path(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path,
    path_field: str,
    hash_field: str,
    errors: list[str],
) -> Path | None:
    path_value = loaded.get(path_field)
    if not isinstance(path_value, str) or not is_safe_round_relative_path(path_value):
        errors.append(f"{rel_path}: {path_field} must be a safe round-relative path")
        return None
    path = round_dir / path_value
    if not path.is_file():
        errors.append(f"{rel_path}: {path_field} points to a missing file: {path_value}")
        return None
    if loaded.get(hash_field) != sha256_file(path):
        errors.append(f"{rel_path}: {hash_field} is stale for {path_value}")
        return None
    return path


def _validate_evidence_refs(loaded: dict[str, Any], rel_path: str, round_dir: Path, errors: list[str]) -> None:
    evidence_refs = loaded.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        errors.append(f"{rel_path}: evidence_refs must be a list")
        return
    evidence_sha256 = loaded.get("evidence_sha256")
    if not isinstance(evidence_sha256, dict):
        errors.append(f"{rel_path}: evidence_sha256 must be an object")
        return
    for ref in evidence_refs:
        if not isinstance(ref, str) or not is_safe_round_relative_path(ref):
            errors.append(f"{rel_path}: evidence_refs must contain safe round-relative paths")
            continue
        path = round_dir / ref
        if not path.is_file():
            errors.append(f"{rel_path}: evidence_ref is missing: {ref}")
        elif evidence_sha256.get(ref) != sha256_file(path):
            errors.append(f"{rel_path}: evidence_sha256 is stale for {ref}")


def _validate_string_list(
    value: Any,
    rel_path: str,
    field: str,
    errors: list[str],
    *,
    require_nonempty: bool = False,
) -> None:
    if not isinstance(value, list):
        errors.append(f"{rel_path}: {field} must be a list")
        return
    if require_nonempty and not value:
        errors.append(f"{rel_path}: {field} must be non-empty")
    for item in value:
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{rel_path}: {field} entries must be non-empty strings")


def _validate_typed_exception(exception: dict[str, Any], rel_path: str, errors: list[str]) -> None:
    if exception.get("type") not in TYPED_EXCEPTION_TYPES:
        errors.append(f"{rel_path}: typed_exception.type must be one of {', '.join(sorted(TYPED_EXCEPTION_TYPES))}")
    if not isinstance(exception.get("rationale"), str) or not exception.get("rationale", "").strip():
        errors.append(f"{rel_path}: typed_exception.rationale must be a non-empty string")
    if not isinstance(exception.get("approved_by"), str) or not exception.get("approved_by", "").strip():
        errors.append(f"{rel_path}: typed_exception.approved_by must be a non-empty string")
