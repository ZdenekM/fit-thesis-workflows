"""Flag quantitative thesis-evaluation claims that need semantic review.

This helper is intentionally a reviewer prompt, not a verdict engine. It should
surface quantitative claims that deserve context-aware human/agent attention:
metric meaning, units, baseline, direction, practical scale, reproducibility,
and whether the thesis interprets the result.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from thesis_review_workflow.paths import rel_repo

ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
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
TABLE_METRIC_RE = re.compile(
    r"\b("
    r"MAE|RMSE|MSE|MAPE|SMAPE|WAPE|F1|AUC|"
    r"accuracy|precision|recall|specificity|sensitivity|SUS|"
    r"score|skore|skóre|success|usability|"
    r"metrik\w*|metric\w*|výsledk\w*|vysledk\w*|"
    r"chyba|chyby|chybov\w*|odchylk\w*|"
    r"úspor\w*|uspor\w*|výnos\w*|vynos\w*|zisk\w*|"
    r"latenc\w*|latency|čas|cas|time|doba|cost|náklad\w*|naklad\w*|"
    r"spotřeb\w*|spotreb\w*"
    r")\b",
    re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(r"(\[\[[^\]]+\]\]|\\todo\{[^}]*\}|\bTODO\b|\bxxx\b)", re.IGNORECASE)
NUMBER_RE = re.compile(r"[-+]?\d+(?:[,.]\d+)?")
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
PRACTICAL_CONTEXT_RE = re.compile(
    r"\b("
    r"praxi|prakt\w*|použit\w*|pouzit\w*|dopad\w*|znamen\w*|"
    r"limit\w*|mez\w*|toler\w*|threshold|kapacit\w*|škál\w*|skal\w*|"
    r"normaliz\w*|relativ\w*|baseline|výchoz\w*|vychoz\w*|"
    r"varianc\w*|rozptyl\w*|směrodat\w*|smerodat\w*|interval\w*"
    r")\b",
    re.IGNORECASE,
)
LOWER_IS_BETTER_RE = re.compile(
    r"\b("
    r"MAE|RMSE|MSE|MAPE|SMAPE|WAPE|error|chyba|chybov\w*|odchyl\w*|"
    r"loss|ztrát\w*|ztrat\w*|latenc\w*|latency|čas|cas|time|"
    r"doba|cost|náklad\w*|naklad\w*|spotřeb\w*|spotreb\w*"
    r")\b",
    re.IGNORECASE,
)
HIGHER_IS_BETTER_RE = re.compile(
    r"\b("
    r"accuracy|precision|recall|specificity|sensitivity|F1|AUC|SUS|"
    r"score|skore|skóre|success|úspěš\w*|uspes\w*|"
    r"úspor\w*|uspor\w*|výnos\w*|vynos\w*|zisk\w*|profit|revenue|"
    r"coverage|pokryt\w*"
    r")\b",
    re.IGNORECASE,
)
PERCENT_SCALE_RE = re.compile(
    r"%|percent|procent|accuracy|precision|recall|specificity|sensitivity|F1|AUC|success|úspěš|uspes", re.IGNORECASE
)
ABSOLUTE_UNIT_RE = re.compile(r"\[(?:W|kW|Wh|kWh|ms|s|min|h|Kč|CZK|EUR|MB|GB|%)\]|\\si\{|\\mathrm\{", re.IGNORECASE)
SCALE_ANCHOR_RE = re.compile(
    r"\b("
    r"kapacit\w*|capacity|peak|špič\w*|spic\w*|"
    r"maximum|max|limit\w*|rozsah\w*|range|installed|instalovan\w*|"
    r"velikost\w*|size"
    r")\b",
    re.IGNORECASE,
)
UNIT_TOKEN_RE = re.compile(
    r"(?<![0-9A-Za-zÀ-ž_])("
    r"kW\s*_?\s*p|kWp|kwp|kWh|MWh|Wh|kW|MW|W|ms|min|s|h|Kč|Kc|CZK|EUR|MB|GB|%"
    r")(?![0-9A-Za-zÀ-ž_])",
    re.IGNORECASE,
)

DATA_EXTENSIONS = {
    ".csv",
    ".tsv",
    ".xlsx",
    ".ods",
    ".parquet",
    ".feather",
    ".ipynb",
    ".json",
    ".jsonl",
}
NOTEBOOK_EXTENSIONS = {".ipynb"}
SCRIPT_EXTENSIONS = {".py", ".r", ".R", ".jl", ".m", ".sql"}
DATA_NAME_RE = re.compile(
    r"(metric|metrik|eval|experiment|mae|rmse|result|vysled|" r"measure|meren|měřen|export|dataset|data)",
    re.IGNORECASE,
)
SCRIPT_NAME_RE = re.compile(
    r"(metric|metrik|eval|experiment|mae|rmse|plot|graf|analysis|analyz|measure|meren|měřen|result|vysled)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SourceLine:
    path: Path
    number: int
    text: str


@dataclass(frozen=True)
class QuantitativeRow:
    path: Path
    number: int
    label: str
    values: dict[str, float]


@dataclass(frozen=True)
class QuantitativeTable:
    path: Path
    header_number: int
    headers: list[str]
    rows: list[QuantitativeRow]


@dataclass(frozen=True)
class ScaleAnchor:
    path: Path
    number: int
    label: str
    value: float
    unit: str


def usage() -> str:
    return "Usage: scripts/check-evaluation-claims CASE_ID [ROUND_ID]"


def repo_root() -> Path:
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
    return Path(output.strip())


def die_usage(message: str) -> None:
    print(message, file=sys.stderr)
    print(usage(), file=sys.stderr)
    raise SystemExit(2)


def validate_id(label: str, value: str) -> None:
    if not ID_RE.fullmatch(value):
        die_usage(f"Invalid {label}. Use only letters, numbers, dot, underscore, and dash.")


def resolve_round(root: Path, case_id: str, round_id: str | None) -> Path:
    case_dir = root / "cases" / case_id
    if not case_dir.is_dir():
        die_usage(f"Case not found: {case_id}")

    if round_id is None:
        current_round = case_dir / "current-round.txt"
        if not current_round.is_file():
            die_usage("ROUND_ID not provided and current-round.txt is missing")
        round_id = current_round.read_text(encoding="utf-8").strip()

    validate_id("round id", round_id)
    round_dir = case_dir / "rounds" / round_id
    if not round_dir.is_dir():
        die_usage(f"Round not found: {round_id}")
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
            suffix = path.suffix
            if suffix in DATA_EXTENSIONS:
                if suffix in {".json", ".jsonl"} and not DATA_NAME_RE.search(path.name):
                    continue
                data.append(path)
                if suffix in NOTEBOOK_EXTENSIONS and SCRIPT_NAME_RE.search(path.name):
                    scripts.append(path)
            elif suffix in SCRIPT_EXTENSIONS and SCRIPT_NAME_RE.search(path.name):
                scripts.append(path)
    return sorted(data), sorted(scripts)


def parse_float(raw: str) -> float:
    return float(raw.replace(",", "."))


def normalize_unit(raw: str) -> str | None:
    text = clean_cell(raw).lower()
    text = text.replace("𝑘", "k").replace("𝑤", "w")
    text = re.sub(r"\s+", "", text)
    text = text.replace("_p", "p")
    if "kwh" in text:
        return "kwh"
    if "mwh" in text:
        return "mwh"
    if re.search(r"(?<!k)wh", text):
        return "wh"
    if "kwp" in text or "kw" in text:
        return "kw"
    if "mw" in text:
        return "mw"
    if re.search(r"(?<!k)(?<!m)w", text):
        return "w"
    if "ms" in text:
        return "ms"
    if "min" in text:
        return "min"
    if re.search(r"\bs\b", text) or text == "s":
        return "s"
    if re.search(r"\bh\b", text) or text == "h":
        return "h"
    if "kč" in text or "kc" in text or "czk" in text:
        return "czk"
    if "eur" in text:
        return "eur"
    if "gb" in text:
        return "gb"
    if "mb" in text:
        return "mb"
    if "%" in text:
        return "%"
    return None


def unit_from_text(text: str) -> str | None:
    bracket = re.search(r"\[([^\]]+)\]", text)
    if bracket:
        unit = normalize_unit(bracket.group(1))
        if unit:
            return unit
    match = UNIT_TOKEN_RE.search(text)
    if not match:
        return None
    return normalize_unit(match.group(0))


def unit_dimension(unit: str) -> str:
    if unit in {"w", "kw", "mw"}:
        return "power"
    if unit in {"wh", "kwh", "mwh"}:
        return "energy"
    if unit in {"ms", "s", "min", "h"}:
        return "time"
    if unit in {"czk", "eur"}:
        return "money"
    if unit in {"mb", "gb"}:
        return "data"
    return unit


def convert_unit(value: float, from_unit: str, to_unit: str) -> float | None:
    if unit_dimension(from_unit) != unit_dimension(to_unit):
        return None
    base_factors = {
        "w": 1.0,
        "kw": 1000.0,
        "mw": 1_000_000.0,
        "wh": 1.0,
        "kwh": 1000.0,
        "mwh": 1_000_000.0,
        "ms": 0.001,
        "s": 1.0,
        "min": 60.0,
        "h": 3600.0,
        "czk": 1.0,
        "eur": 1.0,
        "mb": 1.0,
        "gb": 1024.0,
        "%": 1.0,
    }
    from_factor = base_factors.get(from_unit)
    to_factor = base_factors.get(to_unit)
    if from_factor is None or to_factor is None:
        return None
    return value * from_factor / to_factor


def clean_cell(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"\\\\\s*$", "", text)
    text = re.sub(r"\\(?:textbf|emph|textit)\{([^{}]*)\}", r"\1", text)
    text = text.replace("$", "")
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", "", text)
    return re.sub(r"\s+", " ", text).strip()


def split_table_cells(text: str) -> list[str]:
    stripped = text.strip()
    if re.search(r"^\s*\\(?:hline|cline|toprule|midrule|bottomrule|end|caption|label)", stripped):
        return []
    if "&" in text:
        return [clean_cell(part) for part in stripped.split("&")]
    if re.search(r"\S\s{2,}\S", stripped):
        return [clean_cell(part) for part in re.split(r"\s{2,}", stripped) if part.strip()]
    return []


def metric_direction(header: str) -> str:
    lower = bool(LOWER_IS_BETTER_RE.search(header))
    higher = bool(HIGHER_IS_BETTER_RE.search(header))
    if lower and not higher:
        return "lower"
    if higher and not lower:
        return "higher"
    return "unknown"


def parse_value_cell(cell: str) -> float | None:
    match = NUMBER_RE.search(cell)
    if not match:
        return None
    try:
        return parse_float(match.group(0))
    except ValueError:
        return None


def parse_quantitative_tables(lines: list[SourceLine]) -> list[QuantitativeTable]:
    tables: list[QuantitativeTable] = []
    for index, item in enumerate(lines):
        headers = split_table_cells(item.text)
        if len(headers) < 2:
            continue
        metric_indices = [
            column_index for column_index, header in enumerate(headers[1:], start=1) if TABLE_METRIC_RE.search(header)
        ]
        if not metric_indices:
            continue

        rows: list[QuantitativeRow] = []
        for candidate in lines[index + 1 : index + 18]:
            if candidate.path != item.path:
                break
            text = candidate.text.strip()
            if not text:
                continue
            if re.search(r"^\s*\\(?:end|caption|label)", text):
                break
            cells = split_table_cells(text)
            if len(cells) < len(headers):
                continue
            values: dict[str, float] = {}
            for column_index in metric_indices:
                header = headers[column_index]
                value = parse_value_cell(cells[column_index])
                if value is not None:
                    values[header] = value
            if values:
                rows.append(
                    QuantitativeRow(
                        path=candidate.path,
                        number=candidate.number,
                        label=cells[0],
                        values=values,
                    )
                )
        if rows:
            table_headers = [headers[0], *[headers[column_index] for column_index in metric_indices]]
            tables.append(
                QuantitativeTable(
                    path=item.path,
                    header_number=item.number,
                    headers=table_headers,
                    rows=rows,
                )
            )
    return tables


def find_scale_anchors(lines: list[SourceLine]) -> list[ScaleAnchor]:
    anchors: list[ScaleAnchor] = []

    for item in lines:
        if "\\includegraphics" in item.text or "width=" in item.text:
            continue
        if not SCALE_ANCHOR_RE.search(item.text):
            continue
        unit = unit_from_text(item.text)
        if unit is None:
            continue
        value = parse_value_cell(item.text)
        if value is not None and value > 0:
            anchors.append(
                ScaleAnchor(
                    path=item.path,
                    number=item.number,
                    label=clean_cell(item.text)[:80],
                    value=value,
                    unit=unit,
                )
            )

    for index, item in enumerate(lines):
        headers = split_table_cells(item.text)
        if len(headers) < 2:
            continue
        anchor_indices = [
            column_index
            for column_index, header in enumerate(headers)
            if unit_from_text(header) is not None
            and not TABLE_METRIC_RE.search(header)
            and not PERCENT_SCALE_RE.search(header)
        ]
        if not anchor_indices:
            continue
        for candidate in lines[index + 1 : index + 18]:
            if candidate.path != item.path:
                break
            if re.search(r"^\s*\\(?:end|caption|label)", candidate.text):
                break
            cells = split_table_cells(candidate.text)
            if not cells:
                continue
            for column_index in anchor_indices:
                if len(cells) <= column_index:
                    continue
                value = parse_value_cell(cells[column_index])
                unit = unit_from_text(headers[column_index])
                if value is not None and unit is not None and value > 0:
                    anchors.append(
                        ScaleAnchor(
                            path=candidate.path,
                            number=candidate.number,
                            label=headers[column_index],
                            value=value,
                            unit=unit,
                        )
                    )

    seen: set[tuple[Path, int, str, float, str]] = set()
    deduped: list[ScaleAnchor] = []
    for anchor in anchors:
        signature = (anchor.path, anchor.number, anchor.label, anchor.value, anchor.unit)
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(anchor)
    return deduped


def has_nearby_practical_context(lines: list[SourceLine], path: Path, number: int) -> bool:
    for item in lines:
        if item.path == path and abs(item.number - number) <= 14:
            if PRACTICAL_CONTEXT_RE.search(item.text):
                return True
    return False


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

    root = repo_root()
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
