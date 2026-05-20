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
from thesis_review_workflow.report_calibration import (
    PUBLIC_REPORT_LENGTHS,
    REPORT_CALIBRATION_BASIS_REL,
    report_calibration_expected_controls,
    validate_report_calibration_artifact,
)
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
    r"\breport_calibration_basis\.json\b",
    r"\breport[-_ ]calibration[-_ ]basis(?:\b|_)",
    r"\breviewer profile\b",
    r"\bsource_report_calibration(?:\b|_)",
    r"\b[0-9a-f]{64}\b",
    r"\b(?:approval record|helper[- ]check|workflow profile|review basis|review manifest|agent coverage)\b",
)

CONFIDENCE_LABEL_RE = re.compile(r"\[(?:FAKT|INTERPRETACE|ODHAD|NEOV[EĚ]R[EŘ]NO|K RU[CČ]N[IÍ] KONTROLE)\]")
CLEAN_DEFAULT_MAX_DEFENSE_QUESTIONS = 5
CLEAN_REPORT_LENGTH_BUDGETS = {
    "compact": {"nonempty_lines": 120, "words": 1800},
    "standard": {"nonempty_lines": 170, "words": 2600},
    "extended": {"nonempty_lines": 230, "words": 3600},
}
CLEAN_AUDIT_TABLE_HEADER_RE = re.compile(
    r"^\|.*(?:confidence|evidence|severity|risk|source|stav|závažnost|zavaznost|důkaz|dukaz|riziko).*\|$",
    re.IGNORECASE | re.MULTILINE,
)
CLEAN_TABLE_SEPARATOR_RE = re.compile(r"^\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$", re.MULTILINE)
CLEAN_INTERNAL_HEADING_RE = re.compile(
    r"^##+\s+(?:"
    r"Synthesis Handoff|Review Handoff|Trace|Evidence Ledger|Claim Ledger|Checked Scope|"
    r"Evidence Source Matrix|Report Quality Controls|Pre-submission|Internal Checks|Interní kontroly"
    r")\b",
    re.IGNORECASE | re.MULTILINE,
)
POINT_RE = re.compile(r"\b(?:Body|Bodové hodnocení)\s*:\s*(\d{1,3})\b", re.IGNORECASE)
GRADE_RE = re.compile(r"\b(?:Známka|Navržená známka)\s*:\s*([A-F])\b", re.IGNORECASE)
SOURCE_PATH_RE = re.compile(r"<!--\s*source_materials_path:\s*([^>]+?)\s*-->")
SOURCE_SHA_RE = re.compile(r"<!--\s*source_materials_sha256:\s*([0-9a-f]{64})\s*-->")
TRACE_PATH_RE = re.compile(r"<!--\s*source_trace_path:\s*([^>]+?)\s*-->")
TRACE_SHA_RE = re.compile(r"<!--\s*source_trace_sha256:\s*([0-9a-f]{64})\s*-->")
CALIBRATION_PATH_RE = re.compile(r"<!--\s*source_report_calibration_basis_path:\s*([^>]+?)\s*-->")
CALIBRATION_SHA_RE = re.compile(r"<!--\s*source_report_calibration_basis_sha256:\s*([0-9a-f]{64})\s*-->")
SOURCE_METADATA_COMMENT_RE = re.compile(
    r"^<!--\s*(?:source_(?:materials|trace)_(?:path|sha256)"
    r"|source_report_calibration_(?:basis_(?:path|sha256)|preference_ids|expected_controls)):.*?-->\s*$",
    re.MULTILINE,
)
ANY_SOURCE_METADATA_COMMENT_RE = re.compile(r"^<!--\s*source_[a-z0-9_]+:\s*.*?-->\s*$", re.MULTILINE)
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
    return re.sub(SOURCE_METADATA_COMMENT_RE.pattern + r"\n?", "", text, flags=re.MULTILINE)


def unsupported_source_metadata_comments(text: str) -> list[str]:
    comments: list[str] = []
    for line in text.splitlines():
        if ANY_SOURCE_METADATA_COMMENT_RE.match(line) and not SOURCE_METADATA_COMMENT_RE.match(line):
            comments.append(line.strip())
    return comments


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


def load_json_object(path: Path, label: str, errors: list[str]) -> dict[str, object] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing required JSON artifact: {label}")
        return None
    except json.JSONDecodeError as exc:
        errors.append(f"{label}: invalid JSON: {exc.msg}")
        return None
    if not isinstance(loaded, dict):
        errors.append(f"{label}: JSON artifact must be an object")
        return None
    return loaded


def load_bound_report_calibration_basis(
    round_dir: Path,
    trace: dict[str, object] | None,
    *,
    case_id: str,
    round_id: str,
    errors: list[str],
) -> dict[str, object] | None:
    if not isinstance(trace, dict):
        return None
    basis_path = trace.get("report_calibration_basis_path")
    basis_hash = trace.get("report_calibration_basis_sha256")
    if basis_path is None and basis_hash is None:
        return None
    if basis_path != REPORT_CALIBRATION_BASIS_REL:
        errors.append(f"report calibration basis path must be {REPORT_CALIBRATION_BASIS_REL}")
        return None
    basis_file = round_dir / REPORT_CALIBRATION_BASIS_REL
    if not isinstance(basis_hash, str) or not basis_file.is_file() or basis_hash != sha256_file(basis_file):
        errors.append("report calibration basis hash is stale or missing")
        return None
    errors.extend(
        validate_report_calibration_artifact(
            round_dir,
            REPORT_CALIBRATION_BASIS_REL,
            case_id=case_id,
            round_id=round_id,
        )
    )
    return load_json_object(basis_file, REPORT_CALIBRATION_BASIS_REL, errors)


def validate_calibration_metadata(text: str, trace: dict[str, object] | None, errors: list[str]) -> None:
    path_match = CALIBRATION_PATH_RE.search(text)
    sha_match = CALIBRATION_SHA_RE.search(text)
    if not isinstance(trace, dict):
        return
    trace_path = trace.get("report_calibration_basis_path")
    trace_sha = trace.get("report_calibration_basis_sha256")
    if trace_path is None and trace_sha is None:
        if path_match or sha_match:
            errors.append(
                "draft contains report calibration metadata but trace has no report calibration basis binding"
            )
        return
    if not path_match:
        errors.append("missing report calibration basis path metadata comment")
    elif path_match.group(1).strip() != trace_path:
        errors.append(
            "report calibration basis path metadata must match trace binding, " f"got {path_match.group(1).strip()}"
        )
    if not sha_match:
        errors.append("missing report calibration basis sha256 metadata comment")
    elif sha_match.group(1) != trace_sha:
        errors.append("opponent report draft is stale: report calibration basis hash changed")


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


def record_draft_calibration_issue(
    message: str,
    errors: list[str],
    notes: list[str],
    *,
    allow_draft_calibration_pending: bool,
) -> None:
    if allow_draft_calibration_pending:
        notes.append(message)
    else:
        errors.append(message)


def is_open_calibration_text(value: str) -> bool:
    return any(re.search(pattern, value, re.IGNORECASE) for pattern in OPEN_CALIBRATION_PATTERNS)


def defense_question_count(section: str) -> int:
    return len(re.findall(r"\?", section))


def declared_defense_question_max(expected_report_controls: dict[str, object] | None) -> int | None:
    if not expected_report_controls:
        return None
    question_bounds = expected_report_controls.get("defense_question_count")
    if not isinstance(question_bounds, dict):
        return None
    maximum = question_bounds.get("max")
    if isinstance(maximum, int) and not isinstance(maximum, bool):
        return maximum
    return None


def public_report_length_text(public_text: str) -> str:
    return public_text.split(PRIVATE_COMMENT_HEADING, 1)[0].rstrip()


def validate_clean_report_shape(
    public_text: str,
    *,
    question_count: int,
    expected_report_controls: dict[str, object] | None,
    expected_report_controls_source: str,
    errors: list[str],
) -> None:
    if (
        declared_defense_question_max(expected_report_controls) is None
        and question_count > CLEAN_DEFAULT_MAX_DEFENSE_QUESTIONS
    ):
        errors.append(
            "clean opponent report proposal has excessive defense questions: "
            f"expected at most {CLEAN_DEFAULT_MAX_DEFENSE_QUESTIONS}, got {question_count}"
        )
    if CLEAN_AUDIT_TABLE_HEADER_RE.search(public_text) and CLEAN_TABLE_SEPARATOR_RE.search(public_text):
        errors.append("clean opponent report proposal must not contain audit-style evidence/risk tables")
    for match in CLEAN_INTERNAL_HEADING_RE.finditer(public_text):
        heading = match.group(0).strip()
        errors.append(f"clean opponent report proposal must not contain internal-only heading: {heading}")

    if not expected_report_controls:
        return
    length_class = expected_report_controls.get("public_report_length")
    if length_class is None:
        return
    if length_class not in PUBLIC_REPORT_LENGTHS:
        errors.append(
            "public report length control must be one of " f"{', '.join(sorted(PUBLIC_REPORT_LENGTHS))}: {length_class}"
        )
        return
    budget = CLEAN_REPORT_LENGTH_BUDGETS.get(str(length_class))
    if budget is None:
        return
    length_text = public_report_length_text(public_text)
    nonempty_lines = sum(1 for line in length_text.splitlines() if line.strip())
    words = len(re.findall(r"\S+", length_text))
    if nonempty_lines > budget["nonempty_lines"]:
        errors.append(
            "clean opponent report proposal exceeds "
            f"{expected_report_controls_source} public_report_length={length_class}: "
            f"expected at most {budget['nonempty_lines']} non-empty lines, got {nonempty_lines}"
        )
    if words > budget["words"]:
        errors.append(
            "clean opponent report proposal exceeds "
            f"{expected_report_controls_source} public_report_length={length_class}: "
            f"expected at most {budget['words']} words, got {words}"
        )


def validate_expected_report_controls(
    expected_controls: dict[str, object],
    *,
    source_label: str = "report calibration basis",
    form_fields: dict[str, str],
    points: list[int],
    grades: list[str],
    question_count: int,
    private_comment_nonspace_chars: int,
    errors: list[str],
    notes: list[str],
    allow_draft_calibration_pending: bool,
) -> None:
    is_select_values = expected_controls.get("is_select_values")
    if isinstance(is_select_values, dict):
        for field, expected in is_select_values.items():
            if not isinstance(field, str) or not isinstance(expected, str):
                continue
            actual = form_fields.get(field)
            if actual == expected:
                continue
            message = (
                f"IS form selection for {field} does not match {source_label}: "
                f"expected {expected}, got {actual or '<missing>'}"
            )
            if not actual or is_open_calibration_text(actual):
                record_draft_calibration_issue(
                    message,
                    errors,
                    notes,
                    allow_draft_calibration_pending=allow_draft_calibration_pending,
                )
            else:
                errors.append(message)

    expected_grade = expected_controls.get("overall_grade")
    if isinstance(expected_grade, str):
        if not grades:
            record_draft_calibration_issue(
                f"overall grade does not match {source_label}: expected {expected_grade}, got <missing>",
                errors,
                notes,
                allow_draft_calibration_pending=allow_draft_calibration_pending,
            )
        elif len(grades) != 1:
            errors.append(
                f"overall grade does not match {source_label}: expected one canonical grade {expected_grade}, "
                f"got {', '.join(grades)}"
            )
        elif expected_grade != grades[0]:
            errors.append(f"overall grade does not match {source_label}: expected {expected_grade}, got {grades[0]}")

    interval = expected_controls.get("overall_points_interval")
    if (
        isinstance(interval, list)
        and len(interval) == 2
        and all(isinstance(item, int) and not isinstance(item, bool) for item in interval)
    ):
        if not points:
            record_draft_calibration_issue(
                f"overall points do not match {source_label}: expected {interval[0]}-{interval[1]}, got <missing>",
                errors,
                notes,
                allow_draft_calibration_pending=allow_draft_calibration_pending,
            )
        else:
            low, high = interval
            if len(points) != 1:
                errors.append(
                    f"overall points do not match {source_label}: expected one canonical value {low}-{high}, "
                    f"got {', '.join(str(point) for point in points)}"
                )
            for point_value in points:
                if point_value < low or point_value > high:
                    errors.append(
                        f"overall points do not match {source_label}: " f"expected {low}-{high}, got {point_value}"
                    )

    question_bounds = expected_controls.get("defense_question_count")
    if isinstance(question_bounds, dict):
        minimum = question_bounds.get("min")
        maximum = question_bounds.get("max")
        if isinstance(minimum, int) and not isinstance(minimum, bool) and question_count < minimum:
            errors.append(
                f"defense question count does not match {source_label}: "
                f"expected at least {minimum}, got {question_count}"
            )
        if isinstance(maximum, int) and not isinstance(maximum, bool) and question_count > maximum:
            errors.append(
                f"defense question count does not match {source_label}: "
                f"expected at most {maximum}, got {question_count}"
            )

    if (
        expected_controls.get("private_comment_required") is True
        and private_comment_nonspace_chars < PRIVATE_COMMENT_MIN_NONSPACE_CHARS
    ):
        record_draft_calibration_issue(
            f"private student comment required by {source_label} is missing or too short",
            errors,
            notes,
            allow_draft_calibration_pending=allow_draft_calibration_pending,
        )


def check_text(
    text: str,
    public_text: str,
    errors: list[str],
    *,
    mode: str = "canonical",
    allow_draft_calibration_pending: bool = False,
    draft_calibration_notes: list[str] | None = None,
    expected_report_controls: dict[str, object] | None = None,
    expected_report_controls_source: str = "report calibration basis",
) -> None:
    draft_calibration_notes = draft_calibration_notes if draft_calibration_notes is not None else []
    lines = text.splitlines()
    required_headings = CANONICAL_REQUIRED_HEADINGS if mode == "canonical" else COMMON_REQUIRED_HEADINGS
    for heading in required_headings:
        if heading not in lines:
            errors.append(f"missing required heading: {heading}")
        elif heading.startswith("## ") and not nonempty_body(lines, heading):
            errors.append(f"empty report section: {heading}")

    if mode == "clean":
        if ANY_SOURCE_METADATA_COMMENT_RE.search(text):
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

    if mode == "canonical":
        for comment in unsupported_source_metadata_comments(text):
            errors.append(f"unsupported source metadata comment in opponent report draft: {comment}")

    if CONFIDENCE_LABEL_RE.search(public_text):
        errors.append("internal confidence labels must be rewritten into normal opponent-report prose")

    for pattern in OPEN_CALIBRATION_PATTERNS:
        if re.search(pattern, public_text, re.IGNORECASE):
            record_draft_calibration_issue(
                f"report draft still contains open calibration wording: {pattern}",
                errors,
                draft_calibration_notes,
                allow_draft_calibration_pending=allow_draft_calibration_pending,
            )

    questions = section_text(lines, "## 10. Otázky k obhajobě")
    question_count = defense_question_count(questions)
    if "?" not in questions:
        errors.append("defense questions section must contain at least one explicit question")
    if mode == "clean":
        validate_clean_report_shape(
            public_text,
            question_count=question_count,
            expected_report_controls=expected_report_controls,
            expected_report_controls_source=expected_report_controls_source,
            errors=errors,
        )

    points_section = section_text(lines, "## 11. Body a známka")
    points = [int(match.group(1)) for match in POINT_RE.finditer(points_section)]
    grades = [match.group(1).upper() for match in GRADE_RE.finditer(points_section)]
    if not points:
        record_draft_calibration_issue(
            "concrete numeric point value is required before the report draft can pass",
            errors,
            draft_calibration_notes,
            allow_draft_calibration_pending=allow_draft_calibration_pending,
        )
    if not grades:
        record_draft_calibration_issue(
            "concrete proposed grade is required before the report draft can pass",
            errors,
            draft_calibration_notes,
            allow_draft_calibration_pending=allow_draft_calibration_pending,
        )
    for point_value in points:
        if point_value < 0 or point_value > 100:
            errors.append(f"point value outside 0-100 range: {point_value}")

    private_comment = section_text(lines, PRIVATE_COMMENT_HEADING).strip()
    private_comment_nonspace_chars = len(re.sub(r"\s+", "", private_comment))
    if private_comment_nonspace_chars < PRIVATE_COMMENT_MIN_NONSPACE_CHARS:
        record_draft_calibration_issue(
            "private student comment is too short to be a calibrated IS comment "
            f"({private_comment_nonspace_chars} non-whitespace characters)",
            errors,
            draft_calibration_notes,
            allow_draft_calibration_pending=allow_draft_calibration_pending,
        )

    form_fields, duplicate_fields = parse_colon_fields(section_text(lines, IS_FORM_SECTION_HEADING))
    for duplicate_field in duplicate_fields:
        if duplicate_field in IS_SELECT_FIELDS or duplicate_field in IS_POINT_FIELDS:
            errors.append(f"duplicate IS form field: {duplicate_field}")
    for field, allowed_values in IS_SELECT_FIELDS.items():
        selection_value = form_fields.get(field)
        if not selection_value:
            record_draft_calibration_issue(
                f"missing IS form selection: {field}",
                errors,
                draft_calibration_notes,
                allow_draft_calibration_pending=allow_draft_calibration_pending,
            )
        elif selection_value not in allowed_values and is_open_calibration_text(selection_value):
            record_draft_calibration_issue(
                f"invalid IS form selection for {field}: {selection_value}",
                errors,
                draft_calibration_notes,
                allow_draft_calibration_pending=allow_draft_calibration_pending,
            )
        elif selection_value not in allowed_values:
            errors.append(f"invalid IS form selection for {field}: {selection_value}")
    for field in IS_POINT_FIELDS:
        field_value = form_fields.get(field)
        if not field_value:
            record_draft_calibration_issue(
                f"missing IS form points: {field}",
                errors,
                draft_calibration_notes,
                allow_draft_calibration_pending=allow_draft_calibration_pending,
            )
            continue
        parsed = parse_point_value(field_value)
        if parsed is None and is_open_calibration_text(field_value):
            record_draft_calibration_issue(
                f"invalid IS form point value for {field}: {field_value}",
                errors,
                draft_calibration_notes,
                allow_draft_calibration_pending=allow_draft_calibration_pending,
            )
        elif parsed is None:
            errors.append(f"invalid IS form point value for {field}: {field_value}")
        elif parsed < 0 or parsed > 100:
            errors.append(f"IS form point value outside 0-100 range for {field}: {parsed}")
    if expected_report_controls:
        validate_expected_report_controls(
            expected_report_controls,
            source_label=expected_report_controls_source,
            form_fields=form_fields,
            points=points,
            grades=grades,
            question_count=question_count,
            private_comment_nonspace_chars=private_comment_nonspace_chars,
            errors=errors,
            notes=draft_calibration_notes,
            allow_draft_calibration_pending=allow_draft_calibration_pending,
        )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument("--mode", choices=("canonical", "clean"), default="canonical")
    parser.add_argument("--path", help="round-relative report draft path")
    parser.add_argument(
        "--allow-draft-calibration-pending",
        action="store_true",
        help=(
            "treat missing/unfinished points, grade, IS-point fields, and private-comment calibration as "
            "non-blocking draft status while still validating reviewed materials, trace hashes, structure, "
            "and privacy leaks"
        ),
    )
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
    draft_calibration_notes: list[str] = []
    run_round_ready(root, args.case_id, round_id, errors)
    run_opponent_materials_check(root, args.case_id, round_id, errors)
    trace_errors = validate_structured_evidence_artifact(
        round_dir,
        TRACE_REL,
        case_id=args.case_id,
        round_id=round_id,
    )
    errors.extend(trace_errors)
    trace = load_json_object(round_dir / TRACE_REL, TRACE_REL.as_posix(), errors)
    basis = load_bound_report_calibration_basis(
        round_dir,
        trace,
        case_id=args.case_id,
        round_id=round_id,
        errors=errors,
    )
    expected_controls = report_calibration_expected_controls(basis) if basis is not None else {}
    basis_hash = trace.get("report_calibration_basis_sha256") if isinstance(trace, dict) else None
    expected_controls_source = (
        f"{REPORT_CALIBRATION_BASIS_REL} sha256={basis_hash}"
        if isinstance(basis_hash, str)
        else "report calibration basis"
    )

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
            validate_calibration_metadata(text, trace, errors)
            public_text = strip_metadata_comments(text)
        check_text(
            text,
            public_text,
            errors,
            mode=args.mode,
            allow_draft_calibration_pending=args.allow_draft_calibration_pending,
            draft_calibration_notes=draft_calibration_notes,
            expected_report_controls=expected_controls,
            expected_report_controls_source=expected_controls_source,
        )

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
    if draft_calibration_notes:
        print("Opponent report draft calibration pending:")
        for note in draft_calibration_notes:
            print(f"- {note}")
    print(f"Opponent report {args.mode} check passed")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
