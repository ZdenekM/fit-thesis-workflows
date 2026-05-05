"""Check syntax and basic hygiene for repository helper scripts."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from thesis_review_workflow.cases import repo_root


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
