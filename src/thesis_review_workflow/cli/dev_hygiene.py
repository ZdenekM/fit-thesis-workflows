"""Developer-only hygiene command wrappers for Pants targets."""

from __future__ import annotations

import os
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


def omen_binary(root: Path) -> str | None:
    configured = os.environ.get("OMEN_BIN")
    if configured:
        return configured
    on_path = shutil.which("omen")
    if on_path:
        return on_path
    for relative in (
        Path(".pants.d/dev-tools/omen/bin/omen"),
        Path(".pants.d/dev-tools/omen/bin/omen.exe"),
    ):
        candidate = root / relative
        if candidate.is_file():
            return str(candidate)
    return None


def omen_commands(root: Path) -> list[list[str]]:
    binary = omen_binary(root)
    if binary is None:
        raise SystemExit(
            "omen not found. Install it on PATH, set OMEN_BIN, or install it into "
            ".pants.d/dev-tools/omen/bin/omen. This target is dev-only and is not "
            "part of the thesis case pipeline."
        )
    base = [binary, "-c", "omen.toml", "-p", ".", "-f", "text"]
    return [base + [subcommand] for subcommand in ("score", "hotspot", "deadcode")]


def main(argv: list[str]) -> int:
    root = repo_root()
    if len(argv) != 2 or argv[1] not in {"jscpd", "omen"}:
        print("Usage: dev-hygiene {jscpd|omen}", file=sys.stderr)
        return 2
    if argv[1] == "jscpd":
        return run(jscpd_command(), cwd=root)
    for command in omen_commands(root):
        code = run(command, cwd=root)
        if code != 0:
            return code
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
