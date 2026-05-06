import ast
import io
import json
import tarfile
import zipfile
from collections.abc import Iterator
from pathlib import Path

from thesis_review_workflow import agent_coverage, code_workspace
from thesis_review_workflow.cli.package_workflow_tools import workflow_tool_names_from_peek_payload
from thesis_review_workflow.commands import WORKFLOW_COMMAND_MODULES
from thesis_review_workflow.paths import is_safe_round_relative_path

REPO_ROOT = Path(__file__).resolve().parents[1]


def build_tree(path: str) -> ast.Module:
    return ast.parse((REPO_ROOT / path).read_text(encoding="utf-8"))


def call_nodes(tree: ast.Module, name: str) -> Iterator[ast.Call]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name:
            yield node


def keyword_value(call: ast.Call, name: str) -> ast.expr:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    raise AssertionError(f"Missing {name} keyword")


def literal_keyword(call: ast.Call, name: str):
    return ast.literal_eval(keyword_value(call, name))


def assignment_literal(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"Missing {name} assignment")


def name_keyword(call: ast.Call, name: str) -> str:
    value = keyword_value(call, name)
    if not isinstance(value, ast.Name):
        raise AssertionError(f"{name} keyword should reference a name")
    return value.id


def scripts_shell_sources() -> set[str]:
    tree = build_tree("scripts/BUILD")
    [call] = list(call_nodes(tree, "shell_sources"))
    return set(literal_keyword(call, "sources"))


def workflow_pex_targets() -> dict[str, dict[str, str]]:
    tree = build_tree("scripts/BUILD")
    targets: dict[str, dict[str, str]] = {}
    for call in call_nodes(tree, "pex_binary"):
        tags = set(literal_keyword(call, "tags"))
        if "workflow-tool" not in tags:
            continue
        output_path = literal_keyword(call, "output_path")
        tool_name = Path(output_path).name
        targets[tool_name] = {
            "dependencies": name_keyword(call, "dependencies"),
            "entry_point": literal_keyword(call, "entry_point"),
            "output_path": output_path,
        }
    return targets


def cli_python_sources() -> dict[str, str]:
    tree = build_tree("src/thesis_review_workflow/cli/BUILD")
    return {
        literal_keyword(call, "name"): literal_keyword(call, "source") for call in call_nodes(tree, "python_source")
    }


def workflow_runtime_deps() -> set[str]:
    tree = build_tree("scripts/BUILD")
    return set(assignment_literal(tree, "WORKFLOW_CLI_RUNTIME_DEPS"))


def shell_loop_body(text: str, header: str) -> str:
    start = text.index(header)
    body_start = text.index("\n", start) + 1
    end = text.index("\ndone", body_start)
    return text[body_start:end]


def test_safe_relative_rejects_absolute_and_parent_paths() -> None:
    assert agent_coverage.is_safe_relative("outputs/oponent_podklady_revidovane.md")
    assert not agent_coverage.is_safe_relative("/tmp/oponent_podklady_revidovane.md")
    assert not agent_coverage.is_safe_relative("../outputs/oponent_podklady_revidovane.md")
    assert not agent_coverage.is_safe_relative("outputs\\oponent_podklady_revidovane.md")
    assert not agent_coverage.is_safe_relative("C:/Users/me/oponent_podklady_revidovane.md")
    assert not agent_coverage.is_safe_relative("//server/share/oponent_podklady_revidovane.md")
    assert not agent_coverage.is_safe_relative("outputs/./oponent_podklady_revidovane.md")


def test_shared_round_relative_path_validation_is_windows_aware() -> None:
    assert is_safe_round_relative_path("work/review_manifest.json")
    for value in [
        "",
        ".",
        "./work/review_manifest.json",
        "../work/review_manifest.json",
        "/tmp/review_manifest.json",
        "C:/Users/me/review_manifest.json",
        "C:relative/review_manifest.json",
        "//server/share/review_manifest.json",
        "work//review_manifest.json",
        "work\\review_manifest.json",
    ]:
        assert not is_safe_round_relative_path(value)


def test_archive_suffix_handles_compound_tar_suffixes() -> None:
    assert code_workspace.archive_suffix(Path("code.tar.gz")) == ".tar.gz"
    assert code_workspace.archive_suffix(Path("code.zip")) == ".zip"
    assert code_workspace.archive_suffix(Path("code.7z")) == ".7z"


def test_probe_archive_detects_python_project_zip(tmp_path: Path) -> None:
    archive = tmp_path / "submitted-code.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("project/pyproject.toml", "[project]\nname = 'demo'\n")
        handle.writestr("project/src/main.py", "print('demo')\n")

    probe = code_workspace.probe_archive(archive)

    assert probe.code_like
    assert probe.possible_code
    assert probe.entries_seen == 2


def test_extract_zip_reports_case_insensitive_path_collisions(tmp_path: Path) -> None:
    archive = tmp_path / "code.zip"
    target = tmp_path / "out"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("project/src/Foo.py", "print('upper')\n")
        handle.writestr("project/src/foo.py", "print('lower')\n")

    extracted, skipped = code_workspace.extract_zip(archive, target)

    assert extracted == 1
    assert (target / "project/src/Foo.py").is_file()
    assert not (target / "project/src/foo.py").exists()
    assert any("case-insensitive path collision with project/src/Foo.py" in item for item in skipped)


def test_extract_tar_reports_case_insensitive_path_collisions(tmp_path: Path) -> None:
    archive = tmp_path / "code.tar"
    target = tmp_path / "out"
    with tarfile.open(archive, "w") as handle:
        for name, text in [
            ("project/src/Foo.py", "print('upper')\n"),
            ("project/src/foo.py", "print('lower')\n"),
        ]:
            payload = text.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            handle.addfile(info, io.BytesIO(payload))

    extracted, skipped = code_workspace.extract_tar(archive, target)

    assert extracted == 1
    assert (target / "project/src/Foo.py").is_file()
    assert not (target / "project/src/foo.py").exists()
    assert any("case-insensitive path collision with project/src/Foo.py" in item for item in skipped)


def test_safe_copy_input_dir_reports_case_insensitive_path_collisions(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "out"
    source.mkdir()
    (source / "README.md").write_text("upper\n", encoding="utf-8")
    (source / "readme.md").write_text("lower\n", encoding="utf-8")
    if len(list(source.iterdir())) < 2:
        return

    copied, skipped = code_workspace.safe_copy_input_dir(source, target)

    assert copied == 1
    assert (target / "README.md").is_file()
    assert not (target / "readme.md").exists()
    assert any("case-insensitive path collision with README.md" in item for item in skipped)


def test_workspace_target_registry_reports_case_insensitive_collisions(tmp_path: Path) -> None:
    registry = code_workspace.CaseInsensitivePathRegistry(tmp_path)

    assert registry.register(tmp_path / "Code", label="inputs/Code.zip", kind="directory") is None
    collision = registry.register(tmp_path / "code", label="inputs/code.zip", kind="directory")

    assert collision is not None
    assert "case-insensitive path collision with Code" in collision


def test_workflow_tool_pex_targets_match_command_module_map() -> None:
    pex_targets = workflow_pex_targets()

    assert set(pex_targets) == set(WORKFLOW_COMMAND_MODULES)
    for tool_name, module in WORKFLOW_COMMAND_MODULES.items():
        target = pex_targets[tool_name]
        assert target["dependencies"] == "WORKFLOW_CLI_RUNTIME_DEPS"
        assert target["entry_point"] == f"{module}:console_main"
        assert target["output_path"] == f"workflow-tools/pex/{tool_name}"


def test_workflow_command_modules_have_sources_runtime_deps_and_wrappers() -> None:
    cli_sources = cli_python_sources()
    runtime_deps = workflow_runtime_deps()
    shell_sources = scripts_shell_sources()

    for tool_name, module in WORKFLOW_COMMAND_MODULES.items():
        module_name = module.rsplit(".", 1)[-1]
        assert cli_sources[module_name] == f"{module_name}.py"
        assert f"src/thesis_review_workflow/cli:{module_name}" in runtime_deps
        assert tool_name in shell_sources


def test_package_workflow_tools_is_bootstrap_not_packaged_workflow_tool() -> None:
    cli_sources = cli_python_sources()
    shell_sources = scripts_shell_sources()
    pex_targets = workflow_pex_targets()

    assert cli_sources["package_workflow_tools"] == "package_workflow_tools.py"
    assert "package-workflow-tools" in shell_sources
    assert "package-workflow-tools" not in WORKFLOW_COMMAND_MODULES
    assert "package-workflow-tools" not in pex_targets


def test_package_smoke_covers_generated_launchers_and_posix_runtime() -> None:
    smoke = (REPO_ROOT / "scripts/smoke-package-workflow-tools").read_text(encoding="utf-8")
    tool_loop = shell_loop_body(smoke, 'for tool_name in "${tool_names[@]}"; do')

    assert 'mapfile -t tool_names < <(find "$repo_root/dist/workflow-tools/pex"' in smoke
    assert 'launcher="$repo_root/dist/workflow-tools/bin/$tool_name"' in tool_loop
    assert 'cmd_launcher="$repo_root/dist/workflow-tools/bin/$tool_name.cmd"' in tool_loop
    assert 'ps_launcher="$repo_root/dist/workflow-tools/bin/$tool_name.ps1"' in tool_loop
    assert '[[ ! -x "$launcher" ]]' in tool_loop
    assert '[[ ! -f "$cmd_launcher" ]]' in tool_loop
    assert '[[ ! -f "$ps_launcher" ]]' in tool_loop
    assert 'grep -Fq "..\\\\pex\\\\$tool_name" "$cmd_launcher"' in tool_loop
    assert 'grep -Fq "..\\\\pex\\\\$tool_name" "$ps_launcher"' in tool_loop
    assert 'grep -Fq "Get-Command" "$ps_launcher"' in tool_loop
    assert '"$launcher" --help' in tool_loop
    assert "thesis_review_workflow.cli.package_workflow_tools" in smoke


def test_workflow_tool_peek_parser_enforces_packaging_output_contract() -> None:
    payload = json.dumps(
        [
            {
                "address": "scripts:case_doctor_tool",
                "target_type": "pex_binary",
                "output_path": "workflow-tools/pex/case-doctor",
            },
            {
                "address": "src/thesis_review_workflow:lib",
                "target_type": "python_sources",
            },
            {
                "address": "scripts:check_tooling_tool",
                "target_type": "pex_binary",
                "output_path": "workflow-tools/pex/check-tooling",
            },
        ]
    )

    assert workflow_tool_names_from_peek_payload(payload) == ["case-doctor", "check-tooling"]


def test_workflow_tool_peek_parser_rejects_invalid_packaging_output_contract() -> None:
    missing_output = json.dumps([{"address": "scripts:bad_tool", "target_type": "pex_binary"}])
    wrong_directory = json.dumps(
        [
            {
                "address": "scripts:bad_tool",
                "target_type": "pex_binary",
                "output_path": "wrong-dir/bad-tool",
            }
        ]
    )
    duplicate_output = json.dumps(
        [
            {
                "address": "scripts:a_tool",
                "target_type": "pex_binary",
                "output_path": "workflow-tools/pex/dup-tool",
            },
            {
                "address": "scripts:b_tool",
                "target_type": "pex_binary",
                "output_path": "workflow-tools/pex/dup-tool",
            },
        ]
    )

    for payload in (missing_output, wrong_directory, duplicate_output):
        try:
            workflow_tool_names_from_peek_payload(payload)
        except RuntimeError:
            continue
        raise AssertionError("invalid workflow-tool payload was accepted")
