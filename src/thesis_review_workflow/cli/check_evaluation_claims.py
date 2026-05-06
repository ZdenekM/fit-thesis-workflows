"""Flag quantitative thesis-evaluation claims that need semantic review.

This helper is intentionally a reviewer prompt, not a verdict engine. It should
surface quantitative claims that deserve context-aware human/agent attention:
metric meaning, units, baseline, direction, practical scale, reproducibility,
and whether the thesis interprets the result.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from thesis_review_workflow.cases import MissingCurrentRound
from thesis_review_workflow.cases import repo_root as repo_root_core
from thesis_review_workflow.cases import resolve_round as resolve_round_id
from thesis_review_workflow.evaluation_claims import (
    ABSOLUTE_UNIT_RE,
    NUMBER_RE,
    PERCENT_SCALE_RE,
    QuantitativeRow,
    QuantitativeTable,
    ScaleAnchor,
    SourceLine,
    convert_unit,
    find_scale_anchors,
    has_nearby_practical_context,
    is_data_artifact_path,
    is_script_artifact_path,
    metric_direction,
    parse_quantitative_tables,
    script_artifact_from_data_path,
    unit_dimension,
    unit_from_text,
)
from thesis_review_workflow.ids import validate_id as validate_id_core
from thesis_review_workflow.paths import rel_repo

METRIC_RE = re.compile(
    r"\b("
    r"MAE|RMSE|MSE|MAPE|SMAPE|WAPE|F1|AUC|"
    r"accuracy|precision|recall|specificity|sensitivity|SUS|"
    r"score|skore|skóre|success|usability|"
    r"metrik\w*|výsledk\w*|vysledk\w*|evaluac\w*|"
    r"experiment\w*|měřen\w*|meren\w*|testov\w*|"
    r"chyba|chyby|chybov\w*|odchylk\w*|"
    r"úspor\w*|uspor\w*|výnos\w*|vynos\w*|zisk\w*|"
    r"baseline|výchoz\w*|vychoz\w*|predikc\w*|forecast"
    r")\b",
    re.IGNORECASE,
)
MEASURED_VALUE_RE = re.compile(
    r"("
    r"\b\d+(?:[,.]\d+)?\s*(?:ms|s|min|h|fps|Hz|kWh|Wh|kW|W|Kč|Kc|CZK|EUR|MB|GB|%)\b|"
    r"\b(?:time|latency|runtime|throughput|duration|cost|price|fps|samples?|"
    r"čas|cas|doba|rychlost|propustnost|cena|náklad|naklad|vzork\w*)\b"
    r")",
    re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(r"(\[\[[^\]]+\]\]|\\todo\{[^}]*\}|\bTODO\b|\bxxx\b)", re.IGNORECASE)
BASELINE_RE = re.compile(r"\b(bez|no|baseline|without|výchoz\w*|vychoz\w*|control|kontrol\w*)\b", re.IGNORECASE)
CONCLUSION_RE = re.compile(
    r"\b("
    r"nejlep\w*|nejmen\w*|nejniž\w*|nejniz\w*|vyšš\w*|vyss\w*|"
    r"nižš\w*|nizs\w*|lepš\w*|leps\w*|horš\w*|hors\w*|"
    r"prokaz\w*|dokaz\w*|ukazuj\w*|vyplýv\w*|vyplyv\w*|"
    r"závěr\w*|zaver\w*|proto|tedy|therefore|shows|proves|best|worse"
    r")\b",
    re.IGNORECASE,
)


def usage() -> str:
    return "Usage: scripts/check-evaluation-claims CASE_ID [ROUND_ID]"


def die_usage(message: str) -> None:
    print(message, file=sys.stderr)
    print(usage(), file=sys.stderr)
    raise SystemExit(2)


def validate_id(label: str, value: str) -> None:
    try:
        validate_id_core(label, value)
    except ValueError as exc:
        die_usage(f"Invalid {label}. Use only letters, numbers, dot, underscore, and dash.")
        raise AssertionError("unreachable") from exc


def resolve_round(root: Path, case_id: str, round_id: str | None) -> Path:
    case_dir = root / "cases" / case_id
    if not case_dir.is_dir():
        die_usage(f"Case not found: {case_id}")

    try:
        resolved_round = resolve_round_id(case_dir, round_id)
    except MissingCurrentRound as exc:
        die_usage("ROUND_ID not provided and current-round.txt is missing")
        raise AssertionError("unreachable") from exc
    except ValueError as exc:
        die_usage("Invalid round id. Use only letters, numbers, dot, underscore, and dash.")
        raise AssertionError("unreachable") from exc

    round_dir = case_dir / "rounds" / resolved_round
    if not round_dir.is_dir():
        die_usage(f"Round not found: {resolved_round}")
    return round_dir


def thesis_text_paths(round_dir: Path) -> list[Path]:
    extracted_base = round_dir / "extracted"
    if extracted_base.is_dir():
        return sorted(path for path in extracted_base.rglob("*") if path.is_file() and path.suffix.lower() == ".txt")
    return []


def supplemental_source_paths(round_dir: Path, primary_paths: list[Path]) -> list[Path]:
    if not primary_paths or any(path.suffix.lower() == ".tex" for path in primary_paths):
        return []
    source_base = round_dir / "work" / "thesis-source"
    if not source_base.is_dir():
        return []
    return sorted(path for path in source_base.rglob("*") if path.is_file() and path.suffix.lower() == ".tex")


def read_source_lines(paths: list[Path]) -> list[SourceLine]:
    lines: list[SourceLine] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), start=1):
            lines.append(SourceLine(path=path, number=number, text=line))
    return lines


def find_artifacts(round_dir: Path) -> tuple[list[Path], list[Path]]:
    data: list[Path] = []
    scripts: list[Path] = []
    for base_name in ("inputs", "work"):
        base = round_dir / base_name
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if is_data_artifact_path(path):
                data.append(path)
                if script_artifact_from_data_path(path):
                    scripts.append(path)
            elif is_script_artifact_path(path):
                scripts.append(path)
    return sorted(data), sorted(scripts)


def rel(path: Path, root: Path) -> str:
    return rel_repo(root, path)


def print_warning(warnings: list[str], message: str) -> None:
    if message in warnings:
        return
    warnings.append(message)
    print(f"WARNING: {message}")


def compare_to_baseline(
    root: Path,
    table: QuantitativeTable,
    warnings: list[str],
) -> None:
    baseline = next((row for row in table.rows if BASELINE_RE.search(row.label)), None)
    if baseline is None:
        if len(table.rows) > 1:
            print_warning(
                warnings,
                f"metric table at {rel(table.path, root)}:{table.header_number} has no "
                "explicit baseline/comparator label; do not state improvement without a named baseline",
            )
        return
    candidates = [row for row in table.rows if row is not baseline]
    if not candidates:
        return

    for header in table.headers[1:]:
        if header not in baseline.values:
            continue
        direction = metric_direction(header)
        baseline_value = baseline.values[header]
        if direction == "unknown":
            print_warning(
                warnings,
                f"metric direction is unclear for '{header}' at "
                f"{rel(table.path, root)}:{table.header_number}; explicitly state "
                "whether higher or lower values are better",
            )
            continue
        if baseline_value == 0:
            continue

        def improvement(row: QuantitativeRow) -> float:
            value = row.values.get(header)
            if value is None:
                return float("-inf")
            if direction == "lower":
                return 100.0 * (baseline_value - value) / abs(baseline_value)
            return 100.0 * (value - baseline_value) / abs(baseline_value)

        improvements = [(row, improvement(row)) for row in candidates if header in row.values]
        if not improvements:
            continue
        best_row, best_improvement = max(improvements, key=lambda item: item[1])
        if 0 <= best_improvement < 5:
            print_warning(
                warnings,
                f"best improvement for '{header}' over baseline is only "
                f"{best_improvement:.2f}% ({best_row.label}); avoid a strong "
                "general conclusion without sample size, variance, and practical interpretation",
            )
        for row, row_improvement in improvements:
            if row_improvement < 0:
                print_warning(
                    warnings,
                    f"variant '{row.label}' is worse than baseline for '{header}' at "
                    f"{rel(row.path, root)}:{row.number}; explain when or why the method can degrade results",
                )


def check_metric_relationships(
    root: Path,
    table: QuantitativeTable,
    warnings: list[str],
) -> None:
    for row in table.rows:
        mae_header = next((header for header in row.values if re.search(r"\bMAE\b", header, re.IGNORECASE)), None)
        rmse_header = next((header for header in row.values if re.search(r"\bRMSE\b", header, re.IGNORECASE)), None)
        if not mae_header or not rmse_header:
            continue
        mae = row.values[mae_header]
        rmse = row.values[rmse_header]
        if rmse < mae:
            print_warning(
                warnings,
                f"RMSE is lower than MAE at {rel(row.path, root)}:{row.number}; "
                "check formulas, units, or copied values",
            )
        elif mae > 0 and rmse / mae > 1.5:
            print_warning(
                warnings,
                f"RMSE is more than 1.5x MAE at {rel(row.path, root)}:{row.number}; "
                "interpret whether a few large errors dominate the result",
            )


def check_metric_scales(
    root: Path,
    table: QuantitativeTable,
    warnings: list[str],
) -> None:
    for header in table.headers[1:]:
        values = [row.values[header] for row in table.rows if header in row.values]
        if not values:
            continue
        if PERCENT_SCALE_RE.search(header):
            for row in table.rows:
                value = row.values.get(header)
                if value is None:
                    continue
                if value < 0 or value > 100:
                    print_warning(
                        warnings,
                        f"percentage/score-like metric '{header}' has value {value:.3f} "
                        f"at {rel(row.path, root)}:{row.number}; check scale and units",
                    )
        if max(abs(value) for value in values) >= 100 and not ABSOLUTE_UNIT_RE.search(header):
            print_warning(
                warnings,
                f"metric '{header}' has large absolute values but no obvious unit/scale "
                f"at {rel(table.path, root)}:{table.header_number}; state units and practical meaning",
            )


def check_practical_context(
    root: Path,
    lines: list[SourceLine],
    table: QuantitativeTable,
    warnings: list[str],
) -> None:
    absolute_metric = any(ABSOLUTE_UNIT_RE.search(header) for header in table.headers[1:])
    if not absolute_metric:
        return
    if not has_nearby_practical_context(lines, table.path, table.header_number):
        print_warning(
            warnings,
            f"quantitative table at {rel(table.path, root)}:{table.header_number} "
            "uses absolute units but nearby text does not explain practical scale, "
            "baseline, tolerance, capacity, or usability impact",
        )


def check_compatible_scale_anchors(
    root: Path,
    table: QuantitativeTable,
    anchors: list[ScaleAnchor],
    warnings: list[str],
) -> None:
    if not anchors:
        return
    for header in table.headers[1:]:
        metric_unit = unit_from_text(header)
        if metric_unit is None or metric_unit == "%":
            continue
        compatible = [
            anchor
            for anchor in anchors
            if unit_dimension(anchor.unit) == unit_dimension(metric_unit) and anchor.value > 0
        ]
        if not compatible:
            continue
        values = [row.values[header] for row in table.rows if header in row.values]
        if not values:
            continue
        metric_value = max(abs(value) for value in values)
        best_ratio: tuple[float, ScaleAnchor] | None = None
        for anchor in compatible:
            converted = convert_unit(metric_value, metric_unit, anchor.unit)
            if converted is None:
                continue
            ratio = converted / anchor.value
            if best_ratio is None or ratio > best_ratio[0]:
                best_ratio = (ratio, anchor)
        if best_ratio is None:
            continue
        ratio, anchor = best_ratio
        print_warning(
            warnings,
            f"metric '{header}' is {ratio:.0%} of compatible scale anchor "
            f"'{anchor.label}' ({anchor.value:g} {anchor.unit}) from "
            f"{rel(anchor.path, root)}:{anchor.number}; discuss whether that "
            "magnitude is practically acceptable in the thesis context",
        )


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] in {"-h", "--help"}:
        print(usage())
        return 0
    if len(argv) not in (2, 3):
        die_usage("Expected CASE_ID and optional ROUND_ID")
    case_id = argv[1]
    validate_id("case id", case_id)
    round_id = argv[2] if len(argv) == 3 else None
    if round_id is not None:
        validate_id("round id", round_id)

    root = repo_root_core()
    round_dir = resolve_round(root, case_id, round_id)
    source_paths = thesis_text_paths(round_dir)
    lines = read_source_lines(source_paths)
    metric_lines = [item for item in lines if METRIC_RE.search(item.text) or MEASURED_VALUE_RE.search(item.text)]
    warnings: list[str] = []

    if not source_paths:
        print(
            "ERROR: no extracted thesis text was found; evaluation claims were not checked. "
            "Use the submitted PDF as the rendered source of truth and extract it into extracted/ first.",
            file=sys.stderr,
        )
        return 1

    data_artifacts, script_artifacts = find_artifacts(round_dir)
    if metric_lines:
        if not data_artifacts:
            print_warning(
                warnings,
                "metric/evaluation claims are present, but no obvious measurement data, "
                "result export, or analysis notebook was found under inputs/ or work/",
            )
        if not script_artifacts:
            print_warning(
                warnings,
                "metric/evaluation claims are present, but no obvious metric-calculation "
                "script or analysis script was found under inputs/ or work/",
            )

    for item in metric_lines:
        if PLACEHOLDER_RE.search(item.text):
            print_warning(
                warnings,
                f"placeholder appears near an evaluation/metric claim at " f"{rel(item.path, root)}:{item.number}",
            )
        if CONCLUSION_RE.search(item.text) and NUMBER_RE.search(item.text):
            print_warning(
                warnings,
                f"quantitative conclusion at {rel(item.path, root)}:{item.number} "
                "should be checked for baseline, uncertainty, and practical interpretation",
            )
        if MEASURED_VALUE_RE.search(item.text) and NUMBER_RE.search(item.text):
            unit = unit_from_text(item.text)
            if unit is None and not PERCENT_SCALE_RE.search(item.text):
                print_warning(
                    warnings,
                    f"measured-value claim at {rel(item.path, root)}:{item.number} "
                    "should be checked for unit, scale, baseline, and practical interpretation",
                )

    scale_lines = lines + read_source_lines(supplemental_source_paths(round_dir, source_paths))
    scale_anchors = find_scale_anchors(scale_lines)
    tables = parse_quantitative_tables(lines)
    if tables:
        print("Detected quantitative metric tables:")
        for table in tables:
            print(f"- {rel(table.path, root)}:{table.header_number}: " f"{', '.join(table.headers[1:])}")
            for row in table.rows:
                values = ", ".join(f"{header}={value:.3f}" for header, value in row.values.items())
                print(f"  - {rel(row.path, root)}:{row.number}: {row.label} -> {values}")
            compare_to_baseline(root, table, warnings)
            check_metric_relationships(root, table, warnings)
            check_metric_scales(root, table, warnings)
            check_practical_context(root, lines, table, warnings)
            check_compatible_scale_anchors(root, table, scale_anchors, warnings)

    if warnings:
        print(f"Evaluation-claim check completed with {len(warnings)} warning(s).")
    else:
        print("Evaluation-claim check passed.")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
