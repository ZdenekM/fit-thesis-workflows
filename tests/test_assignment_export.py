"""Contract tests for the FIT IS assignment export checker.

Synthetic `pdftotext -layout` text only, built to the geometry FIT IS prints:
labels at column 0, list markers indented past them, continuation lines hanging
under the item's text, a form feed after every page. Real exports are private
case data and stay out of tracked tests.
"""

from pathlib import Path

import pytest
from thesis_review_workflow.assignment_draft import RENDERINGS
from thesis_review_workflow.assignment_export import check_export, page_count
from thesis_review_workflow.cli import check_assignment_export

REPO_ROOT = Path(__file__).resolve().parents[1]

POINTS = """   1. Prozkoumejte existující přístupy k řešení ukázkového problému a shrňte jejich
      vlastnosti.
   2. Navrhněte vlastní řešení.
   3. Vytvořte krátké video představující vaši práci."""

LITERATURE = """    • NOVÁK, Jan. Ukázková kniha. Brno: Nakladatel, 2020. ISBN 978-0-00-000000-0.
    • DOE, Jane et al. An Example Paper. In: Proceedings of an Example Conference. ACM, 2025,
      s. 1-10. DOI: 10.0000/example."""

SEMESTRAL = "    • Body 1 a 2."


def export(
    *,
    rendering: str = "cs",
    variant: str = "bp",
    title: str = "Ukázkové téma",
    points: str | None = POINTS,
    literature: str | None = LITERATURE,
    semestral: str | None = SEMESTRAL,
    pages: int = 1,
) -> str:
    """One synthetic export; a None field is left out, as FIT IS leaves out an empty one."""

    form = RENDERINGS[rendering]
    lines = [f"                             {form.titles[variant]}", "                                   123456"]
    for label in form.metadata:
        value = title if label == form.title_label else "x"
        lines.append(f"{label:<16}{value}")
    lines.append("")
    for label, body in ((form.points_label, points), (form.literature_label, literature)):
        if body is not None:
            lines += [label, body, ""]
    if semestral is not None:
        lines += [form.semestral_label, semestral, ""]
    lines.append(f"{form.guidelines} https://www.fit.vut.cz/study/theses/")
    lines += [f"{label:<22}" for label in form.footer]
    page = "\n".join(lines) + "\n\n\nFakulta informačních technologií\n\f"
    return page + "Pokračování\n\f" * (pages - 1)


def findings(text: str, **kwargs: object) -> tuple[str, ...]:
    return check_export(text, **kwargs).findings  # type: ignore[arg-type]


def test_a_well_formed_czech_export_passes() -> None:
    check = check_export(export(), language="cs")
    assert check.findings == ()
    assert (check.rendering, check.variant, check.pages) == (RENDERINGS["cs"], "bp", 1)


def test_a_well_formed_english_export_passes_and_the_language_is_checked() -> None:
    text = export(rendering="en", variant="dp")
    assert findings(text, language="en") == ()
    assert any("`en` rendering, not `cs`" in finding for finding in findings(text, language="cs"))


def test_a_second_page_fails() -> None:
    assert page_count(export(pages=2)) == 2
    assert any("2 pages" in finding for finding in findings(export(pages=2)))


def test_an_unrecognised_header_stops_the_check() -> None:
    check = check_export(export().replace("Zadání bakalářské práce", "Posudek"))
    assert check.rendering is None
    assert len(check.findings) == 1 and "not a FIT IS assignment header" in check.findings[0]


def test_no_text_at_all_is_reported() -> None:
    assert "no text could be extracted" in findings("\f")[0]


def test_an_empty_title_fails() -> None:
    assert findings(export(title="")) == ("`Název:` is missing or empty",)


def test_points_typed_as_text_at_the_margin_fail() -> None:
    """The returned assignment: numbers pasted as text, wrapped lines back at the margin."""

    typed = (
        "1. Prozkoumejte existující přístupy k řešení ukázkového problému a shrňte\n"
        "jejich vlastnosti.\n"
        "2. Navrhněte vlastní řešení."
    )
    result = findings(export(points=typed))
    assert any("point 1, 2 starts at the label column" in finding for finding in result)
    assert any("lines after point 1 that do not hang under its text, first: `jejich" in finding for finding in result)


def test_a_number_alone_on_its_line_fails() -> None:
    """What a list imported from another editor prints: the number, then the text a line lower."""

    imported = "   1.\n        Prozkoumejte přístupy.\n        Shrňte je.\n   2.\n        Navrhněte řešení."
    result = findings(export(points=imported))
    assert result == ("`Zadání:` point 1, 2 has its marker on a line of its own and the text below it",)


def test_numbering_must_run_from_one_without_gaps() -> None:
    gap = "   1. Prozkoumejte přístupy.\n   3. Navrhněte řešení."
    assert findings(export(points=gap)) == ("`Zadání:` points are numbered 1, 3, not consecutively from 1",)


def test_a_wrapped_line_that_starts_with_a_number_stays_a_continuation() -> None:
    wrapped = "   1. Implementujte podporu protokolu ve verzi\n      2. generace a ověřte ji.\n   2. Vytvořte video."
    assert findings(export(points=wrapped)) == ()


def test_a_continuation_one_column_off_still_hangs() -> None:
    """`pdftotext` rounds positions to columns, so text at one x can extract a column apart."""

    for column in (5, 7):
        wrapped = " " * column + "ukázkového problému."
        rounded = f"   1. Prozkoumejte přístupy k řešení\n{wrapped}\n   2. Navrhněte řešení."
        assert findings(export(points=rounded)) == ()
        numbered = " " * column + "2. generace."
        assert findings(export(points=f"   1. Podporujte protokol\n{numbered}\n   2. Vytvořte video.")) == ()
        entry = " " * column + "Brno: Nakladatel, 2020."
        assert findings(export(literature=f"    • NOVÁK, Jan. Ukázková kniha.\n{entry}")) == ()


def test_a_sub_list_is_read_by_its_columns_only() -> None:
    """Not modelled: under the text it reads as part of the point, deeper as a line that does not hang."""

    under = "   1. Hlavní úkol.\n      • Dílčí úkol.\n   2. Další úkol."
    assert findings(export(points=under)) == ()
    deeper = "   1. Hlavní úkol.\n         • Dílčí úkol.\n   2. Další úkol."
    assert findings(export(points=deeper)) == (
        "`Zadání:` has lines after point 1 that do not hang under its text, first: `• Dílčí úkol.`",
    )


def test_right_aligned_two_digit_numbers_are_one_list() -> None:
    points = "\n".join(f"   {n:>2}. Bod číslo {n}." for n in range(1, 11))
    assert findings(export(points=points)) == ()


def test_a_marker_typed_into_the_item_text_fails() -> None:
    """Pasting `1. text` and then applying the list button prints the number twice."""

    doubled = "   1. 1. Prozkoumejte přístupy.\n   2. 2. Navrhněte řešení."
    assert findings(export(points=doubled)) == (
        "`Zadání:` point 1, 2 carries a typed marker of its own inside the list item; paste the text without it",
    )
    bulleted = "    • - NOVÁK, Jan. Ukázková kniha. Brno: Nakladatel, 2020."
    assert findings(export(literature=bulleted)) == (
        "`Literatura:` entry 1 carries a typed marker of its own inside the list item; paste the text without it",
    )


def test_text_on_the_label_line_is_reported_alone() -> None:
    result = findings(export().replace("Zadání:\n   1. Prozkoumejte", "Zadání:   1. Prozkoumejte"))
    assert len(result) == 1
    assert result[0].startswith("`Zadání:` has text on the label's own line, outside the list: `1. Prozkoumejte")


def test_missing_points_fail() -> None:
    assert "`Zadání:` is missing or empty" in findings(export(points=None))


def test_literature_outside_a_bullet_list_fails() -> None:
    assert findings(export(literature="TBD")) == ("`Literatura:` is not a bullet list; its first line is `TBD`",)


def test_a_literature_continuation_at_the_margin_fails() -> None:
    broken = "    • DOE, Jane. An Example Paper. In: Proceedings of an Example\nConference. ACM, 2025."
    assert findings(export(literature=broken)) == (
        "`Literatura:` has lines after entry 1 that do not hang under its text, first: `Conference. ACM, 2025.`",
    )


def test_missing_literature_fails() -> None:
    assert "`Literatura:` is missing or empty" in findings(export(literature=None))


def test_the_semestral_field_is_required_unless_explicitly_allowed() -> None:
    text = export(semestral=None)
    assert any("is missing or empty" in finding and "--allow-empty-semestral" in finding for finding in findings(text))
    allowed = check_export(text, allow_empty_semestral=True)
    assert allowed.findings == ()
    assert len(allowed.notes) == 1
    assert allowed.notes[0].endswith("is empty, accepted under `--allow-empty-semestral`")


def test_a_semestral_label_with_nothing_under_it_is_empty() -> None:
    assert any("is missing or empty" in finding for finding in findings(export(semestral="")))


def test_a_semestral_bullet_with_no_text_is_empty() -> None:
    assert any("is missing or empty" in finding for finding in findings(export(semestral="    •")))
    assert findings(export(semestral="1.")) == ()


def test_a_semestral_field_written_as_plain_text_is_filled() -> None:
    """The field carries no list rule; older exports print it as plain text at the margin."""

    assert findings(export(rendering="en", semestral="Points 1 and 2.")) == ()


def test_only_a_later_label_ends_a_field() -> None:
    """Plain text that happens to start like an earlier label stays inside the field."""

    assert findings(export(rendering="en", semestral="Literature: survey of points 1 and 2.")) == ()


def test_the_header_may_carry_the_assignment_number_and_wider_spacing() -> None:
    text = export().replace("Zadání bakalářské práce", "Zadání  bakalářské  práce          123456", 1)
    assert check_export(text).variant == "bp"
    english = export(rendering="en").replace("Bachelor's", "Bachelor\u2019s", 1)
    assert check_export(english).rendering == RENDERINGS["en"]


def test_windows_line_endings_read_the_same() -> None:
    assert findings(export().replace("\n", "\r\n"), language="cs") == ()


def test_the_template_carries_every_label_the_export_check_reads() -> None:
    """Template, draft checker and export checker read one set of labels."""

    template = (REPO_ROOT / "templates" / "assignment-formal.md").read_text(encoding="utf-8")
    for form in RENDERINGS.values():
        block = template.split(form.heading, 1)[1].split("\n## ", 1)[0]
        assert form.guidelines in block


def test_the_command_reports_every_file_and_fails_when_one_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    texts = {"good.pdf": export(), "bad.pdf": export(literature="TBD")}
    for name in texts:
        (tmp_path / name).write_bytes(b"%PDF-1.4\n")
    monkeypatch.setenv("THESIS_REVIEW_CALLER_CWD", str(tmp_path))
    monkeypatch.setattr(check_assignment_export.shutil, "which", lambda _: "pdftotext")
    monkeypatch.setattr(check_assignment_export, "layout_text", lambda _, pdf: texts[pdf.name])

    assert check_assignment_export.main(["good.pdf"]) == 0
    assert check_assignment_export.main(["good.pdf", "bad.pdf", "missing.pdf"]) == 1
    output = capsys.readouterr().out
    assert "ERROR: bad.pdf: `Literatura:` is not a bullet list" in output
    assert "ERROR: missing.pdf: no such file" in output
    assert "failed for 2 of 3 file(s)" in output
    assert "`Zobrazit studentům`" in output
    assert "Rendering not compared with the thesis language" in output
