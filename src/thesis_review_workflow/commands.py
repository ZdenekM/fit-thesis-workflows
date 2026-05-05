"""Command execution and preflight step helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

WORKFLOW_COMMAND_MODULES = {
    "bootstrap-case": "thesis_review_workflow.cli.bootstrap_case",
    "case-doctor": "thesis_review_workflow.cli.case_doctor",
    "check-agent-coverage": "thesis_review_workflow.cli.check_agent_coverage",
    "check-evaluation-claims": "thesis_review_workflow.cli.check_evaluation_claims",
    "check-feedback-language": "thesis_review_workflow.cli.check_feedback_language",
    "check-feedback-output": "thesis_review_workflow.cli.check_feedback_output",
    "check-figure-media-review": "thesis_review_workflow.cli.check_figure_media_review",
    "check-opponent-materials": "thesis_review_workflow.cli.check_opponent_materials",
    "check-opponent-report": "thesis_review_workflow.cli.check_opponent_report",
    "check-private": "thesis_review_workflow.cli.check_private",
    "check-review-manifest": "thesis_review_workflow.cli.check_review_manifest",
    "check-reviewer-profile": "thesis_review_workflow.cli.check_reviewer_profile",
    "check-round-ready": "thesis_review_workflow.cli.check_round_ready",
    "check-supervisor-ready": "thesis_review_workflow.cli.check_supervisor_ready",
    "check-tooling": "thesis_review_workflow.cli.check_tooling",
    "check-typography-formal": "thesis_review_workflow.cli.check_typography_formal",
    "draft-opponent-report": "thesis_review_workflow.cli.draft_opponent_report",
    "extract-pdf-text": "thesis_review_workflow.cli.extract_pdf_text",
    "import-github-code": "thesis_review_workflow.cli.import_github_code",
    "import-round": "thesis_review_workflow.cli.import_round",
    "init-review-manifest": "thesis_review_workflow.cli.init_review_manifest",
    "new-case": "thesis_review_workflow.cli.new_case",
    "opponent-closeout": "thesis_review_workflow.cli.opponent_closeout",
    "opponent-preflight": "thesis_review_workflow.cli.opponent_preflight",
    "prepare-code-workspace": "thesis_review_workflow.cli.prepare_code_workspace",
    "supervisor-deadline": "thesis_review_workflow.cli.supervisor_deadline",
}


@dataclass(frozen=True)
class Step:
    label: str
    command: list[str] | None
    returncode: int
    output: str
    required: bool = True

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def status(self) -> str:
        if self.ok:
            return "PASS"
        return "FAIL" if self.required else "WARN"


def command_display(args: list[str] | None) -> str:
    return " ".join(args) if args else ""


def compact_output(value: str, *, limit: int) -> str:
    lines = [line.rstrip() for line in value.splitlines() if line.strip()]
    text = "\n".join(lines)
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def repo_command_environment(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(root / "src")
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not current else src_path + os.pathsep + current
    return env


def workflow_command_module(command: str) -> str | None:
    path = Path(command)
    if len(path.parts) == 2 and path.parts[0] == "scripts":
        return WORKFLOW_COMMAND_MODULES.get(path.name)
    if len(path.parts) == 1:
        return WORKFLOW_COMMAND_MODULES.get(path.name)
    return None


def resolve_repo_command(root: Path, args: list[str]) -> list[str]:
    module = workflow_command_module(args[0])
    if module is not None:
        return [sys.executable, "-m", module, *args[1:]]
    executable = root / args[0]
    if executable.exists():
        return [str(executable), *args[1:]]
    return args


def run_step(root: Path, label: str, args: list[str], *, required: bool = True) -> Step:
    completed = subprocess.run(
        resolve_repo_command(root, args),
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=repo_command_environment(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return Step(
        label=label,
        command=args,
        returncode=completed.returncode,
        output=completed.stdout.strip(),
        required=required,
    )


def print_step(step: Step, *, output_limit: int) -> None:
    print()
    print(f"## {step.label}: {step.status}")
    if step.command is not None:
        print(f"$ {command_display(step.command)}")
    if step.output:
        print(compact_output(step.output, limit=output_limit))
