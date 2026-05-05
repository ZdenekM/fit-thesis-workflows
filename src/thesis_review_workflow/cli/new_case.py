"""Create a new private thesis case and its first round."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from thesis_review_workflow.cases import repo_root
from thesis_review_workflow.commands import run_step
from thesis_review_workflow.ids import validate_id


def usage() -> str:
    return (
        "Usage: scripts/new-case CASE_ID [WORK_TYPE] [ROUND_LABEL]\n\n"
        "Creates a local gitignored thesis case under cases/ and starts its first round.\n\n"
        "Examples:\n"
        "  scripts/new-case novak-bp-2026 BP first-review\n"
        "  scripts/new-case dp-semantic-search DP"
    )


def replace_field(path: Path, field: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = [f"{field}: {value}" if line.startswith(f"{field}:") else line for line in lines]
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/new-case",
        description="Create a private thesis case and initialize the first round.",
    )
    parser.add_argument("case_id")
    parser.add_argument("work_type", nargs="?", default="unknown")
    parser.add_argument("round_label", nargs="?", default="round-01")
    return parser


def main(argv: list[str]) -> int:
    if any(arg in {"-h", "--help"} for arg in argv[1:]):
        print(usage())
        return 0
    parser = build_parser()
    args = parser.parse_args(argv[1:])

    try:
        validate_id("CASE_ID", args.case_id)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    root = repo_root()
    case_dir = root / "cases" / args.case_id
    if case_dir.exists():
        print(f"Case already exists: cases/{args.case_id}", file=sys.stderr)
        return 1

    case_dir.mkdir(parents=True)
    (case_dir / "rounds").mkdir()
    try:
        shutil.copy2(root / "templates" / "case-notes.md", case_dir / "case.md")
        replace_field(case_dir / "case.md", "Case ID", args.case_id)
        replace_field(case_dir / "case.md", "Work type", args.work_type)
        replace_field(case_dir / "case.md", "Deadline mode", "standard")
        step = run_step(root, "initial round", ["scripts/import-round", args.case_id, args.round_label])
        if not step.ok:
            if step.output:
                print(step.output, file=sys.stderr)
            shutil.rmtree(case_dir, ignore_errors=True)
            return step.returncode
    except BaseException:
        shutil.rmtree(case_dir, ignore_errors=True)
        raise

    current_round = (case_dir / "current-round.txt").read_text(encoding="utf-8").strip()
    print(f"Created case: cases/{args.case_id}")
    print(f"Current round: {current_round}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
