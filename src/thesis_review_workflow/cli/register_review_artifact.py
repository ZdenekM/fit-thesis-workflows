"""Register or update one review artifact in a round manifest."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Any

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.review_manifest import (
    MANIFEST_REL,
    classify_dependency_refs,
    ensure_manifest,
    load_manifest,
    register_artifact,
    registration_defaults,
    validate_dependency_ref_classification,
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
    parser.add_argument("--preset", choices=("auto", "none"), default="auto")
    parser.add_argument("--role")
    parser.add_argument("--agent", default="not_recorded")
    parser.add_argument("--contribution", default="generation")
    parser.add_argument("--review-scope")
    parser.add_argument("--review-status")
    parser.add_argument("--reviewer-role", default="not_recorded")
    parser.add_argument("--reviewer-agent", default="not_recorded")
    parser.add_argument("--reviewed-at", default="")
    parser.add_argument("--limitation", action="append", default=[])
    parser.add_argument("--feeds", action="append", default=[])
    parser.add_argument("--ref", action="append", default=[])
    parser.add_argument("--input-ref", action="append", default=[])
    parser.add_argument("--evidence-ref", action="append", default=[])
    parser.add_argument("--handoff-ref", action="append", default=[])
    parser.add_argument("--check-ref", action="append", default=[])
    parser.add_argument("--allow-ref-class-override", action="store_true")
    parser.add_argument("--used-findings", default="")
    parser.add_argument("--review-basis-path", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--updated-at", default="")
    return parser


def registration_options(args: argparse.Namespace) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    auto_input_refs, auto_evidence_refs, auto_handoff_refs, unknown_refs = classify_dependency_refs(args.ref)
    for ref in unknown_refs:
        errors.append(
            f"--ref {ref}: cannot classify dependency; use --input-ref, --evidence-ref, --handoff-ref, "
            "or --check-ref explicitly"
        )
    input_refs = [*args.input_ref, *auto_input_refs]
    evidence_refs = [*args.evidence_ref, *auto_evidence_refs]
    handoff_refs = [*args.handoff_ref, *auto_handoff_refs]
    errors.extend(
        validate_dependency_ref_classification(
            field="input_refs",
            refs=args.input_ref,
            allow_override=args.allow_ref_class_override,
        )
    )
    errors.extend(
        validate_dependency_ref_classification(
            field="evidence_refs",
            refs=args.evidence_ref,
            allow_override=args.allow_ref_class_override,
        )
    )
    errors.extend(
        validate_dependency_ref_classification(
            field="handoff_refs",
            refs=args.handoff_ref,
            allow_override=args.allow_ref_class_override,
        )
    )
    if errors:
        return None, errors

    if args.preset == "auto":
        defaults = registration_defaults(
            args.artifact_path,
            feeds=args.feeds,
            role=args.role,
            review_scope=args.review_scope,
            review_status=args.review_status,
        )
        role = str(defaults["role"] or "not_recorded")
        review_scope = defaults["review_scope"]
        review_status = str(defaults["review_status"] or "not_recorded")
    else:
        role = args.role or "not_recorded"
        review_scope = args.review_scope
        review_status = args.review_status or "not_recorded"

    return (
        {
            "role": role,
            "review_scope": review_scope,
            "review_status": review_status,
            "input_refs": input_refs,
            "evidence_refs": evidence_refs,
            "handoff_refs": handoff_refs,
        },
        [],
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)
    manifest_path = round_dir / MANIFEST_REL

    try:
        options, option_errors = registration_options(args)
        if option_errors:
            for error in option_errors:
                print(f"ERROR: {error}")
            return 1
        assert options is not None
        manifest = ensure_manifest(load_manifest(manifest_path), args.case_id, round_id)
        register_artifact(
            manifest,
            round_dir,
            args.artifact_path,
            role=options["role"],
            agent=args.agent,
            contribution=args.contribution,
            review_scope=options["review_scope"],
            review_status=options["review_status"],
            reviewer_role=args.reviewer_role,
            reviewer_agent=args.reviewer_agent,
            reviewed_at=args.reviewed_at,
            limitation=args.limitation,
            feeds=args.feeds,
            input_refs=options["input_refs"],
            evidence_refs=options["evidence_refs"],
            handoff_refs=options["handoff_refs"],
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
