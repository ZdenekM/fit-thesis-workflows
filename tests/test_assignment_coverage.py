from pathlib import Path
from typing import Any, cast

from thesis_review_workflow.assignment_coverage import build_map, parse_assignment_points


def test_parse_assignment_points_prefers_assignment_sections() -> None:
    points = parse_assignment_points(
        "\n".join(
            [
                "# Assignment Context",
                "## Formal Assignment Text Or Summary",
                "1. Implement a prototype for data import.",
                "2. Evaluate usability with students.",
                "## Private Assignment Notes For Student",
                "- private note",
                "## Assignment Coverage Hints",
                "- Describe deployment limits.",
            ]
        )
    )

    assert [point.point_id for point in points] == ["A1", "A2", "A3"]
    assert points[0].text == "Implement a prototype for data import."
    assert points[2].source_section == "Assignment Coverage Hints"


def test_parse_assignment_points_does_not_fallback_to_private_notes() -> None:
    points = parse_assignment_points(
        "\n".join(
            [
                "# Assignment Context",
                "## Private Assignment Notes For Student",
                "- Private lab note that is not a formal assignment point.",
            ]
        )
    )

    assert points == []


def test_build_map_marks_materials_and_draft_mentions(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "outputs").mkdir()
    (round_dir / "work").mkdir()
    (round_dir / "notes" / "assignment.md").write_text(
        "\n".join(
            [
                "# Assignment Context",
                "## Formal Assignment Text Or Summary",
                "- Implement prototype for import workflow.",
                "- Evaluate usability with students.",
            ]
        ),
        encoding="utf-8",
    )
    (round_dir / "outputs" / "oponent_podklady_revidovane.md").write_text(
        "The import workflow prototype is covered with README evidence.\n",
        encoding="utf-8",
    )
    (round_dir / "work" / "oponent_posudek_draft.md").write_text(
        "The usability evaluation is discussed cautiously.\n",
        encoding="utf-8",
    )

    artifact = build_map("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    rows = cast(list[dict[str, Any]], artifact["assignment_points"])

    assert artifact["schema_version"] == "assignment-coverage-map-v1"
    assert artifact["assignment_source_present"] is True
    assert artifact["parser_limitations"] == []
    assert rows[0]["opponent_materials"]["state"] == "mentioned"
    assert rows[0]["opponent_report_draft"]["state"] in {"partial", "not_found"}
    assert rows[1]["opponent_report_draft"]["state"] == "partial"


def test_build_map_records_missing_assignment_limitation(tmp_path: Path) -> None:
    artifact = build_map("case-a", "round-a", "2026-05-06T00:00:00Z", tmp_path / "round")

    assert artifact["assignment_source_present"] is False
    assert artifact["assignment_points"] == []
    assert artifact["parser_limitations"]
