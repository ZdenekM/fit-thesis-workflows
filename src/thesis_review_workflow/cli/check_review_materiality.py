"""Write advisory materiality decisions for optional review roles."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.review_materiality import (
    MATERIALITY_ROLES,
    PHASES,
    WORKFLOW_PROFILES,
    build_materiality_decisions,
    write_materiality_decisions,
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-review-materiality",
        description="Write advisory materiality decisions for optional thesis-review roles.",
    )
    parser.add_argument(
        "--workflow", "--profile", dest="workflow_profile", required=True, choices=sorted(WORKFLOW_PROFILES)
    )
    parser.add_argument("--phase", choices=sorted(PHASES), default="auto")
    parser.add_argument(
        "--request-role",
        action="append",
        choices=list(MATERIALITY_ROLES),
        default=[],
        help="record an explicit operator/formal-skill request for a role",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def render_decision_line(role: str, recommendation: str, scope: str) -> str:
    return f"- {role}: {recommendation} ({scope})"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv[1:])
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)

    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    decisions, errors, resolved_phase = build_materiality_decisions(
        round_dir,
        case_id=args.case_id,
        round_id=round_id,
        workflow_profile=args.workflow_profile,
        phase=args.phase,
        requested_roles=tuple(args.request_role),
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    written = write_materiality_decisions(
        round_dir,
        decisions,
        case_id=args.case_id,
        round_id=round_id,
        workflow_profile=args.workflow_profile,
        phase=resolved_phase,
        generated_at=now_utc(),
    )

    print(f"Review materiality profile: {args.workflow_profile}")
    print(f"Review materiality phase: {resolved_phase}")
    for decision in decisions:
        print(render_decision_line(decision.role, decision.recommendation, decision.scope))
    for path in written:
        print(f"Wrote {rel_repo(root, path)}")
    print("Review materiality check passed")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
