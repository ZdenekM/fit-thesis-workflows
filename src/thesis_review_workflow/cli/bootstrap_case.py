"""Bootstrap a private thesis case round from submitted artifacts."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from thesis_review_workflow.code_workspace import (
    collapse_duplicate_top_level,
    extract_archive,
    is_archive,
    is_unsupported_archive,
    safe_copy_input_dir,
    safe_name,
)

ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class CopySpec:
    role: str
    source: Path
    dest_rel: Path


@dataclass(frozen=True)
class CopiedInput:
    role: str
    path: Path
    rel_round: str


@dataclass(frozen=True)
class PdfExtract:
    pdf_rel: str
    extract_rel: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class RollbackState:
    case_dir: Path
    round_dir: Path
    created_case: bool
    previous_current: str | None
    previous_case_md: str | None

    def rollback(self) -> None:
        if self.created_case:
            if self.case_dir.exists():
                shutil.rmtree(self.case_dir)
            return
        if self.round_dir.exists():
            shutil.rmtree(self.round_dir)
        if self.previous_case_md is not None:
            (self.case_dir / "case.md").write_text(self.previous_case_md, encoding="utf-8")
        current = self.case_dir / "current-round.txt"
        if self.previous_current is None:
            current.unlink(missing_ok=True)
        else:
            current.write_text(self.previous_current, encoding="utf-8")


@dataclass(frozen=True)
class PreparedSource:
    source_rel: str
    target_rel: str
    action: str
    detail: str


def repo_root() -> Path:
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
    return Path(output.strip())


def die(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def validate_id(label: str, value: str) -> None:
    if not ID_RE.fullmatch(value) or set(value) == {"."}:
        die(
            f"Invalid {label}. Use only letters, numbers, dot, underscore, and dash; dot-only ids are not allowed.",
            2,
        )


def input_base_dir() -> Path:
    return Path(os.environ.get("THESIS_REVIEW_CALLER_CWD", Path.cwd())).expanduser()


def resolve_existing(path_value: str) -> tuple[Path, str]:
    requested = Path(path_value).expanduser()
    candidate = requested if requested.is_absolute() else input_base_dir() / requested
    if not candidate.exists():
        die(f"Input path does not exist: {path_value}")
    symlink = contains_symlink(candidate)
    if symlink is not None:
        die(
            f"Directory input contains a symlink and was not imported: {symlink}. "
            "Pack the submission as an archive or remove the symlink before bootstrap."
        )
    return candidate.resolve(), requested.name


def contains_symlink(path: Path) -> Path | None:
    if path.is_symlink():
        return path
    if not path.is_dir():
        return None
    for child in path.rglob("*"):
        if child.is_symlink():
            return child
    return None


def check_ignored(root: Path, destination: Path) -> None:
    rel = destination.relative_to(root).as_posix()
    result = subprocess.run(
        ["git", "-C", root.as_posix(), "check-ignore", "-q", rel],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        die(f"Refusing to write private case data to a non-ignored path: {rel}")


def run_command(root: Path, args: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(root / args[0]), *args[1:]],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if check and result.returncode != 0:
        print(result.stdout, end="")
        die(f"Command failed: {' '.join(args)}")
    return result


def read_current_round(case_dir: Path) -> str:
    current = case_dir / "current-round.txt"
    if not current.is_file():
        die(f"Missing current round after import: {current}")
    round_id = current.read_text(encoding="utf-8").strip()
    validate_id("ROUND_ID", round_id)
    return round_id


def replace_field(path: Path, field: str, value: str | None) -> None:
    if value is None or value == "":
        return
    prefix = f"{field}:"
    lines = path.read_text(encoding="utf-8").splitlines()
    replaced = False
    updated: list[str] = []
    for line in lines:
        if line.startswith(prefix):
            updated.append(f"{prefix} {value}")
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        if updated and updated[-1] != "":
            updated.append("")
        updated.append(f"{prefix} {value}")
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def replace_line_prefix(path: Path, prefix: str, value: str | None) -> None:
    if value is None:
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = [f"{prefix} {value}" if line.startswith(prefix) else line for line in lines]
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def append_section(path: Path, title: str, lines: list[str]) -> None:
    original = path.read_text(encoding="utf-8")
    body = "\n".join([f"## {title}", "", *lines, ""])
    separator = "\n" if original.endswith("\n") else "\n\n"
    path.write_text(original + separator + body, encoding="utf-8")


def read_optional_text(value: str | None, file_value: str | None) -> str | None:
    parts: list[str] = []
    if value:
        parts.append(value.strip())
    if file_value:
        path, _ = resolve_existing(file_value)
        if not path.is_file():
            die(f"Expected a text file: {file_value}")
        parts.append(path.read_text(encoding="utf-8").strip())
    return "\n\n".join(part for part in parts if part) or None


def list_rel(items: list[CopiedInput], role: str | None = None) -> list[str]:
    return [item.rel_round for item in items if role is None or item.role == role]


def markdown_paths(paths: list[str], *, empty: str) -> list[str]:
    if not paths:
        return [f"- {empty}"]
    return [f"- `{path}`" for path in paths]


def unique_extract_name(round_dir: Path, pdf_rel: Path) -> Path:
    extracted = round_dir / "extracted"
    candidate = extracted / f"{pdf_rel.stem}.txt"
    if not candidate.exists():
        return candidate
    counter = 2
    while True:
        candidate = extracted / f"{pdf_rel.stem}-{counter}.txt"
        if not candidate.exists():
            return candidate
        counter += 1


def build_copy_plan(args: argparse.Namespace) -> list[CopySpec]:
    specs: list[CopySpec] = []

    def add_many(role: str, values: list[str], subdir: str | None = None) -> None:
        for value in values:
            source, basename = resolve_existing(value)
            if subdir is None:
                dest_rel = Path("inputs") / basename
            else:
                dest_rel = Path("inputs") / subdir / basename
            specs.append(CopySpec(role=role, source=source, dest_rel=dest_rel))

    add_many("thesis_pdf", args.thesis_pdf)
    add_many("assignment_pdf", args.assignment_pdf)
    add_many("source_archive", args.source_archive, "source")
    add_many("code", args.code)
    add_many("repo_snapshot", args.repo_snapshot)
    add_many("previous_feedback", args.previous_feedback, "previous-feedback")
    add_many("operator_notes", args.operator_notes, "operator-notes")
    add_many("input", args.input)

    destinations: dict[Path, CopySpec] = {}
    for spec in specs:
        existing = destinations.get(spec.dest_rel)
        if existing is not None:
            die(
                "Multiple inputs would copy to the same case path: "
                f"{spec.dest_rel.as_posix()} ({existing.source} and {spec.source})"
            )
        destinations[spec.dest_rel] = spec
    return specs


def copy_specs(root: Path, round_dir: Path, specs: list[CopySpec]) -> list[CopiedInput]:
    copied: list[CopiedInput] = []
    for spec in specs:
        destination = round_dir / spec.dest_rel
        check_ignored(root, destination)
        if destination.exists():
            die(f"Destination already exists: {destination.relative_to(root).as_posix()}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if spec.source.is_dir():
            shutil.copytree(spec.source, destination, symlinks=True)
        elif spec.source.is_file():
            shutil.copy2(spec.source, destination)
        else:
            die(f"Unsupported input path type: {spec.source}")
        copied.append(
            CopiedInput(
                role=spec.role,
                path=destination,
                rel_round=destination.relative_to(round_dir).as_posix(),
            )
        )
    return copied


def extract_pdfs(root: Path, round_dir: Path, copied: list[CopiedInput]) -> list[PdfExtract]:
    extracts: list[PdfExtract] = []
    for item in copied:
        if not item.path.is_file() or item.path.suffix.lower() != ".pdf":
            continue
        pdf_rel_path = Path(item.rel_round)
        output = unique_extract_name(round_dir, pdf_rel_path)
        result = run_command(
            root,
            [
                "scripts/extract-pdf-text",
                item.path.as_posix(),
                output.as_posix(),
            ],
            check=False,
        )
        extracts.append(
            PdfExtract(
                pdf_rel=item.rel_round,
                extract_rel=output.relative_to(round_dir).as_posix(),
                ok=result.returncode == 0,
                detail=result.stdout.strip(),
            )
        )
    return extracts


def prepare_source_workspace(round_dir: Path, copied: list[CopiedInput]) -> tuple[list[PreparedSource], list[str]]:
    sources = [item for item in copied if item.role == "source_archive"]
    if not sources:
        return [], []

    workspace = round_dir / "work" / "source"
    workspace.mkdir(parents=True, exist_ok=True)
    prepared: list[PreparedSource] = []
    skipped: list[str] = []

    for source_item in sources:
        target_name = safe_name(source_item.path.stem if source_item.path.is_file() else source_item.path.name)
        target = workspace / target_name
        if target.exists():
            skipped.append(
                f"`{source_item.rel_round}`: target `{target.relative_to(round_dir).as_posix()}` already exists"
            )
            continue
        target.mkdir(parents=True, exist_ok=True)
        if source_item.path.is_file() and is_unsupported_archive(source_item.path):
            target.rmdir()
            skipped.append(f"`{source_item.rel_round}`: unsupported archive format; inspect manually if needed")
            continue
        if source_item.path.is_file() and is_archive(source_item.path):
            extracted, unsafe = extract_archive(source_item.path, target)
            detail = f"{extracted} files extracted"
            if collapse_duplicate_top_level(target):
                detail += "; collapsed duplicate top-level directory"
            if unsafe:
                detail += f"; skipped {len(unsafe)} unsafe/unsupported/over-limit entries"
            prepared.append(
                PreparedSource(
                    source_rel=source_item.rel_round,
                    target_rel=target.relative_to(round_dir).as_posix(),
                    action="extracted archive",
                    detail=detail,
                )
            )
            continue
        if source_item.path.is_dir():
            copied_count, unsafe = safe_copy_input_dir(source_item.path, target)
            detail = f"{copied_count} files copied"
            if unsafe:
                detail += f"; skipped {len(unsafe)} symlink/unsafe/unsupported/over-limit entries"
            prepared.append(
                PreparedSource(
                    source_rel=source_item.rel_round,
                    target_rel=target.relative_to(round_dir).as_posix(),
                    action="copied directory",
                    detail=detail,
                )
            )
            continue
        target.rmdir()
        skipped.append(f"`{source_item.rel_round}`: not an archive or directory")

    report = round_dir / "work" / "source_workspace.md"
    lines = [
        "# Source Workspace Preparation",
        "",
        "- Workspace: `work/source/`",
        "- Scope: ignored case-local workspace for search/diff evidence.",
        "- Advisory: the submitted PDF remains the authoritative rendered thesis. Do not compile sources by default.",
        "",
        "## Prepared Sources",
    ]
    if prepared:
        for prepared_item in prepared:
            lines.append(
                f"- `{prepared_item.source_rel}` -> `{prepared_item.target_rel}` "
                f"({prepared_item.action}; {prepared_item.detail})"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Skipped Or Manual Inputs"])
    lines.extend(skipped if skipped else ["- none"])
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return prepared, skipped


def defaulted(args: argparse.Namespace, name: str, default: str, *, created_case: bool) -> str | None:
    value = getattr(args, name)
    if isinstance(value, str):
        return value
    return default if created_case else None


def fill_case_metadata(
    case_md: Path,
    args: argparse.Namespace,
    *,
    assignment_summary: str | None,
    created_case: bool,
) -> None:
    replace_field(case_md, "Case ID", args.case_id)
    replace_field(case_md, "Work type", defaulted(args, "work_type", "unknown", created_case=created_case))
    replace_field(case_md, "Academic year", args.academic_year)
    replace_field(case_md, "Deadline mode", defaulted(args, "deadline_mode", "standard", created_case=created_case))
    replace_field(case_md, "Deadline override", args.deadline_override)
    replace_field(case_md, "Thesis language", defaulted(args, "thesis_language", "auto", created_case=created_case))
    replace_field(
        case_md, "Student feedback language", defaulted(args, "feedback_language", "cs", created_case=created_case)
    )
    replace_field(
        case_md, "Reviewer profile", defaulted(args, "reviewer_profile", "default", created_case=created_case)
    )
    replace_field(case_md, "Student", args.student)
    replace_field(case_md, "Topic", args.topic)
    replace_field(case_md, "Supervisor / opponent role", args.mode)
    replace_field(case_md, "Assignment summary", assignment_summary)


def fill_assignment_notes(
    round_dir: Path,
    copied: list[CopiedInput],
    extracts: list[PdfExtract],
    assignment_summary: str | None,
    private_assignment_notes: str | None,
) -> None:
    assignment = round_dir / "notes" / "assignment.md"
    assignment_pdfs = list_rel(copied, "assignment_pdf")
    assignment_extracts = [
        item.extract_rel for item in extracts if item.ok and any(item.pdf_rel == pdf for pdf in assignment_pdfs)
    ]

    formal_artifacts = markdown_paths(
        assignment_pdfs,
        empty="TODO: add `inputs/<formal-assignment.pdf>` or state that the official assignment is pasted below.",
    )
    if assignment_summary:
        formal_text = assignment_summary.splitlines()
    elif assignment_extracts:
        formal_text = [
            "TODO: Verify the extracted assignment text before relying on it.",
            "",
            "Candidate extracted assignment text:",
            *markdown_paths(assignment_extracts, empty="none"),
        ]
    else:
        formal_text = [
            "TODO: Paste the official assignment text or a faithful summary. "
            "If text was extracted into `extracted/`, cite that file here."
        ]

    if private_assignment_notes:
        private_notes = private_assignment_notes.splitlines()
    else:
        private_notes = [
            "TODO: Paste the non-public assignment notes that were given to the student. "
            "If there were none, write `None`."
        ]

    lines = [
        "# Assignment Context",
        "",
        "This file is required before generating supervisor feedback or opponent materials.",
        "",
        "Bootstrap advisory: imported files and extracted text are draft evidence. "
        "Verify the formal assignment and private notes before relying on readiness.",
        "",
        "## Formal Assignment Artifacts",
        "",
        *formal_artifacts,
        "",
        "## Formal Assignment Text Or Summary",
        "",
        *formal_text,
        "",
        "## Private Assignment Notes For Student",
        "",
        *private_notes,
        "",
        "## Assignment Coverage Hints",
        "",
        "-",
        "",
    ]
    assignment.write_text("\n".join(lines), encoding="utf-8")


def update_previous_feedback_index(round_dir: Path, copied: list[CopiedInput]) -> None:
    previous = list_rel(copied, "previous_feedback")
    if not previous:
        return
    index = round_dir / "notes" / "previous-feedback-index.md"
    append_section(
        index,
        "Imported Historical Feedback",
        [
            "Use these artifacts as context/calibration only after checking relevance to the current round.",
            "",
            *markdown_paths(previous, empty="none"),
        ],
    )


def fill_round_notes(
    round_dir: Path,
    copied: list[CopiedInput],
    extracts: list[PdfExtract],
    args: argparse.Namespace,
) -> None:
    notes = round_dir / "notes" / "round-notes.md"
    thesis_extracts = [
        item.extract_rel for item in extracts if item.ok and item.pdf_rel in set(list_rel(copied, "thesis_pdf"))
    ]
    assignment_extracts = [
        item.extract_rel for item in extracts if item.ok and item.pdf_rel in set(list_rel(copied, "assignment_pdf"))
    ]
    github_values = [value for value in [*args.github_url, *args.pr_url, args.student_login] if value]

    replace_line_prefix(notes, "Purpose:", args.purpose or f"{args.mode} bootstrap import")
    replace_line_prefix(notes, "- Thesis PDF:", ", ".join(list_rel(copied, "thesis_pdf")) or "not provided")
    replace_line_prefix(
        notes, "- Formal assignment:", ", ".join(list_rel(copied, "assignment_pdf")) or "see notes/assignment.md"
    )
    replace_line_prefix(notes, "- Private assignment notes:", "see notes/assignment.md")
    replace_line_prefix(notes, "- Extracted thesis text:", ", ".join(thesis_extracts) or "not available")
    replace_line_prefix(notes, "- LaTeX sources:", ", ".join(list_rel(copied, "source_archive")) or "not provided")
    replace_line_prefix(
        notes,
        "- Student code:",
        ", ".join([*list_rel(copied, "code"), *list_rel(copied, "repo_snapshot")]) or "not provided",
    )
    replace_line_prefix(notes, "- GitHub repo/PR:", ", ".join(github_values) or "not provided")
    replace_line_prefix(notes, "- README / docs:", "inspect submitted source/code if present")
    replace_line_prefix(
        notes,
        "- Previous feedback:",
        ", ".join(list_rel(copied, "previous_feedback")) or "see notes/previous-feedback-index.md",
    )

    summary = [
        f"- Mode: {args.mode}",
        "- Imported evidence is private case-local data under ignored `cases/`.",
        "- PDF text extraction is advisory; verify extracted assignment/thesis text before relying on it.",
        "- Do not generate sendable feedback or opponent materials without the required authorized agent review loop.",
    ]
    if assignment_extracts:
        summary.append(f"- Extracted assignment text candidates: {', '.join(assignment_extracts)}")
    if args.explicit_check:
        summary.extend(["", "Explicit checks requested by operator:", *[f"- {item}" for item in args.explicit_check]])
    if args.do_not_reopen:
        summary.extend(["", "Operator do-not-reopen boundaries:", *[f"- {item}" for item in args.do_not_reopen]])
    if list_rel(copied, "operator_notes"):
        summary.extend(
            ["", "Imported operator note files:", *markdown_paths(list_rel(copied, "operator_notes"), empty="none")]
        )
    append_section(notes, "Bootstrap Import Summary", summary)


def fill_intake(round_dir: Path, copied: list[CopiedInput], args: argparse.Namespace) -> None:
    if args.mode == "supervisor":
        intake = round_dir / "notes" / "supervisor-intake.md"
        replace_line_prefix(intake, "Typ prace:", args.work_type)
        replace_line_prefix(
            intake,
            "Jazyk prace",
            (
                "(neridi jazyk feedbacku; preferovane nastaveni je Thesis language v case.md): "
                f"{args.thesis_language or ''}"
            ),
        )
        replace_line_prefix(intake, "Tema jednou vetou:", args.topic)
        replace_line_prefix(intake, "Datum revize:", date.today().isoformat())
        replace_line_prefix(intake, "Hlavni cil teto revize:", args.purpose)
        replace_line_prefix(
            intake, "Co chci explicitne zkontrolovat:", "; ".join(args.explicit_check) if args.explicit_check else None
        )
        replace_line_prefix(
            intake, "Co uz nechci v teto fazi otevirat:", "; ".join(args.do_not_reopen) if args.do_not_reopen else None
        )
        replace_line_prefix(
            intake,
            "GitHub repo / PR URL / student login:",
            ", ".join([*args.github_url, *args.pr_url, args.student_login or ""]),
        )
    else:
        intake = round_dir / "notes" / "opponent-intake.md"
        replace_line_prefix(intake, "Typ prace:", args.work_type)
        replace_line_prefix(
            intake,
            "Jazyk prace",
            (
                "(preferovane nastaveni je Thesis language v case.md; zde jen round poznamka): "
                f"{args.thesis_language or ''}"
            ),
        )
        replace_line_prefix(intake, "Nazev prace:", args.title)
        replace_line_prefix(intake, "Tema jednou vetou:", args.topic)
        replace_line_prefix(
            intake, "Co chci explicitne zkontrolovat:", "; ".join(args.explicit_check) if args.explicit_check else None
        )
        replace_line_prefix(
            intake,
            "GitHub repo / PR URL / student login:",
            ", ".join([*args.github_url, *args.pr_url, args.student_login or ""]),
        )

    note_refs = list_rel(copied, "operator_notes")
    if note_refs:
        append_section(intake, "Imported Operator Notes", markdown_paths(note_refs, empty="none"))


def create_or_import_round(root: Path, args: argparse.Namespace) -> tuple[Path, str, RollbackState]:
    case_dir = root / "cases" / args.case_id
    created_case = False
    previous_current = None
    previous_case_md = None
    current_path = case_dir / "current-round.txt"
    if case_dir.exists():
        if current_path.is_file():
            previous_current = current_path.read_text(encoding="utf-8")
        case_md = case_dir / "case.md"
        if case_md.is_file():
            previous_case_md = case_md.read_text(encoding="utf-8")
        run_command(root, ["scripts/import-round", args.case_id, args.round_label], check=True)
    else:
        run_command(
            root,
            [
                "scripts/new-case",
                args.case_id,
                args.work_type or "unknown",
                args.round_label,
            ],
            check=True,
        )
        created_case = True
    round_id = read_current_round(case_dir)
    round_dir = case_dir / "rounds" / round_id
    return (
        case_dir,
        round_id,
        RollbackState(
            case_dir=case_dir,
            round_dir=round_dir,
            created_case=created_case,
            previous_current=previous_current,
            previous_case_md=previous_case_md,
        ),
    )


def print_command_result(title: str, command: list[str], result: subprocess.CompletedProcess[str]) -> None:
    status = "PASS" if result.returncode == 0 else "NEEDS ATTENTION"
    print()
    print(f"## {title}: {status}")
    print(f"$ {' '.join(command)}")
    if result.stdout.strip():
        print(result.stdout.rstrip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/bootstrap-case",
        description="Create or extend a private thesis case round, import artifacts, and run readiness diagnostics.",
    )
    parser.add_argument("mode", choices=["supervisor", "opponent"])
    parser.add_argument("case_id")
    parser.add_argument("round_label")
    parser.add_argument("--work-type", help="BP, DP, or unknown")
    parser.add_argument("--academic-year")
    parser.add_argument("--deadline-mode")
    parser.add_argument("--deadline-override")
    parser.add_argument("--thesis-language")
    parser.add_argument("--feedback-language")
    parser.add_argument("--reviewer-profile")
    parser.add_argument("--student")
    parser.add_argument("--topic")
    parser.add_argument("--title")
    parser.add_argument("--purpose")
    parser.add_argument("--assignment-summary")
    parser.add_argument("--assignment-summary-file")
    parser.add_argument("--private-assignment-notes")
    parser.add_argument("--private-assignment-notes-file")
    parser.add_argument("--thesis-pdf", action="append", default=[])
    parser.add_argument("--assignment-pdf", action="append", default=[])
    parser.add_argument("--source-archive", action="append", default=[])
    parser.add_argument("--code", action="append", default=[], help="Submitted code archive or directory")
    parser.add_argument(
        "--repo-snapshot", action="append", default=[], help="Local submitted repository snapshot directory/archive"
    )
    parser.add_argument("--previous-feedback", action="append", default=[])
    parser.add_argument("--operator-notes", action="append", default=[])
    parser.add_argument("--input", action="append", default=[], help="Additional raw input copied to inputs/")
    parser.add_argument("--github-url", action="append", default=[])
    parser.add_argument("--pr-url", action="append", default=[])
    parser.add_argument("--student-login")
    parser.add_argument("--explicit-check", action="append", default=[])
    parser.add_argument("--do-not-reopen", action="append", default=[])
    parser.add_argument(
        "--strict", action="store_true", help="return non-zero when readiness or case-doctor reports failures"
    )
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    validate_id("CASE_ID", args.case_id)

    root = repo_root()
    copy_plan = build_copy_plan(args)
    assignment_summary = read_optional_text(args.assignment_summary, args.assignment_summary_file)
    private_assignment_notes = read_optional_text(args.private_assignment_notes, args.private_assignment_notes_file)

    case_dir, round_id, rollback = create_or_import_round(root, args)
    round_dir = case_dir / "rounds" / round_id
    created_case = rollback.created_case

    try:
        fill_case_metadata(case_dir / "case.md", args, assignment_summary=assignment_summary, created_case=created_case)

        copied = copy_specs(root, round_dir, copy_plan)
        extracts = extract_pdfs(root, round_dir, copied)
        prepared_sources, skipped_sources = prepare_source_workspace(round_dir, copied)
        fill_assignment_notes(round_dir, copied, extracts, assignment_summary, private_assignment_notes)
        update_previous_feedback_index(round_dir, copied)
        fill_round_notes(round_dir, copied, extracts, args)
        fill_intake(round_dir, copied, args)
    except BaseException:
        rollback.rollback()
        raise

    code_inputs_present = any(item.role in {"code", "repo_snapshot"} for item in copied)
    code_result: subprocess.CompletedProcess[str] | None = None
    if code_inputs_present:
        code_result = run_command(root, ["scripts/prepare-code-workspace", args.case_id, round_id], check=False)

    readiness_cmd = [
        "scripts/check-supervisor-ready" if args.mode == "supervisor" else "scripts/check-round-ready",
        args.case_id,
        round_id,
    ]
    readiness = run_command(root, readiness_cmd, check=False)
    doctor_cmd = ["scripts/case-doctor", args.case_id, round_id]
    doctor = run_command(root, doctor_cmd, check=False)

    print("Bootstrap Case")
    print(f"Case: cases/{args.case_id} ({'created' if created_case else 'existing'})")
    print(f"Round: cases/{args.case_id}/rounds/{round_id}")
    print(f"Copied inputs: {len(copied)}")
    for copied_item in copied:
        print(f"- {copied_item.role}: {copied_item.rel_round}")
    if extracts:
        print(f"PDF extracts: {sum(1 for extract in extracts if extract.ok)}/{len(extracts)}")
        for extract in extracts:
            marker = "ok" if extract.ok else "failed"
            print(f"- {marker}: {extract.pdf_rel} -> {extract.extract_rel}")
    else:
        print("PDF extracts: none")
    if prepared_sources or skipped_sources:
        print(f"Source workspace: {len(prepared_sources)} prepared, {len(skipped_sources)} skipped/manual")
        for source in prepared_sources:
            print(f"- {source.source_rel} -> {source.target_rel} ({source.action})")
    else:
        print("Source workspace: skipped")
    if code_result is not None:
        print_command_result(
            "Code workspace preparation", ["scripts/prepare-code-workspace", args.case_id, round_id], code_result
        )
    else:
        print()
        print("## Code workspace preparation: SKIPPED")
        print("No --code or --repo-snapshot inputs were provided.")

    print_command_result("Readiness check", readiness_cmd, readiness)
    print_command_result("Case doctor", doctor_cmd, doctor)

    print()
    print("## Next steps")
    print("- Verify `notes/assignment.md`; extracted assignment text is only advisory until reviewed.")
    print("- Fill any missing assignment, deadline, reviewer profile, or private-note metadata reported above.")
    if args.mode == "supervisor":
        print("- Before student-facing feedback, run the supervisor workflow with authorized agents.")
    else:
        print("- Before opponent materials, run the opponent workflow with authorized agents.")

    if args.strict and (
        readiness.returncode != 0 or doctor.returncode != 0 or (code_result and code_result.returncode != 0)
    ):
        return 1
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
