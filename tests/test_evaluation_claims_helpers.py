import json
from pathlib import Path

from thesis_review_workflow.cli import check_evaluation_claims


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def make_round(root: Path) -> Path:
    case_dir = root / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    (round_dir / "extracted").mkdir(parents=True)
    (round_dir / "work").mkdir()
    (case_dir / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (case_dir / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    (round_dir / "extracted" / "thesis.txt").write_text("Reported metric claim.\n", encoding="utf-8")
    return round_dir


def quantitative_claims(case_id: str = "case-a") -> dict[str, object]:
    return {
        "schema_version": "quantitative-claims-v1",
        "case_id": case_id,
        "round_id": "round-a",
        "generated_at": "2026-05-07T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "quantitative-claims-reviewer",
        "producer_agent": "agent-a",
        "authorization_note": "Current request explicitly authorized agents.",
        "source_refs": ["extracted/thesis.txt"],
        "claims": [
            {
                "claim_id": "Q1",
                "summary": "Reported metric needs context.",
                "kind": "metric",
                "status": "needs_context",
                "unit": "%",
                "baseline_status": "missing",
                "practical_context": "weak",
                "scale_context": "Percentage denominator is not explicit.",
                "sample_context": "Sample size is not stated.",
                "practical_magnitude": "Magnitude is not interpreted against a user-visible impact.",
                "overclaim_risk": "moderate",
                "reproducibility_refs": [],
                "evidence_refs": ["extracted/thesis.txt"],
                "requires_reviewer_verification": True,
            },
            {
                "claim_id": "Q2",
                "summary": "Experiment result is not verifiable.",
                "kind": "experiment",
                "status": "not_verifiable",
                "unit": "not_verifiable",
                "baseline_status": "not_verifiable",
                "practical_context": "not_verifiable",
                "scale_context": "No scale context is verifiable from the available evidence.",
                "sample_context": "No sample context is verifiable from the available evidence.",
                "practical_magnitude": "No practical magnitude is verifiable from the available evidence.",
                "overclaim_risk": "not_verifiable",
                "reproducibility_refs": [],
                "evidence_refs": ["extracted/thesis.txt"],
                "requires_reviewer_verification": True,
            },
        ],
        "limitations": [],
    }


def test_check_evaluation_claims_validates_structured_artifact(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    write_json(round_dir / "work" / "quantitative_claims.json", quantitative_claims())
    monkeypatch.setattr(check_evaluation_claims, "repo_root", lambda: root)

    assert check_evaluation_claims.main(["scripts/check-evaluation-claims", "case-a"]) == 0

    output = capsys.readouterr().out
    assert "Quantitative claims artifact: cases/case-a/rounds/round-a/work/quantitative_claims.json" in output
    assert "Quantitative claims: 2" in output
    assert "Claim kinds: experiment=1, metric=1" in output
    assert "Claim statuses: needs_context=1, not_verifiable=1" in output
    assert "Baseline statuses: missing=1, not_verifiable=1" in output
    assert "Practical-context statuses: not_verifiable=1, weak=1" in output
    assert "Overclaim-risk statuses: moderate=1, not_verifiable=1" in output
    assert "Synthesis attention claims: 2" in output
    assert "Synthesis handoff: consume the structured claim summaries" in output
    assert "Quantitative claims structured artifact check passed" in output


def test_check_evaluation_claims_requires_structured_artifact(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    make_round(root)
    monkeypatch.setattr(check_evaluation_claims, "repo_root", lambda: root)

    assert check_evaluation_claims.main(["scripts/check-evaluation-claims", "case-a"]) == 1

    output = capsys.readouterr().out
    assert "missing structured evidence artifact" in output
    assert "Create `work/quantitative_claims.json`" in output


def test_check_evaluation_claims_rejects_invalid_enum(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    payload = quantitative_claims()
    claims = payload["claims"]
    assert isinstance(claims, list)
    claims[0]["status"] = "strong"
    write_json(round_dir / "work" / "quantitative_claims.json", payload)
    monkeypatch.setattr(check_evaluation_claims, "repo_root", lambda: root)

    assert check_evaluation_claims.main(["scripts/check-evaluation-claims", "case-a"]) == 1

    output = capsys.readouterr().out
    assert "status must be one of" in output


def test_check_evaluation_claims_rejects_stale_case(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    write_json(round_dir / "work" / "quantitative_claims.json", quantitative_claims(case_id="other-case"))
    monkeypatch.setattr(check_evaluation_claims, "repo_root", lambda: root)

    assert check_evaluation_claims.main(["scripts/check-evaluation-claims", "case-a"]) == 1

    output = capsys.readouterr().out
    assert "case_id does not match requested case" in output
