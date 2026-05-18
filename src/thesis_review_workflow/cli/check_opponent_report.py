"""Validate an opponent-report draft shape and safety before IS submission."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.commands import repo_command_environment, resolve_repo_command
from thesis_review_workflow.markdown_utils import section_text as markdown_section_text
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.structured_evidence import validate_structured_evidence_artifact
from thesis_review_workflow.submitted_reports import (
    OPPONENT_REPORT_SUBMITTED_RECORD_REL,
    validate_submitted_opponent_report_record,
)

DEFAULT_DRAFT = Path("work/oponent_posudek_draft.md")
CLEAN_PROPOSAL = Path("outputs/oponent_posudek_navrh.md")
MATERIALS_REL = Path("outputs/oponent_podklady_revidovane.md")
TRACE_REL = Path("work/opponent_report_trace.json")
IS_FORM_SECTION_HEADING = "## IS formulář (výběry a body)"
PRIVATE_COMMENT_HEADING = "## Komentář pro studenta (neveřejná část)"
PRIVATE_COMMENT_MIN_NONSPACE_CHARS = 80

COMMON_REQUIRED_HEADINGS = (
    "# Návrh oponentského posudku",
    IS_FORM_SECTION_HEADING,
    "## 1. Náročnost zadání",
    "## 2. Rozsah splnění požadavků zadání",
    "## 3. Rozsah technické zprávy",
    "## 4. Prezentační úroveň technické zprávy",
    "## 5. Formální úprava technické zprávy",
    "## 6. Práce s literaturou",
    "## 7. Realizační výstup",
    "## 8. Využitelnost výsledku",
    "## 9. Celkové hodnocení",
    "## 10. Otázky k obhajobě",
    "## 11. Body a známka",
    PRIVATE_COMMENT_HEADING,
)
CANONICAL_REQUIRED_HEADINGS = (
    *COMMON_REQUIRED_HEADINGS,
    "## 12. Před odevzdáním",
)
CLEAN_FORBIDDEN_HEADINGS = ("## 12. Před odevzdáním",)
REQUIRED_HEADINGS = CANONICAL_REQUIRED_HEADINGS

PLACEHOLDER_PATTERNS = (
    r"\bTBD\b",
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\blorem ipsum\b",
    r"\bYYYY-MM-DD\b",
    r"<[^>\n]+>",
)

INTERNAL_PATTERNS = (
    r"(?<!\w)/(?:home|Users|tmp|var|workspace|mnt)/[^\s)\"']*",
    r"\bcases/",
    r"\brounds/",
    r"\bwork/",
    r"\bnotes/",
    r"\bprofiles/",
    r"\boutputs/",
    r"\binputs/",
    r"\bextracted/",
    r"\breview_manifest\.json\b",
    r"\bagent_coverage\.json\b",
    r"\boponent_podklady(?:_revidovane|_draft)?\.md\b",
    r"\boponent_posudek_draft\.md\b",
    r"\boponent_posudek_navrh\.md\b",
    r"\bfeedback_k_posudku\.md\b",
    r"\bgithub_code_intake\.md\b",
    r"\brevision_diff\.md\b",
    r"\breference_report_comparison\.md\b",
    r"\bopponent_reading_packet\.md\b",
    r"\bpr_contribution_review\.md\b",
    r"\bdemo_artifacts_review\.md\b",
    r"\bcode_consistency\.md\b",
    r"\bcode_quality_review\.md\b",
    r"\bfigure_media_review\.md\b",
    r"\btypography_formal_review\.md\b",
    r"\b[0-9a-f]{64}\b",
    r"\b(?:approval record|helper[- ]check|workflow profile|review basis|review manifest|agent coverage)\b",
)

CONFIDENCE_LABEL_RE = re.compile(r"\[(?:FAKT|INTERPRETACE|ODHAD|NEOV[EĚ]R[EŘ]NO|K RU[CČ]N[IÍ] KONTROLE)\]")
POINT_RE = re.compile(r"\b(?:Body|Bodové hodnocení)\s*:\s*(\d{1,3})\b", re.IGNORECASE)
GRADE_RE = re.compile(r"\b(?:Známka|Navržená známka)\s*:\s*([A-F])\b", re.IGNORECASE)
SOURCE_PATH_RE = re.compile(r"<!--\s*source_materials_path:\s*([^>]+?)\s*-->")
SOURCE_SHA_RE = re.compile(r"<!--\s*source_materials_sha256:\s*([0-9a-f]{64})\s*-->")
TRACE_PATH_RE = re.compile(r"<!--\s*source_trace_path:\s*([^>]+?)\s*-->")
TRACE_SHA_RE = re.compile(r"<!--\s*source_trace_sha256:\s*([0-9a-f]{64})\s*-->")
SOURCE_METADATA_COMMENT_RE = re.compile(r"^<!--\s*source_(?:materials|trace)_(?:path|sha256):.*?-->\s*$", re.MULTILINE)
OPEN_CALIBRATION_PATTERNS = (
    r"\bpracovn[ií]\s+draft\b",
    r"\bk\s+ru[cč]n[ií]\s+kalibraci\b",
    r"\bk\s+ru[cč]n[ií]mu\s+(?:v[ýy]b[eě]ru|zad[aá]n[ií])\b",
    r"\bpřed\s+vložen[ií]m\s+do\s+IS\s+ověřte\b",
    r"\bnen[ií]\s+.*\bhotov[aá]\s+formulace\b",
    r"\bzkalibrujte\b",
    r"\bPro\s+neveřejn[ýy]\s+koment[áa]ř\s+studentovi\s+zde\b",
)

IS_SELECT_FIELDS = {
    "Náročnost zadání": {
        "jednoduché zadání",
        "méně obtížné zadání",
        "průměrně obtížné zadání",
        "obtížnější zadání",
        "značně obtížné zadání",
    },
    "Rozsah splnění požadavků zadání": {
        "zadání nesplněno",
        "zadání splněno pouze částečně",
        "zadání splněno pouze částečně s drobnými výhradami",
        "zadání splněno pouze částečně s vážnějšími výhradami",
        "zadání téměř splněno",
        "zadání téměř splněno s drobnými výhradami",
        "zadání téměř splněno s vážnějšími výhradami",
        "student se odůvodněně odchýlil od zadání",
        "student se odůvodněně odchýlil od zadání s drobnými výhradami",
        "student se odůvodněně odchýlil od zadání s vážnějšími výhradami",
        "zadání splněno",
        "zadání splněno s drobnými výhradami",
        "zadání splněno s vážnějšími výhradami",
        "zadání splněno a práce obsahuje podstatná rozšíření",
    },
    "Rozsah technické zprávy": {
        "nesplňuje minimální požadavky",
        "téměř splňuje minimální požadavky",
        "splňuje pouze minimální požadavky",
        "je v obvyklém rozmezí",
        "přesahuje obvyklé rozmezí",
    },
}
IS_POINT_FIELDS = (
    "Prezentační úroveň technické zprávy",
    "Formální úprava technické zprávy",
    "Práce s literaturou",
    "Realizační výstup",
)


def is_safe_relative(value: str) -> bool:
    return is_safe_round_relative_path(value)


def section_text(lines: list[str], heading: str) -> str:
    return markdown_section_text(lines, heading, stop_pattern=r"^##\s+")


def nonempty_body(lines: list[str], heading: str) -> bool:
    body = section_text(lines, heading)
    return bool(body and not re.fullmatch(r"[-\s]*", body))


def parse_colon_fields(section: str) -> tuple[dict[str, str], list[str]]:
    fields: dict[str, str] = {}
    duplicates: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip("- \t")
        value = value.strip()
        if key and value:
            if key in fields and key not in duplicates:
                duplicates.append(key)
            fields[key] = value
    return fields, duplicates


def parse_point_value(value: str) -> int | None:
    match = re.fullmatch(r"(\d{1,3})(?:\s*(?:bod[uůy]?|b\.?))?", value.strip(), re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strip_metadata_comments(text: str) -> str:
    return re.sub(
        r"^<!--\s*source_(?:materials|trace)_(?:path|sha256):.*?-->\s*\n?",
        "",
        text,
        flags=re.MULTILINE,
    )


def validate_trace_metadata(text: str, trace_path: Path, _path_arg: str, errors: list[str]) -> None:
    path_match = TRACE_PATH_RE.search(text)
    sha_match = TRACE_SHA_RE.search(text)
    if not path_match:
        errors.append("missing source trace path metadata comment")
    elif path_match and path_match.group(1).strip() != TRACE_REL.as_posix():
        errors.append(
            "source trace path metadata must be " f"{TRACE_REL.as_posix()}, got {path_match.group(1).strip()}"
        )
    if not sha_match:
        errors.append("missing source trace sha256 metadata comment")
    elif sha_match and trace_path.is_file() and sha_match.group(1) != sha256_file(trace_path):
        errors.append("opponent report draft is stale: opponent report trace hash changed")


def validate_source_metadata(text: str, materials_path: Path, _path_arg: str, errors: list[str]) -> None:
    path_match = SOURCE_PATH_RE.search(text)
    sha_match = SOURCE_SHA_RE.search(text)
    if not path_match:
        errors.append("missing source materials path metadata comment")
    elif path_match and path_match.group(1).strip() != MATERIALS_REL.as_posix():
        errors.append(
            "source materials path metadata must be " f"{MATERIALS_REL.as_posix()}, got {path_match.group(1).strip()}"
        )
    if not sha_match:
        errors.append("missing source materials sha256 metadata comment")
    elif sha_match and materials_path.is_file() and sha_match.group(1) != sha256_file(materials_path):
        errors.append("opponent report draft is stale: reviewed opponent materials hash changed")


def run_round_ready(root: Path, case_id: str, round_id: str, errors: list[str]) -> None:
    result = subprocess.run(
        resolve_repo_command(root, ["scripts/check-round-ready", case_id, round_id]),
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=repo_command_environment(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = "\n".join(line for line in (result.stderr + result.stdout).splitlines() if line.strip())
        errors.append("round readiness check failed" + (f":\n{detail}" if detail else ""))


def run_opponent_materials_check(root: Path, case_id: str, round_id: str, errors: list[str]) -> None:
    result = subprocess.run(
        resolve_repo_command(root, ["scripts/check-opponent-materials", case_id, round_id]),
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=repo_command_environment(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = "\n".join(line for line in (result.stderr + result.stdout).splitlines() if line.strip())
        errors.append("reviewed opponent materials check failed" + (f":\n{detail}" if detail else ""))


def check_text(text: str, public_text: str, errors: list[str], *, mode: str = "canonical") -> None:
    lines = text.splitlines()
    required_headings = CANONICAL_REQUIRED_HEADINGS if mode == "canonical" else COMMON_REQUIRED_HEADINGS
    for heading in required_headings:
        if heading not in lines:
            errors.append(f"missing required heading: {heading}")
        elif heading.startswith("## ") and not nonempty_body(lines, heading):
            errors.append(f"empty report section: {heading}")

    if mode == "clean":
        if SOURCE_METADATA_COMMENT_RE.search(text):
            errors.append("clean opponent report proposal must not contain source metadata comments")
        for heading in CLEAN_FORBIDDEN_HEADINGS:
            if heading in lines:
                errors.append(f"clean opponent report proposal must not contain private checklist heading: {heading}")

    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, public_text, re.IGNORECASE | re.MULTILINE):
            errors.append(f"placeholder remains in report draft: {pattern}")

    for pattern in INTERNAL_PATTERNS:
        if re.search(pattern, public_text, re.IGNORECASE):
            errors.append(f"internal workflow path or artifact leaked into report draft: {pattern}")

    if CONFIDENCE_LABEL_RE.search(public_text):
        errors.append("internal confidence labels must be rewritten into normal opponent-report prose")

    for pattern in OPEN_CALIBRATION_PATTERNS:
        if re.search(pattern, public_text, re.IGNORECASE):
            errors.append(f"report draft still contains open calibration wording: {pattern}")

    questions = section_text(lines, "## 10. Otázky k obhajobě")
    if "?" not in questions:
        errors.append("defense questions section must contain at least one explicit question")

    points = [int(match.group(1)) for match in POINT_RE.finditer(public_text)]
    grades = [match.group(1).upper() for match in GRADE_RE.finditer(public_text)]
    if not points:
        errors.append("concrete numeric point value is required before the report draft can pass")
    if not grades:
        errors.append("concrete proposed grade is required before the report draft can pass")
    for point_value in points:
        if point_value < 0 or point_value > 100:
            errors.append(f"point value outside 0-100 range: {point_value}")

    private_comment = section_text(lines, PRIVATE_COMMENT_HEADING).strip()
    private_comment_nonspace_chars = len(re.sub(r"\s+", "", private_comment))
    if private_comment_nonspace_chars < PRIVATE_COMMENT_MIN_NONSPACE_CHARS:
        errors.append(
            "private student comment is too short to be a calibrated IS comment "
            f"({private_comment_nonspace_chars} non-whitespace characters)"
        )

    form_fields, duplicate_fields = parse_colon_fields(section_text(lines, IS_FORM_SECTION_HEADING))
    for duplicate_field in duplicate_fields:
        if duplicate_field in IS_SELECT_FIELDS or duplicate_field in IS_POINT_FIELDS:
            errors.append(f"duplicate IS form field: {duplicate_field}")
    for field, allowed_values in IS_SELECT_FIELDS.items():
        selection_value = form_fields.get(field)
        if not selection_value:
            errors.append(f"missing IS form selection: {field}")
        elif selection_value not in allowed_values:
            errors.append(f"invalid IS form selection for {field}: {selection_value}")
    for field in IS_POINT_FIELDS:
        field_value = form_fields.get(field)
        if not field_value:
            errors.append(f"missing IS form points: {field}")
            continue
        parsed = parse_point_value(field_value)
        if parsed is None:
            errors.append(f"invalid IS form point value for {field}: {field_value}")
        elif parsed < 0 or parsed > 100:
            errors.append(f"IS form point value outside 0-100 range for {field}: {parsed}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument("--mode", choices=("canonical", "clean"), default="canonical")
    parser.add_argument("--path", help="round-relative report draft path")
    args = parser.parse_args(argv[1:])

    validate_id("CASE_ID", args.case_id)
    path_arg = args.path or (CLEAN_PROPOSAL if args.mode == "clean" else DEFAULT_DRAFT).as_posix()
    if not is_safe_relative(path_arg):
        print("ERROR: --path must be relative inside the round", file=sys.stderr)
        return 2

    root = repo_root()
    try:
        case_dir = require_case_dir(root, args.case_id, error_prefix="ERROR: ", stderr=True)
        round_id = resolve_round(case_dir, args.round_id)
        round_dir = require_round_dir(case_dir, args.case_id, round_id, error_prefix="ERROR: ", stderr=True)
    except SystemExit as exc:
        if exc.code == 2:
            return 2
        raise

    errors: list[str] = []
    run_round_ready(root, args.case_id, round_id, errors)
    run_opponent_materials_check(root, args.case_id, round_id, errors)
    trace_errors = validate_structured_evidence_artifact(
        round_dir,
        TRACE_REL,
        case_id=args.case_id,
        round_id=round_id,
    )
    errors.extend(trace_errors)

    draft_path = round_dir / path_arg
    draft_exists = draft_path.is_file()
    canonical_draft_required = args.mode == "canonical" and (
        path_arg != DEFAULT_DRAFT.as_posix()
        or (round_dir / CLEAN_PROPOSAL).is_file()
        or (round_dir / "outputs" / "feedback_k_posudku.md").is_file()
    )
    if not draft_exists and canonical_draft_required:
        errors.append(f"missing opponent report draft: {path_arg}")
    materials_path = round_dir / MATERIALS_REL
    if not materials_path.is_file():
        errors.append(f"missing reviewed opponent materials: {MATERIALS_REL.as_posix()}")
    trace_path = round_dir / TRACE_REL

    if draft_exists:
        text = draft_path.read_text(encoding="utf-8")
        public_text = text
        if args.mode == "canonical":
            validate_trace_metadata(text, trace_path, path_arg, errors)
            validate_source_metadata(text, materials_path, path_arg, errors)
            public_text = strip_metadata_comments(text)
        check_text(text, public_text, errors, mode=args.mode)

    submitted_record_path = round_dir / OPPONENT_REPORT_SUBMITTED_RECORD_REL
    if submitted_record_path.is_file():
        try:
            submitted_record = json.loads(submitted_record_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{OPPONENT_REPORT_SUBMITTED_RECORD_REL}: invalid JSON: {exc.msg}")
        else:
            errors.extend(
                validate_submitted_opponent_report_record(
                    submitted_record,
                    round_dir=round_dir,
                    case_id=args.case_id,
                    round_id=round_id,
                    rel_path=OPPONENT_REPORT_SUBMITTED_RECORD_REL,
                )
            )
    else:
        submitted_dir = round_dir / "work" / "submitted_reports"
        submitted_text_dir = round_dir / "extracted" / "submitted_reports"
        if (
            submitted_dir.is_dir()
            and any(path.name.startswith("opponent_report") for path in submitted_dir.iterdir() if path.is_file())
        ) or (
            submitted_text_dir.is_dir()
            and any(path.name.startswith("opponent_report") for path in submitted_text_dir.iterdir() if path.is_file())
        ):
            errors.append(f"submitted opponent report files require {OPPONENT_REPORT_SUBMITTED_RECORD_REL}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Opponent report {args.mode} check passed")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
