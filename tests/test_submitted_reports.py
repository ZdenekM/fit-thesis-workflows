import json
from pathlib import Path

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.cli import (
    record_submitted_opponent_report,
    record_submitted_report_delta,
    record_submitted_supervisor_report,
)
from thesis_review_workflow.structured_evidence import STRUCTURED_EVIDENCE_SCHEMAS
from thesis_review_workflow.submitted_report_deltas import (
    OPPONENT_REPORT_DELTAS_REL,
    build_opponent_submitted_report_delta_payload,
    validate_opponent_submitted_report_deltas,
)
from thesis_review_workflow.submitted_reports import (
    OPPONENT_REPORT_APPROVAL_REL,
    OPPONENT_REPORT_CLEAN_REL,
    OPPONENT_REPORT_REVIEW_REL,
    OPPONENT_REPORT_SUBMITTED_PDF_REL,
    OPPONENT_REPORT_SUBMITTED_RECORD_REL,
    OPPONENT_REPORT_SUBMITTED_TEXT_REL,
    SUPERVISOR_REPORT_SUBMITTED_PDF_REL,
    SUPERVISOR_REPORT_SUBMITTED_RECORD_REL,
    SUPERVISOR_REPORT_SUBMITTED_TEXT_REL,
    build_opponent_submitted_report_payload,
    build_supervisor_submitted_report_payload,
    opponent_public_report_text,
    validate_submitted_opponent_report_record,
    validate_submitted_report_record,
)
from thesis_review_workflow.supervisor_report import (
    SUPERVISOR_REPORT_CONFIRMATION_REL,
    SUPERVISOR_REPORT_REVIEWED_REL,
    public_report_text,
)


def reviewed_report_text(*, grade: str = "B", points: int = 82) -> str:
    return f"""# Posudek vedoucího

## Informace k zadání

Zadání bylo splněno.

## Práce s literaturou

Student pracoval s literaturou.

## Aktivita během řešení, konzultace, komunikace

Student konzultoval průběžně.

## Aktivita při dokončování

Definitivní obsah byl konzultován.

## Publikační činnost, ocenění

Publikace nejsou.

## Celkové hodnocení

Práci doporučuji hodnotit jako velmi dobrou.

Známka: {grade}
Body: {points}

## Komentář pro studenta

Děkuji za práci.
"""


def write_confirmation(round_dir: Path, *, grade: str = "B", points: int = 82) -> None:
    reviewed = round_dir / SUPERVISOR_REPORT_REVIEWED_REL
    confirmation = {
        "schema_version": STRUCTURED_EVIDENCE_SCHEMAS[SUPERVISOR_REPORT_CONFIRMATION_REL],
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-13T00:00:00Z",
        "producer_type": "human",
        "producer_role": "supervisor",
        "producer_agent": None,
        "human_reviewer_note": "Confirmed.",
        "source_refs": [SUPERVISOR_REPORT_REVIEWED_REL],
        "limitations": [],
        "reviewed_report_path": SUPERVISOR_REPORT_REVIEWED_REL,
        "reviewed_report_sha256": sha256_file(reviewed),
        "grade": grade,
        "points": points,
        "official_text_confirmed": True,
        "student_comment_confirmed": True,
        "ready_for_is": True,
        "confirmed_by": "supervisor",
        "confirmed_at": "2026-05-13T00:00:00Z",
    }
    path = round_dir / SUPERVISOR_REPORT_CONFIRMATION_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(confirmation, indent=2) + "\n", encoding="utf-8")


def make_submitted_round(tmp_path: Path, *, submitted_text: str | None = None) -> Path:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    reviewed = round_dir / SUPERVISOR_REPORT_REVIEWED_REL
    reviewed.parent.mkdir(parents=True)
    reviewed.write_text(reviewed_report_text(), encoding="utf-8")
    write_confirmation(round_dir)
    pdf = round_dir / SUPERVISOR_REPORT_SUBMITTED_PDF_REL
    text = round_dir / SUPERVISOR_REPORT_SUBMITTED_TEXT_REL
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4\n% synthetic\n")
    text.write_text(
        submitted_text if submitted_text is not None else public_report_text(reviewed.read_text()), encoding="utf-8"
    )
    return round_dir


def opponent_report_text(
    *, grade: str = "B", points: int = 80, conclusion: str = "Práci doporučuji k obhajobě."
) -> str:
    private_comment = (
        "Tento neveřejný komentář stručně shrnuje kalibraci pro studenta a zachovává "
        "samostatnou privátní část mimo veřejný PDF export."
    )
    return f"""# Návrh oponentského posudku

## IS formulář (výběry a body)

Náročnost zadání: obtížnější zadání
Rozsah splnění požadavků zadání: zadání splněno s drobnými výhradami
Rozsah technické zprávy: je v obvyklém rozmezí
Prezentační úroveň technické zprávy: 80 bodů
Formální úprava technické zprávy: 80 bodů
Práce s literaturou: 80 bodů
Realizační výstup: 80 bodů

## 1. Náročnost zadání

Zadání bylo obtížnější a vyžadovalo samostatnou implementaci.

## 2. Rozsah splnění požadavků zadání

Zadání je splněno s drobnými výhradami.

## 3. Rozsah technické zprávy

Technická zpráva je v obvyklém rozmezí.

## 4. Prezentační úroveň technické zprávy

Text je srozumitelný a má drobné rezervy v návaznosti argumentů.

## 5. Formální úprava technické zprávy

Formální úprava je přijatelná.

## 6. Práce s literaturou

Literatura je využita adekvátně.

## 7. Realizační výstup

Realizační výstup odpovídá cílům práce.

## 8. Využitelnost výsledku

Výsledek je použitelný jako základ další práce.

## 9. Celkové hodnocení

{conclusion}

## 10. Otázky k obhajobě

- Jak byste ověřil robustnost řešení na větším vzorku dat?
- Kterou část implementace byste přepracoval jako první?

## 11. Body a známka

Známka: {grade}
Body: {points}

## Komentář pro studenta (neveřejná část)

{private_comment}
"""


def write_opponent_approval(round_dir: Path) -> None:
    clean = round_dir / OPPONENT_REPORT_CLEAN_REL
    review = round_dir / OPPONENT_REPORT_REVIEW_REL
    review.parent.mkdir(parents=True, exist_ok=True)
    review.write_text("# Review\n\nNo blockers.\n", encoding="utf-8")
    approval = {
        "schema_version": "review-approval-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-18T00:00:00Z",
        "producer_type": "human",
        "producer_role": "thesis_opponent_report_reviewer",
        "producer_agent": None,
        "human_reviewer_note": "Approved.",
        "source_refs": [OPPONENT_REPORT_REVIEW_REL, OPPONENT_REPORT_CLEAN_REL],
        "limitations": [],
        "workflow_profile": "opponent_report_review",
        "verdict": "approved",
        "blocking_findings_count": 0,
        "reviewed_artifact_path": OPPONENT_REPORT_REVIEW_REL,
        "reviewed_artifact_sha256": sha256_file(review),
        "review_basis_path": OPPONENT_REPORT_CLEAN_REL,
        "review_basis_sha256": sha256_file(clean),
        "observed_checks": ["check-opponent-report:clean"],
        "approved_by": "reviewer",
        "approved_at": "2026-05-18T00:00:00Z",
    }
    approval_path = round_dir / OPPONENT_REPORT_APPROVAL_REL
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text(json.dumps(approval, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def make_submitted_opponent_round(tmp_path: Path, *, submitted_text: str | None = None) -> Path:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    clean = round_dir / OPPONENT_REPORT_CLEAN_REL
    clean.parent.mkdir(parents=True)
    clean.write_text(opponent_report_text(), encoding="utf-8")
    write_opponent_approval(round_dir)
    pdf = round_dir / OPPONENT_REPORT_SUBMITTED_PDF_REL
    text = round_dir / OPPONENT_REPORT_SUBMITTED_TEXT_REL
    pdf.parent.mkdir(parents=True)
    text.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4\n% synthetic opponent report\n")
    text.write_text(
        submitted_text if submitted_text is not None else opponent_public_report_text(clean.read_text()),
        encoding="utf-8",
    )
    return round_dir


def test_submitted_supervisor_report_record_binds_pdf_text_reviewed_report_and_confirmation(tmp_path: Path) -> None:
    round_dir = make_submitted_round(tmp_path)

    payload = build_supervisor_submitted_report_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        submitted_at="2026-05-13T00:00:00Z",
        recorded_by="operator",
    )

    assert payload["schema_version"] == "submitted-report-v1"
    assert payload["report_kind"] == "supervisor_report"
    assert payload["recorded_by"] == "operator"
    assert payload["ready_for_archive"] is True
    assert payload["public_text_normalized_match"] is True
    assert payload["grade"] == "B"
    assert payload["points"] == 82
    assert validate_submitted_report_record(payload, round_dir=round_dir, case_id="case-a", round_id="round-a") == []


def test_submitted_supervisor_report_rejects_public_text_mismatch(tmp_path: Path) -> None:
    round_dir = make_submitted_round(tmp_path, submitted_text="Známka: B\nBody: 82\nJiny verejny text.\n")

    payload = build_supervisor_submitted_report_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        submitted_at="2026-05-13T00:00:00Z",
        recorded_by="operator",
    )

    errors = validate_submitted_report_record(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
        rel_path=SUPERVISOR_REPORT_SUBMITTED_RECORD_REL,
    )

    assert (
        f"{SUPERVISOR_REPORT_SUBMITTED_RECORD_REL}: submitted public text does not match reviewed public report text"
        in errors
    )


def test_submitted_supervisor_report_validation_recomputes_record_state(tmp_path: Path) -> None:
    round_dir = make_submitted_round(tmp_path)
    payload = build_supervisor_submitted_report_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        submitted_at="2026-05-13T00:00:00Z",
        recorded_by="operator",
    )
    payload["reviewed_points"] = 83
    payload["public_text_normalized_match"] = False

    errors = validate_submitted_report_record(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
        rel_path=SUPERVISOR_REPORT_SUBMITTED_RECORD_REL,
    )

    assert f"{SUPERVISOR_REPORT_SUBMITTED_RECORD_REL}: reviewed_points is stale" in errors
    assert f"{SUPERVISOR_REPORT_SUBMITTED_RECORD_REL}: public_text_normalized_match is stale" in errors


def test_record_submitted_supervisor_report_rolls_back_copies_on_rejected_record(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    reviewed = round_dir / SUPERVISOR_REPORT_REVIEWED_REL
    reviewed.parent.mkdir(parents=True)
    reviewed.write_text(reviewed_report_text(), encoding="utf-8")
    write_confirmation(round_dir)
    (root / "cases" / "case-a" / "case.md").write_text(
        "Work type: BP\nAcademic year: 2025/2026\nReviewer profile: default\n",
        encoding="utf-8",
    )
    (root / "cases" / "case-a" / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    submitted_pdf = tmp_path / "submitted.pdf"
    submitted_text = tmp_path / "submitted.txt"
    submitted_pdf.write_bytes(b"%PDF-1.4\n% synthetic\n")
    submitted_text.write_text("Známka: B\nBody: 82\nJiny verejny text.\n", encoding="utf-8")
    monkeypatch.setattr(record_submitted_supervisor_report, "repo_root", lambda: root)

    result = record_submitted_supervisor_report.main(
        [
            "case-a",
            "round-a",
            "--pdf",
            str(submitted_pdf),
            "--public-text-file",
            str(submitted_text),
            "--recorded-by",
            "operator",
        ]
    )

    assert result == 1
    assert not (round_dir / SUPERVISOR_REPORT_SUBMITTED_PDF_REL).exists()
    assert not (round_dir / SUPERVISOR_REPORT_SUBMITTED_TEXT_REL).exists()
    assert not (round_dir / SUPERVISOR_REPORT_SUBMITTED_RECORD_REL).exists()


def test_submitted_opponent_report_record_binds_clean_review_approval_pdf_and_public_text(tmp_path: Path) -> None:
    round_dir = make_submitted_opponent_round(tmp_path)

    payload = build_opponent_submitted_report_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        submitted_at="2026-05-18T00:00:00Z",
        recorded_by="operator",
    )

    assert payload["schema_version"] == "submitted-report-v1"
    assert payload["report_kind"] == "opponent_report"
    assert payload["recorded_by"] == "operator"
    assert payload["ready_for_archive"] is True
    assert payload["public_text_normalized_match"] is True
    assert payload["field_values_match"] is True
    assert payload["grade"] == "B"
    assert payload["points"] == 80
    assert payload["public_text_section_diffs"] == []
    assert (
        validate_submitted_opponent_report_record(
            payload,
            round_dir=round_dir,
            case_id="case-a",
            round_id="round-a",
        )
        == []
    )


def test_submitted_opponent_report_diff_requires_accepted_delta_for_archive_readiness(tmp_path: Path) -> None:
    clean = opponent_report_text()
    submitted = opponent_public_report_text(clean).replace(
        "Práci doporučuji k obhajobě.",
        "Práci doporučuji k obhajobě. IS export obsahuje drobnou jazykovou úpravu.",
    )
    round_dir = make_submitted_opponent_round(tmp_path, submitted_text=submitted)
    payload = build_opponent_submitted_report_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        submitted_at="2026-05-18T00:00:00Z",
        recorded_by="operator",
    )
    (round_dir / OPPONENT_REPORT_SUBMITTED_RECORD_REL).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    assert payload["ready_for_archive"] is False
    assert payload["public_text_section_diffs"][0]["section"] == "## 9. Celkové hodnocení"
    errors = validate_submitted_opponent_report_record(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )
    assert any("submitted public text does not match reviewed public report projection" in error for error in errors)

    deltas = build_opponent_submitted_report_delta_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        generated_at="2026-05-18T00:01:00Z",
        recorded_by="operator",
        sections=["## 9. Celkové hodnocení"],
        classification="operator_wording_non_material",
        rationale="Non-material wording correction made while entering the IS form.",
    )
    (round_dir / OPPONENT_REPORT_DELTAS_REL).write_text(
        json.dumps(deltas, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    assert deltas["ready_for_archive_with_deltas"] is True
    assert (
        validate_opponent_submitted_report_deltas(
            deltas,
            round_dir=round_dir,
            case_id="case-a",
            round_id="round-a",
        )
        == []
    )
    assert (
        validate_submitted_opponent_report_record(
            payload,
            round_dir=round_dir,
            case_id="case-a",
            round_id="round-a",
        )
        == []
    )


def test_submitted_opponent_report_rejects_material_or_uncovered_deltas(tmp_path: Path) -> None:
    clean = opponent_report_text()
    submitted = opponent_public_report_text(clean).replace(
        "Práci doporučuji k obhajobě.",
        "Práci doporučuji k obhajobě. Závěr byl po odevzdání rozšířen.",
    )
    round_dir = make_submitted_opponent_round(tmp_path, submitted_text=submitted)
    record = build_opponent_submitted_report_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        submitted_at="2026-05-18T00:00:00Z",
        recorded_by="operator",
    )
    (round_dir / OPPONENT_REPORT_SUBMITTED_RECORD_REL).write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    deltas = build_opponent_submitted_report_delta_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        generated_at="2026-05-18T00:01:00Z",
        recorded_by="operator",
        sections=["## 9. Celkové hodnocení"],
        classification="material_change",
        rationale="The public conclusion changed materially after review.",
    )

    assert deltas["ready_for_archive_with_deltas"] is False
    assert (
        validate_opponent_submitted_report_deltas(
            deltas,
            round_dir=round_dir,
            case_id="case-a",
            round_id="round-a",
            require_archive_ready=False,
        )
        == []
    )
    errors = validate_opponent_submitted_report_deltas(
        deltas,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )
    assert any("material submitted-report delta reopens opponent report review" in error for error in errors)


def test_submitted_opponent_report_delta_is_bound_to_current_submitted_record(tmp_path: Path) -> None:
    clean = opponent_report_text()
    submitted = opponent_public_report_text(clean).replace(
        "Práci doporučuji k obhajobě.",
        "Práci doporučuji k obhajobě. IS export obsahuje drobnou jazykovou úpravu.",
    )
    round_dir = make_submitted_opponent_round(tmp_path, submitted_text=submitted)
    payload = build_opponent_submitted_report_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        submitted_at="2026-05-18T00:00:00Z",
        recorded_by="operator",
    )
    record_path = round_dir / OPPONENT_REPORT_SUBMITTED_RECORD_REL
    record_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    deltas = build_opponent_submitted_report_delta_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        generated_at="2026-05-18T00:01:00Z",
        recorded_by="operator",
        sections=["## 9. Celkové hodnocení"],
        classification="operator_wording_non_material",
        rationale="Non-material wording correction made while entering the IS form.",
    )
    (round_dir / OPPONENT_REPORT_DELTAS_REL).write_text(
        json.dumps(deltas, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    payload["recorded_by"] = "different-operator"
    record_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    errors = validate_submitted_opponent_report_record(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert any("submitted_record_sha256 is stale" in error for error in errors)
    assert any("submitted public text does not match reviewed public report projection" in error for error in errors)


def test_submitted_opponent_report_defense_question_section_change_blocks_delta_archive(tmp_path: Path) -> None:
    clean = opponent_report_text()
    submitted = opponent_public_report_text(clean).replace(
        "Kterou část implementace byste přepracoval jako první?",
        "Kterou část implementace byste ponechal beze změny?",
    )
    round_dir = make_submitted_opponent_round(tmp_path, submitted_text=submitted)
    payload = build_opponent_submitted_report_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        submitted_at="2026-05-18T00:00:00Z",
        recorded_by="operator",
    )
    (round_dir / OPPONENT_REPORT_SUBMITTED_RECORD_REL).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    deltas = build_opponent_submitted_report_delta_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        generated_at="2026-05-18T00:01:00Z",
        recorded_by="operator",
        sections=["## 10. Otázky k obhajobě"],
        classification="operator_wording_non_material",
        rationale="Attempted to treat question wording as a bounded text edit.",
    )

    assert deltas["field_values_match"] is False
    assert deltas["ready_for_archive_with_deltas"] is False
    (round_dir / OPPONENT_REPORT_DELTAS_REL).write_text(
        json.dumps(deltas, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    errors = validate_submitted_opponent_report_record(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )
    assert any("submitted public text field values do not match reviewed report basis" in error for error in errors)


def test_submitted_opponent_report_validation_recomputes_record_state(tmp_path: Path) -> None:
    round_dir = make_submitted_opponent_round(tmp_path)
    payload = build_opponent_submitted_report_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        submitted_at="2026-05-18T00:00:00Z",
        recorded_by="operator",
    )
    payload["reviewed_points"] = 81
    payload["public_text_section_diffs"] = [{"section": "stale"}]

    errors = validate_submitted_opponent_report_record(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
        rel_path=OPPONENT_REPORT_SUBMITTED_RECORD_REL,
    )

    assert f"{OPPONENT_REPORT_SUBMITTED_RECORD_REL}: reviewed_points is stale" in errors
    assert f"{OPPONENT_REPORT_SUBMITTED_RECORD_REL}: public_text_section_diffs is stale" in errors


def test_submitted_opponent_report_rejects_bare_internal_artifact_names(tmp_path: Path) -> None:
    submitted = opponent_public_report_text(opponent_report_text()).replace(
        "Práci doporučuji k obhajobě.",
        "Práci doporučuji k obhajobě. Viz oponent_posudek_navrh.md.",
    )
    round_dir = make_submitted_opponent_round(tmp_path, submitted_text=submitted)
    payload = build_opponent_submitted_report_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        submitted_at="2026-05-18T00:00:00Z",
        recorded_by="operator",
    )

    errors = validate_submitted_opponent_report_record(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
        require_archive_ready=False,
    )

    assert any("oponent_posudek_navrh" in error for error in errors)


def test_record_submitted_opponent_report_writes_nonready_capture_for_delta_followup(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    clean = round_dir / OPPONENT_REPORT_CLEAN_REL
    clean.parent.mkdir(parents=True)
    clean.write_text(opponent_report_text(), encoding="utf-8")
    write_opponent_approval(round_dir)
    (root / "cases" / "case-a" / "case.md").write_text(
        "Work type: BP\nAcademic year: 2025/2026\nReviewer profile: default\n",
        encoding="utf-8",
    )
    (root / "cases" / "case-a" / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    submitted_pdf = tmp_path / "submitted.pdf"
    submitted_text = tmp_path / "submitted.txt"
    submitted_pdf.write_bytes(b"%PDF-1.4\n% synthetic\n")
    submitted_text.write_text(
        opponent_public_report_text(clean.read_text()).replace(
            "Práci doporučuji k obhajobě.",
            "Práci doporučuji k obhajobě. IS export obsahuje jazykovou úpravu.",
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(record_submitted_opponent_report, "repo_root", lambda: root)

    result = record_submitted_opponent_report.main(
        [
            "case-a",
            "round-a",
            "--pdf",
            str(submitted_pdf),
            "--public-text-file",
            str(submitted_text),
            "--recorded-by",
            "operator",
            "--submitted-at",
            "2026-05-18T00:00:00Z",
        ]
    )

    assert result == 0
    payload = json.loads((round_dir / OPPONENT_REPORT_SUBMITTED_RECORD_REL).read_text(encoding="utf-8"))
    assert payload["ready_for_archive"] is False
    assert payload["public_text_section_diffs"][0]["section"] == "## 9. Celkové hodnocení"

    monkeypatch.setattr(record_submitted_report_delta, "repo_root", lambda: root)
    result = record_submitted_report_delta.main(
        [
            "case-a",
            "round-a",
            "--section",
            "## 9. Celkové hodnocení",
            "--classification",
            "operator_wording_non_material",
            "--rationale",
            "Non-material IS form wording correction.",
            "--recorded-by",
            "operator",
            "--recorded-at",
            "2026-05-18T00:01:00Z",
        ]
    )

    assert result == 0
    assert (
        validate_submitted_opponent_report_record(
            payload,
            round_dir=round_dir,
            case_id="case-a",
            round_id="round-a",
        )
        == []
    )
