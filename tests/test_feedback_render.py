from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from thesis_review_workflow import feedback_render, pdf_render
from thesis_review_workflow.cli import render_feedback
from thesis_review_workflow.cli.check_feedback_output import LANGUAGE
from thesis_review_workflow.operation_log import OPERATION_LOG_REL
from thesis_review_workflow.review_approvals import build_review_approval_payload, sha256_file
from thesis_review_workflow.review_manifest import MANIFEST_REL

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL = REPO_ROOT / ".agents/skills/thesis-supervisor-feedback/SKILL.md"
PROFILE = feedback_render.APPROVAL_PROFILE
BASIS_REL = PROFILE.review_basis_candidates[0]

CASE_MD = """# Case

Student: Test Student
Topic: Synthetic topic
Student feedback language: {language}
"""


def make_round(tmp_path: Path, *, language: str = "cs") -> Path:
    case_dir = tmp_path / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    (round_dir / "outputs").mkdir(parents=True)
    (round_dir / "work").mkdir()
    (case_dir / "case.md").write_text(CASE_MD.format(language=language), encoding="utf-8")
    (case_dir / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    (round_dir / feedback_render.FEEDBACK_REL).write_text("# Feedback\n", encoding="utf-8")
    (round_dir / BASIS_REL).write_text("# Draft\n", encoding="utf-8")
    return round_dir


def write_manifest(round_dir: Path) -> dict[str, object]:
    reviewed = round_dir / PROFILE.reviewed_artifact_path
    manifest: dict[str, object] = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "artifacts": [],
        "helper_checks": [
            {
                "check": name,
                "status": "passed",
                "exit_code": 0,
                "checked_at": "2026-10-06T00:00:00Z",
                "target_artifacts": [PROFILE.reviewed_artifact_path],
                "target_sha256": {PROFILE.reviewed_artifact_path: sha256_file(reviewed)},
            }
            for name in PROFILE.required_checks
        ],
    }
    path = round_dir / MANIFEST_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def write_approval(round_dir: Path, **overrides: object) -> Path:
    manifest = write_manifest(round_dir)
    payload = build_review_approval_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile=PROFILE.workflow_profile,
        reviewer_role=PROFILE.reviewer_role,
        reviewer_agent="reviewer-agent",
        verdict="approved",
        blocking_findings_count=0,
        reviewed_artifact_path=PROFILE.reviewed_artifact_path,
        review_basis_path=BASIS_REL,
        checks_observed=list(PROFILE.required_checks),
        limitations=[],
        timestamp="2026-10-06T00:00:00Z",
        manifest=manifest,
        required_checks=PROFILE.required_checks,
        approval_path=PROFILE.approval_path,
    )
    payload.update(overrides)
    path = round_dir / PROFILE.approval_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_case_metadata_reads_student_topic_and_language(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path, language="EN")

    metadata = feedback_render.read_case_metadata(round_dir.parents[1] / "case.md")

    assert metadata == feedback_render.FeedbackCaseMetadata(
        language="en", student="Test Student", topic="Synthetic topic"
    )


def test_case_metadata_defaults_to_czech_and_rejects_unknown_language(tmp_path: Path) -> None:
    case_md = tmp_path / "case.md"
    case_md.write_text("Student: X\n", encoding="utf-8")
    assert feedback_render.read_case_metadata(case_md).language == "cs"

    case_md.write_text("Student feedback language: de\n", encoding="utf-8")
    with pytest.raises(feedback_render.RenderError, match="unsupported Student feedback language: de"):
        feedback_render.read_case_metadata(case_md)


@pytest.mark.parametrize("language", ["cs", "en"])
def test_render_metadata_carries_draft_stamp_only_for_drafts(language: str) -> None:
    case = feedback_render.FeedbackCaseMetadata(language=language, student="S", topic="T")

    final = feedback_render.render_metadata(case, draft=False)
    draft = feedback_render.render_metadata(case, draft=True)

    assert final["lang"] == language
    assert "draft" not in final["masthead"]
    assert final["masthead"]["kind"] == feedback_render.KIND[language]
    assert final["sections"]["area_header"] == feedback_render.AREA_HEADER[language]
    assert draft["masthead"]["draft"] == pdf_render.DRAFT_STAMP[language]
    assert final["sections"]["date_label"] == LANGUAGE[language]["date_label"]


@pytest.mark.parametrize("language", ["cs", "en"])
def test_mapped_headings_exist_in_the_skill_output_contract(language: str) -> None:
    skill_text = SKILL.read_text(encoding="utf-8")
    sections = feedback_render.render_metadata(
        feedback_render.FeedbackCaseMetadata(language=language, student="", topic=""), draft=False
    )["sections"]

    headings = [sections["scope"], sections["priority"], *sections["tips"]]
    for heading in headings:
        assert f"\n## {heading}\n" in skill_text, heading
    assert f"\n{sections['date_label']} <" in skill_text
    assert f"| {sections['area_header']} |" in skill_text


def test_packaged_resources_cover_quarto_config(tmp_path: Path) -> None:
    pdf_render.stage_resources(feedback_render.RENDER_KIND, tmp_path)

    config = (tmp_path / "_quarto.yml").read_text(encoding="utf-8")
    for name in ("filters/feedback-blocks.lua", "filters/identifier-links.lua", "filters/czech-quotes.lua"):
        assert name in config
        assert (tmp_path / name).is_file()
    assert "typst-template.typ" in config and (tmp_path / "typst-template.typ").is_file()
    fonts = sorted(path.name for path in (tmp_path / "fonts").glob("*.ttf"))
    assert fonts == [f"NotoSans-{style}.ttf" for style in ("Bold", "BoldItalic", "Italic", "Regular")]
    assert (tmp_path / "fonts" / "LICENSE-OFL").is_file()
    blocks_filter = (tmp_path / "filters" / "feedback-blocks.lua").read_text(encoding="utf-8")
    assert f'"{pdf_render.RENDER_VALUES_NAME}"' in blocks_filter


def test_find_quarto_reports_missing_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_render.shutil, "which", lambda name: None)

    with pytest.raises(pdf_render.RenderError, match=f"quarto is not installed.*send {feedback_render.FEEDBACK_REL}"):
        feedback_render.find_quarto()


@pytest.mark.parametrize(("output", "accepted"), [("1.10.18\n", True), ("1.11.0\n", True), ("1.9.30\n", False)])
def test_quarto_version_refuses_older_than_tested(monkeypatch: pytest.MonkeyPatch, output: str, accepted: bool) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=output, stderr="")

    monkeypatch.setattr(pdf_render.subprocess, "run", fake_run)
    if accepted:
        assert pdf_render.quarto_version(Path("quarto")) == output.strip()
    else:
        with pytest.raises(pdf_render.RenderError, match="older than the tested"):
            pdf_render.quarto_version(Path("quarto"))


def gate_errors(round_dir: Path, *, case_id: str = "case-a") -> list[str]:
    source = (round_dir / feedback_render.FEEDBACK_REL).read_bytes()
    return feedback_render.approval_errors(
        round_dir, case_id=case_id, round_id="round-a", source_sha256=feedback_render.sha256_bytes(source)
    )


def test_approval_gate_accepts_a_valid_approval(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_approval(round_dir)

    assert gate_errors(round_dir) == []


def test_approval_gate_rejects_missing_approval(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)

    errors = gate_errors(round_dir)

    assert any("missing review approval record" in error for error in errors)


def test_approval_gate_rejects_stale_review_basis(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_approval(round_dir)
    (round_dir / BASIS_REL).write_text("# Draft, edited after the review\n", encoding="utf-8")

    errors = gate_errors(round_dir)

    assert any("review basis changed after approval" in error for error in errors)


def test_approval_gate_rejects_invalid_approval_whose_artifact_hash_matches(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    approval = write_approval(round_dir, verdict="changes_required", blocking_findings_count=2)
    payload = json.loads(approval.read_text(encoding="utf-8"))
    assert payload["reviewed_artifact_sha256"] == sha256_file(round_dir / feedback_render.FEEDBACK_REL)

    errors = gate_errors(round_dir)

    assert any("verdict must be approved/pass" in error for error in errors)
    assert any("blocking_findings_count 0" in error for error in errors)


def test_approval_gate_rejects_approval_for_another_round(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_approval(round_dir, round_id="round-b")

    errors = gate_errors(round_dir)

    assert any("round_id does not match" in error for error in errors)


def test_approval_gate_rejects_feedback_edited_after_approval(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_approval(round_dir)
    (round_dir / feedback_render.FEEDBACK_REL).write_text("# Feedback, edited after the review\n", encoding="utf-8")

    errors = gate_errors(round_dir)

    assert any("reviewed_artifact_sha256 is stale" in error for error in errors)


def test_approval_gate_rejects_bytes_that_differ_from_the_approved_file(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_approval(round_dir)

    errors = feedback_render.approval_errors(
        round_dir, case_id="case-a", round_id="round-a", source_sha256=feedback_render.sha256_bytes(b"other")
    )

    assert any("changed after it was read for rendering" in error for error in errors)


def test_approval_gate_requires_the_review_manifest(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_approval(round_dir)
    (round_dir / MANIFEST_REL).unlink()

    assert gate_errors(round_dir) == [f"missing required review manifest: {MANIFEST_REL.as_posix()}"]


def test_approval_gate_rejects_missing_observed_checks_and_self_basis(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_approval(round_dir, checks_observed=[], review_basis_path=feedback_render.FEEDBACK_REL)
    approval = round_dir / PROFILE.approval_path
    payload = json.loads(approval.read_text(encoding="utf-8"))
    payload["review_basis_sha256"] = payload["reviewed_artifact_sha256"]
    approval.write_text(json.dumps(payload), encoding="utf-8")

    errors = gate_errors(round_dir)

    assert any("missing required observed check: check-feedback-output" in error for error in errors)
    assert any("review_basis_path must be one of" in error for error in errors)


def test_approval_gate_rejects_approval_for_another_case(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_approval(round_dir)

    assert any("case_id does not match" in error for error in gate_errors(round_dir, case_id="case-b"))


class FakeRender:
    def __init__(self) -> None:
        self.metadata: dict[str, object] | None = None

    def __call__(self, source: bytes, output: Path, metadata: dict[str, object], quarto: Path) -> None:
        self.metadata = metadata
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"%PDF-1.7 fake\n")


@pytest.fixture
def cli_round(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, FakeRender]:
    round_dir = make_round(tmp_path)
    fake = FakeRender()
    monkeypatch.setattr(render_feedback, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(render_feedback, "find_quarto", lambda: Path("quarto"))
    monkeypatch.setattr(render_feedback, "quarto_version", lambda quarto: "1.10.18")
    monkeypatch.setattr(render_feedback, "render_pdf", fake)
    return round_dir, fake


def operation_records(round_dir: Path) -> list[dict[str, object]]:
    path = round_dir / OPERATION_LOG_REL
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_cli_refuses_unapproved_feedback_without_rendering(
    cli_round: tuple[Path, FakeRender], capsys: pytest.CaptureFixture[str]
) -> None:
    round_dir, fake = cli_round

    assert render_feedback.main(["render-feedback", "case-a"]) == 1

    assert fake.metadata is None
    assert not (round_dir / feedback_render.PDF_REL).exists()
    assert "no valid review approval" in capsys.readouterr().out
    assert operation_records(round_dir) == []


def test_cli_refusal_removes_a_stale_approved_pdf(cli_round: tuple[Path, FakeRender]) -> None:
    round_dir, fake = cli_round
    write_approval(round_dir)
    assert render_feedback.main(["render-feedback", "case-a"]) == 0
    (round_dir / feedback_render.FEEDBACK_REL).write_text("# Feedback, edited\n", encoding="utf-8")

    assert render_feedback.main(["render-feedback", "case-a"]) == 1

    assert not (round_dir / feedback_render.PDF_REL).exists()


def test_cli_missing_source_removes_a_stale_approved_pdf(cli_round: tuple[Path, FakeRender]) -> None:
    round_dir, _ = cli_round
    write_approval(round_dir)
    assert render_feedback.main(["render-feedback", "case-a"]) == 0
    (round_dir / feedback_render.FEEDBACK_REL).unlink()

    assert render_feedback.main(["render-feedback", "case-a"]) == 1

    assert not (round_dir / feedback_render.PDF_REL).exists()


def test_cli_draft_after_an_edit_removes_the_stale_approved_pdf(cli_round: tuple[Path, FakeRender]) -> None:
    round_dir, _ = cli_round
    write_approval(round_dir)
    assert render_feedback.main(["render-feedback", "case-a"]) == 0
    (round_dir / feedback_render.FEEDBACK_REL).write_text("# Feedback, edited\n", encoding="utf-8")

    assert render_feedback.main(["render-feedback", "case-a", "--draft"]) == 0

    assert not (round_dir / feedback_render.PDF_REL).exists()
    assert (round_dir / feedback_render.PREVIEW_PDF_REL).is_file()


def test_cli_failed_approved_render_leaves_no_earlier_pdf(
    cli_round: tuple[Path, FakeRender], monkeypatch: pytest.MonkeyPatch
) -> None:
    round_dir, _ = cli_round
    write_approval(round_dir)
    assert render_feedback.main(["render-feedback", "case-a"]) == 0

    def broken(*args: object) -> None:
        raise feedback_render.RenderError("quarto render exited with 1")

    monkeypatch.setattr(render_feedback, "render_pdf", broken)

    assert render_feedback.main(["render-feedback", "case-a"]) == 1
    assert not (round_dir / feedback_render.PDF_REL).exists()


def test_cli_reports_a_stale_pdf_it_cannot_remove(
    cli_round: tuple[Path, FakeRender], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    round_dir, fake = cli_round
    (round_dir / feedback_render.PDF_REL).write_bytes(b"%PDF old\n")

    def locked(self: Path, missing_ok: bool = False) -> None:
        raise PermissionError("in use")

    monkeypatch.setattr(Path, "unlink", locked)

    assert render_feedback.main(["render-feedback", "case-a", "--draft"]) == 1
    assert "cannot remove the stale" in capsys.readouterr().out
    assert fake.metadata is None


def test_cli_draft_after_reapproval_removes_the_earlier_pdf(cli_round: tuple[Path, FakeRender]) -> None:
    round_dir, _ = cli_round
    write_approval(round_dir)
    assert render_feedback.main(["render-feedback", "case-a"]) == 0
    (round_dir / feedback_render.FEEDBACK_REL).write_text("# Feedback, version B\n", encoding="utf-8")
    write_approval(round_dir)

    assert render_feedback.main(["render-feedback", "case-a", "--draft"]) == 0

    assert not (round_dir / feedback_render.PDF_REL).exists()


def test_cli_draft_keeps_the_pdf_rendered_from_the_current_feedback(cli_round: tuple[Path, FakeRender]) -> None:
    round_dir, _ = cli_round
    write_approval(round_dir)
    assert render_feedback.main(["render-feedback", "case-a"]) == 0

    assert render_feedback.main(["render-feedback", "case-a", "--draft"]) == 0

    assert (round_dir / feedback_render.PDF_REL).is_file()


def test_cli_draft_treats_an_unreadable_log_as_stale(cli_round: tuple[Path, FakeRender]) -> None:
    round_dir, _ = cli_round
    write_approval(round_dir)
    assert render_feedback.main(["render-feedback", "case-a"]) == 0
    (round_dir / OPERATION_LOG_REL).write_bytes(b"\xff\xfe not utf-8\n")

    assert render_feedback.main(["render-feedback", "case-a", "--draft"]) == 0

    assert not (round_dir / feedback_render.PDF_REL).exists()


def test_cli_renders_approved_feedback_and_logs_hashes(cli_round: tuple[Path, FakeRender]) -> None:
    round_dir, fake = cli_round
    write_approval(round_dir)

    assert render_feedback.main(["render-feedback", "case-a", "round-a"]) == 0

    pdf = round_dir / feedback_render.PDF_REL
    assert pdf.is_file()
    assert fake.metadata is not None and "draft" not in fake.metadata["masthead"]  # type: ignore[operator]
    [record] = operation_records(round_dir)
    assert record["operation"] == "render-feedback"
    assert record["artifacts"] == [feedback_render.FEEDBACK_REL, feedback_render.PDF_REL]
    assert record["details"] == {
        "source_sha256": sha256_file(round_dir / feedback_render.FEEDBACK_REL),
        "pdf_sha256": sha256_file(pdf),
        "quarto_version": "1.10.18",
        "draft": "false",
    }


def test_cli_draft_renders_without_approval_outside_outputs(cli_round: tuple[Path, FakeRender]) -> None:
    round_dir, fake = cli_round

    assert render_feedback.main(["render-feedback", "case-a", "--draft"]) == 0

    assert (round_dir / feedback_render.PREVIEW_PDF_REL).is_file()
    assert not (round_dir / feedback_render.PDF_REL).exists()
    assert fake.metadata is not None
    assert fake.metadata["masthead"]["draft"] == "NÁVRH"  # type: ignore[index]
    [record] = operation_records(round_dir)
    assert record["details"]["draft"] == "true"  # type: ignore[index]


def test_cli_reports_missing_quarto(
    cli_round: tuple[Path, FakeRender], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    round_dir, _ = cli_round

    def missing() -> Path:
        raise feedback_render.RenderError("quarto is not installed or not on PATH")

    monkeypatch.setattr(render_feedback, "find_quarto", missing)

    assert render_feedback.main(["render-feedback", "case-a", "--draft"]) == 1
    assert "ERROR: quarto is not installed" in capsys.readouterr().out
    assert operation_records(round_dir) == []
