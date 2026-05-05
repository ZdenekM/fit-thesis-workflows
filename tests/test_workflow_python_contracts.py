import zipfile
from pathlib import Path

import agent_coverage_lib
import thesis_code_workspace


def test_safe_relative_rejects_absolute_and_parent_paths() -> None:
    assert agent_coverage_lib.is_safe_relative("outputs/oponent_podklady_revidovane.md")
    assert not agent_coverage_lib.is_safe_relative("/tmp/oponent_podklady_revidovane.md")
    assert not agent_coverage_lib.is_safe_relative("../outputs/oponent_podklady_revidovane.md")
    assert not agent_coverage_lib.is_safe_relative("outputs\\oponent_podklady_revidovane.md")


def test_archive_suffix_handles_compound_tar_suffixes() -> None:
    assert thesis_code_workspace.archive_suffix(Path("code.tar.gz")) == ".tar.gz"
    assert thesis_code_workspace.archive_suffix(Path("code.zip")) == ".zip"
    assert thesis_code_workspace.archive_suffix(Path("code.7z")) == ".7z"


def test_probe_archive_detects_python_project_zip(tmp_path: Path) -> None:
    archive = tmp_path / "submitted-code.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("project/pyproject.toml", "[project]\nname = 'demo'\n")
        handle.writestr("project/src/main.py", "print('demo')\n")

    probe = thesis_code_workspace.probe_archive(archive)

    assert probe.code_like
    assert probe.possible_code
    assert probe.entries_seen == 2
