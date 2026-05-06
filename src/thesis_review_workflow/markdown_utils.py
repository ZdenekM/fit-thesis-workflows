"""Small Markdown parsing primitives for workflow validators."""

from __future__ import annotations

import re
from collections.abc import Callable


def section_body(lines: list[str], heading: str, *, stop_pattern: str = r"^#{1,2}\s+") -> list[str] | None:
    start = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index + 1
            break
    if start is None:
        return None

    end = len(lines)
    for index in range(start, len(lines)):
        if re.match(stop_pattern, lines[index]):
            end = index
            break
    return lines[start:end]


def section_text(lines: list[str], heading: str, *, stop_pattern: str = r"^#{1,2}\s+") -> str:
    body = section_body(lines, heading, stop_pattern=stop_pattern)
    return "\n".join(body or []).strip()


def markdown_section(text: str, heading: str, *, level: int = 2) -> str:
    marks = "#" * level
    pattern = re.compile(rf"(?ms)^{marks}\s+{re.escape(heading)}\s*$" rf"(.*?)(?=^{marks}\s+|\Z)")
    match = pattern.search(text)
    if not match:
        return ""
    return match.group(1)


def numbered_section_text(text: str, number: int) -> str:
    pattern = re.compile(rf"^##\s+{number}\.\s+.*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    next_match = re.search(r"^##\s+\d+\.\s+.*$", text[match.end() :], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(text)
    return text[match.end() : end].strip()


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    in_code = False

    for char in stripped:
        if char == "\\" and not escaped:
            current.append(char)
            escaped = True
            continue
        if char == "`" and not escaped:
            in_code = not in_code
        if char == "|" and not escaped and not in_code:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        escaped = False

    cells.append("".join(current).strip())
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return cells


def is_delimiter_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def extract_table(
    body: list[str],
    *,
    normalize_header: Callable[[str], str] = str,
    min_table_lines: int = 2,
) -> tuple[list[str], list[list[str]], str | None]:
    table_lines = [line for line in body if line.strip().startswith("|")]
    if len(table_lines) < min_table_lines:
        return [], [], "missing Markdown table"

    rows = [split_table_row(line) for line in table_lines]
    header_index = None
    for index, cells in enumerate(rows):
        if index + 1 < len(rows) and is_delimiter_row(rows[index + 1]):
            header_index = index
            break
    if header_index is None:
        return [], [], "missing Markdown delimiter row"

    headers = [normalize_header(cell) for cell in rows[header_index]]
    data_rows = [row for row in rows[header_index + 2 :] if row and not is_delimiter_row(row)]
    return headers, data_rows, None


def simple_table_rows(section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) >= 2:
            rows.append(cells)
    return rows
