"""Developer-only hygiene command wrappers for Pants targets."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

DEV_HYGIENE_PATHS = [".codex/hooks", "scripts", "src", "tests"]
DEV_HYGIENE_IGNORE_GLOBS = (
    "**/.git/**,**/.pants.d/**,**/.mypy_cache/**,**/__pycache__/**,"
    "**/.pytest_cache/**,**/.venv/**,**/venv/**,**/cases/**,**/dist/**,"
    "**/work/**,**/outputs/**,**/extracted/**"
)


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    return Path.cwd()


def run(command: list[str], *, cwd: Path) -> int:
    try:
        return subprocess.run(command, cwd=cwd, check=False).returncode
    except FileNotFoundError:
        print(f"{command[0]} not found", file=sys.stderr)
        return 127


def jscpd_command() -> list[str]:
    npx = shutil.which("npx")
    if npx is None:
        raise SystemExit("npx not found on PATH. Install Node.js to run jscpd.")
    return [
        npx,
        "--yes",
        "jscpd@4.0.9",
        "--min-lines",
        "20",
        "--min-tokens",
        "100",
        "--threshold",
        "5",
        "--reporters",
        "console",
        "--ignore",
        DEV_HYGIENE_IGNORE_GLOBS,
        *DEV_HYGIENE_PATHS,
    ]


def main(argv: list[str]) -> int:
    root = repo_root()
    if len(argv) != 2 or argv[1] != "jscpd":
        # Omen has its own validated runner: `pants run scripts:omen` (omen_quality.py).
        print("Usage: dev-hygiene jscpd", file=sys.stderr)
        return 2
    return run(jscpd_command(), cwd=root)


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
