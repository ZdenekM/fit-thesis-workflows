import zipfile
from pathlib import Path

from thesis_review_workflow import agent_coverage, code_workspace
from thesis_review_workflow.paths import is_safe_round_relative_path


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
