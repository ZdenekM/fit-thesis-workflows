from pathlib import Path

from thesis_review_workflow.cli.check_scripts import check_review_instruction_ownership, check_windows_operator_contract


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
            "The extensionless launchers are POSIX-only",
        ),
    )
    write_contract_file(
        tmp_path / "src/thesis_review_workflow/commands.py",
        (
            "canonical_command_text",
            "dist\\\\workflow-tools\\\\bin",
        ),
    )
    write_contract_file(
        tmp_path / "src/thesis_review_workflow/cli/init_review_manifest.py",
        (
            "Store logical workflow commands",
            "canonical_command_text",
        ),
    )
    write_contract_file(
        tmp_path / "README.md",
        (
            "Na Windows nespouštějte ani neklikejte bezpříponové",
            "dist\\workflow-tools\\bin\\init-review-manifest.cmd",
            ".\\dist\\workflow-tools\\bin\\init-review-manifest.ps1",
        ),
    )
    write_contract_file(
        tmp_path / "docs/workflow-command-surface.md",
        (
            "do not run or click extensionless `scripts/<tool>` files",
            "stores helper check",
        ),
    )
    write_contract_file(
        tmp_path / "docs/agent-scheduling.md",
        (
            "Command routing: `scripts/<tool>` examples in this document",
            "do not run or click extensionless `scripts/<tool>` files",
        ),
    )
    write_contract_file(
        tmp_path / "docs/historical-opponent-calibration.md",
        (
            "Command routing: `scripts/<tool>` examples in this document",
            "do not run or click extensionless `scripts/<tool>` files",
        ),
    )
    write_contract_file(
        tmp_path / ".codex/hooks/session_start_context.py",
        (
            "logical workflow command check-supervisor-ready",
            "packaged .cmd/.ps1 launcher",
        ),
    )
    write_contract_file(
        tmp_path / ".agents/skills/example/SKILL.md",
        (
            "Command routing: treat `scripts/<tool>` examples below as logical workflow",
            "not run or click extensionless `scripts/<tool>` files",
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
            "Treat `scripts/<tool>` references",
            "logical workflow tool names",
            "platform-native packaging entrypoint",
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


def test_review_instruction_ownership_rejects_copied_owner_text(tmp_path: Path) -> None:
    snippets = (
        (
            "Return only:\n\n"
            "- files written or changed;\n"
            "- top 3-5 findings, verdicts, or risks;\n"
            "- commands/checks run;\n"
            "- explicit limitations;\n"
            "- whether expected output validation passed.\n",
            "copied default subagent handoff list",
        ),
        (
            "default to at most 2 concurrent spawned\n" "workflow agents, use 1 on memory-constrained machines\n",
            "copied scheduling default",
        ),
        (
            "Role states in `work/review_role_plan.json` decide whether\n" "a role needs fresh review\n",
            "copied role-state semantics",
        ),
        (
            "Workflow profiles, materiality profiles, wave workflows, Codex agent\n"
            "profiles, and reviewer preference profiles are separate concepts.\n",
            "copied profile terminology boundary",
        ),
    )

    for index, (snippet, label) in enumerate(snippets):
        root = create_contract_root(
            tmp_path / f"case-{index}",
            agents_snippets=(
                "Windows is a supported operator platform",
                "Do not introduce WSL-only assumptions",
                "Python/Pants/PEX command surface",
                "native `.cmd`/`.ps1` launchers",
                "Windows-aware",
                "Treat `scripts/<tool>` references",
                "logical workflow tool names",
                "platform-native packaging entrypoint",
            ),
        )
        skill_path = root / ".agents/skills/example/SKILL.md"
        skill_path.write_text(
            skill_path.read_text(encoding="utf-8") + "\n" + snippet,
            encoding="utf-8",
        )

        errors: list[str] = []
        check_review_instruction_ownership(root, errors)

        assert any(label in error for error in errors)
