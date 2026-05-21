"""Advisory materiality decisions for optional thesis-review roles."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.reuse import CoverageSatisfiedBy, coverage_satisfies_without_fresh_review
from thesis_review_workflow.structured_evidence import (
    CURRENT_EVIDENCE_SNAPSHOT_REL,
    validate_structured_evidence_artifact,
)
from thesis_review_workflow.theses_similarity import (
    THESES_SIMILARITY_ASSESSMENT_REL,
    THESES_SIMILARITY_EXTRACTED_TEXT_REL,
    THESES_SIMILARITY_INTAKE_REL,
    THESES_SIMILARITY_REPORT_REL,
    THESES_SIMILARITY_REVIEW_REL,
    THESES_SIMILARITY_SILENT_USED_FINDINGS,
    theses_similarity_materiality_evidence_present,
    theses_similarity_materiality_refs,
)
from thesis_review_workflow.theses_similarity_coverage import (
    theses_similarity_assessment_is_silent_no_concern,
    theses_similarity_silent_internal_evidence_satisfied,
)

INDEX_REL = Path("work/review_materiality/index.json")
PROFILE_DIRS = {
    "supervisor_feedback": Path("work/review_materiality/supervisor_feedback"),
    "supervisor_report": Path("work/review_materiality/supervisor_report"),
    "opponent_review": Path("work/review_materiality/opponent_review"),
}
DECISION_SCHEMA = "review-materiality-decision-v1"
INDEX_SCHEMA = "review-materiality-index-v1"

WORKFLOW_PROFILES = {"supervisor_feedback", "supervisor_report", "opponent_review"}
PHASES = {"auto", "non_final", "final"}
MATERIALITY_ROLES = (
    "code_consistency",
    "code_quality",
    "figure_media",
    "typography_formal",
    "literature_citation",
    "github_intake",
    "quantitative_claims",
    "theses_similarity",
)
PACKET_ROLE_FILES = {
    "figure_media": Path("work/review_materiality/supervisor_feedback/figure_media.json"),
    "typography_formal": Path("work/review_materiality/supervisor_feedback/typography_formal.json"),
    "literature_citation": Path("work/review_materiality/supervisor_feedback/literature_citation.json"),
    "theses_similarity": Path("work/review_materiality/supervisor_feedback/theses_similarity.json"),
}
LEGACY_PACKET_ROLE_FILES = {
    "figure_media": Path("work/review_materiality/figure_media.json"),
    "typography_formal": Path("work/review_materiality/typography_formal.json"),
    "literature_citation": Path("work/review_materiality/literature_citation.json"),
}

CODE_WORKSPACE_PATHS = (
    "work/code_workspace.md",
    "work/serena_roots.json",
    "work/code/.prepare-code-workspace-manifest.json",
)
GITHUB_EVIDENCE_MARKER_PATHS = ("outputs/github_code_intake.md",)
GITHUB_EVIDENCE_ROOTS = (Path("inputs/github"), Path("work/github-intake"))
EVALUATION_TABLE_SUFFIXES = {".csv", ".tsv", ".xlsx", ".ods", ".parquet"}
MEDIA_INVENTORY_REL = Path("work/media_presence_inventory.jsonl")
VISUAL_INVENTORY_REL = Path("work/figure_media/visual_inventory.jsonl")
EVIDENCE_REQUIREMENTS_REL = Path("work/evidence_requirements.json")
QUANTITATIVE_CLAIMS_REL = Path("work/quantitative_claims.json")
REVIEW_MANIFEST_REL = Path("work/review_manifest.json")
NEXT_ACTION_STATUSES = {"unresolved", "resolved_by_artifact", "resolved_by_limitation"}
NEXT_ACTION_SEVERITIES = {"required", "advisory"}
NEXT_ACTION_ROLES = {"github_intake", "quantitative_claims", "theses_similarity"}
NEXT_ACTION_STATES = {
    "missing_artifact",
    "validator_failed",
    "present_not_synthesis_covered",
    "silent_no_concern_waiting_for_reviewed_synthesis",
    "current_reviewed_artifact",
    "current_synthesis_covered_artifact",
    "typed_limitation",
}
NEXT_ACTION_CONFIG = {
    "github_intake": {
        "required_artifact_path": "outputs/github_code_intake.md",
        "command": "import-github-code <case-id> <round-id> ...; then run thesis-github-code-intake",
        "skill": "thesis-github-code-intake",
        "typed_limitation_scope": "github_intake",
    },
    "quantitative_claims": {
        "required_artifact_path": QUANTITATIVE_CLAIMS_REL.as_posix(),
        "command": "Run an authorized thesis-quantitative-claims-review, then check-evaluation-claims.",
        "skill": "thesis-quantitative-claims-review",
        "typed_limitation_scope": "quantitative_claims",
    },
    "theses_similarity": {
        "required_artifact_path": THESES_SIMILARITY_REVIEW_REL,
        "command": "Run an authorized thesis-theses-similarity-review, then check-theses-similarity-report.",
        "skill": "thesis-theses-similarity-review",
        "typed_limitation_scope": "theses_similarity",
    },
}
MATERIALITY_LIMITATION_TYPES = {
    "unavailable_evidence",
    "unavailable_tool",
    "manual_review_required",
    "not_material_to_final",
    "out_of_scope_for_round",
    "upstream_or_external_scope",
}
MATERIALITY_LIMITATION_STATUSES = {"accepted", "closed", "resolved"}
MATERIALITY_LIMITATION_TRIGGER = "materiality_next_action"
MATERIALITY_COVERAGE_STATES = {
    "no_material_issue",
    "typed_limitation",
    "current_handoff",
    "current_reviewed_artifact",
    "current_synthesis_covered_artifact",
    "silent_internal_evidence",
    "silent_no_concern_waiting_for_reviewed_synthesis",
    "fresh_review_required",
    "not_satisfied",
}
MATERIALITY_ROLE_ARTIFACTS = {
    "code_consistency": "outputs/code_consistency.md",
    "code_quality": "outputs/code_quality_review.md",
    "figure_media": "outputs/figure_media_review.md",
    "typography_formal": "outputs/typography_formal_review.md",
    "literature_citation": "outputs/literature_citation_review.md",
    "github_intake": "outputs/github_code_intake.md",
    "quantitative_claims": QUANTITATIVE_CLAIMS_REL.as_posix(),
    "theses_similarity": THESES_SIMILARITY_REVIEW_REL,
}
SYNTHESIS_ARTIFACT_BY_WORKFLOW = {
    "supervisor_feedback": "outputs/feedback_student.md",
    "supervisor_report": "outputs/vedouci_posudek_revidovany.md",
    "opponent_review": "outputs/oponent_podklady_revidovane.md",
}
REVIEWED_MANIFEST_STATUSES = {"reviewed", "reviewed_with_notes"}
SILENT_THESES_SIMILARITY_SYNTHESIS_WORKFLOWS = {"supervisor_report", "opponent_review"}

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


@dataclass(frozen=True)
class MaterialityNextAction:
    role: str
    workflow_profile: str
    status: str
    severity: str
    required_artifact_path: str
    reason: str
    command: str
    skill: str
    source_refs: tuple[str, ...]
    source_sha256: dict[str, str]
    typed_limitation_scope: str
    limitations: tuple[str, ...] = ()
    state: str = "missing_artifact"

    @property
    def unresolved(self) -> bool:
        return self.status == "unresolved"


def profile_dir(workflow_profile: str) -> Path:
    return PROFILE_DIRS.get(workflow_profile, Path("work") / "review_materiality" / workflow_profile)


def profile_index_rel(workflow_profile: str) -> Path:
    return profile_dir(workflow_profile) / "index.json"


def role_file_for_profile(role: str, workflow_profile: str) -> Path | None:
    if role not in PACKET_ROLE_FILES:
        return None
    return profile_dir(workflow_profile) / f"{role}.json"


def is_materiality_decision_path(rel_path: str) -> bool:
    path = Path(rel_path)
    return (
        path in PACKET_ROLE_FILES.values()
        or path in LEGACY_PACKET_ROLE_FILES.values()
        or (
            len(path.parts) == 4
            and path.parts[:2] == ("work", "review_materiality")
            and path.name in {f"{role}.json" for role in PACKET_ROLE_FILES}
        )
    )


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


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def github_structured_refs(round_dir: Path) -> list[str]:
    refs = first_existing(round_dir, GITHUB_EVIDENCE_MARKER_PATHS)
    for root_rel in GITHUB_EVIDENCE_ROOTS:
        root = round_dir / root_rel
        if not root.is_dir():
            continue
        refs.extend(path.relative_to(round_dir).as_posix() for path in sorted(root.rglob("*")) if path.is_file())
    return sorted(dict.fromkeys(refs))


def infer_phase(round_dir: Path, workflow_profile: str, requested_phase: str) -> str:
    if requested_phase != "auto":
        return requested_phase
    if workflow_profile in {"opponent_review", "supervisor_report"}:
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
            "theses_similarity": (
                "opponent report defensibility: similarity matches must be resolved or limited before wording"
            ),
            "code_consistency": "mandatory code-bearing review: text-code and reproducibility support",
            "code_quality": (
                "mandatory code-bearing review: architecture, maintainability, runtime, and developer evidence"
            ),
        }
    elif workflow_profile == "supervisor_report":
        impacts = {
            "figure_media": "supervisor report defensibility: visual/result evidence and manual-check boundaries",
            "typography_formal": "supervisor report context: final presentation risks that affect overall assessment",
            "literature_citation": "supervisor report field: work with literature and source-use evidence",
            "github_intake": (
                "publication/open-source/contribution evidence before mentioning repository or PR activity"
            ),
            "quantitative_claims": "grade/points calibration: result claims need unit, baseline, and practical context",
            "theses_similarity": "supervisor report defensibility: similarity matches must be resolved or limited",
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
            "theses_similarity": "student-action priority: investigate unresolved similarity-report matches",
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

    github_refs = github_structured_refs(round_dir)
    if github_refs:
        merge_material(
            decisions,
            workflow_profile,
            "github_intake",
            scope="github_or_pr_evidence",
            reason="structured GitHub/PR evidence is present",
            source_refs=github_refs,
        )

    if theses_similarity_materiality_evidence_present(round_dir):
        merge_material(
            decisions,
            workflow_profile,
            "theses_similarity",
            scope="theses_similarity_report_evidence",
            reason="Theses.cz similarity-report evidence is present and needs contextual review before synthesis",
            source_refs=theses_similarity_materiality_refs(round_dir),
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
        refs = [MEDIA_INVENTORY_REL.as_posix()]
        refs.extend(
            str(record.get("path"))
            for record in media_records
            if isinstance(record.get("path"), str) and (round_dir / str(record.get("path"))).is_file()
        )
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
    elif workflow_profile == "supervisor_feedback" and resolved_phase == "final":
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


def build_materiality_next_actions(
    round_dir: Path,
    decisions: list[MaterialityDecision],
    *,
    workflow_profile: str,
) -> list[MaterialityNextAction]:
    material = {decision.role: decision for decision in decisions if decision.material}
    actions: list[MaterialityNextAction] = []
    github = material.get("github_intake")
    if github is not None:
        config = NEXT_ACTION_CONFIG["github_intake"]
        actions.extend(
            _next_action_for_required_artifact(
                round_dir,
                decision=github,
                workflow_profile=workflow_profile,
                required_artifact_path=config["required_artifact_path"],
                command=config["command"],
                skill=config["skill"],
                typed_limitation_scope=config["typed_limitation_scope"],
            )
        )
    quantitative = material.get("quantitative_claims")
    if quantitative is not None:
        config = NEXT_ACTION_CONFIG["quantitative_claims"]
        errors = _quantitative_resolution_errors(round_dir, workflow_profile=workflow_profile)
        if errors and not _has_typed_limitation(
            round_dir,
            "quantitative_claims",
            workflow_profile=workflow_profile,
        ):
            actions.append(
                _make_next_action(
                    round_dir,
                    decision=quantitative,
                    workflow_profile=workflow_profile,
                    required_artifact_path=config["required_artifact_path"],
                    reason=(
                        "Quantitative materiality is active but " "work/quantitative_claims.json is missing or invalid."
                    ),
                    command=config["command"],
                    skill=config["skill"],
                    typed_limitation_scope=config["typed_limitation_scope"],
                    source_refs=list(quantitative.source_refs),
                    limitations=tuple(errors[:5]),
                )
            )
    theses_similarity = material.get("theses_similarity")
    if theses_similarity is not None:
        config = NEXT_ACTION_CONFIG["theses_similarity"]
        state = _theses_similarity_resolution_state(round_dir, workflow_profile=workflow_profile)
        if state.errors and not _has_typed_limitation(
            round_dir,
            "theses_similarity",
            workflow_profile=workflow_profile,
        ):
            required_artifact_path = config["required_artifact_path"]
            command = config["command"]
            skill = config["skill"]
            if state.state == "silent_no_concern_waiting_for_reviewed_synthesis":
                required_artifact_path = SYNTHESIS_ARTIFACT_BY_WORKFLOW.get(
                    workflow_profile, config["required_artifact_path"]
                )
                command = (
                    "Complete the current synthesis artifact and independent review, then register manifest coverage "
                    f"for {THESES_SIMILARITY_ASSESSMENT_REL} with used_findings="
                    f"{THESES_SIMILARITY_SILENT_USED_FINDINGS}."
                )
                skill = (
                    "thesis-supervisor-report-review"
                    if workflow_profile == "supervisor_report"
                    else "thesis-opponent-materials-review"
                )
            actions.append(
                _make_next_action(
                    round_dir,
                    decision=theses_similarity,
                    workflow_profile=workflow_profile,
                    required_artifact_path=required_artifact_path,
                    reason=state.reason,
                    command=command,
                    skill=skill,
                    typed_limitation_scope=config["typed_limitation_scope"],
                    source_refs=list(theses_similarity.source_refs)
                    + [THESES_SIMILARITY_REVIEW_REL, THESES_SIMILARITY_ASSESSMENT_REL],
                    limitations=tuple(state.errors[:5]),
                    state=state.state,
                )
            )
    return actions


def _quantitative_resolution_errors(round_dir: Path, *, workflow_profile: str) -> list[str]:
    errors = validate_structured_evidence_artifact(
        round_dir,
        QUANTITATIVE_CLAIMS_REL,
        require_existing_refs=True,
    )
    if errors:
        return errors
    if workflow_profile != "supervisor_report":
        return []
    stale_reasons = _artifact_stale_reasons(round_dir, QUANTITATIVE_CLAIMS_REL.as_posix())
    if stale_reasons:
        return stale_reasons
    if _reviewed_or_synthesis_covered_artifact_state(
        round_dir,
        QUANTITATIVE_CLAIMS_REL.as_posix(),
        workflow_profile=workflow_profile,
    ):
        return []
    return [
        "Final supervisor-report quantitative materiality requires a current "
        "work/quantitative_claims.json with independent review, downstream synthesis coverage, "
        "or a typed limitation."
    ]


def _theses_similarity_validation_errors(round_dir: Path) -> list[str]:
    if not (round_dir / THESES_SIMILARITY_REVIEW_REL).is_file():
        return []
    errors: list[str] = []
    for rel_path in (
        THESES_SIMILARITY_REPORT_REL,
        THESES_SIMILARITY_EXTRACTED_TEXT_REL,
        THESES_SIMILARITY_INTAKE_REL,
    ):
        if not (round_dir / rel_path).is_file():
            errors.append(f"missing required Theses.cz similarity artifact: {rel_path}")
    if not (round_dir / THESES_SIMILARITY_ASSESSMENT_REL).is_file():
        errors.append(f"{THESES_SIMILARITY_REVIEW_REL}: {THESES_SIMILARITY_ASSESSMENT_REL} is required")
        return errors
    case_id = round_dir.parents[1].name if len(round_dir.parents) > 1 else ""
    errors.extend(
        validate_structured_evidence_artifact(
            round_dir,
            THESES_SIMILARITY_ASSESSMENT_REL,
            case_id=case_id,
            round_id=round_dir.name,
        )
    )
    return errors


@dataclass(frozen=True)
class ResolutionState:
    state: str
    reason: str
    errors: tuple[str, ...] = ()


def _theses_similarity_resolution_state(round_dir: Path, *, workflow_profile: str) -> ResolutionState:
    if _theses_similarity_silent_internal_evidence_satisfied(round_dir, workflow_profile=workflow_profile):
        return ResolutionState(
            state="current_synthesis_covered_artifact",
            reason="Theses.cz similarity evidence is current and covered by reviewed synthesis.",
        )
    if (round_dir / THESES_SIMILARITY_REVIEW_REL).is_file():
        errors = _theses_similarity_validation_errors(round_dir)
        if errors:
            return ResolutionState(
                state="validator_failed",
                reason="Theses.cz similarity evidence is present but validator checks failed.",
                errors=tuple(errors),
            )
        state = _reviewed_or_synthesis_covered_artifact_state(
            round_dir,
            THESES_SIMILARITY_REVIEW_REL,
            workflow_profile=workflow_profile,
        )
        if state is not None:
            return ResolutionState(
                state=(
                    "current_synthesis_covered_artifact"
                    if state == CoverageSatisfiedBy.CURRENT_SYNTHESIS_COVERED_ARTIFACT
                    else "current_reviewed_artifact"
                ),
                reason="Theses.cz similarity review output is current.",
            )
        message = (
            f"{THESES_SIMILARITY_REVIEW_REL} is present but not independently reviewed "
            "or covered by the current reviewed synthesis artifact."
        )
        return ResolutionState(
            state="present_not_synthesis_covered",
            reason=(
                "Theses.cz similarity review output is present but still needs independent review "
                "or synthesis coverage."
            ),
            errors=(message,),
        )
    if (round_dir / THESES_SIMILARITY_ASSESSMENT_REL).is_file():
        assessment, errors = _load_current_theses_similarity_assessment(round_dir)
        if errors:
            return ResolutionState(
                state="validator_failed",
                reason="Theses.cz similarity assessment is present but validator checks failed.",
                errors=tuple(errors),
            )
        if assessment is None:
            message = f"{THESES_SIMILARITY_ASSESSMENT_REL} is missing or invalid."
            return ResolutionState(state="validator_failed", reason=message, errors=(message,))
        if not _theses_similarity_assessment_is_silent_no_concern(assessment):
            message = (
                f"{THESES_SIMILARITY_ASSESSMENT_REL} records non-silent or reviewer-verification "
                "similarity concerns; run thesis-theses-similarity-review or record a typed limitation."
            )
            return ResolutionState(state="present_not_synthesis_covered", reason=message, errors=(message,))
        if workflow_profile not in SILENT_THESES_SIMILARITY_SYNTHESIS_WORKFLOWS:
            message = (
                f"{THESES_SIMILARITY_ASSESSMENT_REL} records no material concern, but "
                f"{workflow_profile} cannot use silent synthesis coverage; run thesis-theses-similarity-review "
                "or record a typed limitation."
            )
            return ResolutionState(state="present_not_synthesis_covered", reason=message, errors=(message,))
        message = (
            f"{THESES_SIMILARITY_ASSESSMENT_REL} records no material concern but is not covered by "
            "the current reviewed synthesis with the silent internal-evidence marker."
        )
        return ResolutionState(
            state="silent_no_concern_waiting_for_reviewed_synthesis",
            reason=(
                "Theses.cz similarity no-concern assessment is present and waiting for reviewed synthesis coverage."
            ),
            errors=(message,),
        )
    message = (
        f"missing {THESES_SIMILARITY_ASSESSMENT_REL} or {THESES_SIMILARITY_REVIEW_REL} for imported "
        "Theses.cz similarity evidence."
    )
    return ResolutionState(state="missing_artifact", reason=message, errors=(message,))


def _theses_similarity_resolution_errors(round_dir: Path, *, workflow_profile: str) -> list[str]:
    return list(_theses_similarity_resolution_state(round_dir, workflow_profile=workflow_profile).errors)


def _next_action_for_required_artifact(
    round_dir: Path,
    *,
    decision: MaterialityDecision,
    workflow_profile: str,
    required_artifact_path: str,
    command: str,
    skill: str,
    typed_limitation_scope: str,
) -> list[MaterialityNextAction]:
    if _has_typed_limitation(
        round_dir,
        typed_limitation_scope,
        workflow_profile=workflow_profile,
    ):
        return []
    path = round_dir / required_artifact_path
    if not path.is_file():
        return [
            _make_next_action(
                round_dir,
                decision=decision,
                workflow_profile=workflow_profile,
                required_artifact_path=required_artifact_path,
                reason=f"Material role {decision.role} is active but {required_artifact_path} is missing.",
                command=command,
                skill=skill,
                typed_limitation_scope=typed_limitation_scope,
                source_refs=list(decision.source_refs),
            )
        ]
    stale_reasons = _artifact_stale_reasons(round_dir, required_artifact_path)
    if stale_reasons:
        return [
            _make_next_action(
                round_dir,
                decision=decision,
                workflow_profile=workflow_profile,
                required_artifact_path=required_artifact_path,
                reason="; ".join(stale_reasons),
                command=command,
                skill=skill,
                typed_limitation_scope=typed_limitation_scope,
                source_refs=list(decision.source_refs) + [required_artifact_path],
                limitations=tuple(stale_reasons),
            )
        ]
    return []


def _make_next_action(
    round_dir: Path,
    *,
    decision: MaterialityDecision,
    workflow_profile: str,
    required_artifact_path: str,
    reason: str,
    command: str,
    skill: str,
    typed_limitation_scope: str,
    source_refs: list[str],
    limitations: tuple[str, ...] = (),
    state: str = "missing_artifact",
) -> MaterialityNextAction:
    safe_refs = [ref for ref in source_refs if source_ref_is_allowed(ref)]
    return MaterialityNextAction(
        role=decision.role,
        workflow_profile=workflow_profile,
        status="unresolved",
        severity="required",
        required_artifact_path=required_artifact_path,
        reason=reason,
        command=command,
        skill=skill,
        source_refs=tuple(sorted(dict.fromkeys(safe_refs))),
        source_sha256=source_hashes_for_refs(round_dir, safe_refs),
        typed_limitation_scope=typed_limitation_scope,
        limitations=limitations,
        state=state,
    )


def _artifact_stale_reasons(round_dir: Path, artifact_path: str) -> list[str]:
    reasons: list[str] = []
    manifest, _ = load_json_object(round_dir / REVIEW_MANIFEST_REL)
    if manifest is not None:
        for collection in ("artifacts", "supporting_work_artifacts"):
            artifacts = manifest.get(collection)
            if not isinstance(artifacts, list):
                continue
            for artifact in artifacts:
                if not isinstance(artifact, dict) or artifact.get("path") != artifact_path:
                    continue
                source_sha256 = artifact.get("source_sha256")
                if isinstance(source_sha256, dict):
                    for ref, recorded_hash in source_sha256.items():
                        if not isinstance(ref, str) or not isinstance(recorded_hash, str):
                            continue
                        if not is_safe_round_relative_path(ref):
                            reasons.append(f"{artifact_path}: manifest source ref is unsafe: {ref}")
                            continue
                        path = round_dir / ref
                        if not path.is_file():
                            reasons.append(f"{artifact_path}: manifest source ref is missing: {ref}")
                        elif sha256_file(path) != recorded_hash:
                            reasons.append(f"{artifact_path}: manifest source hash is stale for {ref}")
                break
    snapshot, _ = load_json_object(round_dir / CURRENT_EVIDENCE_SNAPSHOT_REL)
    if snapshot is not None:
        snapshot_errors = validate_structured_evidence_artifact(
            round_dir,
            CURRENT_EVIDENCE_SNAPSHOT_REL,
            require_existing_refs=False,
        )
        reasons.extend(f"{artifact_path}: current evidence snapshot invalid: {error}" for error in snapshot_errors)
        items = snapshot.get("items")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict) or item.get("path") != artifact_path:
                    continue
                if item.get("status") != "present":
                    reasons.append(f"{artifact_path}: current evidence snapshot status is {item.get('status')}")
                elif item.get("freshness") not in {"current", "not_applicable"}:
                    reasons.append(f"{artifact_path}: current evidence snapshot freshness is {item.get('freshness')}")
                break
    return reasons


def validate_materiality_limitation_item(
    item: dict[str, Any],
    *,
    scope: str | None = None,
    workflow_profile: str | None = None,
    rel_path: str = REVIEW_MANIFEST_REL.as_posix(),
) -> list[str]:
    errors: list[str] = []
    prefix = rel_path
    limitation_type = item.get("type")
    if limitation_type not in MATERIALITY_LIMITATION_TYPES:
        errors.append(
            f"{prefix}: type must be one of {sorted(MATERIALITY_LIMITATION_TYPES)} "
            f"for {MATERIALITY_LIMITATION_TRIGGER}"
        )
    if item.get("trigger") != MATERIALITY_LIMITATION_TRIGGER:
        errors.append(f"{prefix}: trigger must be {MATERIALITY_LIMITATION_TRIGGER}")
    status = item.get("status")
    if status not in MATERIALITY_LIMITATION_STATUSES:
        errors.append(f"{prefix}: status must be one of {sorted(MATERIALITY_LIMITATION_STATUSES)}")
    item_scope = item.get("scope") or item.get("role")
    if item_scope not in NEXT_ACTION_ROLES:
        errors.append(f"{prefix}: scope/role must be one of {sorted(NEXT_ACTION_ROLES)}")
    elif scope is not None and item_scope != scope:
        errors.append(f"{prefix}: scope/role must be {scope}")
    required_for = item.get("required_for")
    if not isinstance(required_for, list) or not required_for:
        errors.append(f"{prefix}: required_for must be a non-empty list")
    else:
        invalid = [value for value in required_for if value not in WORKFLOW_PROFILES and value != "all"]
        if invalid:
            errors.append(f"{prefix}: required_for contains unknown workflow profile: {', '.join(map(str, invalid))}")
        if workflow_profile is not None and workflow_profile not in required_for and "all" not in required_for:
            errors.append(f"{prefix}: required_for must include {workflow_profile} or all")
    for field in ("description", "impact"):
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{prefix}: {field} must be a non-empty string")
    accepted_by = item.get("accepted_by") or item.get("reviewer_role")
    if not isinstance(accepted_by, str) or not accepted_by.strip():
        errors.append(f"{prefix}: accepted_by or reviewer_role must be a non-empty string")
    return errors


def validate_materiality_workflow_limitations(
    limitations: Any,
    *,
    workflow_profile: str | None = None,
    rel_path: str = REVIEW_MANIFEST_REL.as_posix(),
) -> list[str]:
    if limitations is None:
        return []
    if not isinstance(limitations, list):
        return [f"{rel_path}: workflow_limitations must be a list"]
    errors: list[str] = []
    for index, item in enumerate(limitations, start=1):
        if not isinstance(item, dict):
            continue
        item_scope = item.get("scope") or item.get("role")
        is_materiality_limitation = (
            item.get("trigger") == MATERIALITY_LIMITATION_TRIGGER or item_scope in NEXT_ACTION_ROLES
        )
        if not is_materiality_limitation:
            continue
        item_errors = validate_materiality_limitation_item(
            item,
            workflow_profile=workflow_profile,
            rel_path=f"{rel_path}: workflow_limitations item {index}",
        )
        errors.extend(item_errors)
    return errors


def _has_typed_limitation(
    round_dir: Path,
    scope: str,
    *,
    workflow_profile: str | None,
) -> bool:
    manifest, _ = load_json_object(round_dir / REVIEW_MANIFEST_REL)
    if manifest is None:
        return False
    limitations = manifest.get("workflow_limitations")
    if not isinstance(limitations, list):
        return False
    for item in limitations:
        if not isinstance(item, dict):
            continue
        values = {item.get("scope"), item.get("role")}
        if scope in values and not validate_materiality_limitation_item(
            item,
            scope=scope,
            workflow_profile=workflow_profile,
        ):
            return True
    return False


def _artifact_has_current_independent_review(round_dir: Path, artifact_path: str) -> bool:
    manifest, _ = load_json_object(round_dir / REVIEW_MANIFEST_REL)
    if manifest is None:
        return False
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return False
    path = round_dir / artifact_path
    if not path.is_file():
        return False
    current_hash = sha256_file(path)
    for artifact in artifacts:
        if not isinstance(artifact, dict) or artifact.get("path") != artifact_path:
            continue
        if artifact.get("artifact_sha256") not in {None, current_hash}:
            return False
        review = artifact.get("independent_review")
        if not isinstance(review, dict):
            return False
        return review.get("reviewed_hash") == current_hash
    return False


def _manifest_artifacts_by_path(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {}
    for collection in ("artifacts", "supporting_work_artifacts"):
        records = manifest.get(collection)
        if not isinstance(records, list):
            continue
        for artifact in records:
            if isinstance(artifact, dict) and isinstance(artifact.get("path"), str):
                by_path.setdefault(artifact["path"], artifact)
    return by_path


def _artifact_current_hash_matches(round_dir: Path, artifact: dict[str, Any], artifact_path: str) -> str | None:
    path = round_dir / artifact_path
    if not path.is_file():
        return None
    current_hash = sha256_file(path)
    recorded_hash = artifact.get("artifact_sha256")
    if isinstance(recorded_hash, str) and recorded_hash != current_hash:
        return None
    return current_hash


def _synthesis_artifact_review_current(
    round_dir: Path,
    artifacts_by_path: dict[str, dict[str, Any]],
    covered_by_artifact: str,
) -> bool:
    covered = artifacts_by_path.get(covered_by_artifact)
    if covered is None:
        return False
    current_hash = _artifact_current_hash_matches(round_dir, covered, covered_by_artifact)
    if current_hash is None:
        return False
    review = covered.get("independent_review")
    if not isinstance(review, dict):
        return False
    return review.get("status") in REVIEWED_MANIFEST_STATUSES and review.get("reviewed_hash") == current_hash


def _artifact_covered_by_current_synthesis(
    round_dir: Path,
    artifact_path: str,
    *,
    workflow_profile: str,
    required_used_findings: str | None = None,
) -> bool:
    synthesis_path = SYNTHESIS_ARTIFACT_BY_WORKFLOW.get(workflow_profile)
    if synthesis_path is None:
        return False
    manifest, _ = load_json_object(round_dir / REVIEW_MANIFEST_REL)
    if manifest is None:
        return False
    artifacts_by_path = _manifest_artifacts_by_path(manifest)
    artifact = artifacts_by_path.get(artifact_path)
    if artifact is None:
        return False
    current_hash = _artifact_current_hash_matches(round_dir, artifact, artifact_path)
    if current_hash is None:
        return False
    review = artifact.get("independent_review")
    if not isinstance(review, dict):
        return False
    used_findings = str(review.get("used_findings", "")).strip()
    if required_used_findings is not None and used_findings != required_used_findings:
        return False
    if required_used_findings is None and (not used_findings or used_findings == "not_recorded"):
        return False
    if review.get("status") != "not_required":
        return False
    if review.get("covered_by_artifact") != synthesis_path:
        return False
    if review.get("evidence_hash") != current_hash:
        return False
    if artifact.get("review_scope") != "covered_by_synthesis":
        return False
    return _synthesis_artifact_review_current(round_dir, artifacts_by_path, synthesis_path)


def _reviewed_or_synthesis_covered_artifact_state(
    round_dir: Path,
    artifact_path: str,
    *,
    workflow_profile: str,
) -> CoverageSatisfiedBy | None:
    if not _artifact_is_current(round_dir, artifact_path):
        return None
    if _artifact_has_current_independent_review(round_dir, artifact_path):
        return CoverageSatisfiedBy.CURRENT_REVIEWED_ARTIFACT
    if _artifact_covered_by_current_synthesis(
        round_dir,
        artifact_path,
        workflow_profile=workflow_profile,
    ):
        return CoverageSatisfiedBy.CURRENT_SYNTHESIS_COVERED_ARTIFACT
    return None


def _load_current_theses_similarity_assessment(round_dir: Path) -> tuple[dict[str, Any] | None, list[str]]:
    errors = validate_structured_evidence_artifact(
        round_dir,
        THESES_SIMILARITY_ASSESSMENT_REL,
        require_existing_refs=True,
    )
    stale_reasons = _artifact_stale_reasons(round_dir, THESES_SIMILARITY_ASSESSMENT_REL)
    if errors or stale_reasons:
        return None, errors + stale_reasons
    return load_json_object(round_dir / THESES_SIMILARITY_ASSESSMENT_REL)


def _theses_similarity_assessment_is_silent_no_concern(payload: dict[str, Any]) -> bool:
    return theses_similarity_assessment_is_silent_no_concern(payload)


def _theses_similarity_silent_internal_evidence_satisfied(round_dir: Path, *, workflow_profile: str) -> bool:
    return theses_similarity_silent_internal_evidence_satisfied(
        round_dir,
        workflow_profile=workflow_profile,
    )


def _artifact_is_current(round_dir: Path, artifact_path: str) -> bool:
    return (round_dir / artifact_path).is_file() and not _artifact_stale_reasons(round_dir, artifact_path)


def materiality_coverage_payload(
    round_dir: Path,
    decision: MaterialityDecision,
    *,
    workflow_profile: str,
) -> dict[str, Any]:
    if not decision.material:
        return {
            "coverage_required": False,
            "fresh_review_required": False,
            "coverage_satisfied_by": CoverageSatisfiedBy.TYPED_NO_MATERIAL_ISSUE.value,
            "coverage_state": "no_material_issue",
        }

    if decision.role in NEXT_ACTION_ROLES and _has_typed_limitation(
        round_dir,
        decision.role,
        workflow_profile=workflow_profile,
    ):
        return {
            "coverage_required": True,
            "fresh_review_required": False,
            "coverage_satisfied_by": CoverageSatisfiedBy.TYPED_LIMITATION.value,
            "coverage_state": "typed_limitation",
        }

    artifact_path = MATERIALITY_ROLE_ARTIFACTS.get(decision.role)
    if artifact_path and _artifact_is_current(round_dir, artifact_path):
        coverage = _reviewed_or_synthesis_covered_artifact_state(
            round_dir,
            artifact_path,
            workflow_profile=workflow_profile,
        )
        if coverage is None:
            coverage = (
                CoverageSatisfiedBy.NOT_SATISFIED
                if workflow_profile == "supervisor_report"
                and decision.role in {"quantitative_claims", "theses_similarity"}
                else CoverageSatisfiedBy.CURRENT_HANDOFF
            )
        fresh_review_required = coverage == CoverageSatisfiedBy.NOT_SATISFIED
        return {
            "coverage_required": True,
            "fresh_review_required": fresh_review_required,
            "coverage_satisfied_by": coverage.value,
            "coverage_state": coverage.value,
        }

    if decision.role == "theses_similarity" and _theses_similarity_silent_internal_evidence_satisfied(
        round_dir,
        workflow_profile=workflow_profile,
    ):
        return {
            "coverage_required": True,
            "fresh_review_required": False,
            "coverage_satisfied_by": CoverageSatisfiedBy.SILENT_INTERNAL_EVIDENCE.value,
            "coverage_state": "silent_internal_evidence",
        }

    if (
        decision.role == "theses_similarity"
        and workflow_profile in SILENT_THESES_SIMILARITY_SYNTHESIS_WORKFLOWS
        and (round_dir / THESES_SIMILARITY_ASSESSMENT_REL).is_file()
    ):
        state = _theses_similarity_resolution_state(round_dir, workflow_profile=workflow_profile)
        if state.state == "silent_no_concern_waiting_for_reviewed_synthesis":
            return {
                "coverage_required": True,
                "fresh_review_required": False,
                "coverage_satisfied_by": CoverageSatisfiedBy.NOT_SATISFIED.value,
                "coverage_state": "silent_no_concern_waiting_for_reviewed_synthesis",
            }

    coverage = (
        CoverageSatisfiedBy.NOT_SATISFIED
        if decision.role in NEXT_ACTION_ROLES
        else CoverageSatisfiedBy.FRESH_ROLE_REVIEW
    )
    return {
        "coverage_required": True,
        "fresh_review_required": True,
        "coverage_satisfied_by": coverage.value,
        "coverage_state": (
            "fresh_review_required" if coverage == CoverageSatisfiedBy.FRESH_ROLE_REVIEW else "not_satisfied"
        ),
    }


def decision_payload(
    round_dir: Path,
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
    payload["source_sha256"] = source_hashes_for_refs(round_dir, decision.source_refs)
    payload["limitations"] = list(decision.limitations)
    payload.update(materiality_coverage_payload(round_dir, decision, workflow_profile=workflow_profile))
    return payload


def next_action_payload(action: MaterialityNextAction) -> dict[str, Any]:
    payload = asdict(action)
    payload["source_refs"] = list(action.source_refs)
    payload["limitations"] = list(action.limitations)
    return payload


def _without_materiality_timestamps(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    normalized.pop("generated_at", None)
    decisions = normalized.get("decisions")
    if isinstance(decisions, list):
        normalized["decisions"] = [
            (
                {key: item for key, item in decision.items() if key != "generated_at"}
                if isinstance(decision, dict)
                else decision
            )
            for decision in decisions
        ]
    return normalized


def _has_valid_materiality_timestamps(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if not isinstance(value.get("generated_at"), str) or not value["generated_at"]:
        return False
    decisions = value.get("decisions")
    if isinstance(decisions, list):
        for decision in decisions:
            if not isinstance(decision, dict):
                return False
            if not isinstance(decision.get("generated_at"), str) or not decision["generated_at"]:
                return False
    return True


def _write_json_if_materially_changed(path: Path, payload: dict[str, Any]) -> None:
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = None
        if _has_valid_materiality_timestamps(existing) and (
            _without_materiality_timestamps(existing) == _without_materiality_timestamps(payload)
        ):
            return
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_hashes_for_refs(round_dir: Path, refs: tuple[str, ...] | list[str]) -> dict[str, str]:
    return {
        ref: sha256_file(round_dir / ref)
        for ref in refs
        if is_safe_round_relative_path(ref) and (round_dir / ref).is_file()
    }


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
    materiality_dir = round_dir / profile_dir(workflow_profile)
    materiality_dir.mkdir(parents=True, exist_ok=True)
    next_actions = build_materiality_next_actions(
        round_dir,
        decisions,
        workflow_profile=workflow_profile,
    )

    written: list[Path] = []
    index_payload = {
        "schema_version": INDEX_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "workflow_profile": workflow_profile,
        "phase": phase,
        "generated_at": generated_at,
        "producer_role": producer_role,
        "decisions": [
            decision_payload(
                round_dir,
                decision,
                case_id=case_id,
                round_id=round_id,
                workflow_profile=workflow_profile,
                generated_at=generated_at,
                producer_role=producer_role,
            )
            for decision in decisions
        ],
        "next_actions": [next_action_payload(action) for action in next_actions],
    }
    index_path = round_dir / profile_index_rel(workflow_profile)
    _write_json_if_materially_changed(index_path, index_payload)
    written.append(index_path)

    material_roles = {decision.role for decision in decisions if decision.material}
    for role in PACKET_ROLE_FILES:
        rel_path = role_file_for_profile(role, workflow_profile)
        if rel_path is None:
            continue
        path = round_dir / rel_path
        if role not in material_roles:
            if path.is_file():
                path.unlink()
            continue
        decision = next(item for item in decisions if item.role == role)
        payload = decision_payload(
            round_dir,
            decision,
            case_id=case_id,
            round_id=round_id,
            workflow_profile=workflow_profile,
            generated_at=generated_at,
            producer_role=producer_role,
        )
        _write_json_if_materially_changed(path, payload)
        written.append(path)
    return written


def source_ref_is_allowed(value: str) -> bool:
    return is_safe_round_relative_path(value) or value.startswith(ALLOWED_SYNTHETIC_REFS)


def validate_materiality_coverage_fields(
    item: dict[str, Any],
    prefix: str,
    *,
    recommendation: str | None,
) -> list[str]:
    errors: list[str] = []
    coverage_required = item.get("coverage_required")
    fresh_required = item.get("fresh_review_required")
    coverage_value = item.get("coverage_satisfied_by")
    coverage_state = item.get("coverage_state")
    if not isinstance(coverage_required, bool):
        errors.append(f"{prefix}: coverage_required must be a boolean")
    if not isinstance(fresh_required, bool):
        errors.append(f"{prefix}: fresh_review_required must be a boolean")
    coverage: CoverageSatisfiedBy | None = None
    if not isinstance(coverage_value, str):
        errors.append(f"{prefix}: coverage_satisfied_by must be a string")
    else:
        try:
            coverage = CoverageSatisfiedBy(coverage_value)
        except ValueError:
            allowed = [item.value for item in CoverageSatisfiedBy]
            errors.append(f"{prefix}: coverage_satisfied_by must be one of {allowed}")
    if coverage_state not in MATERIALITY_COVERAGE_STATES:
        errors.append(f"{prefix}: coverage_state must be one of {sorted(MATERIALITY_COVERAGE_STATES)}")
    if recommendation in {"material", "not_material"} and isinstance(coverage_required, bool):
        expected_required = recommendation == "material"
        if coverage_required != expected_required:
            errors.append(f"{prefix}: coverage_required must match recommendation={recommendation}")
    if coverage_required is False and fresh_required is True:
        errors.append(f"{prefix}: fresh_review_required must be false when coverage_required is false")
    silent_waiting = (
        fresh_required is False
        and coverage == CoverageSatisfiedBy.NOT_SATISFIED
        and coverage_state == "silent_no_concern_waiting_for_reviewed_synthesis"
    )
    if (
        fresh_required is False
        and coverage is not None
        and not (coverage_satisfies_without_fresh_review(coverage) or silent_waiting)
    ):
        errors.append(f"{prefix}: non-fresh coverage must use a reusable coverage_satisfied_by value")
    if coverage_state == "silent_no_concern_waiting_for_reviewed_synthesis" and not silent_waiting:
        errors.append(
            f"{prefix}: silent_no_concern_waiting_for_reviewed_synthesis must use "
            "fresh_review_required=false and coverage_satisfied_by=not_satisfied"
        )
    if fresh_required is True and coverage in {
        CoverageSatisfiedBy.CURRENT_HANDOFF,
        CoverageSatisfiedBy.CURRENT_REVIEWED_ARTIFACT,
        CoverageSatisfiedBy.CURRENT_SYNTHESIS_COVERED_ARTIFACT,
        CoverageSatisfiedBy.SILENT_INTERNAL_EVIDENCE,
        CoverageSatisfiedBy.TYPED_LIMITATION,
        CoverageSatisfiedBy.TYPED_NO_MATERIAL_ISSUE,
    }:
        errors.append(f"{prefix}: reusable coverage_satisfied_by cannot require a fresh review")
    if coverage is not None:
        expected_state = {
            CoverageSatisfiedBy.CURRENT_HANDOFF: "current_handoff",
            CoverageSatisfiedBy.CURRENT_REVIEWED_ARTIFACT: "current_reviewed_artifact",
            CoverageSatisfiedBy.CURRENT_SYNTHESIS_COVERED_ARTIFACT: "current_synthesis_covered_artifact",
            CoverageSatisfiedBy.SILENT_INTERNAL_EVIDENCE: "silent_internal_evidence",
            CoverageSatisfiedBy.TYPED_LIMITATION: "typed_limitation",
            CoverageSatisfiedBy.TYPED_NO_MATERIAL_ISSUE: "no_material_issue",
            CoverageSatisfiedBy.FRESH_ROLE_REVIEW: "fresh_review_required",
            CoverageSatisfiedBy.NOT_SATISFIED: "not_satisfied",
        }[coverage]
        if not silent_waiting and coverage_state != expected_state:
            errors.append(f"{prefix}: coverage_state must match coverage_satisfied_by={coverage.value}")
    if recommendation == "not_material" and coverage is not None:
        if coverage != CoverageSatisfiedBy.TYPED_NO_MATERIAL_ISSUE:
            errors.append(f"{prefix}: not_material coverage_satisfied_by must be typed_no_material_issue")
        if coverage_state != "no_material_issue":
            errors.append(f"{prefix}: not_material coverage_state must be no_material_issue")
    return errors


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
    if isinstance(role, str):
        if expected_workflow_profile is not None:
            expected_path = role_file_for_profile(role, expected_workflow_profile)
            if expected_path is not None and expected_path.as_posix() != rel_path:
                errors.append(f"{rel_path}: role {role} must be stored at {expected_path.as_posix()}")
        elif role in PACKET_ROLE_FILES and Path(rel_path) not in LEGACY_PACKET_ROLE_FILES.values():
            path = Path(rel_path)
            if len(path.parts) != 4 or path.parts[0] != "work" or path.parts[1] != "review_materiality":
                errors.append(f"{rel_path}: role {role} must be stored under work/review_materiality/<profile>/")
    if payload.get("recommendation") != "material":
        errors.append(f"{rel_path}: packet materiality decision files must have recommendation=material")
    errors.extend(
        validate_materiality_coverage_fields(
            payload,
            rel_path,
            recommendation=payload.get("recommendation") if isinstance(payload.get("recommendation"), str) else None,
        )
    )
    for field in ("scope", "impact", "reason", "generated_at", "producer_role"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{rel_path}: {field} must be a non-empty string")
    source_refs = payload.get("source_refs")
    if not isinstance(source_refs, list) or not source_refs:
        errors.append(f"{rel_path}: source_refs must be a non-empty list")
    elif any(not isinstance(item, str) or not source_ref_is_allowed(item) for item in source_refs):
        errors.append(f"{rel_path}: source_refs must be safe round-relative paths or allowed synthetic refs")
    else:
        errors.extend(_validate_source_sha256_payload(payload.get("source_sha256"), rel_path, source_refs=source_refs))
    limitations = payload.get("limitations")
    if limitations is not None and not isinstance(limitations, list):
        errors.append(f"{rel_path}: limitations must be a list")
    return errors


def validate_materiality_next_actions_payload(
    actions: Any,
    rel_path: str,
    *,
    workflow_profile: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(actions, list):
        return [f"{rel_path}: next_actions must be a list"]
    for index, action in enumerate(actions, start=1):
        prefix = f"{rel_path}: next_actions item {index}"
        if not isinstance(action, dict):
            errors.append(f"{prefix} must be object")
            continue
        role = action.get("role")
        if role not in NEXT_ACTION_ROLES:
            errors.append(f"{prefix}: role must be one of {sorted(NEXT_ACTION_ROLES)}")
        action_profile = action.get("workflow_profile")
        if action_profile not in WORKFLOW_PROFILES:
            errors.append(f"{prefix}: workflow_profile must be one of {sorted(WORKFLOW_PROFILES)}")
        elif workflow_profile is not None and action_profile != workflow_profile:
            errors.append(f"{prefix}: workflow_profile must be {workflow_profile}")
        if action.get("status") not in NEXT_ACTION_STATUSES:
            errors.append(f"{prefix}: status must be one of {sorted(NEXT_ACTION_STATUSES)}")
        if action.get("severity") not in NEXT_ACTION_SEVERITIES:
            errors.append(f"{prefix}: severity must be one of {sorted(NEXT_ACTION_SEVERITIES)}")
        for field in ("required_artifact_path", "reason", "command", "skill", "typed_limitation_scope"):
            value = action.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}: {field} must be a non-empty string")
        required_path = action.get("required_artifact_path")
        if isinstance(required_path, str) and not is_safe_round_relative_path(required_path):
            errors.append(f"{prefix}: required_artifact_path must be relative inside the round")
        source_refs = action.get("source_refs")
        if not isinstance(source_refs, list):
            errors.append(f"{prefix}: source_refs must be a list")
        elif any(not isinstance(item, str) or not source_ref_is_allowed(item) for item in source_refs):
            errors.append(f"{prefix}: source_refs must be safe round-relative paths or allowed synthetic refs")
        source_sha256 = action.get("source_sha256")
        if not isinstance(source_sha256, dict):
            errors.append(f"{prefix}: source_sha256 must be an object")
        else:
            for ref, digest in source_sha256.items():
                if not isinstance(ref, str) or not is_safe_round_relative_path(ref):
                    errors.append(f"{prefix}: source_sha256 keys must be safe round-relative paths")
                if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    errors.append(f"{prefix}: source_sha256 values must be sha256 hex strings")
        limitations = action.get("limitations")
        if not isinstance(limitations, list):
            errors.append(f"{prefix}: limitations must be a list")
        state = action.get("state")
        if state not in NEXT_ACTION_STATES:
            errors.append(f"{prefix}: state has an unknown materiality resolution value")
    return errors


def load_review_materiality_index(
    round_dir: Path,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    workflow_profile: str | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    index_rel = profile_index_rel(workflow_profile) if workflow_profile else INDEX_REL
    payload, load_errors = load_json_object(round_dir / index_rel)
    if payload is None:
        return None, load_errors
    errors: list[str] = []
    if payload.get("schema_version") != INDEX_SCHEMA:
        errors.append(f"{index_rel.as_posix()}: schema_version must be {INDEX_SCHEMA}")
    if case_id is not None and payload.get("case_id") != case_id:
        errors.append(f"{index_rel.as_posix()}: case_id must be {case_id}")
    if round_id is not None and payload.get("round_id") != round_id:
        errors.append(f"{index_rel.as_posix()}: round_id must be {round_id}")
    profile = payload.get("workflow_profile")
    if profile not in WORKFLOW_PROFILES:
        errors.append(f"{index_rel.as_posix()}: workflow_profile must be one of {sorted(WORKFLOW_PROFILES)}")
    elif workflow_profile is not None and profile != workflow_profile:
        errors.append(f"{index_rel.as_posix()}: workflow_profile must be {workflow_profile}")
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        errors.append(f"{index_rel.as_posix()}: decisions must be a list")
    errors.extend(
        validate_materiality_next_actions_payload(
            payload.get("next_actions", []),
            index_rel.as_posix(),
            workflow_profile=workflow_profile,
        )
    )
    return payload, errors


def _validate_source_sha256_payload(
    value: Any,
    prefix: str,
    *,
    source_refs: list[str] | tuple[str, ...] = (),
) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"{prefix}: source_sha256 must be an object"]
    for ref, digest in value.items():
        if not isinstance(ref, str) or not is_safe_round_relative_path(ref):
            errors.append(f"{prefix}: source_sha256 keys must be safe round-relative paths")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append(f"{prefix}: source_sha256 values must be sha256 hex strings")
    for ref in source_refs:
        if (
            isinstance(ref, str)
            and not ref.startswith(ALLOWED_SYNTHETIC_REFS)
            and is_safe_round_relative_path(ref)
            and ref not in value
        ):
            errors.append(f"{prefix}: source_sha256 missing hash for source_ref {ref}")
    return errors


def _index_decisions_from_payload(
    payload: dict[str, Any]
) -> tuple[list[MaterialityDecision], dict[str, dict[str, str]], list[str]]:
    loaded = payload.get("decisions")
    if not isinstance(loaded, list):
        return [], {}, []
    decisions: list[MaterialityDecision] = []
    hashes_by_role: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    for index, item in enumerate(loaded, start=1):
        prefix = f"{INDEX_REL.as_posix()}: decisions item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        role = item.get("role")
        if role not in MATERIALITY_ROLES:
            errors.append(f"{prefix}: role must be one of {list(MATERIALITY_ROLES)}")
            continue
        recommendation = item.get("recommendation")
        if recommendation not in {"material", "not_material"}:
            errors.append(f"{prefix}: recommendation must be material or not_material")
            continue
        errors.extend(
            validate_materiality_coverage_fields(
                item,
                prefix,
                recommendation=str(recommendation),
            )
        )
        fields: dict[str, str] = {}
        for field in ("scope", "impact", "reason"):
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}: {field} must be a non-empty string")
            else:
                fields[field] = value
        source_refs = item.get("source_refs")
        if not isinstance(source_refs, list):
            errors.append(f"{prefix}: source_refs must be a list")
            refs: tuple[str, ...] = ()
        else:
            invalid_refs = [ref for ref in source_refs if not isinstance(ref, str) or not source_ref_is_allowed(ref)]
            if invalid_refs:
                errors.append(f"{prefix}: source_refs must be safe round-relative paths or allowed synthetic refs")
            refs = tuple(ref for ref in source_refs if isinstance(ref, str))
        limitations = item.get("limitations", [])
        if not isinstance(limitations, list):
            errors.append(f"{prefix}: limitations must be a list")
            limitation_values: tuple[str, ...] = ()
        else:
            limitation_values = tuple(str(value) for value in limitations if isinstance(value, str))
        source_hashes = item.get("source_sha256")
        hash_errors = _validate_source_sha256_payload(source_hashes, prefix, source_refs=refs)
        errors.extend(hash_errors)
        if isinstance(source_hashes, dict) and not hash_errors:
            hashes_by_role[str(role)] = {str(ref): str(digest) for ref, digest in source_hashes.items()}
        if {"scope", "impact", "reason"} <= fields.keys():
            decisions.append(
                MaterialityDecision(
                    role=str(role),
                    recommendation=str(recommendation),
                    scope=fields["scope"],
                    impact=fields["impact"],
                    reason=fields["reason"],
                    source_refs=refs,
                    limitations=limitation_values,
                )
            )
    return decisions, hashes_by_role, errors


def _stored_source_hash_stale_reasons(
    round_dir: Path,
    source_hashes: dict[str, str],
    *,
    role: str,
) -> list[str]:
    reasons: list[str] = []
    for ref, recorded_hash in sorted(source_hashes.items()):
        if not is_safe_round_relative_path(ref):
            reasons.append(f"{role}: stored materiality source ref is unsafe: {ref}")
            continue
        path = round_dir / ref
        if not path.is_file():
            reasons.append(f"{role}: stored materiality source ref is missing: {ref}")
        elif sha256_file(path) != recorded_hash:
            reasons.append(f"{role}: stored materiality source hash is stale for {ref}")
    return reasons


def _current_required_next_actions_from_index(
    round_dir: Path,
    payload: dict[str, Any],
    *,
    workflow_profile: str,
) -> tuple[list[MaterialityNextAction], list[str]]:
    decisions, hashes_by_role, errors = _index_decisions_from_payload(payload)
    if errors:
        return [], errors
    actions = build_materiality_next_actions(round_dir, decisions, workflow_profile=workflow_profile)
    action_roles = {action.role for action in actions}
    stored_actions = payload.get("next_actions")
    if isinstance(stored_actions, list):
        current_actions_by_role = {action.role: action for action in actions}
        material_decisions_by_role = {decision.role: decision for decision in decisions if decision.material}
        for index, action in enumerate(stored_actions, start=1):
            if not isinstance(action, dict):
                continue
            if action.get("status") != "unresolved" or action.get("severity") != "required":
                continue
            role = action.get("role")
            if not isinstance(role, str) or role not in material_decisions_by_role:
                continue
            current_action = current_actions_by_role.get(role)
            if current_action is not None:
                stored_state = action.get("state")
                if isinstance(stored_state, str) and stored_state != current_action.state:
                    errors.append(
                        f"{profile_index_rel(workflow_profile).as_posix()}: next_actions item {index} for {role} "
                        f"is stale: stored state={stored_state} current state={current_action.state}"
                    )
                continue
            coverage_state = _coverage_state_for_role(payload, role)
            if coverage_state in {
                "current_reviewed_artifact",
                "current_synthesis_covered_artifact",
                "current_handoff",
                "silent_internal_evidence",
                "typed_limitation",
                "no_material_issue",
            }:
                errors.append(
                    f"{profile_index_rel(workflow_profile).as_posix()}: next_actions item {index} for {role} "
                    f"contradicts decision coverage_state={coverage_state}"
                )
            elif role == "theses_similarity":
                errors.append(
                    f"{profile_index_rel(workflow_profile).as_posix()}: next_actions item {index} for {role} "
                    "is stale; current Theses.cz similarity evidence no longer has an unresolved next action"
                )
    material_decisions = {decision.role: decision for decision in decisions if decision.material}
    for role in sorted(NEXT_ACTION_ROLES):
        if role in action_roles:
            continue
        decision = material_decisions.get(role)
        if decision is None:
            continue
        config = NEXT_ACTION_CONFIG[role]
        if _has_typed_limitation(
            round_dir,
            config["typed_limitation_scope"],
            workflow_profile=workflow_profile,
        ):
            continue
        stale_reasons = _stored_source_hash_stale_reasons(
            round_dir,
            hashes_by_role.get(role, {}),
            role=role,
        )
        if not stale_reasons:
            continue
        actions.append(
            _make_next_action(
                round_dir,
                decision=decision,
                workflow_profile=workflow_profile,
                required_artifact_path=config["required_artifact_path"],
                reason="; ".join(stale_reasons),
                command=config["command"],
                skill=config["skill"],
                typed_limitation_scope=config["typed_limitation_scope"],
                source_refs=list(decision.source_refs),
                limitations=tuple(stale_reasons),
            )
        )
    return actions, errors


def _coverage_state_for_role(payload: dict[str, Any], role: str) -> str | None:
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        return None
    for item in decisions:
        if isinstance(item, dict) and item.get("role") == role:
            value = item.get("coverage_state")
            return value if isinstance(value, str) else None
    return None


def unresolved_required_next_actions(
    round_dir: Path,
    *,
    workflow_profile: str,
    case_id: str | None = None,
    round_id: str | None = None,
    require_index: bool = False,
) -> tuple[list[dict[str, Any]], list[str]]:
    payload, errors = load_review_materiality_index(
        round_dir,
        case_id=case_id,
        round_id=round_id,
        workflow_profile=workflow_profile,
    )
    if payload is None:
        if require_index and not errors:
            index_rel = profile_index_rel(workflow_profile)
            errors = [f"{index_rel.as_posix()}: missing; run check-review-materiality --workflow {workflow_profile}"]
        return [], errors
    current_actions, current_errors = _current_required_next_actions_from_index(
        round_dir,
        payload,
        workflow_profile=workflow_profile,
    )
    errors.extend(current_errors)
    unresolved = [
        next_action_payload(action)
        for action in current_actions
        if action.status == "unresolved" and action.severity == "required"
    ]
    return unresolved, errors


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
