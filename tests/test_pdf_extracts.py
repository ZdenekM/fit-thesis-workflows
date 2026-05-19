from pathlib import Path

from thesis_review_workflow.pdf_extracts import (
    PDF_EXTRACT_SCHEMA_VERSION,
    expected_pdf_extract_path,
    expected_pdf_extract_ref,
    iter_pdf_extract_sidecars,
    load_pdf_extract_manifest,
    pdf_extract_is_current,
    pdf_extract_sidecar_path,
    source_fingerprints_from_pdf_extract_manifest,
    write_pdf_extract_manifest,
)
from thesis_review_workflow.reuse import SourceClass


def make_round(tmp_path: Path) -> Path:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "inputs").mkdir(parents=True)
    (round_dir / "extracted").mkdir()
    return round_dir


def test_pdf_extract_sidecar_records_hash_bound_source_and_output(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    input_pdf = round_dir / "inputs" / "thesis.pdf"
    output_txt = round_dir / "extracted" / "thesis.txt"
    input_pdf.write_bytes(b"%PDF synthetic\n")
    output_txt.write_text("Extracted text\n", encoding="utf-8")

    manifest = write_pdf_extract_manifest(
        round_dir,
        input_pdf,
        output_txt,
        extractor_version="pdftotext synthetic",
        generated_at="2026-05-13T12:00:00Z",
    )

    input_record = manifest["input_pdf"]
    output_record = manifest["output_text"]
    extractor = manifest["extractor"]

    assert isinstance(input_record, dict)
    assert isinstance(output_record, dict)
    assert isinstance(extractor, dict)
    assert pdf_extract_sidecar_path(output_txt).is_file()
    assert manifest["schema_version"] == PDF_EXTRACT_SCHEMA_VERSION
    assert input_record["path"] == "inputs/thesis.pdf"
    assert output_record["path"] == "extracted/thesis.txt"
    assert extractor["args"] == ["-layout"]
    assert pdf_extract_is_current(round_dir, input_pdf, output_txt, extractor_version="pdftotext synthetic")


def test_pdf_extract_currentness_fails_when_output_changes(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    input_pdf = round_dir / "inputs" / "thesis.pdf"
    output_txt = round_dir / "extracted" / "thesis.txt"
    input_pdf.write_bytes(b"%PDF synthetic\n")
    output_txt.write_text("Extracted text\n", encoding="utf-8")
    write_pdf_extract_manifest(round_dir, input_pdf, output_txt, extractor_version="pdftotext synthetic")

    output_txt.write_text("Changed text\n", encoding="utf-8")

    assert not pdf_extract_is_current(round_dir, input_pdf, output_txt, extractor_version="pdftotext synthetic")


def test_pdf_extract_manifest_exposes_reuse_source_fingerprints(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    input_pdf = round_dir / "inputs" / "thesis.pdf"
    output_txt = round_dir / "extracted" / "thesis.txt"
    input_pdf.write_bytes(b"%PDF synthetic\n")
    output_txt.write_text("Extracted text\n", encoding="utf-8")
    write_pdf_extract_manifest(round_dir, input_pdf, output_txt, extractor_version="pdftotext synthetic")
    loaded = load_pdf_extract_manifest(pdf_extract_sidecar_path(output_txt))

    assert loaded is not None
    fingerprints = source_fingerprints_from_pdf_extract_manifest(loaded)

    assert [(item.source_ref, item.source_class) for item in fingerprints] == [
        ("inputs/thesis.pdf", SourceClass.THESIS_PDF),
        ("extracted/thesis.txt", SourceClass.THESIS_EXTRACT),
    ]
    assert all(item.comparable for item in fingerprints)


def test_specialized_pdf_extract_mapping_handles_theses_similarity_report(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    report_pdf = round_dir / "inputs" / "theses_similarity" / "report.pdf"
    report_txt = round_dir / "extracted" / "theses_similarity" / "report.txt"
    report_pdf.parent.mkdir(parents=True)
    report_txt.parent.mkdir(parents=True)
    report_pdf.write_bytes(b"%PDF synthetic report\n")
    report_txt.write_text("Similarity report\n", encoding="utf-8")
    write_pdf_extract_manifest(round_dir, report_pdf, report_txt, extractor_version="pdftotext synthetic")

    assert expected_pdf_extract_ref("inputs/theses_similarity/report.pdf") == "extracted/theses_similarity/report.txt"
    assert expected_pdf_extract_path(round_dir, report_pdf) == report_txt
    assert iter_pdf_extract_sidecars(round_dir) == [pdf_extract_sidecar_path(report_txt)]
