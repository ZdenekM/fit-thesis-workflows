import hashlib
from pathlib import Path

from thesis_review_workflow.cli import check_opponent_report as checker
from thesis_review_workflow.cli.check_opponent_report import (
    DEFAULT_DRAFT,
    check_text,
    strip_metadata_comments,
    validate_calibration_metadata,
    validate_trace_metadata,
)
from thesis_review_workflow.cli.draft_opponent_report import build_report

IS_IDS = (
    "assignment_difficulty",
    "assignment_fulfillment",
    "technical_report_scope",
    "technical_report_presentation",
    "technical_report_formal_level",
    "literature_work",
    "implementation_output",
    "result_usability",
    "overall_assessment",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace_payload() -> dict[str, object]:
    return {
        "is_items": [
            {
                "item_id": item_id,
                "title": item_id,
                "formulation": f"Formulation for {item_id}.",
                "evidence_refs": ["outputs/oponent_podklady_revidovane.md"],
            }
            for item_id in IS_IDS
        ],
        "defense_questions": [
            {
                "question_id": "D1",
                "question": "Prepared defense question",
                "evidence_refs": ["outputs/oponent_podklady_revidovane.md"],
            }
        ],
        "pre_submission_checks": [
            {
                "check_id": "C1",
                "instruction": "Manual point and grade calibration.",
                "evidence_refs": ["outputs/oponent_podklady_revidovane.md"],
            }
        ],
        "uncertainty_items": [
            {
                "claim_id": "U1",
                "summary": "Runtime was not fully verified.",
                "handling_instruction": "Preserve cautious wording in the overall assessment.",
                "source_refs": ["outputs/oponent_podklady_revidovane.md"],
                "target_section_ids": ["overall_assessment"],
                "report_refs": ["work/oponent_posudek_draft.md"],
                "status": "carried_to_report",
            }
        ],
    }


def test_build_report_uses_structured_trace_without_fallback_prose() -> None:
    report = build_report(trace_payload(), trace_hash="a" * 64, materials_hash="b" * 64)

    assert "<!-- source_trace_path: work/opponent_report_trace.json -->" in report
    assert "<!-- source_trace_sha256: " + "a" * 64 + " -->" in report
    assert "## IS formulář (výběry a body)" in report
    assert "Náročnost zadání: k ručnímu výběru z nabídky IS" in report
    assert "Formulation for assignment_difficulty." in report
    assert "- Prepared defense question?" in report
    assert "- Manual point and grade calibration." in report
    assert "U1: Runtime was not fully verified.; stav: carried_to_report" in report
    assert "pokyn: Preserve cautious wording in the overall assessment." in report
    assert "Z dostupných revidovaných podkladů není pro tuto položku" not in report


def test_build_report_copies_report_calibration_metadata_comments() -> None:
    basis = {
        "applied_preferences": [
            {"preference_id": "opponent.assignment_difficulty.stack_not_enough", "status": "applied"}
        ],
        "expected_report_controls": {
            "overall_grade": "B",
            "overall_points_interval": [80, 84],
            "defense_question_count": {"min": 1, "max": 3},
        },
    }

    report = build_report(
        trace_payload(),
        trace_hash="a" * 64,
        materials_hash="b" * 64,
        report_calibration_basis=basis,
        report_calibration_basis_hash="c" * 64,
    )

    assert "<!-- source_report_calibration_basis_path: work/report_calibration_basis.json -->" in report
    assert "<!-- source_report_calibration_basis_sha256: " + "c" * 64 + " -->" in report
    assert (
        "<!-- source_report_calibration_preference_ids: opponent.assignment_difficulty.stack_not_enough -->" in report
    )
    stripped = strip_metadata_comments(report)
    assert "report_calibration_basis" not in stripped
    assert "source_report_calibration" not in stripped


def test_trace_metadata_validation_detects_stale_trace(tmp_path: Path) -> None:
    trace_path = tmp_path / "opponent_report_trace.json"
    trace_path.write_text('{"version": 1}\n', encoding="utf-8")
    text = (
        "<!-- source_trace_path: work/opponent_report_trace.json -->\n"
        f"<!-- source_trace_sha256: {sha256_file(trace_path)} -->\n"
    )
    errors: list[str] = []

    validate_trace_metadata(text, trace_path, DEFAULT_DRAFT.as_posix(), errors)
    assert errors == []

    trace_path.write_text('{"version": 2}\n', encoding="utf-8")
    validate_trace_metadata(text, trace_path, DEFAULT_DRAFT.as_posix(), errors)

    assert any("opponent report trace hash changed" in error for error in errors)


def test_trace_metadata_required_for_alternate_report_paths(tmp_path: Path) -> None:
    trace_path = tmp_path / "opponent_report_trace.json"
    trace_path.write_text('{"version": 1}\n', encoding="utf-8")
    errors: list[str] = []

    validate_trace_metadata("# Human draft\n", trace_path, "work/muj_posudek_draft.md", errors)

    assert "missing source trace path metadata comment" in errors
    assert "missing source trace sha256 metadata comment" in errors


def test_strip_metadata_comments_removes_trace_and_materials_paths() -> None:
    text = (
        "<!-- source_trace_path: work/opponent_report_trace.json -->\n"
        "<!-- source_trace_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -->\n"
        "<!-- source_materials_path: outputs/oponent_podklady_revidovane.md -->\n"
        "<!-- source_materials_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb -->\n"
        "<!-- source_report_calibration_basis_path: work/report_calibration_basis.json -->\n"
        "<!-- source_report_calibration_basis_sha256: cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc -->\n"
        "# Návrh oponentského posudku\n"
    )

    stripped = strip_metadata_comments(text)

    assert "work/" not in stripped
    assert "outputs/" not in stripped
    assert "report_calibration" not in stripped
    assert stripped.startswith("# Návrh")


def test_calibration_metadata_validation_requires_trace_bound_comments() -> None:
    text = (
        "<!-- source_report_calibration_basis_path: work/report_calibration_basis.json -->\n"
        "<!-- source_report_calibration_basis_sha256: " + "a" * 64 + " -->\n"
    )
    trace: dict[str, object] = {
        "report_calibration_basis_path": "work/report_calibration_basis.json",
        "report_calibration_basis_sha256": "a" * 64,
    }
    errors: list[str] = []

    validate_calibration_metadata(text, trace, errors)

    assert errors == []

    validate_calibration_metadata(text.replace("a" * 64, "b" * 64), trace, errors)
    assert any("report calibration basis hash changed" in error for error in errors)


def calibrated_report_text() -> str:
    return """# Návrh oponentského posudku

## IS formulář (výběry a body)

Náročnost zadání: obtížnější zadání
Rozsah splnění požadavků zadání: zadání splněno s drobnými výhradami
Rozsah technické zprávy: přesahuje obvyklé rozmezí
Prezentační úroveň technické zprávy: 72 bodů
Formální úprava technické zprávy: 75 bodů
Práce s literaturou: 75 bodů
Realizační výstup: 85 bodů

## 1. Náročnost zadání

Text.

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

1. Otázka?

## 11. Body a známka

Bodové hodnocení: 75 bodů

Navržená známka: C

## Komentář pro studenta (neveřejná část)

Děkuji za práci na prototypu a za dotažení hlavní implementace.
K obhajobě si připravte stručné vysvětlení testování, limitů a dalšího možného vývoje.

## 12. Před odevzdáním

Text.
"""


def clean_report_text() -> str:
    return calibrated_report_text().split("## 12. Před odevzdáním", 1)[0].rstrip() + "\n"


def test_check_text_accepts_structured_is_form_fields() -> None:
    errors: list[str] = []

    check_text(calibrated_report_text(), calibrated_report_text(), errors)

    assert errors == []


def test_check_text_clean_mode_accepts_is_entry_proposal_without_private_checklist() -> None:
    text = clean_report_text()
    errors: list[str] = []

    check_text(text, text, errors, mode="clean")

    assert errors == []


def test_check_text_clean_mode_rejects_internal_metadata_and_private_checklist() -> None:
    text = (
        "<!-- source_trace_path: work/opponent_report_trace.json -->\n"
        "<!-- source_trace_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa -->\n"
        + calibrated_report_text()
    )
    errors: list[str] = []

    check_text(text, text, errors, mode="clean")

    assert "clean opponent report proposal must not contain source metadata comments" in errors
    assert "clean opponent report proposal must not contain private checklist heading: ## 12. Před odevzdáním" in errors


def test_check_text_clean_mode_rejects_hashes_and_workflow_mechanics() -> None:
    text = (
        clean_report_text()
        + "\n64d6f3b4c7e834e6ab6bcbd219222d9c84f05a9f568e8b965dd2209f73a4da8e\n"
        + "approval record for outputs/oponent_posudek_navrh.md\n"
    )
    errors: list[str] = []

    check_text(text, text, errors, mode="clean")

    assert any("oponent_posudek_navrh" in error for error in errors)
    assert any("0-9a-f" in error for error in errors)
    assert any("approval record" in error for error in errors)


def test_check_text_rejects_leaked_report_calibration_in_clean_report() -> None:
    text = clean_report_text() + "\nReport calibration basis: work/report_calibration_basis.json\n"
    errors: list[str] = []

    check_text(text, text, errors, mode="clean")

    assert any("report_calibration_basis" in error for error in errors)


def test_check_text_canonical_mode_requires_private_checklist() -> None:
    errors: list[str] = []

    check_text(clean_report_text(), clean_report_text(), errors)

    assert "missing required heading: ## 12. Před odevzdáním" in errors


def test_canonical_mode_requires_default_draft_when_clean_proposal_exists(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.joinpath("outputs").mkdir(parents=True)
    round_dir.joinpath("work").mkdir()
    (root / "cases" / "case-a" / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (root / "cases" / "case-a" / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    (round_dir / "outputs" / "oponent_podklady_revidovane.md").write_text("# Materials\n", encoding="utf-8")
    (round_dir / "outputs" / "oponent_posudek_navrh.md").write_text("# Clean\n", encoding="utf-8")
    (round_dir / "work" / "opponent_report_trace.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(checker, "repo_root", lambda: root)
    monkeypatch.setattr(checker, "run_round_ready", lambda root, case_id, round_id, errors: None)
    monkeypatch.setattr(checker, "run_opponent_materials_check", lambda root, case_id, round_id, errors: None)
    monkeypatch.setattr(checker, "validate_structured_evidence_artifact", lambda *args, **kwargs: [])

    result = checker.main(["check-opponent-report", "--mode", "canonical", "case-a", "round-a"])

    assert result == 1


def test_check_text_requires_valid_is_form_fields() -> None:
    text = calibrated_report_text().replace("obtížnější zadání", "hodně těžké zadání")
    text = text.replace("Realizační výstup: 85 bodů", "Realizační výstup: výborný")
    errors: list[str] = []

    check_text(text, text, errors)

    assert "invalid IS form selection for Náročnost zadání: hodně těžké zadání" in errors
    assert "invalid IS form point value for Realizační výstup: výborný" in errors


def test_check_text_allow_pending_still_rejects_invalid_concrete_calibration_values() -> None:
    text = calibrated_report_text().replace("Bodové hodnocení: 75 bodů", "Bodové hodnocení: 101 bodů")
    text = text.replace("Náročnost zadání: obtížnější zadání", "Náročnost zadání: hodně těžké zadání")
    text = text.replace("Realizační výstup: 85 bodů", "Realizační výstup: 105 bodů")
    errors: list[str] = []
    notes: list[str] = []

    check_text(
        text,
        text,
        errors,
        allow_draft_calibration_pending=True,
        draft_calibration_notes=notes,
    )

    assert "point value outside 0-100 range: 101" in errors
    assert "invalid IS form selection for Náročnost zadání: hodně těžké zadání" in errors
    assert "IS form point value outside 0-100 range for Realizační výstup: 105" in errors
    assert notes == []


def test_check_text_rejects_private_comment_placeholder() -> None:
    text = calibrated_report_text().replace(
        "Děkuji za práci na prototypu a za dotažení hlavní implementace.\n"
        "K obhajobě si připravte stručné vysvětlení testování, limitů a dalšího možného vývoje.",
        "Text.",
    )
    errors: list[str] = []

    check_text(text, text, errors)

    assert any("private student comment is too short" in error for error in errors)


def test_check_text_can_report_draft_calibration_pending_without_blocking_materials() -> None:
    text = calibrated_report_text()
    text = text.replace("Bodové hodnocení: 75 bodů", "Bodové hodnocení: k ručnímu výběru z nabídky IS")
    text = text.replace("Navržená známka: C", "Navržená známka: k ručnímu výběru z nabídky IS")
    text = text.replace("Realizační výstup: 85 bodů", "Realizační výstup: k ručnímu zadání bodů 0-100")
    errors: list[str] = []
    notes: list[str] = []

    check_text(
        text,
        text,
        errors,
        allow_draft_calibration_pending=True,
        draft_calibration_notes=notes,
    )

    assert errors == []
    assert any("concrete numeric point value" in note for note in notes)
    assert any("concrete proposed grade" in note for note in notes)
    assert any("invalid IS form point value for Realizační výstup" in note for note in notes)


def test_check_text_rejects_duplicate_is_form_fields() -> None:
    text = calibrated_report_text().replace(
        "Rozsah splnění požadavků zadání: zadání splněno s drobnými výhradami",
        "Rozsah splnění požadavků zadání: zadání splněno s drobnými výhradami\n"
        "Rozsah splnění požadavků zadání: zadání splněno",
    )
    errors: list[str] = []

    check_text(text, text, errors)

    assert "duplicate IS form field: Rozsah splnění požadavků zadání" in errors


def test_check_text_validates_expected_report_controls() -> None:
    expected_controls = {
        "is_select_values": {
            "Náročnost zadání": "obtížnější zadání",
            "Rozsah splnění požadavků zadání": "zadání splněno s drobnými výhradami",
        },
        "overall_grade": "C",
        "overall_points_interval": [70, 79],
        "defense_question_count": {"min": 1, "max": 2},
        "private_comment_required": True,
    }
    errors: list[str] = []

    check_text(calibrated_report_text(), calibrated_report_text(), errors, expected_report_controls=expected_controls)

    assert errors == []

    mismatched = calibrated_report_text().replace("Navržená známka: C", "Navržená známka: B")
    mismatched = mismatched.replace("Bodové hodnocení: 75 bodů", "Bodové hodnocení: 85 bodů")
    errors = []
    check_text(
        mismatched,
        mismatched,
        errors,
        expected_report_controls=expected_controls,
        expected_report_controls_source="work/report_calibration_basis.json sha256=" + "a" * 64,
    )

    assert any("overall grade does not match work/report_calibration_basis.json" in error for error in errors)
    assert any("overall points do not match work/report_calibration_basis.json" in error for error in errors)


def test_check_text_validates_only_canonical_grade_section_against_expected_controls() -> None:
    text = calibrated_report_text().replace("Navržená známka: C", "Navržená známka: D")
    text = text.replace(
        "## 1. Náročnost zadání\n\nText.", "## 1. Náročnost zadání\n\nZnámka: C v této větě není celkové hodnocení."
    )
    errors: list[str] = []

    check_text(
        text,
        text,
        errors,
        expected_report_controls={"overall_grade": "C"},
    )

    assert any("overall grade does not match report calibration basis: expected C, got D" in error for error in errors)
