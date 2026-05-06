"""Static code-review reproducibility classification."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from thesis_review_workflow.code_workspace import (
    direct_input_code_dirs,
    is_archive,
    is_unsupported_archive,
    likely_project_roots,
    probe_archive,
    suggest_commands,
)

SCHEMA_VERSION = "code-reproducibility-v1"


@dataclass(frozen=True)
class ReproducibilitySummary:
    classification: str
    summary: str
    code_evidence: list[str]
    roots: list[dict[str, object]]
    run_evidence: list[str]
    evidence_requests: list[str]


def local_code_evidence(round_dir: Path) -> list[str]:
    inputs = round_dir / "inputs"
    if not inputs.is_dir():
        return []
    evidence = [path.relative_to(round_dir).as_posix() for path in direct_input_code_dirs(inputs)]
    for path in sorted(inputs.iterdir()):
        if path.is_symlink() or path.is_dir():
            continue
        if is_unsupported_archive(path):
            folded = path.name.lower()
            if any(token in folded for token in ("code", "src", "repo", "project", "submission")):
                evidence.append(f"{path.relative_to(round_dir).as_posix()} (unsupported archive)")
            continue
        if is_archive(path) and probe_archive(path).possible_code:
            evidence.append(path.relative_to(round_dir).as_posix())
    return evidence


def recorded_run_evidence(round_dir: Path) -> list[str]:
    candidates = [round_dir / "work" / "code_environment.md"]
    sandbox = round_dir / "work" / "sandbox"
    if sandbox.is_dir():
        candidates.extend(path for path in sorted(sandbox.rglob("*")) if path.is_file())
    return [path.relative_to(round_dir).as_posix() for path in candidates if path.is_file()]


def root_records(round_dir: Path) -> list[dict[str, object]]:
    workspace = round_dir / "work" / "code"
    if not workspace.is_dir():
        return []
    records = []
    for inventory in likely_project_roots(workspace):
        records.append(
            {
                "path": inventory.path.relative_to(round_dir).as_posix(),
                "languages": sorted(inventory.languages),
                "readmes": inventory.readmes,
                "dependency_manifests": inventory.dependencies,
                "tests": inventory.tests,
                "ci": inventory.ci,
                "suggested_smoke_commands": suggest_commands(inventory),
                "files_seen": inventory.files_seen,
                "inventory_truncated": inventory.truncated,
            }
        )
    return records


def classify(round_dir: Path) -> ReproducibilitySummary:
    code_evidence = local_code_evidence(round_dir)
    roots = root_records(round_dir)
    run_evidence = recorded_run_evidence(round_dir)

    if run_evidence:
        classification = "recorded_run_evidence_present"
        summary = "Recorded operator/sandbox run evidence is present; inspect it before making runtime claims."
    elif not code_evidence and not roots:
        classification = "no_code_evidence"
        summary = "No local code archive or code-like input directory was detected."
    elif not roots:
        classification = "not_attempted"
        summary = "Code evidence exists, but no likely prepared code root is available for static review."
    else:
        has_instructions = any(root["readmes"] or root["dependency_manifests"] for root in roots)
        has_commands = any(root["suggested_smoke_commands"] for root in roots)
        if has_instructions and has_commands:
            classification = "static_setup_present"
            summary = "Static setup evidence and suggested smoke commands are present; commands were not run."
        elif has_instructions:
            classification = "missing_test_commands"
            summary = "Static setup evidence is present, but no cheap test/build command was inferred."
        else:
            classification = "missing_instructions"
            summary = "Prepared code roots lack README or dependency/build manifest evidence."

    requests = evidence_requests(classification, roots, code_evidence)
    return ReproducibilitySummary(classification, summary, code_evidence, roots, run_evidence, requests)


def evidence_requests(classification: str, roots: list[dict[str, object]], code_evidence: list[str]) -> list[str]:
    if classification == "no_code_evidence":
        return []
    requests = []
    if classification == "not_attempted":
        requests.append("Prepare or manually unpack submitted code under work/code before code reviewers rely on it.")
    if classification in {"missing_instructions", "missing_test_commands"}:
        requests.append(
            "Ask for or cite the submitted development/test setup instructions before judging runtime quality."
        )
    if roots and not any(root["dependency_manifests"] for root in roots):
        requests.append("Record missing dependency/build manifests as reproducibility evidence.")
    if code_evidence and not roots:
        requests.append(
            "Classify code as not locally reproducible from submitted instructions "
            "if no inspectable root can be prepared."
        )
    return requests


def to_artifact(case_id: str, round_id: str, generated_at: str, summary: ReproducibilitySummary) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "round_id": round_id,
        "generated_at": generated_at,
        "classification": summary.classification,
        "summary": summary.summary,
        "execution_policy": "static_only_no_submitted_code_executed",
        "code_evidence": summary.code_evidence,
        "roots": summary.roots,
        "run_evidence": summary.run_evidence,
        "evidence_requests": summary.evidence_requests,
    }


def write_artifact(path: Path, artifact: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
