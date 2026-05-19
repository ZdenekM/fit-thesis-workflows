"""Pure summary helpers for the case-doctor CLI."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_classification import (
    CODE_DEPENDENCY_NAMES,
    CODE_SUFFIXES,
    archive_entry_code_like,
    archive_may_be_code_from_name,
    archive_suffix,
    archive_top_entries,
    folded,
    is_archive,
)
from thesis_review_workflow.artifact_registry import final_output_filenames, known_output_labels
from thesis_review_workflow.paths import rel_round

MAX_LIST = 12
KNOWN_OUTPUTS = known_output_labels()
FINAL_OUTPUTS = final_output_filenames()
__all__ = [
    "ArchiveInfo",
    "CODE_SUFFIXES",
    "DirectoryInventory",
    "GateResult",
    "Issue",
    "add_issue",
    "agent_coverage_summary_lines",
    "archive_entry_code_like",
    "archive_may_be_code_from_name",
    "archive_suffix",
    "archive_top_entries",
    "compact_output",
    "file_size_label",
    "folded",
    "gate_failure_severity",
    "is_archive",
    "manifest_summary_lines",
    "matching_extract",
    "nonempty_lines",
    "one_line",
    "output_expectations",
    "path_list",
]


@dataclass(frozen=True)
class Issue:
    severity: str
    message: str


@dataclass(frozen=True)
class GateResult:
    name: str
    command: str
    returncode: int
    output: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass(frozen=True)
class ArchiveInfo:
    path: Path
    size: int
    entry_count: int | None
    top_entries: list[str]
    code_like: bool
    code_unknown: bool
    note: str


@dataclass(frozen=True)
class DirectoryInventory:
    path: Path
    files_seen: int
    truncated: bool
    readmes: list[str]
    dependencies: list[str]
    tests: list[str]
    ci: list[str]
    large: list[str]
    code_files: list[str]

    @property
    def code_like(self) -> bool:
        return bool(
            self.code_files or self.tests or any(Path(item).name in CODE_DEPENDENCY_NAMES for item in self.dependencies)
        )


def add_issue(issues: list[Issue], severity: str, message: str) -> None:
    issues.append(Issue(severity, message))


def file_size_label(size: int) -> str:
    if size >= 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024 * 1024):.1f} GiB"
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MiB"
    if size >= 1024:
        return f"{size / 1024:.1f} KiB"
    return f"{size} B"


def nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def one_line(text: str) -> str:
    lines = nonempty_lines(text)
    if lines:
        return lines[0]
    return "(no output)"


def compact_output(text: str, *, max_lines: int = 3) -> str:
    lines = nonempty_lines(text)
    if not lines:
        return "(no output)"
    selected = lines[:max_lines]
    if len(lines) > max_lines:
        selected.append("...")
    return " | ".join(selected)


def is_thesis_pdf_name(value: str) -> bool:
    tokens = ("thesis", "prace", "bakalar", "diplom")
    if any(token in value for token in tokens):
        return True
    return bool(re.search(r"(^|[_ .-])(bp|dp)([_ .-]|$)", value))


def matching_extract(
    pdf: Path,
    extracted: list[Path],
    *,
    pdf_count: int,
    used_extracts: set[Path],
    known_mappings: Mapping[Path, Path] | None = None,
) -> tuple[Path | None, str]:
    if known_mappings:
        expected = known_mappings.get(pdf)
        if expected is not None:
            if expected in extracted and expected not in used_extracts:
                return expected, "registered mapping"
            return None, ""

    by_stem = {path.stem: path for path in extracted}
    exact = by_stem.get(pdf.stem)
    if exact is not None and exact not in used_extracts:
        return exact, "same-stem"

    pdf_name = folded(pdf.stem)
    assignment_tokens = ("zadani", "assignment")
    if any(token in pdf_name for token in assignment_tokens):
        for path in extracted:
            if path in used_extracts:
                continue
            extract_name = folded(path.stem)
            if any(token in extract_name for token in assignment_tokens):
                return path, "assignment heuristic"
    elif is_thesis_pdf_name(pdf_name):
        for path in extracted:
            if path in used_extracts:
                continue
            extract_name = folded(path.stem)
            if extract_name in {"thesis", "prace", "bp", "dp"} or "thesis" in extract_name:
                return path, "thesis heuristic"

    if pdf_count == 1 and len(extracted) == 1 and extracted[0] not in used_extracts:
        return extracted[0], "single-extract heuristic"
    return None, ""


def path_list(round_dir: Path, paths: list[Path], *, max_items: int = MAX_LIST) -> list[str]:
    items = [rel_round(round_dir, path) for path in sorted(paths)]
    if len(items) > max_items:
        return items[:max_items] + [f"... {len(items) - max_items} more"]
    return items


def manifest_summary_lines(
    *,
    manifest_present: bool,
    outputs_present: bool,
    manifest_error: str | None,
    artifacts: Any,
    supporting_work_artifacts: Any,
    helper_checks: Any,
    coverage_needed: bool,
    coverage_present: bool,
    manifest_rel: str,
    coverage_rel: str,
    issues: list[Issue],
) -> list[str]:
    if not manifest_present:
        if outputs_present:
            add_issue(issues, "ERROR", f"Generated outputs exist but {manifest_rel} is missing.")
        return ["- review manifest: missing"]
    if manifest_error:
        add_issue(issues, "ERROR", f"Review manifest JSON is invalid: {manifest_error}.")
        return [f"- review manifest: invalid JSON ({manifest_error})"]

    lines = [f"- review manifest: present ({manifest_rel})"]
    if coverage_needed:
        if coverage_present:
            lines.append(f"- agent coverage: present ({coverage_rel})")
        else:
            add_issue(issues, "ERROR", f"Required agent coverage is missing: {coverage_rel}.")
            lines.append(f"- agent coverage: missing ({coverage_rel})")
    elif coverage_present:
        lines.append(f"- agent coverage: present but no default role trigger is active ({coverage_rel})")
    else:
        lines.append("- agent coverage: not required")

    if isinstance(artifacts, list):
        lines.append(f"- manifest artifacts: {len(artifacts)}")
    else:
        add_issue(issues, "ERROR", "Review manifest artifacts field is not a list.")
        lines.append("- manifest artifacts: invalid")
    if isinstance(supporting_work_artifacts, list):
        lines.append(f"- supporting work artifacts: {len(supporting_work_artifacts)}")
    else:
        add_issue(issues, "ERROR", "Review manifest supporting_work_artifacts field is not a list.")
        lines.append("- supporting work artifacts: invalid")
    if isinstance(helper_checks, list):
        lines.append(f"- manifest helper checks: {len(helper_checks)}")
    else:
        add_issue(issues, "ERROR", "Review manifest helper_checks field is not a list.")
        lines.append("- manifest helper checks: invalid")
    return lines


def agent_coverage_summary_lines(
    *,
    specs: Mapping[str, Any],
    coverage: Any,
    coverage_error: str | None,
    evidence_exists: Callable[[str], bool],
    issues: list[Issue],
) -> list[str]:
    if coverage_error:
        add_issue(issues, "ERROR", f"Agent coverage JSON is invalid: {coverage_error}.")
        coverage = None
    records: dict[str, dict[str, Any]] = {}
    if coverage and isinstance(coverage.get("roles"), list):
        for item in coverage["roles"]:
            if isinstance(item, dict) and isinstance(item.get("role"), str):
                records[item["role"]] = item

    if not specs and not records:
        return ["- no required role coverage for current round state"]

    lines: list[str] = []
    for role, spec in sorted(specs.items()):
        record = records.get(role)
        if not record:
            lines.append(f"- MISSING {role}: needs {spec.skill} -> {spec.evidence_path}")
            continue
        status = str(record.get("status", ""))
        evidence = ", ".join(str(item) for item in record.get("output_evidence", [])) or spec.evidence_path
        missing: list[str] = []
        if status == "required":
            if spec.evidence_path not in record.get("output_evidence", []):
                missing.append("output_evidence")
            elif not evidence_exists(spec.evidence_path):
                missing.append("output_file")
            if str(record.get("generator_agent", "")).strip() in {"", "not_recorded"}:
                missing.append("generator_agent")
            if str(record.get("generator_role", "")).strip() in {"", "not_recorded"}:
                missing.append("generator_role")
            if spec.requires_review:
                if str(record.get("reviewer_agent", "")).strip() in {"", "not_recorded"}:
                    missing.append("reviewer_agent")
                if str(record.get("reviewer_role", "")).strip() in {"", "not_recorded"}:
                    missing.append("reviewer_role")
                if not str(record.get("reviewed_hash", "")).strip():
                    missing.append("reviewed_hash")
        elif status == "blocked":
            limitation = record.get("typed_limitation")
            limitation_type = limitation.get("type") if isinstance(limitation, dict) else "(missing limitation)"
            missing.append(f"blocked:{limitation_type}")
        detail = f"; missing {', '.join(missing)}" if missing else ""
        lines.append(f"- {status.upper()} {role}: {spec.skill}; evidence {evidence}{detail}")

    for role in sorted(set(records) - set(specs)):
        record = records[role]
        lines.append(f"- STALE {role}: status {record.get('status', '(missing)')}; no current default trigger")
    return lines


def output_expectations(
    output_names: set[str],
    *,
    feedback_draft_present: bool,
    opponent_materials_draft_present: bool,
    reviewed_opponent_materials_present: bool,
    opponent_report_trace_present: bool,
    opponent_report_draft_present: bool,
    opponent_report_review_present: bool,
    code_present: bool,
    issues: list[Issue],
) -> list[str]:
    lines: list[str] = []
    for name in sorted(KNOWN_OUTPUTS):
        marker = "present" if name in output_names else "missing"
        if name in output_names or name in {"feedback_student.md", "oponent_podklady_revidovane.md"}:
            lines.append(f"- {name}: {marker} ({KNOWN_OUTPUTS[name]})")

    if feedback_draft_present and "feedback_student.md" not in output_names:
        add_issue(issues, "WARNING", "Supervisor feedback draft exists but outputs/feedback_student.md is missing.")
    if opponent_materials_draft_present and "oponent_podklady_revidovane.md" not in output_names:
        add_issue(issues, "WARNING", "Opponent materials draft exists but reviewed output is missing.")
    if reviewed_opponent_materials_present and not opponent_report_trace_present:
        add_issue(
            issues, "WARNING", "Reviewed opponent materials exist but work/opponent_report_trace.json is missing."
        )
        lines.append("- work/opponent_report_trace.json: missing (opponent report trace)")
    elif opponent_report_trace_present:
        lines.append("- work/opponent_report_trace.json: present (opponent report trace)")
    if opponent_report_draft_present:
        lines.append("- work/oponent_posudek_draft.md: present (opponent report draft)")
        if not opponent_report_review_present:
            add_issue(
                issues, "WARNING", "Opponent report draft exists but outputs/feedback_k_posudku.md review is missing."
            )

    if code_present and output_names & FINAL_OUTPUTS:
        missing = [name for name in ("code_consistency.md", "code_quality_review.md") if name not in output_names]
        if missing:
            add_issue(
                issues,
                "ERROR",
                "Final synthesis exists with code evidence but missing code review outputs: "
                + ", ".join(f"outputs/{name}" for name in missing)
                + ".",
            )
    return lines


def gate_failure_severity(gate: GateResult, output_names: set[str], *, feedback_draft_present: bool) -> str:
    supervisor_feedback_surface = "feedback_student.md" in output_names or feedback_draft_present
    if gate.name in {"supervisor deadline", "supervisor readiness"} and not supervisor_feedback_surface:
        return "WARNING"
    return "ERROR"
