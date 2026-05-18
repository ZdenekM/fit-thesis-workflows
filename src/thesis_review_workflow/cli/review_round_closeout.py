"""Run profile-aware closeout gates for optimized review rounds."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
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
from thesis_review_workflow.commands import Step, print_step, run_step
from thesis_review_workflow.review_delta import review_delta_closeout_errors
from thesis_review_workflow.review_packets import COMMON_BRIEFING_REL, sha256_file, write_common_briefing
from thesis_review_workflow.review_pipeline_orchestration import (
    REVIEW_ROLE_PLAN_REL,
    REVIEW_RUN_TRACE_REL,
    REVIEW_RUN_TRACE_SCHEMA,
    ReviewRunTraceEvent,
    closeout_wave_for_profile,
    load_review_role_plan,
    validate_review_role_plan_payload,
    validate_review_run_trace_payload,
    validate_role_plan_for_closeout,
)
from thesis_review_workflow.review_profiles import get_workflow_review_profile, profiles_by_id

COVERAGE_REL = "work/agent_coverage.json"
MANIFEST_REL = "work/review_manifest.json"
DELEGATED_CLOSEOUT_COMMANDS = {
    "supervisor_report": "supervisor-report-closeout",
    "opponent_review": "opponent-closeout",
    "opponent_materials": "opponent-closeout",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/review-round-closeout",
        description=(
            "Run the shared review-round closeout surface: manifest refresh, role-plan coverage, "
            "profile final-wave gates, role coverage, manifest completeness, and repo hygiene."
        ),
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--profile",
        choices=sorted(profiles_by_id()),
        help="workflow review profile; defaults to work/review_role_plan.json or work/review_run_trace.json",
    )
    parser.add_argument(
        "--skip-repo-hygiene",
        action="store_true",
        help="skip check-private, check-scripts, and git diff --check",
    )
    parser.add_argument("--output-limit", type=int, default=1200)
    return parser


def infer_profile_id(round_dir: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    for rel_path in (REVIEW_ROLE_PLAN_REL, REVIEW_RUN_TRACE_REL):
        path = round_dir / rel_path
        if not path.is_file():
            continue
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict) and isinstance(loaded.get("profile_id"), str):
            return str(loaded["profile_id"])
    raise ValueError("--profile is required when no review role plan or run trace records the profile")


def split_gate(gate: str, case_id: str, round_id: str) -> list[str]:
    args = shlex.split(gate)
    return [*args, case_id, round_id]


def role_plan_step(round_dir: Path, *, case_id: str, round_id: str, profile_id: str) -> Step:
    try:
        plan = load_review_role_plan(round_dir)
    except (OSError, ValueError) as exc:
        return Step(
            label="Review role plan closeout",
            command=["scripts/prepare-review-round", "--profile", profile_id, case_id, round_id],
            returncode=1,
            output=f"Could not read {REVIEW_ROLE_PLAN_REL}: {exc}",
        )
    errors = validate_role_plan_for_closeout(
        plan,
        round_dir=round_dir,
        case_id=case_id,
        round_id=round_id,
        profile_id=profile_id,
    )
    if errors:
        return Step(
            label="Review role plan closeout",
            command=["scripts/prepare-review-round", "--profile", profile_id, case_id, round_id],
            returncode=1,
            output="\n".join(f"- {error}" for error in errors),
        )
    return Step(
        label="Review role plan closeout",
        command=["scripts/prepare-review-round", "--profile", profile_id, case_id, round_id],
        returncode=0,
        output=f"{REVIEW_ROLE_PLAN_REL} is current enough for closeout.",
    )


def review_delta_step(round_dir: Path, *, case_id: str, round_id: str, profile_id: str) -> Step:
    errors = review_delta_closeout_errors(round_dir, case_id=case_id, round_id=round_id, profile_id=profile_id)
    if errors:
        return Step(
            label="Review delta closeout",
            command=None,
            returncode=1,
            output="\n".join(f"- {error}" for error in errors),
        )
    return Step(
        label="Review delta closeout",
        command=None,
        returncode=0,
        output="No unresolved review deltas block closeout.",
    )


def profile_transition_step(round_dir: Path, *, case_id: str, round_id: str, profile_id: str) -> Step:
    errors: list[str] = []
    for rel_path in (REVIEW_RUN_TRACE_REL, REVIEW_ROLE_PLAN_REL):
        path = round_dir / rel_path
        if not path.is_file():
            errors.append(f"{rel_path} is missing")
            continue
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{rel_path} is invalid JSON: {exc.msg}")
            continue
        if not isinstance(loaded, dict):
            errors.append(f"{rel_path} must contain a JSON object")
            continue
        if rel_path == REVIEW_RUN_TRACE_REL:
            errors.extend(f"{rel_path}: {error}" for error in validate_review_run_trace_payload(loaded))
        elif rel_path == REVIEW_ROLE_PLAN_REL:
            errors.extend(
                f"{rel_path}: {error}" for error in validate_review_role_plan_payload(loaded, round_dir=round_dir)
            )
        for field, expected in (("case_id", case_id), ("round_id", round_id), ("profile_id", profile_id)):
            if loaded.get(field) != expected:
                errors.append(f"{rel_path} records {field}={loaded.get(field)!r}, expected {expected!r}")
    if errors:
        recovery = [
            "Regenerate the profile transition artifacts before closeout mutates manifest state:",
            f"scripts/review-round-start --profile {profile_id} {case_id} {round_id}",
            f"scripts/prepare-review-round --profile {profile_id} {case_id} {round_id}",
        ]
        return Step(
            label="Review profile transition preflight",
            command=None,
            returncode=1,
            output="\n".join([*(f"- {error}" for error in errors), "", *recovery]),
        )
    return Step(
        label="Review profile transition preflight",
        command=None,
        returncode=0,
        output=f"{REVIEW_RUN_TRACE_REL} and {REVIEW_ROLE_PLAN_REL} match this closeout profile.",
    )


def common_briefing_refresh_step(round_dir: Path, *, case_id: str, round_id: str) -> Step:
    try:
        write_common_briefing(case_id, round_id, now_utc(), round_dir)
    except (OSError, ValueError) as exc:
        return Step(
            label="Common briefing refresh after materiality",
            command=None,
            returncode=1,
            output=str(exc),
        )
    return Step(
        label="Common briefing refresh after materiality",
        command=None,
        returncode=0,
        output=f"Refreshed {COMMON_BRIEFING_REL} after materiality decisions.",
    )


def generic_closeout_steps(root: Path, *, case_id: str, round_id: str, profile_id: str) -> list[Step]:
    profile = get_workflow_review_profile(profile_id)
    workflow, wave = closeout_wave_for_profile(profile_id)
    steps: list[Step] = []
    for gate in profile.readiness_gates:
        steps.append(run_step(root, f"Readiness gate: {gate}", split_gate(gate, case_id, round_id)))
    steps.append(
        run_step(root, "Review manifest refresh", ["scripts/init-review-manifest", "--run-checks", case_id, round_id])
    )
    if profile.effective_materiality_profile:
        steps.append(
            run_step(
                root,
                f"Final materiality profile: {profile.effective_materiality_profile}",
                [
                    "scripts/check-review-materiality",
                    "--workflow",
                    profile.effective_materiality_profile,
                    "--phase",
                    "final",
                    case_id,
                    round_id,
                ],
            )
        )
    round_dir = root / "cases" / case_id / "rounds" / round_id
    if profile.effective_materiality_profile:
        steps.append(common_briefing_refresh_step(round_dir, case_id=case_id, round_id=round_id))
    steps.append(role_plan_step(round_dir, case_id=case_id, round_id=round_id, profile_id=profile_id))
    steps.append(review_delta_step(round_dir, case_id=case_id, round_id=round_id, profile_id=profile_id))

    delegated = DELEGATED_CLOSEOUT_COMMANDS.get(profile_id)
    if delegated:
        steps.append(
            run_step(
                root,
                f"Delegated profile closeout: {delegated}",
                [f"scripts/{delegated}", "--skip-repo-hygiene", case_id, round_id],
            )
        )
        return steps

    steps.append(
        run_step(
            root,
            f"Final review wave: {workflow}:{wave}",
            ["scripts/check-review-wave", "--workflow", workflow, "--wave", wave, case_id, round_id],
        )
    )
    steps.append(
        run_step(
            root,
            "Post-wave review manifest refresh",
            ["scripts/init-review-manifest", "--run-checks", case_id, round_id],
        )
    )
    steps.append(run_step(root, "Agent role coverage", ["scripts/check-agent-coverage", case_id, round_id]))
    steps.append(
        run_step(
            root,
            "Review manifest completeness",
            ["scripts/check-review-manifest", "--require-complete", case_id, round_id],
        )
    )
    if profile_id == "supervisor_feedback":
        steps.append(run_step(root, "Feedback language", ["scripts/check-feedback-language", case_id, round_id]))
        steps.append(run_step(root, "Feedback output", ["scripts/check-feedback-output", case_id, round_id]))
    return steps


def repo_hygiene_steps(root: Path) -> list[Step]:
    return [
        run_step(root, "Private workspace hygiene", ["scripts/check-private"]),
        run_step(root, "Script syntax", ["scripts/check-scripts"]),
        run_step(root, "Whitespace/diff hygiene", ["git", "diff", "--check"]),
    ]


def trace_hashes(round_dir: Path, refs: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for ref in refs:
        path = round_dir / ref
        if path.is_file():
            digest = sha256_file(path)
            if digest:
                pairs.append((ref, digest))
    return tuple(pairs)


def append_closeout_trace(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    profile_id: str,
    status: str,
    command: str,
) -> None:
    trace_path = round_dir / REVIEW_RUN_TRACE_REL
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    event = ReviewRunTraceEvent(
        phase="closeout",
        status=status,
        command=command,
        completed_at=now_utc(),
        source_refs=tuple(ref for ref in (REVIEW_ROLE_PLAN_REL,) if (round_dir / ref).is_file()),
        output_refs=tuple(ref for ref in (MANIFEST_REL, COVERAGE_REL) if (round_dir / ref).is_file()),
        source_sha256=trace_hashes(round_dir, (REVIEW_ROLE_PLAN_REL,)),
        output_sha256=trace_hashes(round_dir, (MANIFEST_REL, COVERAGE_REL)),
    )
    payload: dict[str, Any]
    try:
        loaded = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path.is_file() else {}
    except json.JSONDecodeError:
        loaded = {}
    if isinstance(loaded, dict) and loaded.get("schema_version") == REVIEW_RUN_TRACE_SCHEMA:
        mismatches = [
            f"{field}={loaded.get(field)!r}"
            for field, expected in (("case_id", case_id), ("round_id", round_id), ("profile_id", profile_id))
            if loaded.get(field) != expected
        ]
        if mismatches:
            raise ValueError(
                f"{REVIEW_RUN_TRACE_REL} does not belong to this closeout invocation: {', '.join(mismatches)}"
            )
        payload = loaded
        events = payload.get("events")
        if not isinstance(events, list):
            events = []
            payload["events"] = events
        events.append(event.to_json())
        payload["generated_at"] = str(payload.get("generated_at") or now_utc())
    else:
        profile = get_workflow_review_profile(profile_id)
        payload = {
            "schema_version": REVIEW_RUN_TRACE_SCHEMA,
            "case_id": case_id,
            "round_id": round_id,
            "profile_id": profile.profile_id,
            "workflow_profile": profile.workflow_profile,
            "materiality_profile": profile.effective_materiality_profile,
            "operator_surface": profile.operator_surface,
            "generated_at": now_utc(),
            "trace_path": REVIEW_RUN_TRACE_REL,
            "events": [event.to_json()],
        }
    errors = validate_review_run_trace_payload(payload)
    if errors:
        raise ValueError("; ".join(errors))
    trace_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_summary(round_dir: Path, *, profile_id: str, steps: list[Step]) -> None:
    profile = get_workflow_review_profile(profile_id)
    print()
    print("## Review Round Closeout Summary")
    print(f"- Profile: `{profile.profile_id}`.")
    final_status = "present" if (round_dir / profile.final_artifact).is_file() else "missing"
    approval_status = "present" if (round_dir / profile.approval_record).is_file() else "missing"
    print(f"- Final artifact: `{profile.final_artifact}` {final_status}.")
    print(f"- Approval record: `{profile.approval_record}` {approval_status}.")
    print("- PASS means the profile final artifact is review-gated, manifest-checked, and role-plan-covered.")
    print("- FAIL means fix the named gate before relying on the round output.")
    failed = [step.label for step in steps if not step.ok and step.required]
    if failed:
        print("- Next action: fix the first failing gate above, then rerun `review-round-closeout`.")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv[1:])
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)
    try:
        profile_id = infer_profile_id(round_dir, args.profile)
        profile = get_workflow_review_profile(profile_id)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print("Review Round Closeout")
    print(f"Case: cases/{args.case_id}")
    print(f"Round: cases/{args.case_id}/rounds/{round_id}")
    print(f"Profile: {profile.profile_id} ({profile.workflow_profile})")

    preflight = profile_transition_step(
        round_dir,
        case_id=args.case_id,
        round_id=round_id,
        profile_id=profile.profile_id,
    )
    if not preflight.ok:
        print_step(preflight, output_limit=args.output_limit)
        print_summary(round_dir, profile_id=profile.profile_id, steps=[preflight])
        return preflight.returncode

    steps = generic_closeout_steps(root, case_id=args.case_id, round_id=round_id, profile_id=profile.profile_id)
    if not args.skip_repo_hygiene:
        steps.extend(repo_hygiene_steps(root))

    failed = any(not step.ok and step.required for step in steps)
    try:
        append_closeout_trace(
            round_dir,
            case_id=args.case_id,
            round_id=round_id,
            profile_id=profile.profile_id,
            status="failed" if failed else "started",
            command=f"review-round-closeout --profile {profile.profile_id} {args.case_id} {round_id}",
        )
        steps.append(
            Step(
                label="Closeout trace start",
                command=None,
                returncode=0,
                output=f"Recorded closeout start event in {REVIEW_RUN_TRACE_REL}.",
            )
        )
    except (OSError, ValueError) as exc:
        trace_step = Step(
            label="Closeout trace update",
            command=None,
            returncode=1,
            output=str(exc),
        )
        steps.append(trace_step)
        failed = True

    steps.append(
        run_step(
            root,
            "Final manifest refresh after trace update",
            ["scripts/init-review-manifest", "--run-checks", args.case_id, round_id],
        )
    )
    steps.append(
        run_step(
            root,
            "Final review manifest completeness after trace update",
            ["scripts/check-review-manifest", "--require-complete", args.case_id, round_id],
        )
    )
    failed = any(not step.ok and step.required for step in steps)

    try:
        append_closeout_trace(
            round_dir,
            case_id=args.case_id,
            round_id=round_id,
            profile_id=profile.profile_id,
            status="failed" if failed else "passed",
            command=f"review-round-closeout --profile {profile.profile_id} {args.case_id} {round_id}",
        )
        steps.append(
            Step(
                label="Closeout trace final verdict",
                command=None,
                returncode=0,
                output=f"Recorded final closeout verdict in {REVIEW_RUN_TRACE_REL}.",
            )
        )
    except (OSError, ValueError) as exc:
        steps.append(
            Step(
                label="Closeout trace final verdict",
                command=None,
                returncode=1,
                output=str(exc),
            )
        )
        failed = True

    steps.append(
        run_step(
            root,
            "Final manifest refresh after trace verdict",
            ["scripts/init-review-manifest", "--run-checks", args.case_id, round_id],
        )
    )
    steps.append(
        run_step(
            root,
            "Final review manifest completeness after trace verdict",
            ["scripts/check-review-manifest", "--require-complete", args.case_id, round_id],
        )
    )
    failed = any(not step.ok and step.required for step in steps)
    if failed and any(
        step.label == "Closeout trace final verdict" and step.ok and "final closeout verdict" in step.output
        for step in steps
    ):
        try:
            append_closeout_trace(
                round_dir,
                case_id=args.case_id,
                round_id=round_id,
                profile_id=profile.profile_id,
                status="failed",
                command=f"review-round-closeout --profile {profile.profile_id} {args.case_id} {round_id}",
            )
        except (OSError, ValueError):
            pass

    for step in steps:
        print_step(step, output_limit=max(args.output_limit, 200))

    print_summary(round_dir, profile_id=profile.profile_id, steps=steps)
    return 1 if failed else 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
