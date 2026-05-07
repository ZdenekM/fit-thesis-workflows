"""Create a structured opponent-report draft from reviewed opponent materials."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
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
from thesis_review_workflow.markdown_utils import simple_table_rows as parse_markdown_rows
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.structured_evidence import validate_structured_evidence_artifact

MATERIALS_REL = Path("outputs/oponent_podklady_revidovane.md")
DRAFT_REL = Path("work/oponent_posudek_draft.md")
CODE_REPRO_REL = Path("work/code_reproducibility.json")
EVIDENCE_REQUIREMENTS_REL = Path("work/evidence_requirements.json")

IS_ITEMS = (
    ("Náročnost zadání", ("narocnost", "náročnost")),
    ("Rozsah splnění požadavků zadání", ("rozsah splneni", "rozsah splnění", "splneni zadani", "splnění zadání")),
    ("Rozsah technické zprávy", ("rozsah technicke", "rozsah technické")),
    ("Prezentační úroveň technické zprávy", ("prezentacni", "prezentační")),
    ("Formální úprava technické zprávy", ("formalni", "formální")),
    ("Práce s literaturou", ("literatur", "citac", "citac")),
    ("Realizační výstup", ("realizacni", "realizační", "vystup", "výstup")),
    ("Využitelnost výsledku", ("vyuzitelnost", "využitelnost")),
    ("Celkové hodnocení", ("celkove", "celkové")),
)


def run_required(root: Path, command: list[str]) -> None:
    result = subprocess.run(
        resolve_repo_command(root, command),
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
        raise SystemExit(f"Required command failed: {' '.join(command)}\n{detail}")


def normalized(value: str) -> str:
    replacements = str.maketrans("ěščřžýáíéúůňťďóĚŠČŘŽÝÁÍÉÚŮŇŤĎÓ", "escrzyaieuuntdoESCRZYAIEUUNTDO")
    value = value.translate(replacements).lower()
    return re.sub(r"\s+", " ", value).strip()


def is_rows(materials: str) -> dict[str, str]:
    section = section_by_number(materials, 9)
    rows = parse_markdown_rows(section)
    result: dict[str, str] = {}
    if rows and any("polozka" in normalized(cell) or "položka" in normalized(cell) for cell in rows[0]):
        rows = rows[1:]
    for cells in rows:
        item = normalized(cells[0])
        formulation = cells[-1].strip() if cells else ""
        evidence = cells[2].strip() if len(cells) >= 3 else ""
        if not formulation or formulation in {"-", "n/a"}:
            formulation = evidence
        for title, tokens in IS_ITEMS:
            if any(token in item for token in tokens) and formulation:
                result[title] = formulation
    return result


def bullets_from_section(section: str) -> list[str]:
    bullets = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            bullets.append(stripped[2:].strip())
        elif "?" in stripped and len(stripped) > 8:
            bullets.append(stripped.strip("-* "))
    return bullets


def fallback_item_text(title: str) -> str:
    return (
        "Z dostupných revidovaných podkladů není pro tuto položku připravena hotová "
        f"formulace. Před odevzdáním ji zkalibrujte proti části revidovaných podkladů věnované položce {title.lower()}."
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def uncertain_claims(materials: str) -> list[str]:
    section = section_by_number(materials, 6)
    claims = []
    for cells in parse_markdown_rows(section):
        joined = " ".join(cells).lower()
        if (
            "[neovereno]" in joined
            or "[neověřeno]" in joined
            or "[k rucni kontrole]" in joined
            or "[k ruční kontrole]" in joined
        ):
            if cells and cells[0].strip() and "tvrzeni" not in normalized(cells[0]):
                claims.append(cells[0].strip().strip('"'))
    return claims


def advisory_reproducibility_note(round_dir: Path) -> str | None:
    path = round_dir / CODE_REPRO_REL
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return f"Zkontrolovat nevalidní advisory artefakt `{CODE_REPRO_REL.as_posix()}`."
    if not isinstance(loaded, dict):
        return f"Zkontrolovat nevalidní advisory artefakt `{CODE_REPRO_REL.as_posix()}`."
    classification = loaded.get("classification")
    if not isinstance(classification, str) or not classification:
        classification = "nezaznamenáno"
    return f"Zohlednit statickou klasifikaci reprodukovatelnosti kódu: {classification}."


def advisory_evidence_requirements_note(round_dir: Path, case_id: str, round_id: str) -> str | None:
    path = round_dir / EVIDENCE_REQUIREMENTS_REL
    if not path.is_file():
        return None
    errors = validate_structured_evidence_artifact(
        round_dir,
        EVIDENCE_REQUIREMENTS_REL,
        case_id=case_id,
        round_id=round_id,
    )
    if errors:
        return "Zkontrolovat nevalidní strukturovaný artefakt evidence requirements."
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "Zkontrolovat nevalidní strukturovaný artefakt evidence requirements."
    if not isinstance(loaded, dict):
        return "Zkontrolovat nevalidní strukturovaný artefakt evidence requirements."
    requirements = loaded.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        return None
    categories = sorted(
        f"{item.get('category')}:{item.get('state')}"
        for item in requirements
        if isinstance(item, dict) and isinstance(item.get("category"), str) and isinstance(item.get("state"), str)
    )
    suffix = ", ".join(categories) if categories else "nezarazeno"
    return f"Zohlednit strukturované evidence requirements: {suffix}."


def build_report(materials: str, materials_hash: str, *, advisory_notes: list[str] | None = None) -> str:
    rows = is_rows(materials)
    strengths = bullets_from_section(section_by_number(materials, 7))
    risks = bullets_from_section(section_by_number(materials, 8))
    questions = bullets_from_section(section_by_number(materials, 14))
    uncertain = uncertain_claims(materials)
    if not questions:
        questions = [
            "Které hlavní omezení nebo ručně neověřený bod z revidovaných podkladů student při obhajobě nejlépe doloží?"
        ]
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    lines = [
        "<!-- source_materials_path: outputs/oponent_podklady_revidovane.md -->",
        f"<!-- source_materials_sha256: {materials_hash} -->",
        "# Návrh oponentského posudku",
        "",
        f"Datum přípravy draftu: {created}",
        "Stav: pracovní draft pro kontrolu oponentem; před vložením do IS ověřte bodové hodnocení a formulace.",
        "",
    ]
    for index, (title, _) in enumerate(IS_ITEMS, start=1):
        lines.append(f"## {index}. {title}")
        lines.append("")
        lines.append(rows.get(title) or fallback_item_text(title))
        lines.append("")

    lines.extend(
        [
            "## 10. Otázky k obhajobě",
            "",
        ]
    )
    for question in questions:
        question = question if question.endswith("?") else question.rstrip(".") + "?"
        lines.append(f"- {question}")
    lines.extend(
        [
            "",
            "## 11. Body a známka",
            "",
            "Bodové hodnocení: k ruční kalibraci podle splnění zadání, technické kvality, "
            "ověřitelnosti výsledků a rizik níže.",
            "Navržená známka: k ruční kalibraci ve stejné interpretaci jako bodové hodnocení.",
            "",
            "## 12. Před odevzdáním",
            "",
            "- Zkontrolovat, že slovní hodnocení odpovídá bodům a známce.",
            "- Zkontrolovat, že žádné tvrzení nepřekračuje jistotu z dostupných podkladů.",
            "- Zkontrolovat, že otázky k obhajobě míří na podstatné a zodpověditelné body.",
        ]
    )
    if strengths:
        lines.append("- Do celkového hodnocení zapracovat podložené silné stránky: " + "; ".join(strengths[:3]) + ".")
    if risks:
        lines.append("- Do celkového hodnocení zapracovat hlavní rizika: " + "; ".join(risks[:3]) + ".")
    for claim in uncertain[:5]:
        lines.append(f"- Zachovat opatrnou formulaci pro ručně neověřený bod: {claim}")
    for note in advisory_notes or []:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite an existing work/oponent_posudek_draft.md")
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    args = parser.parse_args(argv[1:])

    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    run_required(root, ["scripts/check-round-ready", args.case_id, round_id])
    run_required(root, ["scripts/check-opponent-materials", args.case_id, round_id])

    materials_path = round_dir / MATERIALS_REL
    if not materials_path.is_file():
        raise SystemExit(f"Missing reviewed opponent materials: {MATERIALS_REL.as_posix()}")
    draft_path = round_dir / DRAFT_REL
    if draft_path.exists() and not args.force:
        raise SystemExit(f"Refusing to overwrite existing draft without --force: {DRAFT_REL.as_posix()}")
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    advisory_notes = [
        note
        for note in [
            advisory_reproducibility_note(round_dir),
            advisory_evidence_requirements_note(round_dir, args.case_id, round_id),
        ]
        if note
    ]
    draft_path.write_text(
        build_report(
            materials_path.read_text(encoding="utf-8"),
            sha256_file(materials_path),
            advisory_notes=advisory_notes,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {rel_repo(root, draft_path)}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
