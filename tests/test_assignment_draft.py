"""Contract tests for the structural assignment draft checker.

Synthetic topic cases only: the checker's job is to decide what needs no
judgment, so every case here is built to isolate one rule.
"""

from pathlib import Path

import pytest

from thesis_review_workflow.assignment_draft import RENDERINGS
from thesis_review_workflow.cli import check_assignment_draft

INTAKE = """# Topic Intake

Topic id: t
Academic year: 2026/27
Variants: bp / dp

## Citable Artifacts

- Reference: Example, A. Provenance. Journal, 2026.
  Identifier: 10.0000/example
  Kind: doi

Supplement line: Dale dle pokynu vedouciho.
"""

BRIEF_BODY = """### What The Work Builds On

An existing platform.

### Where To Start

Start from the README.

### Working Agreements

Weekly handover.

### How To Read The Assignment

The domain choice is yours; the criteria are not.

### What Is Out Of Scope

The mobile client."""

BRIEF_SOURCE = f"""# Student Brief

## Shared Brief

{BRIEF_BODY}

## Variant Delta

### bp

Contribution framing: prototype.

### dp

Contribution framing: prototype plus comparison.
"""


def assignment(*, variant: str = "bp", literature: str = "- Example, A. Provenance. Journal, 2026.") -> str:
    title = RENDERINGS["cs"].titles[variant]
    # `Specializace:` is the diplomová práce field, so a dp fixture must carry it.
    specialization = "Specializace:\n" if variant == "dp" else ""
    return f"""# Formal Assignment

Topic id: t
Variant: {variant}
Rendering: cs

## Czech Rendering

### Header

{title}

### Metadata

Ústav: UPGM
Student:
Program:
{specialization}Název: Téma
Kategorie: Softwarové inženýrství
Akademický rok: 2026/27

### Assignment Points

Zadání:

1. Proveďte rešerši.

### Literature

Literatura:

{literature}

### Semestral Defence Requirement

Při obhajobě semestrální části projektu je požadováno: Bod 1.

### Footer

Vedoucí práce: T
Vedoucí ústavu: T
Datum zadání:
Termín pro odevzdání:
Datum schválení:
"""


def projection(variant: str) -> str:
    delta = "prototype." if variant == "bp" else "prototype plus comparison."
    return f"""# Thesis Topic Brief - {variant}

{BRIEF_BODY}

## For This Variant - {variant}

Contribution framing: {delta}
"""


@pytest.fixture
def topic_case(tmp_path: Path) -> Path:
    case_dir = tmp_path / "topic-case"
    (case_dir / "notes").mkdir(parents=True)
    (case_dir / "outputs").mkdir()
    (case_dir / "case.md").write_text(
        "Case ID: t\nCase kind: topic-proposal\nStudent feedback language: en\n", encoding="utf-8"
    )
    (case_dir / "notes/topic_intake.md").write_text(INTAKE, encoding="utf-8")
    (case_dir / "notes/student_brief.md").write_text(BRIEF_SOURCE, encoding="utf-8")
    for variant in ("bp", "dp"):
        (case_dir / f"outputs/assignment_formal_{variant}.md").write_text(assignment(variant=variant), encoding="utf-8")
        (case_dir / f"outputs/student_brief_{variant}.md").write_text(projection(variant), encoding="utf-8")
    return case_dir


def check(case_dir: Path, variant: str | None = None) -> list[str]:
    findings, _ = check_assignment_draft.check_case(case_dir, variant)
    return findings


def test_a_complete_bundle_passes(topic_case: Path) -> None:
    assert check(topic_case) == []


def test_a_thesis_review_case_is_refused(topic_case: Path) -> None:
    (topic_case / "case.md").write_text("Case ID: t\n", encoding="utf-8")
    findings = check(topic_case)
    assert any("topic-proposal" in finding for finding in findings)


def test_an_unknown_case_kind_is_refused(topic_case: Path) -> None:
    (topic_case / "case.md").write_text("Case ID: t\nCase kind: assignment\n", encoding="utf-8")
    assert any("not a known kind" in finding for finding in check(topic_case))


def test_an_undeclared_variant_is_refused(topic_case: Path) -> None:
    assert any("is not declared" in finding for finding in check(topic_case, "mgr"))


def test_empty_literature_fails(topic_case: Path) -> None:
    (topic_case / "outputs/assignment_formal_bp.md").write_text(assignment(literature=""), encoding="utf-8")
    assert any("no literature entry sourced from the intake" in finding for finding in check(topic_case, "bp"))


def test_supplement_only_literature_fails(topic_case: Path) -> None:
    (topic_case / "outputs/assignment_formal_bp.md").write_text(
        assignment(literature="- Dale dle pokynu vedouciho."), encoding="utf-8"
    )
    assert any("no literature entry sourced from the intake" in finding for finding in check(topic_case, "bp"))


def test_a_literature_entry_absent_from_the_intake_fails(topic_case: Path) -> None:
    (topic_case / "outputs/assignment_formal_bp.md").write_text(
        assignment(literature="- Someone, B. Invented Work. 2026."), encoding="utf-8"
    )
    findings = check(topic_case, "bp")
    assert any("not authored in the intake" in finding for finding in findings)


def test_a_literature_wording_placeholder_is_not_special_cased(topic_case: Path) -> None:
    """`AGENTS.md` forbids a free-text gate: a placeholder fails as unsourced, not as a phrase."""

    (topic_case / "outputs/assignment_formal_bp.md").write_text(
        assignment(literature="- Bude doplněno."), encoding="utf-8"
    )
    findings = check(topic_case, "bp")
    assert any("not authored in the intake" in finding for finding in findings)
    assert not any("placeholder" in finding.lower() for finding in findings)


def test_an_unresolved_identifier_fails(topic_case: Path) -> None:
    (topic_case / "notes/topic_intake.md").write_text(
        INTAKE.replace("Identifier: 10.0000/example", "Identifier: UNRESOLVED: no DOI found"), encoding="utf-8"
    )
    findings = check(topic_case, "bp")
    assert any("unresolved value blocks publication" in finding for finding in findings)


def test_a_variant_may_legitimately_cite_more_than_another(topic_case: Path) -> None:
    """Provenance already forces exact equality wherever an entry is used.

    An earlier version required identical MEMBERSHIP across variants and
    rejected a DP citing one work more than its BP.
    """

    intake = INTAKE.replace(
        "Supplement line:",
        "- Reference: Second, C. Extra Work. 2026.\n  Identifier: 10.0000/second\n  Kind: doi\n\nSupplement line:",
    )
    (topic_case / "notes/topic_intake.md").write_text(intake, encoding="utf-8")
    (topic_case / "outputs/assignment_formal_dp.md").write_text(
        assignment(
            variant="dp",
            literature="- Example, A. Provenance. Journal, 2026.\n- Second, C. Extra Work. 2026.",
        ),
        encoding="utf-8",
    )
    assert check(topic_case) == []


def test_an_unaccounted_literature_line_fails(topic_case: Path) -> None:
    """A plain line after a valid citation used to pass, because only bullets were read."""

    (topic_case / "outputs/assignment_formal_bp.md").write_text(
        assignment(literature="- Example, A. Provenance. Journal, 2026.\nInvented, D. Not A Bullet. 2026."),
        encoding="utf-8",
    )
    assert any("neither a bullet nor a continuation" in finding for finding in check(topic_case, "bp"))


def test_a_wrapped_literature_entry_is_one_entry(topic_case: Path) -> None:
    intake = INTAKE.replace(
        "Reference: Example, A. Provenance. Journal, 2026.",
        "Reference: Example, A. Provenance In Depth And At Length. Journal Of Long Titles, 2026.",
    )
    (topic_case / "notes/topic_intake.md").write_text(intake, encoding="utf-8")
    (topic_case / "outputs/assignment_formal_bp.md").write_text(
        assignment(literature="- Example, A. Provenance In Depth And At Length.\n  Journal Of Long Titles, 2026."),
        encoding="utf-8",
    )
    assert check(topic_case, "bp") == []


def test_two_blocks_of_the_same_rendering_fail(topic_case: Path) -> None:
    text = assignment() + "\n## Czech Rendering\n\n### Metadata\n\nÚstav: UPGM\n"
    (topic_case / "outputs/assignment_formal_bp.md").write_text(text, encoding="utf-8")
    assert any("exactly one rendering block" in finding for finding in check(topic_case, "bp"))


def test_a_missing_footer_fails(topic_case: Path) -> None:
    text = assignment()
    text = text[: text.index("Vedoucí práce:")]
    (topic_case / "outputs/assignment_formal_bp.md").write_text(text, encoding="utf-8")
    assert any("`Vedoucí práce:` is missing" in finding for finding in check(topic_case, "bp"))


def test_a_numbered_footer_note_is_not_an_assignment_point(topic_case: Path) -> None:
    """Points were counted across the whole rendering, so a numbered note elsewhere sufficed."""

    text = assignment().replace("1. Proveďte rešerši.\n", "")
    text = text.replace("Datum schválení:", "Datum schválení:\n\n1. Poznámka.")
    (topic_case / "outputs/assignment_formal_bp.md").write_text(text, encoding="utf-8")
    assert any("no numbered assignment point" in finding for finding in check(topic_case, "bp"))


def test_an_unusable_variant_identifier_is_refused(topic_case: Path) -> None:
    """A variant becomes a filename segment, so it is validated rather than trusted."""

    (topic_case / "notes/topic_intake.md").write_text(
        INTAKE.replace("Variants: bp / dp", "Variants: bp / ../../escape"), encoding="utf-8"
    )
    assert any("unusable variant identifier" in finding for finding in check(topic_case))


def test_a_drifted_brief_projection_fails(topic_case: Path) -> None:
    (topic_case / "outputs/student_brief_bp.md").write_text(
        projection("bp").replace("Start from the README.", "Start from the docs."), encoding="utf-8"
    )
    assert any("not exactly the shared brief body" in finding for finding in check(topic_case, "bp"))


def test_an_obligation_appended_to_a_projection_fails(topic_case: Path) -> None:
    """A substring check passed this: the shared body and the delta were both still present."""

    (topic_case / "outputs/student_brief_bp.md").write_text(
        projection("bp") + "\nAlso deliver a second prototype.\n", encoding="utf-8"
    )
    assert any("not exactly the shared brief body" in finding for finding in check(topic_case, "bp"))


def test_a_delta_that_contains_another_variants_delta_as_a_prefix_passes(topic_case: Path) -> None:
    """A substring check rejected this legitimate case."""

    source = BRIEF_SOURCE.replace(
        "Contribution framing: prototype plus comparison.",
        "Contribution framing: prototype.\n\nPlus a comparison against one baseline.",
    )
    (topic_case / "notes/student_brief.md").write_text(source, encoding="utf-8")
    (topic_case / "outputs/student_brief_dp.md").write_text(
        f"""# Thesis Topic Brief - dp

{BRIEF_BODY}

## For This Variant - dp

Contribution framing: prototype.

Plus a comparison against one baseline.
""",
        encoding="utf-8",
    )
    assert check(topic_case, "dp") == []


def test_a_projection_without_its_delta_heading_fails(topic_case: Path) -> None:
    (topic_case / "outputs/student_brief_bp.md").write_text(
        projection("bp").replace("## For This Variant - bp\n\n", ""), encoding="utf-8"
    )
    assert any("canonical shape" in finding for finding in check(topic_case, "bp"))


def test_a_missing_semestral_requirement_fails(topic_case: Path) -> None:
    text = assignment().replace(
        "Při obhajobě semestrální části projektu je požadováno: Bod 1.",
        "Při obhajobě semestrální části projektu je požadováno:",
    )
    (topic_case / "outputs/assignment_formal_bp.md").write_text(text, encoding="utf-8")
    assert any("is empty" in finding for finding in check(topic_case, "bp"))


def test_two_rendering_blocks_fail(topic_case: Path) -> None:
    text = assignment() + "\n## English Rendering\n\n### Metadata\n\nInstitut: DCGM\n"
    (topic_case / "outputs/assignment_formal_bp.md").write_text(text, encoding="utf-8")
    assert any("exactly one rendering block" in finding for finding in check(topic_case, "bp"))


def test_a_declared_rendering_that_does_not_match_the_kept_block_fails(topic_case: Path) -> None:
    text = assignment().replace("Rendering: cs", "Rendering: en")
    (topic_case / "outputs/assignment_formal_bp.md").write_text(text, encoding="utf-8")
    assert any("does not match the kept block" in finding for finding in check(topic_case, "bp"))


def test_out_of_order_metadata_fails(topic_case: Path) -> None:
    text = assignment().replace(
        "Název: Téma\nKategorie: Softwarové inženýrství", "Kategorie: Softwarové inženýrství\nNázev: Téma"
    )
    (topic_case / "outputs/assignment_formal_bp.md").write_text(text, encoding="utf-8")
    assert any("not in the FIT IS field order" in finding for finding in check(topic_case, "bp"))


def test_a_bachelor_variant_may_omit_the_specialization_field(topic_case: Path) -> None:
    """`Specializace:` is a diplomová práce field; a BP without it is not a defect."""

    assert "Specializace:" not in assignment()
    assert check(topic_case, "bp") == []


def test_a_master_variant_without_the_specialization_field_fails(topic_case: Path) -> None:
    """The real dp bundle shipped without it and passed: optional for BOTH was the defect."""

    assert "Specializace:" in assignment(variant="dp")
    (topic_case / "outputs/assignment_formal_dp.md").write_text(
        assignment(variant="dp").replace("Specializace:\n", ""), encoding="utf-8"
    )
    findings = check(topic_case, "dp")
    assert any("`Specializace:` is missing" in finding for finding in findings), findings
    assert any("diplomová práce" in finding for finding in findings)


def test_point_count_is_never_read_as_work_type_or_scope_evidence(topic_case: Path) -> None:
    text = assignment().replace("1. Proveďte rešerši.", "\n".join(f"{n}. Bod {n}." for n in range(1, 12)))
    (topic_case / "outputs/assignment_formal_bp.md").write_text(text, encoding="utf-8")
    assert check(topic_case, "bp") == []


def test_an_obligation_written_into_the_projection_title_fails(topic_case: Path) -> None:
    """Comparing only the designated bodies left the title line unchecked."""

    (topic_case / "outputs/student_brief_bp.md").write_text(
        projection("bp").replace("# Thesis Topic Brief - bp", "# Also deliver a second prototype."), encoding="utf-8"
    )
    assert any("canonical shape" in finding for finding in check(topic_case, "bp"))


def test_inline_text_on_the_literature_label_fails(topic_case: Path) -> None:
    (topic_case / "outputs/assignment_formal_bp.md").write_text(
        assignment().replace("Literatura:\n", "Literatura: Invented, D. Inline Citation. 2026.\n"), encoding="utf-8"
    )
    assert any("carries inline text" in finding for finding in check(topic_case, "bp"))


def test_a_deeper_heading_cannot_hide_unsourced_literature(topic_case: Path) -> None:
    """Stopping the scan at the first `#` let a nested heading shelter citations."""

    (topic_case / "outputs/assignment_formal_bp.md").write_text(
        assignment(
            literature="- Example, A. Provenance. Journal, 2026.\n\n#### Additional reading\n\n- Ghost, E. Unsourced. 2026."
        ),
        encoding="utf-8",
    )
    findings = check(topic_case, "bp")
    assert any("Ghost, E. Unsourced. 2026." in finding for finding in findings)


CZECH_BRIEF_BODY = """### Na čem práce staví

Existující platforma.

### Kde začít

Začněte od README.

### Jak budeme spolupracovat

Týdenní předávka.

### Jak číst zadání

Volba domény je na vás, kritéria nikoli.

### Co do práce nepatří

Mobilní klient."""


def czech_bundle(case_dir: Path) -> None:
    (case_dir / "case.md").write_text(
        "Case ID: t\nCase kind: topic-proposal\nStudent feedback language: cs\n", encoding="utf-8"
    )
    (case_dir / "notes/student_brief.md").write_text(
        f"""# Student Brief

## Shared Brief

{CZECH_BRIEF_BODY}

## Variant Delta

### bp

Přínos: prototyp.

### dp

Přínos: prototyp a srovnání.
""",
        encoding="utf-8",
    )
    for variant, delta in (("bp", "prototyp."), ("dp", "prototyp a srovnání.")):
        (case_dir / f"outputs/student_brief_{variant}.md").write_text(
            f"""# Úvodní podklad k tématu - {variant}

{CZECH_BRIEF_BODY}

## Specifika varianty - {variant}

Přínos: {delta}
""",
            encoding="utf-8",
        )


def test_a_czech_bundle_passes(topic_case: Path) -> None:
    czech_bundle(topic_case)
    assert check(topic_case) == []


def test_english_headings_in_a_czech_case_fail(topic_case: Path) -> None:
    czech_bundle(topic_case)
    source = (topic_case / "notes/student_brief.md").read_text(encoding="utf-8")
    (topic_case / "notes/student_brief.md").write_text(
        source.replace("### Kde začít", "### Where To Start"), encoding="utf-8"
    )
    findings = check(topic_case, "bp")
    assert any("missing headings for the case feedback language" in finding for finding in findings)
    assert any("wrong language or spelling" in finding for finding in findings)


def test_a_czech_section_copied_into_an_english_projection_fails(topic_case: Path) -> None:
    """The opposite-language rule; the other two and the whole-document check all pass this."""

    (topic_case / "outputs/student_brief_bp.md").write_text(
        projection("bp").replace("### Where To Start", "### Kde začít"), encoding="utf-8"
    )
    assert any("wrong language or spelling" in finding for finding in check(topic_case, "bp"))


def test_ascii_folded_czech_headings_fail(topic_case: Path) -> None:
    czech_bundle(topic_case)
    source = (topic_case / "notes/student_brief.md").read_text(encoding="utf-8")
    (topic_case / "notes/student_brief.md").write_text(
        source.replace("### Kde začít", "### Kde zacit"), encoding="utf-8"
    )
    assert any("wrong language or spelling" in finding for finding in check(topic_case, "bp"))


def test_the_source_wrappers_are_not_required_of_a_projection(topic_case: Path) -> None:
    """The two artifacts have deliberately different shapes."""

    projection_text = (topic_case / "outputs/student_brief_bp.md").read_text(encoding="utf-8")
    assert "## Shared Brief" not in projection_text
    assert check(topic_case, "bp") == []


def test_an_unsupported_feedback_language_is_refused(topic_case: Path) -> None:
    (topic_case / "case.md").write_text(
        "Case ID: t\nCase kind: topic-proposal\nStudent feedback language: de\n", encoding="utf-8"
    )
    assert any("not a supported value" in finding for finding in check(topic_case))


def test_a_missing_feedback_language_defaults_to_czech(topic_case: Path) -> None:
    """`templates/case-notes.md` ships `Student feedback language: cs`."""

    czech_bundle(topic_case)
    (topic_case / "case.md").write_text("Case ID: t\nCase kind: topic-proposal\n", encoding="utf-8")
    assert check(topic_case) == []


def test_an_opposite_language_title_inside_a_shared_body_fails(topic_case: Path) -> None:
    """The exemption that kept the neutral wrappers safe used to let this through."""

    czech_bundle(topic_case)
    source = (topic_case / "notes/student_brief.md").read_text(encoding="utf-8")
    (topic_case / "notes/student_brief.md").write_text(
        source.replace("Mobilní klient.", "Mobilní klient.\n\n# Thesis Topic Brief"), encoding="utf-8"
    )
    assert any("wrong language or spelling" in finding for finding in check(topic_case, "bp"))


def test_an_ascii_folded_variant_qualified_title_fails(topic_case: Path) -> None:
    """`ascii_reject()` folded only bare forms, so the qualified spelling escaped."""

    czech_bundle(topic_case)
    text = (topic_case / "outputs/student_brief_bp.md").read_text(encoding="utf-8")
    (topic_case / "outputs/student_brief_bp.md").write_text(
        text.replace("Mobilní klient.", "Mobilní klient.\n\n# Uvodni podklad k tematu - bp"), encoding="utf-8"
    )
    assert any("wrong language or spelling" in finding for finding in check(topic_case, "bp"))


def test_the_neutral_source_wrappers_are_never_forbidden(topic_case: Path) -> None:
    czech_bundle(topic_case)
    source = (topic_case / "notes/student_brief.md").read_text(encoding="utf-8")
    assert source.startswith("# Student Brief")
    assert "## Shared Brief" in source and "## Variant Delta" in source
    assert check(topic_case) == []


def test_another_variants_qualified_heading_is_caught(topic_case: Path) -> None:
    """Enumerating exact forms per current variant left every other suffix open."""

    czech_bundle(topic_case)
    source = (topic_case / "notes/student_brief.md").read_text(encoding="utf-8")
    (topic_case / "notes/student_brief.md").write_text(
        source.replace("Mobilní klient.", "Mobilní klient.\n\n# Uvodni podklad k tematu - dp"), encoding="utf-8"
    )
    assert any("wrong language or spelling" in finding for finding in check(topic_case, "bp"))


def test_an_arbitrary_suffix_on_a_known_heading_base_is_caught(topic_case: Path) -> None:
    czech_bundle(topic_case)
    text = (topic_case / "outputs/student_brief_bp.md").read_text(encoding="utf-8")
    (topic_case / "outputs/student_brief_bp.md").write_text(
        text.replace("Mobilní klient.", "Mobilní klient.\n\n## Specifika varianty - old"), encoding="utf-8"
    )
    assert any("wrong language or spelling" in finding for finding in check(topic_case, "bp"))


def test_a_semestral_requirement_outside_its_section_fails(topic_case: Path) -> None:
    """Validation and promotion must read the same boundary.

    Searching the whole rendering let the field sit under `### Footer`, pass,
    be approved, and then be dropped by promotion — leaving the obligation in
    the approved assignment and out of the thesis case.
    """

    text = assignment()
    moved = "Při obhajobě semestrální části projektu je požadováno: Bod 1."
    text = text.replace(f"{moved}\n", "").replace("Vedoucí práce: T", f"{moved}\nVedoucí práce: T")
    (topic_case / "outputs/assignment_formal_bp.md").write_text(text, encoding="utf-8")
    assert any("outside `### Semestral Defence Requirement`" in finding for finding in check(topic_case, "bp"))
