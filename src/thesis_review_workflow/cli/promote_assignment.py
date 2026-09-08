"""Promote an approved assignment variant into a thesis case's round."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from thesis_review_workflow.assignment_bundle import approval_rel
from thesis_review_workflow.assignment_promotion import (
    ASSIGNMENT_REL,
    PromotionTarget,
    contained_write_errors,
    read_bundle,
    render_assignment_context,
    retained_approval_rel,
    target_errors,
)
from thesis_review_workflow.cli.check_assignment_bundle import check_bundle
from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.operation_log import OPERATION_LOG_REL, append_operation
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.review_approvals import sha256_file

ISSUED_HELP = (
    "Assert that this exact variant is the target student's effective assignment and that its "
    "brief was supplied to them. Approval means the variant MAY be published; it does not mean "
    "the student received it, and no later check can tell the difference."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/promote-assignment",
        description="Write an approved assignment variant into a thesis case as its assignment context.",
    )
    parser.add_argument("topic_case_id")
    parser.add_argument("variant")
    parser.add_argument("target_case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument("--issued", action="store_true", help=ISSUED_HELP)
    parser.add_argument(
        "--issued-note",
        default="yes",
        help="What to record beside the issuance assertion, for example the IS approval date.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Overwrite an existing notes/assignment.md. Lifts that refusal only.",
    )
    parser.add_argument("--actor", default="operator")
    return parser


def promote(
    root: Path,
    topic_case_dir: Path,
    topic_case_id: str,
    variant: str,
    target: PromotionTarget,
    target_case_id: str,
    *,
    issued: bool,
    issued_note: str,
    replace: bool,
    actor: str,
) -> list[str]:
    if not issued:
        return [
            "refusing to promote without an explicit issuance assertion: an approved bundle may be "
            "published, but nothing in it says this student received this assignment. Pass --issued "
            "once that is true."
        ]

    bundle_findings = check_bundle(topic_case_dir, topic_case_id, variant)
    if bundle_findings:
        return ["the bundle is not approved and current; run scripts/check-assignment-bundle", *bundle_findings]

    errors = target_errors(root, target.case_dir, target_case_id, variant)
    if errors:
        return errors

    assignment_path = target.round_dir / ASSIGNMENT_REL
    retained_rel = retained_approval_rel(topic_case_id, variant)
    retained_path = target.round_dir / retained_rel
    # The log is a write too: an `operation_log.jsonl` linked out of the case would carry the
    # case id, actor and issuance note with it.
    log_path = target.round_dir / OPERATION_LOG_REL
    errors = contained_write_errors(target.case_dir, [assignment_path, retained_path, log_path])
    if errors:
        return errors

    if assignment_path.is_file() and not replace:
        return [
            f"{rel_repo(root, assignment_path)} already exists; this case was reviewed against it. "
            "Pass --replace to overwrite it deliberately."
        ]

    approval_path = topic_case_dir / approval_rel(variant)
    assignment, brief = read_bundle(topic_case_dir, variant)

    retained_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(approval_path, retained_path)
    assignment_path.parent.mkdir(parents=True, exist_ok=True)
    assignment_path.write_text(
        render_assignment_context(
            topic_case_id=topic_case_id,
            variant=variant,
            approval_sha256=sha256_file(approval_path),
            retained_rel=retained_rel,
            assignment=assignment,
            brief=brief,
            issued_by=actor,
            issued_note=issued_note,
        ),
        encoding="utf-8",
    )

    append_operation(
        target.round_dir,
        case_id=target_case_id,
        round_id=target.round_id,
        operation="promote-assignment",
        status="passed",
        actor=actor,
        summary=f"Promoted {topic_case_id} variant {variant} into {target_case_id}, asserted issued.",
        command=f"scripts/promote-assignment {topic_case_id} {variant} {target_case_id}",
        artifacts=[ASSIGNMENT_REL.as_posix(), retained_rel.as_posix()],
        checks=["scripts/check-assignment-bundle"],
        details={"topic_case": topic_case_id, "variant": variant, "issued": issued_note},
    )
    return []


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.topic_case_id)
    validate_id("TARGET_CASE_ID", args.target_case_id)
    root = repo_root()
    topic_case_dir = require_case_dir(root, args.topic_case_id)
    target_case_dir = require_case_dir(root, args.target_case_id)
    round_id = resolve_round(target_case_dir, args.round_id)
    target_round_dir = require_round_dir(target_case_dir, args.target_case_id, round_id)
    target = PromotionTarget(target_case_dir, target_round_dir, round_id)

    findings = promote(
        root,
        topic_case_dir,
        args.topic_case_id,
        args.variant,
        target,
        args.target_case_id,
        issued=args.issued,
        issued_note=args.issued_note,
        replace=args.replace,
        actor=args.actor,
    )
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}")
        return 1
    print(f"Promoted {args.topic_case_id} variant {args.variant} into {args.target_case_id}/{round_id}")
    print(f"Wrote {rel_repo(root, target_round_dir / ASSIGNMENT_REL)}")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
