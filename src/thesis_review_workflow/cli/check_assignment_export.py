"""Check assignment PDFs exported from FIT IS before submitting them for approval."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from thesis_review_workflow.assignment_draft import RENDERINGS
from thesis_review_workflow.assignment_export import ExportCheck, check_export
from thesis_review_workflow.paths import resolve_caller_path
from thesis_review_workflow.pdf_extracts import PDF_EXTRACT_ARGS, PDF_EXTRACT_COMMAND


class ExtractionError(RuntimeError):
    """`pdftotext` could not read the PDF."""


def layout_text(executable: str, pdf: Path) -> str:
    """The `pdftotext -layout` text of `pdf`, decoded from explicit UTF-8 rather than the console code page."""

    result = subprocess.run(
        [executable, *PDF_EXTRACT_ARGS, "-enc", "UTF-8", str(pdf), "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ExtractionError(detail or f"{PDF_EXTRACT_COMMAND} exited with {result.returncode}")
    return result.stdout.decode("utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-assignment-export",
        description=(
            "Check assignment PDFs exported from FIT IS: one page, a recognised header, a title, the points as "
            "a numbered list, the literature as a bullet list, and a filled semestral field."
        ),
    )
    parser.add_argument("pdfs", nargs="+", metavar="pdf", help="Assignment PDF exported from FIT IS.")
    parser.add_argument(
        "--language",
        choices=sorted(RENDERINGS),
        help="Require this rendering: the CZ/EN switch at the end of the FIT IS form, set to the thesis language.",
    )
    parser.add_argument(
        "--allow-empty-semestral",
        action="store_true",
        help=(
            "Accept an empty semestral field, for a student who passed the first semester in the previous "
            "academic year. It applies to every PDF of the run, so pass it with that student's export only."
        ),
    )
    return parser


def describe(check: ExportCheck) -> str:
    pages = f"{check.pages} page" + ("" if check.pages == 1 else "s")
    if check.rendering is None or check.variant is None:
        return pages
    return f"{check.rendering.titles[check.variant]} ({check.rendering.key}), {pages}"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    executable = shutil.which(PDF_EXTRACT_COMMAND)
    if executable is None:
        print(f"ERROR: Missing required command: {PDF_EXTRACT_COMMAND}; scripts/check-tooling reports it")
        return 1

    failed = 0
    for value in args.pdfs:
        pdf = resolve_caller_path(value)
        if not pdf.is_file():
            print(f"ERROR: {value}: no such file")
            failed += 1
            continue
        try:
            text = layout_text(executable, pdf)
        except ExtractionError as error:
            print(f"ERROR: {value}: {PDF_EXTRACT_COMMAND} failed: {error}")
            failed += 1
            continue
        check = check_export(text, language=args.language, allow_empty_semestral=args.allow_empty_semestral)
        print(f"{value}: {describe(check)}")
        for note in check.notes:
            print(f"NOTE: {value}: {note}")
        for finding in check.findings:
            print(f"ERROR: {value}: {finding}")
        if check.findings:
            failed += 1

    if args.language is None:
        print("Rendering not compared with the thesis language; pass `--language cs` or `--language en`.")
    print("Not visible in the export, confirm in FIT IS: `Zobrazit studentům` is ticked.")
    if failed:
        print(
            f"Assignment export check failed for {failed} of {len(args.pdfs)} file(s). Wording, the title and "
            "literature currency stay with .agents/skills/thesis-assignment-review/SKILL.md."
        )
        return 1
    print(f"Assignment export check passed for {len(args.pdfs)} file(s)")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
