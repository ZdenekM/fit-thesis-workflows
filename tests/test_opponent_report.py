import hashlib
from pathlib import Path

from thesis_review_workflow.cli.check_opponent_report import (
    DEFAULT_DRAFT,
    strip_metadata_comments,
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
    assert "Formulation for assignment_difficulty." in report
    assert "- Prepared defense question?" in report
    assert "- Manual point and grade calibration." in report
    assert "U1: Runtime was not fully verified.; stav: carried_to_report" in report
    assert "pokyn: Preserve cautious wording in the overall assessment." in report
    assert "Z dostupných revidovaných podkladů není pro tuto položku" not in report


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
        "# Návrh oponentského posudku\n"
    )

    stripped = strip_metadata_comments(text)

    assert "work/" not in stripped
    assert "outputs/" not in stripped
    assert stripped.startswith("# Návrh")
