import hashlib
import json
from pathlib import Path

from thesis_review_workflow.supervisor_report import (
    SUPERVISOR_REPORT_DRAFT_REL,
    SUPERVISOR_REPORT_INPUT_REL,
    SUPERVISOR_REPORT_TRACE_REL,
    check_supervisor_report_intake,
    extract_markdown_grade_points,
    public_report_text,
    validate_draft_metadata,
    validate_report_markdown,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_intake(round_dir: Path, *, activity: str = "dobra") -> Path:
    path = round_dir / SUPERVISOR_REPORT_INPUT_REL
    path.parent.mkdir(parents=True)
    path.write_text(
        f"""# Supervisor Report Intake

## Informace k zadani

Narocnost prace: stredni
Spokojenost s dosazenymi vysledky: spokojen
Splneni zadani: splneno

## Prace s literaturou

Aktivita studenta pri ziskavani materialu: primerena
Jak student materialy vyuzival: vhodne
Co je explicitne nezname / nehodnotit:

## Aktivita behem reseni, konzultace, komunikace

Aktivita a samostatnost: {activity}
Dodrzovani dohodnutych terminu: ano
Prubezne konzultace: ano
Pripravenost na konzultace: dobra
Komunikace: dobra
Co je explicitne nezname / nehodnotit:

## Aktivita pri dokoncovani

Dokonceni s predstihem: ano
Konzultace definitivniho obsahu: ano
Posledni faze prace: standardni
Co je explicitne nezname / nehodnotit:

## Celkove hodnoceni

Navrhovana znamka: B
Navrhovane body: 82

## Publikacni cinnost, oceneni

Publikace: nejsou
Open-source zverejneni softwaru:
Ohlasy:
Oceneni:
Pokud nic z toho neni, jak to formulovat: bez publikaci

## Komentar pro studenta

Soukromy komentar viditelny studentovi v IS: dobra prace
""",
        encoding="utf-8",
    )
    return path


def valid_report(trace_hash: str, input_hash: str) -> str:
    return f"""<!-- source_trace_path: {SUPERVISOR_REPORT_TRACE_REL} -->
<!-- source_trace_sha256: {trace_hash} -->
<!-- supervisor_input_path: {SUPERVISOR_REPORT_INPUT_REL} -->
<!-- supervisor_input_sha256: {input_hash} -->
# Návrh posudku vedoucího

## Informace k zadání

Zadání bylo splněno.

## Práce s literaturou

Student s literaturou pracoval přiměřeně.

## Aktivita během řešení, konzultace, komunikace

Student konzultoval průběžně.

## Aktivita při dokončování

Definitivní obsah byl konzultován.

## Publikační činnost, ocenění

Publikace nejsou.

## Celkové hodnocení

Známka: B
Body: 82

## Komentář pro studenta

Děkuji za práci.
"""


def test_supervisor_report_intake_accepts_required_process_fields(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    write_intake(round_dir)

    result = check_supervisor_report_intake(round_dir)

    assert result.errors == ()


def test_supervisor_report_intake_requires_unknown_marker_when_process_field_missing(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    write_intake(round_dir, activity="")

    result = check_supervisor_report_intake(round_dir)

    assert any("Aktivita a samostatnost" in error for error in result.errors)


def test_validate_supervisor_report_markdown_blocks_public_internal_paths() -> None:
    text = valid_report("0" * 64, "1" * 64).replace(
        "Zadání bylo splněno.",
        "Zadání bylo splněno podle work/review_manifest.json.",
    )

    errors = validate_report_markdown(text, require_grade_points=True)

    assert any("internal workflow path" in error for error in errors)


def test_validate_supervisor_report_markdown_blocks_private_internal_paths() -> None:
    text = valid_report("0" * 64, "1" * 64).replace(
        "Děkuji za práci.",
        "Podívejte se prosím na work/review_manifest.json.",
    )

    errors = validate_report_markdown(text, require_grade_points=True)

    assert any("internal workflow path" in error for error in errors)


def test_validate_supervisor_report_markdown_blocks_visible_top_matter() -> None:
    text = valid_report("0" * 64, "1" * 64).replace(
        "# Návrh posudku vedoucího\n\n## Informace k zadání",
        "# Návrh posudku vedoucího\n\nStav: pracovní draft\n\n## Informace k zadání",
    )

    errors = validate_report_markdown(text, require_grade_points=True)

    assert "unexpected text between supervisor report title and first section" in errors


def test_public_report_text_does_not_remove_duplicate_official_text() -> None:
    text = valid_report("0" * 64, "1" * 64).replace(
        "Děkuji za práci.",
        "Známka: A\nBody: 95\nwork/review_manifest.json",
    )
    text = text.replace("Zadání bylo splněno.", "work/review_manifest.json")

    public = public_report_text(text)

    assert "work/review_manifest.json" in public


def test_extract_markdown_grade_points_reports_conflicts() -> None:
    text = valid_report("0" * 64, "1" * 64).replace("Body: 82", "Body: 82\nBody: 95")

    result = extract_markdown_grade_points(text, require=True)

    assert "supervisor report contains conflicting point values" in result.errors


def test_validate_supervisor_report_draft_metadata_detects_stale_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    input_path = write_intake(round_dir)
    trace_path = round_dir / SUPERVISOR_REPORT_TRACE_REL
    trace_path.parent.mkdir(parents=True)
    trace_path.write_text(json.dumps({"schema_version": "fixture"}) + "\n", encoding="utf-8")
    draft = valid_report("0" * 64, sha256_file(input_path))
    draft_path = round_dir / SUPERVISOR_REPORT_DRAFT_REL
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(draft, encoding="utf-8")

    errors: list[str] = []
    validate_draft_metadata(draft, round_dir, errors)

    assert any("source trace hash changed" in error for error in errors)
