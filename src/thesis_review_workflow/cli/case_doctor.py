"""Print a read-only case/round readiness and artifact status report."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Any

from thesis_review_workflow.agent_coverage import (
    COVERAGE_REL,
    coverage_required,
    inferred_coverage_required,
    inferred_role_specs,
    load_json_object,
)
from thesis_review_workflow.case_doctor_summary import (
    CODE_SUFFIXES,
    ArchiveInfo,
    DirectoryInventory,
    GateResult,
    Issue,
    add_issue,
    agent_coverage_summary_lines,
    archive_entry_code_like,
    archive_may_be_code_from_name,
    archive_suffix,
    archive_top_entries,
    compact_output,
    file_size_label,
    gate_failure_severity,
    is_archive,
    manifest_summary_lines,
    matching_extract,
    nonempty_lines,
    one_line,
    output_expectations,
    path_list,
)
from thesis_review_workflow.cases import read_current_round, repo_root
from thesis_review_workflow.commands import command_display, repo_command_environment, resolve_repo_command
from thesis_review_workflow.ids import is_valid_id
from thesis_review_workflow.ids import validate_id as validate_id_core
from thesis_review_workflow.metadata import read_fields
from thesis_review_workflow.operation_log import operation_log_summary_lines
from thesis_review_workflow.paths import rel_repo, rel_round
from thesis_review_workflow.pdf_extracts import expected_pdf_extract_path
from thesis_review_workflow.submission_bundle import submission_bundle_visibility_lines

MANIFEST_REL = Path("work/review_manifest.json")
LARGE_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_LIST = 12
MAX_WALK_FILES = 5000
SAFE_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "target",
    ".venv",
    "venv",
}
DEPENDENCY_NAMES = {
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "CMakeLists.txt",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    "compose.yml",
}
MEDIA_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".ppt",
    ".pptx",
    ".odp",
    ".key",
    ".ipynb",
}


def validate_id(label: str, value: str) -> None:
    try:
        validate_id_core(label, value)
    except ValueError as exc:
        print(
            str(exc),
            file=sys.stderr,
        )
        raise SystemExit(2) from exc


def run_gate(root: Path, name: str, args: list[str], timeout: int = 45) -> GateResult:
    display = command_display(args)
    try:
        result = subprocess.run(
            resolve_repo_command(root, args),
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=repo_command_environment(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return GateResult(name, display, 1, f"Timed out after {timeout}s")
    if result.returncode == 0:
        parts = (result.stdout.strip(), result.stderr.strip())
    else:
        parts = (result.stderr.strip(), result.stdout.strip())
    output = "\n".join(part for part in parts if part)
    return GateResult(name, display, result.returncode, output)


def find_files(base: Path, predicate: Any, *, max_seen: int = MAX_WALK_FILES) -> list[Path]:
    if not base.is_dir():
        return []
    matches: list[Path] = []
    files_seen = 0
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [name for name in dirnames if name not in SAFE_SKIP_DIRS]
        for filename in filenames:
            path = Path(dirpath) / filename
            files_seen += 1
            if predicate(path):
                matches.append(path)
            if files_seen >= max_seen:
                return sorted(matches)
    return sorted(matches)


def inspect_archive(path: Path) -> ArchiveInfo:
    size = path.stat().st_size
    if size > LARGE_ARCHIVE_BYTES:
        return ArchiveInfo(
            path,
            size,
            None,
            [],
            False,
            archive_may_be_code_from_name(path),
            "large archive; metadata only, entries not listed",
        )

    suffix = archive_suffix(path)
    names: list[str] = []
    note = "metadata listed"
    try:
        if suffix == ".zip":
            with zipfile.ZipFile(path) as handle:
                for index, item in enumerate(handle.infolist()):
                    if index >= MAX_WALK_FILES:
                        note = f"metadata truncated at {MAX_WALK_FILES} entries"
                        break
                    names.append(item.filename)
        elif suffix in {".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz", ".tbz2", ".txz"}:
            with tarfile.open(path, mode="r:*") as handle:
                for index, member in enumerate(handle):
                    if index >= MAX_WALK_FILES:
                        note = f"metadata truncated at {MAX_WALK_FILES} entries"
                        break
                    names.append(member.name)
        else:
            note = "archive format not inspected"
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
        note = f"archive metadata unreadable: {exc}"

    code_like = any(archive_entry_code_like(name) for name in names)
    code_unknown = not names and archive_may_be_code_from_name(path)
    return ArchiveInfo(
        path,
        size,
        len(names) if names or note == "metadata listed" else None,
        archive_top_entries(names),
        code_like,
        code_unknown,
        note,
    )


def walk_inventory(root: Path) -> DirectoryInventory:
    files_seen = 0
    truncated = False
    readmes: list[str] = []
    dependencies: list[str] = []
    tests: list[str] = []
    ci: list[str] = []
    large: list[str] = []
    code_files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SAFE_SKIP_DIRS]
        for filename in filenames:
            path = Path(dirpath) / filename
            files_seen += 1
            rel = path.relative_to(root).as_posix()
            lower = rel.lower()
            name = path.name
            if name.lower().startswith("readme") and len(readmes) < MAX_LIST:
                readmes.append(rel)
            if name in DEPENDENCY_NAMES and len(dependencies) < MAX_LIST:
                dependencies.append(rel)
            if lower.startswith(".github/workflows/") and len(ci) < MAX_LIST:
                ci.append(rel)
            if (
                re.search(r"(^|/)(test|tests|spec|specs)(/|$)", lower) or re.search(r"(test|spec)\.", name.lower())
            ) and len(tests) < MAX_LIST:
                tests.append(rel)
            if Path(name).suffix.lower() in CODE_SUFFIXES and len(code_files) < MAX_LIST:
                code_files.append(rel)
            try:
                if path.stat().st_size >= 10 * 1024 * 1024 and len(large) < MAX_LIST:
                    large.append(rel)
            except OSError:
                pass
            if files_seen >= MAX_WALK_FILES:
                truncated = True
                return DirectoryInventory(
                    root, files_seen, truncated, readmes, dependencies, tests, ci, large, code_files
                )
    return DirectoryInventory(root, files_seen, truncated, readmes, dependencies, tests, ci, large, code_files)


def candidate_code_dirs(round_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for rel in (
        "work/code",
        "work/github-intake",
        "inputs/code",
        "inputs/src",
        "inputs/source",
        "inputs/submission",
        "inputs/github",
    ):
        path = round_dir / rel
        if path.is_dir():
            candidates.append(path)

    for base in (round_dir / "inputs", round_dir / "work"):
        if not base.is_dir():
            continue
        for path in base.iterdir():
            if not path.is_dir() or path in candidates or path.name in SAFE_SKIP_DIRS:
                continue
            if path.name in {"thesis-source", "figure_media"}:
                continue
            lower = path.name.lower()
            if any(token in lower for token in ("code", "src", "source", "repo", "app", "project", "github")):
                candidates.append(path)

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def output_section(title: str, lines: list[str]) -> None:
    print()
    print(f"## {title}")
    if lines:
        for line in lines:
            print(line)
    else:
        print("- none")


def pdf_extract_status(round_dir: Path, issues: list[Issue]) -> tuple[list[Path], list[Path], list[str]]:
    pdfs = find_files(round_dir / "inputs", lambda path: path.suffix.lower() == ".pdf")
    extracted = find_files(round_dir / "extracted", lambda path: path.suffix.lower() == ".txt")
    known_mappings = {
        pdf: expected
        for pdf in pdfs
        if (expected := expected_pdf_extract_path(round_dir, pdf)) != round_dir / "extracted" / f"{pdf.stem}.txt"
    }
    lines: list[str] = []
    used_extracts: set[Path] = set()
    for pdf in pdfs:
        extract, match_kind = matching_extract(
            pdf,
            extracted,
            pdf_count=len(pdfs),
            used_extracts=used_extracts,
            known_mappings=known_mappings,
        )
        if extract is None:
            lines.append(f"- {rel_round(round_dir, pdf)} -> missing matching extracted text")
            add_issue(issues, "WARNING", f"Missing matching text extract for {rel_round(round_dir, pdf)}.")
            continue
        used_extracts.add(extract)
        status = "present"
        try:
            if extract.stat().st_mtime < pdf.stat().st_mtime:
                status = "older than PDF"
                add_issue(issues, "WARNING", f"Text extract is older than PDF: {rel_round(round_dir, extract)}.")
        except OSError:
            status = "mtime unavailable"
        qualifier = f", {match_kind}" if match_kind != "same-stem" else ""
        lines.append(f"- {rel_round(round_dir, pdf)} -> {rel_round(round_dir, extract)} ({status}{qualifier})")
    if not pdfs:
        lines.append("- no PDFs under inputs/")
    if extracted:
        lines.append(
            f"- Extracted text files: {len(extracted)} ({', '.join(path_list(round_dir, extracted, max_items=6))})"
        )
    else:
        lines.append("- Extracted text files: none")
    return pdfs, extracted, lines


def collect_feedback_rounds(case_dir: Path, current_round_id: str) -> tuple[list[Path], list[Path]]:
    rounds_dir = case_dir / "rounds"
    if not rounds_dir.is_dir():
        return [], []
    previous: list[Path] = []
    other: list[Path] = []
    for round_path in sorted(rounds_dir.iterdir()):
        if not round_path.is_dir() or round_path.name == current_round_id:
            continue
        feedback = round_path / "outputs" / "feedback_student.md"
        if feedback.is_file():
            if round_path.name < current_round_id:
                previous.append(feedback)
            else:
                other.append(feedback)
    return previous, other


def manifest_summary(round_dir: Path, outputs: list[Path], issues: list[Issue]) -> list[str]:
    manifest_path = round_dir / MANIFEST_REL
    if not manifest_path.is_file():
        return manifest_summary_lines(
            manifest_present=False,
            outputs_present=bool(outputs),
            manifest_error=None,
            artifacts=[],
            supporting_work_artifacts=[],
            helper_checks=[],
            coverage_needed=False,
            coverage_present=False,
            manifest_rel=MANIFEST_REL.as_posix(),
            coverage_rel=COVERAGE_REL.as_posix(),
            issues=issues,
        )

    manifest: dict[str, Any] | None = None
    manifest_error = None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        manifest_error = exc.msg

    artifacts = manifest.get("artifacts", []) if isinstance(manifest, dict) else []
    supporting_work_artifacts = manifest.get("supporting_work_artifacts", []) if isinstance(manifest, dict) else []
    checks = manifest.get("helper_checks", []) if isinstance(manifest, dict) else []
    return manifest_summary_lines(
        manifest_present=True,
        outputs_present=bool(outputs),
        manifest_error=manifest_error,
        artifacts=artifacts,
        supporting_work_artifacts=supporting_work_artifacts,
        helper_checks=checks,
        coverage_needed=isinstance(manifest, dict) and inferred_coverage_required(round_dir, manifest),
        coverage_present=(round_dir / COVERAGE_REL).is_file(),
        manifest_rel=MANIFEST_REL.as_posix(),
        coverage_rel=COVERAGE_REL.as_posix(),
        issues=issues,
    )


def agent_coverage_summary(round_dir: Path, issues: list[Issue]) -> list[str]:
    manifest_path = round_dir / MANIFEST_REL
    if not manifest_path.is_file():
        return ["- unavailable: review manifest is missing"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ["- unavailable: review manifest JSON is invalid"]
    if not isinstance(manifest, dict):
        return ["- unavailable: review manifest is not an object"]

    specs = inferred_role_specs(round_dir, manifest)
    coverage = None
    coverage_error = None
    try:
        coverage = load_json_object(round_dir / COVERAGE_REL)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        coverage_error = str(exc)
    return agent_coverage_summary_lines(
        specs=specs,
        coverage=coverage,
        coverage_error=coverage_error,
        evidence_exists=lambda path: (round_dir / path).is_file(),
        issues=issues,
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts/case-doctor",
        description="Print a read-only readiness/status report for a thesis case round.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    args = parser.parse_args(argv[1:])

    validate_id("CASE_ID", args.case_id)
    if args.round_id:
        validate_id("ROUND_ID", args.round_id)

    root = repo_root()
    case_dir = root / "cases" / args.case_id
    issues: list[Issue] = []

    if not case_dir.is_dir():
        print(f"Case Doctor: cases/{args.case_id}")
        print(f"ERROR: Case does not exist: cases/{args.case_id}")
        return 1

    case_md = case_dir / "case.md"
    if not case_md.is_file():
        print(f"Case Doctor: cases/{args.case_id}")
        print(f"ERROR: Missing case metadata: cases/{args.case_id}/case.md")
        return 1

    current_round_raw = read_current_round(case_dir)
    current_round: str | None = None
    current_round_label = "(missing)"
    if current_round_raw:
        current_round_label = current_round_raw
        if is_valid_id(current_round_raw):
            current_round = current_round_raw
        elif args.round_id:
            add_issue(
                issues,
                "WARNING",
                f"current-round.txt contains invalid round id: {current_round_raw}.",
            )
        else:
            print(f"Case Doctor: cases/{args.case_id}")
            print("ERROR: Invalid ROUND_ID in current-round.txt. Use only letters, numbers, dot, underscore, and dash.")
            return 2
    elif args.round_id:
        add_issue(issues, "WARNING", f"Missing current round: cases/{args.case_id}/current-round.txt.")
    else:
        print(f"Case Doctor: cases/{args.case_id}")
        print(f"ERROR: Missing current round: cases/{args.case_id}/current-round.txt")
        return 1

    round_id = args.round_id or current_round
    if round_id is None:
        print(f"Case Doctor: cases/{args.case_id}")
        print(f"ERROR: Missing current round: cases/{args.case_id}/current-round.txt")
        return 1
    round_dir = case_dir / "rounds" / round_id
    if not round_dir.is_dir():
        print(f"Case Doctor: cases/{args.case_id}")
        print(f"Round: {round_id}")
        print(f"ERROR: Round does not exist: cases/{args.case_id}/rounds/{round_id}")
        return 1

    if args.round_id and current_round and args.round_id != current_round:
        add_issue(
            issues,
            "WARNING",
            f"Requested round {args.round_id} differs from current-round.txt ({current_round}).",
        )

    case_fields = read_fields(case_md)
    rounds_dir = case_dir / "rounds"
    rounds = sorted(path.name for path in rounds_dir.iterdir() if path.is_dir()) if rounds_dir.is_dir() else []
    previous_feedback, other_feedback = collect_feedback_rounds(case_dir, round_id)

    gates = [
        run_gate(root, "reviewer profile", ["scripts/check-reviewer-profile", args.case_id]),
        run_gate(root, "round readiness", ["scripts/check-round-ready", args.case_id, round_id]),
        run_gate(root, "tooling preflight", ["scripts/check-tooling", "--fast", args.case_id, round_id]),
        run_gate(root, "supervisor deadline", ["scripts/supervisor-deadline", args.case_id, round_id]),
        run_gate(root, "supervisor readiness", ["scripts/check-supervisor-ready", args.case_id, round_id]),
        run_gate(
            root,
            "feedback language config",
            ["scripts/check-feedback-language", "--config-only", args.case_id, round_id],
        ),
    ]

    pdfs, extracted, pdf_lines = pdf_extract_status(round_dir, issues)
    outputs = sorted((round_dir / "outputs").glob("*.md")) if (round_dir / "outputs").is_dir() else []
    archive_paths = find_files(round_dir / "inputs", is_archive)
    archives = [inspect_archive(path) for path in archive_paths]
    for info in archives:
        if info.size > LARGE_ARCHIVE_BYTES:
            add_issue(issues, "WARNING", f"Large archive was not entry-listed: {rel_round(round_dir, info.path)}.")
        if info.code_unknown:
            add_issue(
                issues,
                "WARNING",
                f"Archive may contain code but was not classifiable from metadata: {rel_round(round_dir, info.path)}.",
            )
    code_dirs = candidate_code_dirs(round_dir)
    inventories = [walk_inventory(path) for path in code_dirs]
    code_present = bool(
        any(info.code_like or info.code_unknown for info in archives)
        or any(inventory.code_like for inventory in inventories)
        or (round_dir / "inputs" / "github").is_dir()
        or (round_dir / "work" / "github-intake").is_dir()
    )
    work_code = round_dir / "work" / "code"
    if code_present and not work_code.is_dir() and not (round_dir / "work" / "github-intake").is_dir():
        add_issue(
            issues,
            "WARNING",
            "Code evidence is present but no inspectable work/code or work/github-intake workspace exists.",
        )

    media = find_files(round_dir, lambda path: path.suffix.lower() in MEDIA_SUFFIXES)
    output_names = {path.name for path in outputs}
    feedback_draft_present = (round_dir / "work" / "feedback_student_draft.md").is_file()
    output_lines = output_expectations(
        output_names,
        feedback_draft_present=feedback_draft_present,
        opponent_materials_draft_present=(round_dir / "work" / "oponent_podklady_draft.md").is_file(),
        reviewed_opponent_materials_present=(round_dir / "outputs" / "oponent_podklady_revidovane.md").is_file(),
        opponent_report_trace_present=(round_dir / "work" / "opponent_report_trace.json").is_file(),
        opponent_report_draft_present=(round_dir / "work" / "oponent_posudek_draft.md").is_file(),
        opponent_report_review_present="feedback_k_posudku.md" in output_names,
        code_present=code_present,
        issues=issues,
    )
    manifest_lines = manifest_summary(round_dir, outputs, issues)

    if outputs or (round_dir / MANIFEST_REL).is_file():
        if (round_dir / MANIFEST_REL).is_file():
            try:
                manifest = json.loads((round_dir / MANIFEST_REL).read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                manifest = {}
            if isinstance(manifest, dict) and coverage_required(round_dir, manifest):
                gates.append(run_gate(root, "agent coverage", ["scripts/check-agent-coverage", args.case_id, round_id]))
        gates.append(
            run_gate(
                root, "review manifest", ["scripts/check-review-manifest", "--require-complete", args.case_id, round_id]
            )
        )
    if (round_dir / "outputs" / "feedback_student.md").is_file():
        gates.append(
            run_gate(root, "feedback language output", ["scripts/check-feedback-language", args.case_id, round_id])
        )
        gates.append(run_gate(root, "feedback output", ["scripts/check-feedback-output", args.case_id, round_id]))
    if (round_dir / "outputs" / "oponent_podklady_revidovane.md").is_file():
        gates.append(run_gate(root, "opponent materials", ["scripts/check-opponent-materials", args.case_id, round_id]))
        gates.append(
            run_gate(root, "opponent report trace/draft", ["scripts/check-opponent-report", args.case_id, round_id])
        )
    if (round_dir / "outputs" / "code_consistency.md").is_file():
        gates.append(run_gate(root, "code consistency", ["scripts/check-code-consistency", args.case_id, round_id]))
    if (round_dir / "outputs" / "code_quality_review.md").is_file():
        gates.append(
            run_gate(root, "code quality review", ["scripts/check-code-quality-review", args.case_id, round_id])
        )
    if (round_dir / "work" / "quantitative_claims.json").is_file():
        gates.append(run_gate(root, "quantitative claims", ["scripts/check-evaluation-claims", args.case_id, round_id]))
    if (round_dir / "outputs" / "literature_citation_review.md").is_file():
        gates.append(
            run_gate(
                root,
                "literature/citation review",
                ["scripts/check-literature-citation-review", args.case_id, round_id],
            )
        )
    if (round_dir / "outputs" / "figure_media_review.md").is_file():
        gates.append(
            run_gate(root, "figure/media review", ["scripts/check-figure-media-review", args.case_id, round_id])
        )
    if (round_dir / "outputs" / "typography_formal_review.md").is_file():
        gates.append(
            run_gate(
                root,
                "typography/formal review",
                ["scripts/check-typography-formal", "--require-output", args.case_id, round_id],
            )
        )

    for gate in gates:
        if not gate.ok:
            severity = gate_failure_severity(
                gate, {path.name for path in outputs}, feedback_draft_present=feedback_draft_present
            )
            suffix = (
                " (blocks supervisor feedback)" if severity == "WARNING" and gate.name.startswith("supervisor") else ""
            )
            add_issue(issues, severity, f"{gate.name} failed{suffix}: {compact_output(gate.output)}")

    status = "ERROR" if any(issue.severity == "ERROR" for issue in issues) else "WARNING" if issues else "OK"
    print("Case Doctor")
    print(f"Case: cases/{args.case_id}")
    print(f"Round: cases/{args.case_id}/rounds/{round_id}")
    error_count = sum(1 for issue in issues if issue.severity == "ERROR")
    warning_count = sum(1 for issue in issues if issue.severity == "WARNING")
    previous_rounds = ", ".join(rel_repo(root, path.parent.parent) for path in previous_feedback)
    other_rounds = ", ".join(rel_repo(root, path.parent.parent) for path in other_feedback)
    print(f"Status: {status} ({error_count} errors, {warning_count} warnings)")

    output_section(
        "Case / Round",
        [
            f"- Current round: {current_round_label}",
            f"- Requested round: {args.round_id or '(current)'}",
            f"- Available rounds: {', '.join(rounds) if rounds else 'none'}",
            f"- Previous feedback rounds: {previous_rounds if previous_feedback else 'none'}",
            f"- Other feedback rounds: {other_rounds if other_feedback else 'none'}",
        ],
    )

    output_section(
        "Metadata",
        [
            f"- Work type: {case_fields.get('work type', '(missing)')}",
            f"- Academic year: {case_fields.get('academic year', '(missing)')}",
            f"- Deadline mode: {case_fields.get('deadline mode', 'standard') or 'standard'}",
            f"- Deadline override: {case_fields.get('deadline override', '(none)') or '(none)'}",
            f"- Reviewer profile: {case_fields.get('reviewer profile', 'default') or 'default'}",
            f"- Student feedback language: {case_fields.get('student feedback language', 'cs') or 'cs'}",
            f"- Thesis language: {case_fields.get('thesis language', 'auto') or 'auto'}",
        ],
    )

    gate_lines = []
    for gate in gates:
        label = "PASS" if gate.ok else "FAIL"
        output = one_line(gate.output) if gate.ok else compact_output(gate.output)
        gate_lines.append(f"- {label} {gate.name}: `{gate.command}` -> {output}")
    output_section("Workflow Gates", gate_lines)

    tooling_gate = next((gate for gate in gates if gate.name == "tooling preflight"), None)
    output_section(
        "Tooling Preflight",
        nonempty_lines(tooling_gate.output) if tooling_gate else ["- not run"],
    )

    note_files = sorted((round_dir / "notes").glob("*.md")) if (round_dir / "notes").is_dir() else []
    thesis_source = round_dir / "work" / "thesis-source"
    input_lines = [
        f"- Notes: {', '.join(path_list(round_dir, note_files)) if note_files else 'none'}",
        f"- PDFs: {len(pdfs)}",
        f"- Archives: {len(archives)}",
        f"- Extracted text files: {len(extracted)}",
        f"- Thesis source workspace: {'present' if thesis_source.is_dir() else 'missing'}",
    ]
    output_section("Inputs And Extracts", input_lines + pdf_lines)

    archive_lines: list[str] = []
    for info in archives:
        bits = [
            rel_round(round_dir, info.path),
            file_size_label(info.size),
            f"entries: {info.entry_count if info.entry_count is not None else 'not listed'}",
            "code-like" if info.code_like else "possible-code" if info.code_unknown else "not code-classified",
            info.note,
        ]
        archive_lines.append("- " + "; ".join(bits))
    if not archive_lines:
        archive_lines.append("- none")
    output_section("Archives", archive_lines)
    output_section("Submission Bundle Inventory", submission_bundle_visibility_lines(round_dir))

    code_lines: list[str] = [f"- Code evidence detected: {'yes' if code_present else 'no'}"]
    code_workspace_report = round_dir / "work" / "code_workspace.md"
    serena_roots = round_dir / "work" / "serena_roots.json"
    code_lines.append(f"- Code workspace report: {'present' if code_workspace_report.is_file() else 'missing'}")
    code_lines.append(f"- Serena roots: {'present' if serena_roots.is_file() else 'missing'}")
    for inventory in inventories:
        code_lines.append(
            f"- {rel_round(round_dir, inventory.path)}: {inventory.files_seen} files"
            + (" (truncated)" if inventory.truncated else "")
        )
        for label, values in (
            ("README", inventory.readmes),
            ("dependency/build manifests", inventory.dependencies),
            ("tests", inventory.tests),
            ("CI", inventory.ci),
            ("large files", inventory.large),
            ("code files", inventory.code_files),
        ):
            if values:
                code_lines.append(f"  - {label}: {', '.join(values)}")
    output_section("Code Evidence", code_lines)

    media_lines = [f"- {item}" for item in path_list(round_dir, media)]
    if media:
        media_lines.insert(
            0, "- Media/demo artifacts are inventoried only; visual/video content was not inspected by this command."
        )
    output_section("Demo And Media", media_lines)

    output_section("Generated Outputs", output_lines + manifest_lines)

    output_section("Agent Role Coverage", agent_coverage_summary(round_dir, issues))

    output_section(
        "Operation Log",
        operation_log_summary_lines(round_dir, case_id=args.case_id, round_id=round_id),
    )

    issue_lines = [f"- {issue.severity}: {issue.message}" for issue in issues]
    output_section(
        "Issues / Next Actions",
        issue_lines if issue_lines else ["- OK: no blocking findings or warnings from this read-only diagnostic."],
    )

    return 1 if any(issue.severity == "ERROR" for issue in issues) else 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
