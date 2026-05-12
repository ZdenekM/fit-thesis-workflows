"""Create a formal supervisor-report draft from structured trace data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.commands import command_display, run_step
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.structured_evidence import (
    SUPERVISOR_REPORT_TRACE_REL,
    validate_structured_evidence_artifact,
)
from thesis_review_workflow.supervisor_report import SUPERVISOR_REPORT_DRAFT_REL, SUPERVISOR_REPORT_INPUT_REL

REPORT_FIELD_ORDER = (
    ("assignment_information", "Informace k zadání"),
    ("literature_work", "Práce s literaturou"),
    ("activity_during_solution", "Aktivita během řešení, konzultace, komunikace"),
    ("completion_activity", "Aktivita při dokončování"),
    ("publication_activity", "Publikační činnost, ocenění"),
    ("overall_assessment", "Celkové hodnocení"),
    ("student_comment", "Komentář pro studenta"),
)


def run_required(root: Path, label: str, command: list[str]) -> None:
    result = run_step(root, label, command)
    if not result.ok:
        detail = f"\n{result.output}" if result.output else ""
        raise SystemExit(f"Required command failed: {command_display(command)}{detail}")


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {label}: {exc.msg}") from exc
    if not isinstance(loaded, dict):
        raise SystemExit(f"Invalid JSON in {label}: expected object")
    return loaded


def load_valid_trace(round_dir: Path, case_id: str, round_id: str) -> dict[str, Any]:
    errors = validate_structured_evidence_artifact(
        round_dir,
        SUPERVISOR_REPORT_TRACE_REL,
        case_id=case_id,
        round_id=round_id,
    )
    if errors:
        detail = "\n".join(f"ERROR: {error}" for error in errors)
        raise SystemExit(
            "Missing or invalid `work/supervisor_report_trace.json`; create it with an explicitly "
            f"authorized supervisor-report agent before drafting.\n{detail}"
        )
    return load_json_object(round_dir / SUPERVISOR_REPORT_TRACE_REL, SUPERVISOR_REPORT_TRACE_REL)


def report_fields_by_id(trace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fields = trace.get("report_fields")
    if not isinstance(fields, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for field in fields:
        if isinstance(field, dict) and isinstance(field.get("field_id"), str):
            result[field["field_id"]] = field
    return result


def grading_lines(trace: dict[str, Any]) -> list[str]:
    grading = trace.get("grading")
    if not isinstance(grading, dict):
        return ["Známka: k ruční kalibraci", "Body: k ruční kalibraci"]
    grade = grading.get("grade")
    points = grading.get("points")
    points_interval = grading.get("points_interval")
    lines: list[str] = []
    if isinstance(grade, str) and grade in {"A", "B", "C", "D", "E", "F"}:
        lines.append(f"Známka: {grade}")
    else:
        lines.append("Známka: k ruční kalibraci")
    if isinstance(points, int):
        lines.append(f"Body: {points}")
    else:
        lines.append("Body: k ruční kalibraci")
        if isinstance(points_interval, str) and points_interval.strip():
            lines.append(f"Orientační bodové rozmezí k ověření: {points_interval.strip()}")
    rationale = grading.get("rationale")
    if isinstance(rationale, str) and rationale.strip():
        lines.append("")
        lines.append(rationale.strip())
    return lines


def build_report(trace: dict[str, Any], *, trace_hash: str, input_hash: str) -> str:
    fields = report_fields_by_id(trace)
    lines = [
        f"<!-- source_trace_path: {SUPERVISOR_REPORT_TRACE_REL} -->",
        f"<!-- source_trace_sha256: {trace_hash} -->",
        f"<!-- supervisor_input_path: {SUPERVISOR_REPORT_INPUT_REL} -->",
        f"<!-- supervisor_input_sha256: {input_hash} -->",
        "# Návrh posudku vedoucího",
        "",
    ]
    for field_id, title in REPORT_FIELD_ORDER:
        field = fields[field_id]
        lines.append(f"## {title}")
        lines.append("")
        lines.append(str(field["formulation"]).strip())
        if field_id == "overall_assessment":
            lines.append("")
            lines.extend(grading_lines(trace))
        lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/draft-supervisor-report",
        description="Create work/vedouci_posudek_draft.md from work/supervisor_report_trace.json.",
    )
    parser.add_argument("--force", action="store_true", help=f"overwrite an existing {SUPERVISOR_REPORT_DRAFT_REL}")
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    run_required(root, "supervisor report readiness", ["scripts/check-supervisor-report-ready", args.case_id, round_id])
    trace = load_valid_trace(round_dir, args.case_id, round_id)

    draft_path = round_dir / SUPERVISOR_REPORT_DRAFT_REL
    if draft_path.exists() and not args.force:
        raise SystemExit(f"Refusing to overwrite existing draft without --force: {SUPERVISOR_REPORT_DRAFT_REL}")
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(
        build_report(
            trace,
            trace_hash=sha256_file(round_dir / SUPERVISOR_REPORT_TRACE_REL),
            input_hash=sha256_file(round_dir / SUPERVISOR_REPORT_INPUT_REL),
        ),
        encoding="utf-8",
    )
    run_required(
        root, "supervisor report draft validation", ["scripts/check-supervisor-report", args.case_id, round_id]
    )
    print(f"Wrote {rel_repo(root, draft_path)}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
