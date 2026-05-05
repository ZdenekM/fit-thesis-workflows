"""Validate figure/media review output and reusable visual inventory."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
SHA256_RE = re.compile(r"^[A-Fa-f0-9]{64}$")
KNOWN_STATUSES = {
    "inventoried_only",
    "pdf_inspected",
    "source_asset_checked",
    "not_available",
}
EVIDENCE_STATUSES = {"pdf_inspected", "source_asset_checked"}
CHANGE_STATUSES = {
    "added",
    "removed",
    "caption_changed",
    "visual_content_changed",
    "claim_alignment_changed",
    "unchanged",
    "not_comparable",
}
KNOWN_VISUAL_ANALYSIS_VERSIONS = {"figure-media-visual-v1"}
KNOWN_CLAIM_ALIGNMENT_VERSIONS = {"figure-media-claim-v1"}
KNOWN_VISUAL_REUSE_REASONS = {
    "matching_source_asset_sha256",
    "matching_rendered_crop_sha256",
}
KNOWN_TEXT_MENTION_ROLES = {
    "introduces",
    "interprets",
    "uses_as_evidence",
    "references_only",
}
KNOWN_CLAIM_ALIGNMENTS = {
    "supports",
    "partially_supports",
    "does_not_support",
    "not_verifiable",
}
EVIDENCE_CLAIM_ALIGNMENTS = {
    "supports",
    "partially_supports",
    "does_not_support",
}
REQUIRED_JSON_FIELDS = (
    "item_id",
    "type",
    "pdf_anchor",
    "caption_or_nearby_claim",
    "source_asset_path",
    "inspection_status",
    "visual_description",
    "limitations",
    "downstream_relevance",
)
REQUIRED_HEADINGS = (
    "# Figure/Media Review",
    "## Review Scope",
    "## Visual Inventory",
    "## Inspected Figures And Tables",
    "## Changes Since Previous Round",
    "## Context And Claim Alignment",
    "## Findings",
    "## Downstream Use",
    "## Review Status",
    "## Manual Checks",
)
PLACEHOLDER_RE = re.compile(
    r"(\bYYYY-MM-DD\b|\bTBD\b|\blorem ipsum\b|^\s*(?:[-*]\s*)?TODO\s*:)",
    re.IGNORECASE | re.MULTILINE,
)
ANGLE_PLACEHOLDER_RE = re.compile(r"<([^>\n]+)>")
AUTOLINK_RE = re.compile(
    r"(?:https?://|mailto:)[^\s<>]+|[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+",
    re.IGNORECASE,
)
VISUAL_CLAIM_RE = re.compile(
    r"\b("
    r"shows?|depicts?|displays?|visible|contains?|"
    r"ukazuje|zobrazuje|znazornuje|znázorňuje|videt|vidět|viditel|obsahuje"
    r")\b",
    re.IGNORECASE,
)
NOT_VISUALLY_VERIFIED_RE = re.compile(
    r"(not visually verified|visual content was not verified|not inspected|"
    r"not checked|nebyl[ao]? vizualne|nebyl[ao]? vizuálně|neoveren|neověřen)",
    re.IGNORECASE,
)
ABSOLUTE_PATH_RE = re.compile(r"(?<!\w)/(?:home|Users|tmp|var|workspace|mnt)/[^\s)]+")


def usage() -> str:
    return "Usage: scripts/check-figure-media-review CASE_ID [ROUND_ID]"


def repo_root() -> Path:
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
    return Path(output.strip())


def die_usage(message: str) -> None:
    print(message, file=sys.stderr)
    print(usage(), file=sys.stderr)
    raise SystemExit(2)


def validate_id(label: str, value: str) -> None:
    if not ID_RE.fullmatch(value):
        die_usage(f"Invalid {label}. Use only letters, numbers, dot, underscore, and dash.")


def resolve_round(case_dir: Path, round_id: str | None) -> str:
    if round_id:
        validate_id("ROUND_ID", round_id)
        return round_id

    current_round = case_dir / "current-round.txt"
    if not current_round.is_file():
        die_usage(f"Missing current round: {case_dir}/current-round.txt")
    resolved = current_round.read_text(encoding="utf-8").strip()
    validate_id("ROUND_ID", resolved)
    return resolved


def normalized(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = value.replace("ě", "e").replace("š", "s").replace("č", "c")
    value = value.replace("ř", "r").replace("ž", "z").replace("ý", "y")
    value = value.replace("á", "a").replace("í", "i").replace("é", "e")
    value = value.replace("ú", "u").replace("ů", "u").replace("ň", "n")
    value = value.replace("ť", "t").replace("ď", "d")
    value = re.sub(r"\s+", " ", value.strip().lower())
    return value.strip(" .;:-")


def section_body(lines: list[str], heading: str) -> list[str] | None:
    start = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index + 1
            break
    if start is None:
        return None

    end = len(lines)
    for index in range(start, len(lines)):
        if re.match(r"^#{1,2}\s+", lines[index]):
            end = index
            break
    return lines[start:end]


def section_text(lines: list[str], heading: str) -> str:
    body = section_body(lines, heading)
    if body is None:
        return ""
    return "\n".join(body).strip()


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


def extract_table(body: list[str]) -> tuple[list[str], list[list[str]], str | None]:
    table_lines = [line for line in body if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return [], [], "missing Markdown table"

    rows = [split_table_row(line) for line in table_lines]
    header_index = None
    for index, cells in enumerate(rows):
        if index + 1 < len(rows) and is_delimiter_row(rows[index + 1]):
            header_index = index
            break
    if header_index is None:
        return [], [], "missing Markdown delimiter row"

    headers = [normalized(cell) for cell in rows[header_index]]
    data_rows = [row for row in rows[header_index + 2 :] if row and not is_delimiter_row(row)]
    return headers, data_rows, None


def scalar(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    if value is None:
        return ""
    return str(value).strip()


def read_inventory(
    path: Path,
    errors: list[str],
    *,
    missing_message: str | None = "missing reusable visual inventory: work/figure_media/visual_inventory.jsonl",
) -> list[dict[str, Any]]:
    if not path.is_file():
        if missing_message:
            errors.append(missing_message)
        return []

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"visual_inventory.jsonl line {line_number}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(value, dict):
            errors.append(f"visual_inventory.jsonl line {line_number}: expected JSON object")
            continue
        records.append(value)
    if not records:
        errors.append("visual_inventory.jsonl has no inventory records")
    return records


def previous_rounds(case_dir: Path, round_id: str) -> list[Path]:
    rounds_dir = case_dir / "rounds"
    rounds = sorted(path for path in rounds_dir.iterdir() if path.is_dir())
    names = [path.name for path in rounds]
    if round_id not in names:
        return []
    current_index = names.index(round_id)
    return rounds[:current_index]


def previous_inventories(
    case_dir: Path,
    round_id: str,
    errors: list[str],
) -> dict[str, list[dict[str, Any]]]:
    inventories: dict[str, list[dict[str, Any]]] = {}
    for previous_round in previous_rounds(case_dir, round_id):
        inventory = previous_round / "work" / "figure_media" / "visual_inventory.jsonl"
        if inventory.is_file():
            inventories[previous_round.name] = read_inventory(
                inventory,
                errors,
                missing_message=None,
            )
    return inventories


def check_sha256_field(
    record: dict[str, Any],
    field: str,
    item_id: str,
    errors: list[str],
) -> str:
    value = scalar(record.get(field, ""))
    if value and not SHA256_RE.fullmatch(value):
        errors.append(f"{item_id}: invalid {field}; expected SHA-256 hex digest")
    return value


def previous_record(
    previous_records_by_round: dict[str, list[dict[str, Any]]],
    round_id: str,
    item_id: str,
) -> dict[str, Any] | None:
    for record in previous_records_by_round.get(round_id, []):
        if scalar(record.get("item_id", "")) == item_id:
            return record
    return None


def matching_visual_hash(current: dict[str, Any], previous: dict[str, Any]) -> bool:
    current_source = scalar(current.get("source_asset_sha256", ""))
    previous_source = scalar(previous.get("source_asset_sha256", ""))
    if current_source and current_source == previous_source:
        return True
    current_crop = scalar(current.get("rendered_crop_sha256", ""))
    previous_crop = scalar(previous.get("rendered_crop_sha256", ""))
    return bool(current_crop and current_crop == previous_crop)


def validate_text_mentions(
    record: dict[str, Any],
    item_id: str,
    errors: list[str],
) -> None:
    if "text_mentions" not in record:
        return
    mentions = record["text_mentions"]
    if not isinstance(mentions, list):
        errors.append(f"{item_id}: text_mentions must be a list")
        return
    for mention_index, mention in enumerate(mentions, start=1):
        if not isinstance(mention, dict):
            errors.append(f"{item_id}: text_mentions[{mention_index}] must be an object")
            continue
        anchor = scalar(mention.get("anchor", ""))
        excerpt = scalar(mention.get("excerpt", ""))
        role = scalar(mention.get("role", ""))
        if not anchor:
            errors.append(f"{item_id}: text_mentions[{mention_index}].anchor is empty")
        if not excerpt:
            errors.append(f"{item_id}: text_mentions[{mention_index}].excerpt is empty")
        if role not in KNOWN_TEXT_MENTION_ROLES:
            errors.append(f"{item_id}: unknown text mention role: {role}")


def check_visual_reuse(
    record: dict[str, Any],
    item_id: str,
    visual_version: str,
    source_hash: str,
    crop_hash: str,
    previous_records_by_round: dict[str, list[dict[str, Any]]],
    errors: list[str],
) -> None:
    reused_from = scalar(record.get("visual_reused_from_round", ""))
    reuse_reason = scalar(record.get("visual_reuse_reason", ""))
    if not reused_from:
        if reuse_reason:
            errors.append(f"{item_id}: visual_reuse_reason requires visual_reused_from_round")
        return

    if not ID_RE.fullmatch(reused_from):
        errors.append(f"{item_id}: invalid visual_reused_from_round: {reused_from}")
        return
    if reused_from not in previous_records_by_round:
        errors.append(f"{item_id}: visual_reused_from_round does not point to a previous inventory: {reused_from}")
        return
    if reuse_reason not in KNOWN_VISUAL_REUSE_REASONS:
        errors.append(f"{item_id}: unknown visual_reuse_reason: {reuse_reason}")
        return
    if not visual_version:
        errors.append(f"{item_id}: visual_reused_from_round requires visual_analysis_version")
    previous = previous_record(previous_records_by_round, reused_from, item_id)
    if previous is None:
        errors.append(f"{item_id}: no matching previous inventory record in {reused_from}")
        return
    previous_version = scalar(previous.get("visual_analysis_version", ""))
    if visual_version and previous_version != visual_version:
        errors.append(f"{item_id}: visual_analysis_version does not match previous record in {reused_from}")

    if reuse_reason == "matching_source_asset_sha256":
        previous_hash = scalar(previous.get("source_asset_sha256", ""))
        if not source_hash or source_hash != previous_hash:
            errors.append(
                f"{item_id}: visual reuse source_asset_sha256 does not match previous record in {reused_from}"
            )
    if reuse_reason == "matching_rendered_crop_sha256":
        previous_hash = scalar(previous.get("rendered_crop_sha256", ""))
        if not crop_hash or crop_hash != previous_hash:
            errors.append(
                f"{item_id}: visual reuse rendered_crop_sha256 does not match previous record in {reused_from}"
            )


def check_claim_alignment_reuse(
    record: dict[str, Any],
    item_id: str,
    claim_alignment: str,
    claim_version: str,
    context_hash: str,
    previous_records_by_round: dict[str, list[dict[str, Any]]],
    errors: list[str],
) -> None:
    reused_from = scalar(record.get("claim_alignment_reused_from_round", ""))
    if not reused_from:
        return

    if not ID_RE.fullmatch(reused_from):
        errors.append(f"{item_id}: invalid claim_alignment_reused_from_round: {reused_from}")
        return
    if reused_from not in previous_records_by_round:
        errors.append(
            f"{item_id}: claim_alignment_reused_from_round does not point to a previous inventory: {reused_from}"
        )
        return
    if not claim_alignment:
        errors.append(f"{item_id}: claim_alignment_reused_from_round requires claim_alignment")
    if not claim_version:
        errors.append(f"{item_id}: claim_alignment_reused_from_round requires claim_alignment_version")
    if not context_hash:
        errors.append(f"{item_id}: claim_alignment_reused_from_round requires context_hash")

    previous = previous_record(previous_records_by_round, reused_from, item_id)
    if previous is None:
        errors.append(f"{item_id}: no matching previous inventory record in {reused_from}")
        return
    if not matching_visual_hash(record, previous):
        errors.append(
            f"{item_id}: claim alignment reuse requires matching source asset or rendered crop hash in {reused_from}"
        )
    previous_context_hash = scalar(previous.get("context_hash", ""))
    if context_hash and previous_context_hash != context_hash:
        errors.append(f"{item_id}: claim alignment context_hash does not match previous record in {reused_from}")
    previous_version = scalar(previous.get("claim_alignment_version", ""))
    if claim_version and previous_version != claim_version:
        errors.append(f"{item_id}: claim_alignment_version does not match previous record in {reused_from}")
    previous_alignment = scalar(previous.get("claim_alignment", ""))
    if claim_alignment and previous_alignment != claim_alignment:
        errors.append(f"{item_id}: claim_alignment does not match previous record in {reused_from}")


def check_inventory(
    records: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
    previous_records_by_round: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, str]]:
    inventory_by_item: dict[str, dict[str, str]] = {}
    seen: set[str] = set()
    for index, record in enumerate(records, start=1):
        missing = [field for field in REQUIRED_JSON_FIELDS if field not in record]
        if missing:
            errors.append(f"inventory record {index}: missing field(s): {', '.join(missing)}")
            continue

        item_id = scalar(record["item_id"])
        status = scalar(record["inspection_status"])
        pdf_anchor = scalar(record["pdf_anchor"])
        source_asset = scalar(record["source_asset_path"])
        description = scalar(record["visual_description"])
        limitations = scalar(record["limitations"])
        relevance = scalar(record["downstream_relevance"])
        source_hash = check_sha256_field(record, "source_asset_sha256", item_id or f"record {index}", errors)
        crop_hash = check_sha256_field(record, "rendered_crop_sha256", item_id or f"record {index}", errors)
        context_hash = check_sha256_field(record, "context_hash", item_id or f"record {index}", errors)
        visual_version = scalar(record.get("visual_analysis_version", ""))
        claim_alignment = scalar(record.get("claim_alignment", ""))
        claim_rationale = scalar(record.get("claim_alignment_rationale", ""))
        claim_version = scalar(record.get("claim_alignment_version", ""))

        if not item_id:
            errors.append(f"inventory record {index}: item_id is empty")
            continue
        if item_id in seen:
            errors.append(f"inventory record {index}: duplicate item_id: {item_id}")
        seen.add(item_id)
        inventory_by_item[item_id] = {
            "inspection_status": status,
            "claim_alignment": claim_alignment,
            "context_hash": context_hash,
            "visual_reused_from_round": scalar(record.get("visual_reused_from_round", "")),
            "claim_alignment_reused_from_round": scalar(record.get("claim_alignment_reused_from_round", "")),
        }

        if status not in KNOWN_STATUSES:
            errors.append(f"{item_id}: unknown inspection_status: {status}")
        if not pdf_anchor and status in {"pdf_inspected", "source_asset_checked"}:
            errors.append(f"{item_id}: {status} requires a PDF anchor")
        if status == "source_asset_checked" and not source_asset:
            errors.append(f"{item_id}: source_asset_checked requires source_asset_path")
        if source_asset and ABSOLUTE_PATH_RE.search(source_asset):
            errors.append(f"{item_id}: source_asset_path must be workspace-relative, not absolute")
        if not description:
            errors.append(f"{item_id}: visual_description is empty")
        if status in EVIDENCE_STATUSES and not source_hash and not crop_hash:
            warnings.append(f"{item_id}: inspected item has no source_asset_sha256 or rendered_crop_sha256")
        if status in {"inventoried_only", "not_available"} and not NOT_VISUALLY_VERIFIED_RE.search(
            description + " " + limitations
        ):
            errors.append(f"{item_id}: {status} description must state that visual content was not verified")
        if not limitations:
            warnings.append(f"{item_id}: limitations field is empty; write 'None.' when there are no limitations")
        if not relevance:
            warnings.append(f"{item_id}: downstream_relevance is empty")
        if visual_version and visual_version not in KNOWN_VISUAL_ANALYSIS_VERSIONS:
            errors.append(f"{item_id}: unknown visual_analysis_version: {visual_version}")
        if claim_version and claim_version not in KNOWN_CLAIM_ALIGNMENT_VERSIONS:
            errors.append(f"{item_id}: unknown claim_alignment_version: {claim_version}")
        validate_text_mentions(record, item_id, errors)
        check_visual_reuse(
            record,
            item_id,
            visual_version,
            source_hash,
            crop_hash,
            previous_records_by_round,
            errors,
        )
        if not claim_alignment:
            errors.append(f"{item_id}: missing claim_alignment")
        elif claim_alignment not in KNOWN_CLAIM_ALIGNMENTS:
            errors.append(f"{item_id}: unknown claim_alignment: {claim_alignment}")
        elif claim_alignment in EVIDENCE_CLAIM_ALIGNMENTS and status not in EVIDENCE_STATUSES:
            errors.append(
                f"{item_id}: claim_alignment={claim_alignment} requires pdf_inspected or source_asset_checked status"
            )
        if claim_alignment and not claim_version:
            errors.append(f"{item_id}: claim_alignment requires claim_alignment_version")
        if claim_alignment and not claim_rationale:
            warnings.append(f"{item_id}: claim_alignment_rationale is empty")
        if not claim_alignment and "claim_alignment_reused_from_round" in record:
            errors.append(f"{item_id}: claim_alignment_reused_from_round requires claim_alignment")
        check_claim_alignment_reuse(
            record,
            item_id,
            claim_alignment,
            claim_version,
            context_hash,
            previous_records_by_round,
            errors,
        )
        if "previous_round_change" in record:
            change = scalar(record["previous_round_change"])
            if change and change not in CHANGE_STATUSES:
                errors.append(f"{item_id}: unknown previous_round_change: {change}")
    return inventory_by_item


def check_headings(lines: list[str], errors: list[str]) -> None:
    present = {line.strip() for line in lines if re.match(r"^#{1,2}\s+", line)}
    for heading in REQUIRED_HEADINGS:
        if heading not in present:
            errors.append(f"missing required heading: {heading}")
    positions: list[int] = []
    for heading in REQUIRED_HEADINGS:
        try:
            positions.append(next(index for index, line in enumerate(lines) if line.strip() == heading))
        except StopIteration:
            return
    if positions != sorted(positions):
        errors.append("required headings are not in the expected order")


def check_required_table(
    lines: list[str],
    heading: str,
    required_headers: tuple[str, ...],
    min_rows: int,
    errors: list[str],
) -> tuple[list[str], list[list[str]]]:
    body = section_body(lines, heading)
    if body is None:
        return [], []
    headers, rows, table_error = extract_table(body)
    if table_error:
        errors.append(f"{heading}: {table_error}")
        return [], []
    missing = [header for header in required_headers if header not in headers]
    if missing:
        errors.append(f"{heading}: missing table column(s): {', '.join(missing)}")
    if len(rows) < min_rows:
        errors.append(f"{heading}: expected at least {min_rows} data row(s), got {len(rows)}")
    for row_number, cells in enumerate(rows, start=1):
        if len(cells) != len(headers):
            errors.append(
                f"{heading}: malformed table row {row_number}: expected {len(headers)} cells, got {len(cells)}"
            )
    return headers, rows


def cell(headers: list[str], row: list[str], name: str) -> str:
    if name not in headers:
        return ""
    index = headers.index(name)
    if index >= len(row):
        return ""
    return row[index]


def item_cell(headers: list[str], row: list[str], name: str = "item") -> str:
    return re.sub(r"^`([^`]*)`$", r"\1", cell(headers, row, name).strip()).strip()


def check_visual_inventory_table(lines: list[str], errors: list[str]) -> None:
    headers, rows = check_required_table(
        lines,
        "## Visual Inventory",
        ("item", "type", "pdf anchor", "inspection status", "description"),
        1,
        errors,
    )
    if not headers:
        return
    for row_number, row in enumerate(rows, start=1):
        status = normalized(cell(headers, row, "inspection status"))
        if status not in KNOWN_STATUSES:
            errors.append(f"visual inventory row {row_number}: unknown inspection status: {status}")


def check_context_alignment_table(
    lines: list[str],
    inventory_by_item: dict[str, dict[str, str]],
    errors: list[str],
) -> None:
    headers, rows = check_required_table(
        lines,
        "## Context And Claim Alignment",
        ("item", "text role", "claim alignment", "reuse status", "action"),
        0,
        errors,
    )
    if not headers:
        return
    context_items: set[str] = set()
    for row_number, row in enumerate(rows, start=1):
        item = item_cell(headers, row)
        role = normalized(cell(headers, row, "text role"))
        alignment = normalized(cell(headers, row, "claim alignment"))
        if item not in inventory_by_item:
            errors.append(f"context alignment row {row_number}: item is not present in visual_inventory.jsonl: {item}")
            continue
        context_items.add(item)
        if role and role not in KNOWN_TEXT_MENTION_ROLES:
            errors.append(f"context alignment row {row_number}: unknown text role: {role}")
        if alignment and alignment not in KNOWN_CLAIM_ALIGNMENTS:
            errors.append(f"context alignment row {row_number}: unknown claim alignment: {alignment}")
        inventory_alignment = inventory_by_item[item].get("claim_alignment", "")
        if alignment != inventory_alignment:
            errors.append(
                f"context alignment row {row_number}: claim alignment {alignment or '<empty>'} "
                f"does not match inventory claim_alignment {inventory_alignment or '<empty>'} for {item}"
            )
    missing_items = sorted(set(inventory_by_item) - context_items)
    for item in missing_items:
        errors.append(f"Context And Claim Alignment is missing inventory item: {item}")


def check_findings_table(
    lines: list[str],
    inventory_by_item: dict[str, dict[str, str]],
    errors: list[str],
    warnings: list[str],
) -> None:
    headers, rows = check_required_table(
        lines,
        "## Findings",
        ("priority", "item", "inspection status", "claim", "evidence", "downstream use"),
        0,
        errors,
    )
    if not headers:
        return
    for row_number, row in enumerate(rows, start=1):
        item = item_cell(headers, row)
        status = normalized(cell(headers, row, "inspection status"))
        claim = cell(headers, row, "claim")
        evidence = cell(headers, row, "evidence")
        combined = f"{claim} {evidence}"
        if status not in KNOWN_STATUSES:
            errors.append(f"finding row {row_number}: unknown inspection status: {status}")
            continue
        inventory = inventory_by_item.get(item)
        if not inventory:
            if item:
                errors.append(f"finding row {row_number}: item is not present in visual_inventory.jsonl: {item}")
        elif inventory.get("inspection_status") != status:
            errors.append(
                f"finding row {row_number}: status {status} does not match inventory status "
                f"{inventory.get('inspection_status')} for {item}"
            )
        if VISUAL_CLAIM_RE.search(combined) and status not in EVIDENCE_STATUSES:
            errors.append(
                f"finding row {row_number}: visual-content claim requires pdf_inspected or source_asset_checked status"
            )


def check_previous_round_comparison(
    lines: list[str],
    case_dir: Path,
    round_id: str,
    warnings: list[str],
) -> None:
    previous = previous_rounds(case_dir, round_id)
    if not previous:
        return
    text = section_text(lines, "## Changes Since Previous Round")
    if not text:
        warnings.append("previous rounds exist, but Changes Since Previous Round is empty")
        return
    normalized_text = normalized(text)
    if not any(status in normalized_text for status in CHANGE_STATUSES):
        warnings.append(
            "previous rounds exist, but Changes Since Previous Round does not record a known change classification"
        )


def check_manual_checks(lines: list[str], warnings: list[str]) -> None:
    body = section_body(lines, "## Manual Checks")
    if body is None:
        return
    items = [line for line in body if re.match(r"^\s*(?:[-*]\s+|\d+\.\s+)", line)]
    if len(items) < 1:
        warnings.append("Manual Checks should contain at least one concrete item or state that none remain")


def check_hygiene(text: str, errors: list[str]) -> None:
    if ABSOLUTE_PATH_RE.search(text):
        errors.append("figure/media review contains an absolute filesystem path")
    if PLACEHOLDER_RE.search(text):
        errors.append("leftover placeholder/template text")
    for match in ANGLE_PLACEHOLDER_RE.finditer(text):
        value = match.group(1).strip()
        if not AUTOLINK_RE.fullmatch(value):
            errors.append("leftover angle-bracket placeholder/template text")


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] in {"-h", "--help"}:
        print(usage())
        return 0
    if len(argv) not in {2, 3}:
        die_usage("Expected CASE_ID and optional ROUND_ID.")

    case_id = argv[1]
    validate_id("CASE_ID", case_id)
    root = repo_root()
    case_dir = root / "cases" / case_id
    if not case_dir.is_dir():
        print(f"ERROR: Case does not exist: cases/{case_id}", file=sys.stderr)
        return 2

    round_id = resolve_round(case_dir, argv[2] if len(argv) == 3 else None)
    round_dir = case_dir / "rounds" / round_id
    if not round_dir.is_dir():
        print(f"ERROR: Round does not exist: cases/{case_id}/rounds/{round_id}", file=sys.stderr)
        return 2

    output = round_dir / "outputs" / "figure_media_review.md"
    inventory = round_dir / "work" / "figure_media" / "visual_inventory.jsonl"
    if not output.is_file():
        print(
            f"ERROR: Missing figure/media review: cases/{case_id}/rounds/{round_id}/outputs/figure_media_review.md",
            file=sys.stderr,
        )
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    previous_records_by_round = previous_inventories(case_dir, round_id, errors)
    records = read_inventory(inventory, errors)
    inventory_by_item = check_inventory(records, errors, warnings, previous_records_by_round)

    text = output.read_text(encoding="utf-8")
    lines = text.splitlines()
    check_headings(lines, errors)
    check_visual_inventory_table(lines, errors)
    check_context_alignment_table(lines, inventory_by_item, errors)
    check_findings_table(lines, inventory_by_item, errors, warnings)
    check_previous_round_comparison(lines, case_dir, round_id, warnings)
    check_manual_checks(lines, warnings)
    check_hygiene(text, errors)

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Figure/media review check passed")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
