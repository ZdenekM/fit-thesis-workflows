import json
from pathlib import Path

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.cli.check_literature_citation_review import validate_source_acquisition_file
from thesis_review_workflow.literature_source_acquisition import validate_source_acquisition_payload


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def valid_payload(round_dir: Path) -> dict[str, object]:
    (round_dir / "extracted").mkdir(parents=True)
    (round_dir / "extracted" / "thesis.txt").write_text("Claim [1].\n", encoding="utf-8")
    (round_dir / "work" / "source" / "refs.bib").parent.mkdir(parents=True)
    (round_dir / "work" / "source" / "refs.bib").write_text("@article{a}\n", encoding="utf-8")
    evidence = round_dir / "work" / "literature" / "abe-suzuki.txt"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("full text extract\n", encoding="utf-8")
    source_refs = ["extracted/thesis.txt", "work/source/refs.bib"]
    return {
        "schema_version": "literature-source-acquisition-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-18T12:00:00Z",
        "producer_type": "agent",
        "producer_role": "thesis_literature_citation_reviewer",
        "producer_agent": "agent-a",
        "source_resolution_policy": "legal_public_sources_only",
        "target_selection_policy": {
            "selected_when": [
                "central to thesis argument",
                "metadata mismatch or suspicious claim-source alignment",
            ]
        },
        "source_refs": source_refs,
        "source_sha256": {ref: sha256_file(round_dir / ref) for ref in source_refs},
        "citations": [
            {
                "citation_id": "ref-1",
                "citation_label": "[1]",
                "title_or_source": "Abe and Suzuki contour source",
                "selection_status": "selected",
                "selection_reasons": ["suspicious metadata mismatch"],
                "thesis_refs": ["extracted/thesis.txt"],
                "acquisition_status": "full_text_read",
                "attempts": [
                    {
                        "source_type": "open_repository_pdf",
                        "locator": "https://example.test/source.pdf",
                        "status": "full_text_read",
                    }
                ],
                "local_source_refs": ["work/literature/abe-suzuki.txt"],
                "source_evidence_refs": ["work/literature/abe-suzuki.txt"],
                "claim_support_checked": [
                    {
                        "claim_ref": "extracted/thesis.txt",
                        "verdict": "does_not_support",
                    }
                ],
                "limitations": [],
            },
            {
                "citation_id": "ref-2",
                "citation_label": "[2]",
                "title_or_source": "Background source",
                "selection_status": "not_selected",
                "selection_reasons": ["not material to contested or central claims"],
                "thesis_refs": ["extracted/thesis.txt"],
                "acquisition_status": "not_attempted_not_material",
                "attempts": [],
                "local_source_refs": [],
                "source_evidence_refs": [],
                "claim_support_checked": [],
                "limitations": [],
            },
        ],
        "limitations": [],
    }


def test_source_acquisition_payload_accepts_targeted_selected_source(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    payload = valid_payload(round_dir)

    assert (
        validate_source_acquisition_payload(
            payload,
            round_dir=round_dir,
            case_id="case-a",
            round_id="round-a",
        )
        == []
    )


def test_source_acquisition_payload_rejects_selected_without_attempt(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    payload = valid_payload(round_dir)
    selected = payload["citations"][0]  # type: ignore[index]
    selected["attempts"] = []  # type: ignore[index]

    errors = validate_source_acquisition_payload(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert any("selected citation must record at least one source attempt" in error for error in errors)


def test_source_acquisition_payload_rejects_stale_source_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    payload = valid_payload(round_dir)
    (round_dir / "extracted" / "thesis.txt").write_text("Changed claim [1].\n", encoding="utf-8")

    errors = validate_source_acquisition_payload(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert any("source_sha256 is stale for extracted/thesis.txt" in error for error in errors)


def test_source_acquisition_payload_rejects_invalid_attempt_status(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    payload = valid_payload(round_dir)
    selected = payload["citations"][0]  # type: ignore[index]
    selected["attempts"][0]["status"] = "download_failed"  # type: ignore[index]

    errors = validate_source_acquisition_payload(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert any("attempts item 1 status must be one of" in error for error in errors)


def test_source_acquisition_payload_rejects_mismatched_attempt_status(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    payload = valid_payload(round_dir)
    selected = payload["citations"][0]  # type: ignore[index]
    selected["attempts"][0]["status"] = "abstract_read"  # type: ignore[index]

    errors = validate_source_acquisition_payload(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert any("acquisition_status must match at least one attempt status" in error for error in errors)


def test_source_acquisition_payload_rejects_blocked_selected_without_limitations(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    payload = valid_payload(round_dir)
    selected = payload["citations"][0]  # type: ignore[index]
    selected["acquisition_status"] = "paywalled_unavailable"  # type: ignore[index]
    selected["attempts"][0]["status"] = "paywalled_unavailable"  # type: ignore[index]
    selected["local_source_refs"] = []  # type: ignore[index]
    selected["source_evidence_refs"] = []  # type: ignore[index]
    selected["claim_support_checked"] = [  # type: ignore[index]
        {"claim_ref": "extracted/thesis.txt", "verdict": "not_checked"}
    ]

    errors = validate_source_acquisition_payload(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert any("paywalled_unavailable selected citation must record a limitation" in error for error in errors)
    assert any(
        "selected blocked/unresolved citations require a top-level limitations entry" in error for error in errors
    )


def test_literature_checker_rejects_missing_source_acquisition(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"

    errors = validate_source_acquisition_file(
        round_dir / "work" / "literature" / "source_acquisition.json",
        "case-a",
        "round-a",
        round_dir,
    )

    assert errors == [
        "missing targeted literature source acquisition artifact: "
        "work/literature/source_acquisition.json; select key/suspicious citations and record legal source attempts"
    ]


def test_literature_checker_accepts_source_acquisition_file(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    path = round_dir / "work" / "literature" / "source_acquisition.json"
    write_json(path, valid_payload(round_dir))

    assert validate_source_acquisition_file(path, "case-a", "round-a", round_dir) == []
