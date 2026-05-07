import hashlib
import json
from pathlib import Path

from thesis_review_workflow.cli.check_opponent_calibration_profile import profile_binding_errors
from thesis_review_workflow.opponent_calibration import validate_opponent_calibration_artifact
from thesis_review_workflow.work_artifacts import collect_supporting_work_artifacts, validate_supporting_work_artifacts


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def common_fields(schema_version: str) -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "reviewer_profile_id": "zm-calibration",
        "case_id": "calibration-case",
        "round_id": "round-a",
        "generated_at": "2026-05-07T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "opponent-calibration-reviewer",
        "producer_agent": "agent-a",
        "authorization_note": "Current request explicitly authorized agents.",
        "source_refs": ["inputs/historical_cases/case-001/opponent_report.md"],
        "limitations": [],
    }


def create_calibration_refs(round_dir: Path) -> None:
    for rel in (
        "inputs/historical_cases/case-001/opponent_report.md",
        "inputs/historical_cases/case-001/assignment.md",
        "inputs/historical_cases/case-002/opponent_report.md",
        "outputs/reviewer_calibration_profile.md",
    ):
        path = round_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic fixture\n", encoding="utf-8")


def historical_case_payload() -> dict[str, object]:
    return {
        **common_fields("historical-opponent-case-analysis-v1"),
        "historical_case_id": "case-001",
        "work_type": "diploma thesis",
        "domain": "synthetic software engineering",
        "case_strength": "typical",
        "artifact_availability": {"assignment": "present", "thesis": "present", "report": "present"},
        "code_availability": {"submitted_code": "present"},
        "report_shape": {"length_class": "medium"},
        "judgment_calibration": {"strictness": "medium"},
        "evidence_habits": {"relied_on": ["assignment", "thesis", "code"]},
        "corpus_coverage": {"work_type": "diploma thesis", "domain": "synthetic"},
        "recurring_checks": [
            {
                "check_id": "assignment-map",
                "evidence_class": "assignment_fulfillment",
                "prompt": "Map submitted work to assignment points.",
            }
        ],
    }


def historical_case_payload_for(historical_case_id: str) -> dict[str, object]:
    payload = historical_case_payload()
    payload["historical_case_id"] = historical_case_id
    payload["source_refs"] = [f"inputs/historical_cases/{historical_case_id}/opponent_report.md"]
    return payload


def confidence_by_dimension() -> dict[str, dict[str, str]]:
    return {
        "style": {"level": "medium", "rationale": "Two synthetic reports."},
        "grading": {"level": "low", "rationale": "Small corpus."},
        "severity": {"level": "medium", "rationale": "Repeated categories."},
        "questions": {"level": "medium", "rationale": "Stable question pattern."},
        "evidence_expectations": {"level": "medium", "rationale": "Repeated evidence demands."},
        "checklist_coverage": {"level": "medium", "rationale": "Several recurring checks."},
    }


def test_validate_historical_case_analysis_accepts_path_classified_payload(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", historical_case_payload())

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/calibration/historical_case_analyses/case-001.json",
        case_id="calibration-case",
        round_id="round-a",
    )

    assert errors == []


def test_validate_historical_case_analysis_rejects_filename_mismatch(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-002.json", historical_case_payload())

    errors = validate_opponent_calibration_artifact(
        round_dir, "work/calibration/historical_case_analyses/case-002.json"
    )

    assert any("historical_case_id must match the analysis filename" in error for error in errors)


def test_validate_historical_case_analysis_requires_matching_source_anchor(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    other_ref = round_dir / "inputs/historical_cases/case-002/opponent_report.md"
    other_ref.parent.mkdir(parents=True, exist_ok=True)
    other_ref.write_text("other synthetic fixture\n", encoding="utf-8")
    payload = {
        **historical_case_payload(),
        "source_refs": ["inputs/historical_cases/case-002/opponent_report.md"],
    }
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/calibration/historical_case_analyses/case-001.json",
    )

    assert any("source_refs must not point to a different historical case id" in error for error in errors)
    assert any(
        "source_refs must include at least one ref under inputs/historical_cases/case-001/" in error for error in errors
    )


def test_validate_historical_case_analysis_requires_source_refs(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    payload = {
        **historical_case_payload(),
        "source_refs": [],
    }
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/calibration/historical_case_analyses/case-001.json",
    )

    assert any("source_refs must not be empty" in error for error in errors)


def test_validate_profile_manifest_binds_markdown_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    analysis_path = round_dir / "work/calibration/historical_case_analyses/case-001.json"
    write_json(analysis_path, historical_case_payload())
    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    payload = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": sha256_file(profile_path),
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "profile_version": 1,
        "profile_previous_sha256": None,
        "profile_change_summary": "Initial synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    write_json(round_dir / "work/calibration/reviewer_calibration_profile.json", payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/calibration/reviewer_calibration_profile.json",
        case_id="calibration-case",
        round_id="round-a",
    )

    assert errors == []

    profile_path.write_text("changed\n", encoding="utf-8")
    stale_errors = validate_opponent_calibration_artifact(
        round_dir, "work/calibration/reviewer_calibration_profile.json"
    )
    assert any("profile_markdown_sha256 is stale" in error for error in stale_errors)


def test_validate_profile_manifest_reports_non_string_hash_without_crashing(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", historical_case_payload())
    payload = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": 123,
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "profile_version": 1,
        "profile_previous_sha256": None,
        "profile_change_summary": "Initial synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    write_json(round_dir / "work/calibration/reviewer_calibration_profile.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/calibration/reviewer_calibration_profile.json")

    assert any("profile_markdown_sha256 must be a 64-character hex string" in error for error in errors)


def test_validate_profile_manifest_rejects_wrong_markdown_path(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", historical_case_payload())
    wrong_profile = round_dir / "outputs/other_profile.md"
    wrong_profile.write_text("synthetic wrong profile\n", encoding="utf-8")
    payload = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "profile_markdown_path": "outputs/other_profile.md",
        "profile_markdown_sha256": sha256_file(wrong_profile),
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "profile_version": 1,
        "profile_previous_sha256": None,
        "profile_change_summary": "Initial synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    write_json(round_dir / "work/calibration/reviewer_calibration_profile.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/calibration/reviewer_calibration_profile.json")

    assert any("profile_markdown_path must be outputs/reviewer_calibration_profile.md" in error for error in errors)


def test_validate_profile_manifest_requires_existing_historical_case_refs(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    payload = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": ["inputs/historical_cases/case-001/opponent_report.md"],
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": sha256_file(profile_path),
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": ["work/calibration/historical_case_analyses/missing.json"],
        "profile_version": 1,
        "profile_previous_sha256": None,
        "profile_change_summary": "Initial synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    write_json(round_dir / "work/calibration/reviewer_calibration_profile.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/calibration/reviewer_calibration_profile.json")

    assert any(
        "ref does not exist: work/calibration/historical_case_analyses/missing.json" in error for error in errors
    )


def test_validate_reviewer_checklist_requires_evidence_class_entries(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", historical_case_payload())
    payload = {
        **common_fields("opponent-reviewer-checklist-v1"),
        "checklist_items": [
            {
                "item_id": "assignment-map",
                "evidence_class": "assignment_fulfillment",
                "prompt": "Map submitted work to assignment points.",
                "source_case_refs": ["work/calibration/historical_case_analyses/case-001.json"],
                "requires_current_case_evidence": True,
            }
        ],
    }
    write_json(round_dir / "work/calibration/reviewer_checklist.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/calibration/reviewer_checklist.json")

    assert errors == []


def test_validate_reviewer_checklist_rejects_unsafe_source_case_refs(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    payload = {
        **common_fields("opponent-reviewer-checklist-v1"),
        "checklist_items": [
            {
                "item_id": "assignment-map",
                "evidence_class": "assignment_fulfillment",
                "prompt": "Map submitted work to assignment points.",
                "source_case_refs": ["/tmp/private-case.json"],
                "requires_current_case_evidence": True,
            }
        ],
    }
    write_json(round_dir / "work/calibration/reviewer_checklist.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/calibration/reviewer_checklist.json")

    assert any("ref must be relative inside the round" in error for error in errors)


def test_validate_profile_history_jsonl(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    analysis_path = round_dir / "work/calibration/historical_case_analyses/case-001.json"
    write_json(analysis_path, historical_case_payload())
    entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "schema_version": "opponent-reviewer-calibration-history-v1",
        "profile_version": 1,
        "previous_profile_markdown_sha256": None,
        "profile_markdown_sha256": "a" * 64,
        "profile_manifest_sha256": "b" * 64,
        "source_case_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "review_status": "accepted",
        "change_summary": "Initial synthetic profile.",
    }
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/calibration/reviewer_calibration_profile_history.jsonl",
        case_id="calibration-case",
        round_id="round-a",
    )

    assert errors == []


def test_validate_profile_history_requires_common_metadata(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", historical_case_payload())
    entry = {
        "schema_version": "opponent-reviewer-calibration-history-v1",
        "profile_version": 1,
        "previous_profile_markdown_sha256": None,
        "profile_markdown_sha256": "a" * 64,
        "profile_manifest_sha256": "b" * 64,
        "source_case_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "review_status": "accepted",
        "change_summary": "Initial synthetic profile.",
    }
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/calibration/reviewer_calibration_profile_history.jsonl",
        case_id="calibration-case",
        round_id="round-a",
    )

    assert any("case_id does not match requested case" in error for error in errors)
    assert any("producer_role must be non-empty str" in error for error in errors)
    assert any("producer_type must be agent or human" in error for error in errors)


def test_validate_history_rejects_empty_source_case_refs(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "profile_version": 1,
        "previous_profile_markdown_sha256": None,
        "profile_markdown_sha256": "a" * 64,
        "profile_manifest_sha256": "b" * 64,
        "source_case_refs": [],
        "review_status": "accepted",
        "change_summary": "Initial synthetic profile.",
    }
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    errors = validate_opponent_calibration_artifact(
        round_dir, "work/calibration/reviewer_calibration_profile_history.jsonl"
    )

    assert any("source_case_refs must not be empty" in error for error in errors)


def test_profile_binding_requires_two_used_historical_analyses(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    analysis_refs = [
        "work/calibration/historical_case_analyses/case-001.json",
        "work/calibration/historical_case_analyses/case-002.json",
    ]
    for rel_path in analysis_refs:
        case_id = rel_path.rsplit("/", maxsplit=1)[1].removesuffix(".json")
        write_json(round_dir / rel_path, historical_case_payload_for(case_id))
    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    profile = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": analysis_refs[:1],
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": sha256_file(profile_path),
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": analysis_refs[:1],
        "profile_version": 1,
        "profile_previous_sha256": None,
        "profile_change_summary": "Initial synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    profile_manifest = round_dir / "work/calibration/reviewer_calibration_profile.json"
    write_json(profile_manifest, profile)
    history = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": analysis_refs[:1],
        "profile_version": 1,
        "previous_profile_markdown_sha256": None,
        "profile_markdown_sha256": sha256_file(profile_path),
        "profile_manifest_sha256": sha256_file(profile_manifest),
        "source_case_refs": analysis_refs[:1],
        "review_status": "reviewed",
        "change_summary": "Initial synthetic profile.",
    }
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.write_text(json.dumps(history) + "\n", encoding="utf-8")

    errors = profile_binding_errors(round_dir, profile, analysis_refs)

    assert any(
        "source_case_refs: must reference at least two distinct historical case analyses" in error for error in errors
    )


def test_profile_binding_rejects_stale_latest_history(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    analysis_refs = [
        "work/calibration/historical_case_analyses/case-001.json",
        "work/calibration/historical_case_analyses/case-002.json",
    ]
    for rel_path in analysis_refs:
        case_id = rel_path.rsplit("/", maxsplit=1)[1].removesuffix(".json")
        write_json(round_dir / rel_path, historical_case_payload_for(case_id))
    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    profile = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": analysis_refs,
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": sha256_file(profile_path),
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": analysis_refs,
        "profile_version": 2,
        "profile_previous_sha256": "a" * 64,
        "profile_change_summary": "Second synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    profile_manifest = round_dir / "work/calibration/reviewer_calibration_profile.json"
    write_json(profile_manifest, profile)
    history_entries = [
        {
            **common_fields("opponent-reviewer-calibration-history-v1"),
            "source_refs": analysis_refs,
            "profile_version": 2,
            "previous_profile_markdown_sha256": "a" * 64,
            "profile_markdown_sha256": "b" * 64,
            "profile_manifest_sha256": "c" * 64,
            "source_case_refs": analysis_refs,
            "review_status": "reviewed",
            "change_summary": "Second synthetic profile.",
        },
        {
            **common_fields("opponent-reviewer-calibration-history-v1"),
            "source_refs": analysis_refs,
            "profile_version": 1,
            "previous_profile_markdown_sha256": None,
            "profile_markdown_sha256": "d" * 64,
            "profile_manifest_sha256": "e" * 64,
            "source_case_refs": analysis_refs,
            "review_status": "reviewed",
            "change_summary": "Out-of-order stale entry.",
        },
    ]
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.write_text("\n".join(json.dumps(entry) for entry in history_entries) + "\n", encoding="utf-8")

    errors = profile_binding_errors(round_dir, profile, analysis_refs)

    assert any("profile_version entries must be strictly increasing" in error for error in errors)
    assert any("latest profile_version does not match profile manifest" in error for error in errors)
    assert any("latest profile_markdown_sha256 is stale" in error for error in errors)
    assert any("latest profile_manifest_sha256 is stale" in error for error in errors)


def test_validate_historical_case_analysis_rejects_dot_only_stem(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"

    errors = validate_opponent_calibration_artifact(round_dir, "work/calibration/historical_case_analyses/...json")

    assert errors == ["work/calibration/historical_case_analyses/...json: unknown opponent calibration artifact path"]


def test_work_artifacts_collects_and_validates_calibration_artifacts(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", historical_case_payload())

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert (
        by_path["work/calibration/historical_case_analyses/case-001.json"]["schema_version"]
        == "historical-opponent-case-analysis-v1"
    )
    assert validate_supporting_work_artifacts(records, round_dir, case_id="calibration-case", round_id="round-a") == []
