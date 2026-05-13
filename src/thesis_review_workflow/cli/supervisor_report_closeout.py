"""Run closeout gates for a reviewed and confirmed supervisor report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.commands import Step, print_step, run_step
from thesis_review_workflow.review_materiality import unresolved_required_next_actions

COVERAGE_REL = Path("work/agent_coverage.json")
SUPERVISOR_REPORT_DRAFT_REL = Path("work/vedouci_posudek_draft.md")
SUPERVISOR_REPORT_REVIEWED_REL = Path("outputs/vedouci_posudek_revidovany.md")
SUPERVISOR_REPORT_CONFIRMATION_REL = Path("work/supervisor_report_confirmation.json")
SUPERVISOR_REPORT_REVIEW_REL = Path("work/reviews/supervisor_report_review.json")
SUPERVISOR_REPORT_TRACE_REL = Path("work/supervisor_report_trace.json")
FINAL_SNAPSHOT_REFS = (
    "notes/assignment.md",
    "notes/supervisor-report-operator-input.md",
    "work/code_workspace.md",
    "work/serena_roots.json",
    "work/code_reproducibility.json",
    "work/quantitative_claims.json",
    "work/supervisor_report_feedback_history.json",
    "work/supervisor_report_trace.json",
    "work/vedouci_posudek_draft.md",
    "work/supervisor_report_confirmation.json",
    "work/reviews/supervisor_report_review.json",
    "outputs/github_code_intake.md",
    "outputs/code_consistency.md",
    "outputs/code_quality_review.md",
    "outputs/literature_citation_review.md",
    "outputs/figure_media_review.md",
    "outputs/typography_formal_review.md",
    "outputs/theses_similarity_review.md",
    "outputs/vedouci_posudek_revidovany.md",
)


def current_evidence_snapshot_command(round_dir: Path, case_id: str, round_id: str) -> list[str]:
    command = ["scripts/update-current-evidence-snapshot", "--no-known"]
    for rel_path in FINAL_SNAPSHOT_REFS:
        if (round_dir / rel_path).exists():
            command.extend(["--source-ref", rel_path])
    command.extend([case_id, round_id])
    return command


def materiality_next_actions_step(round_dir: Path, *, case_id: str, round_id: str) -> Step:
    actions, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile="supervisor_report",
        case_id=case_id,
        round_id=round_id,
    )
    command = [
        "scripts/check-review-materiality",
        "--workflow",
        "supervisor_report",
        "--phase",
        "final",
        case_id,
        round_id,
    ]
    if errors:
        return Step(
            label="Final materiality next actions",
            command=command,
            returncode=1,
            output="Could not validate final materiality next actions:\n" + "\n".join(f"- {error}" for error in errors),
        )
    if actions:
        lines = [
            "Unresolved required final materiality next actions:",
            *[f"- {action['role']}: {action['required_artifact_path']} - {action['reason']}" for action in actions],
            "Resolve each action with a current artifact, synthesis-covered evidence, or a typed accepted limitation.",
        ]
        return Step(label="Final materiality next actions", command=command, returncode=1, output="\n".join(lines))
    return Step(
        label="Final materiality next actions",
        command=command,
        returncode=0,
        output="No unresolved required final materiality next actions.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/supervisor-report-closeout",
        description=(
            "Validate reviewed and confirmed supervisor report, final review approval, provenance, "
            "role coverage, and repo hygiene."
        ),
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--skip-repo-hygiene",
        action="store_true",
        help="skip check-private, check-scripts, and git diff --check",
    )
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    print("Supervisor Report Closeout")
    print(f"Case: cases/{args.case_id}")
    print(f"Round: cases/{args.case_id}/rounds/{round_id}")

    steps: list[Step] = []
    steps.append(
        run_step(root, "Supervisor report readiness", ["scripts/check-supervisor-report-ready", args.case_id, round_id])
    )
    steps.append(
        run_step(
            root,
            "Reviewed and confirmed supervisor report",
            ["scripts/check-supervisor-report", "--require-reviewed", "--require-confirmation", args.case_id, round_id],
        )
    )
    steps.append(
        run_step(
            root,
            "Current evidence snapshot",
            current_evidence_snapshot_command(round_dir, args.case_id, round_id),
        )
    )
    steps.append(
        run_step(
            root,
            "Final supervisor report materiality",
            [
                "scripts/check-review-materiality",
                "--workflow",
                "supervisor_report",
                "--phase",
                "final",
                args.case_id,
                round_id,
            ],
        )
    )
    steps.append(materiality_next_actions_step(round_dir, case_id=args.case_id, round_id=round_id))
    steps.append(
        run_step(
            root,
            "Pre-wave review manifest refresh",
            ["scripts/init-review-manifest", "--run-checks", args.case_id, round_id],
        )
    )
    steps.append(
        run_step(
            root,
            "Final supervisor report review wave",
            ["scripts/check-review-wave", "--workflow", "supervisor_report", "--wave", "final", args.case_id, round_id],
        )
    )
    steps.append(
        run_step(
            root,
            "Post-wave review manifest refresh",
            ["scripts/init-review-manifest", "--run-checks", args.case_id, round_id],
        )
    )
    if (round_dir / COVERAGE_REL).is_file():
        steps.append(run_step(root, "Agent role coverage", ["scripts/check-agent-coverage", args.case_id, round_id]))
    else:
        steps.append(
            Step(
                label="Agent role coverage",
                command=["scripts/check-agent-coverage", args.case_id, round_id],
                returncode=0,
                output="skipped: work/agent_coverage.json is not present after manifest refresh",
                required=True,
            )
        )
    steps.append(
        run_step(
            root,
            "Review manifest completeness",
            ["scripts/check-review-manifest", "--require-complete", args.case_id, round_id],
        )
    )
    if not args.skip_repo_hygiene:
        steps.append(run_step(root, "Private workspace hygiene", ["scripts/check-private"]))
        steps.append(run_step(root, "Script syntax", ["scripts/check-scripts"]))
        steps.append(run_step(root, "Whitespace/diff hygiene", ["git", "diff", "--check"]))

    for step in steps:
        print_step(step, output_limit=1000)

    print()
    print("## Supervisor Report Closeout Summary")
    for label, rel_path in (
        ("Trace", SUPERVISOR_REPORT_TRACE_REL),
        ("Draft", SUPERVISOR_REPORT_DRAFT_REL),
        ("Reviewed report", SUPERVISOR_REPORT_REVIEWED_REL),
        ("Review approval", SUPERVISOR_REPORT_REVIEW_REL),
        ("Supervisor confirmation", SUPERVISOR_REPORT_CONFIRMATION_REL),
    ):
        if (round_dir / rel_path).is_file():
            print(f"- {label} present: `{rel_path.as_posix()}`.")
        else:
            print(f"- {label} missing: `{rel_path.as_posix()}`.")
    print("- PASS means the report is reviewed, hash-bound to supervisor confirmation, and ready for IS transfer.")
    print("- FAIL means fix the named gate before relying on the report.")
    return 1 if any(not step.ok and step.required for step in steps) else 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
