"""Package workflow PEX tools and generate platform launchers."""

from __future__ import annotations

import argparse
import json
import shutil
import stat
import subprocess
import sys
import textwrap
from pathlib import Path, PurePosixPath
from typing import Any

from thesis_review_workflow.cases import repo_root

POSIX_LAUNCHER = r"""
#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/../../.." && pwd -P)"
export THESIS_REVIEW_CALLER_CWD="${THESIS_REVIEW_CALLER_CWD:-$PWD}"
export PYTHONPATH=
export PEX_ROOT="${PEX_ROOT:-$repo_root/.pants.d/pex_root}"
python_bin="${WORKFLOW_TOOLS_PYTHON:-}"
if [[ -z "$python_bin" ]]; then
  if command -v python3.12 >/dev/null 2>&1; then
    python_bin="python3.12"
  else
    python_bin="python3"
  fi
fi
if ! "$python_bin" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)'; then
  echo "Workflow tool launchers require Python 3.12. Set WORKFLOW_TOOLS_PYTHON=/path/to/python3.12 if needed." >&2
  exit 1
fi
cd "$repo_root"
exec "$python_bin" "$script_dir/../pex/{tool_name}" "$@"
"""

CMD_LAUNCHER = r"""
@echo off
setlocal
set "script_dir=%~dp0"
for %%I in ("%script_dir%..\..\..") do set "repo_root=%%~fI"
if not defined THESIS_REVIEW_CALLER_CWD set "THESIS_REVIEW_CALLER_CWD=%CD%"
set "PYTHONPATH="
if not defined PEX_ROOT set "PEX_ROOT=%repo_root%\.pants.d\pex_root"
set "pex_path=%script_dir%..\pex\{tool_name}"
if defined WORKFLOW_TOOLS_PYTHON goto use_env_python
py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
if not errorlevel 1 goto use_py_launcher
python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
if not errorlevel 1 goto use_python_launcher
goto python_error

:use_env_python
"%WORKFLOW_TOOLS_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
if errorlevel 1 goto python_error
cd /d "%repo_root%" || exit /b 1
"%WORKFLOW_TOOLS_PYTHON%" "%pex_path%" %*
exit /b %ERRORLEVEL%

:use_py_launcher
cd /d "%repo_root%" || exit /b 1
py -3.12 "%pex_path%" %*
exit /b %ERRORLEVEL%

:use_python_launcher
cd /d "%repo_root%" || exit /b 1
python "%pex_path%" %*
exit /b %ERRORLEVEL%

:python_error
echo Workflow tool launchers require Python 3.12. Set WORKFLOW_TOOLS_PYTHON=C:\Path\To\python.exe if needed. 1>&2
exit /b 1
"""

PS_LAUNCHER = r"""
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..")).Path
if (-not $env:THESIS_REVIEW_CALLER_CWD) {
    $env:THESIS_REVIEW_CALLER_CWD = (Get-Location).Path
}
$env:PYTHONPATH = ""
if (-not $env:PEX_ROOT) {
    $env:PEX_ROOT = Join-Path $repoRoot ".pants.d\pex_root"
}
$pexPath = Join-Path $scriptDir "..\pex\{tool_name}"
$candidates = @()
if ($env:WORKFLOW_TOOLS_PYTHON) {
    $candidates += ,@($env:WORKFLOW_TOOLS_PYTHON)
} else {
    $candidates += ,@("py", "-3.12")
    $candidates += ,@("python")
}
$pythonExe = $null
$pythonArgs = @()
foreach ($candidate in $candidates) {
    $exe = $candidate[0]
    $baseArgs = @($candidate | Select-Object -Skip 1)
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
        continue
    }
    & $exe @baseArgs -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" *> $null
    if ($LASTEXITCODE -eq 0) {
        $pythonExe = $exe
        $pythonArgs = $baseArgs
        break
    }
}
if (-not $pythonExe) {
    Write-Error ("Workflow tool launchers require Python 3.12. " +
        "Set WORKFLOW_TOOLS_PYTHON=C:\Path\To\python.exe if needed.")
    exit 1
}
Set-Location $repoRoot
& $pythonExe @pythonArgs $pexPath @args
exit $LASTEXITCODE
"""


def render(template: str, tool_name: str) -> str:
    return textwrap.dedent(template).lstrip("\n").replace("{tool_name}", tool_name)


def run_text(args: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(detail or f"{' '.join(args)} failed")
    return completed.stdout


def workflow_tool_names_from_peek_payload(payload: str) -> list[str]:
    targets: Any = json.loads(payload)
    tools: list[str] = []
    seen: set[str] = set()
    for target in targets:
        if not isinstance(target, dict) or target.get("target_type") != "pex_binary":
            continue
        address = target.get("address")
        output_path = target.get("output_path")
        if not isinstance(output_path, str):
            raise RuntimeError(f"workflow-tool target {address} has no output_path")
        path = PurePosixPath(output_path)
        if str(path.parent) != "workflow-tools/pex":
            raise RuntimeError(
                f"workflow-tool target {address} must output under workflow-tools/pex/, got {output_path}"
            )
        if path.name in seen:
            raise RuntimeError(f"Duplicate workflow-tool output path for {path.name}")
        seen.add(path.name)
        tools.append(path.name)
    if not tools:
        raise RuntimeError("No workflow-tool pex_binary targets found.")
    return sorted(tools)


def workflow_tool_names(root: Path) -> list[str]:
    payload = run_text(["pants", "--tag=workflow-tool", "peek", "::"], cwd=root)
    return workflow_tool_names_from_peek_payload(payload)


def write_launchers(root: Path, tool_name: str) -> None:
    bin_dir = root / "dist" / "workflow-tools" / "bin"
    posix = bin_dir / tool_name
    cmd = bin_dir / f"{tool_name}.cmd"
    ps = bin_dir / f"{tool_name}.ps1"
    posix.write_text(render(POSIX_LAUNCHER, tool_name), encoding="utf-8")
    posix.chmod(posix.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    cmd.write_text(render(CMD_LAUNCHER, tool_name), encoding="utf-8")
    ps.write_text(render(PS_LAUNCHER, tool_name), encoding="utf-8")


def package(root: Path) -> list[str]:
    expected_tools = workflow_tool_names(root)
    print("Packaging workflow tools into dist/workflow-tools/bin/")
    shutil.rmtree(root / "dist" / "workflow-tools", ignore_errors=True)
    completed = subprocess.run(["pants", "--tag=workflow-tool", "package", "::"], cwd=root, check=False)
    if completed.returncode != 0:
        raise RuntimeError("pants workflow-tool package failed")
    bin_dir = root / "dist" / "workflow-tools" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    expected = set(expected_tools)
    for tool_name in expected_tools:
        pex_dir = root / "dist" / "workflow-tools" / "pex" / tool_name
        if not pex_dir.is_dir():
            raise RuntimeError(f"Missing packed PEX directory: dist/workflow-tools/pex/{tool_name}")
        write_launchers(root, tool_name)

    pex_root = root / "dist" / "workflow-tools" / "pex"
    for pex_dir in pex_root.iterdir() if pex_root.is_dir() else []:
        if pex_dir.is_dir() and pex_dir.name not in expected:
            raise RuntimeError(f"Unexpected packed PEX directory: dist/workflow-tools/pex/{pex_dir.name}")
    return expected_tools


def launcher_listing_lines(tools: list[str]) -> list[str]:
    lines = ["Packaged tools:"]
    for tool_name in sorted(tools):
        lines.append(f"- POSIX launcher: dist/workflow-tools/bin/{tool_name}")
        lines.append(f"  Windows cmd: dist\\workflow-tools\\bin\\{tool_name}.cmd")
        lines.append(f"  PowerShell: .\\dist\\workflow-tools\\bin\\{tool_name}.ps1")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts/package-workflow-tools",
        description="Package workflow PEX tools and generate POSIX, cmd, and PowerShell launchers.",
    )
    parser.parse_args(sys.argv[1:] if argv is None else argv[1:])
    root = repo_root()
    try:
        tools = package(root)
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print()
    for line in launcher_listing_lines(tools):
        print(line)
    print("PEX_ROOT defaults to .pants.d/pex_root in the repository unless already set.")
    print("The extensionless launchers are POSIX-only; Windows users should run the .cmd or .ps1 launchers.")
    return 0


def console_main() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    console_main()
