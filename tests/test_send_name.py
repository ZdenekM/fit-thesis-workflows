from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from thesis_review_workflow import send_name

DAY = datetime.date(2026, 10, 13)


def test_name_is_dated_ascii_and_ordered() -> None:
    name = send_name.send_pdf_name(
        day=DAY, who=send_name.surname("Jan Karel Novák"), scope="BP", kind="feedback", language="cs"
    )

    assert name == "2026-10-13_Novak_BP_zpetna-vazba.pdf"


@pytest.mark.parametrize(
    ("kind", "language", "label"),
    [("feedback", "en", "feedback"), ("brief", "cs", "podklad-k-tematu"), ("brief", "en", "topic-brief")],
)
def test_name_uses_the_kind_label_of_the_language(kind: str, language: str, label: str) -> None:
    assert send_name.send_pdf_name(day=DAY, who="Novák", scope="dp", kind=kind, language=language) == (
        f"2026-10-13_Novak_DP_{label}.pdf"
    )


def test_name_leaves_out_empty_parts() -> None:
    assert send_name.send_pdf_name(day=DAY, who="", scope="", kind="feedback", language="cs") == (
        "2026-10-13_zpetna-vazba.pdf"
    )


def test_slug_flattens_spaces_and_punctuation() -> None:
    assert send_name.ascii_slug("  Ďurďa / O'Brien ") == "Durda-O-Brien"
    assert send_name.surname("") == ""


def test_copy_match_is_scoped_by_kind_and_scope() -> None:
    assert send_name.is_send_copy("2026-10-13_Novak_BP_zpetna-vazba.pdf", kind="feedback")
    assert send_name.is_send_copy("2026-10-13_Novak_zpetna-vazba.pdf", kind="feedback")
    assert send_name.is_send_copy("2026-10-13_feedback.pdf", kind="feedback")
    assert not send_name.is_send_copy("2026-10-13_Novak_BP_zpetna-vazba.pdf", kind="brief")
    assert not send_name.is_send_copy("feedback_student.pdf", kind="feedback")
    assert send_name.is_send_copy("2026-10-13_x_BP_podklad-k-tematu.pdf", kind="brief", scope="BP")
    assert not send_name.is_send_copy("2026-10-13_x_DP_podklad-k-tematu.pdf", kind="brief", scope="BP")
    assert not send_name.is_send_copy("2026-10-13_x_BP_topic-brief.pdf", kind="brief", scope="xp")


def test_copy_match_rejects_names_the_generator_cannot_produce() -> None:
    assert not send_name.is_send_copy("2026-10-13_Novak_BP_archived_feedback.pdf", kind="feedback")
    assert not send_name.is_send_copy("2026-02-30_Novak_BP_feedback.pdf", kind="feedback")
    assert not send_name.is_send_copy("2026-10-13_Novak_XP_feedback.pdf", kind="feedback")


def test_work_type_part_keeps_only_bp_or_dp() -> None:
    assert send_name.work_type_part(" dp ") == "DP"
    for work_type in ("unknown", "BP / DP / unknown", "xx", ""):
        assert send_name.work_type_part(work_type) == ""


def test_slug_transliterates_letters_without_a_decomposition() -> None:
    assert send_name.ascii_slug("Đặng Łukasik Øster Strauß") == "Dang-Lukasik-Oster-Strauss"


def test_install_copies_the_pdf_under_the_name(tmp_path: Path) -> None:
    pdf = tmp_path / "feedback_student.pdf"
    pdf.write_bytes(b"%PDF new\n")

    target = send_name.install_send_copy(pdf, "2026-10-13_Novak_BP_zpetna-vazba.pdf")

    assert target == tmp_path / "2026-10-13_Novak_BP_zpetna-vazba.pdf"
    assert target.read_bytes() == b"%PDF new\n"


def test_removal_names_each_copy_and_keeps_unrelated_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    older = tmp_path / "2026-10-01_Novak_BP_zpetna-vazba.pdf"
    older.write_bytes(b"%PDF old\n")
    unrelated = [
        tmp_path / "2026-10-01_notes.pdf",
        tmp_path / "feedback_student.pdf",
        tmp_path / "2026-10-01_x_BP_topic-brief.pdf",
    ]
    for path in unrelated:
        path.write_bytes(b"%PDF\n")

    assert send_name.remove_send_copies(tmp_path, kind="feedback")

    assert not older.exists()
    assert all(path.exists() for path in unrelated)
    assert older.name in capsys.readouterr().out


def test_removal_reports_a_copy_it_cannot_remove(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "2026-10-01_feedback.pdf").write_bytes(b"%PDF old\n")

    def locked(self: Path, missing_ok: bool = False) -> None:
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "unlink", locked)

    assert not send_name.remove_send_copies(tmp_path, kind="feedback")
