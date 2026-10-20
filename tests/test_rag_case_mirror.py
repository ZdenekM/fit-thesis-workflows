"""Tests for the allowlisted case Markdown mirror that local RAG indexes."""

from pathlib import Path

import pytest

from thesis_review_workflow.rag_case_mirror import refresh_mirror, select_case_markdown

ROUND = "demo-bp-2027/rounds/r1"

INDEXED = [
    "demo-bp-2027/case.md",
    f"{ROUND}/notes/round-notes.md",
    f"{ROUND}/outputs/feedback_student.md",
    f"{ROUND}/outputs/nested/literature_citation_review.md",
    f"{ROUND}/notes/assignment-source.txt",
    f"{ROUND}/work/submitted_reports/report_transcript.md",
    f"{ROUND}/work/feedback_student_draft.md",
    f"{ROUND}/work/supervisor_packets/text_assignment_findings.md",
    f"{ROUND}/work/reviews/supervisor_feedback_review_notes.md",
    f"{ROUND}/work/literature/source_notes.md",
    f"{ROUND}/work/calibration/profile_versions/v1.md",
    f"{ROUND}/work/github-intake/contribution-map.md",
    "topic-x/outputs/student_brief_bp.md",
    "topic-x/work/reviews/assignment_review_bp.md",
    "_literature/bobak-2020-x/notes.md",
]

NOT_INDEXED = [
    "demo-bp-2027/current-round.txt",
    f"{ROUND}/outputs/feedback_student.pdf",
    f"{ROUND}/inputs/thesis.pdf",
    f"{ROUND}/inputs/student_working_document.md",
    f"{ROUND}/outputs/feedback.txt",
    f"{ROUND}/inputs/github/README.md",
    f"{ROUND}/extracted/thesis.txt",
    f"{ROUND}/extracted/notes.md",
    f"{ROUND}/work/code/student/README.md",
    f"{ROUND}/work/thesis-source/chapter.md",
    f"{ROUND}/work/submission_bundle/README.md",
    f"{ROUND}/work/github-intake/raw/diff.md",
    f"{ROUND}/work/code_workspace.md",
    f"{ROUND}/work/submission_bundle_inventory.md",
    f"{ROUND}/work/supervisor_packets/text_assignment.md",
    f"{ROUND}/work/review_deltas/delta.md",
    f"{ROUND}/work/common_briefing.json",
    "_literature/bobak-2020-x/fulltext.txt",
    "_literature/bobak-2020-x/paper.pdf",
    "_other/notes/x.md",
]


@pytest.fixture
def cases(tmp_path: Path) -> Path:
    root = tmp_path / "cases"
    for rel in INDEXED + NOT_INDEXED:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"content of {rel}\n", encoding="utf-8")
    return root


def test_selects_exactly_the_allowlisted_case_markdown(cases: Path) -> None:
    assert select_case_markdown(cases) == sorted(INDEXED)


def test_refresh_copies_the_allowlist_and_nothing_else(cases: Path) -> None:
    result = refresh_mirror(cases)
    mirrored = sorted(p.relative_to(cases / "_rag").as_posix() for p in (cases / "_rag").rglob("*") if p.is_file())
    assert mirrored == sorted(INDEXED)
    assert (result.copied, result.unchanged, result.removed) == (len(INDEXED), 0, 0)
    assert (cases / "_rag" / INDEXED[0]).read_text(encoding="utf-8") == f"content of {INDEXED[0]}\n"


def test_the_mirror_never_mirrors_itself(cases: Path) -> None:
    refresh_mirror(cases)
    assert not any(rel.startswith("_rag/") for rel in select_case_markdown(cases))


def test_refresh_updates_changed_files_and_drops_removed_ones(cases: Path) -> None:
    refresh_mirror(cases)
    (cases / INDEXED[1]).write_text("edited\n", encoding="utf-8")
    (cases / INDEXED[2]).unlink()
    stray = cases / "_rag" / "leftover" / "old.md"
    stray.parent.mkdir(parents=True)
    stray.write_text("old\n", encoding="utf-8")

    result = refresh_mirror(cases)

    assert (cases / "_rag" / INDEXED[1]).read_text(encoding="utf-8") == "edited\n"
    assert not (cases / "_rag" / INDEXED[2]).exists()
    assert not stray.parent.exists()
    assert (result.copied, result.removed) == (1, 2)
    assert result.unchanged == len(INDEXED) - 2


def test_symlinks_are_neither_selected_nor_followed(cases: Path, tmp_path: Path) -> None:
    secret = tmp_path / "secret.md"
    secret.write_text("private\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x_findings.md").write_text("private\n", encoding="utf-8")
    (outside / "review.md").write_text("private\n", encoding="utf-8")
    (cases / ROUND / "notes" / "linked.md").symlink_to(secret)
    (cases / "linked-case").symlink_to(cases / "demo-bp-2027", target_is_directory=True)
    (cases / ROUND / "work" / "linked_packets").symlink_to(outside, target_is_directory=True)
    (cases / "topic-x" / "work" / "reviews").rename(tmp_path / "moved-reviews")
    (cases / "topic-x" / "work" / "reviews").symlink_to(outside, target_is_directory=True)

    selected = select_case_markdown(cases)
    assert f"{ROUND}/notes/linked.md" not in selected
    assert not any(rel.startswith("linked-case/") for rel in selected)
    assert not any("linked_packets" in rel or rel.startswith("topic-x/work/reviews/") for rel in selected)


def test_an_empty_allowlist_still_creates_the_mirror_root(tmp_path: Path) -> None:
    root = tmp_path / "cases"
    root.mkdir()
    refresh_mirror(root)
    assert (root / "_rag").is_dir()


def test_refuses_to_write_through_a_symlinked_mirror_directory(cases: Path, tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (cases / "_rag").mkdir()
    (cases / "_rag" / "demo-bp-2027").symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(ValueError):
        refresh_mirror(cases)
    assert not any(elsewhere.iterdir())


def test_refuses_a_symlinked_mirror(cases: Path, tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (cases / "_rag").symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(ValueError):
        refresh_mirror(cases)
    assert not any(elsewhere.iterdir())
