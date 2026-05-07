import json
from pathlib import Path

from thesis_review_workflow.opponent_packets import PACKET_ROLES, generate_packets, render_packet


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

    assert len(written) == len(PACKET_ROLES)
    assert (round_dir / "work" / "opponent_packets" / "text_structure_assignment.md").is_file()
    text = (round_dir / "work" / "opponent_packets" / "text_structure_assignment.md").read_text(encoding="utf-8")
    assert "Schema version: `opponent-review-packet-v1`" in text
    assert "`case.md` (present)" in text
    assert "`profiles/default.md` (present)" in text
    assert "`work/assignment_coverage_agent.json` (present)" in text
    assert str(tmp_path) not in text


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


def test_packet_lists_input_directories(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "inputs" / "submitted-src").mkdir(parents=True)
    role = next(item for item in PACKET_ROLES if item.key == "code_quality")

    text = render_packet("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir, role)

    assert "`inputs/submitted-src/`" in text


def test_packets_use_role_owned_expected_outputs() -> None:
    vague = [
        role
        for role in PACKET_ROLES
        if role.expected_output.startswith("findings for") or " or " in role.expected_output
    ]

    assert vague == []
