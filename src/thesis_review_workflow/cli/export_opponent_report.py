"""Export a calibrated opponent-report draft into the clean IS-entry proposal."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from thesis_review_workflow.cli.check_opponent_report import CLEAN_PROPOSAL, DEFAULT_DRAFT, SOURCE_METADATA_COMMENT_RE
from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.commands import command_display, repo_command_environment, resolve_repo_command
from thesis_review_workflow.paths import is_safe_round_relative_path, rel_repo

PRIVATE_CHECKLIST_HEADING = "## 12. Před odevzdáním"
DRAFT_STATUS_PREFIXES = ("Datum přípravy draftu:", "Stav:")


def run_required(root: Path, command: list[str]) -> None:
    result = subprocess.run(
        resolve_repo_command(root, command),
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=repo_command_environment(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = "\n".join(line for line in (result.stderr + result.stdout).splitlines() if line.strip())
        raise SystemExit(f"Required command failed: {command_display(command)}\n{detail}")


def is_safe_relative(value: str) -> bool:
    return is_safe_round_relative_path(value)


def clean_export_text(text: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    before_first_h2 = True
    skipping_private_checklist = False

    for line in lines:
        stripped = line.strip()
        if skipping_private_checklist:
            if stripped.startswith("## ") and stripped != PRIVATE_CHECKLIST_HEADING:
                skipping_private_checklist = False
            else:
                continue

        if stripped == PRIVATE_CHECKLIST_HEADING:
            skipping_private_checklist = True
            continue
        if SOURCE_METADATA_COMMENT_RE.match(line):
            continue
        if stripped.startswith("## "):
            before_first_h2 = False
        if before_first_h2 and any(line.startswith(prefix) for prefix in DRAFT_STATUS_PREFIXES):
            continue

        kept.append(line)

    while kept and not kept[-1].strip():
        kept.pop()
    return "\n".join(kept) + "\n"


def temp_output_rel(output_rel: str) -> str:
    output_path = Path(output_rel)
    return output_path.with_name(f".{output_path.name}.tmp").as_posix()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite an existing clean proposal")
    parser.add_argument("--source", default=DEFAULT_DRAFT.as_posix(), help="round-relative canonical draft path")
    parser.add_argument("--output", default=CLEAN_PROPOSAL.as_posix(), help="round-relative clean proposal path")
    parser.add_argument("--allow-alternate-output", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    args = parser.parse_args(argv[1:])

    validate_id("CASE_ID", args.case_id)
    if not is_safe_relative(args.source):
        print("ERROR: --source must be relative inside the round", file=sys.stderr)
        return 2
    if not is_safe_relative(args.output):
        print("ERROR: --output must be relative inside the round", file=sys.stderr)
        return 2
    if args.source == args.output:
        print("ERROR: --source and --output must be different round-relative paths", file=sys.stderr)
        return 2
    if args.output != CLEAN_PROPOSAL.as_posix() and not args.allow_alternate_output:
        print(
            "ERROR: export-opponent-report writes the canonical clean proposal path; "
            "alternate outputs require --allow-alternate-output",
            file=sys.stderr,
        )
        return 2

    root = repo_root()
    try:
        case_dir = require_case_dir(root, args.case_id, error_prefix="ERROR: ", stderr=True)
        round_id = resolve_round(case_dir, args.round_id, stderr=True)
        round_dir = require_round_dir(case_dir, args.case_id, round_id, error_prefix="ERROR: ", stderr=True)
    except SystemExit as exc:
        if exc.code == 2:
            return 2
        raise

    source_path = round_dir / args.source
    output_path = round_dir / args.output
    if not source_path.is_file():
        print(f"ERROR: Missing canonical opponent report draft: {args.source}", file=sys.stderr)
        return 1

    run_required(
        root,
        ["scripts/check-opponent-report", "--mode", "canonical", "--path", args.source, args.case_id, round_id],
    )

    exported = clean_export_text(source_path.read_text(encoding="utf-8"))
    temp_rel = temp_output_rel(args.output)
    temp_path = round_dir / temp_rel
    if output_path.exists():
        existing = output_path.read_text(encoding="utf-8")
        if existing != exported and not args.force:
            print(
                f"ERROR: Refusing to overwrite existing clean proposal without --force: {args.output}", file=sys.stderr
            )
            return 1

    temp_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        temp_path.write_text(exported, encoding="utf-8")
        run_required(
            root,
            ["scripts/check-opponent-report", "--mode", "canonical", "--path", args.source, args.case_id, round_id],
        )
        run_required(
            root,
            ["scripts/check-opponent-report", "--mode", "clean", "--path", temp_rel, args.case_id, round_id],
        )
        temp_path.replace(output_path)
        run_required(
            root,
            ["scripts/check-opponent-report", "--mode", "clean", "--path", args.output, args.case_id, round_id],
        )
    finally:
        if temp_path.exists():
            temp_path.unlink()
    print(f"Wrote {rel_repo(root, output_path)}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
