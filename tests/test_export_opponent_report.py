from pathlib import Path

from thesis_review_workflow.cli import export_opponent_report as exporter


def calibrated_canonical_report() -> str:
    return """<!-- source_trace_path: work/opponent_report_trace.json -->
<!-- source_trace_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -->
<!-- source_materials_path: outputs/oponent_podklady_revidovane.md -->
<!-- source_materials_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb -->
# Návrh oponentského posudku

Datum přípravy draftu: 2026-05-18T00:00:00Z
Stav: připraveno pro nezávislou kontrolu oponentem.

## IS formulář (výběry a body)

Náročnost zadání: obtížnější zadání
Rozsah splnění požadavků zadání: zadání splněno s drobnými výhradami
Rozsah technické zprávy: je v obvyklém rozmezí
Prezentační úroveň technické zprávy: 80 bodů
Formální úprava technické zprávy: 80 bodů
Práce s literaturou: 80 bodů
Realizační výstup: 80 bodů

## 1. Náročnost zadání

Stav: tato věta je obsah posudku a export ji musí zachovat.

## 2. Rozsah splnění požadavků zadání

Text.

## 3. Rozsah technické zprávy

Text.

## 4. Prezentační úroveň technické zprávy

Text.

## 5. Formální úprava technické zprávy

Text.

## 6. Práce s literaturou

Text.

## 7. Realizační výstup

Text.

## 8. Využitelnost výsledku

Text.

## 9. Celkové hodnocení

Text.

## 10. Otázky k obhajobě

- Jak lze výsledek zopakovat?

## 11. Body a známka

Body: 80
Známka: B

## Komentář pro studenta (neveřejná část)

Děkuji za zpracovanou práci. Silnou stránkou je funkční prototyp a přiměřené pokrytí zadání.
K obhajobě doporučuji připravit konkrétní metodiku testování, stručnou ukázku výsledků
a jasné oddělení vlastního přínosu od použitých knihoven.

## 12. Před odevzdáním

- Zkontrolovat, že slovní hodnocení odpovídá bodům a známce.
"""


def make_round(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.joinpath("work").mkdir(parents=True)
    round_dir.joinpath("outputs").mkdir()
    (root / "cases" / "case-a" / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (root / "cases" / "case-a" / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    (round_dir / "work" / "oponent_posudek_draft.md").write_text(
        calibrated_canonical_report(),
        encoding="utf-8",
    )
    return root, round_dir


def test_clean_export_text_strips_metadata_intro_status_and_private_checklist() -> None:
    exported = exporter.clean_export_text(calibrated_canonical_report())

    assert "source_trace_path" not in exported
    assert "source_materials_sha256" not in exported
    assert "Datum přípravy draftu:" not in exported
    assert "Stav: připraveno" not in exported
    assert "## 12. Před odevzdáním" not in exported
    assert "Zkontrolovat, že slovní hodnocení" not in exported
    assert "## IS formulář (výběry a body)" in exported
    assert "## Komentář pro studenta (neveřejná část)" in exported
    assert "Stav: tato věta je obsah posudku" in exported


def test_main_exports_clean_proposal_and_runs_canonical_and_clean_checks(tmp_path: Path, monkeypatch) -> None:
    root, round_dir = make_round(tmp_path)
    commands: list[list[str]] = []

    monkeypatch.setattr(exporter, "repo_root", lambda: root)
    monkeypatch.setattr(exporter, "run_required", lambda root_arg, command: commands.append(command))

    result = exporter.main(["export-opponent-report", "case-a", "round-a"])

    assert result == 0
    output = round_dir / "outputs" / "oponent_posudek_navrh.md"
    assert output.is_file()
    assert "source_trace_path" not in output.read_text(encoding="utf-8")
    assert commands == [
        [
            "scripts/check-opponent-report",
            "--mode",
            "canonical",
            "--path",
            "work/oponent_posudek_draft.md",
            "case-a",
            "round-a",
        ],
        [
            "scripts/check-opponent-report",
            "--mode",
            "canonical",
            "--path",
            "work/oponent_posudek_draft.md",
            "case-a",
            "round-a",
        ],
        [
            "scripts/check-opponent-report",
            "--mode",
            "clean",
            "--path",
            "outputs/.oponent_posudek_navrh.md.tmp",
            "case-a",
            "round-a",
        ],
        [
            "scripts/check-opponent-report",
            "--mode",
            "clean",
            "--path",
            "outputs/oponent_posudek_navrh.md",
            "case-a",
            "round-a",
        ],
    ]


def test_main_refuses_to_overwrite_changed_clean_proposal_without_force(tmp_path: Path, monkeypatch) -> None:
    root, round_dir = make_round(tmp_path)
    output = round_dir / "outputs" / "oponent_posudek_navrh.md"
    output.write_text("# Human edit\n", encoding="utf-8")

    monkeypatch.setattr(exporter, "repo_root", lambda: root)
    monkeypatch.setattr(exporter, "run_required", lambda _root, _command: None)

    result = exporter.main(["export-opponent-report", "case-a", "round-a"])

    assert result == 1
    assert output.read_text(encoding="utf-8") == "# Human edit\n"


def test_main_overwrites_changed_clean_proposal_with_force(tmp_path: Path, monkeypatch) -> None:
    root, round_dir = make_round(tmp_path)
    output = round_dir / "outputs" / "oponent_posudek_navrh.md"
    output.write_text("# Human edit\n", encoding="utf-8")

    monkeypatch.setattr(exporter, "repo_root", lambda: root)
    monkeypatch.setattr(exporter, "run_required", lambda _root, _command: None)

    result = exporter.main(["export-opponent-report", "--force", "case-a", "round-a"])

    assert result == 0
    assert output.read_text(encoding="utf-8") != "# Human edit\n"


def test_main_rejects_unsafe_round_relative_paths(tmp_path: Path, monkeypatch) -> None:
    root, _round_dir = make_round(tmp_path)
    monkeypatch.setattr(exporter, "repo_root", lambda: root)

    result = exporter.main(["export-opponent-report", "--source", "../draft.md", "case-a", "round-a"])

    assert result == 2


def test_main_rejects_alternate_output_without_explicit_dev_flag(tmp_path: Path, monkeypatch) -> None:
    root, _round_dir = make_round(tmp_path)
    monkeypatch.setattr(exporter, "repo_root", lambda: root)

    result = exporter.main(["export-opponent-report", "--output", "outputs/other.md", "case-a", "round-a"])

    assert result == 2


def test_main_preserves_existing_output_when_clean_temp_validation_fails(tmp_path: Path, monkeypatch) -> None:
    root, round_dir = make_round(tmp_path)
    output = round_dir / "outputs" / "oponent_posudek_navrh.md"
    output.write_text("# Existing reviewed candidate\n", encoding="utf-8")

    def fail_clean_temp(_root: Path, command: list[str]) -> None:
        if command[1:5] == ["--mode", "clean", "--path", "outputs/.oponent_posudek_navrh.md.tmp"]:
            raise SystemExit("clean temp validation failed")

    monkeypatch.setattr(exporter, "repo_root", lambda: root)
    monkeypatch.setattr(exporter, "run_required", fail_clean_temp)

    try:
        exporter.main(["export-opponent-report", "--force", "case-a", "round-a"])
    except SystemExit as exc:
        assert str(exc) == "clean temp validation failed"
    else:
        raise AssertionError("expected clean temp validation failure")

    assert output.read_text(encoding="utf-8") == "# Existing reviewed candidate\n"
    assert not (round_dir / "outputs" / ".oponent_posudek_navrh.md.tmp").exists()
