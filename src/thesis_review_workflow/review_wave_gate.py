"""Shared checks for thesis-review agent wave outputs."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from thesis_review_workflow import agent_coverage
from thesis_review_workflow.commands import repo_command_environment, resolve_repo_command
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.review_approvals import require_review_approval_path, validate_review_approval_artifact
from thesis_review_workflow.review_materiality import unresolved_required_next_actions

DEFAULT_HANDOFF_HEADING = "## Synthesis Handoff"


@dataclass(frozen=True)
class CheckCommand:
    args: tuple[str, ...]
    required: bool = True


@dataclass(frozen=True)
class ApprovalRecordExpectation:
    path: str
    reviewed_artifact_path: str = ""


@dataclass(frozen=True)
class ExpectedOutput:
    role: str
    paths: tuple[str, ...]
    checks: tuple[CheckCommand, ...] = ()
    handoff_heading: str = DEFAULT_HANDOFF_HEADING
    handoff_required: bool = False
    owned_paths: tuple[str, ...] = ()
    approval_record: ApprovalRecordExpectation | None = None


@dataclass(frozen=True)
class WaveSpec:
    workflow: str
    wave: str
    outputs: tuple[ExpectedOutput, ...]


@dataclass
class GateResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def merge(self, other: "GateResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.passed.extend(other.passed)


def _safe_rel_path(value: str, *, label: str) -> str:
    if not is_safe_round_relative_path(value):
        raise ValueError(f"{label} must be a safe round-relative path: {value}")
    return value


def _check_command_from_json(value: Any) -> CheckCommand:
    required = True
    args_value: Any = value
    if isinstance(value, dict):
        args_value = value.get("args")
        required = bool(value.get("required", True))
    if not isinstance(args_value, list) or not all(isinstance(item, str) for item in args_value):
        raise ValueError("check command must be a list of strings or an object with an args list")
    if not args_value:
        raise ValueError("check command args must not be empty")
    return CheckCommand(tuple(args_value), required=required)


def _approval_from_json(value: Any) -> ApprovalRecordExpectation | None:
    if value in (None, "", False):
        return None
    if isinstance(value, str):
        path = _safe_rel_path(value, label="approval_record")
        require_review_approval_path(path)
        return ApprovalRecordExpectation(path)
    if not isinstance(value, dict):
        raise ValueError("approval_record must be a path string or object")
    approval_path_value = value.get("path")
    if not isinstance(approval_path_value, str):
        raise ValueError("approval_record.path must be a string")
    reviewed = value.get("reviewed_artifact_path", "")
    if reviewed is not None and not isinstance(reviewed, str):
        raise ValueError("approval_record.reviewed_artifact_path must be a string")
    if reviewed:
        _safe_rel_path(reviewed, label="approval_record.reviewed_artifact_path")
    safe_path = _safe_rel_path(approval_path_value, label="approval_record.path")
    require_review_approval_path(safe_path)
    return ApprovalRecordExpectation(
        safe_path,
        reviewed_artifact_path=reviewed or "",
    )


def expected_output_from_json(value: Any) -> ExpectedOutput:
    if not isinstance(value, dict):
        raise ValueError("expected output must be an object")
    role = value.get("role")
    if not isinstance(role, str) or not role.strip():
        raise ValueError("expected output role must be a non-empty string")

    if "paths" in value:
        raw_paths = value["paths"]
        if not isinstance(raw_paths, list) or not all(isinstance(item, str) for item in raw_paths):
            raise ValueError(f"{role}: paths must be a list of strings")
        paths = tuple(_safe_rel_path(item, label=f"{role}.paths") for item in raw_paths)
    else:
        path = value.get("path")
        if not isinstance(path, str):
            raise ValueError(f"{role}: path must be a string when paths is absent")
        paths = (_safe_rel_path(path, label=f"{role}.path"),)
    if not paths:
        raise ValueError(f"{role}: at least one path is required")

    raw_checks = value.get("checks", [])
    if not isinstance(raw_checks, list):
        raise ValueError(f"{role}: checks must be a list")
    checks = tuple(_check_command_from_json(item) for item in raw_checks)

    raw_owned_paths = value.get("owned_paths", [])
    if not isinstance(raw_owned_paths, list) or not all(isinstance(item, str) for item in raw_owned_paths):
        raise ValueError(f"{role}: owned_paths must be a list of strings")
    owned_paths = tuple(_safe_rel_path(item, label=f"{role}.owned_paths") for item in raw_owned_paths)

    handoff_heading = value.get("handoff_heading", DEFAULT_HANDOFF_HEADING)
    if not isinstance(handoff_heading, str) or not handoff_heading.strip():
        raise ValueError(f"{role}: handoff_heading must be a non-empty string")

    return ExpectedOutput(
        role=role,
        paths=paths,
        checks=checks,
        handoff_heading=handoff_heading,
        handoff_required=bool(value.get("handoff_required", False)),
        owned_paths=owned_paths,
        approval_record=_approval_from_json(value.get("approval_record")),
    )


def wave_spec_from_json(payload: dict[str, Any]) -> WaveSpec:
    workflow = payload.get("workflow") or payload.get("profile") or "custom"
    wave = payload.get("wave") or "custom"
    outputs = payload.get("outputs")
    if not isinstance(workflow, str) or not workflow.strip():
        raise ValueError("workflow/profile must be a non-empty string")
    if not isinstance(wave, str) or not wave.strip():
        raise ValueError("wave must be a non-empty string")
    if not isinstance(outputs, list) or not outputs:
        raise ValueError("outputs must be a non-empty list")
    return WaveSpec(
        workflow=workflow,
        wave=wave,
        outputs=tuple(expected_output_from_json(item) for item in outputs),
    )


def load_wave_spec(path: Path) -> WaveSpec:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid wave spec JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("wave spec JSON must be an object")
    return wave_spec_from_json(payload)


def _check(*args: str, required: bool = True) -> CheckCommand:
    return CheckCommand(args, required=required)


def builtin_wave_spec(workflow: str, wave: str) -> WaveSpec:
    normalized_workflow = workflow.replace("-", "_")
    normalized_wave = wave.replace("-", "_")
    key = (normalized_workflow, normalized_wave)

    specs: dict[tuple[str, str], WaveSpec] = {
        (
            "supervisor_feedback",
            "draft",
        ): WaveSpec(
            workflow="supervisor_feedback",
            wave="draft",
            outputs=(
                ExpectedOutput(
                    role="supervisor_feedback_draft",
                    paths=("work/feedback_student_draft.md",),
                    checks=(
                        _check("check-feedback-language", "--artifact", "work/feedback_student_draft.md"),
                        _check("check-feedback-output", "--artifact", "work/feedback_student_draft.md"),
                    ),
                ),
            ),
        ),
        (
            "supervisor_feedback",
            "final",
        ): WaveSpec(
            workflow="supervisor_feedback",
            wave="final",
            outputs=(
                ExpectedOutput(
                    role="supervisor_feedback_final",
                    paths=("outputs/feedback_student.md",),
                    checks=(_check("check-feedback-language"), _check("check-feedback-output")),
                    approval_record=ApprovalRecordExpectation(
                        "work/reviews/supervisor_feedback_review.json",
                        reviewed_artifact_path="outputs/feedback_student.md",
                    ),
                ),
            ),
        ),
        (
            "opponent_materials",
            "draft",
        ): WaveSpec(
            workflow="opponent_materials",
            wave="draft",
            outputs=(
                ExpectedOutput(
                    role="opponent_materials_draft",
                    paths=("work/oponent_podklady_draft.md", "outputs/oponent_podklady.md"),
                ),
            ),
        ),
        (
            "opponent_materials",
            "reviewed",
        ): WaveSpec(
            workflow="opponent_materials",
            wave="reviewed",
            outputs=(
                ExpectedOutput(
                    role="opponent_materials_reviewed",
                    paths=("outputs/oponent_podklady_revidovane.md",),
                    checks=(_check("check-opponent-materials"),),
                    approval_record=ApprovalRecordExpectation(
                        "work/reviews/opponent_materials_review.json",
                        reviewed_artifact_path="outputs/oponent_podklady_revidovane.md",
                    ),
                ),
            ),
        ),
        (
            "opponent_report",
            "trace",
        ): WaveSpec(
            workflow="opponent_report",
            wave="trace",
            outputs=(
                ExpectedOutput(
                    role="opponent_report_trace",
                    paths=("work/opponent_report_trace.json",),
                    checks=(_check("check-opponent-report"),),
                ),
            ),
        ),
        (
            "opponent_report",
            "draft",
        ): WaveSpec(
            workflow="opponent_report",
            wave="draft",
            outputs=(
                ExpectedOutput(
                    role="opponent_report_draft",
                    paths=("work/oponent_posudek_draft.md",),
                    checks=(_check("check-opponent-report"),),
                ),
            ),
        ),
        (
            "opponent_report_review",
            "final",
        ): WaveSpec(
            workflow="opponent_report_review",
            wave="final",
            outputs=(
                ExpectedOutput(
                    role="opponent_report_review",
                    paths=("outputs/feedback_k_posudku.md",),
                    approval_record=ApprovalRecordExpectation(
                        "work/reviews/opponent_report_review.json",
                        reviewed_artifact_path="outputs/feedback_k_posudku.md",
                    ),
                ),
            ),
        ),
        (
            "supervisor_report",
            "trace",
        ): WaveSpec(
            workflow="supervisor_report",
            wave="trace",
            outputs=(
                ExpectedOutput(
                    role="supervisor_report_trace",
                    paths=("work/supervisor_report_trace.json",),
                    checks=(_check("check-supervisor-report"),),
                ),
            ),
        ),
        (
            "supervisor_report",
            "draft",
        ): WaveSpec(
            workflow="supervisor_report",
            wave="draft",
            outputs=(
                ExpectedOutput(
                    role="supervisor_report_draft",
                    paths=("work/vedouci_posudek_draft.md",),
                    checks=(_check("check-supervisor-report"),),
                ),
            ),
        ),
        (
            "supervisor_report",
            "final",
        ): WaveSpec(
            workflow="supervisor_report",
            wave="final",
            outputs=(
                ExpectedOutput(
                    role="supervisor_report_reviewed",
                    paths=("outputs/vedouci_posudek_revidovany.md",),
                    checks=(_check("check-supervisor-report", "--require-reviewed"),),
                    approval_record=ApprovalRecordExpectation(
                        "work/reviews/supervisor_report_review.json",
                        reviewed_artifact_path="outputs/vedouci_posudek_revidovany.md",
                    ),
                ),
            ),
        ),
    }
    try:
        return specs[key]
    except KeyError as exc:
        available = ", ".join(f"{profile}:{wave_name}" for profile, wave_name in sorted(specs))
        raise ValueError(f"unknown workflow/wave {workflow}:{wave}; available: {available}") from exc


def render_check_args(args: tuple[str, ...], *, case_id: str, round_id: str, selected_path: str) -> list[str]:
    return [item.format(case_id=case_id, round_id=round_id, selected_path=selected_path) for item in args]


def selected_output_path(round_dir: Path, expected: ExpectedOutput, result: GateResult) -> str | None:
    existing = [rel_path for rel_path in expected.paths if (round_dir / rel_path).is_file()]
    if not existing:
        choices = " or ".join(expected.paths)
        result.errors.append(f"{expected.role}: missing expected output: {choices}")
        return None
    if len(existing) > 1:
        result.warnings.append(f"{expected.role}: multiple alternative outputs exist; using {existing[0]}")
    return existing[0]


def check_nonempty(round_dir: Path, rel_path: str, role: str, result: GateResult) -> None:
    path = round_dir / rel_path
    try:
        if path.stat().st_size == 0:
            result.errors.append(f"{role}: expected output is empty: {rel_path}")
        else:
            result.passed.append(f"{role}: output exists and is non-empty: {rel_path}")
    except OSError as exc:
        result.errors.append(f"{role}: could not stat {rel_path}: {exc}")


def check_handoff(
    round_dir: Path,
    rel_path: str,
    expected: ExpectedOutput,
    result: GateResult,
    *,
    require_handoffs: bool,
) -> None:
    if not expected.handoff_required and not require_handoffs:
        return
    path = round_dir / rel_path
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        result.errors.append(f"{expected.role}: could not read {rel_path}: {exc}")
        return
    if expected.handoff_heading in text.splitlines():
        result.passed.append(f"{expected.role}: synthesis handoff present in {rel_path}")
        return
    message = f"{expected.role}: missing synthesis handoff heading {expected.handoff_heading!r} in {rel_path}"
    if expected.handoff_required or require_handoffs:
        result.errors.append(message)
    else:
        result.warnings.append(message)


def paths_for_hygiene(selected_path: str, expected: ExpectedOutput) -> tuple[str, ...]:
    paths = [selected_path]
    for rel_path in expected.owned_paths:
        if rel_path not in paths:
            paths.append(rel_path)
    if expected.approval_record and expected.approval_record.path not in paths:
        paths.append(expected.approval_record.path)
    return tuple(paths)


def check_whitespace(round_dir: Path, rel_paths: tuple[str, ...], role: str, result: GateResult) -> None:
    for rel_path in rel_paths:
        path = round_dir / rel_path
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            result.errors.append(f"{role}: could not read {rel_path} for whitespace check: {exc}")
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.endswith((" ", "\t")):
                result.errors.append(f"{role}: trailing whitespace in {rel_path}:{line_number}")
                break
        else:
            result.passed.append(f"{role}: whitespace check passed for {rel_path}")
        if text and not text.endswith("\n"):
            result.warnings.append(f"{role}: {rel_path} has no final newline")


def run_check_command(
    root: Path,
    args: list[str],
    *,
    case_id: str,
    round_id: str,
    role: str,
    required: bool,
    result: GateResult,
) -> None:
    command_args = args
    if case_id not in args and round_id not in args:
        command_args = [*args, case_id, round_id]
    command = resolve_repo_command(root, command_args)
    completed = subprocess.run(
        command,
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=repo_command_environment(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    label = " ".join(command_args)
    if completed.returncode == 0:
        result.passed.append(f"{role}: checker passed: {label}")
        return
    detail = "\n".join(line for line in (completed.stderr + completed.stdout).splitlines() if line.strip())
    message = f"{role}: checker failed ({label})" + (f":\n{detail}" if detail else "")
    if required:
        result.errors.append(message)
    else:
        result.warnings.append(message)


def validate_approval_record(
    round_dir: Path,
    expected: ExpectedOutput,
    selected_path: str,
    result: GateResult,
    *,
    case_id: str,
    round_id: str,
) -> None:
    approval = expected.approval_record
    if approval is None:
        return
    expected_reviewed = approval.reviewed_artifact_path or selected_path
    for error in validate_review_approval_artifact(
        round_dir,
        approval.path,
        case_id=case_id,
        round_id=round_id,
        reviewed_artifact_path=expected_reviewed,
    ):
        result.errors.append(f"{expected.role}: {error}")

    if result.ok:
        result.passed.append(f"{expected.role}: approval record shape passed: {approval.path}")


def validate_expected_output(
    root: Path,
    round_dir: Path,
    expected: ExpectedOutput,
    *,
    case_id: str,
    round_id: str,
    require_handoffs: bool,
) -> GateResult:
    result = GateResult()
    selected_path = selected_output_path(round_dir, expected, result)
    if selected_path is None:
        return result
    check_nonempty(round_dir, selected_path, expected.role, result)
    check_handoff(round_dir, selected_path, expected, result, require_handoffs=require_handoffs)
    check_whitespace(round_dir, paths_for_hygiene(selected_path, expected), expected.role, result)
    validate_approval_record(round_dir, expected, selected_path, result, case_id=case_id, round_id=round_id)
    for check in expected.checks:
        rendered = render_check_args(check.args, case_id=case_id, round_id=round_id, selected_path=selected_path)
        run_check_command(
            root,
            rendered,
            case_id=case_id,
            round_id=round_id,
            role=expected.role,
            required=check.required,
            result=result,
        )
    return result


def validate_wave(
    root: Path,
    round_dir: Path,
    spec: WaveSpec,
    *,
    case_id: str,
    round_id: str,
    require_handoffs: bool = False,
) -> GateResult:
    result = GateResult()
    check_materiality_next_actions(round_dir, spec, case_id=case_id, round_id=round_id, result=result)
    check_agent_coverage(round_dir, spec, case_id=case_id, round_id=round_id, result=result)
    for expected in spec.outputs:
        result.merge(
            validate_expected_output(
                root,
                round_dir,
                expected,
                case_id=case_id,
                round_id=round_id,
                require_handoffs=require_handoffs,
            )
        )
    return result


def check_agent_coverage(
    round_dir: Path,
    spec: WaveSpec,
    *,
    case_id: str,
    round_id: str,
    result: GateResult,
) -> None:
    if not agent_coverage_wave(spec):
        return
    manifest_path = round_dir / "work" / "review_manifest.json"
    coverage_path = round_dir / agent_coverage.COVERAGE_REL
    if not manifest_path.is_file():
        result.errors.append("agent coverage: work/review_manifest.json is required for final/reviewed waves")
        return
    try:
        manifest = agent_coverage.load_json_object(manifest_path)
        coverage = agent_coverage.load_json_object(coverage_path) if coverage_path.is_file() else None
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result.errors.append(f"agent coverage: could not load coverage inputs: {exc}")
        return
    if manifest is None:
        result.errors.append("agent coverage: work/review_manifest.json must contain a JSON object")
        return
    errors, warnings = agent_coverage.validate_coverage(coverage, manifest, case_id, round_id, round_dir)
    result.errors.extend(f"agent coverage: {error}" for error in errors)
    result.warnings.extend(f"agent coverage: {warning}" for warning in warnings)
    if not errors:
        result.passed.append("agent coverage clear")


def agent_coverage_wave(spec: WaveSpec) -> bool:
    workflow = spec.workflow.replace("-", "_")
    wave = spec.wave.replace("-", "_")
    return (workflow, wave) in {
        ("supervisor_feedback", "final"),
        ("supervisor_report", "final"),
        ("opponent_materials", "reviewed"),
        ("opponent_report_review", "final"),
    }


def check_materiality_next_actions(
    round_dir: Path,
    spec: WaveSpec,
    *,
    case_id: str,
    round_id: str,
    result: GateResult,
) -> None:
    workflow_profile = materiality_profile_for_wave(spec)
    if workflow_profile is None:
        return
    actions, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile=workflow_profile,
        case_id=case_id,
        round_id=round_id,
        require_index=True,
    )
    for error in errors:
        result.errors.append(f"materiality next actions: {error}")
    for action in actions:
        result.errors.append(
            "materiality next action unresolved: "
            f"{action.get('role')} requires {action.get('required_artifact_path')}: {action.get('reason')}"
        )
    if not errors and not actions:
        result.passed.append("materiality next actions clear")


def materiality_profile_for_wave(spec: WaveSpec) -> str | None:
    workflow = spec.workflow.replace("-", "_")
    wave = spec.wave.replace("-", "_")
    if workflow == "supervisor_feedback" and wave in {"draft", "final"}:
        return "supervisor_feedback"
    if workflow == "supervisor_report" and wave in {"trace", "draft", "final"}:
        return "supervisor_report"
    if workflow == "opponent_materials" and wave in {"draft", "reviewed"}:
        return "opponent_review"
    return None
