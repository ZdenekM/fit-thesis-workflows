from pathlib import Path

from thesis_review_workflow.cli import check_supervisor_reading_pass
from thesis_review_workflow.cli.check_feedback_output import INTERNAL_PATTERNS
from thesis_review_workflow.cli.check_opponent_materials import INTERNAL_WORKFLOW_PATTERNS
from thesis_review_workflow.cli.check_private import PRIVATE_MARKDOWN_RE
from thesis_review_workflow.cli.init_review_manifest import helper_dependency_hashes
from thesis_review_workflow.review_delta import APPEND_ONLY_OPERATOR_NOTE_REFS
from thesis_review_workflow.review_packets import COMMON_BRIEFING_BASE_INPUTS
from thesis_review_workflow.structured_evidence import CURRENT_EVIDENCE_DEFAULT_SOURCE_REFS
from thesis_review_workflow.supervisor_packets import BASE_INPUTS as SUPERVISOR_PACKET_BASE_INPUTS
from thesis_review_workflow.supervisor_packets import PACKET_ROLES
from thesis_review_workflow.supervisor_reading_pass import (
    METADATA_LABELS,
    OBSERVATION_LABELS,
    OBSERVATIONS_HEADING,
    ROUTING_VALUES,
    SUPERVISOR_READING_PASS_REL,
    SUPERVISOR_READING_PASS_TEMPLATE,
    UNVERIFIED_EVIDENCE_TOKEN,
    routing_counts,
    validate_reading_pass_text,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

METADATA = "\n".join(
    [
        "Cteny artefakt: inputs/thesis.pdf",
        "Datum cteni: 2026-09-07",
        "Forma zapisu: diktovano",
        "Rozsah cteni: kapitoly 1-3",
        "Co jsem necetl: prilohy",
    ]
)


def pass_text(*blocks: str, metadata: str = METADATA) -> str:
    return "\n".join(["# Reading Pass", "", metadata, "", OBSERVATIONS_HEADING, "", *blocks])


def block(title: str, observation: str, evidence: str, routing: str) -> str:
    return "\n".join(
        [
            f"### {title}",
            "",
            f"Pozorovani: {observation}",
            f"Evidence: {evidence}",
            f"Routing: {routing}",
            "",
        ]
    )


def test_minimal_valid_pass_has_no_errors() -> None:
    text = pass_text(block("Struktura", "Kapitola 2 nema uvod", "kapitola 2, str. 14", "student_feedback"))
    errors, warnings = validate_reading_pass_text(text)
    assert errors == []
    assert warnings == []
    assert routing_counts(text)["student_feedback"] == 1


def test_every_routing_value_is_accepted() -> None:
    blocks = [
        block(f"Blok {index}", "pozorovani", "kapitola 3", routing) for index, routing in enumerate(ROUTING_VALUES)
    ]
    errors, _ = validate_reading_pass_text(pass_text(*blocks))
    assert errors == []


def test_missing_metadata_label_is_an_error() -> None:
    metadata = "\n".join(line for line in METADATA.splitlines() if not line.startswith("Rozsah cteni:"))
    errors, _ = validate_reading_pass_text(
        pass_text(block("A", "pozorovani", "kapitola 1", "internal_only"), metadata=metadata)
    )
    assert any("missing metadata label: Rozsah cteni:" in error for error in errors)


def test_empty_required_metadata_value_is_an_error() -> None:
    metadata = METADATA.replace("Cteny artefakt: inputs/thesis.pdf", "Cteny artefakt:")
    errors, _ = validate_reading_pass_text(
        pass_text(block("A", "pozorovani", "kapitola 1", "internal_only"), metadata=metadata)
    )
    assert any("metadata label has no value: Cteny artefakt:" in error for error in errors)


def test_optional_metadata_value_may_be_empty() -> None:
    metadata = METADATA.replace("Co jsem necetl: prilohy", "Co jsem necetl:")
    errors, _ = validate_reading_pass_text(
        pass_text(block("A", "pozorovani", "kapitola 1", "internal_only"), metadata=metadata)
    )
    assert errors == []


def test_missing_observation_label_is_an_error() -> None:
    incomplete = "\n".join(["### A", "", "Pozorovani: chybi evidence", "Routing: internal_only", ""])
    errors, _ = validate_reading_pass_text(pass_text(incomplete))
    assert any("missing Evidence:" in error for error in errors)


def test_unknown_routing_value_is_an_error() -> None:
    errors, _ = validate_reading_pass_text(pass_text(block("A", "pozorovani", "kapitola 1", "maybe")))
    assert any("Routing must be one of" in error and "maybe" in error for error in errors)


def test_generic_evidence_is_an_error() -> None:
    errors, _ = validate_reading_pass_text(pass_text(block("A", "pozorovani", "cela prace", "student_feedback")))
    assert any("Evidence is generic" in error for error in errors)


def test_unverified_evidence_may_not_route_to_student_feedback() -> None:
    errors, _ = validate_reading_pass_text(
        pass_text(block("A", "pozorovani", UNVERIFIED_EVIDENCE_TOKEN, "student_feedback"))
    )
    assert any("unverified evidence must route to" in error for error in errors)


def test_unverified_evidence_may_route_to_verify_first() -> None:
    errors, warnings = validate_reading_pass_text(
        pass_text(
            block("A", "pozorovani", UNVERIFIED_EVIDENCE_TOKEN, "verify_first"),
            block("B", "pozorovani", "kapitola 4", "student_feedback"),
        )
    )
    assert errors == []
    assert warnings == []


def test_all_unverified_pass_warns_without_failing() -> None:
    errors, warnings = validate_reading_pass_text(
        pass_text(block("A", "pozorovani", UNVERIFIED_EVIDENCE_TOKEN, "verify_first"))
    )
    assert errors == []
    assert any("every observation is unverified" in warning for warning in warnings)


def test_pass_without_observations_is_an_error() -> None:
    errors, _ = validate_reading_pass_text(pass_text())
    assert any("no observation blocks" in error for error in errors)


def test_missing_observations_heading_is_an_error() -> None:
    errors, _ = validate_reading_pass_text("\n".join(["# Reading Pass", "", METADATA, ""]))
    assert any("missing observations heading" in error for error in errors)


def test_prose_mentioning_a_label_is_not_a_field() -> None:
    prose_block = "\n".join(
        [
            "### A",
            "",
            "Text that talks about Routing: values in the middle of a sentence is prose.",
            "Pozorovani: pozorovani",
            "Evidence: kapitola 1",
            "Routing: internal_only",
            "",
        ]
    )
    errors, _ = validate_reading_pass_text(pass_text(prose_block))
    assert errors == []


def make_round(root: Path, *, text: str | None) -> Path:
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (root / "cases" / "case-a" / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    if text is not None:
        (round_dir / SUPERVISOR_READING_PASS_REL).write_text(text, encoding="utf-8")
    return round_dir


def test_cli_accepts_a_round_without_a_reading_pass(capsys, monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    make_round(root, text=None)
    monkeypatch.setattr(check_supervisor_reading_pass, "repo_root", lambda: root)
    assert check_supervisor_reading_pass.main(["check-supervisor-reading-pass", "case-a"]) == 0
    captured = capsys.readouterr()
    assert "is absent, which is valid" in captured.out
    assert SUPERVISOR_READING_PASS_TEMPLATE in captured.out


def test_cli_reports_routing_counts_for_a_valid_pass(capsys, monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    make_round(
        root,
        text=pass_text(
            block("A", "pozorovani", "kapitola 2", "student_feedback"),
            block("B", "pozorovani", "kapitola 3", "internal_only"),
        ),
    )
    monkeypatch.setattr(check_supervisor_reading_pass, "repo_root", lambda: root)
    assert check_supervisor_reading_pass.main(["check-supervisor-reading-pass", "case-a", "round-a"]) == 0
    captured = capsys.readouterr()
    assert "student_feedback 1" in captured.out
    assert "internal_only 1" in captured.out


def test_cli_fails_on_a_malformed_pass(capsys, monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    make_round(root, text=pass_text(block("A", "pozorovani", "cela prace", "student_feedback")))
    monkeypatch.setattr(check_supervisor_reading_pass, "repo_root", lambda: root)
    assert check_supervisor_reading_pass.main(["check-supervisor-reading-pass", "case-a"]) == 1
    captured = capsys.readouterr()
    assert "is not usable" in captured.err
    assert "Evidence is generic" in captured.err


def test_owned_path_reaches_every_consumer(tmp_path: Path) -> None:
    """A declared path with one owner is only worth having if every consumer reads it there.

    Every entry here was a real omission at some point in this slice: the leak lists and the
    privacy guard were the chartered five, and the packet, briefing and manifest-dependency
    surfaces were found afterwards by the parent and the implementation review.
    """

    assert SUPERVISOR_READING_PASS_REL in CURRENT_EVIDENCE_DEFAULT_SOURCE_REFS
    assert SUPERVISOR_READING_PASS_REL in APPEND_ONLY_OPERATOR_NOTE_REFS
    assert SUPERVISOR_READING_PASS_REL in SUPERVISOR_PACKET_BASE_INPUTS
    assert SUPERVISOR_READING_PASS_REL in COMMON_BRIEFING_BASE_INPUTS
    assert SUPERVISOR_READING_PASS_REL in PACKET_ROLES[0].role_inputs
    basename = Path(SUPERVISOR_READING_PASS_REL).name
    assert any(basename.replace(".", "\\.") in pattern for pattern in INTERNAL_PATTERNS)
    assert any(basename.replace(".", "\\.") in pattern for pattern in INTERNAL_WORKFLOW_PATTERNS)
    assert PRIVATE_MARKDOWN_RE.search(f"cases/case-a/rounds/round-a/{SUPERVISOR_READING_PASS_REL}")

    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / SUPERVISOR_READING_PASS_REL).write_text("x", encoding="utf-8")
    for check in ("check-supervisor-ready", "check-feedback-language", "check-feedback-output"):
        hashes = helper_dependency_hashes(round_dir, check)
        assert f"round:{SUPERVISOR_READING_PASS_REL}" in hashes, check


def test_tracked_template_is_not_treated_as_a_private_artifact() -> None:
    """The template and the round note must not share a basename; the guard has no template exception."""

    assert PRIVATE_MARKDOWN_RE.search(SUPERVISOR_READING_PASS_TEMPLATE) is None
    assert Path(SUPERVISOR_READING_PASS_TEMPLATE).name != Path(SUPERVISOR_READING_PASS_REL).name


def test_template_matches_the_checker_contract() -> None:
    """The template is the operator's only documentation of the shape the checker enforces."""

    text = (REPO_ROOT / SUPERVISOR_READING_PASS_TEMPLATE).read_text(encoding="utf-8")
    for label in METADATA_LABELS:
        assert any(line.startswith(label) for line in text.splitlines()), label
    for label in OBSERVATION_LABELS:
        assert f"{label}" in text, label
    assert OBSERVATIONS_HEADING in text
    assert SUPERVISOR_READING_PASS_REL in text
    assert UNVERIFIED_EVIDENCE_TOKEN in text
    for routing in ROUTING_VALUES:
        assert f"`{routing}`" in text, routing


def test_markdown_formatting_cannot_defeat_the_unverified_rule() -> None:
    """The one rule the routing enum exists for must survive a backtick or a full stop."""

    for evidence in (f"`{UNVERIFIED_EVIDENCE_TOKEN}`", f"{UNVERIFIED_EVIDENCE_TOKEN}.", " NEOVEROVANO "):
        errors, _ = validate_reading_pass_text(pass_text(block("A", "pozorovani", evidence, "student_feedback")))
        assert any("unverified evidence must route to" in error for error in errors), evidence


def test_markdown_formatting_cannot_defeat_the_generic_evidence_rule() -> None:
    for evidence in ("cela prace.", "`cela prace`", "Celá práce", "TODO."):
        errors, _ = validate_reading_pass_text(pass_text(block("A", "pozorovani", evidence, "student_feedback")))
        assert any("Evidence is generic" in error for error in errors), evidence


def test_a_routing_value_with_formatting_is_still_counted() -> None:
    text = pass_text(block("A", "pozorovani", "kapitola 2", "`student_feedback`"))
    errors, _ = validate_reading_pass_text(text)
    assert errors == []
    assert routing_counts(text)["student_feedback"] == 1


def test_a_repeated_label_is_an_error_rather_than_a_silent_first_wins() -> None:
    repeated = "\n".join(
        [
            "### A",
            "",
            "Pozorovani: pozorovani",
            "Evidence: kapitola 1",
            "Routing: student_feedback",
            "Routing: internal_only",
            "",
        ]
    )
    errors, _ = validate_reading_pass_text(pass_text(repeated))
    assert any("appears more than once" in error for error in errors)


def test_observation_content_before_the_section_is_an_error() -> None:
    text = "\n".join(
        [
            "# Reading Pass",
            "",
            METADATA,
            "",
            "### Stray",
            "",
            "Pozorovani: pozorovani",
            f"Evidence: {UNVERIFIED_EVIDENCE_TOKEN}",
            "Routing: student_feedback",
            "",
            OBSERVATIONS_HEADING,
            "",
            block("A", "pozorovani", "kapitola 1", "internal_only"),
        ]
    )
    errors, _ = validate_reading_pass_text(text)
    assert any("observation heading outside" in error for error in errors)


def test_observation_content_under_a_later_section_is_an_error() -> None:
    text = pass_text(
        block("A", "pozorovani", "kapitola 1", "internal_only"),
        "## Dalsi poznamky",
        "",
        block("B", "pozorovani", UNVERIFIED_EVIDENCE_TOKEN, "student_feedback"),
    )
    errors, _ = validate_reading_pass_text(text)
    assert any("outside" in error for error in errors)


def test_a_sub_heading_starts_its_own_block_instead_of_merging() -> None:
    text = pass_text(
        block("A", "pozorovani", "kapitola 1", "internal_only"),
        "#### B",
        "",
        "Pozorovani: pozorovani",
        f"Evidence: {UNVERIFIED_EVIDENCE_TOKEN}",
        "Routing: student_feedback",
        "",
    )
    errors, _ = validate_reading_pass_text(text)
    assert any("unverified evidence must route to" in error for error in errors)


def test_an_untitled_observation_heading_is_an_error() -> None:
    untitled = "\n".join(["###", "", "Pozorovani: pozorovani", "Evidence: kapitola 1", "Routing: internal_only", ""])
    errors, _ = validate_reading_pass_text(pass_text(untitled))
    assert any("observation heading has no title" in error for error in errors)
