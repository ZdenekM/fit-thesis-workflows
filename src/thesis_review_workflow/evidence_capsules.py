"""Structured evidence-capsule handoff validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.paths import is_safe_round_relative_path

EVIDENCE_CAPSULE_SCHEMA = "evidence-capsule-v1"
EVIDENCE_CAPSULES_REL = "work/context/evidence_capsules.json"

ALLOWED_ROUND_REF_PREFIXES = ("inputs/", "extracted/", "notes/", "work/", "outputs/")
ANCHOR_TYPES = {"page", "section", "path", "line", "figure", "table", "paragraph", "other"}
OPEN_RAW_SOURCE_REASONS = {
    "ambiguous_extraction",
    "contradiction",
    "grade_impact",
    "missing_anchor",
    "p0_p1_verification",
    "reviewer_challenge",
    "schema_mismatch",
    "source_hash_mismatch",
}
PRODUCER_TYPES = {"agent", "deterministic_helper", "human"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def is_manifest_safe_round_ref(value: str) -> bool:
    return is_safe_round_relative_path(value) and value.startswith(ALLOWED_ROUND_REF_PREFIXES)


def round_ref_sha256(round_dir: Path, rel_path: str) -> str:
    if not is_manifest_safe_round_ref(rel_path):
        raise ValueError(f"ref must be a safe round-relative artifact path: {rel_path}")
    path = round_dir / rel_path
    if not path.is_file():
        raise ValueError(f"ref does not point to an existing file: {rel_path}")
    return sha256_file(path)


def source_sha256_for_refs(round_dir: Path, refs: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for ref in sorted(set(refs)):
        hashes[ref] = round_ref_sha256(round_dir, ref)
    return hashes


def validate_source_sha256_map(
    value: Any,
    prefix: str,
    errors: list[str],
    *,
    round_dir: Path | None = None,
    expected_refs: list[str] | None = None,
    require_existing_refs: bool = True,
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{prefix}: source_sha256 must be object")
        return
    for ref, digest in value.items():
        if not isinstance(ref, str) or not is_manifest_safe_round_ref(ref):
            errors.append(f"{prefix}: source_sha256 keys must be safe round-relative artifact paths")
            continue
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"{prefix}: source_sha256 values must be sha256 hex strings")
            continue
        if round_dir is not None:
            path = round_dir / ref
            if path.is_file():
                if sha256_file(path) != digest:
                    errors.append(f"{prefix}: source_sha256 is stale for {ref}")
            elif require_existing_refs:
                errors.append(f"{prefix}: source_sha256 points to a missing file: {ref}")
    for ref in expected_refs or []:
        if not isinstance(ref, str) or not is_manifest_safe_round_ref(ref):
            continue
        if ref not in value:
            errors.append(f"{prefix}: source_sha256 missing hash for {ref}")


def validate_evidence_capsules_payload(
    loaded: Any,
    rel_path: str = EVIDENCE_CAPSULES_REL,
    *,
    round_dir: Path | None = None,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(loaded, dict):
        return [f"{rel_path}: evidence capsule artifact must be an object"]

    _validate_header(loaded, rel_path, EVIDENCE_CAPSULE_SCHEMA, case_id, round_id, errors)
    source_refs = _require_list(loaded, "source_refs", rel_path, errors)
    declared_source_refs = (
        {ref for ref in source_refs if isinstance(ref, str)} if isinstance(source_refs, list) else set()
    )
    if isinstance(source_refs, list):
        _validate_ref_list(source_refs, f"{rel_path}: source_refs", errors, round_dir, require_existing_refs)

    capsules = _require_list(loaded, "capsules", rel_path, errors)
    if isinstance(capsules, list):
        for index, capsule in enumerate(capsules, start=1):
            _validate_capsule(
                capsule,
                f"{rel_path}: capsules item {index}",
                loaded,
                declared_source_refs,
                round_dir,
                require_existing_refs,
                errors,
            )
    if isinstance(source_refs, list):
        validate_source_sha256_map(
            loaded.get("source_sha256"),
            rel_path,
            errors,
            round_dir=round_dir,
            expected_refs=sorted(declared_source_refs),
            require_existing_refs=require_existing_refs,
        )
    _validate_string_list(loaded.get("limitations"), f"{rel_path}: limitations", errors)
    return errors


def _validate_header(
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
    for field in ("case_id", "round_id", "generated_at", "producer_role"):
        _require_nonempty_string(loaded, field, rel_path, errors)
    producer_type = loaded.get("producer_type")
    if producer_type not in PRODUCER_TYPES:
        errors.append(f"{rel_path}: producer_type must be one of agent, deterministic_helper, human")
    if producer_type in {"agent", "deterministic_helper"}:
        _require_nonempty_string(loaded, "producer_agent", rel_path, errors)
    elif producer_type == "human":
        _require_nonempty_string(loaded, "human_reviewer_note", rel_path, errors)


def _validate_capsule(
    capsule: Any,
    prefix: str,
    loaded: dict[str, Any],
    declared_source_refs: set[str],
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    if not isinstance(capsule, dict):
        errors.append(f"{prefix} must be object")
        return
    _require_nonempty_string(capsule, "capsule_id", prefix, errors)
    _require_nonempty_string(capsule, "source_ref", prefix, errors)
    _require_nonempty_string(capsule, "summary", prefix, errors)
    source_ref = capsule.get("source_ref")
    source_hash = capsule.get("source_sha256")
    if isinstance(source_ref, str):
        _validate_ref(source_ref, f"{prefix}: source_ref", errors, round_dir, require_existing_refs)
        _require_declared_source_ref(source_ref, declared_source_refs, f"{prefix}: source_ref", errors)
        if not isinstance(source_hash, str) or not SHA256_RE.fullmatch(source_hash):
            errors.append(f"{prefix}: source_sha256 must be a 64-character hex string")
        else:
            top_level_hashes = loaded.get("source_sha256")
            if isinstance(top_level_hashes, dict) and top_level_hashes.get(source_ref) not in {None, source_hash}:
                errors.append(f"{prefix}: source_sha256 does not match top-level hash for {source_ref}")
            if (
                round_dir is not None
                and (round_dir / source_ref).is_file()
                and sha256_file(round_dir / source_ref) != source_hash
            ):
                errors.append(f"{prefix}: source_sha256 is stale for {source_ref}")

    anchor_ids = _validate_anchor_refs(
        capsule.get("anchor_refs"),
        f"{prefix}: anchor_refs",
        declared_source_refs,
        errors,
        round_dir,
        require_existing_refs,
    )
    _validate_fact_items(capsule.get("extracted_facts"), f"{prefix}: extracted_facts", anchor_ids, errors)
    _validate_claim_items(capsule.get("candidate_claims"), f"{prefix}: candidate_claims", anchor_ids, errors)
    _validate_string_list(capsule.get("uncertainties"), f"{prefix}: uncertainties", errors)
    _validate_string_list(capsule.get("limitations"), f"{prefix}: limitations", errors)
    _validate_enum_list(
        capsule.get("open_raw_source_if"), OPEN_RAW_SOURCE_REASONS, f"{prefix}: open_raw_source_if", errors
    )


def _validate_anchor_refs(
    value: Any,
    prefix: str,
    declared_source_refs: set[str],
    errors: list[str],
    round_dir: Path | None,
    require_existing_refs: bool,
) -> set[str]:
    anchors = _require_list_value(value, prefix, errors)
    anchor_ids: set[str] = set()
    if not isinstance(anchors, list):
        return anchor_ids
    for index, item in enumerate(anchors, start=1):
        item_prefix = f"{prefix} item {index}"
        if not isinstance(item, dict):
            errors.append(f"{item_prefix} must be object")
            continue
        _require_nonempty_string(item, "anchor_id", item_prefix, errors)
        anchor_id = item.get("anchor_id")
        if isinstance(anchor_id, str) and anchor_id:
            if anchor_id in anchor_ids:
                errors.append(f"{item_prefix}: anchor_id must be unique within the capsule")
            anchor_ids.add(anchor_id)
        _require_nonempty_string(item, "source_ref", item_prefix, errors)
        source_ref = item.get("source_ref")
        if isinstance(source_ref, str):
            _validate_ref(source_ref, f"{item_prefix}: source_ref", errors, round_dir, require_existing_refs)
            _require_declared_source_ref(source_ref, declared_source_refs, f"{item_prefix}: source_ref", errors)
        _require_enum(item, "anchor_type", ANCHOR_TYPES, item_prefix, errors)
        _require_nonempty_string(item, "locator", item_prefix, errors)
    return anchor_ids


def _validate_fact_items(value: Any, prefix: str, anchor_ids: set[str], errors: list[str]) -> None:
    facts = _require_list_value(value, prefix, errors)
    if not isinstance(facts, list):
        return
    for index, item in enumerate(facts, start=1):
        item_prefix = f"{prefix} item {index}"
        if not isinstance(item, dict):
            errors.append(f"{item_prefix} must be object")
            continue
        _require_nonempty_string(item, "fact_id", item_prefix, errors)
        _require_nonempty_string(item, "summary", item_prefix, errors)
        _validate_anchor_id_list(item.get("anchor_refs"), f"{item_prefix}: anchor_refs", anchor_ids, errors)


def _validate_claim_items(value: Any, prefix: str, anchor_ids: set[str], errors: list[str]) -> None:
    claims = _require_list_value(value, prefix, errors)
    if not isinstance(claims, list):
        return
    for index, item in enumerate(claims, start=1):
        item_prefix = f"{prefix} item {index}"
        if not isinstance(item, dict):
            errors.append(f"{item_prefix} must be object")
            continue
        _require_nonempty_string(item, "claim_id", item_prefix, errors)
        _require_nonempty_string(item, "claim_text", item_prefix, errors)
        _validate_anchor_id_list(item.get("anchor_refs"), f"{item_prefix}: anchor_refs", anchor_ids, errors)


def _validate_anchor_id_list(value: Any, prefix: str, anchor_ids: set[str], errors: list[str]) -> None:
    refs = _require_list_value(value, prefix, errors)
    if not isinstance(refs, list):
        return
    for index, ref in enumerate(refs, start=1):
        if not isinstance(ref, str) or not ref:
            errors.append(f"{prefix} item {index}: anchor ref must be non-empty str")
        elif ref not in anchor_ids:
            errors.append(f"{prefix} item {index}: anchor ref is not defined in anchor_refs: {ref}")


def _validate_ref_list(
    value: list[Any],
    prefix: str,
    errors: list[str],
    round_dir: Path | None,
    require_existing_refs: bool,
) -> None:
    for index, ref in enumerate(value, start=1):
        _validate_ref(ref, f"{prefix} item {index}", errors, round_dir, require_existing_refs)


def _validate_ref(
    value: Any,
    label: str,
    errors: list[str],
    round_dir: Path | None,
    require_existing_refs: bool,
) -> None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label}: ref must be non-empty str")
        return
    if not is_manifest_safe_round_ref(value):
        errors.append(f"{label}: ref must be relative under inputs/, extracted/, notes/, work/, or outputs/")
        return
    if round_dir is not None and require_existing_refs and not (round_dir / value).is_file():
        errors.append(f"{label}: referenced file is missing: {value}")


def _require_declared_source_ref(value: str, declared_source_refs: set[str], label: str, errors: list[str]) -> None:
    if is_manifest_safe_round_ref(value) and value not in declared_source_refs:
        errors.append(f"{label}: ref must be listed in top-level source_refs")


def _validate_string_list(value: Any, prefix: str, errors: list[str]) -> None:
    items = _require_list_value(value, prefix, errors)
    if not isinstance(items, list):
        return
    for index, item in enumerate(items, start=1):
        if not isinstance(item, str):
            errors.append(f"{prefix} item {index}: item must be str")


def _validate_enum_list(value: Any, allowed: set[str], prefix: str, errors: list[str]) -> None:
    items = _require_list_value(value, prefix, errors)
    if not isinstance(items, list):
        return
    for index, item in enumerate(items, start=1):
        if item not in allowed:
            choices = ", ".join(sorted(allowed))
            errors.append(f"{prefix} item {index}: value must be one of {choices}")


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
