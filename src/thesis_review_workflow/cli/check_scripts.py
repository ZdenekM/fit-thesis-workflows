"""Check syntax and basic hygiene for repository helper scripts."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from thesis_review_workflow.cases import repo_root

WINDOWS_RULE_SNIPPETS = (
    "Windows is a supported operator platform",
    "Do not introduce WSL-only assumptions",
    "Python/Pants/PEX command surface",
    "native `.cmd`/`.ps1` launchers",
    "Windows-aware",
    "Treat `scripts/<tool>` references",
    "logical workflow tool names",
    "platform-native packaging entrypoint",
)

WINDOWS_CONTRACT_FILES = {
    Path("scripts/package-workflow-tools.cmd"): (
        "thesis_review_workflow.cli.package_workflow_tools",
        "WORKFLOW_TOOLS_PYTHON",
        "py -3.12",
        "python",
    ),
    Path("scripts/package-workflow-tools.ps1"): (
        "thesis_review_workflow.cli.package_workflow_tools",
        "WORKFLOW_TOOLS_PYTHON",
        "Get-Command",
    ),
    Path("src/thesis_review_workflow/cli/package_workflow_tools.py"): (
        "CMD_LAUNCHER",
        "PS_LAUNCHER",
        "The extensionless launchers are POSIX-only",
    ),
    Path("src/thesis_review_workflow/commands.py"): (
        "canonical_command_text",
        "dist\\\\workflow-tools\\\\bin",
    ),
    Path("src/thesis_review_workflow/cli/init_review_manifest.py"): (
        "Store logical workflow commands",
        "canonical_command_text",
    ),
    Path("README.md"): (
        "Na Windows nespouštějte ani neklikejte bezpříponové",
        "dist\\workflow-tools\\bin\\init-review-manifest.cmd",
        ".\\dist\\workflow-tools\\bin\\init-review-manifest.ps1",
    ),
    Path("docs/workflow-command-surface.md"): (
        "do not run or click extensionless `scripts/<tool>` files",
        "stores helper check",
    ),
    Path("docs/agent-scheduling.md"): (
        "Command routing: `scripts/<tool>` examples in this document",
        "do not run or click extensionless `scripts/<tool>` files",
    ),
    Path("docs/historical-opponent-calibration.md"): (
        "Command routing: `scripts/<tool>` examples in this document",
        "do not run or click extensionless `scripts/<tool>` files",
    ),
    Path(".codex/hooks/session_start_context.py"): (
        "logical workflow command check-supervisor-ready",
        "packaged .cmd/.ps1 launcher",
    ),
}

SKILL_COMMAND_ROUTING_SNIPPETS = (
    "Command routing: treat `scripts/<tool>` examples below as logical workflow",
    "not run or click extensionless `scripts/<tool>` files",
)


def script_files(root: Path) -> list[Path]:
    scripts_dir = root / "scripts"
    if not scripts_dir.is_dir():
        return []
    return sorted(path for path in scripts_dir.iterdir() if path.is_file())


def first_line(path: Path) -> str:
    with path.open("rb") as handle:
        return handle.readline().decode("utf-8", errors="replace").strip()


def check_python_syntax(path: Path, errors: list[str]) -> None:
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        errors.append(f"{path}: Python syntax check failed: {exc}")


def check_bash_syntax(path: Path, bash: str, errors: list[str]) -> None:
    completed = subprocess.run(
        [bash, "-n", str(path)],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        errors.append(f"{path}: Bash syntax check failed: {detail}")


def check_newlines(path: Path, errors: list[str]) -> None:
    try:
        content = path.read_bytes()
    except OSError as exc:
        errors.append(f"{path}: could not read script: {exc}")
        return
    if b"\r\n" in content:
        errors.append(f"{path}: CRLF newlines are not allowed in repository scripts")


def check_executable(path: Path, errors: list[str]) -> None:
    if os.name == "nt":
        return
    if not os.access(path, os.X_OK):
        errors.append(f"{path}: script is not executable")


def check_required_snippets(path: Path, snippets: tuple[str, ...], errors: list[str]) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"{path}: could not read required Windows compatibility contract file: {exc}")
        return
    except UnicodeDecodeError as exc:
        errors.append(f"{path}: required Windows compatibility contract file is not UTF-8: {exc}")
        return

    missing = [snippet for snippet in snippets if snippet not in content]
    if missing:
        formatted = ", ".join(repr(snippet) for snippet in missing)
        errors.append(f"{path}: missing Windows compatibility contract marker(s): {formatted}")


def check_windows_operator_contract(root: Path, errors: list[str]) -> None:
    check_required_snippets(root / "AGENTS.md", WINDOWS_RULE_SNIPPETS, errors)
    for rel_path, snippets in WINDOWS_CONTRACT_FILES.items():
        check_required_snippets(root / rel_path, snippets, errors)
    skills_dir = root / ".agents" / "skills"
    if skills_dir.is_dir():
        for skill_path in sorted(skills_dir.glob("*/SKILL.md")):
            check_required_snippets(skill_path, SKILL_COMMAND_ROUTING_SNIPPETS, errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts/check-scripts",
        description="Check syntax and basic hygiene for repository helper scripts.",
    )
    parser.parse_args(sys.argv[1:] if argv is None else argv[1:])

    root = repo_root()
    bash = shutil.which("bash")
    errors: list[str] = []
    skipped_bash: list[Path] = []

    check_windows_operator_contract(root, errors)

    for path in script_files(root):
        check_newlines(path, errors)
        shebang = first_line(path)
        if shebang.startswith("#!"):
            check_executable(path, errors)
        if "python" in shebang:
            check_python_syntax(path, errors)
        elif "bash" in shebang:
            if bash is not None:
                check_bash_syntax(path, bash, errors)
            else:
                skipped_bash.append(path)

    if errors:
        print("Script syntax check failed", file=sys.stderr)
        print("\n".join(errors), file=sys.stderr)
        return 1
    if skipped_bash:
        print(
            f"Script syntax check passed; skipped {len(skipped_bash)} POSIX shell syntax checks "
            "because bash is not available.",
            file=sys.stderr,
        )
    else:
        print("Script syntax check passed")
    return 0


def console_main() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    console_main()
