from thesis_review_workflow.markdown_utils import (
    extract_table,
    is_delimiter_row,
    markdown_section,
    numbered_section_text,
    section_body,
    section_text,
    simple_table_rows,
    split_table_row,
)


def test_section_body_uses_configurable_heading_boundary() -> None:
    lines = [
        "## Target",
        "body",
        "### Nested",
        "nested body",
        "## Next",
        "outside",
    ]

    assert section_body(lines, "## Target") == ["body", "### Nested", "nested body"]
    assert section_body(lines, "## Target", stop_pattern=r"^#{1,6}\s+") == ["body"]
    assert section_text(lines, "## Missing") == ""


def test_markdown_section_and_numbered_section_extract_text_blocks() -> None:
    text = "\n".join(
        [
            "## Review Status",
            "approved",
            "with note",
            "## Student-Facing Synthesis",
            "summary",
            "## 6. Evidence",
            "ledger",
            "## 7. Strengths",
            "ok",
        ]
    )

    assert markdown_section(text, "Review Status") == "\napproved\nwith note\n"
    assert numbered_section_text(text, 6) == "ledger"
    assert numbered_section_text(text, 8) == ""


def test_split_table_row_respects_escaped_pipes_and_code_spans() -> None:
    row = r"| item | `a|b` | escaped \| pipe | tail |"

    assert split_table_row(row) == ["item", "`a|b`", r"escaped \| pipe", "tail"]


def test_extract_table_finds_header_delimiter_and_normalizes_headers() -> None:
    body = [
        "intro",
        "| Item | Evidence |",
        "| --- | :---: |",
        "| A | path/file.py:10 |",
        "| --- | --- |",
    ]

    headers, rows, error = extract_table(body, normalize_header=str.lower, min_table_lines=3)

    assert error is None
    assert headers == ["item", "evidence"]
    assert rows == [["A", "path/file.py:10"]]
    assert is_delimiter_row(["---", ":---:"])


def test_extract_table_reports_missing_table_and_delimiter() -> None:
    assert extract_table([], min_table_lines=1) == ([], [], "missing Markdown table")
    assert extract_table(["| A | B |", "| x | y |"], min_table_lines=1) == (
        [],
        [],
        "missing Markdown delimiter row",
    )


def test_simple_table_rows_preserves_legacy_dash_skip_behavior() -> None:
    section = "\n".join(
        [
            "| claim | support |",
            "| --- | --- |",
            "| keep | ok |",
            "| skip---legacy | value |",
        ]
    )

    assert simple_table_rows(section) == [["claim", "support"], ["keep", "ok"]]
