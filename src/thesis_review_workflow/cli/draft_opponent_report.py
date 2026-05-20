"""Create an opponent-report bridge draft from reviewed structured trace data."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.commands import command_display, repo_command_environment, resolve_repo_command
from thesis_review_workflow.opponent_calibration import (
    OPPONENT_CALIBRATION_ADVISORY_REL,
    OPPONENT_CALIBRATION_USE_REL,
    validate_opponent_calibration_artifact,
)
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.report_calibration import (
    REPORT_CALIBRATION_BASIS_REL,
    report_calibration_applied_preference_ids,
    report_calibration_expected_control_keys,
    validate_report_calibration_artifact,
)
from thesis_review_workflow.structured_evidence import validate_structured_evidence_artifact

MATERIALS_REL = Path("outputs/oponent_podklady_revidovane.md")
DRAFT_REL = Path("work/oponent_posudek_draft.md")
TRACE_REL = Path("work/opponent_report_trace.json")
CODE_REPRO_REL = Path("work/code_reproducibility.json")
EVIDENCE_REQUIREMENTS_REL = Path("work/evidence_requirements.json")
CALIBRATION_CONTEXT_RELS = (Path(OPPONENT_CALIBRATION_USE_REL), Path(OPPONENT_CALIBRATION_ADVISORY_REL))

IS_SECTIONS = (
    ("assignment_difficulty", "Náročnost zadání"),
    ("assignment_fulfillment", "Rozsah splnění požadavků zadání"),
    ("technical_report_scope", "Rozsah technické zprávy"),
    ("technical_report_presentation", "Prezentační úroveň technické zprávy"),
    ("technical_report_formal_level", "Formální úprava technické zprávy"),
    ("literature_work", "Práce s literaturou"),
    ("implementation_output", "Realizační výstup"),
    ("result_usability", "Využitelnost výsledku"),
    ("overall_assessment", "Celkové hodnocení"),
)

IS_FORM_SECTION_HEADING = "## IS formulář (výběry a body)"
IS_FORM_PLACEHOLDERS = (
    "Náročnost zadání: k ručnímu výběru z nabídky IS",
    "Rozsah splnění požadavků zadání: k ručnímu výběru z nabídky IS",
    "Rozsah technické zprávy: k ručnímu výběru z nabídky IS",
    "Prezentační úroveň technické zprávy: k ručnímu zadání bodů 0-100",
    "Formální úprava technické zprávy: k ručnímu zadání bodů 0-100",
    "Práce s literaturou: k ručnímu zadání bodů 0-100",
    "Realizační výstup: k ručnímu zadání bodů 0-100",
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
        raise SystemExit(f"Required command failed: {command_display(command)}\n{detail}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {label}: {exc.msg}") from exc
    if not isinstance(loaded, dict):
        raise SystemExit(f"Invalid JSON in {label}: expected object")
    return loaded


def load_valid_trace(round_dir: Path, case_id: str, round_id: str) -> dict[str, Any]:
    errors = validate_structured_evidence_artifact(
        round_dir,
        TRACE_REL,
        case_id=case_id,
        round_id=round_id,
    )
    if errors:
        detail = "\n".join(f"ERROR: {error}" for error in errors)
        raise SystemExit(
            "Missing or invalid `work/opponent_report_trace.json`; create it with an explicitly "
            f"authorized opponent-report-trace reviewer before drafting.\n{detail}"
        )
    return load_json_object(round_dir / TRACE_REL, TRACE_REL.as_posix())


def load_bound_report_calibration_basis(
    round_dir: Path, trace: dict[str, Any], case_id: str, round_id: str
) -> dict[str, Any] | None:
    basis_path = trace.get("report_calibration_basis_path")
    basis_hash = trace.get("report_calibration_basis_sha256")
    if basis_path is None and basis_hash is None:
        return None
    if basis_path != REPORT_CALIBRATION_BASIS_REL:
        raise SystemExit(f"Invalid report calibration basis path in trace: {basis_path!r}")
    basis_file = round_dir / REPORT_CALIBRATION_BASIS_REL
    if not isinstance(basis_hash, str) or not basis_file.is_file() or basis_hash != sha256_file(basis_file):
        raise SystemExit("Invalid report calibration basis binding in trace: stale or missing hash")
    errors = validate_report_calibration_artifact(
        round_dir,
        REPORT_CALIBRATION_BASIS_REL,
        case_id=case_id,
        round_id=round_id,
    )
    if errors:
        detail = "\n".join(f"ERROR: {error}" for error in errors)
        raise SystemExit("Invalid `work/report_calibration_basis.json`; refresh it before drafting.\n" f"{detail}")
    return load_json_object(round_dir / REPORT_CALIBRATION_BASIS_REL, REPORT_CALIBRATION_BASIS_REL)


def validate_current_case_calibration(round_dir: Path, case_id: str, round_id: str) -> str | None:
    existing = [rel_path for rel_path in CALIBRATION_CONTEXT_RELS if (round_dir / rel_path).is_file()]
    if len(existing) > 1:
        paths = ", ".join(path.as_posix() for path in existing)
        raise SystemExit(f"Conflicting current-case opponent calibration artifacts: {paths}")
    if not existing:
        return None
    rel_path = existing[0]
    errors = validate_opponent_calibration_artifact(
        round_dir,
        rel_path,
        case_id=case_id,
        round_id=round_id,
    )
    if errors:
        detail = "\n".join(f"ERROR: {error}" for error in errors)
        raise SystemExit(
            "Invalid current-case opponent calibration artifact; refresh or remove it before drafting.\n" f"{detail}"
        )
    return rel_path.as_posix()


def trace_items_by_id(trace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = trace.get("is_items")
    if not isinstance(items, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("item_id"), str):
            result[item["item_id"]] = item
    return result


def trace_text_items(trace: dict[str, Any], field: str, text_field: str) -> list[str]:
    items = trace.get(field)
    if not isinstance(items, list):
        return []
    values: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get(text_field)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
    return values


def trace_uncertainty_items(trace: dict[str, Any]) -> list[str]:
    items = trace.get("uncertainty_items")
    if not isinstance(items, list):
        return []
    result: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        claim_id = item.get("claim_id")
        summary = item.get("summary")
        instruction = item.get("handling_instruction")
        status = item.get("status")
        target_ids = item.get("target_section_ids")
        if (
            isinstance(claim_id, str)
            and isinstance(summary, str)
            and isinstance(instruction, str)
            and isinstance(status, str)
            and isinstance(target_ids, list)
        ):
            targets = ", ".join(str(target) for target in target_ids)
            result.append(f"{claim_id}: {summary}; stav: {status}; cílové položky: {targets}; pokyn: {instruction}.")
    return result


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


def build_report(
    trace: dict[str, Any],
    *,
    trace_hash: str,
    materials_hash: str,
    report_calibration_basis: dict[str, Any] | None = None,
    report_calibration_basis_hash: str | None = None,
    advisory_notes: list[str] | None = None,
) -> str:
    items = trace_items_by_id(trace)
    questions = trace_text_items(trace, "defense_questions", "question")
    checks = trace_text_items(trace, "pre_submission_checks", "instruction")
    uncertainty_items = trace_uncertainty_items(trace)
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    calibration_comments: list[str] = []
    calibration_checks: list[str] = []
    if report_calibration_basis is not None:
        preference_ids = report_calibration_applied_preference_ids(report_calibration_basis)
        expected_controls = sorted(report_calibration_expected_control_keys(report_calibration_basis))
        calibration_comments.extend(
            [
                f"<!-- source_report_calibration_basis_path: {REPORT_CALIBRATION_BASIS_REL} -->",
                f"<!-- source_report_calibration_basis_sha256: {report_calibration_basis_hash or ''} -->",
            ]
        )
        if preference_ids:
            calibration_comments.append(
                "<!-- source_report_calibration_preference_ids: " + ", ".join(preference_ids) + " -->"
            )
        if expected_controls:
            calibration_comments.append(
                "<!-- source_report_calibration_expected_controls: " + ", ".join(expected_controls) + " -->"
            )
            calibration_checks.append(
                "Ověřit, že výběry IS, body, známka, počet otázek a neveřejný komentář "
                "odpovídají strukturované reportové kalibraci."
            )

    lines = [
        f"<!-- source_trace_path: {TRACE_REL.as_posix()} -->",
        f"<!-- source_trace_sha256: {trace_hash} -->",
        f"<!-- source_materials_path: {MATERIALS_REL.as_posix()} -->",
        f"<!-- source_materials_sha256: {materials_hash} -->",
        *calibration_comments,
        "# Návrh oponentského posudku",
        "",
        f"Datum přípravy draftu: {created}",
        "Stav: pracovní draft pro kontrolu oponentem; před vložením do IS ověřte bodové hodnocení a formulace.",
        "",
        IS_FORM_SECTION_HEADING,
        "",
        *IS_FORM_PLACEHOLDERS,
        "",
    ]
    for index, (item_id, title) in enumerate(IS_SECTIONS, start=1):
        trace_item = items[item_id]
        formulation = trace_item["formulation"]
        lines.append(f"## {index}. {title}")
        lines.append("")
        lines.append(str(formulation).strip())
        lines.append("")

    lines.extend(["## 10. Otázky k obhajobě", ""])
    for question in questions:
        rendered = question if question.endswith("?") else question.rstrip(".") + "?"
        lines.append(f"- {rendered}")
    lines.extend(
        [
            "",
            "## 11. Body a známka",
            "",
            "Bodové hodnocení: k ruční kalibraci podle splnění zadání, technické kvality, "
            "ověřitelnosti výsledků a rizik níže.",
            "Navržená známka: k ruční kalibraci ve stejné interpretaci jako bodové hodnocení.",
            "",
            "## Komentář pro studenta (neveřejná část)",
            "",
            "Děkuji za zpracovanou práci. Veřejné hodnocení výše shrnuje hlavní důvody bodového "
            "hodnocení a známky. Pro neveřejný komentář studentovi zde stručně vysvětlete, co se "
            "podle vás povedlo, proč hodnocení není vyšší, co si má student připravit k obhajobě "
            "a jaké konkrétní kroky by mu pomohly při dalším rozvoji práce. Neuvádějte interní "
            "cesty, hash hodnoty ani auditní detaily; pište věcně, přímo a podpůrně.",
            "",
            "## 12. Před odevzdáním",
            "",
        ]
    )
    for check in checks:
        lines.append(f"- {check}")
    for check in calibration_checks:
        lines.append(f"- {check}")
    for uncertainty in uncertainty_items:
        lines.append(f"- Zohlednit strukturovaný uncertainty ledger: {uncertainty}")
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
    trace_path = round_dir / TRACE_REL
    trace = load_valid_trace(round_dir, args.case_id, round_id)
    report_calibration_basis = load_bound_report_calibration_basis(round_dir, trace, args.case_id, round_id)
    if not isinstance(trace.get("calibration_context"), dict):
        validate_current_case_calibration(round_dir, args.case_id, round_id)
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
            trace,
            trace_hash=sha256_file(trace_path),
            materials_hash=sha256_file(materials_path),
            report_calibration_basis=report_calibration_basis,
            report_calibration_basis_hash=(
                sha256_file(round_dir / REPORT_CALIBRATION_BASIS_REL) if report_calibration_basis is not None else None
            ),
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
