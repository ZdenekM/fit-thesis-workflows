"""Shared helpers for role-specific review packet generation."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from thesis_review_workflow.commands import repo_command_environment, resolve_repo_command
from thesis_review_workflow.review_materiality import (
    is_materiality_decision_path,
    unresolved_required_next_actions,
    validate_review_materiality_artifact,
)
from thesis_review_workflow.structured_evidence import (
    STRUCTURED_EVIDENCE_SCHEMAS,
    validate_structured_evidence_artifact,
)

SEMANTIC_MODEL = "gpt-5.5"
SEMANTIC_REASONING = "xhigh"
MECHANICAL_MODEL = "gpt-5.3-codex-spark"
MECHANICAL_REASONING = "high"

CASE_INPUTS = ("case.md",)
PROFILE_INPUTS = (
    "profiles/default.md",
    "profiles/local/default.md",
)
COMMON_CONSTRAINTS = (
    "Use only case-local or round-relative paths in notes and outputs.",
    "State missing, unavailable, or uninspected evidence as a limitation; do not infer failure from absence.",
    "Use confidence labels for important claims: [FAKT], [INTERPRETACE], [ODHAD], [NEOVERENO], [K RUCNI KONTROLE].",
    "Do not move private case inputs, generated outputs, or submitted code into tracked repository paths.",
)
SNAPSHOT_SOURCE_PATHS = (
    "work/current_evidence_snapshot.json",
    "work/code_workspace.md",
    "work/serena_roots.json",
    "work/review_manifest.json",
    "work/agent_coverage.json",
    "outputs/github_code_intake.md",
    "outputs/oponent_podklady_revidovane.md",
    "work/opponent_report_trace.json",
    "work/oponent_posudek_draft.md",
    "work/supervisor_report_feedback_history.json",
    "work/supervisor_report_trace.json",
    "work/vedouci_posudek_draft.md",
    "outputs/vedouci_posudek_revidovany.md",
    "work/supervisor_report_confirmation.json",
    "work/reviews/feedback_student_review.json",
    "work/reviews/opponent_materials_review.json",
    "work/reviews/opponent_report_review.json",
    "work/reviews/supervisor_report_review.json",
)
LATE_COMMUNICATION_PATHS = (
    "notes/operator-late-communications.md",
    "notes/late-communications.md",
    "notes/round-notes.md",
    "work/current_evidence_snapshot.json",
)
CODE_WORKSPACE_PATHS = (
    "work/code_workspace.md",
    "work/serena_roots.json",
    "work/code/.prepare-code-workspace-manifest.json",
)
QUANTITATIVE_CLAIMS_REL = "work/quantitative_claims.json"


@dataclass(frozen=True)
class PacketRole:
    key: str
    title: str
    skill: str
    expected_output: str
    mission: str
    focus: tuple[str, ...]
    role_inputs: tuple[str, ...]
    constraints: tuple[str, ...]
    activation: str = "mandatory"
    activation_paths: tuple[str, ...] = ()
    model: str = SEMANTIC_MODEL
    reasoning: str = SEMANTIC_REASONING
    model_note: str = "Semantic reviewer role; keep on gpt-5.5/xhigh unless the operator changes the policy."
    activation_check: tuple[str, ...] = ()
    activation_workflow_profile: str | None = None


def rel_status(
    round_dir: Path,
    rel_path: str,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    materiality_workflow_profile: str | None = None,
) -> str:
    path = round_dir / rel_path
    if not path.exists():
        return "missing"
    if is_materiality_decision_path(rel_path):
        errors = validate_review_materiality_artifact(
            round_dir,
            rel_path,
            case_id=case_id,
            round_id=round_id,
            workflow_profile=materiality_workflow_profile,
        )
        if errors:
            return "invalid"
    if rel_path in STRUCTURED_EVIDENCE_SCHEMAS:
        errors = validate_structured_evidence_artifact(round_dir, rel_path, case_id=case_id, round_id=round_id)
        if errors:
            return "invalid"
    return "present"


def existing_paths(
    round_dir: Path,
    rel_paths: tuple[str, ...],
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    materiality_workflow_profile: str | None = None,
) -> list[str]:
    return [
        rel_path
        for rel_path in rel_paths
        if rel_status(
            round_dir,
            rel_path,
            case_id=case_id,
            round_id=round_id,
            materiality_workflow_profile=materiality_workflow_profile,
        )
        == "present"
    ]


def top_level_paths(round_dir: Path, rel_dir: str, *, limit: int = 12) -> list[str]:
    directory = round_dir / rel_dir
    if not directory.is_dir():
        return []
    paths = sorted(path for path in directory.iterdir() if path.is_file() or (path.is_dir() and not path.is_symlink()))
    rendered: list[str] = []
    for path in paths[:limit]:
        suffix = "/" if path.is_dir() else ""
        rendered.append(f"{rel_dir}/{path.name}{suffix}")
    return rendered


def extracted_text_paths(round_dir: Path, *, limit: int = 8) -> list[str]:
    extracted = round_dir / "extracted"
    if not extracted.is_dir():
        return []
    paths = sorted(path for path in extracted.rglob("*.txt") if path.is_file())
    return [path.relative_to(round_dir).as_posix() for path in paths[:limit]]


def path_list(lines: list[str]) -> str:
    if not lines:
        return "- none detected\n"
    return "".join(f"- `{line}`\n" for line in lines)


def text_list(lines: list[str]) -> str:
    if not lines:
        return "- none\n"
    return "".join(f"- {line}\n" for line in lines)


def status_list(
    round_dir: Path,
    paths: tuple[str, ...],
    *,
    case_id: str | None = None,
    round_id: str | None = None,
) -> str:
    return "".join(
        f"- `{rel_path}` ({rel_status(round_dir, rel_path, case_id=case_id, round_id=round_id)})\n"
        for rel_path in paths
    )


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_status_list(
    round_dir: Path,
    paths: tuple[str, ...],
    *,
    case_id: str | None = None,
    round_id: str | None = None,
) -> str:
    lines: list[str] = []
    for rel_path in paths:
        status = rel_status(round_dir, rel_path, case_id=case_id, round_id=round_id)
        digest = sha256_file(round_dir / rel_path)
        hash_text = f", sha256={digest}" if digest else ""
        lines.append(f"- `{rel_path}` ({status}{hash_text})")
    return "\n".join(lines) + "\n"


def has_code_evidence(round_dir: Path) -> bool:
    return any((round_dir / rel_path).exists() for rel_path in CODE_WORKSPACE_PATHS)


def check_passes(root: Path, args: tuple[str, ...], *, case_id: str, round_id: str) -> bool:
    if not root.is_dir():
        return False
    command_args = [item.format(case_id=case_id, round_id=round_id) for item in args]
    if case_id not in command_args and round_id not in command_args:
        command_args = [*command_args, case_id, round_id]
    completed = subprocess.run(
        resolve_repo_command(root, command_args),
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=repo_command_environment(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.returncode == 0


def role_is_active(
    round_dir: Path,
    role: PacketRole,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
) -> bool:
    if role.activation == "mandatory":
        return True
    if role.activation == "code":
        return has_code_evidence(round_dir)
    if role.activation == "existing_artifact":
        paths = role.activation_paths or role.role_inputs
        return bool(
            existing_paths(
                round_dir,
                paths,
                case_id=case_id,
                round_id=round_id,
                materiality_workflow_profile=role.activation_workflow_profile,
            )
        )
    if role.activation == "existing_artifact_or_next_action":
        paths = role.activation_paths or role.role_inputs
        if existing_paths(
            round_dir,
            paths,
            case_id=case_id,
            round_id=round_id,
            materiality_workflow_profile=role.activation_workflow_profile,
        ):
            return True
        if case_id is None or round_id is None or role.activation_workflow_profile is None:
            return False
        actions, errors = unresolved_required_next_actions(
            round_dir,
            workflow_profile=role.activation_workflow_profile,
            case_id=case_id,
            round_id=round_id,
        )
        if errors:
            return False
        return any(action.get("role") == role.key for action in actions)
    if role.activation == "check":
        if case_id is None or round_id is None or not role.activation_check:
            return False
        return check_passes(round_dir.parents[3], role.activation_check, case_id=case_id, round_id=round_id)
    raise ValueError(f"Unknown packet activation mode: {role.activation}")


def prune_inactive_packets(
    packet_dir: Path,
    roles: tuple[PacketRole, ...],
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
) -> None:
    for role in roles:
        if role_is_active(round_dir, role, case_id=case_id, round_id=round_id):
            continue
        path = packet_dir / f"{role.key}.md"
        if path.is_file():
            path.unlink()


def generated_role_paths(
    roles: tuple[PacketRole, ...],
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
) -> list[str]:
    return [f"{role.key}.md" for role in roles if role_is_active(round_dir, role, case_id=case_id, round_id=round_id)]


def first_nonempty_lines(path: Path, *, limit: int = 5) -> list[str]:
    if not path.is_file():
        return []
    lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line == "-":
            continue
        lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def previous_feedback_index(round_dir: Path, *, limit: int = 8) -> list[str]:
    case_dir = round_dir.parents[1]
    current_round = round_dir.name
    rounds_dir = case_dir / "rounds"
    if not rounds_dir.is_dir():
        return []
    entries: list[str] = []
    for candidate in sorted(rounds_dir.iterdir()):
        if candidate.name == current_round:
            continue
        feedback = candidate / "outputs" / "feedback_student.md"
        if feedback.is_file():
            entries.append(f"round `{candidate.name}`: `outputs/feedback_student.md`")
        if len(entries) >= limit:
            break
    return entries


def current_evidence_snapshot_section(round_dir: Path, *, case_id: str, round_id: str) -> str:
    review_records = tuple(
        path.relative_to(round_dir).as_posix()
        for path in sorted((round_dir / "work" / "reviews").glob("*.json"))
        if path.is_file()
    )
    paths = SNAPSHOT_SOURCE_PATHS + review_records
    return "\n".join(
        [
            "## Current Evidence Snapshot",
            "",
            hash_status_list(round_dir, paths, case_id=case_id, round_id=round_id),
            "Markdown packets render this snapshot for orientation only. Readiness-critical hashes or freshness facts "
            "must come from `work/current_evidence_snapshot.json`, review records, manifests, traces, or other "
            "structured/hash-bound artifacts.",
            "",
        ]
    )


def omen_advisory_section(round_dir: Path) -> str:
    paths = (
        "work/current_evidence_snapshot.json",
        "work/code_quality_omen.md",
        "work/code_quality_omen.json",
    )
    return "\n".join(
        [
            "## Omen Advisory Static Analysis",
            "",
            "Omen MCP is useful for code-quality reviewer confidence but is not an operator prerequisite or a "
            "standalone verdict.",
            status_list(round_dir, paths),
            "If Omen was run, map its signals back to concrete code evidence and thesis defensibility before using "
            "them.",
            "",
        ]
    )


def late_communications_section(round_dir: Path) -> str:
    return "\n".join(
        [
            "## Late Communications And Diagnostics",
            "",
            status_list(round_dir, LATE_COMMUNICATION_PATHS),
            "Use late-breaking notes only as references when they are case-local, registered, or registerable as "
            "supporting work artifacts.",
            "",
        ]
    )


def materiality_next_actions_section(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    workflow_profile: str,
) -> str:
    actions, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile=workflow_profile,
        case_id=case_id,
        round_id=round_id,
    )
    lines = ["## Materiality Next Actions", ""]
    if errors:
        lines.extend(f"- invalid materiality index: {error}" for error in errors)
    elif not actions:
        lines.append("- none")
    else:
        for action in actions:
            role = action.get("role", "unknown")
            required = action.get("required_artifact_path", "unknown")
            command = action.get("command", "not recorded")
            reason = action.get("reason", "not recorded")
            limitation = action.get("typed_limitation_scope", "not recorded")
            lines.append(f"- `{role}` requires `{required}`: {reason}")
            lines.append(f"  Command/skill: {command}")
            lines.append(f"  Typed limitation scope if unavailable: `{limitation}`")
    lines.extend(
        [
            "",
            "Resolve required actions before synthesis/final readiness, or record a typed workflow limitation.",
            "",
        ]
    )
    return "\n".join(lines)


def _count_claim_values(claims: list[object], field: str) -> str:
    counts: dict[str, int] = {}
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        value = claim.get(field)
        if isinstance(value, str) and value:
            counts[value] = counts.get(value, 0) + 1
    if not counts:
        return "none"
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def quantitative_claims_handoff_section(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    limit: int = 8,
) -> str:
    lines = ["## Quantitative Claims Handoff", ""]
    path = round_dir / QUANTITATIVE_CLAIMS_REL
    if not path.is_file():
        lines.extend(
            [
                f"- `{QUANTITATIVE_CLAIMS_REL}` is missing.",
                "- If this packet belongs to the quantitative role, use it with the materiality next action to "
                "author the structured handoff.",
                "- If quantitative materiality is active, resolve the materiality next action before synthesis.",
                "",
            ]
        )
        return "\n".join(lines)

    errors = validate_structured_evidence_artifact(
        round_dir,
        QUANTITATIVE_CLAIMS_REL,
        case_id=case_id,
        round_id=round_id,
    )
    if errors:
        lines.extend(f"- invalid quantitative claims artifact: {error}" for error in errors)
        lines.append("")
        return "\n".join(lines)

    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        lines.extend([f"- cannot read `{QUANTITATIVE_CLAIMS_REL}`: {exc}", ""])
        return "\n".join(lines)
    claims = loaded.get("claims") if isinstance(loaded, dict) else None
    claim_list = claims if isinstance(claims, list) else []
    lines.extend(
        [
            f"- Artifact: `{QUANTITATIVE_CLAIMS_REL}` ({len(claim_list)} claim(s))",
            f"- Status counts: {_count_claim_values(claim_list, 'status')}",
            f"- Baseline counts: {_count_claim_values(claim_list, 'baseline_status')}",
            f"- Practical-context counts: {_count_claim_values(claim_list, 'practical_context')}",
            f"- Overclaim-risk counts: {_count_claim_values(claim_list, 'overclaim_risk')}",
            "",
        ]
    )
    if claim_list:
        lines.append("Claims:")
    for claim in claim_list[:limit]:
        if not isinstance(claim, dict):
            continue
        claim_id = str(claim.get("claim_id", "unknown")).strip() or "unknown"
        kind = str(claim.get("kind", "unknown")).strip() or "unknown"
        status = str(claim.get("status", "unknown")).strip() or "unknown"
        baseline = str(claim.get("baseline_status", "unknown")).strip() or "unknown"
        context = str(claim.get("practical_context", "unknown")).strip() or "unknown"
        overclaim = str(claim.get("overclaim_risk", "unknown")).strip() or "unknown"
        magnitude = str(claim.get("practical_magnitude", "")).strip()
        summary = str(claim.get("summary", "")).strip() or "No summary recorded."
        evidence_refs = claim.get("evidence_refs")
        if isinstance(evidence_refs, list):
            evidence = ", ".join(f"`{item}`" for item in evidence_refs if isinstance(item, str)) or "none"
        else:
            evidence = "none"
        lines.append(
            f"- `{claim_id}` {kind}/{status}, baseline={baseline}, practical_context={context}; "
            f"overclaim_risk={overclaim}; evidence: {evidence}; "
            f"magnitude: {magnitude or 'not recorded'}; summary: {summary}"
        )
    if len(claim_list) > limit:
        lines.append(f"- {len(claim_list) - limit} additional claim(s) omitted from packet.")
    lines.extend(
        [
            "",
            "Use this structured handoff first. Open raw result sections only to verify material claims, resolve "
            "contradictions, or calibrate wording.",
            "",
        ]
    )
    return "\n".join(lines)
