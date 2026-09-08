"""Contract tests for the assignment authoring surface.

These read the tracked templates, the default profile, and the operator doc
directly, the way `tests/test_agent_profile_contracts.py` reads the tracked
registry: the artifacts under test ARE the contract, so a fixture copy would
only prove the fixture right.
"""

from pathlib import Path

from thesis_review_workflow.assignment_draft import (
    BRIEF_LANGUAGES,
    RENDERINGS,
    SUPPLEMENT_LABEL,
    ascii_folded,
    form_labels,
)
from thesis_review_workflow.metadata import CASE_KINDS, DEFAULT_CASE_KIND, case_kind, unresolved_values

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / "templates"
UNRESOLVED_MARKER = "UNRESOLVED:"
AUTHORING_STYLE_HEADING = "## Assignment Authoring Style"


def read(path: Path) -> str:
    assert path.is_file(), f"{path} is missing — the BUILD dependency or the slice did not land it"
    return path.read_text(encoding="utf-8")


def flat(text: str) -> str:
    """Collapse wrapping so a prose assertion does not depend on where a line broke."""

    return " ".join(text.split())


def headings(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.startswith("#")]


def test_topic_intake_template_carries_its_required_sections() -> None:
    text = read(TEMPLATES / "topic-intake.md")
    found = headings(text)
    for heading in (
        "## Motivation",
        "## Citable Artifacts",
        "## Success Criteria",
        "## Out Of Scope",
        "## Variant Notes",
    ):
        assert heading in found, f"templates/topic-intake.md lost `{heading}`"
    assert "Topic id:" in text
    assert "Depends on topic:" in text


def test_topic_intake_citable_artifacts_carry_an_identifier_slot() -> None:
    """The probe could not supply a DOI and an agent must not invent one."""

    text = read(TEMPLATES / "topic-intake.md")
    body = text.split("## Citable Artifacts", 1)[1].split("\n## ", 1)[0]
    assert "Identifier:" in body
    assert "Kind: doi / arxiv / isbn / url" in body
    assert "unresolved marker in the `Identifier:` value" in flat(body)
    assert SUPPLEMENT_LABEL in body, "the one admissible non-sourced literature line is declared, never matched"


def test_topic_intake_separates_sibling_exclusion_from_dependency() -> None:
    """Mutual exclusion between offered topics is not `Depends on topic:`."""

    text = read(TEMPLATES / "topic-intake.md")
    out_of_scope = text.split("## Out Of Scope", 1)[1].split("\n## ", 1)[0]
    assert "### Not Part Of The Work" in out_of_scope
    assert "### Sibling Topics This One Excludes" in out_of_scope
    assert "not `Depends on topic:`" in flat(out_of_scope), "the slot must say what it is not"


def test_topic_intake_splits_success_criteria_three_ways() -> None:
    text = read(TEMPLATES / "topic-intake.md")
    criteria = text.split("## Success Criteria", 1)[1].split("\n## ", 1)[0]
    for heading in (
        "### Assessable As An Assignment Point",
        "### Rationale Only",
        "### Interpretation For The Student",
    ):
        assert heading in criteria, f"templates/topic-intake.md lost `{heading}`"


# From the checker's single source, so template and checker cannot drift.
CZECH_FIELD_ORDER = form_labels(RENDERINGS["cs"])
ENGLISH_FIELD_ORDER = form_labels(RENDERINGS["en"])


def rendering_block(text: str, heading: str) -> str:
    assert heading in text, f"templates/assignment-formal.md lost `{heading}`"
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def field_labels_in_order(block: str, expected: tuple[str, ...]) -> list[str]:
    """Labels that actually open a line, so a mention inside prose does not count."""

    wanted = set(expected)
    return [line.split(":", 1)[0] + ":" for line in block.splitlines() if line.split(":", 1)[0] + ":" in wanted]


def test_assignment_formal_template_carries_one_fillable_block_per_rendering() -> None:
    """A filled copy must produce the exact FIT IS field set, not a mixed one."""

    text = read(TEMPLATES / "assignment-formal.md")
    assert "Rendering: cs / en" in text
    assert "delete the rendering block you are not using" in flat(text)

    czech = rendering_block(text, "## Czech Rendering")
    assert field_labels_in_order(czech, CZECH_FIELD_ORDER) == list(CZECH_FIELD_ORDER)
    assert not set(field_labels_in_order(czech, ENGLISH_FIELD_ORDER)) - {"Student:"}

    english = rendering_block(text, "## English Rendering")
    assert field_labels_in_order(english, ENGLISH_FIELD_ORDER) == list(ENGLISH_FIELD_ORDER)
    assert not set(field_labels_in_order(english, CZECH_FIELD_ORDER)) - {"Student:"}


def test_assignment_formal_template_carries_both_document_titles_per_rendering() -> None:
    text = read(TEMPLATES / "assignment-formal.md")
    czech = rendering_block(text, "## Czech Rendering")
    english = rendering_block(text, "## English Rendering")
    assert "Zadání bakalářské práce" in czech and "Zadání diplomové práce" in czech
    assert "Bachelor's Thesis Assignment" in english and "Master's Thesis Assignment" in english


def test_assignment_formal_template_declares_no_bilingual_title_pair() -> None:
    """The corpus carries no English title field inside a Czech document."""

    text = read(TEMPLATES / "assignment-formal.md")
    assert "no English title field inside a Czech document" in flat(text)


def test_student_brief_template_is_shared_plus_variant_delta() -> None:
    """~85% of two briefs for one topic was variant-independent in the probe."""

    text = read(TEMPLATES / "student-brief.md")
    # Locate the HEADINGS, not the backticked mentions of them in the surrounding prose.
    shared_at = text.index("\n## Shared Brief\n")
    delta_at = text.index("\n## Variant Delta\n")
    assert shared_at >= 0 and delta_at > shared_at
    assert "byte-identically" in flat(text[:shared_at])
    delta = text[delta_at:]
    assert "### bp" in delta and "### dp" in delta
    assert "### How To Read The Assignment" in text[shared_at:delta_at]
    for language in BRIEF_LANGUAGES.values():
        for heading in language.content_headings:
            assert heading in text, f"templates/student-brief.md omits the {language.key} heading `{heading}`"
        # The projection shape must be fixed per language, not guessed.
        assert f"{language.title} - <variant>" in text
        assert f"{language.delta_heading} - <variant>" in text


def test_no_brief_language_heading_is_spelled_like_a_neutral_source_wrapper() -> None:
    """The wrappers are language-neutral, so a wrong-language heading can be forbidden anywhere."""

    neutral = {"# Student Brief", "## Shared Brief", "## Variant Delta"}
    for language in BRIEF_LANGUAGES.values():
        owned = set(language.heading_bases()) | {ascii_folded(base) for base in language.heading_bases()}
        assert not owned & neutral, f"{language.key} claims a neutral wrapper: {sorted(owned & neutral)}"


def test_the_brief_source_and_its_per_variant_projection_are_distinguished() -> None:
    """A per-variant brief is a projection, not a second authored brief."""

    template = read(TEMPLATES / "student-brief.md")
    assert "notes/student_brief.md" in template
    assert "outputs/student_brief_<variant>.md" in template
    assert "Never author two whole briefs." in flat(template)

    doc = read(REPO_ROOT / "docs" / "assignment-authoring.md")
    layout = doc.split("```text", 1)[1].split("```", 1)[0]
    assert "notes/student_brief.md" in layout, "the doc layout must name the canonical brief source"
    assert "projection" in layout


def test_every_authoring_template_points_at_the_unresolved_marker_rule() -> None:
    for name in ("topic-intake.md", "assignment-formal.md", "student-brief.md"):
        text = read(TEMPLATES / name)
        assert "unresolved marker" in flat(text), f"templates/{name} does not mention the marker"
        assert "## Unresolved Values" in text, f"templates/{name} does not point at the rule"


def test_no_authoring_template_trips_its_own_marker() -> None:
    """Explaining the marker must not read as an unresolved value.

    The review that produced this test found the earlier `UNRESOLVED:`-anywhere
    reading blocking publication of a bundle whose every value was resolved.
    """

    for name in ("topic-intake.md", "assignment-formal.md", "student-brief.md"):
        found = unresolved_values(read(TEMPLATES / name))
        assert not found, f"templates/{name} trips the marker in its own prose at lines {found}"
    doc = read(REPO_ROOT / "docs" / "assignment-authoring.md")
    fenced = [line for line in doc.splitlines() if line.startswith(("Identifier:", "- UNRESOLVED:"))]
    assert unresolved_values("\n".join(fenced)), "the doc must show a worked unresolved example"


def test_the_marker_rule_reads_the_value_position_only() -> None:
    assert unresolved_values("Identifier: UNRESOLVED: no DOI on the publisher page") == [
        (1, "no DOI on the publisher page")
    ]
    assert unresolved_values("- UNRESOLVED: academic year not confirmed") == [(1, "academic year not confirmed")]
    assert unresolved_values("UNRESOLVED: bare value") == [(1, "bare value")]
    assert unresolved_values("Use `UNRESOLVED:` when a value cannot be verified.") == []
    assert unresolved_values("Write `UNRESOLVED: <what is missing>` in place of the value.") == []
    assert unresolved_values("Identifier: 10.1109/RO-MAN.2019.8956307") == []


def test_the_operator_doc_declares_the_marker_as_a_publication_blocker() -> None:
    text = read(REPO_ROOT / "docs" / "assignment-authoring.md")
    assert UNRESOLVED_MARKER in text
    assert "publication blocker" in text
    assert "value position" in flat(text), "the doc must state the bounded rule, not just the token"
    assert "metadata::UNRESOLVED_VALUE_RE" in flat(text), "the doc must point at the single instrument"
    assert "TODO:" in text, "the doc must separate the unresolved marker from ordinary TODO slots"


def test_case_notes_template_offers_every_accepted_case_kind() -> None:
    text = read(TEMPLATES / "case-notes.md")
    line = next(line for line in text.splitlines() if line.startswith("Case kind:"))
    offered = [value.strip() for value in line.removeprefix("Case kind:").split("/")]
    assert offered == list(CASE_KINDS), "templates/case-notes.md and metadata::CASE_KINDS disagree"


def test_case_kind_defaults_and_rejects_unknown_values() -> None:
    assert DEFAULT_CASE_KIND == "thesis-review"
    assert case_kind({}) == DEFAULT_CASE_KIND
    assert case_kind({"case kind": ""}) == DEFAULT_CASE_KIND
    assert case_kind({"case kind": "Topic-Proposal"}) == "topic-proposal"
    assert case_kind({"case kind": "thesis-review"}) == "thesis-review"
    assert case_kind({"case kind": "assignment"}) is None


def test_reviewer_profile_template_offers_the_authoring_style_section() -> None:
    text = read(TEMPLATES / "reviewer-profile.md")
    assert AUTHORING_STYLE_HEADING in text
    section = text.split(AUTHORING_STYLE_HEADING, 1)[1].split("\n## ", 1)[0]
    assert "layer 3" in section
    assert "Supervision conventions" in section


def test_default_profile_carries_the_generic_base_including_open_solution_space() -> None:
    text = read(REPO_ROOT / "profiles" / "default.md")
    assert AUTHORING_STYLE_HEADING in text
    section = text.split(AUTHORING_STYLE_HEADING, 1)[1].split("\n## ", 1)[0]
    assert "imperative second-person plural" in flat(section)
    assert "presentation deliverable" in section
    assert "does not distinguish BP from" in flat(section)
    assert "must not push an open point toward specifying" in flat(section)
    assert "no stated criterion" in section


def test_default_profile_keeps_layer_three_out_of_the_tracked_base() -> None:
    """Supervision conventions are supervisor properties, not institutional norm."""

    section = (
        read(REPO_ROOT / "profiles" / "default.md")
        .split(AUTHORING_STYLE_HEADING, 1)[1]
        .split("\n## ", 1)[0]
        .lower()
    )
    for personal in ("reading order", "milestone", "commit hygiene", "responsiveness"):
        assert personal not in section, f"`{personal}` is layer 3 and must not be in profiles/default.md"


def test_profiles_readme_admits_the_section_and_excludes_field_values() -> None:
    text = read(REPO_ROOT / "profiles" / "README.md")
    assert "## Assignment Authoring Boundary" in text
    assert "Factual field values are not profile content." in flat(text)
