import json
from pathlib import Path
from typing import Any, cast

from thesis_review_workflow.report_calibration import (
    REPORT_CALIBRATION_BASIS_REL,
    validate_report_calibration_artifact,
    validate_report_calibration_payload,
)
from thesis_review_workflow.work_artifacts import sha256_file


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str = "synthetic fixture\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def repo_round(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    (repo / "src" / "thesis_review_workflow").mkdir(parents=True)
    write_text(repo / "profiles" / "default.md", "# Default profile\n\n## Opponent Report Style\n")
    round_dir = repo / "cases" / "case-a" / "rounds" / "round-a"
    write_text(round_dir / "notes" / "opponent-report-operator-feedback.md", "# Operator feedback\n")
    write_text(round_dir / "outputs" / "oponent_podklady_revidovane.md", "# Materials\n")
    return repo, round_dir


def valid_payload(repo: Path, round_dir: Path) -> dict[str, object]:
    operator_rel = "notes/opponent-report-operator-feedback.md"
    return {
        "schema_version": "report-calibration-basis-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "calibration_scope": "opponent_report",
        "reviewer_profile_id": "default",
        "workflow_profile": "opponent_review",
        "operator_surface": "opponent_materials",
        "wave_workflow": "opponent_report",
        "generated_at": "2026-05-20T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "thesis-opponent-materials-reviewer",
        "producer_agent": "agent-a",
        "authorization_note": "Synthetic test authorization.",
        "source_refs": [operator_rel, "outputs/oponent_podklady_revidovane.md"],
        "profile_sources": [
            {
                "path": "profiles/default.md",
                "sha256": sha256_file(repo / "profiles" / "default.md"),
                "sections_used": ["Opponent Report Style"],
            }
        ],
        "operator_calibration_sources": [
            {
                "path": operator_rel,
                "sha256": sha256_file(round_dir / operator_rel),
                "purpose": "report calibration",
            }
        ],
        "related_calibration_artifacts": [],
        "applied_preferences": [
            {
                "preference_id": "opponent.assignment_difficulty.stack_not_enough",
                "source_keys": [
                    "profile:profiles/default.md",
                    f"operator:{operator_rel}",
                ],
                "applies_to": ["assignment_difficulty"],
                "instruction": "Use the structured calibration basis, not profile prose parsing.",
                "priority": "must",
                "status": "applied",
                "decision_reason": "Synthetic operator note confirms this preference applies.",
            }
        ],
        "expected_report_controls": {
            "is_select_values": {
                "Náročnost zadání": "průměrně obtížné zadání",
                "Rozsah splnění požadavků zadání": "zadání splněno s vážnějšími výhradami",
            },
            "overall_grade": "D",
            "overall_points_interval": [65, 74],
            "defense_question_count": {"min": 1, "max": 3},
            "public_report_length": "compact",
            "private_comment_required": True,
        },
        "limitations": [],
    }


def test_report_calibration_basis_validates_hash_bound_sources(tmp_path: Path) -> None:
    repo, round_dir = repo_round(tmp_path)
    write_json(round_dir / REPORT_CALIBRATION_BASIS_REL, valid_payload(repo, round_dir))

    errors = validate_report_calibration_artifact(
        round_dir,
        REPORT_CALIBRATION_BASIS_REL,
        case_id="case-a",
        round_id="round-a",
        expected_reviewer_profile_id="default",
        expected_profile_source_paths=["profiles/default.md"],
    )

    assert errors == []

    (round_dir / "notes" / "opponent-report-operator-feedback.md").write_text("changed\n", encoding="utf-8")

    stale_errors = validate_report_calibration_artifact(
        round_dir,
        REPORT_CALIBRATION_BASIS_REL,
        case_id="case-a",
        round_id="round-a",
        expected_reviewer_profile_id="default",
        expected_profile_source_paths=["profiles/default.md"],
    )

    assert any("hash is stale for notes/opponent-report-operator-feedback.md" in error for error in stale_errors)


def test_report_calibration_rejects_unregistered_operator_note_globs(tmp_path: Path) -> None:
    repo, round_dir = repo_round(tmp_path)
    payload = valid_payload(repo, round_dir)
    payload["source_refs"] = ["notes/random-operator-feedback.md"]
    payload["operator_calibration_sources"] = [
        {
            "path": "notes/random-operator-feedback.md",
            "sha256": "0" * 64,
            "purpose": "report calibration",
        }
    ]

    errors = validate_report_calibration_payload(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
        require_existing_refs=False,
    )

    assert any("path is not a registered operator calibration source" in error for error in errors)


def test_report_calibration_rejects_unbound_preference_source_keys(tmp_path: Path) -> None:
    repo, round_dir = repo_round(tmp_path)
    payload = valid_payload(repo, round_dir)
    applied_preferences = cast(list[dict[str, Any]], payload["applied_preferences"])
    applied_preferences[0]["source_keys"] = [
        "profile:profiles/default.md",
        "operator:notes/opponent-report-review-intake.md",
    ]

    errors = validate_report_calibration_payload(payload, round_dir=round_dir, require_existing_refs=False)

    assert any("source key is not declared in hashed calibration sources" in error for error in errors)


def test_report_calibration_rejects_profile_prose_as_round_ref(tmp_path: Path) -> None:
    repo, round_dir = repo_round(tmp_path)
    payload = valid_payload(repo, round_dir)
    payload["source_refs"] = ["profiles/default.md"]

    errors = validate_report_calibration_payload(payload, round_dir=round_dir, require_existing_refs=False)

    assert any("ref must be relative under inputs/, extracted/, notes/, work/, or outputs/" in error for error in errors)


def test_report_calibration_rejects_invalid_expected_controls(tmp_path: Path) -> None:
    repo, round_dir = repo_round(tmp_path)
    payload = valid_payload(repo, round_dir)
    payload["expected_report_controls"] = {
        "is_select_values": {"Náročnost zadání": "semantic guess from profile prose"},
        "overall_grade": "Z",
        "overall_points_interval": [80, 60],
        "defense_question_count": {"min": 4, "max": 2},
        "public_report_length": "verbose",
        "private_comment_required": "yes",
        "unexpected_control": True,
    }

    errors = validate_report_calibration_payload(payload, round_dir=round_dir, require_existing_refs=False)

    assert any("unsupported value" in error for error in errors)
    assert any("overall_grade must be one of" in error for error in errors)
    assert any("overall_points_interval must stay within 0-100" in error for error in errors)
    assert any("defense_question_count min cannot exceed max" in error for error in errors)
    assert any("public_report_length must be one of" in error for error in errors)
    assert any("private_comment_required must be bool" in error for error in errors)
    assert any("expected_report_controls has unknown key" in error for error in errors)


def test_report_calibration_rejects_empty_controls_and_grade_interval_mismatch(tmp_path: Path) -> None:
    repo, round_dir = repo_round(tmp_path)
    payload = valid_payload(repo, round_dir)
    payload["expected_report_controls"] = {}

    empty_errors = validate_report_calibration_payload(payload, round_dir=round_dir, require_existing_refs=False)

    assert any("expected_report_controls must contain at least one known control" in error for error in empty_errors)

    payload["expected_report_controls"] = {
        "overall_grade": "A",
        "overall_points_interval": [65, 74],
    }

    mismatch_errors = validate_report_calibration_payload(payload, round_dir=round_dir, require_existing_refs=False)

    assert any("overall_points_interval does not overlap grade A band" in error for error in mismatch_errors)


def test_report_calibration_rejects_non_effective_profile_sources(tmp_path: Path) -> None:
    repo, round_dir = repo_round(tmp_path)
    payload = valid_payload(repo, round_dir)
    write_text(repo / "profiles" / "local" / "other.md", "# Other profile\n")
    profile_sources = cast(list[dict[str, Any]], payload["profile_sources"])
    profile_sources.append(
        {
            "path": "profiles/local/other.md",
            "sha256": sha256_file(repo / "profiles" / "local" / "other.md"),
            "sections_used": ["Opponent Report Style"],
        }
    )

    errors = validate_report_calibration_payload(
        payload,
        round_dir=round_dir,
        require_existing_refs=False,
        expected_reviewer_profile_id="default",
        expected_profile_source_paths=["profiles/default.md"],
    )

    assert any("profile_sources includes non-effective reviewer profile source profiles/local/other.md" in error for error in errors)

    payload["reviewer_profile_id"] = "other"
    profile_errors = validate_report_calibration_payload(
        payload,
        round_dir=round_dir,
        require_existing_refs=False,
        expected_reviewer_profile_id="default",
        expected_profile_source_paths=["profiles/default.md"],
    )

    assert any("reviewer_profile_id does not match case Reviewer profile" in error for error in profile_errors)
