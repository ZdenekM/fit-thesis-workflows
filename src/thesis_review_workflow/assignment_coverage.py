"""Advisory assignment coverage map for opponent review."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = "assignment-coverage-map-v1"
ASSIGNMENT_REL = Path("notes/assignment.md")
MATERIALS_REL = Path("outputs/oponent_podklady_revidovane.md")
DRAFT_REL = Path("work/oponent_posudek_draft.md")


@dataclass(frozen=True)
class AssignmentPoint:
    point_id: str
    text: str
    source_section: str


def normalized(value: str) -> str:
    replacements = str.maketrans("ěščřžýáíéúůňťďóĚŠČŘŽÝÁÍÉÚŮŇŤĎÓ", "escrzyaieuuntdoESCRZYAIEUUNTDO")
    value = value.translate(replacements).lower()
    return re.sub(r"\s+", " ", value).strip()


def section_lines(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    expected = normalized(heading.removeprefix("## "))
    start = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## ") and normalized(stripped.removeprefix("## ")) == expected:
            start = index + 1
            break
    if start is None:
        return []
    body: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        body.append(line)
    return body


def useful_line(line: str) -> str:
    stripped = line.strip()
    stripped = re.sub(r"^[-*]\s+", "", stripped)
    stripped = re.sub(r"^\d+[.)]\s+", "", stripped)
    return stripped.strip()


def is_placeholder(value: str) -> bool:
    lowered = normalized(value)
    return not lowered or lowered in {"todo", "none", "-", "n/a"} or lowered.startswith("todo:")


def parse_assignment_points(assignment_text: str) -> list[AssignmentPoint]:
    candidates: list[tuple[str, str]] = []
    for heading in ("## Formal Assignment Text Or Summary", "## Assignment Coverage Hints"):
        for line in section_lines(assignment_text, heading):
            item = useful_line(line)
            if not is_placeholder(item):
                candidates.append((heading.removeprefix("## "), item))
    points: list[AssignmentPoint] = []
    seen: set[str] = set()
    for source, item in candidates:
        key = normalized(item)
        if key in seen:
            continue
        seen.add(key)
        points.append(AssignmentPoint(f"A{len(points) + 1}", item, source))
    return points


def parser_limitations(assignment_source_present: bool, points: list[AssignmentPoint]) -> list[str]:
    if not assignment_source_present:
        return ["notes/assignment.md is missing; assignment coverage could not be parsed."]
    if not points:
        return [
            "No assignment points were parsed from Formal Assignment Text Or Summary " "or Assignment Coverage Hints."
        ]
    return []


def coverage_state(point: AssignmentPoint, text: str) -> tuple[str, list[str]]:
    if not text.strip():
        return "not_available", []
    norm_text = normalized(text)
    tokens = [token for token in re.findall(r"[a-zA-Z0-9_]+", normalized(point.text)) if len(token) >= 4]
    unique = sorted(set(tokens))
    hits = [token for token in unique if token in norm_text]
    if len(hits) >= min(3, max(1, len(unique))):
        return "mentioned", hits[:8]
    if hits:
        return "partial", hits[:8]
    return "not_found", []


def build_map(case_id: str, round_id: str, generated_at: str, round_dir: Path) -> dict[str, object]:
    assignment_path = round_dir / ASSIGNMENT_REL
    assignment_source_present = assignment_path.is_file()
    assignment_text = assignment_path.read_text(encoding="utf-8") if assignment_source_present else ""
    materials_text = (
        (round_dir / MATERIALS_REL).read_text(encoding="utf-8") if (round_dir / MATERIALS_REL).is_file() else ""
    )
    draft_text = (round_dir / DRAFT_REL).read_text(encoding="utf-8") if (round_dir / DRAFT_REL).is_file() else ""
    points = parse_assignment_points(assignment_text)
    rows = []
    for point in points:
        materials_state, materials_hits = coverage_state(point, materials_text)
        draft_state, draft_hits = coverage_state(point, draft_text)
        rows.append(
            {
                "point_id": point.point_id,
                "text": point.text,
                "source_section": point.source_section,
                "opponent_materials": {"state": materials_state, "matched_terms": materials_hits},
                "opponent_report_draft": {"state": draft_state, "matched_terms": draft_hits},
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "round_id": round_id,
        "generated_at": generated_at,
        "assignment_source": ASSIGNMENT_REL.as_posix(),
        "assignment_source_present": assignment_source_present,
        "advisory": True,
        "parser_limitations": parser_limitations(assignment_source_present, points),
        "assignment_points": rows,
    }


def write_artifact(path: Path, artifact: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
