"""Phase-aware shape contract for student-facing supervisor feedback.

Neither `check_feedback_language` nor `check_feedback_output` had pytest coverage before
this file; only the two smoke scripts exercised them, and both exercise the late shape with
no declared phase. The early-shape tests below cover both checkers, because the first
attempt at this slice made the language check accept a shape the output check rejected.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from thesis_review_workflow.cli import check_feedback_language, check_feedback_output

LATE_CS = check_feedback_language.CS_REQUIRED_HEADINGS
EARLY_CS = check_feedback_language.CS_EARLY_REQUIRED_HEADINGS
LATE_EN = check_feedback_language.EN_REQUIRED_HEADINGS
EARLY_EN = check_feedback_language.EN_EARLY_REQUIRED_HEADINGS


def make_case(tmp_path: Path, *, language: str, headings: list[str], review_phase: str | None) -> Path:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "outputs").mkdir(parents=True)
    (round_dir / "work").mkdir()
    (round_dir.parents[1] / "case.md").write_text(
        f"Work type: BP\nStudent feedback language: {language}\n", encoding="utf-8"
    )
    (round_dir.parents[1] / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    body = "\n".join(f"{heading}\n\nObsah.\n" for heading in headings)
    (round_dir / "outputs" / "feedback_student.md").write_text(body, encoding="utf-8")
    if review_phase is not None:
        (round_dir / "work" / "review_run_trace.json").write_text(
            json.dumps({"review_phase": review_phase}), encoding="utf-8"
        )
    return root


def run(root: Path, monkeypatch) -> int:
    monkeypatch.setattr(check_feedback_language, "repo_root", lambda: root)
    return check_feedback_language.main(["scripts/check-feedback-language", "case-a", "round-a"])


def test_the_early_set_is_a_strict_subset_of_the_late_set() -> None:
    """A late-shape artifact must always satisfy the early requirement too."""
    assert set(EARLY_CS) < set(LATE_CS)
    assert set(EARLY_EN) < set(LATE_EN)


def test_early_shape_passes_when_the_phase_is_declared(monkeypatch, tmp_path: Path) -> None:
    root = make_case(tmp_path, language="cs", headings=EARLY_CS, review_phase="early")

    assert run(root, monkeypatch) == 0


def test_early_shape_fails_without_a_declared_phase(monkeypatch, tmp_path: Path, capsys) -> None:
    """The shape follows the declaration, so an undeclared round still owes the late shape."""
    root = make_case(tmp_path, language="cs", headings=EARLY_CS, review_phase=None)

    result = run(root, monkeypatch)

    assert result == 1
    assert "Missing Czech headings with diacritics" in capsys.readouterr().err


def test_early_shape_fails_when_an_early_heading_is_missing(monkeypatch, tmp_path: Path) -> None:
    root = make_case(tmp_path, language="cs", headings=EARLY_CS[:-1], review_phase="early")

    assert run(root, monkeypatch) == 1


def test_late_shape_still_passes_in_every_phase(monkeypatch, tmp_path: Path) -> None:
    for index, phase in enumerate((None, "early", "non_final", "final")):
        root = make_case(tmp_path / str(index), language="cs", headings=LATE_CS, review_phase=phase)
        assert run(root, monkeypatch) == 0, f"late shape must pass with phase {phase}"


def test_english_early_shape_follows_the_same_rule(monkeypatch, tmp_path: Path) -> None:
    root = make_case(tmp_path, language="en", headings=EARLY_EN, review_phase="early")

    assert run(root, monkeypatch) == 0


def test_diacritics_rule_still_bites_in_the_early_phase(monkeypatch, tmp_path: Path, capsys) -> None:
    ascii_headings = [
        "# Zpetna vazba k aktualni verzi prace",
        "## Kratke celkove shrnuti",
        "## Rozsah kontroly",
        "## Odhad faze prace a doporucene zamereni",
        "## Nejvyssi priority pro aktualni iteraci",
        "## Doporuceny plan dalsich uprav",
    ]
    root = make_case(tmp_path, language="cs", headings=ascii_headings, review_phase="early")

    result = run(root, monkeypatch)

    assert result == 1
    assert "Found ASCII-only Czech headings" in capsys.readouterr().err


def test_english_headings_are_still_rejected_in_czech_early_feedback(monkeypatch, tmp_path: Path, capsys) -> None:
    root = make_case(tmp_path, language="cs", headings=[*EARLY_CS, *EARLY_EN], review_phase="early")

    result = run(root, monkeypatch)

    assert result == 1
    assert "Found English headings in Czech feedback" in capsys.readouterr().err


EARLY_BODY_CS = """# Zpětná vazba k aktuální verzi práce

Datum kontroly: 2026-09-07

## Krátké celkové shrnutí

Kostra práce stojí a repozitář se rozjel; teď je nejdůležitější dotáhnout strukturu kapitol.

## Rozsah kontroly

Prošel jsem osnovu textu a stav repozitáře. Typografii, literaturu a obrázky jsem v této fázi
odložil, takže jejich stav zatím není ověřen a chybí i běh kódu; omezení uvádím záměrně.

## Odhad fáze práce a doporučené zaměření

Práce je v rané fázi, takže se soustředíme na směr a strukturu, ne na formu.

## Nejvyšší priority pro aktuální iteraci

| Priorita | Oblast | Proč teď | Co udělat | Kde se to projevuje |
|---|---|---|---|---|
| P0 | Struktura | Ovlivní další kapitoly | Rozepsat osnovu kapitol 3 a 4 | Osnova, kapitoly 3-4 |
| P1 | Repozitář | Bez běhu nelze nic ověřit | Doplnit README se spuštěním | Repozitář, README.md |

## Doporučený plán dalších úprav

Do příští konzultace dotáhnout osnovu a README; pak se pustíme do návrhové kapitoly.
"""


def write_output_case(tmp_path: Path, *, body: str, review_phase: str | None) -> Path:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "outputs").mkdir(parents=True)
    (round_dir / "work").mkdir()
    (round_dir / "notes").mkdir()
    (round_dir.parents[1] / "case.md").write_text("Work type: BP\nStudent feedback language: cs\n", encoding="utf-8")
    (round_dir.parents[1] / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    (round_dir / "outputs" / "feedback_student.md").write_text(body, encoding="utf-8")
    if review_phase is not None:
        (round_dir / "work" / "review_run_trace.json").write_text(
            json.dumps({"review_phase": review_phase}), encoding="utf-8"
        )
    return root


def run_output(root: Path, monkeypatch) -> int:
    """Run the output checker with its two subprocess gates stubbed.

    `check-supervisor-ready` needs deadline configuration and `check-feedback-language` is
    covered directly above; these tests are about the shape rules in this checker.
    """
    monkeypatch.setattr(check_feedback_output, "repo_root", lambda: root)
    monkeypatch.setattr(check_feedback_output, "run_supervisor_ready", lambda *args, **kwargs: None)
    monkeypatch.setattr(check_feedback_output, "run_language_check", lambda *args, **kwargs: None)
    return check_feedback_output.main(["scripts/check-feedback-output", "case-a", "round-a"])


def test_output_check_accepts_the_early_shape_when_the_phase_is_declared(monkeypatch, tmp_path: Path) -> None:
    """The gate that Slice 4's first attempt failed: the early shape omits the checklist."""
    root = write_output_case(tmp_path, body=EARLY_BODY_CS, review_phase="early")

    assert run_output(root, monkeypatch) == 0


def test_output_check_rejects_the_early_shape_without_a_declared_phase(monkeypatch, tmp_path: Path, capsys) -> None:
    root = write_output_case(tmp_path, body=EARLY_BODY_CS, review_phase=None)

    result = run_output(root, monkeypatch)

    assert result == 1
    assert "checklist" in capsys.readouterr().err.lower()


def test_output_check_rejects_the_early_shape_when_a_later_phase_is_declared(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    """Guards against an inverted phase selector, which a subset alone cannot catch."""
    root = write_output_case(tmp_path, body=EARLY_BODY_CS, review_phase="final")

    result = run_output(root, monkeypatch)

    assert result == 1
    assert "checklist" in capsys.readouterr().err.lower()


def test_language_check_rejects_the_early_shape_when_a_later_phase_is_declared(monkeypatch, tmp_path: Path) -> None:
    for phase in ("non_final", "final"):
        root = make_case(tmp_path / phase, language="cs", headings=EARLY_CS, review_phase=phase)
        assert run(root, monkeypatch) == 1, f"early shape must not satisfy phase {phase}"


def body_with_priority_rows(rows: list[str]) -> str:
    """The early body with its priority table replaced by `rows`."""
    marker = "|---|---|---|---|---|\n"
    head, _, tail = EARLY_BODY_CS.partition(marker)
    rest = tail.partition("\n## Doporučený plán")[2]
    return head + marker + "\n".join(rows) + "\n\n## Doporučený plán" + rest


def priority_row(label: str, index: int) -> str:
    return (
        f"| {label} | Oblast {index} | Ovlivní další postup práce "
        f"| Konkrétní akce číslo {index} k dotažení | Kapitola {index}, str. {index}0 |"
    )


def test_early_phase_caps_the_priority_list(monkeypatch, tmp_path: Path, capsys) -> None:
    body = body_with_priority_rows([priority_row("P1", index) for index in range(1, 7)])
    root = write_output_case(tmp_path, body=body, review_phase="early")

    result = run_output(root, monkeypatch)

    assert result == 1
    assert "too many priority rows for the early phase" in capsys.readouterr().err


def test_early_phase_caps_the_p0_count(monkeypatch, tmp_path: Path, capsys) -> None:
    body = body_with_priority_rows([priority_row("P0", index) for index in range(1, 4)])
    root = write_output_case(tmp_path, body=body, review_phase="early")

    result = run_output(root, monkeypatch)

    assert result == 1
    assert "too many P0 rows for the early phase" in capsys.readouterr().err


def test_a_late_phase_round_keeps_the_wider_priority_allowance(monkeypatch, tmp_path: Path) -> None:
    """The early cap must not leak into a late round, which allows up to eight rows."""
    body = body_with_priority_rows([priority_row("P1", index) for index in range(1, 7)])
    body = body + (
        "\n## Checklist pro aktuální fázi\n\n"
        "- Dotáhnout osnovu kapitol tři a čtyři na odstavce.\n"
        "- Doplnit README s postupem spuštění a závislostmi.\n"
        "- Popsat v textu, co přesně demonstrátor ověřuje.\n"
    )
    root = write_output_case(tmp_path, body=body, review_phase="final")

    assert run_output(root, monkeypatch) == 0


def test_required_headings_rejects_an_unsupported_language() -> None:
    with pytest.raises(ValueError):
        check_feedback_language.required_headings("de", "early")
