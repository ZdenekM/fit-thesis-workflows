"""Check student-feedback heading language against case metadata."""

from __future__ import annotations

import argparse
import sys

from thesis_review_workflow.cases import MissingCurrentRound, repo_root, resolve_round
from thesis_review_workflow.metadata import read_fields

CS_REQUIRED_HEADINGS = [
    "# Zpětná vazba k aktuální verzi práce",
    "## Krátké celkové shrnutí",
    "## Rozsah kontroly",
    "## Odhad fáze práce a doporučené zaměření",
    "## Co se od minulé verze posunulo",
    "## Co je na práci už dobré",
    "## Nejvyšší priority pro aktuální iteraci",
    "## Splnění zadání",
    "## Připomínky k textu práce",
    "## Soulad textu s kódem",
    "## Co z minulé zpětné vazby zůstává",
    "## Doporučený plán dalších úprav",
    "## Checklist pro aktuální fázi",
]
CS_ASCII_REJECT_HEADINGS = [
    "# Zpetna vazba k aktualni verzi prace",
    "## Kratke celkove shrnuti",
    "## Odhad faze prace a doporucene zamereni",
    "## Co se od minule posunulo",
    "## Co se od minule verze posunulo",
    "## Co je na praci uz dobre",
    "## Nejvyssi priority pro aktualni iteraci",
    "## Splneni zadani",
    "## Pripominky k textu prace",
    "## Soulad textu s kodem",
    "## Co z minule zpetne vazby zustava",
    "## Doporuceny plan dalsich uprav",
    "## Checklist pro aktualni fazi",
]
EN_REQUIRED_HEADINGS = [
    "# Feedback on the Current Thesis Version",
    "## Brief Overall Summary",
    "## Review Scope",
    "## Estimated Work Phase and Recommended Focus",
    "## Progress Since Previous Feedback",
    "## What Is Already Working Well",
    "## Highest Priorities for This Iteration",
    "## Assignment Fulfillment",
    "## Thesis Text Feedback",
    "## Text-Code Alignment",
    "## Remaining Items From Previous Feedback",
    "## Recommended Next Revision Plan",
    "## Checklist for the Current Phase",
]


def usage() -> str:
    return (
        "Usage: scripts/check-feedback-language [--config-only] CASE_ID [ROUND_ID]\n\n"
        "Checks outputs/feedback_student.md heading structure against Student feedback language in case.md.\n"
        "Use --config-only to validate case.md before feedback output exists."
    )


def report_missing(label: str, headings: list[str], existing: set[str], errors: list[str]) -> None:
    missing = [heading for heading in headings if heading not in existing]
    if missing:
        errors.append(label)
        errors.extend(f"- {heading}" for heading in missing)


def report_present(label: str, headings: list[str], existing: set[str], errors: list[str]) -> None:
    present = [heading for heading in headings if heading in existing]
    if present:
        errors.append(label)
        errors.extend(f"- {heading}" for heading in present)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-feedback-language",
        description="Check feedback heading language against case metadata.",
    )
    parser.add_argument("--config-only", action="store_true")
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def main(argv: list[str]) -> int:
    if any(arg in {"-h", "--help"} for arg in argv[1:]):
        print(usage())
        return 0
    parser = build_parser()
    args = parser.parse_args(argv[1:])

    root = repo_root()
    case_dir = root / "cases" / args.case_id
    if not case_dir.is_dir():
        print(f"Case does not exist: cases/{args.case_id}", file=sys.stderr)
        return 1
    case_md = case_dir / "case.md"
    if not case_md.is_file():
        print(f"Missing case metadata: cases/{args.case_id}/case.md", file=sys.stderr)
        return 1

    language = read_fields(case_md).get("student feedback language", "cs").lower() or "cs"
    if language not in {"cs", "en"}:
        print(
            f"Unsupported Student feedback language in case.md: '{language}'. Expected 'cs' or 'en'.",
            file=sys.stderr,
        )
        return 1
    if args.config_only:
        print(f"Feedback language config OK: {language}")
        return 0

    try:
        round_id = resolve_round(case_dir, args.round_id)
    except MissingCurrentRound:
        print(f"Missing current round: cases/{args.case_id}/current-round.txt", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    round_dir = case_dir / "rounds" / round_id
    if not round_dir.is_dir():
        print(f"Round does not exist: cases/{args.case_id}/rounds/{round_id}", file=sys.stderr)
        return 1
    feedback = round_dir / "outputs" / "feedback_student.md"
    if not feedback.is_file():
        print(
            f"Missing feedback output: cases/{args.case_id}/rounds/{round_id}/outputs/feedback_student.md",
            file=sys.stderr,
        )
        return 1

    existing = set(feedback.read_text(encoding="utf-8").splitlines())
    errors: list[str] = []
    if language == "cs":
        report_missing("Missing Czech headings with diacritics:", CS_REQUIRED_HEADINGS, existing, errors)
        report_present("Found ASCII-only Czech headings:", CS_ASCII_REJECT_HEADINGS, existing, errors)
        report_present("Found English headings in Czech feedback:", EN_REQUIRED_HEADINGS, existing, errors)
    else:
        report_missing("Missing English headings:", EN_REQUIRED_HEADINGS, existing, errors)
        report_present(
            "Found Czech headings in English feedback:",
            [*CS_REQUIRED_HEADINGS, *CS_ASCII_REJECT_HEADINGS],
            existing,
            errors,
        )
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Feedback language check passed: {language}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
