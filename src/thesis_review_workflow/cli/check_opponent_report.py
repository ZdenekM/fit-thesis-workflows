"""Validate an opponent-report draft shape and safety before IS submission."""

from __future__ import annotations

import argparse
import hashlib
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
from thesis_review_workflow.markdown_utils import numbered_section_text as section_by_number
from thesis_review_workflow.markdown_utils import section_body as markdown_section_body
from thesis_review_workflow.markdown_utils import section_text as markdown_section_text
from thesis_review_workflow.markdown_utils import simple_table_rows as parse_markdown_rows
from thesis_review_workflow.paths import is_safe_round_relative_path

DEFAULT_DRAFT = Path("work/oponent_posudek_draft.md")
MATERIALS_REL = Path("outputs/oponent_podklady_revidovane.md")

REQUIRED_HEADINGS = (
    "# Návrh oponentského posudku",
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
    "## 12. Před odevzdáním",
)

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
    r"\bfeedback_k_posudku\.md\b",
    r"\bgithub_code_intake\.md\b",
    r"\brevision_diff\.md\b",
    r"\breference_report_comparison\.md\b",
    r"\bpr_contribution_review\.md\b",
    r"\bdemo_artifacts_review\.md\b",
    r"\bcode_consistency\.md\b",
    r"\bcode_quality_review\.md\b",
    r"\bfigure_media_review\.md\b",
    r"\btypography_formal_review\.md\b",
)

COACHING_PATTERNS = (
    r"\bstudent(?:ovi|ka|ce)?\s+doporučuji\b",
    r"\bdoporučuji\s+student(?:ovi|ce)?\b",
    r"\bměl(?:a)?\s+bys(?:te)?\b",
    r"\bpro další verzi práce\b",
)

CONFIDENCE_LABEL_RE = re.compile(r"\[(?:FAKT|INTERPRETACE|ODHAD|NEOV[EĚ]R[EŘ]NO|K RU[CČ]N[IÍ] KONTROLE)\]")
POINT_RE = re.compile(r"\b(?:Body|Bodové hodnocení)\s*:\s*(\d{1,3})\b", re.IGNORECASE)
GRADE_RE = re.compile(r"\b(?:Známka|Navržená známka)\s*:\s*([A-F])\b", re.IGNORECASE)
SOURCE_PATH_RE = re.compile(r"<!--\s*source_materials_path:\s*([^>]+?)\s*-->")
SOURCE_SHA_RE = re.compile(r"<!--\s*source_materials_sha256:\s*([0-9a-f]{64})\s*-->")
UNCERTAINTY_TERMS = (
    "neověř",
    "neover",
    "nelze",
    "z dostupných podkladů",
    "z dostupnych podkladu",
    "ruční kontrol",
    "rucni kontrol",
    "nebylo možné",
    "nebylo mozne",
)
OPEN_CALIBRATION_PATTERNS = (
    r"\bpracovn[ií]\s+draft\b",
    r"\bk\s+ru[cč]n[ií]\s+kalibraci\b",
    r"\bpřed\s+vložen[ií]m\s+do\s+IS\s+ověřte\b",
    r"\bnen[ií]\s+.*\bhotov[aá]\s+formulace\b",
    r"\bzkalibrujte\b",
)
GENERIC_UNCERTAINTY_TOKENS = {
    "tvrzeni",
    "tvrzení",
    "plny",
    "plný",
    "byl",
    "byla",
    "bylo",
    "neni",
    "není",
    "nebyl",
    "nebyla",
    "nebylo",
    "overen",
    "ověřen",
    "overena",
    "ověřena",
    "overeno",
    "ověřeno",
}


def is_safe_relative(value: str) -> bool:
    return is_safe_round_relative_path(value)


def section_body(lines: list[str], heading: str) -> list[str] | None:
    return markdown_section_body(lines, heading, stop_pattern=r"^##\s+")


def section_text(lines: list[str], heading: str) -> str:
    return markdown_section_text(lines, heading, stop_pattern=r"^##\s+")


def nonempty_body(lines: list[str], heading: str) -> bool:
    body = section_text(lines, heading)
    return bool(body and not re.fullmatch(r"[-\s]*", body))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strip_metadata_comments(text: str) -> str:
    return re.sub(r"^<!--\s*source_materials_(?:path|sha256):.*?-->\s*\n?", "", text, flags=re.MULTILINE)


def validate_source_metadata(text: str, materials_path: Path, path_arg: str, errors: list[str]) -> None:
    path_match = SOURCE_PATH_RE.search(text)
    sha_match = SOURCE_SHA_RE.search(text)
    metadata_required = path_arg == DEFAULT_DRAFT.as_posix()
    if not path_match and metadata_required:
        errors.append("missing source materials path metadata comment")
    elif path_match and path_match.group(1).strip() != MATERIALS_REL.as_posix():
        errors.append(
            "source materials path metadata must be " f"{MATERIALS_REL.as_posix()}, got {path_match.group(1).strip()}"
        )
    if not sha_match and metadata_required:
        errors.append("missing source materials sha256 metadata comment")
    elif sha_match and materials_path.is_file() and sha_match.group(1) != sha256_file(materials_path):
        errors.append("opponent report draft is stale: reviewed opponent materials hash changed")


def normalize_tokens(value: str) -> list[str]:
    tokens = re.findall(r"[A-Za-zÁ-Žá-ž0-9]{5,}", value.lower())
    return [token for token in tokens if token not in GENERIC_UNCERTAINTY_TOKENS]


def uncertain_claims(materials_text: str) -> list[str]:
    section = section_by_number(materials_text, 6)
    claims: list[str] = []
    for cells in parse_markdown_rows(section):
        joined = " ".join(cells).lower()
        if (
            "[neovereno]" in joined
            or "[neověřeno]" in joined
            or "[k rucni kontrole]" in joined
            or "[k ruční kontrole]" in joined
        ):
            if cells and cells[0].strip() and "tvrzeni" not in cells[0].lower() and "tvrzení" not in cells[0].lower():
                claims.append(cells[0].strip().strip('"'))
    return claims


def text_chunks(text: str) -> list[str]:
    chunks: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("- ", "* ")):
            chunks.append(stripped[2:].lower())
        else:
            chunks.extend(chunk.strip().lower() for chunk in re.split(r"(?<=[.!?])\s+", stripped) if chunk.strip())
    return chunks


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


def check_text(text: str, public_text: str, materials_text: str, errors: list[str]) -> None:
    lines = text.splitlines()
    for heading in REQUIRED_HEADINGS:
        if heading not in lines:
            errors.append(f"missing required heading: {heading}")
        elif heading.startswith("## ") and not nonempty_body(lines, heading):
            errors.append(f"empty report section: {heading}")

    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, public_text, re.IGNORECASE | re.MULTILINE):
            errors.append(f"placeholder remains in report draft: {pattern}")

    for pattern in INTERNAL_PATTERNS:
        if re.search(pattern, public_text, re.IGNORECASE):
            errors.append(f"internal workflow path or artifact leaked into report draft: {pattern}")

    for pattern in COACHING_PATTERNS:
        if re.search(pattern, public_text, re.IGNORECASE):
            errors.append(f"student-coaching wording does not belong in opponent report: {pattern}")

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
    for value in points:
        if value < 0 or value > 100:
            errors.append(f"point value outside 0-100 range: {value}")

    lower_materials = materials_text.lower()
    lower_text = public_text.lower()
    if (
        "[neovereno]" in lower_materials
        or "[neověřeno]" in lower_materials
        or "[k rucni kontrole]" in lower_materials
        or "[k ruční kontrole]" in lower_materials
    ):
        if not any(term in lower_text for term in UNCERTAINTY_TERMS):
            errors.append(
                "reviewed materials contain uncertainty/manual-check labels, "
                "but report draft does not preserve any uncertainty wording"
            )
    chunks = text_chunks(public_text)
    for claim in uncertain_claims(materials_text):
        tokens = normalize_tokens(claim)[:3]
        if tokens and not any(
            any(token in chunk for token in tokens) and any(term in chunk for term in UNCERTAINTY_TERMS)
            for chunk in chunks
        ):
            errors.append(f"uncertain source claim is not preserved in report draft wording: {claim}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument("--path", default=DEFAULT_DRAFT.as_posix(), help="round-relative report draft path")
    args = parser.parse_args(argv[1:])

    validate_id("CASE_ID", args.case_id)
    if not is_safe_relative(args.path):
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

    draft_path = round_dir / args.path
    if not draft_path.is_file():
        errors.append(f"missing opponent report draft: {args.path}")
    materials_path = round_dir / MATERIALS_REL
    if not materials_path.is_file():
        errors.append(f"missing reviewed opponent materials: {MATERIALS_REL.as_posix()}")

    if draft_path.is_file():
        materials_text = materials_path.read_text(encoding="utf-8") if materials_path.is_file() else ""
        text = draft_path.read_text(encoding="utf-8")
        validate_source_metadata(text, materials_path, args.path, errors)
        check_text(text, strip_metadata_comments(text), materials_text, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Opponent report draft check passed")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
