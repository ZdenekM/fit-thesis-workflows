import io
import tarfile
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
