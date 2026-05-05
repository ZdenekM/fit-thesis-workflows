"""Extract thesis PDF text into the ignored case workspace."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from thesis_review_workflow.cases import repo_root


def usage() -> str:
    return (
        "Usage: scripts/extract-pdf-text INPUT.pdf OUTPUT.txt\n\n"
        "Extracts text with pdftotext. Install Poppler if pdftotext is missing."
    )


def is_allowed_extract_path(root: Path, output: Path) -> bool:
    try:
        rel = output.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    parts = rel.parts
    return len(parts) >= 6 and parts[0] == "cases" and parts[2] == "rounds" and parts[4] == "extracted"


def git_ignored(root: Path, rel: str) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", rel],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/extract-pdf-text",
        description="Extract text from a thesis PDF into cases/<case>/rounds/<round>/extracted/.",
    )
    parser.add_argument("input_pdf")
    parser.add_argument("output_txt")
    return parser


def main(argv: list[str]) -> int:
    if any(arg in {"-h", "--help"} for arg in argv[1:]):
        print(usage())
        return 0
    parser = build_parser()
    args = parser.parse_args(argv[1:])

    if shutil.which("pdftotext") is None:
        print("Missing required command: pdftotext", file=sys.stderr)
        return 1

    root = repo_root()
    input_pdf = Path(args.input_pdf).expanduser()
    output_txt = Path(args.output_txt).expanduser()
    if not input_pdf.is_file():
        print(f"Input PDF does not exist: {args.input_pdf}", file=sys.stderr)
        return 1

    output_txt.parent.mkdir(parents=True, exist_ok=True)
    output_abs = output_txt.resolve()
    if not is_allowed_extract_path(root, output_abs):
        print(
            "Refusing to write extracted thesis text outside cases/<case>/rounds/<round>/extracted/.",
            file=sys.stderr,
        )
        return 1
    output_rel = output_abs.relative_to(root.resolve()).as_posix()
    if not git_ignored(root, output_rel):
        print(f"Refusing to write extracted thesis text to a non-ignored path: {output_rel}", file=sys.stderr)
        return 1

    result = subprocess.run(
        ["pdftotext", "-layout", str(input_pdf), str(output_txt)],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = "\n".join(part for part in (result.stderr.strip(), result.stdout.strip()) if part)
        if detail:
            print(detail, file=sys.stderr)
        return result.returncode
    print(f"Extracted text: {output_txt}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
