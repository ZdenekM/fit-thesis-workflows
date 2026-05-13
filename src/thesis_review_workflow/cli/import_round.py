"""Create a new private thesis round and import submitted inputs."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from thesis_review_workflow.cases import repo_root
from thesis_review_workflow.commands import run_step
from thesis_review_workflow.ids import validate_id
from thesis_review_workflow.paths import resolve_caller_path


def usage() -> str:
    return (
        "Usage: scripts/import-round CASE_ID ROUND_LABEL [INPUT_PATH ...]\n\n"
        "Creates a new timestamped round and optionally copies thesis/code artifacts into inputs/.\n"
        "INPUT_PATH can be a file or directory. Paths are copied by basename.\n\n"
        "Examples:\n"
        "  scripts/import-round novak-bp-2026 second-review thesis.pdf student-code.zip\n"
        "  scripts/import-round novak-bp-2026 final-check ~/Downloads/thesis.pdf ~/Downloads/repo"
    )


def safe_label(value: str) -> str:
    label = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return label


def replace_field(path: Path, field: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = [f"{field}: {value}" if line.startswith(f"{field}:") else line for line in lines]
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def copy_input(source: Path, destination_dir: Path) -> None:
    destination = destination_dir / source.name
    if source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
    elif source.is_file():
        shutil.copy2(source, destination)
    else:
        raise RuntimeError(f"Unsupported input path type: {source}")


def previous_feedback_paths(root: Path, case_dir: Path, excluded_round_dir: Path) -> list[str]:
    rounds = case_dir / "rounds"
    if not rounds.is_dir():
        return []
    paths: list[str] = []
    for feedback in rounds.glob("*/outputs/feedback_student.md"):
        try:
            feedback.relative_to(excluded_round_dir)
            continue
        except ValueError:
            pass
        paths.append(feedback.relative_to(root).as_posix())
    return sorted(paths)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/import-round",
        description="Create a new private thesis round and optionally copy input artifacts.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_label")
    parser.add_argument("inputs", nargs="*")
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
    label = safe_label(args.round_label)
    if not label:
        print("ROUND_LABEL must contain at least one letter, number, dot, underscore, or dash.", file=sys.stderr)
        return 2

    root = repo_root()
    case_dir = root / "cases" / args.case_id
    if not case_dir.is_dir():
        print(f"Case does not exist: cases/{args.case_id}", file=sys.stderr)
        print(f"Create it first with: scripts/new-case {args.case_id}", file=sys.stderr)
        return 1

    input_paths: list[Path] = []
    target_basenames: dict[str, Path] = {}
    for raw in args.inputs:
        path = resolve_caller_path(raw)
        if not path.exists():
            print(f"Input path does not exist: {raw}", file=sys.stderr)
            return 1
        key = path.name.casefold()
        if key in target_basenames:
            print(f"Multiple inputs would copy to the same basename on Windows: {path.name}", file=sys.stderr)
            return 1
        target_basenames[key] = path
        input_paths.append(path)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    round_id = f"{timestamp}-{label}"
    round_dir = case_dir / "rounds" / round_id
    tmp_round_dir = case_dir / "rounds" / f".tmp-{round_id}-{os.getpid()}"
    if round_dir.exists():
        print(f"Round already exists: cases/{args.case_id}/rounds/{round_id}", file=sys.stderr)
        return 1
    if tmp_round_dir.exists():
        print(f"Temporary round directory already exists: {tmp_round_dir}", file=sys.stderr)
        return 1

    try:
        for subdir in ("notes", "inputs", "extracted", "work", "outputs"):
            (tmp_round_dir / subdir).mkdir(parents=True, exist_ok=True)

        for template in (
            "round-notes.md",
            "assignment.md",
            "supervisor-intake.md",
            "opponent-intake.md",
            "opponent-report-review-intake.md",
        ):
            shutil.copy2(root / "templates" / template, tmp_round_dir / "notes" / template)
        replace_field(tmp_round_dir / "notes" / "round-notes.md", "Round", round_id)
        replace_field(tmp_round_dir / "notes" / "round-notes.md", "Date", datetime.now().strftime("%Y-%m-%d"))

        for source in input_paths:
            copy_input(source, tmp_round_dir / "inputs")
            if source.is_file() and source.suffix.casefold() == ".pdf":
                copied_pdf = tmp_round_dir / "inputs" / source.name
                output = tmp_round_dir / "extracted" / f"{source.stem}.txt"
                step = run_step(root, "PDF text extraction", ["scripts/extract-pdf-text", str(copied_pdf), str(output)])
                if step.ok:
                    print(f"Extracted PDF text: extracted/{output.name}")
                else:
                    output.unlink(missing_ok=True)
                    print(
                        f"PDF text extraction failed for {source.name}; keep the PDF in inputs/ "
                        "and note the limitation.",
                        file=sys.stderr,
                    )

        index = tmp_round_dir / "notes" / "previous-feedback-index.md"
        lines = [
            "# Previous Feedback Index",
            "",
            "Use these artifacts when preparing iterative supervisor feedback.",
            "",
            *[f"- {path}" for path in previous_feedback_paths(root, case_dir, round_dir)],
        ]
        index.write_text("\n".join(lines) + "\n", encoding="utf-8")

        shutil.move(str(tmp_round_dir), str(round_dir))
        (case_dir / "current-round.txt").write_text(round_id + "\n", encoding="utf-8")
    except BaseException:
        shutil.rmtree(tmp_round_dir, ignore_errors=True)
        raise

    print(f"Created round: cases/{args.case_id}/rounds/{round_id}")
    if input_paths:
        print(f"Copied inputs: {len(input_paths)}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
