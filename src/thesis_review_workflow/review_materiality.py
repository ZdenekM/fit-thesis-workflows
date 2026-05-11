"""Advisory materiality decisions for optional thesis-review roles."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.structured_evidence import validate_structured_evidence_artifact

INDEX_REL = Path("work/review_materiality/index.json")
DECISION_SCHEMA = "review-materiality-decision-v1"
INDEX_SCHEMA = "review-materiality-index-v1"

WORKFLOW_PROFILES = {"supervisor_feedback", "opponent_review"}
PHASES = {"auto", "non_final", "final"}
MATERIALITY_ROLES = (
    "code_consistency",
    "code_quality",
    "figure_media",
    "typography_formal",
    "literature_citation",
    "github_intake",
    "quantitative_claims",
)
PACKET_ROLE_FILES = {
    "figure_media": Path("work/review_materiality/figure_media.json"),
    "typography_formal": Path("work/review_materiality/typography_formal.json"),
    "literature_citation": Path("work/review_materiality/literature_citation.json"),
}

CODE_WORKSPACE_PATHS = (
    "work/code_workspace.md",
    "work/serena_roots.json",
    "work/code/.prepare-code-workspace-manifest.json",
)
GITHUB_EVIDENCE_PATHS = (
    "outputs/github_code_intake.md",
    "inputs/github",
    "work/github-intake",
)
EVALUATION_TABLE_SUFFIXES = {".csv", ".tsv", ".xlsx", ".ods", ".parquet"}
MEDIA_INVENTORY_REL = Path("work/media_presence_inventory.jsonl")
VISUAL_INVENTORY_REL = Path("work/figure_media/visual_inventory.jsonl")
EVIDENCE_REQUIREMENTS_REL = Path("work/evidence_requirements.json")
QUANTITATIVE_CLAIMS_REL = Path("work/quantitative_claims.json")

GITHUB_URL_RE = re.compile(r"(?:https://github\.com/|git@github\.com:)", re.IGNORECASE)
ALLOWED_SYNTHETIC_REFS = ("operator-request:", "workflow-profile:", "phase:")


@dataclass(frozen=True)
class MaterialityDecision:
    role: str
    recommendation: str
    scope: str
    impact: str
    reason: str
    source_refs: tuple[str, ...]
    limitations: tuple[str, ...] = ()

    @property
    def material(self) -> bool:
        return self.recommendation == "material"


def is_materiality_decision_path(rel_path: str) -> bool:
    return Path(rel_path) in PACKET_ROLE_FILES.values()


def role_file_for(role: str) -> Path | None:
    return PACKET_ROLE_FILES.get(role)


def is_present(round_dir: Path, rel_path: str) -> bool:
    return (round_dir / rel_path).exists()


def first_existing(round_dir: Path, rel_paths: tuple[str, ...]) -> list[str]:
    return [rel_path for rel_path in rel_paths if is_present(round_dir, rel_path)]


def load_json_object(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, []
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"{path.name}: cannot read JSON materiality input: {exc}"]
    if not isinstance(loaded, dict):
        return None, [f"{path.name}: JSON materiality input must be an object"]
    return loaded, []


def load_valid_structured(
    round_dir: Path,
    rel_path: Path,
    *,
    case_id: str,
    round_id: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    path = round_dir / rel_path
    if not path.is_file():
        return None, []
    errors = validate_structured_evidence_artifact(round_dir, rel_path, case_id=case_id, round_id=round_id)
    if errors:
        return None, errors
    return load_json_object(path)


def load_media_inventory(round_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = round_dir / MEDIA_INVENTORY_REL
    if not path.is_file():
        return [], []
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{MEDIA_INVENTORY_REL.as_posix()}:{line_number}: invalid JSONL record: {exc.msg}")
            continue
        if not isinstance(loaded, dict):
            errors.append(f"{MEDIA_INVENTORY_REL.as_posix()}:{line_number}: record must be an object")
            continue
        records.append(loaded)
    return records, errors


def evidence_requirement_categories(requirements: dict[str, Any] | None) -> dict[str, list[str]]:
    if requirements is None:
        return {}
    loaded = requirements.get("requirements")
    if not isinstance(loaded, list):
        return {}
    categories: dict[str, list[str]] = {}
    for item in loaded:
        if not isinstance(item, dict):
            continue
        category = item.get("category")
        state = item.get("state")
        refs = item.get("evidence_refs")
        if not isinstance(category, str) or state == "not_applicable":
            continue
        source_refs = [ref for ref in refs if isinstance(ref, str)] if isinstance(refs, list) else []
        categories.setdefault(category, []).extend(source_refs or [EVIDENCE_REQUIREMENTS_REL.as_posix()])
    return categories


def evaluation_table_paths(round_dir: Path) -> list[str]:
    roots = (round_dir / "inputs", round_dir / "work", round_dir / "outputs")
    paths: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() in EVALUATION_TABLE_SUFFIXES:
                paths.append(path.relative_to(round_dir).as_posix())
    return paths


def github_note_refs(round_dir: Path) -> list[str]:
    refs: list[str] = []
    for notes_dir in (round_dir / "notes",):
        if not notes_dir.is_dir():
            continue
        for path in sorted(notes_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace")
            if GITHUB_URL_RE.search(text):
                refs.append(path.relative_to(round_dir).as_posix())
    return refs


def infer_phase(round_dir: Path, workflow_profile: str, requested_phase: str) -> str:
    if requested_phase != "auto":
        return requested_phase
    if workflow_profile == "opponent_review":
        return "final"
    _ = round_dir
    return "non_final"


def impact_for(workflow_profile: str, role: str) -> str:
    if workflow_profile == "opponent_review":
        impacts = {
            "figure_media": (
                "opponent report defensibility: presentation/visual claims, confidence labels, or manual checks"
            ),
            "typography_formal": "IS-item impact: formal presentation and readability calibration",
            "literature_citation": "IS-item impact: work with literature and claim support, not student coaching",
            "github_intake": (
                "contribution-scope impact: PR/repository evidence must be frozen before judging implementation"
            ),
            "quantitative_claims": (
                "grade-calibration impact: result claims need unit, baseline, magnitude, and reproducibility checks"
            ),
            "code_consistency": "mandatory code-bearing review: text-code and reproducibility support",
            "code_quality": (
                "mandatory code-bearing review: architecture, maintainability, runtime, and developer evidence"
            ),
        }
    else:
        impacts = {
            "figure_media": "student-action priority: fix visual/demo evidence boundaries that affect current feedback",
            "typography_formal": "student-action priority: late formal fixes that can still affect submission quality",
            "literature_citation": "student-action priority: cited-source support or clear literature gaps",
            "github_intake": "student-action priority: freeze and scope GitHub/PR evidence before code feedback",
            "quantitative_claims": "student-action priority: make metric/result claims proportionate and reproducible",
            "code_consistency": "mandatory code-bearing review: unsupported implementation and reproducibility claims",
            "code_quality": "mandatory code-bearing review: implementation design, tests, and developer evidence",
        }
    return impacts[role]


def material_decision(
    workflow_profile: str,
    role: str,
    *,
    scope: str,
    reason: str,
    source_refs: list[str],
    limitations: tuple[str, ...] = (),
) -> MaterialityDecision:
    return MaterialityDecision(
        role=role,
        recommendation="material",
        scope=scope,
        impact=impact_for(workflow_profile, role),
        reason=reason,
        source_refs=tuple(sorted(dict.fromkeys(source_refs))),
        limitations=limitations,
    )


def not_material_decision(workflow_profile: str, role: str, *, reason: str) -> MaterialityDecision:
    return MaterialityDecision(
        role=role,
        recommendation="not_material",
        scope="not_triggered",
        impact=impact_for(workflow_profile, role),
        reason=reason,
        source_refs=(),
    )


def merge_material(
    decisions: dict[str, MaterialityDecision],
    workflow_profile: str,
    role: str,
    *,
    scope: str,
    reason: str,
    source_refs: list[str],
    limitations: tuple[str, ...] = (),
) -> None:
    existing = decisions.get(role)
    if existing is None or not existing.material:
        decisions[role] = material_decision(
            workflow_profile,
            role,
            scope=scope,
            reason=reason,
            source_refs=source_refs,
            limitations=limitations,
        )
        return
    decisions[role] = material_decision(
        workflow_profile,
        role,
        scope=existing.scope,
        reason=f"{existing.reason}; {reason}",
        source_refs=[*existing.source_refs, *source_refs],
        limitations=(*existing.limitations, *limitations),
    )


def build_materiality_decisions(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    workflow_profile: str,
    phase: str = "auto",
    requested_roles: tuple[str, ...] = (),
) -> tuple[list[MaterialityDecision], list[str], str]:
    if workflow_profile not in WORKFLOW_PROFILES:
        return [], [f"unknown workflow profile: {workflow_profile}"], phase
    if phase not in PHASES:
        return [], [f"unknown phase: {phase}"], phase
    unknown_roles = sorted(set(requested_roles) - set(MATERIALITY_ROLES))
    if unknown_roles:
        return [], [f"unknown requested materiality role: {', '.join(unknown_roles)}"], phase

    resolved_phase = infer_phase(round_dir, workflow_profile, phase)
    errors: list[str] = []
    decisions = {
        role: not_material_decision(workflow_profile, role, reason="no structured materiality trigger detected")
        for role in MATERIALITY_ROLES
    }

    evidence_requirements, requirement_errors = load_valid_structured(
        round_dir,
        EVIDENCE_REQUIREMENTS_REL,
        case_id=case_id,
        round_id=round_id,
    )
    errors.extend(requirement_errors)
    quantitative_claims, quantitative_errors = load_valid_structured(
        round_dir,
        QUANTITATIVE_CLAIMS_REL,
        case_id=case_id,
        round_id=round_id,
    )
    errors.extend(quantitative_errors)
    media_records, media_errors = load_media_inventory(round_dir)
    errors.extend(media_errors)

    for role in requested_roles:
        merge_material(
            decisions,
            workflow_profile,
            role,
            scope="explicit_request",
            reason="operator or formal skill request explicitly asked for this role",
            source_refs=[f"operator-request:{role}"],
        )

    code_refs = first_existing(round_dir, CODE_WORKSPACE_PATHS)
    if code_refs:
        for role in ("code_consistency", "code_quality"):
            merge_material(
                decisions,
                workflow_profile,
                role,
                scope="mandatory_code_bearing_rule",
                reason="prepared code workspace evidence exists",
                source_refs=code_refs,
            )

    github_refs = [*first_existing(round_dir, GITHUB_EVIDENCE_PATHS), *github_note_refs(round_dir)]
    if github_refs:
        merge_material(
            decisions,
            workflow_profile,
            "github_intake",
            scope="github_or_pr_evidence",
            reason="GitHub/PR evidence is present or explicitly referenced",
            source_refs=github_refs,
        )

    requirement_categories = evidence_requirement_categories(evidence_requirements)
    media_refs = requirement_categories.get("media", [])
    if (round_dir / VISUAL_INVENTORY_REL).is_file():
        merge_material(
            decisions,
            workflow_profile,
            "figure_media",
            scope="visual_inventory_review",
            reason="visual inventory already exists",
            source_refs=[VISUAL_INVENTORY_REL.as_posix()],
        )
    if media_records:
        categories = {str(record.get("category")) for record in media_records if record.get("category")}
        scope = "presentation_demo_boundary" if categories <= {"video", "presentation"} else "visual_media_review"
        reason = (
            "structural media inventory contains presentation/demo media"
            if scope == "presentation_demo_boundary"
            else ("structural media inventory contains visual/media artifacts")
        )
        refs = [str(record.get("path")) for record in media_records if isinstance(record.get("path"), str)]
        merge_material(decisions, workflow_profile, "figure_media", scope=scope, reason=reason, source_refs=refs)
    if media_refs:
        merge_material(
            decisions,
            workflow_profile,
            "figure_media",
            scope="evidence_requirement_media",
            reason="structured evidence requirements include media evidence",
            source_refs=media_refs,
        )

    existing_outputs = {
        "figure_media": "outputs/figure_media_review.md",
        "typography_formal": "outputs/typography_formal_review.md",
        "literature_citation": "outputs/literature_citation_review.md",
    }
    for role, rel_path in existing_outputs.items():
        if (round_dir / rel_path).is_file():
            merge_material(
                decisions,
                workflow_profile,
                role,
                scope="existing_review_output",
                reason="existing internal evidence output should remain visible to synthesis",
                source_refs=[rel_path],
            )

    if workflow_profile == "opponent_review":
        for role in ("typography_formal", "literature_citation"):
            merge_material(
                decisions,
                workflow_profile,
                role,
                scope="opponent_is_item",
                reason="opponent workflow has IS/report calibration items for this role",
                source_refs=["workflow-profile:opponent_review"],
            )
    elif resolved_phase == "final":
        merge_material(
            decisions,
            workflow_profile,
            "typography_formal",
            scope="final_supervisor_phase",
            reason="supervisor workflow is in final/prefinal phase",
            source_refs=["phase:final"],
        )

    quantitative_refs: list[str] = []
    if quantitative_claims is not None:
        quantitative_refs.append(QUANTITATIVE_CLAIMS_REL.as_posix())
    quantitative_refs.extend(requirement_categories.get("evaluation_data", []))
    quantitative_refs.extend(requirement_categories.get("evaluation_script", []))
    quantitative_refs.extend(evaluation_table_paths(round_dir))
    if quantitative_refs:
        merge_material(
            decisions,
            workflow_profile,
            "quantitative_claims",
            scope="quantitative_or_evaluation_evidence",
            reason="structured quantitative/evaluation evidence is present",
            source_refs=quantitative_refs,
        )

    ordered = [decisions[role] for role in MATERIALITY_ROLES]
    return ordered, errors, resolved_phase


def decision_payload(
    decision: MaterialityDecision,
    *,
    case_id: str,
    round_id: str,
    workflow_profile: str,
    generated_at: str,
    producer_role: str,
) -> dict[str, Any]:
    payload = asdict(decision)
    payload.update(
        {
            "schema_version": DECISION_SCHEMA,
            "case_id": case_id,
            "round_id": round_id,
            "workflow_profile": workflow_profile,
            "generated_at": generated_at,
            "producer_role": producer_role,
        }
    )
    payload["source_refs"] = list(decision.source_refs)
    payload["limitations"] = list(decision.limitations)
    return payload


def write_materiality_decisions(
    round_dir: Path,
    decisions: list[MaterialityDecision],
    *,
    case_id: str,
    round_id: str,
    workflow_profile: str,
    phase: str,
    generated_at: str,
    producer_role: str = "check-review-materiality",
) -> list[Path]:
    materiality_dir = round_dir / "work" / "review_materiality"
    materiality_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    index_payload = {
        "schema_version": INDEX_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "workflow_profile": workflow_profile,
        "phase": phase,
        "generated_at": generated_at,
        "producer_role": producer_role,
        "decisions": [asdict(decision) for decision in decisions],
    }
    index_path = round_dir / INDEX_REL
    index_path.write_text(json.dumps(index_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    written.append(index_path)

    material_roles = {decision.role for decision in decisions if decision.material}
    for role, rel_path in PACKET_ROLE_FILES.items():
        path = round_dir / rel_path
        if role not in material_roles:
            if path.is_file():
                path.unlink()
            continue
        decision = next(item for item in decisions if item.role == role)
        payload = decision_payload(
            decision,
            case_id=case_id,
            round_id=round_id,
            workflow_profile=workflow_profile,
            generated_at=generated_at,
            producer_role=producer_role,
        )
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    return written


def source_ref_is_allowed(value: str) -> bool:
    return is_safe_round_relative_path(value) or value.startswith(ALLOWED_SYNTHETIC_REFS)


def validate_materiality_decision_payload(
    payload: dict[str, Any],
    rel_path: str,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    expected_workflow_profile: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != DECISION_SCHEMA:
        errors.append(f"{rel_path}: schema_version must be {DECISION_SCHEMA}")
    if case_id is not None and payload.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id must be {case_id}")
    if round_id is not None and payload.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id must be {round_id}")
    workflow_profile = payload.get("workflow_profile")
    if workflow_profile not in WORKFLOW_PROFILES:
        errors.append(f"{rel_path}: workflow_profile must be one of {sorted(WORKFLOW_PROFILES)}")
    elif expected_workflow_profile is not None and workflow_profile != expected_workflow_profile:
        errors.append(f"{rel_path}: workflow_profile must be {expected_workflow_profile}")
    role = payload.get("role")
    if role not in MATERIALITY_ROLES:
        errors.append(f"{rel_path}: role must be one of {list(MATERIALITY_ROLES)}")
    expected_path = PACKET_ROLE_FILES.get(role) if isinstance(role, str) else None
    if expected_path is not None and expected_path.as_posix() != rel_path:
        errors.append(f"{rel_path}: role {role} must be stored at {expected_path.as_posix()}")
    if payload.get("recommendation") != "material":
        errors.append(f"{rel_path}: packet materiality decision files must have recommendation=material")
    for field in ("scope", "impact", "reason", "generated_at", "producer_role"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{rel_path}: {field} must be a non-empty string")
    source_refs = payload.get("source_refs")
    if not isinstance(source_refs, list) or not source_refs:
        errors.append(f"{rel_path}: source_refs must be a non-empty list")
    elif any(not isinstance(item, str) or not source_ref_is_allowed(item) for item in source_refs):
        errors.append(f"{rel_path}: source_refs must be safe round-relative paths or allowed synthetic refs")
    limitations = payload.get("limitations")
    if limitations is not None and not isinstance(limitations, list):
        errors.append(f"{rel_path}: limitations must be a list")
    return errors


def validate_review_materiality_artifact(
    round_dir: Path,
    rel_path: str,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    workflow_profile: str | None = None,
) -> list[str]:
    if not is_materiality_decision_path(rel_path):
        return [f"{rel_path}: unknown review materiality decision path"]
    path = round_dir / rel_path
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{rel_path}: missing review materiality decision"]
    except OSError as exc:
        return [f"{rel_path}: cannot read review materiality decision: {exc}"]
    except json.JSONDecodeError as exc:
        return [f"{rel_path}: invalid JSON: {exc.msg}"]
    if not isinstance(loaded, dict):
        return [f"{rel_path}: review materiality decision must be a JSON object"]
    return validate_materiality_decision_payload(
        loaded,
        rel_path,
        case_id=case_id,
        round_id=round_id,
        expected_workflow_profile=workflow_profile,
    )
