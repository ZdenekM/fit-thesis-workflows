from pathlib import Path

from thesis_review_workflow.cli.check_scripts import check_windows_operator_contract


def write_contract_file(path: Path, snippets: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(snippets) + "\n", encoding="utf-8")


def create_contract_root(tmp_path: Path, *, agents_snippets: tuple[str, ...]) -> Path:
    write_contract_file(tmp_path / "AGENTS.md", agents_snippets)
    write_contract_file(
        tmp_path / "scripts/package-workflow-tools.cmd",
        (
            "thesis_review_workflow.cli.package_workflow_tools",
            "WORKFLOW_TOOLS_PYTHON",
            "py -3.12",
            "python",
        ),
    )
    write_contract_file(
        tmp_path / "scripts/package-workflow-tools.ps1",
        (
            "thesis_review_workflow.cli.package_workflow_tools",
            "WORKFLOW_TOOLS_PYTHON",
            "Get-Command",
        ),
    )
    write_contract_file(
        tmp_path / "src/thesis_review_workflow/cli/package_workflow_tools.py",
        (
            "CMD_LAUNCHER",
            "PS_LAUNCHER",
            "Windows launchers are generated as .cmd and .ps1",
        ),
    )
    return tmp_path


def test_windows_operator_contract_accepts_required_rule_and_launchers(tmp_path: Path) -> None:
    root = create_contract_root(
        tmp_path,
        agents_snippets=(
            "Windows is a supported operator platform",
            "Do not introduce WSL-only assumptions",
            "Python/Pants/PEX command surface",
            "native `.cmd`/`.ps1` launchers",
            "Windows-aware",
        ),
    )

    errors: list[str] = []
    check_windows_operator_contract(root, errors)

    assert errors == []


def test_windows_operator_contract_rejects_missing_active_rule(tmp_path: Path) -> None:
    root = create_contract_root(
        tmp_path,
        agents_snippets=(
            "Windows is a supported operator platform",
            "Python/Pants/PEX command surface",
            "native `.cmd`/`.ps1` launchers",
            "Windows-aware",
        ),
    )

    errors: list[str] = []
    check_windows_operator_contract(root, errors)

    assert any("Do not introduce WSL-only assumptions" in error for error in errors)
