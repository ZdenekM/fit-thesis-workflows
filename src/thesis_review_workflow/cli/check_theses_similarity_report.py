"""Validate imported Theses.cz similarity-report evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.review_approvals import validate_review_approval_artifact
from thesis_review_workflow.structured_evidence import validate_structured_evidence_artifact
from thesis_review_workflow.theses_similarity import (
    CURRENT_SUBMISSION_LINK_STATUSES,
    THESES_SIMILARITY_ASSESSMENT_REL,
    THESES_SIMILARITY_EXTRACTED_TEXT_REL,
    THESES_SIMILARITY_INTAKE_REL,
    THESES_SIMILARITY_INTAKE_SCHEMA,
    THESES_SIMILARITY_REPORT_REL,
    THESES_SIMILARITY_REVIEW_APPROVAL_REL,
    THESES_SIMILARITY_REVIEW_DRAFT_REL,
    THESES_SIMILARITY_REVIEW_REL,
    parse_report_text,
    theses_similarity_evidence_present,
)

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ABSOLUTE_PATH_RE = re.compile(r"(?<!\w)/(?:home|Users|tmp|var|workspace|mnt)/[^\s)\"']*")
WINDOWS_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s)\"']*")
EXPECTED_INTAKE_SOURCE_REFS = [THESES_SIMILARITY_REPORT_REL, THESES_SIMILARITY_EXTRACTED_TEXT_REL]
INTAKE_PARSED_FIELDS = (
    "report_evaluated_at_text",
    "compared_document",
    "overall_similarity",
    "source_documents",
    "matched_passages",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-theses-similarity-report",
        description="Validate imported Theses.cz similarity-report evidence when present.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def load_json_object(path: Path, rel_path: str, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"missing required Theses.cz similarity artifact: {rel_path}")
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{rel_path}: invalid JSON: {exc.msg}")
        return None
    if not isinstance(loaded, dict):
        errors.append(f"{rel_path}: JSON artifact must be an object")
        return None
    return loaded


def require_string(
    value: dict[str, Any], field: str, prefix: str, errors: list[str], *, allow_empty: bool = False
) -> str:
    item = value.get(field)
    if not isinstance(item, str) or (not allow_empty and not item.strip()):
        errors.append(f"{prefix}: {field} must be a string")
        return ""
    return item


def require_list(value: dict[str, Any], field: str, prefix: str, errors: list[str]) -> list[Any]:
    item = value.get(field)
    if not isinstance(item, list):
        errors.append(f"{prefix}: {field} must be a list")
        return []
    return item


def check_hash_bound_file(round_dir: Path, rel_path: str, recorded_hash: Any, prefix: str, errors: list[str]) -> None:
    path = round_dir / rel_path
    if not path.is_file():
        errors.append(f"{prefix}: referenced file is missing: {rel_path}")
        return
    if not isinstance(recorded_hash, str) or not SHA256_RE.fullmatch(recorded_hash):
        errors.append(f"{prefix}: sha256 must be a 64-character hex string")
        return
    if sha256_file(path) != recorded_hash:
        errors.append(f"{prefix}: sha256 is stale for {rel_path}")


def normalized_json(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))


def validate_file_record(
    round_dir: Path,
    loaded: dict[str, Any],
    field: str,
    expected_path: str,
    errors: list[str],
) -> None:
    prefix = f"{THESES_SIMILARITY_INTAKE_REL}: {field}"
    record = loaded.get(field)
    if not isinstance(record, dict):
        errors.append(f"{prefix} must be an object")
        return
    path_value = record.get("path")
    if path_value != expected_path:
        errors.append(f"{prefix}: path must be {expected_path}")
    check_hash_bound_file(round_dir, expected_path, record.get("sha256"), prefix, errors)
    if field == "report_pdf":
        page_count = record.get("page_count")
        if page_count is not None and (not isinstance(page_count, int) or page_count < 1):
            errors.append(f"{prefix}: page_count must be a positive integer or null")
    if field == "extracted_text" and record.get("extractor") != "pdftotext -layout":
        errors.append(f"{prefix}: extractor must be pdftotext -layout")


def validate_similarity_value(value: Any, prefix: str, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be an object or null")
        return
    require_string(value, "raw", prefix, errors)
    numeric = value.get("numeric_value")
    less_than = value.get("less_than")
    if numeric is not None and not isinstance(numeric, (int, float)):
        errors.append(f"{prefix}: numeric_value must be numeric or null")
    if less_than is not None and not isinstance(less_than, (int, float)):
        errors.append(f"{prefix}: less_than must be numeric or null")
    if numeric is not None and less_than is not None:
        errors.append(f"{prefix}: numeric_value and less_than must not both be set")


def validate_source_documents(loaded: dict[str, Any], errors: list[str]) -> set[int]:
    source_documents = require_list(loaded, "source_documents", THESES_SIMILARITY_INTAKE_REL, errors)
    ranks: set[int] = set()
    for index, item in enumerate(source_documents, start=1):
        prefix = f"{THESES_SIMILARITY_INTAKE_REL}: source_documents item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        rank = item.get("rank")
        if not isinstance(rank, int) or rank < 1:
            errors.append(f"{prefix}: rank must be a positive integer")
        elif rank in ranks:
            errors.append(f"{prefix}: duplicate rank {rank}")
        else:
            ranks.add(rank)
        for field in (
            "source_type",
            "title",
            "url_text",
            "changed_or_downloaded_text",
            "word_count_text",
        ):
            require_string(item, field, prefix, errors, allow_empty=True)
        validate_similarity_value(item.get("similarity"), f"{prefix}: similarity", errors)
        raw_lines = item.get("raw_lines")
        if not isinstance(raw_lines, list) or not all(isinstance(line, str) for line in raw_lines):
            errors.append(f"{prefix}: raw_lines must be a list of strings")
    return ranks


def validate_matched_passages(loaded: dict[str, Any], source_ranks: set[int], errors: list[str]) -> None:
    passages = require_list(loaded, "matched_passages", THESES_SIMILARITY_INTAKE_REL, errors)
    passage_ids: set[str] = set()
    for index, item in enumerate(passages, start=1):
        prefix = f"{THESES_SIMILARITY_INTAKE_REL}: matched_passages item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        passage_id = require_string(item, "passage_id", prefix, errors)
        if passage_id:
            if passage_id in passage_ids:
                errors.append(f"{prefix}: duplicate passage_id {passage_id}")
            passage_ids.add(passage_id)
        source_ids = require_list(item, "source_ids", prefix, errors)
        for source_index, source_id in enumerate(source_ids, start=1):
            if not isinstance(source_id, int):
                errors.append(f"{prefix}: source_ids item {source_index} must be an integer")
            elif source_ranks and source_id not in source_ranks:
                errors.append(f"{prefix}: source_ids item {source_index} references unknown source rank {source_id}")
        if not isinstance(item.get("report_line"), int):
            errors.append(f"{prefix}: report_line must be an integer")
        report_page = item.get("report_page")
        if report_page is not None and (not isinstance(report_page, int) or report_page < 1):
            errors.append(f"{prefix}: report_page must be a positive integer or null")
        require_string(item, "checked_document_ref", prefix, errors)
        limitations = require_list(item, "extraction_limitations", prefix, errors)
        if not all(isinstance(limitation, str) for limitation in limitations):
            errors.append(f"{prefix}: extraction_limitations must contain only strings")


def validate_intake(round_dir: Path, case_id: str, round_id: str, errors: list[str]) -> None:
    intake_path = round_dir / THESES_SIMILARITY_INTAKE_REL
    loaded = load_json_object(intake_path, THESES_SIMILARITY_INTAKE_REL, errors)
    if loaded is None:
        return
    if loaded.get("schema_version") != THESES_SIMILARITY_INTAKE_SCHEMA:
        errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: schema_version must be {THESES_SIMILARITY_INTAKE_SCHEMA}")
    if loaded.get("case_id") != case_id:
        errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: case_id does not match requested case")
    if loaded.get("round_id") != round_id:
        errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: round_id does not match requested round")
    for field in ("generated_at", "producer_type", "producer_role", "producer_agent"):
        require_string(loaded, field, THESES_SIMILARITY_INTAKE_REL, errors)
    if loaded.get("producer_type") != "deterministic_helper":
        errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: producer_type must be deterministic_helper")
    if loaded.get("producer_role") != "import-theses-report":
        errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: producer_role must be import-theses-report")
    if loaded.get("producer_agent") != "import-theses-report":
        errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: producer_agent must be import-theses-report")
    source_refs = require_list(loaded, "source_refs", THESES_SIMILARITY_INTAKE_REL, errors)
    string_source_refs: list[str] = []
    for index, ref in enumerate(source_refs, start=1):
        if not isinstance(ref, str) or not ref:
            errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: source_refs item {index} must be a non-empty string")
            continue
        if ref.startswith("/") or WINDOWS_PATH_RE.search(ref) or "\\" in ref:
            errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: source_refs item {index} must be round-relative")
        string_source_refs.append(ref)
    for rel_path in EXPECTED_INTAKE_SOURCE_REFS:
        if rel_path not in source_refs:
            errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: source_refs must include {rel_path}")
    for ref in sorted(set(string_source_refs) - set(EXPECTED_INTAKE_SOURCE_REFS)):
        errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: unexpected source_refs item {ref}")
    limitations = require_list(loaded, "limitations", THESES_SIMILARITY_INTAKE_REL, errors)
    if not all(isinstance(limitation, str) for limitation in limitations):
        errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: limitations must contain only strings")
    validate_file_record(round_dir, loaded, "report_pdf", THESES_SIMILARITY_REPORT_REL, errors)
    validate_file_record(round_dir, loaded, "extracted_text", THESES_SIMILARITY_EXTRACTED_TEXT_REL, errors)
    if loaded.get("current_submission_link") not in CURRENT_SUBMISSION_LINK_STATUSES:
        errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: current_submission_link has an unknown value")
    require_string(loaded, "report_evaluated_at_text", THESES_SIMILARITY_INTAKE_REL, errors, allow_empty=True)
    if not isinstance(loaded.get("compared_document"), dict):
        errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: compared_document must be an object")
    validate_similarity_value(
        loaded.get("overall_similarity"), f"{THESES_SIMILARITY_INTAKE_REL}: overall_similarity", errors
    )
    source_ranks = validate_source_documents(loaded, errors)
    validate_matched_passages(loaded, source_ranks, errors)
    report_text = round_dir / THESES_SIMILARITY_EXTRACTED_TEXT_REL
    if report_text.is_file():
        parsed = normalized_json(parse_report_text(report_text.read_text(encoding="utf-8", errors="replace")))
        for field in INTAKE_PARSED_FIELDS:
            if normalized_json(loaded.get(field)) != parsed.get(field):
                errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: parsed field {field} is stale")
    parser = loaded.get("parser")
    if not isinstance(parser, dict):
        errors.append(f"{THESES_SIMILARITY_INTAKE_REL}: parser must be an object")
    else:
        require_string(parser, "parser_name", f"{THESES_SIMILARITY_INTAKE_REL}: parser", errors)
        require_list(parser, "limitations", f"{THESES_SIMILARITY_INTAKE_REL}: parser", errors)


def validate_markdown_artifact(round_dir: Path, rel_path: str, errors: list[str]) -> bool:
    output = round_dir / rel_path
    if not output.is_file():
        return False
    text = output.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        errors.append(f"{rel_path}: output must not be empty")
    if ABSOLUTE_PATH_RE.search(text) or WINDOWS_PATH_RE.search(text):
        errors.append(f"{rel_path}: output contains an absolute filesystem path")
    if "cases/" in text:
        errors.append(f"{rel_path}: output contains an exact case workspace path")
    return True


def validate_markdown_outputs(round_dir: Path, errors: list[str]) -> None:
    validate_markdown_artifact(round_dir, THESES_SIMILARITY_REVIEW_DRAFT_REL, errors)
    final_output_present = validate_markdown_artifact(round_dir, THESES_SIMILARITY_REVIEW_REL, errors)
    if final_output_present and not (round_dir / THESES_SIMILARITY_ASSESSMENT_REL).is_file():
        errors.append(f"{THESES_SIMILARITY_REVIEW_REL}: assessment.json is required when the review output exists")


def validate_evidence(round_dir: Path, case_id: str, round_id: str) -> list[str]:
    errors: list[str] = []
    if not theses_similarity_evidence_present(round_dir):
        return errors
    for rel_path in (
        THESES_SIMILARITY_REPORT_REL,
        THESES_SIMILARITY_EXTRACTED_TEXT_REL,
        THESES_SIMILARITY_INTAKE_REL,
    ):
        if not (round_dir / rel_path).is_file():
            errors.append(f"missing required Theses.cz similarity artifact: {rel_path}")
    if (round_dir / THESES_SIMILARITY_INTAKE_REL).is_file():
        validate_intake(round_dir, case_id, round_id, errors)
    if (round_dir / THESES_SIMILARITY_ASSESSMENT_REL).is_file():
        errors.extend(
            validate_structured_evidence_artifact(
                round_dir,
                THESES_SIMILARITY_ASSESSMENT_REL,
                case_id=case_id,
                round_id=round_id,
            )
        )
    validate_markdown_outputs(round_dir, errors)
    if (round_dir / THESES_SIMILARITY_REVIEW_APPROVAL_REL).is_file():
        errors.extend(
            validate_review_approval_artifact(
                round_dir,
                THESES_SIMILARITY_REVIEW_APPROVAL_REL,
                case_id=case_id,
                round_id=round_id,
                reviewed_artifact_path=THESES_SIMILARITY_REVIEW_REL,
            )
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv[1:])
    validate_id("CASE_ID", args.case_id, stderr=True)
    root = repo_root()
    try:
        case_dir = require_case_dir(root, args.case_id, error_prefix="ERROR: ", stderr=True)
        round_id = resolve_round(case_dir, args.round_id, stderr=True)
        round_dir = require_round_dir(case_dir, args.case_id, round_id, error_prefix="ERROR: ", stderr=True)
    except SystemExit as exc:
        if exc.code == 2:
            return 2
        raise

    errors = validate_evidence(round_dir, args.case_id, round_id)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if theses_similarity_evidence_present(round_dir):
        print(f"Theses.cz similarity report check passed: {rel_repo(root, round_dir)}")
    else:
        print(f"No Theses.cz similarity report evidence present: {rel_repo(root, round_dir)}")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
