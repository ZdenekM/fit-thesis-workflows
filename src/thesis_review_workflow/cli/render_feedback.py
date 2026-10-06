"""Render reviewed student-facing supervisor feedback to an A4 PDF."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.feedback_render import (
    APPROVAL_PROFILE,
    FEEDBACK_REL,
    PDF_REL,
    PREVIEW_PDF_REL,
    RenderError,
    approval_errors,
    find_quarto,
    pdf_rendered_from,
    quarto_version,
    read_case_metadata,
    render_metadata,
    render_pdf,
    sha256_bytes,
)
from thesis_review_workflow.operation_log import append_operation
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.review_approvals import sha256_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/render-feedback",
        description=(
            f"Render the round's reviewed {FEEDBACK_REL} to {PDF_REL} for the student. "
            f"Requires Quarto and a valid {APPROVAL_PROFILE.approval_path}; the Markdown is not modified."
        ),
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--draft",
        action="store_true",
        help=(
            f"render without the review approval, stamped as a draft, to {PREVIEW_PDF_REL}; "
            "for operator preview only, never for sending"
        ),
    )
    parser.add_argument("--actor", default=os.environ.get("USER", "operator"))
    return parser


def remove_stale_pdf(round_dir: Path, reason: str) -> bool:
    """Remove `outputs/feedback_student.pdf`; False when it exists but cannot be removed.

    Called whenever no approval covers the current Markdown, and before every approved
    render, so a failed render never leaves an earlier version behind to be attached.
    """
    stale = round_dir / PDF_REL
    if not stale.is_file():
        return True
    try:
        stale.unlink()
    except OSError as exc:
        print(f"ERROR: cannot remove the stale {PDF_REL} (close it if it is open in a viewer): {exc}")
        return False
    if reason:
        print(f"Removed the stale {PDF_REL}: {reason}.")
    return True


def report_unapproved(errors: list[str]) -> None:
    print(f"ERROR: {FEEDBACK_REL} has no valid review approval; refusing to render it for sending:")
    for error in errors:
        print(f"- {error}")
    print("Re-run the supervisor-feedback review, or use --draft for a stamped operator preview.")


def passes_gate(round_dir: Path, args: argparse.Namespace, round_id: str, source_sha256: str) -> bool:
    """Apply the approval gate and keep `outputs/` honest in both modes.

    Unapproved Markdown: the PDF is removed and only `--draft` continues. Approved
    Markdown: a final render clears the PDF first, so a failed render leaves none; a draft
    keeps it only when the operation log shows it was rendered from these exact bytes.
    """
    errors = approval_errors(round_dir, case_id=args.case_id, round_id=round_id, source_sha256=source_sha256)
    if errors:
        if not remove_stale_pdf(round_dir, f"no approval covers the current {FEEDBACK_REL}"):
            return False
        if not args.draft:
            report_unapproved(errors)
        return bool(args.draft)
    if not args.draft:
        return remove_stale_pdf(round_dir, "")
    if pdf_rendered_from(round_dir, source_sha256):
        return True
    return remove_stale_pdf(round_dir, f"it was not rendered from the current {FEEDBACK_REL}")


def record_render(
    round_dir: Path, args: argparse.Namespace, round_id: str, output_rel: str, version: str, source_sha256: str
) -> None:
    kind = "a draft preview PDF" if args.draft else "a PDF for the student"
    append_operation(
        round_dir,
        case_id=args.case_id,
        round_id=round_id,
        operation="render-feedback",
        status="passed",
        actor=args.actor,
        summary=f"Rendered {FEEDBACK_REL} to {kind}.",
        command="render-feedback" + (" --draft" if args.draft else ""),
        artifacts=[FEEDBACK_REL, output_rel],
        details={
            "source_sha256": source_sha256,
            "pdf_sha256": sha256_file(round_dir / output_rel),
            "quarto_version": version,
            "draft": "true" if args.draft else "false",
        },
    )


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)

    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)
    source = round_dir / FEEDBACK_REL
    if not source.is_file():
        print(f"ERROR: missing {rel_repo(root, source)}; finish and review the feedback first.")
        remove_stale_pdf(round_dir, f"{FEEDBACK_REL} is missing")
        return 1
    source_bytes = source.read_bytes()
    source_sha256 = sha256_bytes(source_bytes)
    if not passes_gate(round_dir, args, round_id, source_sha256):
        return 1

    output_rel = PREVIEW_PDF_REL if args.draft else PDF_REL
    try:
        case_metadata = read_case_metadata(case_dir / "case.md")
        quarto = find_quarto()
        version = quarto_version(quarto)
        render_pdf(source_bytes, round_dir / output_rel, render_metadata(case_metadata, draft=args.draft), quarto)
    except RenderError as exc:
        print(f"ERROR: {exc}")
        return 1

    record_render(round_dir, args, round_id, output_rel, version, source_sha256)
    print(f"Rendered: {rel_repo(root, round_dir / output_rel)}")
    if args.draft:
        print("Draft preview only: it carries a visible draft stamp and must not be sent.")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
