"""Import a private Theses.cz similarity report into a thesis round."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.cases import MissingCurrentRound
from thesis_review_workflow.cases import repo_root as repo_root_core
from thesis_review_workflow.cases import resolve_round as resolve_round_core
from thesis_review_workflow.cli.extract_pdf_text import git_ignored, is_allowed_extract_path
from thesis_review_workflow.ids import validate_id
from thesis_review_workflow.paths import resolve_caller_path
from thesis_review_workflow.pdf_extracts import build_pdf_extract_manifest, pdf_extract_sidecar_path, pdftotext_version
from thesis_review_workflow.theses_similarity import (
    CURRENT_SUBMISSION_LINK_STATUSES,
    THESES_SIMILARITY_INTAKE_REL,
    build_intake_payload,
)

REPORT_PDF_REL = Path("inputs/theses_similarity/report.pdf")
REPORT_TEXT_REL = Path("extracted/theses_similarity/report.txt")
INTAKE_REL = Path(THESES_SIMILARITY_INTAKE_REL)


def usage() -> str:
    return (
        "Usage: scripts/import-theses-report CASE_ID [ROUND_ID] REPORT.pdf\n\n"
        "Copies a private Theses.cz similarity report into the ignored case workspace, "
        "extracts text with pdftotext, and writes work/theses_similarity/intake.json."
    )


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/import-theses-report",
        description="Import a private Theses.cz similarity report into a thesis round.",
        usage="scripts/import-theses-report CASE_ID [ROUND_ID] REPORT.pdf",
    )
    parser.add_argument("case_id")
    parser.add_argument("positionals", nargs="+", help="REPORT.pdf, or ROUND_ID REPORT.pdf")
    parser.add_argument(
        "--current-submission-link",
        choices=sorted(CURRENT_SUBMISSION_LINK_STATUSES),
        default="unverified",
        help="Explicit operator status for whether this report belongs to the current round submission.",
    )
    return parser


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    if len(args.positionals) not in {1, 2}:
        parser.error("expected REPORT.pdf, or ROUND_ID REPORT.pdf")
    args.round_id = args.positionals[0] if len(args.positionals) == 2 else None
    args.report_pdf = args.positionals[-1]
    return args


def compact_detail(value: str, *, limit: int = 600) -> str:
    text = "\n".join(line.strip() for line in value.splitlines() if line.strip())
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def run_text(args: list[str]) -> str:
    completed = subprocess.run(
        args,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        detail = compact_detail("\n".join(part for part in (completed.stderr, completed.stdout) if part))
        raise RuntimeError(detail or f"{args[0]} failed with exit code {completed.returncode}")
    return completed.stdout


def report_page_count(report_pdf: Path) -> tuple[int | None, list[str]]:
    if shutil.which("pdfinfo") is None:
        return None, ["Missing optional command: pdfinfo; report page count was not recorded."]
    try:
        output = run_text(["pdfinfo", str(report_pdf)])
    except RuntimeError:
        return None, ["pdfinfo failed; report page count was not recorded."]
    for line in output.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() == "Pages":
            try:
                return int(value.strip()), []
            except ValueError:
                return None, [f"pdfinfo returned a non-integer page count: {value.strip()}"]
    return None, ["pdfinfo output did not include a Pages field; report page count was not recorded."]


def extract_report_text(report_pdf: Path, output_txt: Path) -> None:
    if shutil.which("pdftotext") is None:
        raise RuntimeError("Missing required command: pdftotext")
    run_text(["pdftotext", "-layout", str(report_pdf), str(output_txt)])


def case_insensitive_collision(root: Path, path: Path) -> Path | None:
    rel = path.relative_to(root)
    current = root
    for part in rel.parts:
        if not current.is_dir():
            return None
        target = part.casefold()
        for existing in current.iterdir():
            if existing.name.casefold() == target and existing.name != part:
                return existing
        current = current / part
    return None


def ensure_private_target(root: Path, target: Path) -> None:
    rel = target.relative_to(root).as_posix()
    current = root
    for part in target.relative_to(root).parent.parts:
        current = current / part
        if current.is_symlink():
            symlink_rel = current.relative_to(root).as_posix()
            raise RuntimeError(f"Refusing to write Theses.cz report data through symlinked path: {symlink_rel}")
        if current.exists() and not current.is_dir():
            current_rel = current.relative_to(root).as_posix()
            raise RuntimeError(f"Refusing to write Theses.cz report data through non-directory path: {current_rel}")
    if target.is_symlink():
        raise RuntimeError(f"Refusing to overwrite symlinked Theses.cz report target: {rel}")
    try:
        target.parent.resolve(strict=False).relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise RuntimeError(f"Refusing to write Theses.cz report data outside the repository: {rel}") from exc
    if not git_ignored(root, rel):
        raise RuntimeError(f"Refusing to write Theses.cz report data to a non-ignored path: {rel}")


def ensure_targets_available(root: Path, targets: list[Path]) -> None:
    for target in targets:
        ensure_private_target(root, target)
        collision = case_insensitive_collision(root, target)
        if collision is not None:
            rel = target.relative_to(root).as_posix()
            collision_rel = collision.relative_to(root).as_posix()
            raise RuntimeError(f"Refusing case-insensitive target collision for {rel}: existing {collision_rel}")
        if target.exists():
            rel = target.relative_to(root).as_posix()
            raise RuntimeError(f"Theses.cz similarity report is already imported at {rel}")

    report_text = next(target for target in targets if target.name == "report.txt")
    if not is_allowed_extract_path(root, report_text.resolve(strict=False)):
        raise RuntimeError(
            "Refusing to write extracted Theses.cz report text outside " "cases/<case>/rounds/<round>/extracted/."
        )


def tmp_path_for(target: Path) -> Path:
    return target.with_name(f".{target.name}.tmp-{os.getpid()}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_case_round(root: Path, case_id: str, round_id: str | None) -> tuple[str, Path]:
    case_dir = root / "cases" / case_id
    if not case_dir.is_dir():
        raise RuntimeError(f"Case does not exist: cases/{case_id}")
    try:
        resolved_round_id = resolve_round_core(case_dir, round_id)
    except MissingCurrentRound as exc:
        raise RuntimeError("ROUND_ID not provided and current-round.txt is missing") from exc
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    round_dir = case_dir / "rounds" / resolved_round_id
    if not round_dir.is_dir():
        raise RuntimeError(f"Round does not exist: cases/{case_id}/rounds/{resolved_round_id}")
    return resolved_round_id, round_dir


def import_report(
    *,
    root: Path,
    case_id: str,
    round_id: str,
    round_dir: Path,
    source_pdf: Path,
    current_submission_link: str,
) -> dict[str, Any]:
    report_pdf = round_dir / REPORT_PDF_REL
    report_text = round_dir / REPORT_TEXT_REL
    report_text_sidecar = pdf_extract_sidecar_path(report_text)
    intake = round_dir / INTAKE_REL
    targets = [report_pdf, report_text, report_text_sidecar, intake]
    ensure_targets_available(root, targets)

    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)

    tmp_pdf = tmp_path_for(report_pdf)
    tmp_text = tmp_path_for(report_text)
    tmp_sidecar = tmp_path_for(report_text_sidecar)
    tmp_intake = tmp_path_for(intake)
    tmp_targets = [tmp_pdf, tmp_text, tmp_sidecar, tmp_intake]
    for tmp_target in tmp_targets:
        if tmp_target.exists():
            raise RuntimeError(f"Temporary import target already exists: {tmp_target}")
        ensure_private_target(root, tmp_target)

    committed_targets: list[Path] = []
    try:
        shutil.copy2(source_pdf, tmp_pdf)
        extract_report_text(tmp_pdf, tmp_text)
        page_count, page_limitations = report_page_count(tmp_pdf)
        report_text_value = tmp_text.read_text(encoding="utf-8", errors="replace")
        payload = build_intake_payload(
            case_id=case_id,
            round_id=round_id,
            generated_at=utc_now(),
            report_pdf_path=REPORT_PDF_REL.as_posix(),
            report_pdf_sha256=sha256_file(tmp_pdf),
            extracted_text_path=REPORT_TEXT_REL.as_posix(),
            extracted_text_sha256=sha256_file(tmp_text),
            report_text=report_text_value,
            page_count=page_count,
            current_submission_link=current_submission_link,
            limitations=page_limitations,
        )
        write_json(tmp_intake, payload)
        os.replace(tmp_pdf, report_pdf)
        committed_targets.append(report_pdf)
        os.replace(tmp_text, report_text)
        committed_targets.append(report_text)
        sidecar_payload = build_pdf_extract_manifest(
            round_dir,
            report_pdf,
            report_text,
            extractor_version=pdftotext_version(),
        )
        write_json(tmp_sidecar, sidecar_payload)
        os.replace(tmp_sidecar, report_text_sidecar)
        committed_targets.append(report_text_sidecar)
        os.replace(tmp_intake, intake)
        committed_targets.append(intake)
        return payload
    except BaseException:
        for tmp_target in tmp_targets:
            tmp_target.unlink(missing_ok=True)
        for target in committed_targets:
            target.unlink(missing_ok=True)
        raise


def main(argv: list[str]) -> int:
    if any(arg in {"-h", "--help"} for arg in argv[1:]):
        print(usage())
        return 0
    args = parse_args(argv)
    try:
        validate_id("CASE_ID", args.case_id)
        if args.round_id is not None:
            validate_id("ROUND_ID", args.round_id)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    root = repo_root_core()
    try:
        round_id, round_dir = resolve_case_round(root, args.case_id, args.round_id)
        source_pdf = resolve_caller_path(args.report_pdf)
        if not source_pdf.is_file():
            print(f"Report PDF does not exist: {args.report_pdf}", file=sys.stderr)
            return 1
        if source_pdf.suffix.casefold() != ".pdf":
            print(f"Report input must be a PDF file: {args.report_pdf}", file=sys.stderr)
            return 1
        import_report(
            root=root,
            case_id=args.case_id,
            round_id=round_id,
            round_dir=round_dir,
            source_pdf=source_pdf,
            current_submission_link=args.current_submission_link,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    round_rel = round_dir.relative_to(root).as_posix()
    print(f"Imported Theses.cz similarity report: {round_rel}/{REPORT_PDF_REL.as_posix()}")
    print(f"Extracted report text: {round_rel}/{REPORT_TEXT_REL.as_posix()}")
    print(f"Intake written: {round_rel}/{INTAKE_REL.as_posix()}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
