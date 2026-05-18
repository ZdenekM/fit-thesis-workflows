import json
from pathlib import Path

from thesis_review_workflow.cli import check_figure_media_review


def test_figure_media_checker_rejects_blocked_structured_role_state(tmp_path: Path) -> None:
    errors: list[str] = []
    coverage = tmp_path / "work" / "agent_coverage.json"
    coverage.parent.mkdir(parents=True)
    coverage.write_text(
        json.dumps(
            {
                "schema_version": "agent-coverage-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "roles": [
                    {
                        "role": "figure_media",
                        "status": "blocked",
                        "coverage_satisfied_by": "typed_limitation",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    check_figure_media_review.check_structured_pipeline_state(tmp_path, errors)

    assert errors == [
        "agent coverage records figure_media as blocked; rerun the role or keep it as a typed limitation "
        "before relying on figure/media evidence"
    ]


def test_figure_media_checker_rejects_structured_parent_fallback(tmp_path: Path) -> None:
    errors: list[str] = []
    coverage = tmp_path / "work" / "agent_coverage.json"
    coverage.parent.mkdir(parents=True)
    coverage.write_text(
        json.dumps(
            {
                "schema_version": "agent-coverage-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "roles": [
                    {
                        "role": "figure_media",
                        "status": "required",
                        "coverage_satisfied_by": "fresh_role_review",
                        "generator_role": "thesis-figure-media-review",
                        "generator_agent": "limited_figure_media_parent_review",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    check_figure_media_review.check_structured_pipeline_state(tmp_path, errors)

    assert errors == [
        "agent coverage records a parent/fallback/limited figure_media generator or reviewer; "
        "rerun the role or record a blocked typed limitation before relying on this evidence"
    ]


def test_figure_media_checker_does_not_scan_markdown_text_for_failure_words(tmp_path: Path) -> None:
    errors: list[str] = []

    check_figure_media_review.check_structured_pipeline_state(Path(tmp_path), errors)

    assert errors == []
