"""Command execution and preflight step helpers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


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


def resolve_repo_command(root: Path, args: list[str]) -> list[str]:
    executable = root / args[0]
    if executable.exists():
        return [str(executable), *args[1:]]
    return args


def run_step(root: Path, label: str, args: list[str], *, required: bool = True) -> Step:
    completed = subprocess.run(
        resolve_repo_command(root, args),
        cwd=root,
        text=True,
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
