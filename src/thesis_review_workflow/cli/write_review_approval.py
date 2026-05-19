"""Write a structured pass-only review approval record."""

from __future__ import annotations

import argparse
import json
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
from thesis_review_workflow.closeout_preflight import free_space_preflight_step
from thesis_review_workflow.paths import is_safe_round_relative_path, rel_repo
from thesis_review_workflow.review_approvals import (
    APPROVAL_PROFILES,
    REVIEW_APPROVAL_SCHEMA,
    ReviewApprovalProfile,
    build_review_approval_payload,
    require_review_approval_path,
    resolve_review_basis,
    validate_review_approval_artifact,
)
from thesis_review_workflow.review_manifest import MANIFEST_REL, load_manifest

CUSTOM_PROFILE = "custom"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/write-review-approval",
        description="Write work/reviews/*_review.json after an actual independent pass review.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--profile",
        choices=[*sorted(APPROVAL_PROFILES), CUSTOM_PROFILE],
        required=True,
        help="Canonical approval profile, or custom for standalone evidence.",
    )
    parser.add_argument("--approval-path", default="")
    parser.add_argument("--workflow-profile", default="")
    parser.add_argument("--reviewed-artifact", default="")
    parser.add_argument("--review-basis", default="")
    parser.add_argument("--reviewer-role", default="")
    parser.add_argument("--reviewer-agent", default="")
    parser.add_argument("--human-reviewer", default="")
    parser.add_argument("--verdict", choices=["approved", "pass"], default="approved")
    parser.add_argument("--blocking-findings-count", type=int, default=0)
    parser.add_argument("--check", dest="checks_observed", action="append", default=[])
    parser.add_argument("--limitation", action="append", default=[])
    parser.add_argument("--notes", default="")
    parser.add_argument("--used-findings", default="")
    parser.add_argument("--timestamp", default="")
    return parser


def read_manifest(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    loaded = load_manifest(path)
    return loaded if loaded else None


def profile_from_args(args: argparse.Namespace, round_dir: Path) -> tuple[str, str, str, str, str, tuple[str, ...]]:
    if args.profile == CUSTOM_PROFILE:
        required = {
            "--approval-path": args.approval_path,
            "--workflow-profile": args.workflow_profile,
            "--reviewed-artifact": args.reviewed_artifact,
            "--review-basis": args.review_basis,
            "--reviewer-role": args.reviewer_role,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"custom approval requires {', '.join(missing)}")
        approval_path = args.approval_path
        require_review_approval_path(approval_path)
        for label, value in (
            ("--reviewed-artifact", args.reviewed_artifact),
            ("--review-basis", args.review_basis),
        ):
            if not is_safe_round_relative_path(value):
                raise ValueError(f"{label} must be a safe round-relative path")
        return (
            approval_path,
            args.workflow_profile,
            args.reviewed_artifact,
            args.review_basis,
            args.reviewer_role,
            tuple(args.checks_observed),
        )

    profile: ReviewApprovalProfile = APPROVAL_PROFILES[args.profile]
    approval_path = args.approval_path or profile.approval_path
    require_review_approval_path(approval_path)
    if approval_path != profile.approval_path:
        raise ValueError(f"{args.profile} approval path must be {profile.approval_path}")
    reviewed_artifact = args.reviewed_artifact or profile.reviewed_artifact_path
    if reviewed_artifact != profile.reviewed_artifact_path:
        raise ValueError(f"{args.profile} reviewed artifact must be {profile.reviewed_artifact_path}")
    review_basis = resolve_review_basis(round_dir, profile, args.review_basis)
    if args.reviewer_role and args.reviewer_role != profile.reviewer_role:
        raise ValueError(f"{args.profile} reviewer role must be {profile.reviewer_role}")
    reviewer_role = args.reviewer_role or profile.reviewer_role
    return (
        approval_path,
        profile.workflow_profile,
        reviewed_artifact,
        review_basis,
        reviewer_role,
        profile.required_checks,
    )


def reviewer_identity(args: argparse.Namespace) -> tuple[str, str]:
    if args.reviewer_agent and args.human_reviewer:
        raise ValueError("use only one of --reviewer-agent or --human-reviewer")
    if args.reviewer_agent:
        return args.reviewer_agent, ""
    if args.human_reviewer:
        return f"human:{args.human_reviewer}", args.human_reviewer
    raise ValueError("--reviewer-agent or --human-reviewer is required")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)

    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    preflight = free_space_preflight_step(round_dir)
    if not preflight.ok:
        print(f"ERROR: {preflight.output}")
        return 1

    try:
        approval_path, workflow_profile, reviewed_artifact, review_basis, reviewer_role, required_checks = (
            profile_from_args(args, round_dir)
        )
        reviewer_agent, human_reviewer = reviewer_identity(args)
        checks_observed = sorted(dict.fromkeys(args.checks_observed))
        payload = build_review_approval_payload(
            round_dir,
            case_id=args.case_id,
            round_id=round_id,
            workflow_profile=workflow_profile,
            reviewer_role=reviewer_role,
            reviewer_agent=reviewer_agent,
            verdict=args.verdict,
            blocking_findings_count=args.blocking_findings_count,
            reviewed_artifact_path=reviewed_artifact,
            review_basis_path=review_basis,
            checks_observed=checks_observed,
            limitations=args.limitation,
            timestamp=args.timestamp or now_utc(),
            human_reviewer=human_reviewer,
            notes=args.notes,
            used_findings=args.used_findings,
            manifest=read_manifest(round_dir / MANIFEST_REL),
            required_checks=required_checks,
            approval_path=approval_path,
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    output = round_dir / approval_path
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    errors = validate_review_approval_artifact(
        round_dir,
        approval_path,
        case_id=args.case_id,
        round_id=round_id,
        reviewed_artifact_path=reviewed_artifact,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Wrote {rel_repo(root, output)} ({REVIEW_APPROVAL_SCHEMA})")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
