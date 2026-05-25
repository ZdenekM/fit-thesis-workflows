"""Command execution and preflight step helpers."""

from __future__ import annotations

import os
import shlex
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROCESS_GROUP_MODE_ENV = "THESIS_REVIEW_PROCESS_GROUP_MODE"
PROCESS_GROUP_MODE_INHERIT = "inherit"

WORKFLOW_COMMAND_MODULES = {
    "audit-context-budget": "thesis_review_workflow.cli.audit_context_budget",
    "bootstrap-case": "thesis_review_workflow.cli.bootstrap_case",
    "case-doctor": "thesis_review_workflow.cli.case_doctor",
    "check-agent-coverage": "thesis_review_workflow.cli.check_agent_coverage",
    "check-assignment-coverage": "thesis_review_workflow.cli.check_assignment_coverage",
    "check-code-consistency": "thesis_review_workflow.cli.check_code_consistency",
    "check-code-quality-review": "thesis_review_workflow.cli.check_code_quality_review",
    "check-code-reproducibility": "thesis_review_workflow.cli.check_code_reproducibility",
    "check-evidence-presence": "thesis_review_workflow.cli.check_evidence_presence",
    "check-evaluation-claims": "thesis_review_workflow.cli.check_evaluation_claims",
    "check-external-opponent-feedback": "thesis_review_workflow.cli.check_external_opponent_feedback",
    "check-feedback-language": "thesis_review_workflow.cli.check_feedback_language",
    "check-feedback-output": "thesis_review_workflow.cli.check_feedback_output",
    "check-figure-media-review": "thesis_review_workflow.cli.check_figure_media_review",
    "check-literature-citation-review": "thesis_review_workflow.cli.check_literature_citation_review",
    "check-opponent-calibration-case": "thesis_review_workflow.cli.check_opponent_calibration_case",
    "check-opponent-calibration-profile": "thesis_review_workflow.cli.check_opponent_calibration_profile",
    "check-opponent-materials": "thesis_review_workflow.cli.check_opponent_materials",
    "check-opponent-report": "thesis_review_workflow.cli.check_opponent_report",
    "check-private": "thesis_review_workflow.cli.check_private",
    "check-report-calibration": "thesis_review_workflow.cli.check_report_calibration",
    "check-review-manifest": "thesis_review_workflow.cli.check_review_manifest",
    "check-review-materiality": "thesis_review_workflow.cli.check_review_materiality",
    "check-review-wave": "thesis_review_workflow.cli.check_review_wave",
    "check-reviewer-profile": "thesis_review_workflow.cli.check_reviewer_profile",
    "check-revision-diff": "thesis_review_workflow.cli.check_revision_diff",
    "check-round-ready": "thesis_review_workflow.cli.check_round_ready",
    "check-scripts": "thesis_review_workflow.cli.check_scripts",
    "check-supervisor-report": "thesis_review_workflow.cli.check_supervisor_report",
    "check-supervisor-report-calibration-profile": (
        "thesis_review_workflow.cli.check_supervisor_report_calibration_profile"
    ),
    "check-supervisor-report-ready": "thesis_review_workflow.cli.check_supervisor_report_ready",
    "check-supervisor-ready": "thesis_review_workflow.cli.check_supervisor_ready",
    "check-theses-similarity-report": "thesis_review_workflow.cli.check_theses_similarity_report",
    "check-theses-checker-summary": "thesis_review_workflow.cli.check_theses_checker_summary",
    "check-tooling": "thesis_review_workflow.cli.check_tooling",
    "check-typography-formal": "thesis_review_workflow.cli.check_typography_formal",
    "confirm-supervisor-report": "thesis_review_workflow.cli.confirm_supervisor_report",
    "draft-opponent-report": "thesis_review_workflow.cli.draft_opponent_report",
    "draft-supervisor-report": "thesis_review_workflow.cli.draft_supervisor_report",
    "export-opponent-report": "thesis_review_workflow.cli.export_opponent_report",
    "extract-pdf-text": "thesis_review_workflow.cli.extract_pdf_text",
    "import-github-code": "thesis_review_workflow.cli.import_github_code",
    "import-round": "thesis_review_workflow.cli.import_round",
    "import-theses-report": "thesis_review_workflow.cli.import_theses_report",
    "init-review-manifest": "thesis_review_workflow.cli.init_review_manifest",
    "inventory-submission-bundle": "thesis_review_workflow.cli.inventory_submission_bundle",
    "materialize-submission-bundle": "thesis_review_workflow.cli.materialize_submission_bundle",
    "materialize-submission-bundle-candidate": ("thesis_review_workflow.cli.materialize_submission_bundle_candidate"),
    "new-case": "thesis_review_workflow.cli.new_case",
    "opponent-closeout": "thesis_review_workflow.cli.opponent_closeout",
    "opponent-preflight": "thesis_review_workflow.cli.opponent_preflight",
    "prepare-review-round": "thesis_review_workflow.cli.prepare_review_round",
    "prepare-opponent-packets": "thesis_review_workflow.cli.prepare_opponent_packets",
    "prepare-supervisor-report-packets": "thesis_review_workflow.cli.prepare_supervisor_report_packets",
    "prepare-supervisor-packets": "thesis_review_workflow.cli.prepare_supervisor_packets",
    "prepare-code-workspace": "thesis_review_workflow.cli.prepare_code_workspace",
    "record-report-amendment": "thesis_review_workflow.cli.record_report_amendment",
    "record-review-delta": "thesis_review_workflow.cli.record_review_delta",
    "record-submitted-opponent-report": "thesis_review_workflow.cli.record_submitted_opponent_report",
    "record-submitted-report-delta": "thesis_review_workflow.cli.record_submitted_report_delta",
    "record-submitted-supervisor-report": "thesis_review_workflow.cli.record_submitted_supervisor_report",
    "record-theses-checker-summary": "thesis_review_workflow.cli.record_theses_checker_summary",
    "record-workflow-operation": "thesis_review_workflow.cli.record_workflow_operation",
    "refresh-round-hashes": "thesis_review_workflow.cli.refresh_round_hashes",
    "register-review-artifact": "thesis_review_workflow.cli.register_review_artifact",
    "review-round-closeout": "thesis_review_workflow.cli.review_round_closeout",
    "review-round-start": "thesis_review_workflow.cli.review_round_start",
    "supervisor-report-closeout": "thesis_review_workflow.cli.supervisor_report_closeout",
    "supervisor-deadline": "thesis_review_workflow.cli.supervisor_deadline",
    "update-current-evidence-snapshot": "thesis_review_workflow.cli.update_current_evidence_snapshot",
    "update-round-reuse-index": "thesis_review_workflow.cli.update_round_reuse_index",
    "write-review-approval": "thesis_review_workflow.cli.write_review_approval",
}


@dataclass(frozen=True)
class Step:
    label: str
    command: list[str] | None
    returncode: int
    output: str
    required: bool = True
    elapsed_seconds: float | None = None
    recovery_command: str | None = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def status(self) -> str:
        if self.ok:
            return "PASS"
        return "FAIL" if self.required else "WARN"


def command_display(args: list[str] | None) -> str:
    if not args:
        return ""
    tool_name = workflow_command_name(args[0])
    if os.name == "nt" and tool_name is not None:
        return subprocess.list2cmdline([f".\\dist\\workflow-tools\\bin\\{tool_name}.cmd", *args[1:]])
    return shlex.join(canonical_command_args(args))


def canonical_command_args(args: list[str]) -> list[str]:
    if not args:
        return args
    tool_name = workflow_command_name(args[0])
    if tool_name is None:
        return args
    return [tool_name, *args[1:]]


def canonical_command_text(command: str) -> str:
    try:
        args = shlex.split(command, posix="\\" not in command)
    except ValueError:
        return command
    args = [arg.strip("\"'") for arg in args]
    return " ".join(canonical_command_args(args))


def compact_output(value: str, *, limit: int) -> str:
    lines = [line.rstrip() for line in value.splitlines() if line.strip()]
    text = "\n".join(lines)
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def repo_command_environment(root: Path, *, extra_env: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(root / "src")
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not current else src_path + os.pathsep + current
    if extra_env:
        env.update(extra_env)
    return env


def workflow_command_module(command: str) -> str | None:
    tool_name = workflow_command_name(command)
    if tool_name is None:
        return None
    return WORKFLOW_COMMAND_MODULES.get(tool_name)


def workflow_command_name(command: str) -> str | None:
    normalized = command.replace("\\", "/")
    stripped = normalized.removeprefix("./")
    name = stripped.rsplit("/", 1)[-1]
    for suffix in (".cmd", ".ps1"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    if "/" in stripped and not (stripped.startswith("scripts/") or stripped.startswith("dist/workflow-tools/bin/")):
        return None
    if name in WORKFLOW_COMMAND_MODULES:
        return name
    return None


def resolve_repo_command(root: Path, args: list[str]) -> list[str]:
    module = workflow_command_module(args[0])
    if module is not None:
        return [sys.executable, "-m", module, *args[1:]]
    executable = root / args[0]
    if executable.exists():
        return [str(executable), *args[1:]]
    return args


def terminate_process_tree(process: subprocess.Popen[str], *, timeout: float = 5.0) -> bool:
    if process.poll() is not None:
        return True
    if os.name == "nt":
        try:
            process.send_signal(getattr(signal, "CTRL_BREAK_EVENT", signal.SIGTERM))
            process.wait(timeout=timeout)
            return True
        except (OSError, subprocess.TimeoutExpired):
            pass
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        try:
            process.wait(timeout=timeout)
            return True
        except (OSError, subprocess.TimeoutExpired):
            return process.poll() is not None
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=timeout)
        return True
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        process.kill()
    try:
        process.wait(timeout=timeout)
        return True
    except (OSError, subprocess.TimeoutExpired):
        return process.poll() is not None


def run_step(
    root: Path,
    label: str,
    args: list[str],
    *,
    required: bool = True,
    extra_env: dict[str, str] | None = None,
) -> Step:
    started = time.monotonic()
    resolved = resolve_repo_command(root, args)
    env = repo_command_environment(root, extra_env=extra_env)
    inherit_process_group = os.environ.get(PROCESS_GROUP_MODE_ENV) == PROCESS_GROUP_MODE_INHERIT
    if os.name == "nt" and not inherit_process_group:
        process = subprocess.Popen(
            resolved,
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)),
        )
    elif os.name == "nt":
        process = subprocess.Popen(
            resolved,
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    elif inherit_process_group:
        process = subprocess.Popen(
            resolved,
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    else:
        process = subprocess.Popen(
            resolved,
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    try:
        stdout, _ = process.communicate()
    except KeyboardInterrupt:
        if not terminate_process_tree(process):
            print(f"WARNING: helper process tree may still be running for pid {process.pid}", file=sys.stderr)
        raise
    elapsed = time.monotonic() - started
    return Step(
        label=label,
        command=args,
        returncode=process.returncode if process.returncode is not None else 1,
        output=(stdout or "").strip(),
        required=required,
        elapsed_seconds=elapsed,
    )


def print_step(step: Step, *, output_limit: int) -> None:
    print()
    print(f"## {step.label}: {step.status}")
    if step.command is not None:
        print(f"$ {command_display(step.command)}")
    if step.elapsed_seconds is not None:
        print(f"elapsed: {step.elapsed_seconds:.1f}s")
    if step.output:
        print(compact_output(step.output, limit=output_limit))
