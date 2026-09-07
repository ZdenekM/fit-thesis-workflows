"""Create a new private thesis round and import submitted inputs."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath

from thesis_review_workflow.cases import repo_root
from thesis_review_workflow.commands import run_step
from thesis_review_workflow.ids import validate_id
from thesis_review_workflow.paths import resolve_caller_path
from thesis_review_workflow.input_provenance import (
    InputRequest,
    StoredInput,
    directory_input_record,
    normalize_input_name,
    plan_input_storage,
    write_input_provenance,
)
from thesis_review_workflow.round_scaffolding import round_kinds, skipped_for_kind, templates_for_kind


def usage() -> str:
    return (
        "Usage: scripts/import-round [--kind KIND] CASE_ID ROUND_LABEL [INPUT_PATH ...]\n\n"
        "Creates a new timestamped round and optionally copies thesis/code artifacts into inputs/.\n"
        "INPUT_PATH can be a file or directory. Stored names are normalized, identical file\n"
        "content is stored once, and work/input_provenance.json records where each original went.\n"
        f"KIND is one of {', '.join(round_kinds())} and decides which notes templates the round\n"
        "is scaffolded with; omitted, the round gets every intake template as before. Do not place\n"
        "--kind between input paths.\n\n"
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


def copy_input(source: Path, destination: Path) -> None:
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
    parser.add_argument(
        "--kind",
        choices=round_kinds(),
        default=None,
        help=(
            "round kind, which decides the notes templates this round is scaffolded with. "
            "Omitted, the round gets the templates every round used to get, and the command "
            "prints what a declared kind would have skipped. Do not place it between input "
            "paths, since the trailing inputs are a variadic positional."
        ),
    )
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
    for raw in args.inputs:
        path = resolve_caller_path(raw)
        if not path.exists():
            print(f"Input path does not exist: {raw}", file=sys.stderr)
            return 1
        input_paths.append(path)

    file_requests = [
        InputRequest(role="input", source=path, dest_dir_rel=PurePosixPath("inputs"))
        for path in input_paths
        if path.is_file()
    ]
    directory_inputs = [path for path in input_paths if not path.is_file()]
    try:
        plan = plan_input_storage(file_requests, refuse_case_insensitive_clash=True)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    # One casefolded namespace across files and directories: the guard this slice replaced
    # covered every input path, so a file and a directory normalizing to one name must still
    # be refused with a message rather than a copytree traceback.
    claimed: dict[str, str] = {
        PurePosixPath(record.stored_rel).name.casefold(): record.stored_rel for record in plan.records
    }
    directory_targets: dict[str, Path] = {}
    for path in directory_inputs:
        stored = normalize_input_name(path.name)
        key = stored.casefold()
        if key in claimed:
            print(
                f"A directory input and a file input would both be stored as {stored} "
                f"(already claimed by {claimed[key]})",
                file=sys.stderr,
            )
            return 1
        if key in directory_targets:
            print(f"Multiple directory inputs would copy to the same name on Windows: {stored}", file=sys.stderr)
            return 1
        claimed[key] = f"inputs/{stored}"
        directory_targets[key] = path

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

        for template, target in templates_for_kind(args.kind):
            shutil.copy2(root / "templates" / template, tmp_round_dir / "notes" / target)
        replace_field(tmp_round_dir / "notes" / "round-notes.md", "Round", round_id)
        replace_field(tmp_round_dir / "notes" / "round-notes.md", "Date", datetime.now().strftime("%Y-%m-%d"))

        for source, destination_rel in plan.copies:
            copy_input(source, tmp_round_dir / destination_rel)
        directory_records: list[StoredInput] = []
        for path in directory_inputs:
            stored = normalize_input_name(path.name)
            copy_input(path, tmp_round_dir / "inputs" / stored)
            directory_records.append(directory_input_record(path, f"inputs/{stored}"))

        write_input_provenance(
            tmp_round_dir,
            case_id=args.case_id,
            round_id=round_id,
            records=(*plan.records, *directory_records),
        )

        # Extraction is derived from the stored file, not from the original path: the stored
        # name is normalized, so deriving the extract from `source.stem` would write an
        # extract whose name no longer matches its PDF.
        for _, destination_rel in plan.copies:
            stored = PurePosixPath(destination_rel)
            if stored.suffix.casefold() != ".pdf":
                continue
            copied_pdf = tmp_round_dir / destination_rel
            output = tmp_round_dir / "extracted" / f"{stored.stem}.txt"
            step = run_step(root, "PDF text extraction", ["scripts/extract-pdf-text", str(copied_pdf), str(output)])
            if step.ok:
                print(f"Extracted PDF text: extracted/{output.name}")
            else:
                output.unlink(missing_ok=True)
                print(
                    f"PDF text extraction failed for {stored.name}; keep the PDF in inputs/ "
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
    print(f"Round kind: {args.kind or '(unspecified)'}")
    skipped = skipped_for_kind(args.kind)
    if args.kind is None:
        would_skip = {
            kind: skipped_for_kind(kind) for kind in round_kinds() if skipped_for_kind(kind)
        }
        shortest = min(would_skip.values(), key=len, default=())
        if shortest:
            print(
                "No kind declared, so every intake template was scaffolded. Declaring one "
                f"would skip at least: {', '.join(shortest)}"
            )
    elif skipped:
        print(f"Skipped templates this kind does not use: {', '.join(skipped)}")
    if plan.copies or directory_inputs:
        print(f"Copied inputs: {len(plan.copies) + len(directory_inputs)}")
    deduplicated = [record for record in plan.records if not record.is_first_occurrence]
    for record in deduplicated:
        print(f"Deduplicated identical input: {record.original_name} -> {record.stored_rel}")
    renamed = [
        record
        for record in (*plan.records, *directory_records)
        if record.is_first_occurrence and PurePosixPath(record.stored_rel).name != record.original_name
    ]
    for record in renamed:
        print(f"Normalized input name: {record.original_name} -> {record.stored_rel}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
