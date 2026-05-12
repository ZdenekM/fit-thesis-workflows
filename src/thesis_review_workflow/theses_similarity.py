"""Structural Theses.cz similarity-report parsing contracts."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

THESES_SIMILARITY_INTAKE_SCHEMA = "theses-similarity-intake-v1"
THESES_SIMILARITY_ASSESSMENT_SCHEMA = "theses-similarity-assessment-v1"
THESES_SIMILARITY_ASSESSMENT_REL = "work/theses_similarity/assessment.json"
THESES_SIMILARITY_INTAKE_REL = "work/theses_similarity/intake.json"
THESES_SIMILARITY_REVIEW_DRAFT_REL = "work/theses_similarity/review_draft.md"
THESES_SIMILARITY_REVIEW_REL = "outputs/theses_similarity_review.md"

CURRENT_SUBMISSION_LINK_STATUSES = {"matched", "unverified", "mismatched"}
CURRENT_SUBMISSION_MATCH_STATUSES = {"matched", "unverified", "mismatched"}
SIMILARITY_JUDGMENT_CATEGORIES = {
    "no_material_concern",
    "self_revision_overlap_expected",
    "self_revision_overlap_unverified",
    "external_match_needs_review",
    "external_match_resolved_as_standard_or_common_material",
    "external_match_resolved_as_cited_and_proportionate",
    "external_match_cited_but_still_needs_review",
    "external_match_unresolved",
    "report_unusable_or_incomplete",
}
SIMILARITY_SYNTHESIS_ACTIONS = {"silent", "surface", "manual_check"}
SIMILARITY_CONFIDENCE_VALUES = {"low", "medium", "high"}
SIMILARITY_UNRESOLVED_CATEGORIES = {
    "self_revision_overlap_unverified",
    "external_match_needs_review",
    "external_match_cited_but_still_needs_review",
    "external_match_unresolved",
    "report_unusable_or_incomplete",
}

REPORT_EVALUATED_RE = re.compile(r"\bvyhodnoceno:\s*(?P<value>.+)$", re.IGNORECASE)
SIMILARITY_RE = re.compile(r"^Podobnost\s+(?P<value><\s*1|[0-9]+(?:[.,][0-9]+)?)\s*%$")
SOURCE_INDEX_RE = re.compile(r"^(?P<rank>[0-9]+)\.$")
MARKER_LINE_RE = re.compile(r"^\s*(?P<ids>[0-9]+(?:\s+[0-9]+)*)\s*$")
URL_TOKEN_RE = re.compile(r"^(https?://|//|/id/|www\.)", re.IGNORECASE)


@dataclass(frozen=True)
class SimilarityValue:
    raw: str
    numeric_value: float | None
    less_than: float | None


@dataclass(frozen=True)
class SourceDocument:
    rank: int
    source_type: str
    title: str
    url_text: str
    changed_or_downloaded_text: str
    word_count_text: str
    similarity: SimilarityValue
    report_line_start: int
    report_line_end: int
    raw_lines: tuple[str, ...]


@dataclass(frozen=True)
class MatchedPassage:
    passage_id: str
    source_ids: tuple[int, ...]
    report_line: int
    report_page: int | None
    checked_document_ref: str
    extraction_limitations: tuple[str, ...]


def parse_similarity_value(raw: str) -> SimilarityValue:
    value = raw.strip().replace(",", ".")
    if value.startswith("<"):
        numeric = value[1:].strip()
        return SimilarityValue(raw=raw.strip(), numeric_value=None, less_than=float(numeric))
    return SimilarityValue(raw=raw.strip(), numeric_value=float(value), less_than=None)


def parse_report_text(text: str) -> dict[str, Any]:
    lines = _normalized_lines(text)
    source_section_start = _find_line_containing(lines, "Zdrojové dokumenty")
    passage_section_start = _find_line_containing(lines, "Vyznačení podobností")
    source_section_end = passage_section_start if passage_section_start is not None else len(lines)
    overall_similarity = _first_similarity(lines[: source_section_start or len(lines)])
    source_documents = _parse_source_documents(lines, source_section_start, source_section_end)
    source_ranks = {item.rank for item in source_documents}
    return {
        "report_evaluated_at_text": _first_evaluated_at(lines),
        "compared_document": _compared_document(lines, source_section_start),
        "overall_similarity": asdict(overall_similarity) if overall_similarity else None,
        "source_documents": [_source_document_to_json(item) for item in source_documents],
        "matched_passages": [
            asdict(item) for item in _parse_matched_passages(lines, passage_section_start, source_ranks)
        ],
        "parser": {
            "parser_name": "theses_similarity.parse_report_text",
            "template": "theses.cz similarity report",
            "confidence": "structural",
            "limitations": [
                "Parser extracts bounded report labels and anchors only; "
                "it does not evaluate misconduct, authorship, or quality.",
            ],
        },
    }


def build_intake_payload(
    *,
    case_id: str,
    round_id: str,
    generated_at: str,
    report_pdf_path: str,
    report_pdf_sha256: str,
    extracted_text_path: str,
    extracted_text_sha256: str,
    report_text: str,
    page_count: int | None,
    current_submission_link: str = "unverified",
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    if current_submission_link not in CURRENT_SUBMISSION_LINK_STATUSES:
        raise ValueError("current_submission_link must be matched, unverified, or mismatched")
    parsed = parse_report_text(report_text)
    return {
        "schema_version": THESES_SIMILARITY_INTAKE_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "generated_at": generated_at,
        "producer_type": "deterministic_helper",
        "producer_role": "import-theses-report",
        "producer_agent": "import-theses-report",
        "source_refs": [report_pdf_path, extracted_text_path],
        "limitations": limitations or [],
        "report_pdf": {
            "path": report_pdf_path,
            "sha256": report_pdf_sha256,
            "page_count": page_count,
        },
        "extracted_text": {
            "path": extracted_text_path,
            "sha256": extracted_text_sha256,
            "extractor": "pdftotext -layout",
        },
        "current_submission_link": current_submission_link,
        **parsed,
    }


def _normalized_lines(text: str) -> list[tuple[int, int, str]]:
    lines: list[tuple[int, int, str]] = []
    page = 1
    for index, raw in enumerate(text.splitlines(), start=1):
        if "\f" in raw:
            parts = raw.split("\f")
            for part_index, part in enumerate(parts):
                line = part.strip()
                if line:
                    lines.append((index, page, line))
                if part_index < len(parts) - 1:
                    page += 1
            continue
        line = raw.strip()
        if line:
            lines.append((index, page, line))
    return lines


def _find_line_containing(lines: list[tuple[int, int, str]], needle: str) -> int | None:
    for index, (_, _, line) in enumerate(lines):
        if needle in line:
            return index
    return None


def _first_similarity(lines: list[tuple[int, int, str]]) -> SimilarityValue | None:
    for _, _, line in lines:
        match = SIMILARITY_RE.match(line)
        if match:
            return parse_similarity_value(match.group("value"))
    return None


def _first_evaluated_at(lines: list[tuple[int, int, str]]) -> str:
    for _, _, line in lines:
        match = REPORT_EVALUATED_RE.search(line)
        if match:
            return match.group("value").strip()
    return ""


def _compared_document(lines: list[tuple[int, int, str]], end: int | None) -> dict[str, Any]:
    start = _find_line_containing(lines, "Porovnávaný dokument")
    if start is None:
        return {"raw_lines": [], "report_line_start": None, "report_line_end": None}
    limit = end if end is not None else len(lines)
    raw_lines: list[str] = []
    line_start = None
    line_end = None
    for line_number, _, line in lines[start + 1 : limit]:
        if REPORT_EVALUATED_RE.search(line) or SIMILARITY_RE.match(line):
            break
        raw_lines.append(line)
        line_start = line_number if line_start is None else line_start
        line_end = line_number
    return {
        "raw_lines": raw_lines,
        "report_line_start": line_start,
        "report_line_end": line_end,
    }


def _parse_source_documents(
    lines: list[tuple[int, int, str]],
    start: int | None,
    end: int,
) -> list[SourceDocument]:
    if start is None:
        return []
    entries: list[SourceDocument] = []
    current_rank: int | None = None
    current_start = 0
    current_lines: list[tuple[int, int, str]] = []
    for line_number, page, line in lines[start + 1 : end]:
        match = SOURCE_INDEX_RE.match(line)
        if match:
            if current_rank is not None and current_lines:
                entries.append(_source_document_from_lines(current_rank, current_start, current_lines))
            current_rank = int(match.group("rank"))
            current_start = line_number
            current_lines = []
            continue
        if current_rank is not None:
            current_lines.append((line_number, page, line))
    if current_rank is not None and current_lines:
        entries.append(_source_document_from_lines(current_rank, current_start, current_lines))
    return entries


def _source_document_from_lines(
    rank: int,
    line_start: int,
    lines: list[tuple[int, int, str]],
) -> SourceDocument:
    raw_lines = [line for _, _, line in lines]
    similarity_index = next((i for i, line in enumerate(raw_lines) if SIMILARITY_RE.match(line)), None)
    content = raw_lines[:similarity_index] if similarity_index is not None else raw_lines
    similarity_match = SIMILARITY_RE.match(raw_lines[similarity_index]) if similarity_index is not None else None
    similarity = (
        parse_similarity_value(similarity_match.group("value"))
        if similarity_match is not None
        else SimilarityValue(raw="", numeric_value=None, less_than=None)
    )
    source_type = content[0] if content else ""
    url_index = next((i for i, line in enumerate(content) if URL_TOKEN_RE.match(line)), None)
    title_lines = content[1:url_index] if url_index is not None else content[1:]
    url_lines: list[str] = []
    if url_index is not None:
        for line in content[url_index:]:
            if line.startswith(("Změněno", "Staženo")):
                break
            url_lines.append(line)
    changed_or_downloaded = next(
        (line for line in content if line.startswith(("Změněno", "Staženo"))),
        "",
    )
    return SourceDocument(
        rank=rank,
        source_type=source_type,
        title=" ".join(title_lines).strip(),
        url_text="".join(url_lines).strip(),
        changed_or_downloaded_text=changed_or_downloaded,
        word_count_text=_word_count_text(changed_or_downloaded),
        similarity=similarity,
        report_line_start=line_start,
        report_line_end=lines[-1][0] if lines else line_start,
        raw_lines=tuple(raw_lines),
    )


def _source_document_to_json(item: SourceDocument) -> dict[str, Any]:
    return {
        "rank": item.rank,
        "source_type": item.source_type,
        "title": item.title,
        "url_text": item.url_text,
        "changed_or_downloaded_text": item.changed_or_downloaded_text,
        "word_count_text": item.word_count_text,
        "similarity": asdict(item.similarity),
        "report_line_start": item.report_line_start,
        "report_line_end": item.report_line_end,
        "raw_lines": list(item.raw_lines),
    }


def _word_count_text(value: str) -> str:
    if "," not in value:
        return ""
    return value.rsplit(",", 1)[-1].strip()


def _parse_matched_passages(
    lines: list[tuple[int, int, str]],
    start: int | None,
    source_ranks: set[int],
) -> list[MatchedPassage]:
    if start is None:
        return []
    passages: list[MatchedPassage] = []
    for line_number, page, line in lines[start + 1 :]:
        match = MARKER_LINE_RE.match(line)
        if not match:
            continue
        source_ids = tuple(int(value) for value in match.group("ids").split())
        if not source_ids:
            continue
        if not set(source_ids).issubset(source_ranks):
            continue
        passages.append(
            MatchedPassage(
                passage_id=f"passage-{len(passages) + 1}",
                source_ids=source_ids,
                report_line=line_number,
                report_page=page,
                checked_document_ref="unavailable",
                extraction_limitations=("pdftotext marker line gives source IDs but not a stable rendered text span",),
            )
        )
    return passages
