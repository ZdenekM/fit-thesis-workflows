$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
if (-not $env:THESIS_REVIEW_CALLER_CWD) {
    $env:THESIS_REVIEW_CALLER_CWD = (Get-Location).Path
}
$env:PYTHONPATH = Join-Path $repoRoot "src"
Set-Location $repoRoot
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
    Write-Error ("Workflow tool packaging requires Python 3.12. " +
        "Set WORKFLOW_TOOLS_PYTHON=C:\Path\To\python.exe if needed.")
    exit 1
}
& $pythonExe @pythonArgs -m thesis_review_workflow.cli.package_workflow_tools @args
exit $LASTEXITCODE
