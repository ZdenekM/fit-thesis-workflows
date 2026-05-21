import json
from pathlib import Path
from typing import Any, cast

from thesis_review_workflow.cli import check_report_calibration
from thesis_review_workflow.report_calibration import (
    REPORT_CALIBRATION_APPLICABILITY_NOT_APPLICABLE,
    REPORT_CALIBRATION_APPLICABILITY_UNBOUND,
    REPORT_CALIBRATION_BASIS_REL,
    REPORT_CALIBRATION_NOT_APPLICABLE_LIMITATION_TYPE,
    report_calibration_applicability,
    report_calibration_check_targets,
    report_calibration_dependency_files,
    validate_report_calibration_artifact,
    validate_report_calibration_payload,
)
from thesis_review_workflow.structured_evidence import OPPONENT_REPORT_TRACE_REL, REQUIRED_OPPONENT_IS_ITEM_IDS
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
    write_text(repo / "cases" / "case-a" / "case.md", "Reviewer profile: default\n")
    write_text(round_dir / "notes" / "opponent-report-operator-feedback.md", "# Operator feedback\n")
    write_text(round_dir / "work" / "oponent_posudek_draft.md", "# Draft report\n")
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


def report_trace_quality_controls() -> dict[str, object]:
    evidence_ref = "outputs/oponent_podklady_revidovane.md"
    claim_id = "claim-overall"
    return {
        "assignment_fulfillment_map": {
            "source_refs": [evidence_ref],
            "points": [
                {
                    "point_id": "assignment-point-1",
                    "summary": "Synthetic assignment point is partially evidenced.",
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
                "criterion_scope": "Synthetic fixture checks the item independently.",
                "evidence_refs": [evidence_ref],
                "do_not_mix_with": ["overall_assessment"],
                "wording_tone": "Evidence-bound and compact.",
            }
            for item_id in sorted(REQUIRED_OPPONENT_IS_ITEM_IDS)
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
            }
        ],
        "technical_report_scope_basis": {
            "status": "operator_accepted_limitation",
            "wording_mode": "manual_check",
            "evidence_refs": [evidence_ref],
            "typed_limitation": {
                "type": "checker_summary_not_available",
                "description": "Synthetic fixture records manual acceptance instead of a Theses Checker summary.",
                "accepted_by": "test-operator",
            },
        },
        "strength_grade_tension": {
            "strength_refs": [evidence_ref],
            "limiting_factor_refs": [evidence_ref],
            "grade_interval_rationale": "Synthetic grade interval follows the evidence ledger.",
            "private_comment_focus": "No private comment in this fixture.",
        },
        "defense_question_strategy": [
            {
                "question_id": "D1",
                "purpose": "Probe one evidence gap.",
                "target_item_id": "overall_assessment",
                "evidence_gap_or_tension": "Runtime confidence is limited.",
                "single_focus": True,
            }
        ],
    }


def valid_not_applicable_trace(repo: Path, round_dir: Path) -> dict[str, object]:
    materials_hash = sha256_file(round_dir / "outputs" / "oponent_podklady_revidovane.md")
    operator_rel = "notes/opponent-report-operator-feedback.md"
    profile_rel = "profiles/default.md"
    return {
        "schema_version": "opponent-report-trace-v2",
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-20T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "thesis-opponent-materials-reviewer",
        "producer_agent": "agent-a",
        "authorization_note": "Synthetic test authorization.",
        "source_refs": ["outputs/oponent_podklady_revidovane.md", operator_rel],
        "source_materials_path": "outputs/oponent_podklady_revidovane.md",
        "source_materials_sha256": materials_hash,
        "trace_review_status": "accepted",
        "reviewer_role": "independent-opponent-report-trace-reviewer",
        "reviewed_at": "2026-05-20T00:00:00Z",
        "trace_generated_from": ["outputs/oponent_podklady_revidovane.md"],
        "is_items": [
            {
                "item_id": item_id,
                "title": item_id.replace("_", " "),
                "formulation": "Draft-ready formulation.",
                "evidence_refs": ["outputs/oponent_podklady_revidovane.md"],
            }
            for item_id in sorted(REQUIRED_OPPONENT_IS_ITEM_IDS)
        ],
        "defense_questions": [
            {
                "question_id": "D1",
                "question": "Which evidence gap should the student explain?",
                "evidence_refs": ["outputs/oponent_podklady_revidovane.md"],
            }
        ],
        "pre_submission_checks": [
            {
                "check_id": "C1",
                "instruction": "Check final IS controls manually.",
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
        **report_trace_quality_controls(),
        "report_calibration_limitation": {
            "type": REPORT_CALIBRATION_NOT_APPLICABLE_LIMITATION_TYPE,
            "calibration_scope": "opponent_report",
            "reviewer_profile_id": "default",
            "assessed_by": "agent",
            "assessor_role": "thesis-opponent-materials-review",
            "assessed_at": "2026-05-20T00:00:00Z",
            "profile_sources": [
                {
                    "path": profile_rel,
                    "sha256": sha256_file(repo / profile_rel),
                }
            ],
            "operator_calibration_sources": [
                {
                    "path": operator_rel,
                    "sha256": sha256_file(round_dir / operator_rel),
                }
            ],
            "rationale": "Synthetic reviewer found no applicable profile-specific or operator-calibration preference.",
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

    assert any(
        "ref must be relative under inputs/, extracted/, notes/, work/, or outputs/" in error for error in errors
    )


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

    assert any(
        "profile_sources includes non-effective reviewer profile source profiles/local/other.md" in error
        for error in errors
    )

    payload["reviewer_profile_id"] = "other"
    profile_errors = validate_report_calibration_payload(
        payload,
        round_dir=round_dir,
        require_existing_refs=False,
        expected_reviewer_profile_id="default",
        expected_profile_source_paths=["profiles/default.md"],
    )

    assert any("reviewer_profile_id does not match case Reviewer profile" in error for error in profile_errors)


def test_report_calibration_applicability_accepts_typed_not_applicable_limitation(tmp_path: Path) -> None:
    _repo, round_dir = repo_round(tmp_path)
    write_json(
        round_dir / OPPONENT_REPORT_TRACE_REL,
        {
            "report_calibration_limitation": {
                "type": REPORT_CALIBRATION_NOT_APPLICABLE_LIMITATION_TYPE,
                "calibration_scope": "opponent_report",
            }
        },
    )

    assert report_calibration_applicability(round_dir) == REPORT_CALIBRATION_APPLICABILITY_NOT_APPLICABLE


def test_report_calibration_applicability_is_unbound_without_basis_or_limitation(tmp_path: Path) -> None:
    _repo, round_dir = repo_round(tmp_path)

    assert report_calibration_applicability(round_dir) == REPORT_CALIBRATION_APPLICABILITY_UNBOUND


def test_check_report_calibration_accepts_valid_not_applicable_trace(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    repo, round_dir = repo_round(tmp_path)
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, valid_not_applicable_trace(repo, round_dir))
    monkeypatch.setattr(check_report_calibration, "repo_root", lambda: repo)

    result = check_report_calibration.main(["case-a", "round-a"])

    assert result == 0
    assert "not applicable" in capsys.readouterr().out


def test_check_report_calibration_rejects_invalid_not_applicable_trace(tmp_path: Path, monkeypatch, capsys) -> None:
    repo, round_dir = repo_round(tmp_path)
    payload = valid_not_applicable_trace(repo, round_dir)
    limitation = cast(dict[str, object], payload["report_calibration_limitation"])
    limitation.pop("assessed_by")
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, payload)
    monkeypatch.setattr(check_report_calibration, "repo_root", lambda: repo)

    result = check_report_calibration.main(["case-a", "round-a"])

    assert result == 1
    assert "report_calibration_limitation: assessed_by must be one of" in capsys.readouterr().err


def test_report_calibration_not_applicable_targets_and_dependencies(tmp_path: Path) -> None:
    repo, round_dir = repo_round(tmp_path)
    write_text(round_dir / "outputs" / "oponent_posudek_navrh.md", "# Clean report\n")
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, valid_not_applicable_trace(repo, round_dir))

    assert report_calibration_check_targets(round_dir) == [
        "work/opponent_report_trace.json",
        "notes/opponent-report-operator-feedback.md",
    ]
    dependencies = dict(report_calibration_dependency_files(round_dir))

    assert dependencies["repo:profiles/default.md"] == repo / "profiles/default.md"
    assert dependencies["round:notes/opponent-report-operator-feedback.md"] == (
        round_dir / "notes/opponent-report-operator-feedback.md"
    )


def test_check_report_calibration_rejects_unbound_round(tmp_path: Path, monkeypatch, capsys) -> None:
    repo, _round_dir = repo_round(tmp_path)
    monkeypatch.setattr(check_report_calibration, "repo_root", lambda: repo)

    result = check_report_calibration.main(["case-a", "round-a"])

    assert result == 1
    assert "report calibration basis is not bound" in capsys.readouterr().err
