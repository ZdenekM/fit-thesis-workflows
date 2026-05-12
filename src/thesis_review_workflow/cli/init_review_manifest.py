"""Create or refresh a round review provenance manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from thesis_review_workflow.agent_coverage import (
    COVERAGE_REL,
    build_coverage,
    coverage_required,
    load_json_object,
    write_coverage,
)
from thesis_review_workflow.artifact_registry import (
    explicit_internal_review_filenames,
    internal_evidence_filenames,
    output_defaults,
    output_spec,
)
from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.commands import canonical_command_text, repo_command_environment, resolve_repo_command
from thesis_review_workflow.opponent_calibration import calibration_profile_check_targets
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.review_manifest import apply_review_approval_records, merge_supporting_work_artifacts
from thesis_review_workflow.supervisor_report_calibration import supervisor_report_calibration_profile_check_targets
from thesis_review_workflow.theses_similarity import (
    THESES_SIMILARITY_REVIEW_REL,
    theses_similarity_check_targets,
    theses_similarity_evidence_present,
)
from thesis_review_workflow.work_artifacts import collect_supporting_work_artifacts

MANIFEST_REL = Path("work/review_manifest.json")
INTERNAL_EVIDENCE = internal_evidence_filenames()
REQUIRE_STANDALONE_REVIEW = explicit_internal_review_filenames()


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest["updated_at"] = now_utc()
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def target_hashes(round_dir: Path, targets: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for target in targets:
        path = round_dir / target
        if path.is_file():
            hashes[target] = sha256_file(path)
    return hashes


def source_hashes(round_dir: Path, refs: Any) -> dict[str, str]:
    if not isinstance(refs, list):
        return {}
    hashes: dict[str, str] = {}
    for ref in refs:
        if not isinstance(ref, str):
            continue
        path = round_dir / ref
        if path.is_file():
            hashes[ref] = sha256_file(path)
    return hashes


def rel(path: Path, round_dir: Path) -> str:
    return path.relative_to(round_dir).as_posix()


def file_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".zip", ".tar", ".gz", ".tgz", ".7z"}:
        return "archive"
    if suffix in {".md", ".txt"}:
        return "text"
    if suffix in {".json", ".jsonl", ".yml", ".yaml", ".toml"}:
        return "structured_data"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        return "image"
    return "file"


def collect_tree(round_dir: Path, subdir: str) -> list[dict[str, str]]:
    base = round_dir / subdir
    if not base.is_dir():
        return []
    records = []
    for path in sorted(base.rglob("*")):
        if path.is_file():
            records.append({"path": rel(path, round_dir), "kind": file_kind(path)})
    return records


def collect_work_artifacts(round_dir: Path) -> list[dict[str, str]]:
    return collect_supporting_work_artifacts(round_dir)


def load_existing(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Existing manifest is not valid JSON: {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise SystemExit(f"Existing manifest must be a JSON object: {path}")
    return loaded


def artifact_defaults(filename: str, synthesis: str | None) -> tuple[str, tuple[str, ...], str, str, str]:
    artifact_type, skills, scope = output_defaults(filename)
    covered_by = ""
    used_findings = ""
    if filename in INTERNAL_EVIDENCE and filename not in REQUIRE_STANDALONE_REVIEW and synthesis:
        scope = "covered_by_synthesis"
        covered_by = synthesis
        used_findings = "not_recorded"
    return artifact_type, tuple(skills), scope, covered_by, used_findings


def default_review(scope: str, covered_by: str, used_findings: str) -> dict[str, Any]:
    if scope == "covered_by_synthesis":
        return {
            "status": "not_required",
            "reviewer_role": "",
            "reviewer_agent": "",
            "reviewed_at": "",
            "reviewed_hash": "",
            "covered_by_artifact": covered_by,
            "used_findings": used_findings,
            "exception": (
                "Standalone review is not recorded; findings are intended to be checked by the "
                "downstream synthesis review."
            ),
            "notes": "",
        }
    return {
        "status": "not_recorded",
        "reviewer_role": "not_recorded",
        "reviewer_agent": "not_recorded",
        "reviewed_at": "",
        "reviewed_hash": "",
        "covered_by_artifact": "",
        "used_findings": "",
        "exception": (
            "Review status was not recorded in this manifest when the artifact was created; "
            "verify manually before relying on it."
        ),
        "notes": "",
    }


def default_agent() -> dict[str, str]:
    return {
        "role": "not_recorded",
        "agent": "not_recorded",
        "contribution": "generation",
        "notes": "Fill when known.",
    }


def output_artifacts(round_dir: Path, existing: dict[str, Any]) -> list[dict[str, Any]]:
    existing_by_path = {
        item.get("path"): item
        for item in existing.get("artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    output_dir = round_dir / "outputs"
    if not output_dir.is_dir():
        return []

    names = {path.name for path in output_dir.glob("*.md") if path.is_file()}
    synthesis = None
    if "feedback_student.md" in names:
        synthesis = "outputs/feedback_student.md"
    elif "oponent_podklady_revidovane.md" in names:
        synthesis = "outputs/oponent_podklady_revidovane.md"

    artifacts = []
    for path in sorted(output_dir.glob("*.md")):
        current_hash = sha256_file(path)
        rel_path = rel(path, round_dir)
        filename = path.name
        artifact_type, skills, scope, covered_by, used_findings = artifact_defaults(filename, synthesis)
        previous = dict(existing_by_path.get(rel_path, {}))
        previous_scope = previous.get("review_scope")
        if filename in REQUIRE_STANDALONE_REVIEW:
            effective_scope = "internal_only"
        elif (
            filename in INTERNAL_EVIDENCE
            and filename not in REQUIRE_STANDALONE_REVIEW
            and synthesis
            and previous_scope in {None, "", "internal_only"}
        ):
            effective_scope = "covered_by_synthesis"
        else:
            effective_scope = previous_scope or scope
        review = previous.get("independent_review")
        if not isinstance(review, dict):
            review = default_review(effective_scope, covered_by, used_findings)
        elif (
            effective_scope == "covered_by_synthesis"
            and review.get("status") in {"not_recorded", "not_required"}
            and not review.get("covered_by_artifact")
        ):
            review = default_review(effective_scope, covered_by, used_findings)
        elif effective_scope == "covered_by_synthesis" and not review.get("covered_by_artifact"):
            review = {
                **review,
                "covered_by_artifact": covered_by,
                "used_findings": review.get("used_findings") or used_findings,
            }
        if effective_scope == "covered_by_synthesis" and not review.get("evidence_hash"):
            review = {**review, "evidence_hash": current_hash}
        elif filename in REQUIRE_STANDALONE_REVIEW and review.get("status") == "not_required":
            review = default_review(effective_scope, "", "")

        limitations = previous.get("limitations") or []
        if not limitations and effective_scope in {"sendable_final", "standalone_final"}:
            limitations = [
                "Review status was reconstructed after artifact creation; confirm independent review before reuse."
            ]

        spec = output_spec(filename)
        entry = {
            "path": rel_path,
            "artifact_type": artifact_type if spec is not None else previous.get("artifact_type") or artifact_type,
            "artifact_sha256": current_hash,
            "review_scope": effective_scope,
            "skills": list(skills) if spec is not None else previous.get("skills") or list(skills),
            "generated_by": previous.get("generated_by") or [default_agent()],
            "independent_review": review,
            "helper_checks": previous.get("helper_checks") or [],
            "limitations": limitations,
            "notes": previous.get("notes") or "",
        }
        for field in ("input_refs", "evidence_refs", "check_refs"):
            if field in previous:
                entry[field] = previous[field]
        source_refs: list[str] = []
        for field in ("input_refs", "evidence_refs"):
            value = entry.get(field)
            if isinstance(value, list):
                source_refs.extend(ref for ref in value if isinstance(ref, str))
        if source_refs:
            entry["source_sha256"] = source_hashes(round_dir, source_refs)
        artifacts.append(entry)
    return artifacts


def required_checks(
    case_id: str,
    round_id: str,
    artifact_paths: set[str],
    round_dir: Path,
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(name: str, command: str, targets: list[str]) -> None:
        # Store logical workflow commands, not POSIX wrapper paths. The runner
        # resolves them to Python modules, and operator docs map them to native
        # launchers on Windows.
        checks.append(
            {
                "check": name,
                "command": canonical_command_text(command),
                "target_artifacts": targets,
                "target_sha256": target_hashes(round_dir, targets),
                "status": "not_recorded",
                "checked_at": "",
                "exit_code": None,
                "notes": "Fill after running, or keep as an explicit limitation for reconstructed manifests.",
            }
        )

    if "outputs/feedback_student.md" in artifact_paths:
        add(
            "check-supervisor-ready",
            f"check-supervisor-ready {case_id} {round_id}",
            ["outputs/feedback_student.md"],
        )
        add(
            "check-feedback-language",
            f"check-feedback-language {case_id} {round_id}",
            ["outputs/feedback_student.md"],
        )
        add(
            "check-feedback-output",
            f"check-feedback-output {case_id} {round_id}",
            ["outputs/feedback_student.md"],
        )
    if "outputs/vedouci_posudek_revidovany.md" in artifact_paths:
        targets = ["work/supervisor_report_trace.json", "outputs/vedouci_posudek_revidovany.md"]
        if (round_dir / "work" / "vedouci_posudek_draft.md").is_file():
            targets.append("work/vedouci_posudek_draft.md")
        add(
            "check-supervisor-report-ready",
            f"check-supervisor-report-ready {case_id} {round_id}",
            ["outputs/vedouci_posudek_revidovany.md"],
        )
        add("check-supervisor-report", f"check-supervisor-report {case_id} {round_id}", targets)
    if "outputs/oponent_podklady_revidovane.md" in artifact_paths:
        add(
            "check-round-ready",
            f"check-round-ready {case_id} {round_id}",
            ["outputs/oponent_podklady_revidovane.md"],
        )
        add(
            "check-opponent-materials",
            f"check-opponent-materials {case_id} {round_id}",
            ["outputs/oponent_podklady_revidovane.md"],
        )
        targets = ["work/opponent_report_trace.json", "outputs/oponent_podklady_revidovane.md"]
        if (round_dir / "work" / "oponent_posudek_draft.md").is_file():
            targets.append("work/oponent_posudek_draft.md")
        add("check-opponent-report", f"check-opponent-report {case_id} {round_id}", targets)
    if "outputs/figure_media_review.md" in artifact_paths:
        add(
            "check-figure-media-review",
            f"check-figure-media-review {case_id} {round_id}",
            ["outputs/figure_media_review.md"],
        )
    if "outputs/typography_formal_review.md" in artifact_paths:
        add(
            "check-typography-formal",
            f"check-typography-formal --require-output {case_id} {round_id}",
            ["outputs/typography_formal_review.md"],
        )
    if theses_similarity_evidence_present(round_dir):
        targets = theses_similarity_check_targets(round_dir)
        if THESES_SIMILARITY_REVIEW_REL in artifact_paths and THESES_SIMILARITY_REVIEW_REL not in targets:
            targets.append(THESES_SIMILARITY_REVIEW_REL)
        add(
            "check-theses-similarity-report",
            f"check-theses-similarity-report {case_id} {round_id}",
            targets,
        )
    if "outputs/code_consistency.md" in artifact_paths:
        add(
            "check-code-consistency",
            f"check-code-consistency {case_id} {round_id}",
            ["outputs/code_consistency.md"],
        )
    if "outputs/code_quality_review.md" in artifact_paths:
        add(
            "check-code-quality-review",
            f"check-code-quality-review {case_id} {round_id}",
            ["outputs/code_quality_review.md"],
        )
    if supporting_work_artifact_present(manifest, "work/quantitative_claims.json"):
        add(
            "check-evaluation-claims",
            f"check-evaluation-claims {case_id} {round_id}",
            ["work/quantitative_claims.json"],
        )
    if "outputs/revision_diff.md" in artifact_paths:
        add(
            "check-revision-diff",
            f"check-revision-diff {case_id} {round_id}",
            ["outputs/revision_diff.md"],
        )
    if "outputs/reviewer_calibration_profile.md" in artifact_paths:
        add(
            "check-opponent-calibration-profile",
            f"check-opponent-calibration-profile {case_id} {round_id}",
            calibration_profile_check_targets(round_dir),
        )
    if "outputs/supervisor_report_calibration_profile.md" in artifact_paths:
        add(
            "check-supervisor-report-calibration-profile",
            f"check-supervisor-report-calibration-profile {case_id} {round_id}",
            supervisor_report_calibration_profile_check_targets(round_dir),
        )
    if coverage_required(round_dir, manifest):
        add("check-agent-coverage", f"check-agent-coverage {case_id} {round_id}", sorted(artifact_paths))
    add(
        "check-review-manifest",
        f"check-review-manifest --require-complete {case_id} {round_id}",
        sorted(artifact_paths),
    )
    checks[-1]["status"] = "not_applicable"
    checks[-1]["notes"] = "This command is the closeout gate itself; run it after review metadata has been recorded."
    return checks


def supporting_work_artifact_present(manifest: dict[str, Any], rel_path: str) -> bool:
    records = manifest.get("supporting_work_artifacts")
    if not isinstance(records, list):
        return False
    return any(isinstance(record, dict) and record.get("path") == rel_path for record in records)


def merge_checks(existing: dict[str, Any], generated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing_by_name = {
        item.get("check"): item
        for item in existing.get("helper_checks", [])
        if isinstance(item, dict) and isinstance(item.get("check"), str)
    }
    merged = []
    for item in generated:
        previous = existing_by_name.get(item["check"])
        if item.get("check") == "check-review-manifest":
            merged.append(item)
        elif (
            isinstance(previous, dict)
            and isinstance(previous.get("command"), str)
            and canonical_command_text(previous["command"]) == canonical_command_text(item.get("command", ""))
        ):
            if previous.get("target_artifacts") != item.get("target_artifacts"):
                stale = dict(item)
                stale["notes"] = "Target artifact set changed since the previous check; rerun this helper check."
                merged.append(stale)
                continue
            if previous.get("target_sha256") != item.get("target_sha256"):
                stale = dict(item)
                stale["notes"] = "Target artifact hash changed since the previous check; rerun this helper check."
                merged.append(stale)
                continue
            updated = {**item, **previous}
            updated["command"] = item["command"]
            if not updated.get("target_artifacts"):
                updated["target_artifacts"] = item["target_artifacts"]
            if not updated.get("target_sha256"):
                updated["target_sha256"] = item["target_sha256"]
            merged.append(updated)
        else:
            merged.append(item)
    return merged


def add_artifact_refs(manifest: dict[str, Any]) -> None:
    input_refs = [
        record["path"]
        for collection in ("inputs", "extracted_artifacts", "notes")
        for record in manifest.get(collection, [])
        if isinstance(record, dict) and isinstance(record.get("path"), str)
    ]
    work_refs = [
        record["path"]
        for record in manifest.get("supporting_work_artifacts", [])
        if isinstance(record, dict) and isinstance(record.get("path"), str)
    ]
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        return
    evidence_outputs = [
        artifact.get("path")
        for artifact in artifacts
        if isinstance(artifact, dict)
        and isinstance(artifact.get("path"), str)
        and artifact.get("path", "").removeprefix("outputs/") in INTERNAL_EVIDENCE
    ]
    check_refs_by_artifact: dict[str, list[str]] = {}
    for check in manifest.get("helper_checks", []):
        if not isinstance(check, dict) or not isinstance(check.get("check"), str):
            continue
        for target in check.get("target_artifacts", []):
            if isinstance(target, str):
                check_refs_by_artifact.setdefault(target, []).append(check["check"])

    for artifact in artifacts:
        if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
            continue
        path = artifact["path"]
        artifact.setdefault("input_refs", input_refs)
        if "evidence_refs" not in artifact:
            refs = list(work_refs)
            if path in {"outputs/feedback_student.md", "outputs/oponent_podklady_revidovane.md"}:
                refs.extend(ref for ref in evidence_outputs if ref != path)
            artifact["evidence_refs"] = refs
        artifact.setdefault("check_refs", check_refs_by_artifact.get(path, []))


def compact_output(stdout: str, stderr: str) -> str:
    lines = [line for line in (stderr + "\n" + stdout).splitlines() if line.strip()]
    if not lines:
        return ""
    text = " | ".join(lines)
    if len(text) > 1000:
        return text[:997] + "..."
    return text


def run_check_record(root: Path, round_dir: Path, check: dict[str, Any]) -> None:
    command = check.get("command")
    if not isinstance(command, str) or not command.strip():
        check["status"] = "failed"
        check["notes"] = "Missing command."
        check["checked_at"] = now_utc()
        check["exit_code"] = None
        return
    result = subprocess.run(
        resolve_repo_command(root, shlex.split(command)),
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=repo_command_environment(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    check["status"] = "passed" if result.returncode == 0 else "failed"
    check["checked_at"] = now_utc()
    check["exit_code"] = result.returncode
    targets = check.get("target_artifacts")
    if isinstance(targets, list) and all(isinstance(target, str) for target in targets):
        check["target_sha256"] = target_hashes(round_dir, targets)
    detail = compact_output(result.stdout, result.stderr)
    check["notes"] = detail or "Executed by init-review-manifest --run-checks."


def run_helper_checks(root: Path, manifest_path: Path, manifest: dict[str, Any]) -> None:
    checks = manifest.get("helper_checks")
    if not isinstance(checks, list):
        return
    round_dir = manifest_path.parents[1]
    for check in checks:
        if not isinstance(check, dict):
            continue
        if check.get("check") == "check-review-manifest":
            check["status"] = "not_applicable"
            check["checked_at"] = ""
            check["exit_code"] = None
            check["notes"] = (
                "Run this command after review metadata has been recorded; "
                "it is not executed by init-review-manifest --run-checks."
            )
            continue
        run_check_record(root, round_dir, check)
    write_manifest(manifest_path, manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-checks", action="store_true", help="run generated read-only helper checks and record their status"
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    args = parser.parse_args()

    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    manifest_path = round_dir / MANIFEST_REL
    existing = load_existing(manifest_path)
    artifacts = output_artifacts(round_dir, existing)
    artifact_paths = {item["path"] for item in artifacts}
    limitations = existing.get("workflow_limitations")
    if not isinstance(limitations, list):
        limitations = []
    if artifacts and not limitations:
        limitations = [
            {
                "scope": "review_provenance",
                "description": "This manifest was initialized after one or more generated artifacts already existed.",
                "impact": (
                    "Generator and reviewer identities or helper-check statuses may need manual confirmation "
                    "before reuse."
                ),
                "status": "open",
            }
        ]

    inputs = collect_tree(round_dir, "inputs")
    extracted = collect_tree(round_dir, "extracted")
    notes = collect_tree(round_dir, "notes")
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": args.case_id,
        "round_id": round_id,
        "updated_at": now_utc(),
        "manifest_path": MANIFEST_REL.as_posix(),
        "inputs": inputs,
        "extracted_artifacts": extracted,
        "notes": notes,
        "supporting_work_artifacts": [],
        "helper_checks": [],
        "workflow_limitations": limitations,
        "artifacts": artifacts,
    }
    work_artifacts = merge_supporting_work_artifacts(
        existing.get("supporting_work_artifacts"),
        collect_work_artifacts(round_dir),
    )
    manifest["supporting_work_artifacts"] = work_artifacts
    add_artifact_refs(manifest)

    existing_coverage = load_json_object(round_dir / COVERAGE_REL)
    write_coverage(
        round_dir / COVERAGE_REL,
        build_coverage(args.case_id, round_id, round_dir, manifest, existing_coverage),
    )
    work_artifacts = merge_supporting_work_artifacts(
        existing.get("supporting_work_artifacts"),
        collect_work_artifacts(round_dir),
    )
    manifest["supporting_work_artifacts"] = work_artifacts
    checks = merge_checks(existing, required_checks(args.case_id, round_id, artifact_paths, round_dir, manifest))
    manifest["helper_checks"] = checks
    add_artifact_refs(manifest)
    apply_review_approval_records(manifest, round_dir)

    write_manifest(manifest_path, manifest)
    if args.run_checks:
        run_helper_checks(root, manifest_path, manifest)
        write_manifest(manifest_path, manifest)
    print(f"Wrote {rel_repo(root, manifest_path)}")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
