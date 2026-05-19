"""Start a thesis review round with deterministic preparation steps."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.commands import Step, run_step
from thesis_review_workflow.paths import is_safe_round_relative_path, rel_repo, resolve_caller_path
from thesis_review_workflow.review_pipeline_orchestration import (
    REVIEW_RUN_TRACE_REL,
    ReviewRunTraceEvent,
    RoundMaterialDescriptor,
    RoundStartAction,
    TracePhase,
    build_review_run_trace_payload,
    plan_review_round_start,
)
from thesis_review_workflow.review_profiles import profiles_by_id
from thesis_review_workflow.submission_bundle import build_and_write_submission_bundle_inventory

METADATA_KEY_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True, slots=True)
class ExecutedAction:
    status: str
    command: str
    notes: tuple[str, ...] = ()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/review-round-start",
        description="Run deterministic start-of-round preparation and write work/review_run_trace.json.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--profile",
        required=True,
        choices=sorted(profiles_by_id()),
        help="Workflow review profile, not a Codex agent profile.",
    )
    parser.add_argument("--fresh-materials-expected", action="store_true")
    parser.add_argument("--provisional-stale-review", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write the review-run trace with skipped planned actions, without running helper commands.",
    )
    parser.add_argument(
        "--material-currentness",
        default="current",
        choices=["current", "newer_than_previous", "stale", "missing", "unknown"],
        help="Currentness applied to material flags in this invocation.",
    )
    parser.add_argument("--thesis-pdf", action="append", default=[], metavar="ROUND_REL_PATH")
    parser.add_argument("--source-archive", action="append", default=[], metavar="ROUND_REL_PATH")
    parser.add_argument("--code-archive", action="append", default=[], metavar="ROUND_REL_PATH")
    parser.add_argument("--code-directory", action="append", default=[], metavar="ROUND_REL_PATH")
    parser.add_argument("--github-url", action="append", default=[], metavar="URL")
    parser.add_argument("--theses-report", action="append", default=[], metavar="ROUND_REL_PATH")
    parser.add_argument("--reviewed-report-draft", action="append", default=[], metavar="ROUND_REL_PATH")
    parser.add_argument("--submission-bundle", action="append", default=[], metavar="ROUND_REL_PATH")
    parser.add_argument(
        "--bundle-classification",
        default="",
        choices=["", "container_bundle", "reference_bundle"],
        help="Classification applied to --submission-bundle inputs.",
    )
    parser.add_argument(
        "--bundle-child",
        action="append",
        default=[],
        metavar="ROUND_REL_PATH",
        help="Authoritative child ref for a classified submission bundle.",
    )
    parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Structured metadata field for planner diagnostics; raw values are not written to the trace.",
    )
    parser.add_argument(
        "--metadata-file",
        action="append",
        default=[],
        metavar="KEY=PATH",
        help="Read a structured metadata field from a caller-relative UTF-8 file.",
    )
    parser.add_argument("--generated-at", default="", help=argparse.SUPPRESS)
    return parser


def parse_key_value(raw: str, *, option: str) -> tuple[str, str]:
    if "=" not in raw:
        raise ValueError(f"{option} must use KEY=VALUE")
    key, value = raw.split("=", 1)
    if not key or not METADATA_KEY_RE.fullmatch(key):
        raise ValueError(f"{option} key must use only letters, numbers, dot, underscore, and dash")
    return key, value


def metadata_fields(metadata: list[str], metadata_files: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw in metadata:
        key, value = parse_key_value(raw, option="--metadata")
        fields[key] = value
    for raw in metadata_files:
        key, value = parse_key_value(raw, option="--metadata-file")
        path = resolve_caller_path(value)
        if not path.is_file():
            raise ValueError(f"--metadata-file path does not exist: {value}")
        fields[key] = path.read_text(encoding="utf-8")
    return fields


def material_descriptors_from_args(args: argparse.Namespace) -> tuple[RoundMaterialDescriptor, ...]:
    currentness = args.material_currentness
    materials: list[RoundMaterialDescriptor] = []
    for kind, values in [
        ("thesis_pdf", args.thesis_pdf),
        ("source_archive", args.source_archive),
        ("code_archive", args.code_archive),
        ("code_directory", args.code_directory),
        ("theses_similarity_report", args.theses_report),
        ("reviewed_report_draft", args.reviewed_report_draft),
    ]:
        materials.extend(RoundMaterialDescriptor(kind, path=value, currentness=currentness) for value in values)
    for url in args.github_url:
        kind = "github_pr_url" if "/pull/" in url else "github_snapshot_request"
        materials.append(RoundMaterialDescriptor(kind, url=url, currentness=currentness))
    for value in args.submission_bundle:
        materials.append(
            RoundMaterialDescriptor(
                "submission_bundle",
                path=value,
                currentness=currentness,
                bundle_classification=args.bundle_classification,
                decomposed_authoritative_refs=tuple(args.bundle_child),
            )
        )
    return tuple(materials)


def safe_trace_refs(refs: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(ref for ref in refs if "*" not in ref and is_safe_round_relative_path(ref))


def trace_safe_blocker_notes(codes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(f"{code}: blocked; see command stderr for input-specific details" for code in codes)


def digest_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def trace_hashes(round_dir: Path, refs: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for rel_path in safe_trace_refs(refs):
        path = round_dir / rel_path
        if path.is_file():
            pairs.append((rel_path, digest_file(path)))
    return tuple(pairs)


def git_ignored(root: Path, path: Path) -> bool:
    rel = rel_repo(root, path)
    return (
        subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", rel],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def ensure_private_trace_target(root: Path, target: Path) -> None:
    try:
        target.resolve(strict=False).relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise RuntimeError(f"Refusing to write review-run trace outside the repository: {target}") from exc
    if target.is_symlink():
        raise RuntimeError(f"Refusing to overwrite symlinked review-run trace target: {rel_repo(root, target)}")
    if not git_ignored(root, target):
        raise RuntimeError(f"Refusing to write review-run trace to a non-ignored path: {rel_repo(root, target)}")


def write_trace(
    *,
    root: Path,
    round_dir: Path,
    case_id: str,
    round_id: str,
    profile_id: str,
    generated_at: str,
    events: list[ReviewRunTraceEvent],
) -> Path:
    target = round_dir / REVIEW_RUN_TRACE_REL
    ensure_private_trace_target(root, target)
    payload = build_review_run_trace_payload(
        case_id=case_id,
        round_id=round_id,
        profile_id=profile_id,
        generated_at=generated_at,
        events=tuple(events),
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def action_phase(action_id: str) -> str:
    return {
        "classify_bundle": "start",
        "inventory_submission_bundle": "start",
        "extract_pdf_text": "extraction",
        "import_github_snapshot": "import",
        "prepare_code_workspace": "import",
        "ensure_profile_note": "packet_prep",
        "update_current_evidence": "packet_prep",
        "update_reuse_index": "packet_prep",
        "run_readiness_gate": "packet_prep",
        "prepare_role_plan": "role_plan",
    }[action_id]


def substitute_placeholders(command: str, *, case_id: str, round_id: str) -> str:
    return command.replace("<case-id>", case_id).replace("<round-id>", round_id)


def shlex_join(args: list[str]) -> str:
    return " ".join(shlex.quote(arg) for arg in args)


def print_step_output(step: Step) -> None:
    if step.output:
        print(step.output)


def run_workflow_step(root: Path, label: str, args: list[str]) -> ExecutedAction:
    step = run_step(root, label, args)
    print_step_output(step)
    return ExecutedAction(
        "passed" if step.ok else "failed",
        shlex_join(args),
        () if step.ok else (f"command exited with status {step.returncode}",),
    )


def source_refs_for_snapshot(materials: tuple[RoundMaterialDescriptor, ...]) -> list[str]:
    return [material.path for material in materials if material.path and is_safe_round_relative_path(material.path)]


def github_material_for_action(
    action: RoundStartAction,
    materials: tuple[RoundMaterialDescriptor, ...],
) -> RoundMaterialDescriptor:
    for material in materials:
        if material.ref in action.material_refs and material.kind in {"github_snapshot_request", "github_pr_url"}:
            return material
    raise RuntimeError("GitHub import action is missing its material descriptor")


def material_for_action(
    action: RoundStartAction,
    materials: tuple[RoundMaterialDescriptor, ...],
    *,
    kind: str,
) -> RoundMaterialDescriptor:
    for material in materials:
        if material.kind == kind and material.ref in action.material_refs:
            return material
    raise RuntimeError(f"{kind} action is missing its material descriptor")


def execute_action(
    *,
    root: Path,
    round_dir: Path,
    case_id: str,
    round_id: str,
    action: RoundStartAction,
    materials: tuple[RoundMaterialDescriptor, ...],
) -> ExecutedAction:
    if action.action_id == "classify_bundle":
        return ExecutedAction(
            "passed",
            "record container_bundle/reference_bundle classification in review_run_trace",
            ("classified parent bundle from explicit descriptor",),
        )
    if action.action_id == "inventory_submission_bundle":
        bundle_refs = tuple(ref for ref in action.material_refs if ref)
        build_and_write_submission_bundle_inventory(
            case_id=case_id,
            round_id=round_id,
            round_dir=round_dir,
            bundle_refs=bundle_refs,
            producer="scripts/review-round-start",
        )
        return ExecutedAction(
            "passed",
            "review-round-start internal submission-bundle inventory",
            (f"inventoried {len(bundle_refs)} submitted bundle(s)",),
        )
    if action.action_id == "ensure_profile_note":
        target = round_dir / "notes" / "supervisor-report-operator-input.md"
        if target.exists():
            return ExecutedAction(
                "skipped", "copy supervisor-report operator-intake template", ("note already exists",)
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / "templates" / "supervisor-report-intake.md", target)
        return ExecutedAction("passed", "copy supervisor-report operator-intake template")
    if action.action_id == "extract_pdf_text":
        material = material_for_action(action, materials, kind="thesis_pdf")
        output_rel = action.target_refs[0]
        return run_workflow_step(
            root,
            "PDF text extraction",
            [
                "extract-pdf-text",
                str(round_dir / material.path),
                str(round_dir / output_rel),
            ],
        )
    if action.action_id == "import_github_snapshot":
        material = github_material_for_action(action, materials)
        if material.kind == "github_pr_url":
            result = run_workflow_step(
                root,
                "GitHub PR intake",
                ["import-github-code", case_id, round_id, "--pr-url", material.url],
            )
        else:
            result = run_workflow_step(
                root,
                "GitHub repository intake",
                ["import-github-code", case_id, round_id, "--repo", material.url],
            )
        return ExecutedAction(
            result.status,
            f"import-github-code {case_id} {round_id} <github-ref-redacted>",
            result.notes,
        )
    if action.action_id == "prepare_code_workspace":
        return run_workflow_step(root, "Code workspace preparation", ["prepare-code-workspace", case_id, round_id])
    if action.action_id == "update_current_evidence":
        command = ["update-current-evidence-snapshot", case_id, round_id]
        for rel_path in source_refs_for_snapshot(materials):
            command.extend(["--source-ref", rel_path])
        return run_workflow_step(root, "Current evidence snapshot", command)
    if action.action_id == "update_reuse_index":
        return run_workflow_step(root, "Round reuse index", ["update-round-reuse-index", case_id, round_id])
    if action.action_id == "run_readiness_gate":
        command = shlex.split(substitute_placeholders(action.command, case_id=case_id, round_id=round_id))
        return run_workflow_step(root, f"Readiness gate: {command[0]}", command)
    if action.action_id == "prepare_role_plan":
        return ExecutedAction(
            "planned",
            substitute_placeholders(action.command, case_id=case_id, round_id=round_id),
            ("next command; review-round-start does not write work/review_role_plan.json",),
        )
    raise RuntimeError(f"Unsupported round-start action: {action.action_id}")


def redacted_action_command(action: RoundStartAction, *, case_id: str, round_id: str) -> str:
    if action.action_id == "import_github_snapshot":
        return f"import-github-code {case_id} {round_id} <github-ref-redacted>"
    if action.action_id == "extract_pdf_text":
        return "extract-pdf-text <input-pdf> <output-text>"
    return substitute_placeholders(action.command, case_id=case_id, round_id=round_id)


def event_for_action(
    *,
    action: RoundStartAction,
    status: str,
    command: str,
    round_dir: Path,
    notes: tuple[str, ...] = (),
) -> ReviewRunTraceEvent:
    output_refs = safe_trace_refs(action.target_refs)
    return ReviewRunTraceEvent(
        phase=cast(TracePhase, action_phase(action.action_id)),
        status=status,
        command=command,
        completed_at=utc_now() if status not in {"started", "planned"} else "",
        source_refs=safe_trace_refs(action.material_refs),
        output_refs=output_refs,
        output_sha256=trace_hashes(round_dir, output_refs),
        notes=notes,
    )


def run_round_start(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    validate_id("CASE_ID", args.case_id, stderr=True)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id, stderr=True)

    try:
        fields = metadata_fields(args.metadata, args.metadata_file)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    root = repo_root()
    case_dir = require_case_dir(root, args.case_id, stderr=True)
    round_id = resolve_round(case_dir, args.round_id, stderr=True)
    round_dir = require_round_dir(case_dir, args.case_id, round_id, stderr=True)
    materials = material_descriptors_from_args(args)
    plan = plan_review_round_start(
        case_id=args.case_id,
        round_id=round_id,
        profile_id=args.profile,
        materials=materials,
        fresh_materials_expected=args.fresh_materials_expected,
        provisional_stale_review=args.provisional_stale_review,
        metadata_fields=fields,
    )
    generated_at = args.generated_at or utc_now()
    invocation = f"review-round-start --profile {args.profile} {args.case_id} {round_id}"
    if args.dry_run:
        invocation += " --dry-run"
    events: list[ReviewRunTraceEvent] = [
        ReviewRunTraceEvent(
            phase="start",
            status="started",
            command=invocation,
            started_at=generated_at,
            source_refs=safe_trace_refs(tuple(material.ref for material in materials if material.ref)),
            output_refs=(REVIEW_RUN_TRACE_REL,),
            notes=(f"profile={plan.profile_id}", f"dry_run={args.dry_run}"),
        )
    ]

    if plan.blockers:
        blocker_codes = tuple(blocker.code for blocker in plan.blockers)
        events.append(
            ReviewRunTraceEvent(
                phase="start",
                status="blocked",
                command=invocation,
                completed_at=utc_now(),
                source_refs=safe_trace_refs(tuple(material.ref for material in materials if material.ref)),
                output_refs=(REVIEW_RUN_TRACE_REL,),
                notes=trace_safe_blocker_notes(blocker_codes),
            )
        )
        write_trace(
            root=root,
            round_dir=round_dir,
            case_id=args.case_id,
            round_id=round_id,
            profile_id=args.profile,
            generated_at=generated_at,
            events=events,
        )
        for blocker in plan.blockers:
            print(f"BLOCKER: {blocker.code}: {blocker.message}", file=sys.stderr)
        return 1

    try:
        write_trace(
            root=root,
            round_dir=round_dir,
            case_id=args.case_id,
            round_id=round_id,
            profile_id=args.profile,
            generated_at=generated_at,
            events=events,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for diagnostic in plan.diagnostics:
        print(f"{diagnostic.severity.upper()}: {diagnostic.code}: {diagnostic.message}")

    for action in plan.actions:
        if args.dry_run and action.action_id != "prepare_role_plan":
            event = event_for_action(
                action=action,
                status="skipped",
                command=redacted_action_command(action, case_id=args.case_id, round_id=round_id),
                round_dir=round_dir,
                notes=("dry run",),
            )
            events.append(event)
            write_trace(
                root=root,
                round_dir=round_dir,
                case_id=args.case_id,
                round_id=round_id,
                profile_id=args.profile,
                generated_at=generated_at,
                events=events,
            )
            print(f"SKIP {action.action_id}: dry run")
            continue

        if action.action_id != "prepare_role_plan":
            events.append(
                event_for_action(
                    action=action,
                    status="started",
                    command=redacted_action_command(action, case_id=args.case_id, round_id=round_id),
                    round_dir=round_dir,
                )
            )
            write_trace(
                root=root,
                round_dir=round_dir,
                case_id=args.case_id,
                round_id=round_id,
                profile_id=args.profile,
                generated_at=generated_at,
                events=events,
            )

        try:
            executed = execute_action(
                root=root,
                round_dir=round_dir,
                case_id=args.case_id,
                round_id=round_id,
                action=action,
                materials=materials,
            )
        except (OSError, RuntimeError, shutil.Error, ValueError) as exc:
            executed = ExecutedAction(
                "failed", redacted_action_command(action, case_id=args.case_id, round_id=round_id), (str(exc),)
            )

        events.append(
            event_for_action(
                action=action,
                status=executed.status,
                command=executed.command,
                round_dir=round_dir,
                notes=executed.notes,
            )
        )
        write_trace(
            root=root,
            round_dir=round_dir,
            case_id=args.case_id,
            round_id=round_id,
            profile_id=args.profile,
            generated_at=generated_at,
            events=events,
        )
        print(f"{executed.status.upper()} {action.action_id}")
        if executed.status == "failed":
            print(
                f"Review round start failed. Trace: {rel_repo(root, round_dir / REVIEW_RUN_TRACE_REL)}", file=sys.stderr
            )
            return 1

    print(f"Review round start trace: {rel_repo(root, round_dir / REVIEW_RUN_TRACE_REL)}")
    next_command = substitute_placeholders(
        plan.next_command + " <case-id> <round-id>",
        case_id=args.case_id,
        round_id=round_id,
    )
    print(f"Next command: {next_command}")
    return 0


def console_main() -> int:
    return run_round_start(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
