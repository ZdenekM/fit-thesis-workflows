from pathlib import Path

from thesis_review_workflow.evaluation_claims import (
    SourceLine,
    clean_cell,
    convert_unit,
    find_scale_anchors,
    has_nearby_practical_context,
    is_data_artifact_path,
    is_script_artifact_path,
    metric_direction,
    parse_quantitative_tables,
    script_artifact_from_data_path,
    split_table_cells,
    unit_from_text,
)


def source_lines(path: Path, texts: list[str]) -> list[SourceLine]:
    return [SourceLine(path=path, number=index, text=text) for index, text in enumerate(texts, start=1)]


def test_table_cell_cleanup_and_metric_direction() -> None:
    assert clean_cell(r"  \textbf{RMSE [kW]} \\  ") == "RMSE [kW]"
    assert split_table_cells("Method        RMSE [kW]    Accuracy [%]") == ["Method", "RMSE [kW]", "Accuracy [%]"]
    assert metric_direction("RMSE [kW]") == "lower"
    assert metric_direction("Accuracy [%]") == "higher"
    assert metric_direction("Metric value") == "unknown"


def test_parse_quantitative_tables_keeps_metric_columns_only() -> None:
    path = Path("cases/case/rounds/round-a/extracted/thesis.txt")
    lines = source_lines(
        path,
        [
            "System capacity is 100 kW.",
            "Method        Capacity [kW]    RMSE [kW]    MAE [kW]",
            "baseline      100              10           8",
            "variant       100              9            10",
        ],
    )

    tables = parse_quantitative_tables(lines)

    assert len(tables) == 1
    assert tables[0].headers == ["Method", "RMSE [kW]", "MAE [kW]"]
    assert tables[0].rows[1].label == "variant"
    assert tables[0].rows[1].values == {"RMSE [kW]": 9.0, "MAE [kW]": 10.0}


def test_unit_conversion_and_scale_anchor_detection() -> None:
    path = Path("cases/case/rounds/round-a/extracted/thesis.txt")
    lines = source_lines(
        path,
        [
            "Installed capacity is 100 kW and defines the practical scale.",
            "Name        Limit [kW]",
            "battery     50",
            r"\includegraphics[width=100 kW]{plot}",
        ],
    )

    anchors = find_scale_anchors(lines)

    assert unit_from_text("RMSE [Wh]") == "wh"
    assert convert_unit(1.5, "kwh", "wh") == 1500.0
    assert convert_unit(1.0, "kwh", "kw") is None
    assert [(anchor.value, anchor.unit) for anchor in anchors] == [(100.0, "kw"), (50.0, "kw")]
    assert has_nearby_practical_context(lines, path, 2)


def test_artifact_path_classification() -> None:
    assert is_data_artifact_path(Path("inputs/eval_results.csv"))
    assert is_data_artifact_path(Path("inputs/result_metrics.json"))
    assert not is_data_artifact_path(Path("inputs/config.json"))
    assert script_artifact_from_data_path(Path("work/eval_analysis.ipynb"))
    assert is_script_artifact_path(Path("work/eval_metrics.py"))
    assert not is_script_artifact_path(Path("work/app.py"))
