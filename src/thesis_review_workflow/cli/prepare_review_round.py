"""Prepare role plans and compact packets for a thesis review round."""

from __future__ import annotations

import argparse
import json
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
from thesis_review_workflow.commands import run_step
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.review_pipeline_orchestration import (
    REVIEW_ROLE_PLAN_REL,
    REVIEW_RUN_TRACE_REL,
    build_review_role_plan_payload,
    packet_contract_for_profile,
)
from thesis_review_workflow.review_profiles import get_workflow_review_profile, profiles_by_id


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/prepare-review-round",
        description="Write work/review_role_plan.json and prepare compact role packets.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--profile",
        choices=sorted(profiles_by_id()),
        help=f"Workflow review profile. Defaults to {REVIEW_RUN_TRACE_REL} when present.",
    )
    parser.add_argument("--skip-ready-check", action="store_true")
    parser.add_argument("--skip-materiality-check", action="store_true")
    parser.add_argument(
        "--agents-authorized",
        action="store_true",
        help="Pass through explicit role-agent authorization where the packet contract requires it.",
    )
    parser.add_argument(
        "--authorization-note",
        default="current request explicitly authorizes review role agents and independent review loop",
    )
    parser.add_argument("--generated-at", default="", help=argparse.SUPPRESS)
    return parser


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


def ensure_private_role_plan_target(root: Path, target: Path) -> None:
    try:
        target.resolve(strict=False).relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise RuntimeError(f"Refusing to write role plan outside the repository: {target}") from exc
    if target.is_symlink():
        raise RuntimeError(f"Refusing to overwrite symlinked role-plan target: {rel_repo(root, target)}")
    if not git_ignored(root, target):
        raise RuntimeError(f"Refusing to write role plan to a non-ignored path: {rel_repo(root, target)}")


def infer_profile_from_trace(round_dir: Path) -> str | None:
    path = round_dir / REVIEW_RUN_TRACE_REL
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    profile_id = loaded.get("profile_id")
    return profile_id if isinstance(profile_id, str) and profile_id in profiles_by_id() else None


def refresh_materiality_before_packets(
    root: Path,
    *,
    profile_id: str,
    case_id: str,
    round_id: str,
    skip_materiality_check: bool,
) -> bool:
    if skip_materiality_check:
        return False
    profile = get_workflow_review_profile(profile_id)
    materiality_profile = profile.effective_materiality_profile
    if materiality_profile is None:
        return False
    snapshot = run_step(
        root,
        "current evidence snapshot",
        ["update-current-evidence-snapshot", case_id, round_id],
    )
    if snapshot.output:
        print(snapshot.output)
    if not snapshot.ok:
        raise RuntimeError(f"current evidence snapshot failed with status {snapshot.returncode}")
    command = ["check-review-materiality", "--workflow", materiality_profile]
    if profile_id == "supervisor_report":
        command.extend(["--phase", "final"])
    command.extend([case_id, round_id])
    materiality = run_step(root, "review materiality", command)
    if materiality.output:
        print(materiality.output)
    if not materiality.ok:
        raise RuntimeError(f"review materiality check failed with status {materiality.returncode}")
    return True


def packet_command_args(
    args: argparse.Namespace,
    *,
    profile_id: str,
    case_id: str,
    round_id: str,
    materiality_refreshed: bool = False,
) -> list[str]:
    _, _, command = packet_contract_for_profile(profile_id)
    command_args = [command, case_id, round_id]
    skip_legacy_ready_check = args.skip_ready_check or (
        profile_id == "opponent_report_review" and command == "prepare-opponent-packets"
    )
    if skip_legacy_ready_check:
        command_args.append("--skip-ready-check")
    if command == "prepare-supervisor-report-packets":
        if args.skip_materiality_check or materiality_refreshed:
            command_args.append("--skip-materiality-check")
        if not args.agents_authorized:
            raise ValueError("supervisor_report packet preparation requires --agents-authorized")
        command_args.extend(["--agents-authorized", "--authorization-note", args.authorization_note])
    return command_args


def write_role_plan(root: Path, round_dir: Path, payload: dict[str, object]) -> Path:
    target = round_dir / REVIEW_ROLE_PLAN_REL
    ensure_private_role_plan_target(root, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)

    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)
    profile_id = args.profile or infer_profile_from_trace(round_dir)
    if profile_id is None:
        print(f"ERROR: --profile is required when {REVIEW_RUN_TRACE_REL} is missing or unreadable", file=sys.stderr)
        return 2

    try:
        packet_command_args(args, profile_id=profile_id, case_id=args.case_id, round_id=round_id)
        materiality_refreshed = refresh_materiality_before_packets(
            root,
            profile_id=profile_id,
            case_id=args.case_id,
            round_id=round_id,
            skip_materiality_check=args.skip_materiality_check,
        )
        command_args = packet_command_args(
            args,
            profile_id=profile_id,
            case_id=args.case_id,
            round_id=round_id,
            materiality_refreshed=materiality_refreshed,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    packets = run_step(root, "Review packet preparation", command_args)
    if packets.output:
        print(packets.output)
    if not packets.ok:
        return packets.returncode

    try:
        payload = build_review_role_plan_payload(
            case_id=args.case_id,
            round_id=round_id,
            profile_id=profile_id,
            generated_at=args.generated_at or utc_now(),
            round_dir=round_dir,
        )
        output = write_role_plan(root, round_dir, payload)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Review role plan: {rel_repo(root, output)}")
    print(f"Workflow profile: {profile_id}")
    print(f"Packet command: {' '.join(command_args)}")
    print("Next action: spawn scheduled role agents according to work/review_role_plan.json")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
