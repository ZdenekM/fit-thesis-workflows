"""Claim-level review-basis ledger validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.evidence_capsules import (
    EVIDENCE_CAPSULES_REL,
    PRODUCER_TYPES,
    SHA256_RE,
    is_manifest_safe_round_ref,
    validate_source_sha256_map,
)

CLAIM_REVIEW_BASIS_SCHEMA = "claim-review-basis-v1"
CLAIM_REVIEW_BASIS_REL = "work/context/claim_review_basis.json"

CLAIM_PRIORITIES = {"p0", "p1", "p2", "p3", "informational"}
RAW_SOURCE_ESCALATION_REASONS = {
    "contradiction",
    "grade_impact",
    "missing_anchor",
    "p0_p1_verification",
    "reviewer_challenge",
}
VERIFICATION_STATUSES = {
    "pending",
    "verified_from_basis",
    "needs_raw_source",
    "contradicted",
    "unsupported",
    "not_applicable",
}
CLAIM_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


def validate_claim_review_basis_payload(
    loaded: Any,
    rel_path: str = CLAIM_REVIEW_BASIS_REL,
    *,
    round_dir: Path | None = None,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(loaded, dict):
        return [f"{rel_path}: claim review basis artifact must be an object"]

    _validate_header(loaded, rel_path, case_id, round_id, errors)
    if "review_basis_path" in loaded or "review_basis_sha256" in loaded:
        errors.append(f"{rel_path}: use draft_ref/draft_sha256; review_basis_path belongs only to approval records")
    _validate_draft_binding(loaded, rel_path, round_dir, errors)
    _validate_optional_ref_list(
        loaded.get("capsule_refs"), f"{rel_path}: capsule_refs", errors, round_dir, require_existing_refs
    )
    _validate_string_list(loaded.get("limitations"), f"{rel_path}: limitations", errors)

    claims = _require_list(loaded, "claims", rel_path, errors)
    if isinstance(claims, list):
        for index, claim in enumerate(claims, start=1):
            _validate_claim(claim, f"{rel_path}: claims item {index}", round_dir, require_existing_refs, errors)
    return errors


def _validate_header(
    loaded: dict[str, Any],
    rel_path: str,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    if loaded.get("schema_version") != CLAIM_REVIEW_BASIS_SCHEMA:
        errors.append(f"{rel_path}: schema_version must be {CLAIM_REVIEW_BASIS_SCHEMA}")
    if case_id is not None and loaded.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and loaded.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    for field in ("case_id", "round_id", "generated_at", "producer_role"):
        _require_nonempty_string(loaded, field, rel_path, errors)
    producer_type = loaded.get("producer_type")
    if producer_type not in PRODUCER_TYPES:
        errors.append(f"{rel_path}: producer_type must be one of agent, deterministic_helper, human")
    if producer_type in {"agent", "deterministic_helper"}:
        _require_nonempty_string(loaded, "producer_agent", rel_path, errors)
    elif producer_type == "human":
        _require_nonempty_string(loaded, "human_reviewer_note", rel_path, errors)


def _validate_draft_binding(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    errors: list[str],
) -> None:
    _require_nonempty_string(loaded, "draft_ref", rel_path, errors)
    draft_ref = loaded.get("draft_ref")
    if isinstance(draft_ref, str):
        if not is_manifest_safe_round_ref(draft_ref) or not draft_ref.startswith(("work/", "outputs/")):
            errors.append(f"{rel_path}: draft_ref must be a safe work/ or outputs/ round-relative path")
        elif round_dir is not None and (round_dir / draft_ref).is_file():
            draft_hash = loaded.get("draft_sha256")
            if draft_hash != sha256_file(round_dir / draft_ref):
                errors.append(f"{rel_path}: draft_sha256 is stale for {draft_ref}")
        elif round_dir is not None:
            errors.append(f"{rel_path}: draft_ref points to a missing file: {draft_ref}")
    if not isinstance(loaded.get("draft_sha256"), str) or not SHA256_RE.fullmatch(str(loaded.get("draft_sha256"))):
        errors.append(f"{rel_path}: draft_sha256 must be a 64-character hex string")


def _validate_claim(
    claim: Any,
    prefix: str,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    if not isinstance(claim, dict):
        errors.append(f"{prefix} must be object")
        return
    _require_nonempty_string(claim, "claim_id", prefix, errors)
    claim_id = claim.get("claim_id")
    if isinstance(claim_id, str) and claim_id and not CLAIM_ID_RE.fullmatch(claim_id):
        errors.append(f"{prefix}: claim_id may contain only letters, digits, underscore, dot, colon, or hyphen")
    _require_nonempty_string(claim, "claim_text", prefix, errors)
    _require_enum(claim, "priority", CLAIM_PRIORITIES, prefix, errors)
    _require_enum(claim, "verification_status", VERIFICATION_STATUSES, prefix, errors)
    if not isinstance(claim.get("grade_impact"), bool):
        errors.append(f"{prefix}: grade_impact must be bool")

    evidence_refs = _validate_optional_ref_list(
        claim.get("evidence_refs"),
        f"{prefix}: evidence_refs",
        errors,
        round_dir,
        require_existing_refs,
    )
    capsule_refs = _validate_optional_ref_list(
        claim.get("capsule_refs"),
        f"{prefix}: capsule_refs",
        errors,
        round_dir,
        require_existing_refs,
    )
    escalation_reasons, escalation_refs = _validate_escalations(
        claim.get("raw_source_escalations"),
        f"{prefix}: raw_source_escalations",
        round_dir,
        require_existing_refs,
        errors,
    )
    validate_source_sha256_map(
        claim.get("source_sha256"),
        prefix,
        errors,
        round_dir=round_dir,
        expected_refs=evidence_refs + capsule_refs + escalation_refs,
        require_existing_refs=require_existing_refs,
    )
    if not evidence_refs and not capsule_refs and "missing_anchor" not in escalation_reasons:
        errors.append(f"{prefix}: missing evidence/capsule refs require missing_anchor escalation")
    if claim.get("priority") in {"p0", "p1"} and "p0_p1_verification" not in escalation_reasons:
        errors.append(f"{prefix}: p0/p1 claims require p0_p1_verification escalation")
    if claim.get("grade_impact") is True and "grade_impact" not in escalation_reasons:
        errors.append(f"{prefix}: grade-impacting claims require grade_impact escalation")
    if claim.get("verification_status") == "needs_raw_source" and not escalation_reasons:
        errors.append(f"{prefix}: needs_raw_source requires at least one raw_source_escalation")
    if claim.get("verification_status") == "contradicted" and "contradiction" not in escalation_reasons:
        errors.append(f"{prefix}: contradicted claims require contradiction escalation")


def _validate_escalations(
    value: Any,
    prefix: str,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> tuple[set[str], list[str]]:
    escalations = _require_list_value(value, prefix, errors)
    reasons: set[str] = set()
    source_refs: list[str] = []
    if not isinstance(escalations, list):
        return reasons, source_refs
    for index, item in enumerate(escalations, start=1):
        item_prefix = f"{prefix} item {index}"
        if not isinstance(item, dict):
            errors.append(f"{item_prefix} must be object")
            continue
        _require_enum(item, "reason", RAW_SOURCE_ESCALATION_REASONS, item_prefix, errors)
        reason = item.get("reason")
        if isinstance(reason, str):
            reasons.add(reason)
        source_refs.extend(
            _validate_optional_ref_list(
                item.get("source_refs"), f"{item_prefix}: source_refs", errors, round_dir, require_existing_refs
            )
        )
        if "note" in item and not isinstance(item.get("note"), str):
            errors.append(f"{item_prefix}: note must be str when present")
    return reasons, source_refs


def _validate_optional_ref_list(
    value: Any,
    prefix: str,
    errors: list[str],
    round_dir: Path | None,
    require_existing_refs: bool,
) -> list[str]:
    refs = _require_list_value(value, prefix, errors)
    safe_refs: list[str] = []
    if not isinstance(refs, list):
        return safe_refs
    for index, ref in enumerate(refs, start=1):
        if not isinstance(ref, str) or not ref:
            errors.append(f"{prefix} item {index}: ref must be non-empty str")
            continue
        if not is_manifest_safe_round_ref(ref):
            errors.append(
                f"{prefix} item {index}: ref must be relative under inputs/, extracted/, notes/, work/, or outputs/"
            )
            continue
        if round_dir is not None and require_existing_refs and not (round_dir / ref).is_file():
            errors.append(f"{prefix} item {index}: referenced file is missing: {ref}")
        safe_refs.append(ref)
    return safe_refs


def _validate_string_list(value: Any, prefix: str, errors: list[str]) -> None:
    items = _require_list_value(value, prefix, errors)
    if not isinstance(items, list):
        return
    for index, item in enumerate(items, start=1):
        if not isinstance(item, str):
            errors.append(f"{prefix} item {index}: item must be str")


def _require_nonempty_string(value: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    if not isinstance(value.get(field), str) or not value[field]:
        errors.append(f"{prefix}: {field} must be non-empty str")


def _require_enum(value: dict[str, Any], field: str, allowed: set[str], prefix: str, errors: list[str]) -> None:
    loaded = value.get(field)
    if loaded not in allowed:
        choices = ", ".join(sorted(allowed))
        errors.append(f"{prefix}: {field} must be one of {choices}")


def _require_list(value: dict[str, Any], field: str, prefix: str, errors: list[str]) -> Any:
    loaded = value.get(field)
    if not isinstance(loaded, list):
        errors.append(f"{prefix}: {field} must be list")
    return loaded


def _require_list_value(value: Any, prefix: str, errors: list[str]) -> Any:
    if not isinstance(value, list):
        errors.append(f"{prefix} must be list")
    return value


def default_capsule_refs() -> list[str]:
    return [EVIDENCE_CAPSULES_REL]
