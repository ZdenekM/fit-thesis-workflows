import json
import zipfile
from pathlib import Path

from thesis_review_workflow.opponent_packets import PACKET_ROLES, generate_packets, render_packet
from thesis_review_workflow.report_calibration import REPORT_CALIBRATION_BASIS_REL
from thesis_review_workflow.review_materiality import MaterialityDecision, write_materiality_decisions
from thesis_review_workflow.review_packets import COMMON_BRIEFING_REL, validate_common_briefing_payload
from thesis_review_workflow.submission_bundle import (
    build_submission_bundle_inventory,
    write_submission_bundle_inventory,
)
from thesis_review_workflow.theses_checker_summary import THESES_CHECKER_SUMMARY_REL
from thesis_review_workflow.theses_similarity import THESES_SIMILARITY_REPORT_REL, THESES_SIMILARITY_REVIEW_REL


def write_assignment_coverage(round_dir: Path, *, valid: bool = True) -> None:
    path = round_dir / "work" / "assignment_coverage_agent.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not valid:
        path.write_text("{}\n", encoding="utf-8")
        return
    payload = {
        "schema_version": "assignment-coverage-agent-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-07T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "assignment-coverage-reviewer",
        "producer_agent": "agent-a",
        "authorization_note": "Current request explicitly authorized agents.",
        "source_refs": ["notes/assignment.md"],
        "assignment_points": [
            {
                "point_id": "A1",
                "summary": "Requirement.",
                "source_refs": ["notes/assignment.md"],
                "coverage": {
                    "status": "covered",
                    "evidence_refs": ["notes/assignment.md"],
                    "limitations": [],
                    "requires_reviewer_verification": False,
                },
            }
        ],
        "limitations": [],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_quantitative_claims(round_dir: Path) -> None:
    (round_dir / "extracted").mkdir(parents=True, exist_ok=True)
    (round_dir / "extracted" / "thesis.txt").write_text("Metric claim.\n", encoding="utf-8")
    payload = {
        "schema_version": "quantitative-claims-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-11T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "quantitative-claims-reviewer",
        "producer_agent": "agent-a",
        "authorization_note": "Current request explicitly authorized agents.",
        "source_refs": ["extracted/thesis.txt"],
        "claims": [
            {
                "claim_id": "Q1",
                "summary": "Reported latency lacks practical context.",
                "kind": "performance",
                "status": "needs_context",
                "unit": "ms",
                "baseline_status": "missing",
                "practical_context": "weak",
                "scale_context": "Latency scale is stated only as a single number.",
                "sample_context": "Workload size is not stated.",
                "practical_magnitude": "Magnitude is not interpreted against a baseline workload.",
                "overclaim_risk": "moderate",
                "reproducibility_refs": [],
                "evidence_refs": ["extracted/thesis.txt"],
                "requires_reviewer_verification": True,
            }
        ],
        "limitations": [],
    }
    path = round_dir / "work" / "quantitative_claims.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_report_calibration_basis(round_dir: Path) -> None:
    repo_root = round_dir.parents[3]
    profile = repo_root / "profiles" / "default.md"
    operator_note = round_dir / "notes" / "opponent-report-operator-feedback.md"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text("# Default profile\n", encoding="utf-8")
    operator_note.parent.mkdir(parents=True, exist_ok=True)
    operator_note.write_text("# Operator report calibration\n", encoding="utf-8")
    payload = {
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
        "source_refs": ["notes/opponent-report-operator-feedback.md"],
        "profile_sources": [
            {
                "path": "profiles/default.md",
                "sha256": sha256_path(profile),
                "sections_used": ["Opponent Report Style"],
            }
        ],
        "operator_calibration_sources": [
            {
                "path": "notes/opponent-report-operator-feedback.md",
                "sha256": sha256_path(operator_note),
                "purpose": "report calibration",
            }
        ],
        "related_calibration_artifacts": [],
        "applied_preferences": [
            {
                "preference_id": "opponent.assignment_difficulty.stack_not_enough",
                "source_keys": [
                    "profile:profiles/default.md",
                    "operator:notes/opponent-report-operator-feedback.md",
                ],
                "applies_to": ["assignment_difficulty"],
                "instruction": "Use the structured calibration basis.",
                "priority": "must",
                "status": "applied",
                "decision_reason": "Synthetic fixture.",
            }
        ],
        "expected_report_controls": {
            "is_select_values": {"Náročnost zadání": "průměrně obtížné zadání"},
            "overall_grade": "D",
            "overall_points_interval": [65, 74],
            "defense_question_count": {"min": 1, "max": 3},
            "public_report_length": "compact",
            "private_comment_required": True,
        },
        "limitations": [],
    }
    path = round_dir / REPORT_CALIBRATION_BASIS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_theses_checker_summary(round_dir: Path) -> None:
    source = round_dir / "notes" / "theses-checker-output.txt"
    pdf = round_dir / "inputs" / "thesis.pdf"
    source.parent.mkdir(parents=True, exist_ok=True)
    pdf.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("Normostrany: 42.5\n", encoding="utf-8")
    pdf.write_bytes(b"%PDF synthetic\n")
    payload = {
        "schema_version": "theses-checker-summary-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-20T00:00:00Z",
        "captured_at": "2026-05-20T00:00:00Z",
        "producer_type": "deterministic_helper",
        "producer_role": "record-theses-checker-summary",
        "producer_agent": "record-theses-checker-summary",
        "source_refs": ["notes/theses-checker-output.txt", "inputs/thesis.pdf"],
        "source_artifact": {
            "path": "notes/theses-checker-output.txt",
            "sha256": sha256_path(source),
            "kind": "copied_text",
        },
        "checked_pdf": {
            "path": "inputs/thesis.pdf",
            "sha256": sha256_path(pdf),
        },
        "normostrany": 42.5,
        "status": "within_required_range",
        "thresholds": {"minimum": 30, "recommended_minimum": 35},
        "checker_timestamp": None,
        "limitations": [],
    }
    path = round_dir / THESES_CHECKER_SUMMARY_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256_path(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_materiality(round_dir: Path, role: str) -> None:
    write_materiality_decisions(
        round_dir,
        [
            MaterialityDecision(
                role=role,
                recommendation="material",
                scope="explicit_request",
                impact="opponent report defensibility",
                reason="test materiality decision",
                source_refs=(f"operator-request:{role}",),
            )
        ],
        case_id="case-a",
        round_id="round-a",
        workflow_profile="opponent_review",
        phase="final",
        generated_at="2026-05-11T00:00:00Z",
    )


def test_generate_packets_writes_all_role_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "inputs").mkdir()
    (round_dir / "extracted").mkdir()
    (round_dir / "work").mkdir()
    (repo_root / "profiles").mkdir(parents=True)
    (repo_root / "profiles" / "default.md").write_text("# Default profile\n", encoding="utf-8")
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    write_assignment_coverage(round_dir)
    (round_dir / "extracted" / "thesis.txt").write_text("Synthetic thesis text.\n", encoding="utf-8")

    written = generate_packets("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)

    assert [path.name for path in written] == ["text_structure_assignment.md", "current_evidence_snapshot.md"]
    assert (round_dir / "work" / "opponent_packets" / "text_structure_assignment.md").is_file()
    text = (round_dir / "work" / "opponent_packets" / "text_structure_assignment.md").read_text(encoding="utf-8")
    assert "Schema version: `opponent-review-packet-v1`" in text
    assert "Recommended model: `gpt-5.5`" in text
    assert "Recommended reasoning: `xhigh`" in text
    assert f"Common briefing: `{COMMON_BRIEFING_REL}`" in text
    briefing = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))
    common_inputs = {item["path"]: item for item in briefing["common_inputs"]}
    profile_inputs = {item["path"]: item for item in briefing["reviewer_profile_inputs"]}
    advisory = {item["path"]: item for item in briefing["advisory_artifacts"]}
    assert common_inputs["case.md"]["status"] == "present"
    assert profile_inputs["profiles/default.md"]["status"] == "present"
    assert advisory["work/assignment_coverage_agent.json"]["status"] == "present"
    assert str(tmp_path) not in text


def test_common_briefing_surfaces_report_calibration_basis_and_sources(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "work" / "review_deltas").mkdir(parents=True)
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    (round_dir / "notes" / "random-operator-feedback.md").write_text(
        "# Not a registered report-calibration source\n",
        encoding="utf-8",
    )
    (round_dir / "work" / "review_deltas" / "report-calibration.json").write_text(
        '{"schema_version":"review-delta-v1"}\n',
        encoding="utf-8",
    )
    write_report_calibration_basis(round_dir)
    write_theses_checker_summary(round_dir)

    generate_packets("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)

    briefing = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))
    snapshot_refs = {item["path"]: item for item in briefing["snapshot_refs"]}
    calibration_sources = {item["path"]: item for item in briefing["report_calibration_sources"]}
    advisory = {item["path"]: item for item in briefing["advisory_artifacts"]}
    packet = (round_dir / "work" / "opponent_packets" / "text_structure_assignment.md").read_text(encoding="utf-8")

    assert snapshot_refs[REPORT_CALIBRATION_BASIS_REL]["status"] == "current"
    assert snapshot_refs[THESES_CHECKER_SUMMARY_REL]["status"] == "current"
    assert advisory[THESES_CHECKER_SUMMARY_REL]["status"] == "current"
    assert calibration_sources["notes/opponent-report-operator-feedback.md"]["status"] == "present"
    assert calibration_sources["notes/opponent-report-review-intake.md"]["status"] == "missing"
    assert calibration_sources["work/operation_log.jsonl"]["status"] == "missing"
    assert calibration_sources["work/opponent_report_revision_request.json"]["status"] == "missing"
    assert calibration_sources["work/review_deltas/report-calibration.json"]["status"] == "present"
    assert "notes/random-operator-feedback.md" not in calibration_sources
    assert "## Report Calibration Basis" in packet
    assert "Start from `work/report_calibration_basis.json` when present" in packet
    assert "Do not infer reviewer preferences from free-form profile, note, or report prose" in packet
    assert "Theses Checker summary" in packet
    assert "not new packet roles" in packet

    briefing["report_calibration_sources"].append({"path": "notes/random-operator-feedback.md", "status": "missing"})
    errors = validate_common_briefing_payload(
        briefing,
        COMMON_BRIEFING_REL,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )
    assert any("path is not a registered report calibration source" in error for error in errors)


def test_common_briefing_marks_wrong_profile_report_calibration_basis_invalid(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: local/other\n", encoding="utf-8")
    (repo_root / "profiles" / "local").mkdir(parents=True)
    (repo_root / "profiles" / "local" / "other.md").write_text("# Other profile\n", encoding="utf-8")
    write_report_calibration_basis(round_dir)

    generate_packets("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)

    briefing = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))
    snapshot_refs = {item["path"]: item for item in briefing["snapshot_refs"]}
    packet = (round_dir / "work" / "opponent_packets" / "text_structure_assignment.md").read_text(encoding="utf-8")

    assert snapshot_refs[REPORT_CALIBRATION_BASIS_REL]["status"] == "invalid"
    assert f"`{REPORT_CALIBRATION_BASIS_REL}` (invalid" in packet


def test_common_briefing_marks_invalid_theses_checker_summary_invalid(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    write_theses_checker_summary(round_dir)
    (round_dir / THESES_CHECKER_SUMMARY_REL).write_text('{"schema_version": "wrong"}\n', encoding="utf-8")

    generate_packets("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)

    briefing = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))
    snapshot_refs = {item["path"]: item for item in briefing["snapshot_refs"]}
    advisory = {item["path"]: item for item in briefing["advisory_artifacts"]}

    assert snapshot_refs[THESES_CHECKER_SUMMARY_REL]["status"] == "invalid"
    assert advisory[THESES_CHECKER_SUMMARY_REL]["status"] == "invalid"


def test_generate_packets_emits_code_and_structured_optional_packets_only_when_triggered(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "work").mkdir(parents=True)
    (round_dir / "work" / "code_workspace.md").write_text("Prepared code root.\n", encoding="utf-8")
    (round_dir / "work" / "figure_media").mkdir(parents=True)
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (round_dir / "work" / "figure_media" / "visual_inventory.jsonl").write_text("{}\n", encoding="utf-8")
    write_materiality(round_dir, "figure_media")
    (round_dir / "outputs").mkdir()
    (round_dir / "outputs" / "literature_citation_review.md").write_text("# Literature\n", encoding="utf-8")

    written = generate_packets("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    names = {path.name for path in written}

    assert "code_consistency.md" in names
    assert "code_quality.md" in names
    assert "figure_media.md" in names
    assert "literature_citation.md" not in names
    assert "typography_formal.md" not in names

    code_quality = (round_dir / "work" / "opponent_packets" / "code_quality.md").read_text(encoding="utf-8")
    assert "## Omen Advisory Static Analysis" in code_quality
    assert "not an operator prerequisite" in code_quality


def test_code_packets_require_prepared_code_workspace_not_raw_archive(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "inputs").mkdir(parents=True)
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (round_dir / "inputs" / "thesis-source.zip").write_text("not necessarily submitted code\n", encoding="utf-8")

    written = generate_packets("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    names = {path.name for path in written}

    assert "code_consistency.md" not in names
    assert "code_quality.md" not in names


def test_code_reproducibility_artifact_alone_does_not_activate_code_packets(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "work").mkdir(parents=True)
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (round_dir / "work" / "code_reproducibility.json").write_text(
        '{"classification": "no_code_evidence"}\n',
        encoding="utf-8",
    )

    written = generate_packets("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    names = {path.name for path in written}

    assert "code_consistency.md" not in names
    assert "code_quality.md" not in names


def test_inactive_optional_packets_are_pruned(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    materiality = round_dir / "work" / "review_materiality" / "opponent_review" / "figure_media.json"
    write_materiality(round_dir, "figure_media")

    generate_packets("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    assert (round_dir / "work" / "opponent_packets" / "figure_media.md").is_file()

    materiality.unlink()
    generate_packets("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)

    assert not (round_dir / "work" / "opponent_packets" / "figure_media.md").exists()


def test_optional_materiality_paths_are_role_specific(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    write_materiality(round_dir, "typography_formal")

    written = generate_packets("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    names = {path.name for path in written}

    assert "typography_formal.md" in names
    assert "literature_citation.md" not in names


def test_opponent_packet_renders_materiality_next_actions(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "inputs").mkdir()
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (round_dir / "inputs" / "results.csv").write_text("metric,value\nlatency,42\n", encoding="utf-8")
    write_materiality_decisions(
        round_dir,
        [
            MaterialityDecision(
                role="quantitative_claims",
                recommendation="material",
                scope="explicit_request",
                impact="opponent report defensibility",
                reason="test materiality decision",
                source_refs=("inputs/results.csv",),
            )
        ],
        case_id="case-a",
        round_id="round-a",
        workflow_profile="opponent_review",
        phase="final",
        generated_at="2026-05-11T00:00:00Z",
    )
    role = next(item for item in PACKET_ROLES if item.key == "text_structure_assignment")

    text = render_packet("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir, role)

    assert "## Materiality Next Actions" in text
    assert "`quantitative_claims` [missing_artifact] requires `work/quantitative_claims.json`" in text

    written = generate_packets("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    assert "quantitative_claims.md" in {path.name for path in written}


def test_opponent_packets_emit_theses_similarity_packet_from_next_action(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    report = round_dir / THESES_SIMILARITY_REPORT_REL
    report.parent.mkdir(parents=True)
    report.write_bytes(b"%PDF synthetic\n")
    write_materiality(round_dir, "theses_similarity")

    written = generate_packets("case-a", "round-a", "2026-05-12T00:00:00Z", round_dir)
    names = {path.name for path in written}
    text = (round_dir / "work" / "opponent_packets" / "theses_similarity.md").read_text(encoding="utf-8")

    assert "theses_similarity.md" in names
    assert f"`theses_similarity` [missing_artifact] requires `{THESES_SIMILARITY_REVIEW_REL}`" in text
    assert THESES_SIMILARITY_REPORT_REL in text
    assert "Do not leak raw report URLs" in text


def test_opponent_packet_consumes_quantitative_claims_handoff(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    write_quantitative_claims(round_dir)

    written = generate_packets("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    names = {path.name for path in written}
    text = (round_dir / "work" / "opponent_packets" / "synthesis.md").read_text(encoding="utf-8")
    briefing = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))

    assert "quantitative_claims.md" in names
    assert "## Reusable Handoff Refs" in text
    assert "`work/quantitative_claims.json` (present" in text
    advisory = {item["path"]: item for item in briefing["advisory_artifacts"]}
    assert advisory["work/quantitative_claims.json"]["status"] == "present"


def test_packet_marks_invalid_structured_artifact_as_limitation(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "work").mkdir()
    (repo_root / "profiles").mkdir(parents=True)
    (repo_root / "profiles" / "default.md").write_text("# Default profile\n", encoding="utf-8")
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    write_assignment_coverage(round_dir, valid=False)
    role = next(item for item in PACKET_ROLES if item.key == "text_structure_assignment")

    text = render_packet("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir, role)

    assert "`work/assignment_coverage_agent.json` (invalid)" in text
    assert "## Missing Role Inputs To Treat As Limitations" in text
    assert "`work/assignment_coverage_agent.json`" in text.split("## Missing Role Inputs To Treat As Limitations", 1)[1]


def test_packet_marks_missing_role_inputs_as_limitations(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    role = next(item for item in PACKET_ROLES if item.key == "code_consistency")

    text = render_packet("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir, role)

    assert "## Missing Role Inputs To Treat As Limitations" in text
    assert "`work/code_workspace.md`" in text
    assert "Do not run submitted code unless the operator explicitly authorized that run." in text


def test_packet_includes_synthesis_review_contract(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    role = next(item for item in PACKET_ROLES if item.key == "synthesis")

    text = render_packet("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir, role)

    assert "Run an independent thesis-opponent-materials-review pass" in text
    assert "work/oponent_podklady_draft.md" in text
    assert "Recommended model: `gpt-5.5`" in text


def test_report_review_packet_starts_from_trace_controls_and_synthesis_handoffs(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    role = next(item for item in PACKET_ROLES if item.key == "report_review")

    text = render_packet("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir, role)

    assert "trace report-quality controls" in text
    assert "`## Synthesis Handoff`" in text
    assert THESES_CHECKER_SUMMARY_REL in text


def test_packet_lists_input_directories(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "inputs" / "submitted-src").mkdir(parents=True)

    generate_packets("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    briefing = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))

    assert "inputs/submitted-src/" in briefing["available_round_inputs"]


def test_packets_surface_submission_bundle_visibility_before_raw_archives(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "inputs").mkdir(parents=True)
    with zipfile.ZipFile(round_dir / "inputs" / "submission.zip", "w") as handle:
        handle.writestr("handoff/src/app.py", "print('synthetic')\n")
        handle.writestr("handoff/demo.mp4", b"mp4")
        handle.writestr("handoff/app.apk", b"apk")
    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/submission.zip"],
        producer="scripts/review-round-start",
        generated_at="2026-05-19T12:00:00Z",
    )
    write_submission_bundle_inventory(round_dir=round_dir, payload=payload)

    generate_packets("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)

    briefing = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))
    visibility = "\n".join(briefing["submission_bundle_visibility"])
    text = (round_dir / "work" / "opponent_packets" / "text_structure_assignment.md").read_text(encoding="utf-8")

    assert "Submission Bundle Inventory" in text
    assert "Use this inventory before opening raw submitted bundles" in text
    assert "First-party-looking code:" in visibility
    assert "Demo/media/executables:" in visibility
    assert "media_artifact" in visibility
    assert "executable_artifact" in visibility


def test_packets_use_role_owned_expected_outputs() -> None:
    vague = [
        role
        for role in PACKET_ROLES
        if role.expected_output.startswith("findings for") or " or " in role.expected_output
    ]

    assert vague == []


def test_check_activated_roles_use_shape_gates() -> None:
    checks = {role.key: role.activation_check for role in PACKET_ROLES if role.activation == "check"}

    assert checks["materials_review"] == (
        "check-review-wave",
        "--workflow",
        "opponent_materials",
        "--wave",
        "draft",
    )
    assert checks["report_trace"] == (
        "check-review-wave",
        "--workflow",
        "opponent_materials",
        "--wave",
        "reviewed",
    )
    assert checks["report_review"] == (
        "check-review-wave",
        "--workflow",
        "opponent_report",
        "--wave",
        "draft",
    )
