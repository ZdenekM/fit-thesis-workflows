"""Record a submitted opponent-report PDF and bind it to reviewed state."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.operation_log import append_operation
from thesis_review_workflow.paths import rel_repo, resolve_caller_path
from thesis_review_workflow.submitted_reports import (
    OPPONENT_REPORT_SUBMITTED_PDF_REL,
    OPPONENT_REPORT_SUBMITTED_RECORD_REL,
    OPPONENT_REPORT_SUBMITTED_TEXT_REL,
    build_opponent_submitted_report_payload,
    copy_or_extract_public_text,
    copy_submitted_pdf,
    validate_submitted_opponent_report_record,
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/record-submitted-opponent-report",
        description=(
            "Copy the submitted opponent-report PDF into the ignored round workspace and record "
            "a hash-bound comparison against the reviewed clean IS-entry proposal."
        ),
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument("--pdf", required=True, help="submitted opponent report PDF")
    parser.add_argument(
        "--public-text-file",
        default="",
        help=(
            "optional canonical public-text transcription using the clean opponent-report Markdown headings; "
            "if omitted, pdftotext -layout is attempted and may fail archive parsing on raw IS layout"
        ),
    )
    parser.add_argument("--recorded-by", required=True, help="operator identity for the submitted report record")
    parser.add_argument("--submitted-at", default="", help="ISO timestamp; defaults to current UTC time")
    parser.add_argument("--force", action="store_true", help="overwrite existing submitted-report artifacts")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)
    root = repo_root()
    copied_rels: list[str] = []
    try:
        case_dir = require_case_dir(root, args.case_id)
        round_id = resolve_round(case_dir, args.round_id)
        round_dir = require_round_dir(case_dir, args.case_id, round_id)
        pdf_rel = copy_submitted_pdf(
            resolve_caller_path(args.pdf),
            round_dir,
            force=args.force,
            target_rel=OPPONENT_REPORT_SUBMITTED_PDF_REL,
        )
        copied_rels.append(pdf_rel)
        public_text_file = resolve_caller_path(args.public_text_file) if args.public_text_file else None
        public_text_rel = copy_or_extract_public_text(
            pdf_path=round_dir / pdf_rel,
            round_dir=round_dir,
            public_text_file=public_text_file,
            force=args.force,
            target_rel=OPPONENT_REPORT_SUBMITTED_TEXT_REL,
        )
        copied_rels.append(public_text_rel)
        payload = build_opponent_submitted_report_payload(
            round_dir,
            case_id=args.case_id,
            round_id=round_id,
            submitted_at=args.submitted_at or now_utc(),
            recorded_by=args.recorded_by,
            pdf_rel=pdf_rel,
            public_text_rel=public_text_rel,
        )
        errors = validate_submitted_opponent_report_record(
            payload,
            round_dir=round_dir,
            case_id=args.case_id,
            round_id=round_id,
            rel_path=OPPONENT_REPORT_SUBMITTED_RECORD_REL,
            require_archive_ready=False,
        )
        if errors:
            raise ValueError("\n".join(errors))
        output = round_dir / OPPONENT_REPORT_SUBMITTED_RECORD_REL
        if output.exists() and not args.force:
            raise ValueError(
                f"refusing to overwrite existing submitted-report record without --force: "
                f"{OPPONENT_REPORT_SUBMITTED_RECORD_REL}"
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        append_operation(
            round_dir,
            case_id=args.case_id,
            round_id=round_id,
            operation="submitted-opponent-report-capture",
            status="passed",
            actor=args.recorded_by,
            summary="Recorded submitted opponent report PDF, extracted public text, and archive-readiness record.",
            command=f"record-submitted-opponent-report {args.case_id} {round_id}",
            artifacts=[pdf_rel, public_text_rel, OPPONENT_REPORT_SUBMITTED_RECORD_REL],
            checks=["check-opponent-report:clean"],
        )
    except (OSError, ValueError) as exc:
        if "round_dir" in locals() and not args.force:
            for rel in reversed(copied_rels):
                (round_dir / rel).unlink(missing_ok=True)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {rel_repo(root, output)}")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
