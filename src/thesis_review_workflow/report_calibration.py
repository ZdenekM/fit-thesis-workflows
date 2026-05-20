"""Structural contract for applied opponent-report calibration basis."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file, validate_common_artifact_fields
from thesis_review_workflow.ids import is_valid_id
from thesis_review_workflow.paths import is_safe_round_relative_path

REPORT_CALIBRATION_BASIS_REL = "work/report_calibration_basis.json"
REPORT_CALIBRATION_BASIS_SCHEMA = "report-calibration-basis-v1"

CALIBRATION_SCOPE = "opponent_report"
WORKFLOW_PROFILES = {"opponent_review", "opponent_materials", "opponent_report_review"}
OPERATOR_SURFACES = {"opponent_materials", "opponent_report_review"}
WAVE_WORKFLOWS = {"opponent_report"}
PREFERENCE_PRIORITIES = {"must", "should", "advisory"}
PREFERENCE_STATUSES = {"applied", "not_applicable", "conflict"}
PUBLIC_REPORT_LENGTHS = {"compact", "standard", "extended"}
GRADES = {"A", "B", "C", "D", "E", "F"}
GRADE_POINT_BANDS = {
    "A": (90, 100),
    "B": (80, 89),
    "C": (70, 79),
    "D": (60, 69),
    "E": (50, 59),
    "F": (0, 49),
}

IS_SELECT_VALUES = {
    "Náročnost zadání": {
        "jednoduché zadání",
        "méně obtížné zadání",
        "průměrně obtížné zadání",
        "obtížnější zadání",
        "značně obtížné zadání",
    },
    "Rozsah splnění požadavků zadání": {
        "zadání nesplněno",
        "zadání splněno pouze částečně",
        "zadání splněno pouze částečně s drobnými výhradami",
        "zadání splněno pouze částečně s vážnějšími výhradami",
        "zadání téměř splněno",
        "zadání téměř splněno s drobnými výhradami",
        "zadání téměř splněno s vážnějšími výhradami",
        "student se odůvodněně odchýlil od zadání",
        "student se odůvodněně odchýlil od zadání s drobnými výhradami",
        "student se odůvodněně odchýlil od zadání s vážnějšími výhradami",
        "zadání splněno",
        "zadání splněno s drobnými výhradami",
        "zadání splněno s vážnějšími výhradami",
        "zadání splněno a práce obsahuje podstatná rozšíření",
    },
    "Rozsah technické zprávy": {
        "nesplňuje minimální požadavky",
        "téměř splňuje minimální požadavky",
        "splňuje pouze minimální požadavky",
        "je v obvyklém rozmezí",
        "přesahuje obvyklé rozmezí",
    },
}

ROUND_SOURCE_PREFIXES = ("inputs/", "extracted/", "notes/", "work/", "outputs/")
OPERATOR_CALIBRATION_EXACT_PATHS = {
    "notes/opponent-report-operator-feedback.md",
    "notes/opponent-report-review-intake.md",
    "work/operation_log.jsonl",
    "work/opponent_report_revision_request.json",
}
RELATED_CALIBRATION_ARTIFACT_PATHS = {
    "work/opponent_calibration_use.json",
    "work/opponent_calibration_advisory.json",
    "work/opponent_report_revision_request.json",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def is_report_calibration_basis_path(rel_path: str) -> bool:
    return rel_path == REPORT_CALIBRATION_BASIS_REL


def validate_report_calibration_artifact(
    round_dir: Path,
    rel_path: Path | str = REPORT_CALIBRATION_BASIS_REL,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
    expected_reviewer_profile_id: str | None = None,
    expected_profile_source_paths: list[str] | None = None,
) -> list[str]:
    rel = rel_path.as_posix() if isinstance(rel_path, Path) else rel_path
    if rel != REPORT_CALIBRATION_BASIS_REL:
        return [f"{rel}: unknown report calibration artifact path"]
    path = round_dir / rel
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{rel}: missing report calibration artifact"]
    except OSError as exc:
        detail = exc.strerror or exc.__class__.__name__
        return [f"{rel}: cannot read report calibration artifact: {detail}"]
    except json.JSONDecodeError as exc:
        return [f"{rel}: invalid JSON: {exc.msg}"]
    if not isinstance(loaded, dict):
        return [f"{rel}: JSON report calibration artifact must be an object"]
    return validate_report_calibration_payload(
        loaded,
        rel,
        round_dir=round_dir,
        case_id=case_id,
        round_id=round_id,
        require_existing_refs=require_existing_refs,
        expected_reviewer_profile_id=expected_reviewer_profile_id,
        expected_profile_source_paths=expected_profile_source_paths,
    )


def validate_report_calibration_payload(
    loaded: dict[str, Any],
    rel_path: str = REPORT_CALIBRATION_BASIS_REL,
    *,
    round_dir: Path | None = None,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
    expected_reviewer_profile_id: str | None = None,
    expected_profile_source_paths: list[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    if rel_path != REPORT_CALIBRATION_BASIS_REL:
        return [f"{rel_path}: unknown report calibration artifact path"]
    validate_common_artifact_fields(
        loaded,
        rel_path,
        REPORT_CALIBRATION_BASIS_SCHEMA,
        case_id,
        round_id,
        errors,
        required_string_fields=(
            "case_id",
            "round_id",
            "generated_at",
            "producer_role",
            "calibration_scope",
            "reviewer_profile_id",
            "workflow_profile",
            "operator_surface",
            "wave_workflow",
        ),
    )
    _require_enum(loaded, "calibration_scope", {CALIBRATION_SCOPE}, rel_path, errors)
    _require_enum(loaded, "workflow_profile", WORKFLOW_PROFILES, rel_path, errors)
    _require_enum(loaded, "operator_surface", OPERATOR_SURFACES, rel_path, errors)
    _require_enum(loaded, "wave_workflow", WAVE_WORKFLOWS, rel_path, errors)
    _require_id(loaded, "reviewer_profile_id", rel_path, errors)

    _validate_round_refs(loaded.get("source_refs"), f"{rel_path}: source_refs", round_dir, require_existing_refs, errors)
    _validate_profile_sources(loaded.get("profile_sources"), rel_path, round_dir, require_existing_refs, errors)
    _validate_expected_profile_sources(
        loaded,
        rel_path,
        expected_reviewer_profile_id=expected_reviewer_profile_id,
        expected_profile_source_paths=expected_profile_source_paths,
        errors=errors,
    )
    _validate_operator_sources(
        loaded.get("operator_calibration_sources"),
        rel_path,
        round_dir,
        require_existing_refs,
        errors,
    )
    _validate_related_artifacts(
        loaded.get("related_calibration_artifacts"),
        rel_path,
        round_dir,
        require_existing_refs,
        errors,
    )
    _validate_reviewer_profile_binding(loaded, rel_path, errors)
    _validate_preferences(loaded.get("applied_preferences"), rel_path, _declared_source_keys(loaded), errors)
    _validate_expected_controls(loaded.get("expected_report_controls"), rel_path, errors)
    _validate_string_list(loaded.get("limitations"), f"{rel_path}: limitations", errors)
    return errors


def report_calibration_source_refs(payload: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    source_refs = payload.get("source_refs")
    if isinstance(source_refs, list):
        refs.extend(ref for ref in source_refs if isinstance(ref, str))
    for field in ("operator_calibration_sources", "related_calibration_artifacts"):
        values = payload.get(field)
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                refs.append(item["path"])
    return sorted(dict.fromkeys(refs))


def profile_source_paths(payload: dict[str, Any]) -> list[str]:
    values = payload.get("profile_sources")
    if not isinstance(values, list):
        return []
    return sorted(
        {
            item["path"]
            for item in values
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
    )


def _validate_profile_sources(
    values: Any,
    rel_path: str,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    sources = _require_nonempty_list_value(values, f"{rel_path}: profile_sources", errors)
    if not isinstance(sources, list):
        return
    repo_root = _repo_root_for_round(round_dir)
    for index, item in enumerate(sources, start=1):
        prefix = f"{rel_path}: profile_sources item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        path = item.get("path")
        if not isinstance(path, str) or not path:
            errors.append(f"{prefix}: path must be non-empty str")
        elif not _is_allowed_profile_path(path):
            errors.append(f"{prefix}: path must be profiles/default.md or profiles/local/<profile-id>.md")
        _require_sha(item, "sha256", prefix, errors)
        _validate_string_list(item.get("sections_used"), f"{prefix}: sections_used", errors, require_nonempty=True)
        if (
            isinstance(path, str)
            and _is_allowed_profile_path(path)
            and repo_root is not None
            and isinstance(item.get("sha256"), str)
            and SHA256_RE.fullmatch(item["sha256"])
        ):
            _validate_repo_file_hash(
                repo_root,
                path,
                item["sha256"],
                f"{prefix}: sha256",
                require_existing_refs,
                errors,
            )


def _validate_operator_sources(
    values: Any,
    rel_path: str,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    sources = _require_list_value(values, f"{rel_path}: operator_calibration_sources", errors)
    if not isinstance(sources, list):
        return
    for index, item in enumerate(sources, start=1):
        prefix = f"{rel_path}: operator_calibration_sources item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        path = item.get("path")
        if not isinstance(path, str) or not path:
            errors.append(f"{prefix}: path must be non-empty str")
        elif not _is_allowed_operator_source(path):
            errors.append(f"{prefix}: path is not a registered operator calibration source")
        _require_sha(item, "sha256", prefix, errors)
        _require_nonempty_string(item, "purpose", prefix, errors)
        if isinstance(path, str) and _is_allowed_operator_source(path):
            _validate_round_file_hash(round_dir, path, item.get("sha256"), f"{prefix}: sha256", require_existing_refs, errors)


def _validate_related_artifacts(
    values: Any,
    rel_path: str,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    artifacts = _require_list_value(values, f"{rel_path}: related_calibration_artifacts", errors)
    if not isinstance(artifacts, list):
        return
    for index, item in enumerate(artifacts, start=1):
        prefix = f"{rel_path}: related_calibration_artifacts item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        path = item.get("path")
        if not isinstance(path, str) or not path:
            errors.append(f"{prefix}: path must be non-empty str")
        elif path not in RELATED_CALIBRATION_ARTIFACT_PATHS:
            errors.append(f"{prefix}: path is not a supported related calibration artifact")
        _require_sha(item, "sha256", prefix, errors)
        _require_nonempty_string(item, "relationship", prefix, errors)
        if isinstance(path, str) and path in RELATED_CALIBRATION_ARTIFACT_PATHS:
            _validate_round_file_hash(round_dir, path, item.get("sha256"), f"{prefix}: sha256", require_existing_refs, errors)


def _declared_source_keys(loaded: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    profile_sources = loaded.get("profile_sources")
    if isinstance(profile_sources, list):
        for item in profile_sources:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                keys.add(f"profile:{item['path']}")
    for field, namespace in (
        ("operator_calibration_sources", "operator"),
        ("related_calibration_artifacts", "related"),
    ):
        values = loaded.get(field)
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                keys.add(f"{namespace}:{item['path']}")
    return keys


def _validate_reviewer_profile_binding(loaded: dict[str, Any], rel_path: str, errors: list[str]) -> None:
    reviewer_profile_id = loaded.get("reviewer_profile_id")
    if not isinstance(reviewer_profile_id, str) or not is_valid_id(reviewer_profile_id):
        return
    profile_paths = set(profile_source_paths(loaded))
    if reviewer_profile_id == "default":
        expected = {"profiles/default.md", "profiles/local/default.md"}
    else:
        expected = {f"profiles/local/{reviewer_profile_id}.md"}
    if not profile_paths.intersection(expected):
        choices = ", ".join(sorted(expected))
        errors.append(f"{rel_path}: profile_sources must include reviewer_profile_id source: {choices}")


def _validate_expected_profile_sources(
    loaded: dict[str, Any],
    rel_path: str,
    *,
    expected_reviewer_profile_id: str | None,
    expected_profile_source_paths: list[str] | None,
    errors: list[str],
) -> None:
    if expected_reviewer_profile_id is not None and loaded.get("reviewer_profile_id") != expected_reviewer_profile_id:
        errors.append(f"{rel_path}: reviewer_profile_id does not match case Reviewer profile")
    if expected_profile_source_paths is None:
        return
    actual = set(profile_source_paths(loaded))
    expected = set(expected_profile_source_paths)
    missing = sorted(expected.difference(actual))
    extra = sorted(actual.difference(expected))
    for path in missing:
        errors.append(f"{rel_path}: profile_sources missing effective reviewer profile source {path}")
    for path in extra:
        errors.append(f"{rel_path}: profile_sources includes non-effective reviewer profile source {path}")


def _validate_preferences(values: Any, rel_path: str, declared_source_keys: set[str], errors: list[str]) -> None:
    preferences = _require_nonempty_list_value(values, f"{rel_path}: applied_preferences", errors)
    if not isinstance(preferences, list):
        return
    seen: set[str] = set()
    for index, item in enumerate(preferences, start=1):
        prefix = f"{rel_path}: applied_preferences item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        preference_id = item.get("preference_id")
        if not isinstance(preference_id, str) or not preference_id:
            errors.append(f"{prefix}: preference_id must be non-empty str")
        elif not is_valid_id(preference_id):
            errors.append(f"{prefix}: preference_id contains unsupported characters")
        elif preference_id in seen:
            errors.append(f"{prefix}: duplicate preference_id {preference_id}")
        else:
            seen.add(preference_id)
        _validate_string_list(item.get("source_keys"), f"{prefix}: source_keys", errors, require_nonempty=True)
        _validate_preference_source_keys(
            item.get("source_keys"),
            f"{prefix}: source_keys",
            declared_source_keys,
            errors,
        )
        _validate_string_list(item.get("applies_to"), f"{prefix}: applies_to", errors, require_nonempty=True)
        _require_nonempty_string(item, "instruction", prefix, errors)
        _require_enum(item, "priority", PREFERENCE_PRIORITIES, prefix, errors)
        _require_enum(item, "status", PREFERENCE_STATUSES, prefix, errors)
        _require_nonempty_string(item, "decision_reason", prefix, errors)


def _validate_expected_controls(value: Any, rel_path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{rel_path}: expected_report_controls must be object")
        return
    known_keys = {
        "is_select_values",
        "overall_grade",
        "overall_points_interval",
        "defense_question_count",
        "public_report_length",
        "private_comment_required",
    }
    unknown = sorted(set(value).difference(known_keys))
    for key in unknown:
        errors.append(f"{rel_path}: expected_report_controls has unknown key: {key}")
    if not any(key in value for key in known_keys):
        errors.append(f"{rel_path}: expected_report_controls must contain at least one known control")
    is_select_values = value.get("is_select_values")
    if is_select_values is not None:
        if not isinstance(is_select_values, dict):
            errors.append(f"{rel_path}: expected_report_controls.is_select_values must be object")
        else:
            for field, selection in is_select_values.items():
                if field not in IS_SELECT_VALUES:
                    errors.append(f"{rel_path}: expected_report_controls.is_select_values has unknown IS field: {field}")
                    continue
                if selection not in IS_SELECT_VALUES[field]:
                    errors.append(
                        f"{rel_path}: expected_report_controls.is_select_values[{field!r}] has unsupported value"
                    )
    grade = value.get("overall_grade")
    if grade is not None and grade not in GRADES:
        errors.append(f"{rel_path}: expected_report_controls.overall_grade must be one of: {', '.join(sorted(GRADES))}")
    interval = value.get("overall_points_interval")
    parsed_interval: tuple[int, int] | None = None
    if interval is not None:
        if not (
            isinstance(interval, list)
            and len(interval) == 2
            and all(isinstance(item, int) and not isinstance(item, bool) for item in interval)
        ):
            errors.append(f"{rel_path}: expected_report_controls.overall_points_interval must be [min, max]")
        elif interval[0] < 0 or interval[1] > 100 or interval[0] > interval[1]:
            errors.append(f"{rel_path}: expected_report_controls.overall_points_interval must stay within 0-100")
        else:
            parsed_interval = (interval[0], interval[1])
    if grade in GRADE_POINT_BANDS and parsed_interval is not None:
        band_min, band_max = GRADE_POINT_BANDS[grade]
        interval_min, interval_max = parsed_interval
        if interval_max < band_min or interval_min > band_max:
            errors.append(
                f"{rel_path}: expected_report_controls.overall_points_interval does not overlap grade {grade} band"
            )
    question_count = value.get("defense_question_count")
    if question_count is not None:
        if not isinstance(question_count, dict):
            errors.append(f"{rel_path}: expected_report_controls.defense_question_count must be object")
        else:
            minimum = question_count.get("min")
            maximum = question_count.get("max")
            if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 0:
                errors.append(f"{rel_path}: expected_report_controls.defense_question_count.min must be non-negative int")
            if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 0:
                errors.append(f"{rel_path}: expected_report_controls.defense_question_count.max must be non-negative int")
            if (
                isinstance(minimum, int)
                and not isinstance(minimum, bool)
                and isinstance(maximum, int)
                and not isinstance(maximum, bool)
            ):
                if minimum > maximum:
                    errors.append(f"{rel_path}: expected_report_controls.defense_question_count min cannot exceed max")
    length = value.get("public_report_length")
    if length is not None and length not in PUBLIC_REPORT_LENGTHS:
        errors.append(
            f"{rel_path}: expected_report_controls.public_report_length must be one of: "
            f"{', '.join(sorted(PUBLIC_REPORT_LENGTHS))}"
        )
    private_comment_required = value.get("private_comment_required")
    if private_comment_required is not None and not isinstance(private_comment_required, bool):
        errors.append(f"{rel_path}: expected_report_controls.private_comment_required must be bool")


def _repo_root_for_round(round_dir: Path | None) -> Path | None:
    if round_dir is None:
        return None
    candidates = [round_dir, *round_dir.parents]
    for candidate in candidates:
        if (candidate / "profiles").is_dir() and (candidate / "src" / "thesis_review_workflow").is_dir():
            return candidate
    if len(round_dir.parents) >= 4:
        candidate = round_dir.parents[3]
        if (candidate / "profiles").is_dir():
            return candidate
    return None


def _is_allowed_profile_path(value: str) -> bool:
    if not is_safe_round_relative_path(value):
        return False
    if value == "profiles/default.md":
        return True
    if not value.startswith("profiles/local/") or not value.endswith(".md"):
        return False
    profile_id = value.removeprefix("profiles/local/").removesuffix(".md")
    return "/" not in profile_id and is_valid_id(profile_id)


def _is_allowed_operator_source(value: str) -> bool:
    if not is_safe_round_relative_path(value):
        return False
    if value in OPERATOR_CALIBRATION_EXACT_PATHS:
        return True
    if not value.startswith("work/review_deltas/") or not value.endswith(".json"):
        return False
    name = value.removeprefix("work/review_deltas/")
    return "/" not in name and bool(name.removesuffix(".json"))


def _is_allowed_round_ref(value: str) -> bool:
    return is_safe_round_relative_path(value) and value.startswith(ROUND_SOURCE_PREFIXES)


def _validate_round_refs(
    values: Any,
    label: str,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    refs = _require_list_value(values, label, errors)
    if not isinstance(refs, list):
        return
    for index, ref in enumerate(refs, start=1):
        _validate_round_ref(ref, f"{label} item {index}", round_dir, require_existing_refs, errors)


def _validate_round_ref(
    value: Any,
    label: str,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label}: ref must be non-empty str")
        return
    if not _is_allowed_round_ref(value):
        errors.append(f"{label}: ref must be relative under inputs/, extracted/, notes/, work/, or outputs/")
        return
    if require_existing_refs and round_dir is not None and not (round_dir / value).exists():
        errors.append(f"{label}: ref does not exist: {value}")


def _validate_preference_source_keys(
    values: Any,
    label: str,
    declared_source_keys: set[str],
    errors: list[str],
) -> None:
    if not isinstance(values, list):
        return
    for index, value in enumerate(values, start=1):
        if not isinstance(value, str):
            continue
        if ":" not in value:
            errors.append(f"{label} item {index}: source key must include a namespace prefix")
            continue
        namespace, path = value.split(":", 1)
        if namespace == "profile":
            if not _is_allowed_profile_path(path):
                errors.append(f"{label} item {index}: profile source key has unsupported path")
        elif namespace in {"operator", "related"}:
            if not _is_allowed_round_ref(path):
                errors.append(f"{label} item {index}: {namespace} source key has unsupported round path")
        else:
            errors.append(f"{label} item {index}: source key namespace must be profile, operator, or related")
            continue
        if value not in declared_source_keys:
            errors.append(f"{label} item {index}: source key is not declared in hashed calibration sources")


def _validate_round_file_hash(
    round_dir: Path | None,
    rel_path: str,
    digest: Any,
    label: str,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        return
    if round_dir is None:
        return
    path = round_dir / rel_path
    if not path.is_file():
        if require_existing_refs:
            errors.append(f"{label}: referenced file is missing: {rel_path}")
        return
    if sha256_file(path) != digest:
        errors.append(f"{label}: hash is stale for {rel_path}")


def _validate_repo_file_hash(
    repo_root: Path,
    rel_path: str,
    digest: str,
    label: str,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    path = repo_root / rel_path
    if not path.is_file():
        if require_existing_refs:
            errors.append(f"{label}: referenced profile file is missing: {rel_path}")
        return
    if sha256_file(path) != digest:
        errors.append(f"{label}: hash is stale for {rel_path}")


def _require_nonempty_string(value: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    if not isinstance(value.get(field), str) or not value[field]:
        errors.append(f"{prefix}: {field} must be non-empty str")


def _require_id(value: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    loaded = value.get(field)
    if not isinstance(loaded, str) or not loaded:
        errors.append(f"{prefix}: {field} must be non-empty str")
    elif not is_valid_id(loaded):
        errors.append(f"{prefix}: {field} contains unsupported characters")


def _require_enum(value: dict[str, Any], field: str, allowed: set[str], prefix: str, errors: list[str]) -> None:
    loaded = value.get(field)
    if loaded not in allowed:
        errors.append(f"{prefix}: {field} must be one of: {', '.join(sorted(allowed))}")


def _require_sha(value: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    loaded = value.get(field)
    if not isinstance(loaded, str) or not SHA256_RE.fullmatch(loaded):
        errors.append(f"{prefix}: {field} must be a 64-character hex string")


def _require_list_value(value: Any, label: str, errors: list[str]) -> Any:
    if not isinstance(value, list):
        errors.append(f"{label} must be list")
    return value


def _require_nonempty_list_value(value: Any, label: str, errors: list[str]) -> Any:
    loaded = _require_list_value(value, label, errors)
    if isinstance(loaded, list) and not loaded:
        errors.append(f"{label} must not be empty")
    return loaded


def _validate_string_list(value: Any, label: str, errors: list[str], *, require_nonempty: bool = False) -> None:
    if not isinstance(value, list):
        errors.append(f"{label} must be list")
        return
    if require_nonempty and not value:
        errors.append(f"{label} must not be empty")
    for index, item in enumerate(value, start=1):
        if not isinstance(item, str) or not item:
            errors.append(f"{label} item {index}: value must be non-empty str")
