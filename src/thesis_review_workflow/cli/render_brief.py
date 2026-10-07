"""Render an approved topic brief projection to an A4 PDF for the student."""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

from thesis_review_workflow import pdf_render
from thesis_review_workflow.assignment_bundle import assignment_formal_rel, brief_projection_rel
from thesis_review_workflow.assignment_draft import VARIANT_RE
from thesis_review_workflow.brief_render import (
    approval_errors,
    brief_case,
    exact_entry,
    find_quarto,
    official_title,
    pdf_rel,
    pdf_rendered_from,
    preview_pdf_rel,
    read_bound,
    render_pdf,
    render_values,
    require_topic_case,
    write_render_record,
)
from thesis_review_workflow.cli.context import repo_root, require_case_dir, validate_id
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.pdf_render import RenderError, quarto_version


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/render-brief",
        description=(
            "Render a topic case's approved outputs/student_brief_<variant>.md to "
            "outputs/student_brief_<variant>.pdf for the student. Requires Quarto and a bundle "
            "approval that scripts/check-assignment-bundle accepts; the Markdown is not modified."
        ),
    )
    parser.add_argument("case_id", help="the topic-proposal case")
    parser.add_argument("variant", help="the assignment variant, for example bp or dp")
    parser.add_argument(
        "--draft",
        action="store_true",
        help=(
            "render without the bundle approval, stamped as a draft, to "
            "work/student_brief_<variant>_preview.pdf; for operator preview only, never for sending"
        ),
    )
    return parser


def passes_gate(case_dir: Path, args: argparse.Namespace, read: dict[str, bytes]) -> tuple[bool, str]:
    """Apply the approval gate and keep `outputs/` honest in both modes.

    Unapproved Markdown: the PDF is removed and only `--draft` continues. Approved Markdown:
    a final render clears the PDF first, so a failed render leaves none; a draft keeps it
    only when its render record shows it was rendered under this exact approval. Returns
    whether to continue and the approval record's hash ("" when nothing approves).
    """
    output_rel = pdf_rel(args.variant)
    brief_rel = brief_projection_rel(args.variant)
    errors, approval_sha256 = approval_errors(case_dir, case_id=args.case_id, variant=args.variant, read=read)
    if errors:
        if not pdf_render.remove_stale_pdf(case_dir, output_rel, f"no bundle approval covers the current {brief_rel}"):
            return False, ""
        if not args.draft:
            print(f"ERROR: {brief_rel} has no valid bundle approval; refusing to render it:")
            for error in errors:
                print(f"- {error}")
            print("Finish the assignment review, or use --draft for a stamped operator preview.")
        return bool(args.draft), ""
    if not args.draft:
        return pdf_render.remove_stale_pdf(case_dir, output_rel, ""), approval_sha256
    if pdf_rendered_from(case_dir, args.variant, approval_sha256):
        return True, approval_sha256
    reason = "it was not rendered under the current bundle approval"
    return pdf_render.remove_stale_pdf(case_dir, output_rel, reason), approval_sha256


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    validate_id("CASE_ID", args.case_id)
    if not VARIANT_RE.fullmatch(args.variant):
        print(f"ERROR: unusable variant identifier: {args.variant!r}")
        return 2

    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    try:
        fields = require_topic_case(case_dir)
    except RenderError as exc:
        print(f"ERROR: {exc}")
        return 1
    source = case_dir / brief_projection_rel(args.variant)
    if not exact_entry(source):
        print(f"ERROR: missing {rel_repo(root, source)} (spelled exactly so); author and review the brief first.")
        if exact_entry(case_dir / pdf_rel(args.variant)):
            pdf_render.remove_stale_pdf(
                case_dir, pdf_rel(args.variant), f"{brief_projection_rel(args.variant)} is missing"
            )
        return 1
    read = read_bound(case_dir, args.variant)
    proceed, approval_sha256 = passes_gate(case_dir, args, read)
    if not proceed:
        return 1

    output_rel = preview_pdf_rel(args.variant) if args.draft else pdf_rel(args.variant)
    try:
        case = brief_case(fields, case_dir.name)
        quarto = find_quarto(args.variant)
        version = quarto_version(quarto)
        topic = official_title(read[assignment_formal_rel(args.variant)].decode("utf-8", errors="replace"))
        values = render_values(case, args.variant, topic=topic, today=datetime.date.today(), draft=args.draft)
        render_pdf(read[brief_projection_rel(args.variant)], case_dir / output_rel, values, quarto)
        if not args.draft:
            write_render_record(
                case_dir, case_id=args.case_id, variant=args.variant, approval_sha256=approval_sha256, version=version
            )
    except (RenderError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Rendered: {rel_repo(root, case_dir / output_rel)} (Quarto {version})")
    if args.draft:
        print("Draft preview only: it carries a visible draft stamp and must not be sent.")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
