"""Record an operator-supplied FIT Theses Checker summary."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
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
from thesis_review_workflow.paths import is_safe_round_relative_path, rel_repo
from thesis_review_workflow.theses_checker_summary import (
    CHECKED_PDF_LIMITATION_TYPES,
    SOURCE_KINDS,
    SUMMARY_STATUSES,
    THESES_CHECKER_SUMMARY_REL,
    THESES_CHECKER_SUMMARY_SCHEMA,
    validate_theses_checker_summary_payload,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_round_path(value: str, *, label: str) -> str:
    normalized = Path(value).as_posix()
    if not is_safe_round_relative_path(normalized):
        raise SystemExit(f"ERROR: {label} must be relative inside the round")
    if not normalized.startswith(("inputs/", "extracted/", "notes/", "work/", "outputs/")):
        raise SystemExit(f"ERROR: {label} must be under inputs/, extracted/, notes/, work/, or outputs/")
    return normalized


def hash_record(round_dir: Path, rel_path: str) -> dict[str, str]:
    path = round_dir / rel_path
    if not path.is_file():
        raise SystemExit(f"ERROR: referenced file is missing: {rel_path}")
    return {"path": rel_path, "sha256": sha256_file(path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/record-theses-checker-summary",
        description="Normalize operator-supplied FIT Theses Checker output into work/theses_checker_summary.json.",
    )
    parser.add_argument("--source", required=True, help="round-relative saved/exported/copied checker output")
    parser.add_argument("--source-kind", choices=sorted(SOURCE_KINDS), default="operator_transcript")
    parser.add_argument("--checked-pdf", help="round-relative rendered thesis PDF checked by FIT Theses Checker")
    parser.add_argument("--checked-pdf-limitation", choices=sorted(CHECKED_PDF_LIMITATION_TYPES))
    parser.add_argument("--checked-pdf-limitation-note")
    parser.add_argument("--accepted-by", default="operator", help="who accepted a missing checked-PDF binding")
    parser.add_argument("--normostrany", required=True, type=float)
    parser.add_argument("--status", required=True, choices=sorted(SUMMARY_STATUSES))
    parser.add_argument("--minimum", type=float)
    parser.add_argument("--recommended-minimum", type=float)
    parser.add_argument("--maximum", type=float)
    parser.add_argument("--checker-timestamp")
    parser.add_argument("--captured-at")
    parser.add_argument("--limitation", action="append", default=[])
    parser.add_argument("--force", action="store_true", help="overwrite an existing summary")
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def payload_from_args(args: argparse.Namespace, round_dir: Path, round_id: str) -> dict[str, Any]:
    source_rel = safe_round_path(args.source, label="--source")
    source = hash_record(round_dir, source_rel)
    source["kind"] = args.source_kind
    source_refs = [source_rel]

    checked_pdf = None
    checked_pdf_limitation = None
    if args.checked_pdf:
        checked_pdf_rel = safe_round_path(args.checked_pdf, label="--checked-pdf")
        checked_pdf = hash_record(round_dir, checked_pdf_rel)
        source_refs.append(checked_pdf_rel)
        if args.checked_pdf_limitation or args.checked_pdf_limitation_note:
            raise SystemExit("ERROR: checked-PDF limitation arguments cannot be used with --checked-pdf")
    else:
        if not args.checked_pdf_limitation or not args.checked_pdf_limitation_note:
            raise SystemExit(
                "ERROR: provide --checked-pdf or both --checked-pdf-limitation and --checked-pdf-limitation-note"
            )
        checked_pdf_limitation = {
            "type": args.checked_pdf_limitation,
            "description": args.checked_pdf_limitation_note,
            "accepted_by": args.accepted_by,
        }

    thresholds = {
        key: value
        for key, value in (
            ("minimum", args.minimum),
            ("recommended_minimum", args.recommended_minimum),
            ("maximum", args.maximum),
        )
        if value is not None
    }

    return {
        "schema_version": THESES_CHECKER_SUMMARY_SCHEMA,
        "case_id": args.case_id,
        "round_id": round_id,
        "generated_at": utc_now(),
        "producer_type": "deterministic_helper",
        "producer_role": "record-theses-checker-summary",
        "producer_agent": "record-theses-checker-summary",
        "source_refs": source_refs,
        "source_artifact": source,
        "checked_pdf": checked_pdf,
        "checked_pdf_limitation": checked_pdf_limitation,
        "normostrany": args.normostrany,
        "thresholds": thresholds,
        "status": args.status,
        "checker_timestamp": args.checker_timestamp,
        "captured_at": args.captured_at or utc_now(),
        "limitations": args.limitation,
    }


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)

    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    output_path = round_dir / THESES_CHECKER_SUMMARY_REL
    if output_path.exists() and not args.force:
        print(f"ERROR: Refusing to overwrite existing summary without --force: {THESES_CHECKER_SUMMARY_REL}")
        return 1

    payload = payload_from_args(args, round_dir, round_id)
    errors = validate_theses_checker_summary_payload(
        payload,
        THESES_CHECKER_SUMMARY_REL,
        round_dir=round_dir,
        case_id=args.case_id,
        round_id=round_id,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {rel_repo(root, output_path)}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
