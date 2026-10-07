"""Contract tests for `render-brief`: the bundle-approval gate, `outputs/` honesty, and layout values.

Quarto is replaced by a fake renderer; `scripts/smoke-render-brief` renders for real.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

# Sibling imports, not `tests.`: the test root is not a package in the Pants sandbox.
from test_assignment_bundle import CASE_ID, approved_case, payload, write_approval  # noqa: F401
from test_assignment_draft import assignment, czech_bundle
from thesis_review_workflow import brief_render, pdf_render
from thesis_review_workflow.assignment_bundle import approval_rel, assignment_formal_rel, brief_projection_rel
from thesis_review_workflow.assignment_draft import BRIEF_LANGUAGES, RENDERINGS
from thesis_review_workflow.cli import render_brief

PDF_REL = brief_render.pdf_rel("bp")
PREVIEW_REL = brief_render.preview_pdf_rel("bp")
BRIEF_REL = brief_projection_rel("bp")
ASSIGNMENT_REL = assignment_formal_rel("bp")


class FakeRender:
    def __init__(self) -> None:
        self.values: dict[str, object] | None = None

    def __call__(self, source: bytes, output: Path, values: dict[str, object], quarto: Path) -> None:
        self.values = values
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"%PDF-1.7 fake\n")


@pytest.fixture
def cli_case(approved_case: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, FakeRender]:  # noqa: F811
    cases_root = approved_case.parent / "cases"
    cases_root.mkdir()
    case_dir = approved_case.rename(cases_root / CASE_ID)
    fake = FakeRender()
    monkeypatch.setattr(render_brief, "repo_root", lambda: cases_root.parent)
    monkeypatch.setattr(render_brief, "find_quarto", lambda variant: Path("quarto"))
    monkeypatch.setattr(render_brief, "quarto_version", lambda quarto: "1.10.18")
    monkeypatch.setattr(render_brief, "render_pdf", fake)
    return case_dir, fake


def run(*args: str) -> int:
    return render_brief.main(["render-brief", CASE_ID, *args])


def stale_pdf(case_dir: Path) -> Path:
    pdf = case_dir / PDF_REL
    pdf.write_bytes(b"%PDF-1.7 earlier approved render\n")
    return pdf


def test_cli_renders_an_approved_brief_without_touching_the_markdown(cli_case: tuple[Path, FakeRender]) -> None:
    case_dir, fake = cli_case
    before = (case_dir / BRIEF_REL).read_bytes()

    assert run("bp") == 0

    assert (case_dir / PDF_REL).is_file()
    assert (case_dir / BRIEF_REL).read_bytes() == before
    assert fake.values is not None and "draft" not in fake.values["masthead"]  # type: ignore[operator]


def test_cli_records_the_approval_and_prints_the_official_title(cli_case: tuple[Path, FakeRender]) -> None:
    case_dir, fake = cli_case
    (case_dir / "case.md").write_text(
        (case_dir / "case.md").read_text(encoding="utf-8") + "Topic: Working label never printed\n", encoding="utf-8"
    )

    assert run("bp") == 0

    record = json.loads((case_dir / brief_render.render_record_rel("bp")).read_text(encoding="utf-8"))
    assert record["approval_sha256"] == pdf_render.sha256_bytes((case_dir / approval_rel("bp")).read_bytes())
    assert record["pdf_sha256"] == pdf_render.sha256_bytes((case_dir / PDF_REL).read_bytes())
    assert fake.values is not None
    assert fake.values["masthead"]["topic"] == "Téma"  # type: ignore[index]


def test_cli_draft_after_reapproval_removes_the_earlier_pdf(cli_case: tuple[Path, FakeRender]) -> None:
    case_dir, _ = cli_case
    assert run("bp") == 0
    write_approval(case_dir, payload(case_dir, timestamp="2026-10-07T00:00:00Z"))

    assert run("bp", "--draft") == 0

    assert not (case_dir / PDF_REL).exists()
    assert (case_dir / PREVIEW_REL).is_file()


def test_cli_draft_treats_an_unreadable_render_record_as_stale(cli_case: tuple[Path, FakeRender]) -> None:
    case_dir, _ = cli_case
    assert run("bp") == 0
    (case_dir / brief_render.render_record_rel("bp")).write_text("{not json", encoding="utf-8")

    assert run("bp", "--draft") == 0

    assert not (case_dir / PDF_REL).exists()


@pytest.mark.parametrize("draft", [False, True])
def test_cli_unsupported_language_still_removes_the_earlier_pdf(cli_case: tuple[Path, FakeRender], draft: bool) -> None:
    case_dir, _ = cli_case
    assert run("bp") == 0
    case_md = case_dir / "case.md"
    case_md.write_text(
        case_md.read_text(encoding="utf-8").replace("Student feedback language: en", "Student feedback language: cz"),
        encoding="utf-8",
    )

    assert run("bp", *(["--draft"] if draft else [])) == 1

    assert not (case_dir / PDF_REL).exists()


def test_cli_wrong_case_variant_touches_nothing(cli_case: tuple[Path, FakeRender]) -> None:
    case_dir, fake = cli_case
    pdf = stale_pdf(case_dir)

    assert run("BP") == 1

    assert fake.values is None
    assert pdf.is_file()


def test_exact_entry_requires_the_exact_spelling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "student_brief_bp.md").write_text("x", encoding="utf-8")

    assert brief_render.exact_entry(tmp_path / "student_brief_bp.md")
    assert not brief_render.exact_entry(tmp_path / "student_brief_BP.md")
    assert not brief_render.exact_entry(tmp_path / "missing" / "student_brief_bp.md")


@pytest.mark.parametrize(("rendering", "expected"), [("cs", "Téma"), ("none", "")])
def test_official_title_reads_the_single_rendering_block(rendering: str, expected: str) -> None:
    text = assignment(variant="bp")
    if rendering == "none":
        text = text.replace("## Czech Rendering", "## Something Else")

    assert brief_render.official_title(text) == expected


def test_title_labels_are_the_fit_is_rendering_fields() -> None:
    for key, label in brief_render.TITLE_LABEL.items():
        assert label in RENDERINGS[key].metadata


def test_cli_refuses_a_variant_without_approval(
    cli_case: tuple[Path, FakeRender], capsys: pytest.CaptureFixture[str]
) -> None:
    case_dir, fake = cli_case

    assert run("dp") == 1

    assert fake.values is None
    assert not (case_dir / brief_render.pdf_rel("dp")).exists()
    assert "no valid bundle approval" in capsys.readouterr().out


def test_cli_edit_after_approval_refuses_and_removes_the_earlier_pdf(cli_case: tuple[Path, FakeRender]) -> None:
    case_dir, fake = cli_case
    pdf = stale_pdf(case_dir)
    with (case_dir / BRIEF_REL).open("a", encoding="utf-8") as handle:
        handle.write("\nAn obligation added after review.\n")

    assert run("bp") == 1

    assert fake.values is None
    assert not pdf.exists()


def test_cli_draft_of_an_edited_brief_previews_outside_outputs_and_removes_the_pdf(
    cli_case: tuple[Path, FakeRender],
) -> None:
    case_dir, fake = cli_case
    pdf = stale_pdf(case_dir)
    (case_dir / "notes/topic_intake.md").write_text(
        (case_dir / "notes/topic_intake.md").read_text(encoding="utf-8") + "\nEdited.\n", encoding="utf-8"
    )

    assert run("bp", "--draft") == 0

    assert (case_dir / PREVIEW_REL).is_file()
    assert not pdf.exists()
    assert fake.values is not None
    assert fake.values["masthead"]["draft"] == "DRAFT"  # type: ignore[index]


def test_cli_draft_of_an_approved_brief_keeps_the_pdf_rendered_under_that_approval(
    cli_case: tuple[Path, FakeRender],
) -> None:
    case_dir, _ = cli_case
    assert run("bp") == 0

    assert run("bp", "--draft") == 0

    assert (case_dir / PDF_REL).is_file()
    assert (case_dir / PREVIEW_REL).is_file()


def test_cli_draft_removes_an_approved_looking_pdf_without_a_render_record(cli_case: tuple[Path, FakeRender]) -> None:
    case_dir, _ = cli_case
    pdf = stale_pdf(case_dir)

    assert run("bp", "--draft") == 0

    assert not pdf.exists()


def test_cli_failed_approved_render_leaves_no_earlier_pdf(
    cli_case: tuple[Path, FakeRender], monkeypatch: pytest.MonkeyPatch
) -> None:
    case_dir, _ = cli_case
    pdf = stale_pdf(case_dir)

    def failing(*args: object) -> None:
        raise pdf_render.RenderError("quarto render exited with 1")

    monkeypatch.setattr(render_brief, "render_pdf", failing)

    assert run("bp") == 1
    assert not pdf.exists()


def test_cli_missing_projection_removes_the_earlier_pdf(cli_case: tuple[Path, FakeRender]) -> None:
    case_dir, _ = cli_case
    pdf = stale_pdf(case_dir)
    (case_dir / BRIEF_REL).unlink()

    assert run("bp") == 1
    assert not pdf.exists()


def test_cli_refuses_a_thesis_review_case_before_touching_it(
    cli_case: tuple[Path, FakeRender], capsys: pytest.CaptureFixture[str]
) -> None:
    case_dir, fake = cli_case
    (case_dir / "case.md").write_text("Case kind: thesis-review\n", encoding="utf-8")
    pdf = stale_pdf(case_dir)

    assert run("bp", "--draft") == 1

    assert fake.values is None
    assert pdf.is_file()
    assert "topic-proposal" in capsys.readouterr().out


@pytest.mark.parametrize("variant", ["../bp", "b p", ""])
def test_cli_refuses_an_unusable_variant(cli_case: tuple[Path, FakeRender], variant: str) -> None:
    _, fake = cli_case

    assert run(variant) == 2
    assert fake.values is None


@pytest.mark.parametrize("rel", [BRIEF_REL, ASSIGNMENT_REL])
def test_gate_rejects_bytes_that_differ_from_the_approved_file(approved_case: Path, rel: str) -> None:  # noqa: F811
    read = brief_render.read_bound(approved_case, "bp")
    read[rel] = b"other"

    errors, approval_sha256 = brief_render.approval_errors(approved_case, case_id=CASE_ID, variant="bp", read=read)

    assert errors == [f"{approval_rel('bp')}: {rel} changed after it was read for rendering"]
    assert approval_sha256 == ""


def test_gate_rejects_an_approval_replaced_after_the_bundle_check(
    approved_case: Path, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    read = brief_render.read_bound(approved_case, "bp")
    checked = brief_render.check_bundle

    def check_then_replace(case_dir: Path, case_id: str, variant: str) -> list[str]:
        errors = checked(case_dir, case_id, variant)
        write_approval(case_dir, payload(case_dir, verdict="changes_requested"))
        return errors

    monkeypatch.setattr(brief_render, "check_bundle", check_then_replace)

    errors, approval_sha256 = brief_render.approval_errors(approved_case, case_id=CASE_ID, variant="bp", read=read)

    assert any("verdict" in error for error in errors)
    assert approval_sha256 == ""


def test_gate_returns_the_hash_of_the_approval_record(approved_case: Path) -> None:  # noqa: F811
    read = brief_render.read_bound(approved_case, "bp")

    errors, approval_sha256 = brief_render.approval_errors(approved_case, case_id=CASE_ID, variant="bp", read=read)

    assert errors == []
    assert approval_sha256 == pdf_render.sha256_bytes((approved_case / approval_rel("bp")).read_bytes())


def test_gate_rejects_a_hand_written_record_that_check_bundle_rejects(approved_case: Path) -> None:  # noqa: F811
    write_approval(approved_case, payload(approved_case, verdict="changes_requested"))
    read = brief_render.read_bound(approved_case, "bp")

    errors, _ = brief_render.approval_errors(approved_case, case_id=CASE_ID, variant="bp", read=read)

    assert any("verdict" in error for error in errors)


@pytest.mark.parametrize("draft", [False, True])
def test_render_values_map_the_czech_projection_headings(tmp_path: Path, draft: bool) -> None:
    case_dir = tmp_path / "topic"
    (case_dir / "notes").mkdir(parents=True)
    (case_dir / "outputs").mkdir()
    czech_bundle(case_dir)
    case = brief_render.brief_case(brief_render.require_topic_case(case_dir), case_dir.name)

    values = brief_render.render_values(case, "bp", topic="Téma", today=datetime.date(2026, 10, 7), draft=draft)

    assert values["lang"] == "cs"
    assert values["title"] == "Úvodní podklad k tématu"
    assert values["date"] == "7. 10. 2026"
    assert values["masthead"]["kind"] == "Bakalářská práce"
    assert ("draft" in values["masthead"]) is draft
    assert values["headings"] == {
        "title": "Úvodní podklad k tématu - bp",
        "content": [
            "Na čem práce staví",
            "Kde začít",
            "Jak budeme spolupracovat",
            "Jak číst zadání",
            "Co do práce nepatří",
        ],
        "delta": "Specifika varianty - bp",
        "delta_display": "Specifika varianty",
    }


@pytest.mark.parametrize("language", ["cs", "en"])
def test_mapped_headings_are_the_projection_contract(language: str) -> None:
    contract = BRIEF_LANGUAGES[language]
    case = brief_render.BriefCase(language=contract)

    values = brief_render.render_values(case, "dp", topic="T", today=datetime.date(2026, 1, 2), draft=False)

    headings = [f"# {values['headings']['title']}"]
    headings += [f"### {name}" for name in values["headings"]["content"]]
    headings.append(f"## {values['headings']['delta']}")
    assert headings == list(contract.projection_headings("dp"))


def test_english_date_and_an_unknown_work_type() -> None:
    case = brief_render.BriefCase(language=BRIEF_LANGUAGES["en"])

    values = brief_render.render_values(case, "xp", topic="T", today=datetime.date(2026, 1, 2), draft=False)

    assert values["date"] == "2 January 2026"
    assert values["masthead"]["kind"] == "xp"


def test_packaged_resources_cover_the_brief_quarto_config(tmp_path: Path) -> None:
    pdf_render.stage_resources(brief_render.RENDER_KIND, tmp_path)

    config = (tmp_path / "_quarto.yml").read_text(encoding="utf-8")
    for name in ("filters/brief-blocks.lua", "filters/identifier-links.lua", "filters/czech-quotes.lua"):
        assert name in config
        assert (tmp_path / name).is_file()
    assert (tmp_path / "typst-template.typ").is_file()
    assert not (tmp_path / "filters" / "feedback-blocks.lua").exists()
    blocks_filter = (tmp_path / "filters" / "brief-blocks.lua").read_text(encoding="utf-8")
    assert f'"{pdf_render.RENDER_VALUES_NAME}"' in blocks_filter
    fonts = sorted(path.name for path in (tmp_path / "fonts").glob("*.ttf"))
    assert fonts == [f"NotoSans-{style}.ttf" for style in ("Bold", "BoldItalic", "Italic", "Regular")]
