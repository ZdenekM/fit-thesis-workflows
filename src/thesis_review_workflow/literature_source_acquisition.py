"""Contracts for targeted literature source acquisition evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from thesis_review_workflow.evidence_capsules import validate_source_sha256_map
from thesis_review_workflow.paths import is_safe_round_relative_path

SOURCE_ACQUISITION_REL = "work/literature/source_acquisition.json"
SOURCE_ACQUISITION_SCHEMA = "literature-source-acquisition-v1"

KNOWN_SELECTION_STATUSES = {"selected", "not_selected"}
KNOWN_ACQUISITION_STATUSES = {
    "pdf_read",
    "full_text_read",
    "metadata_verified",
    "abstract_read",
    "open_metadata_only",
    "paywalled_unavailable",
    "not_found",
    "not_attempted_operator_disabled",
    "not_attempted_not_material",
}
KNOWN_CLAIM_SUPPORT_VERDICTS = {
    "supports",
    "partially_supports",
    "does_not_support",
    "unclear",
    "not_checked",
}
ATTEMPTED_STATUSES = {
    "pdf_read",
    "full_text_read",
    "metadata_verified",
    "abstract_read",
    "open_metadata_only",
    "paywalled_unavailable",
    "not_found",
}
BLOCKED_OR_UNRESOLVED_STATUSES = {
    "paywalled_unavailable",
    "not_found",
    "not_attempted_operator_disabled",
}
LOCAL_EVIDENCE_STATUSES = {"pdf_read", "full_text_read"}
CLAIM_CHECK_STATUSES = {
    "pdf_read",
    "full_text_read",
    "metadata_verified",
    "abstract_read",
    "open_metadata_only",
}


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def validate_round_relative_refs(
    rel_path: str,
    label: str,
    refs: Any,
    errors: list[str],
    *,
    round_dir: Path | None,
    require_literature_work_path: bool = False,
) -> list[str]:
    values = string_list(refs)
    if not isinstance(refs, list):
        errors.append(f"{rel_path}: {label} must be a list of round-relative paths")
        return values
    for value in values:
        if not is_safe_round_relative_path(value):
            errors.append(f"{rel_path}: {label} contains an unsafe round-relative path: {value}")
            continue
        if require_literature_work_path and not value.startswith("work/literature/"):
            errors.append(f"{rel_path}: {label} must stay under work/literature/: {value}")
            continue
        if round_dir is not None and not (round_dir / value).is_file():
            errors.append(f"{rel_path}: {label} referenced file is missing: {value}")
    return values


def validate_attempts(rel_path: str, citation_id: str, attempts: Any, errors: list[str]) -> set[str]:
    if not isinstance(attempts, list):
        errors.append(f"{rel_path}: {citation_id}: attempts must be a list")
        return set()
    valid_statuses: set[str] = set()
    for index, attempt in enumerate(attempts, start=1):
        if not isinstance(attempt, dict):
            errors.append(f"{rel_path}: {citation_id}: attempts item {index} must be an object")
            continue
        missing = [field for field in ("source_type", "locator", "status") if not non_empty_string(attempt.get(field))]
        if missing:
            errors.append(f"{rel_path}: {citation_id}: attempts item {index} missing {', '.join(missing)}")
            continue
        if attempt.get("status") not in KNOWN_ACQUISITION_STATUSES:
            expected = ", ".join(sorted(KNOWN_ACQUISITION_STATUSES))
            errors.append(f"{rel_path}: {citation_id}: attempts item {index} status must be one of: {expected}")
            continue
        valid_statuses.add(str(attempt.get("status")))
    return valid_statuses


def validate_claim_support_checks(rel_path: str, citation_id: str, claim_checks: Any, errors: list[str]) -> bool:
    if not isinstance(claim_checks, list):
        errors.append(f"{rel_path}: {citation_id}: claim_support_checked must be a list")
        return False
    valid_count = 0
    for index, item in enumerate(claim_checks, start=1):
        if not isinstance(item, dict):
            errors.append(f"{rel_path}: {citation_id}: claim_support_checked item {index} must be an object")
            continue
        if not non_empty_string(item.get("claim_ref")):
            errors.append(f"{rel_path}: {citation_id}: claim_support_checked item {index} missing claim_ref")
        verdict = item.get("verdict")
        if verdict not in KNOWN_CLAIM_SUPPORT_VERDICTS:
            expected = ", ".join(sorted(KNOWN_CLAIM_SUPPORT_VERDICTS))
            errors.append(
                f"{rel_path}: {citation_id}: claim_support_checked item {index} verdict must be one of: {expected}"
            )
            continue
        valid_count += 1
    return valid_count > 0


def validate_citation(
    citation: Any,
    rel_path: str,
    index: int,
    errors: list[str],
    *,
    round_dir: Path | None,
) -> None:
    if not isinstance(citation, dict):
        errors.append(f"{rel_path}: citations item {index} must be an object")
        return
    citation_id = citation.get("citation_id")
    if not non_empty_string(citation_id):
        citation_id = f"citations item {index}"
        errors.append(f"{rel_path}: {citation_id}: missing citation_id")
    else:
        citation_id = str(citation_id).strip()
    if not non_empty_string(citation.get("citation_label")):
        errors.append(f"{rel_path}: {citation_id}: missing citation_label")
    if not non_empty_string(citation.get("title_or_source")):
        errors.append(f"{rel_path}: {citation_id}: missing title_or_source")

    selection_status = citation.get("selection_status")
    if selection_status not in KNOWN_SELECTION_STATUSES:
        expected = ", ".join(sorted(KNOWN_SELECTION_STATUSES))
        errors.append(f"{rel_path}: {citation_id}: selection_status must be one of: {expected}")
    acquisition_status = citation.get("acquisition_status")
    if acquisition_status not in KNOWN_ACQUISITION_STATUSES:
        expected = ", ".join(sorted(KNOWN_ACQUISITION_STATUSES))
        errors.append(f"{rel_path}: {citation_id}: acquisition_status must be one of: {expected}")

    selection_reasons = string_list(citation.get("selection_reasons"))
    if not selection_reasons:
        errors.append(f"{rel_path}: {citation_id}: selection_reasons must be a non-empty string list")
    thesis_refs = validate_round_relative_refs(
        rel_path,
        f"{citation_id}: thesis_refs",
        citation.get("thesis_refs"),
        errors,
        round_dir=round_dir,
    )
    if selection_status == "selected" and not thesis_refs:
        errors.append(f"{rel_path}: {citation_id}: selected citation must include thesis_refs")

    attempt_statuses = validate_attempts(rel_path, citation_id, citation.get("attempts"), errors)
    if selection_status == "selected" and acquisition_status in ATTEMPTED_STATUSES:
        if not attempt_statuses:
            errors.append(f"{rel_path}: {citation_id}: selected citation must record at least one source attempt")
        elif acquisition_status not in attempt_statuses:
            errors.append(
                f"{rel_path}: {citation_id}: selected citation acquisition_status must match "
                "at least one attempt status"
            )
    if selection_status == "selected" and acquisition_status == "not_attempted_not_material":
        errors.append(f"{rel_path}: {citation_id}: selected citation cannot be not_attempted_not_material")
    if selection_status == "selected" and acquisition_status in BLOCKED_OR_UNRESOLVED_STATUSES:
        limitations = string_list(citation.get("limitations"))
        if not limitations:
            errors.append(f"{rel_path}: {citation_id}: {acquisition_status} selected citation must record a limitation")

    local_refs = validate_round_relative_refs(
        rel_path,
        f"{citation_id}: local_source_refs",
        citation.get("local_source_refs", []),
        errors,
        round_dir=round_dir,
        require_literature_work_path=True,
    )
    evidence_refs = validate_round_relative_refs(
        rel_path,
        f"{citation_id}: source_evidence_refs",
        citation.get("source_evidence_refs", []),
        errors,
        round_dir=round_dir,
        require_literature_work_path=True,
    )
    if (
        selection_status == "selected"
        and acquisition_status in LOCAL_EVIDENCE_STATUSES
        and not (local_refs or evidence_refs)
    ):
        errors.append(
            f"{rel_path}: {citation_id}: {acquisition_status} must cite cached PDF/text evidence under work/literature/"
        )

    claim_checks = citation.get("claim_support_checked", [])
    has_valid_claim_checks = validate_claim_support_checks(rel_path, citation_id, claim_checks, errors)
    if selection_status == "selected" and acquisition_status in CLAIM_CHECK_STATUSES and not has_valid_claim_checks:
        errors.append(f"{rel_path}: {citation_id}: selected accessible source must record claim_support_checked")


def validate_source_acquisition_payload(
    loaded: Any,
    rel_path: str = SOURCE_ACQUISITION_REL,
    *,
    round_dir: Path | None = None,
    case_id: str | None = None,
    round_id: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(loaded, dict):
        return [f"{rel_path}: JSON work artifact must be an object"]
    if loaded.get("schema_version") != SOURCE_ACQUISITION_SCHEMA:
        errors.append(f"{rel_path}: schema_version must be {SOURCE_ACQUISITION_SCHEMA}")
    if case_id is not None and loaded.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and loaded.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    for field in ("generated_at", "producer_role", "source_resolution_policy"):
        if not non_empty_string(loaded.get(field)):
            errors.append(f"{rel_path}: missing {field}")
    if not isinstance(loaded.get("target_selection_policy"), dict):
        errors.append(f"{rel_path}: target_selection_policy must be an object")
    if not isinstance(loaded.get("limitations"), list):
        errors.append(f"{rel_path}: limitations must be a list")
    source_refs = validate_round_relative_refs(
        rel_path,
        "source_refs",
        loaded.get("source_refs"),
        errors,
        round_dir=round_dir,
    )
    if not source_refs:
        errors.append(f"{rel_path}: source_refs must include thesis/bibliography inputs used for triage")
    validate_source_sha256_map(
        loaded.get("source_sha256"),
        rel_path,
        errors,
        round_dir=round_dir,
        expected_refs=source_refs,
    )
    citations = loaded.get("citations")
    if not isinstance(citations, list):
        errors.append(f"{rel_path}: citations must be a list")
        return errors
    if not citations:
        errors.append(f"{rel_path}: citations must include at least one triaged citation")
    selected_count = 0
    for index, citation in enumerate(citations, start=1):
        if isinstance(citation, dict) and citation.get("selection_status") == "selected":
            selected_count += 1
        validate_citation(citation, rel_path, index, errors, round_dir=round_dir)
    if selected_count == 0 and not loaded.get("no_selected_sources_rationale"):
        errors.append(f"{rel_path}: no selected citations; provide no_selected_sources_rationale")
    if selected_count > 0:
        blocked_selected = [
            citation
            for citation in citations
            if isinstance(citation, dict)
            and citation.get("selection_status") == "selected"
            and citation.get("acquisition_status") in BLOCKED_OR_UNRESOLVED_STATUSES
        ]
        if blocked_selected and not string_list(loaded.get("limitations")):
            errors.append(f"{rel_path}: selected blocked/unresolved citations require a top-level limitations entry")
    return errors
