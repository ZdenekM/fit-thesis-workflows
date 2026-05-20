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
from thesis_review_workflow.cli.export_opponent_report import clean_export_text

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


def opponent_report_quality_controls(*, question_ids: tuple[str, ...] = ("D1",)) -> dict[str, object]:
    evidence_ref = "outputs/oponent_podklady_revidovane.md"
    claim_id = "claim-overall"
    optional_ref = {
        "summary": "Synthetic reviewed materials require compact cautious report wording.",
        "evidence_refs": [evidence_ref],
        "wording_mode": "manual_check",
        "materiality_reason": "The topic can affect an IS report section or defense question.",
        "limitations": ["Synthetic fixture only."],
    }
    return {
        "assignment_fulfillment_map": {
            "source_refs": [evidence_ref],
            "points": [
                {
                    "point_id": "assignment-point-1",
                    "summary": "Fixture assignment point is partially evidenced.",
                    "fulfillment_state": "partially_fulfilled",
                    "evidence_strength": "direct",
                    "evidence_refs": [evidence_ref],
                    "report_impact": "Mention as a calibrated limitation.",
                }
            ],
        },
        "rubric_alignment": [
            {
                "item_id": item_id,
                "criterion_scope": "Fixture checks the item independently.",
                "evidence_refs": [evidence_ref],
                "do_not_mix_with": ["overall_assessment"],
                "wording_tone": "Evidence-bound and compact.",
            }
            for item_id in IS_IDS
        ],
        "report_claim_ledger": [
            {
                "claim_id": claim_id,
                "target_item_id": "overall_assessment",
                "summary": "Overall public wording is evidence-bound.",
                "evidence_class": "reviewed_materials",
                "evidence_strength": "direct",
                "public_wording_mode": "direct",
                "evidence_refs": [evidence_ref],
            }
        ],
        "checked_scope": [
            {
                "evidence_class": "reviewed_materials",
                "status": "checked",
                "source_refs": [evidence_ref],
                "limitations": [],
            }
        ],
        "evidence_source_matrix": [
            {
                "claim_id": claim_id,
                "source_class": "reviewed_materials",
                "support_mode": "supports",
                "source_refs": [evidence_ref],
            },
            {
                "claim_id": claim_id,
                "source_class": "thesis_text",
                "support_mode": "partially_supports",
                "source_refs": ["extracted/thesis.txt"],
            },
            {
                "claim_id": claim_id,
                "source_class": "submitted_code_static",
                "support_mode": "limits",
                "source_refs": ["notes/static-code-evidence.md"],
            },
            {
                "claim_id": claim_id,
                "source_class": "build_run_demo",
                "support_mode": "not_checked",
                "source_refs": ["notes/run-demo-evidence.md"],
            },
            {
                "claim_id": claim_id,
                "source_class": "media_visual",
                "support_mode": "not_available",
                "source_refs": ["notes/media-inventory.md"],
                "media_status": "inventoried_only",
            },
        ],
        "technical_report_scope_basis": {
            "status": "operator_accepted_limitation",
            "wording_mode": "manual_check",
            "evidence_refs": [evidence_ref],
            "typed_limitation": {
                "type": "checker_summary_not_available",
                "description": "Fixture records manual acceptance instead of a Theses Checker summary.",
                "accepted_by": "test-operator",
            },
        },
        "strength_grade_tension": {
            "strength_refs": ["outputs/oponent_podklady_revidovane.md"],
            "limiting_factor_refs": ["outputs/oponent_podklady_revidovane.md"],
            "grade_interval_rationale": "Fixture grade interval follows the evidence ledger.",
            "private_comment_focus": "No private comment in this fixture.",
        },
        "defense_question_strategy": [
            {
                "question_id": question_id,
                "purpose": "Probe one evidence gap.",
                "target_item_id": "overall_assessment",
                "evidence_gap_or_tension": "Runtime confidence is limited.",
                "single_focus": True,
            }
            for question_id in question_ids
        ],
        "evaluation_claim_review": {
            **optional_ref,
            "summary": (
                "Partial evaluation evidence exists, but repeatability fields and metric definitions are limited."
            ),
        },
        "scaling_claim_review": {
            **optional_ref,
            "summary": "Scaling and performance language requires stress, boundary, or comparator evidence.",
        },
        "third_party_authorship_review": {
            **optional_ref,
            "summary": (
                "Third-party libraries, assets, AI assistance, and generated code need internal authorship checks."
            ),
        },
        "contribution_boundary_review": {
            **optional_ref,
            "summary": "Student contribution should be separated from framework and library behavior.",
        },
        "citation_support_review": {
            **optional_ref,
            "summary": "Citation support must be checked separately from bibliography relevance.",
        },
        "technical_difficulty_breakdown": {
            **optional_ref,
            "summary": (
                "Technical difficulty is split across integration, algorithmic, platform, and evaluation dimensions."
            ),
        },
        "result_usability_level": {
            **optional_ref,
            "summary": "Result usability is calibrated as demonstrator, prototype, pilot tool, or deployable tool.",
        },
        "deployment_readiness": {
            **optional_ref,
            "summary": "Deployment readiness depends on build, install, run, environment, docs, and demo limitations.",
        },
    }


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
        **opponent_report_quality_controls(),
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
    assert "skutečně zkontrolovanému rozsahu" in report
    assert "každé veřejné tvrzení má odpovídající záznam o tvrzení" in report
    assert "FIT IS rubriky řeší vlastní kritérium" in report
    assert "Theses Checker souhrnu nebo z výslovně přijaté limitace" in report
    assert "strukturovanou kontrolu pro evaluační a metrická tvrzení" in report
    assert "strukturovanou kontrolu pro tvrzení o škálování" in report
    assert "strukturovanou kontrolu pro hranice cizích komponent a autorství" in report
    assert "strukturovanou kontrolu pro hranice vlastního přínosu" in report
    assert "strukturovanou kontrolu pro oporu citací pro tvrzení" in report
    assert "strukturovanou kontrolu pro rozpad technické náročnosti" in report
    assert "strukturovanou kontrolu pro využitelnost výsledku" in report
    assert "strukturovanou kontrolu pro stav nasazení nebo použitelnosti v cílovém prostředí" in report
    assert "U1: Runtime was not fully verified.; stav: carried_to_report" in report
    assert "pokyn: Preserve cautious wording in the overall assessment." in report
    assert "Z dostupných revidovaných podkladů není pro tuto položku" not in report


def test_clean_export_removes_trace_quality_checklist_detail() -> None:
    report = build_report(trace_payload(), trace_hash="a" * 64, materials_hash="b" * 64)
    clean = clean_export_text(report)

    assert "## 12. Před odevzdáním" not in clean
    assert "strukturovanou kontrolu pro" not in clean
    assert "každé veřejné tvrzení má odpovídající záznam" not in clean
    assert "source_trace_path" not in clean
    assert "work/" not in clean
    assert "Formulation for overall_assessment." in clean


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
        "<!-- source_report_calibration_basis_sha256: "
        "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc -->\n"
        "# Návrh oponentského posudku\n"
    )

    stripped = strip_metadata_comments(text)

    assert "work/" not in stripped
    assert "outputs/" not in stripped
    assert "report_calibration" not in stripped
    assert stripped.startswith("# Návrh")


def test_check_text_canonical_mode_rejects_unsupported_source_metadata() -> None:
    text = "<!-- source_theses_checker_summary_sha256: " + "d" * 64 + " -->\n" + calibrated_report_text()
    public_text = strip_metadata_comments(text)
    errors: list[str] = []

    check_text(text, public_text, errors)

    assert any("unsupported source metadata comment" in error for error in errors)


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


def test_check_text_clean_mode_rejects_audit_tables_and_internal_headings() -> None:
    text = (
        clean_report_text()
        + "\n## Synthesis Handoff\n\n"
        + "| Severity | Evidence | Risk |\n"
        + "|---|---|---|\n"
        + "| high | internal | leak |\n"
    )
    errors: list[str] = []

    check_text(text, text, errors, mode="clean")

    assert "clean opponent report proposal must not contain audit-style evidence/risk tables" in errors
    assert any("internal-only heading: ## Synthesis Handoff" in error for error in errors)


def test_check_text_clean_mode_rejects_excessive_questions() -> None:
    questions = "\n".join(f"{index}. Otázka {index}?" for index in range(1, 7))
    text = clean_report_text().replace("1. Otázka?", questions)
    errors: list[str] = []

    check_text(text, text, errors, mode="clean")

    assert "clean opponent report proposal has excessive defense questions: expected at most 5, got 6" in errors


def test_check_text_clean_mode_counts_multiple_questions_on_one_line() -> None:
    questions = "1. První otázka? Druhá otázka? Třetí otázka? Čtvrtá otázka? Pátá otázka? Šestá otázka?"
    text = clean_report_text().replace("1. Otázka?", questions)
    errors: list[str] = []

    check_text(text, text, errors, mode="clean")

    assert "clean opponent report proposal has excessive defense questions: expected at most 5, got 6" in errors


def test_check_text_clean_mode_uses_calibration_question_max_when_declared() -> None:
    questions = "1. První otázka? Druhá otázka? Třetí otázka? Čtvrtá otázka? Pátá otázka? Šestá otázka?"
    text = clean_report_text().replace("1. Otázka?", questions)
    errors: list[str] = []

    check_text(
        text,
        text,
        errors,
        mode="clean",
        expected_report_controls={"defense_question_count": {"max": 6}},
        expected_report_controls_source="test calibration",
    )

    assert not any("excessive defense questions" in error for error in errors)
    assert errors == []


def test_check_text_clean_mode_enforces_declared_public_length_class() -> None:
    long_section = "\n".join(f"Strukturální řádek {index}." for index in range(130))
    text = clean_report_text().replace("## 9. Celkové hodnocení\n\nText.", f"## 9. Celkové hodnocení\n\n{long_section}")
    errors: list[str] = []

    check_text(
        text,
        text,
        errors,
        mode="clean",
        expected_report_controls={"public_report_length": "compact"},
        expected_report_controls_source="test calibration",
    )

    assert any("public_report_length=compact" in error for error in errors)


def test_check_text_clean_mode_enforces_declared_public_word_budget() -> None:
    long_paragraph = " ".join(f"slovo{index}" for index in range(1900))
    text = clean_report_text().replace(
        "## 9. Celkové hodnocení\n\nText.", f"## 9. Celkové hodnocení\n\n{long_paragraph}"
    )
    errors: list[str] = []

    check_text(
        text,
        text,
        errors,
        mode="clean",
        expected_report_controls={"public_report_length": "compact"},
        expected_report_controls_source="test calibration",
    )

    assert any("expected at most 1800 words" in error for error in errors)


def test_check_text_clean_mode_public_length_ignores_private_comment() -> None:
    long_private_comment = " ".join(f"komentar{index}" for index in range(1900))
    text = clean_report_text().replace(
        "Děkuji za práci na prototypu a za dotažení hlavní implementace.\n"
        "K obhajobě si připravte stručné vysvětlení testování, limitů a dalšího možného vývoje.",
        long_private_comment,
    )
    errors: list[str] = []

    check_text(
        text,
        text,
        errors,
        mode="clean",
        expected_report_controls={"public_report_length": "compact"},
        expected_report_controls_source="test calibration",
    )

    assert not any("public_report_length=compact" in error for error in errors)
    assert errors == []


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
