import hashlib
import json
from pathlib import Path

from thesis_review_workflow.cli import import_theses_report as cli

SYNTHETIC_REPORT = """
Porovnávaný dokument
Synthetic thesis
Podobnost 5 %
vyhodnoceno: 12. 5. 2026 12:07

Zdrojové dokumenty, ve kterych byla nalezena podobnost
1.
Zaverecna prace
Prior synthetic version
https://theses.example.invalid/id/previous
Změněno 1. 1. 2025, 9 000 slov
Podobnost 4 %

Vyznačení podobností ve zkoumanem dokumentu
1
"""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_round(root: Path, *, current_round: bool = True) -> Path:
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    for subdir in ("notes", "inputs", "extracted", "work", "outputs"):
        (round_dir / subdir).mkdir(parents=True, exist_ok=True)
    if current_round:
        (root / "cases" / "case-a" / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    return round_dir


def source_pdf(tmp_path: Path, name: str = "theses-Šuľa.pdf") -> Path:
    source = tmp_path / "Stažené" / name
    source.parent.mkdir(parents=True)
    source.write_bytes(b"%PDF-1.4 synthetic theses report\n")
    return source


def install_import_fakes(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(cli, "repo_root_core", lambda: root)
    monkeypatch.setattr(cli, "git_ignored", lambda root_arg, rel: rel.startswith("cases/"))
    monkeypatch.setattr(cli, "report_page_count", lambda report_pdf: (1, []))
    monkeypatch.setattr(cli, "utc_now", lambda: "2026-05-12T00:00:00Z")

    def fake_extract(report_pdf: Path, output_txt: Path) -> None:
        output_txt.write_text(SYNTHETIC_REPORT, encoding="utf-8")

    monkeypatch.setattr(cli, "extract_report_text", fake_extract)


def test_import_report_writes_private_targets_and_intake(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    report = source_pdf(tmp_path)
    install_import_fakes(monkeypatch, root)

    result = cli.main(["scripts/import-theses-report", "case-a", str(report)])

    assert result == 0
    assert "Intake written" in capsys.readouterr().out
    copied_pdf = round_dir / "inputs/theses_similarity/report.pdf"
    extracted_text = round_dir / "extracted/theses_similarity/report.txt"
    intake_path = round_dir / "work/theses_similarity/intake.json"
    assert copied_pdf.read_bytes() == report.read_bytes()
    assert extracted_text.read_text(encoding="utf-8") == SYNTHETIC_REPORT

    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    assert intake["schema_version"] == "theses-similarity-intake-v1"
    assert intake["case_id"] == "case-a"
    assert intake["round_id"] == "round-a"
    assert intake["current_submission_link"] == "unverified"
    assert intake["report_pdf"] == {
        "path": "inputs/theses_similarity/report.pdf",
        "sha256": sha256_file(copied_pdf),
        "page_count": 1,
    }
    assert intake["extracted_text"]["sha256"] == sha256_file(extracted_text)
    assert intake["source_documents"][0]["rank"] == 1
    assert intake["matched_passages"][0]["passage_id"] == "passage-1"
    assert "theses-Šuľa" not in json.dumps(intake, ensure_ascii=False)


def test_import_report_accepts_explicit_round_and_submission_link_status(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root, current_round=False)
    report = source_pdf(tmp_path)
    install_import_fakes(monkeypatch, root)

    result = cli.main(
        [
            "scripts/import-theses-report",
            "--current-submission-link",
            "matched",
            "case-a",
            "round-a",
            str(report),
        ]
    )

    assert result == 0
    intake = json.loads((round_dir / "work/theses_similarity/intake.json").read_text(encoding="utf-8"))
    assert intake["current_submission_link"] == "matched"


def test_import_report_rejects_case_insensitive_existing_target(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    (round_dir / "inputs/theses_similarity").mkdir(parents=True)
    (round_dir / "inputs/theses_similarity/Report.PDF").write_bytes(b"already here")
    report = source_pdf(tmp_path)
    install_import_fakes(monkeypatch, root)

    result = cli.main(["scripts/import-theses-report", "case-a", str(report)])

    assert result == 1
    assert "case-insensitive target collision" in capsys.readouterr().err
    assert not (round_dir / "work/theses_similarity/intake.json").exists()


def test_import_report_rejects_case_insensitive_parent_collision(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    (round_dir / "inputs/Theses_Similarity").mkdir(parents=True)
    report = source_pdf(tmp_path)
    install_import_fakes(monkeypatch, root)

    result = cli.main(["scripts/import-theses-report", "case-a", str(report)])

    assert result == 1
    assert "case-insensitive target collision" in capsys.readouterr().err
    assert not (round_dir / "work/theses_similarity/intake.json").exists()


def test_import_report_refuses_non_ignored_target(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    make_round(root)
    report = source_pdf(tmp_path)
    install_import_fakes(monkeypatch, root)
    monkeypatch.setattr(cli, "git_ignored", lambda root_arg, rel: False)

    result = cli.main(["scripts/import-theses-report", "case-a", str(report)])

    assert result == 1
    assert "non-ignored path" in capsys.readouterr().err


def test_import_report_refuses_symlinked_private_target_parent(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (round_dir / "inputs/theses_similarity").symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError):
        return
    report = source_pdf(tmp_path)
    install_import_fakes(monkeypatch, root)

    result = cli.main(["scripts/import-theses-report", "case-a", str(report)])

    assert result == 1
    assert "symlinked path" in capsys.readouterr().err
    assert not (outside / "report.pdf").exists()


def test_report_page_count_does_not_record_raw_pdfinfo_paths(tmp_path: Path, monkeypatch) -> None:
    report = source_pdf(tmp_path)
    monkeypatch.setattr(cli.shutil, "which", lambda command: "/usr/bin/pdfinfo")
    monkeypatch.setattr(
        cli,
        "run_text",
        lambda args: (_ for _ in ()).throw(RuntimeError(f"Syntax Error: {report}: invalid PDF")),
    )

    page_count, limitations = cli.report_page_count(report)

    assert page_count is None
    assert limitations == ["pdfinfo failed; report page count was not recorded."]
    assert str(report) not in limitations[0]


def test_import_report_cleans_temporary_files_on_extraction_failure(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    report = source_pdf(tmp_path)
    install_import_fakes(monkeypatch, root)

    def failing_extract(report_pdf: Path, output_txt: Path) -> None:
        raise RuntimeError("synthetic extraction failure")

    monkeypatch.setattr(cli, "extract_report_text", failing_extract)

    result = cli.main(["scripts/import-theses-report", "case-a", str(report)])

    assert result == 1
    assert not (round_dir / "inputs/theses_similarity/report.pdf").exists()
    assert not (round_dir / "extracted/theses_similarity/report.txt").exists()
    assert not (round_dir / "work/theses_similarity/intake.json").exists()
    assert list((round_dir / "inputs/theses_similarity").glob(".*.tmp-*")) == []


def test_import_report_cleans_final_files_on_commit_failure(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    report = source_pdf(tmp_path)
    install_import_fakes(monkeypatch, root)
    real_replace = cli.os.replace
    calls = 0

    def flaky_replace(source: Path, target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic commit failure")
        real_replace(source, target)

    monkeypatch.setattr(cli.os, "replace", flaky_replace)

    result = cli.main(["scripts/import-theses-report", "case-a", str(report)])

    assert result == 1
    assert not (round_dir / "inputs/theses_similarity/report.pdf").exists()
    assert not (round_dir / "extracted/theses_similarity/report.txt").exists()
    assert not (round_dir / "work/theses_similarity/intake.json").exists()
    assert list((round_dir / "inputs/theses_similarity").glob(".*.tmp-*")) == []
    assert list((round_dir / "extracted/theses_similarity").glob(".*.tmp-*")) == []
    assert list((round_dir / "work/theses_similarity").glob(".*.tmp-*")) == []
