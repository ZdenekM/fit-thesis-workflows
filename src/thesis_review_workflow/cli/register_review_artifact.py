"""Register or update one review artifact in a round manifest."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.review_manifest import (
    MANIFEST_REL,
    ensure_manifest,
    load_manifest,
    register_artifact,
    write_manifest,
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/register-review-artifact",
        description="Register or update one review artifact in work/review_manifest.json.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id")
    parser.add_argument("artifact_path")
    parser.add_argument("--role", default="not_recorded")
    parser.add_argument("--agent", default="not_recorded")
    parser.add_argument("--contribution", default="generation")
    parser.add_argument("--review-scope")
    parser.add_argument("--review-status", default="not_recorded")
    parser.add_argument("--reviewer-role", default="not_recorded")
    parser.add_argument("--reviewer-agent", default="not_recorded")
    parser.add_argument("--reviewed-at", default="")
    parser.add_argument("--limitation", action="append", default=[])
    parser.add_argument("--feeds", action="append", default=[])
    parser.add_argument("--input-ref", action="append", default=[])
    parser.add_argument("--evidence-ref", action="append", default=[])
    parser.add_argument("--check-ref", action="append", default=[])
    parser.add_argument("--used-findings", default="")
    parser.add_argument("--review-basis-path", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--updated-at", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)
    manifest_path = round_dir / MANIFEST_REL

    try:
        manifest = ensure_manifest(load_manifest(manifest_path), args.case_id, round_id)
        register_artifact(
            manifest,
            round_dir,
            args.artifact_path,
            role=args.role,
            agent=args.agent,
            contribution=args.contribution,
            review_scope=args.review_scope,
            review_status=args.review_status,
            reviewer_role=args.reviewer_role,
            reviewer_agent=args.reviewer_agent,
            reviewed_at=args.reviewed_at,
            limitation=args.limitation,
            feeds=args.feeds,
            input_refs=args.input_ref,
            evidence_refs=args.evidence_ref,
            check_refs=args.check_ref,
            used_findings=args.used_findings,
            review_basis_path=args.review_basis_path,
            notes=args.notes,
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    write_manifest(manifest_path, manifest, args.updated_at or now_utc())
    print(f"Registered {args.artifact_path} in cases/{args.case_id}/rounds/{round_id}/work/review_manifest.json")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
