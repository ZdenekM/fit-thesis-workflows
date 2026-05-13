import json
from pathlib import Path

from thesis_review_workflow.context_budget import (
    SCHEMA_VERSION,
    build_context_budget_report,
    estimate_tokens,
    render_context_budget_report,
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_context_budget_counts_managed_and_raw_surfaces(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    write(round_dir / "work" / "common_briefing.json", "{}\n")
    write(round_dir / "work" / "supervisor_packets" / "text_assignment.md", "# Packet\n")
    write(round_dir / "work" / "context" / "evidence_capsules.json", '{"capsules": []}\n')
    write(round_dir / "work" / "context" / "claim_review_basis.json", '{"claims": []}\n')
    write(round_dir / "work" / "reuse" / "reuse_index.json", '{"decisions": []}\n')
    write(round_dir / "extracted" / "thesis.txt", "raw thesis text\n")

    report = build_context_budget_report("case-a", "round-a", round_dir)
    surfaces = {surface["name"]: surface for surface in report["surfaces"]}

    assert report["schema_version"] == SCHEMA_VERSION
    assert report["advisory"] is True
    assert surfaces["common_briefing"]["file_count"] == 1
    assert surfaces["role_packets"]["file_count"] == 1
    assert surfaces["evidence_capsules"]["estimated_tokens"] == estimate_tokens(len('{"capsules": []}\n'))
    assert surfaces["raw_sources"]["file_count"] == 1
    assert report["totals"]["managed_context_estimated_tokens"] > 0
    json.dumps(report)


def test_context_budget_warns_on_large_role_packet_and_raw_ratio(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    write(round_dir / "work" / "common_briefing.json", "{}\n")
    write(round_dir / "work" / "supervisor_packets" / "code_quality.md", "x" * 120)
    write(round_dir / "inputs" / "thesis.pdf", "p" * 120)

    report = build_context_budget_report(
        "case-a",
        "round-a",
        round_dir,
        max_role_packet_tokens=10,
        raw_transfer_ratio=0.1,
    )
    codes = {warning["code"] for warning in report["warnings"]}

    assert "large_role_packet" in codes
    assert "managed_context_near_raw_source_size" in codes


def test_context_budget_warns_when_raw_sources_have_no_structured_handoffs(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    write(round_dir / "inputs" / "thesis.pdf", "raw")

    report = build_context_budget_report("case-a", "round-a", round_dir)
    codes = {warning["code"] for warning in report["warnings"]}

    assert "missing_common_briefing" in codes
    assert "missing_role_packets" in codes
    assert "missing_structured_handoffs" in codes


def test_render_context_budget_report_is_advisory_and_omits_raw_content(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    write(round_dir / "inputs" / "thesis.pdf", "secret raw content")

    text = render_context_budget_report(build_context_budget_report("case-a", "round-a", round_dir))

    assert "# Context Budget Audit" in text
    assert "Mode: advisory" in text
    assert "secret raw content" not in text
    assert "`inputs/thesis.pdf`" in text
