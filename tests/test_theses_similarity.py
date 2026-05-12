import hashlib
import json
from pathlib import Path
from typing import Any

from thesis_review_workflow.structured_evidence import validate_structured_evidence_artifact
from thesis_review_workflow.theses_similarity import (
    THESES_SIMILARITY_ASSESSMENT_SCHEMA,
    build_intake_payload,
    parse_report_text,
    parse_similarity_value,
)

SYNTHETIC_REPORT = """
      Podobnosti se vsemi nalezenymi dokumenty

                               Porovnávaný dokument
Zaverecna prace
Synthetic checked thesis title
Synthetic Student
https://theses.example.invalid/auth/system/podobny_uzel?plag_dokument=/id/current/synthetic.pdf
Zmeneno 1. 1. 2026, 10 000 slov
Podobnost 42 %

                              vyhodnoceno: 12. 5. 2026 12:07

     Zdrojové dokumenty, ve kterych byla nalezena podobnost

1.
Zaverecna prace
Prior synthetic version
https://theses.example.invalid/auth/system/podobny_uzel?plag_dokument=/id/previous/synthetic.pdf
Zmeneno 1. 1. 2025, 9 000 slov
Podobnost 40 %

2.
Zdroj z internetu
Synthetic reference page
example.invalid
https://example.invalid/synthetic-source
Stazeno 1. 1. 2024, 500 slov
Podobnost < 1 %

            Vyznačení podobností ve zkoumanem dokumentu
  1    2
Synthetic extracted paragraph omitted from tracked fixture.
"""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text(round_dir: Path, rel: str, text: str = "fixture\n") -> Path:
    path = round_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def common_assessment(round_dir: Path) -> dict[str, Any]:
    for rel in (
        "inputs/theses_similarity/report.pdf",
        "extracted/theses_similarity/report.txt",
        "work/theses_similarity/intake.json",
        "extracted/thesis.txt",
    ):
        write_text(round_dir, rel)
    write_json(
        round_dir / "work" / "theses_similarity" / "intake.json", {"matched_passages": [{"passage_id": "passage-1"}]}
    )
    return {
        "schema_version": THESES_SIMILARITY_ASSESSMENT_SCHEMA,
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-12T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "thesis-theses-similarity-review",
        "producer_agent": "agent-a",
        "authorization_note": "Current request explicitly authorized agents.",
        "source_refs": [
            "inputs/theses_similarity/report.pdf",
            "extracted/theses_similarity/report.txt",
            "work/theses_similarity/intake.json",
            "extracted/thesis.txt",
        ],
        "source_sha256": {
            rel: sha256_file(round_dir / rel)
            for rel in (
                "inputs/theses_similarity/report.pdf",
                "extracted/theses_similarity/report.txt",
                "work/theses_similarity/intake.json",
                "extracted/thesis.txt",
            )
        },
        "limitations": [],
        "current_submission_match": "unverified",
        "judgments": [
            {
                "judgment_id": "J1",
                "source_ids": [1],
                "passage_refs": ["work/theses_similarity/intake.json#passage-1"],
                "basis_refs": ["extracted/thesis.txt"],
                "category": "self_revision_overlap_unverified",
                "rationale": "Self-overlap requires previous-round confirmation.",
                "confidence": "medium",
                "evidence_refs": ["work/theses_similarity/intake.json", "extracted/thesis.txt"],
                "synthesis_action": "manual_check",
                "requires_reviewer_verification": True,
                "limitations": [],
            }
        ],
    }


def test_parse_similarity_value_preserves_less_than_without_thresholding() -> None:
    value = parse_similarity_value("< 1")

    assert value.raw == "< 1"
    assert value.numeric_value is None
    assert value.less_than == 1.0


def test_parse_report_text_extracts_structural_sources_and_passage_anchors() -> None:
    parsed = parse_report_text(SYNTHETIC_REPORT)

    assert parsed["overall_similarity"] == {"raw": "42", "numeric_value": 42.0, "less_than": None}
    assert parsed["report_evaluated_at_text"] == "12. 5. 2026 12:07"
    assert [item["rank"] for item in parsed["source_documents"]] == [1, 2]
    assert parsed["source_documents"][1]["similarity"] == {
        "raw": "< 1",
        "numeric_value": None,
        "less_than": 1.0,
    }
    assert parsed["matched_passages"][0]["source_ids"] == (1, 2)
    assert "plagiarism" not in json.dumps(parsed).lower()


def test_parse_report_text_ignores_numeric_lines_that_are_not_known_source_markers() -> None:
    parsed = parse_report_text(SYNTHETIC_REPORT + "\n2026\n")

    assert [item["source_ids"] for item in parsed["matched_passages"]] == [(1, 2)]


def test_build_intake_payload_records_current_submission_link_without_judgment() -> None:
    payload = build_intake_payload(
        case_id="case-a",
        round_id="round-a",
        generated_at="2026-05-12T00:00:00Z",
        report_pdf_path="inputs/theses_similarity/report.pdf",
        report_pdf_sha256="a" * 64,
        extracted_text_path="extracted/theses_similarity/report.txt",
        extracted_text_sha256="b" * 64,
        report_text=SYNTHETIC_REPORT,
        page_count=2,
        current_submission_link="unverified",
    )

    assert payload["schema_version"] == "theses-similarity-intake-v1"
    assert payload["current_submission_link"] == "unverified"
    assert payload["report_pdf"]["page_count"] == 2
    assert payload["overall_similarity"]["numeric_value"] == 42.0


def test_validate_theses_similarity_assessment_accepts_anchored_payload(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = common_assessment(round_dir)
    write_json(round_dir / "work" / "theses_similarity" / "assessment.json", payload)

    errors = validate_structured_evidence_artifact(
        round_dir,
        "work/theses_similarity/assessment.json",
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == []


def test_validate_theses_similarity_assessment_rejects_unanchored_judgment(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = common_assessment(round_dir)
    payload["judgments"][0]["basis_refs"] = []
    payload["judgments"][0]["category"] = "copied"
    write_json(round_dir / "work" / "theses_similarity" / "assessment.json", payload)

    errors = validate_structured_evidence_artifact(round_dir, "work/theses_similarity/assessment.json")

    assert any("basis_refs must not be empty" in error for error in errors)
    assert any("category must be one of" in error for error in errors)


def test_validate_theses_similarity_assessment_rejects_whole_file_passage_ref(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = common_assessment(round_dir)
    payload["judgments"][0]["passage_refs"] = ["work/theses_similarity/intake.json"]
    write_json(round_dir / "work" / "theses_similarity" / "assessment.json", payload)

    errors = validate_structured_evidence_artifact(round_dir, "work/theses_similarity/assessment.json")

    assert any("passage ref must be work/theses_similarity/intake.json#<passage-id>" in error for error in errors)


def test_validate_theses_similarity_assessment_rejects_silent_unresolved_item(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = common_assessment(round_dir)
    payload["judgments"][0]["synthesis_action"] = "silent"
    payload["judgments"][0]["requires_reviewer_verification"] = False
    write_json(round_dir / "work" / "theses_similarity" / "assessment.json", payload)

    errors = validate_structured_evidence_artifact(round_dir, "work/theses_similarity/assessment.json")

    assert any("unresolved/material category must not use synthesis_action silent" in error for error in errors)
    assert any("unresolved/material category requires reviewer verification" in error for error in errors)


def test_validate_theses_similarity_assessment_rejects_stale_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = common_assessment(round_dir)
    payload["source_sha256"]["extracted/thesis.txt"] = "0" * 64
    write_json(round_dir / "work" / "theses_similarity" / "assessment.json", payload)

    errors = validate_structured_evidence_artifact(round_dir, "work/theses_similarity/assessment.json")

    assert any("source_sha256 hash is stale for extracted/thesis.txt" in error for error in errors)
