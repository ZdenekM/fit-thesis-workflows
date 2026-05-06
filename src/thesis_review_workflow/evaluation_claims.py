"""Pure helpers for quantitative thesis-evaluation claim checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

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
NUMBER_RE = re.compile(r"[-+]?\d+(?:[,.]\d+)?")
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
    r"%|percent|procent|accuracy|precision|recall|specificity|sensitivity|F1|AUC|success|úspěš|uspes",
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


def is_data_artifact_path(path: Path) -> bool:
    suffix = path.suffix
    if suffix not in DATA_EXTENSIONS:
        return False
    return suffix not in {".json", ".jsonl"} or bool(DATA_NAME_RE.search(path.name))


def is_script_artifact_path(path: Path) -> bool:
    suffix = path.suffix
    return suffix in SCRIPT_EXTENSIONS and bool(SCRIPT_NAME_RE.search(path.name))


def script_artifact_from_data_path(path: Path) -> bool:
    return path.suffix in NOTEBOOK_EXTENSIONS and bool(SCRIPT_NAME_RE.search(path.name))


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
