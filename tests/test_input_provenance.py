import json
from pathlib import Path, PurePosixPath

from thesis_review_workflow.cli import import_round
from thesis_review_workflow.input_provenance import (
    INPUT_PROVENANCE_REL,
    InputRequest,
    build_input_provenance_payload,
    directory_input_record,
    normalize_input_name,
    plan_input_storage,
    validate_input_provenance_payload,
    write_input_provenance,
)
from thesis_review_workflow.work_artifacts import KNOWN_JSON_ARTIFACT_SCHEMAS


def test_download_suffixes_and_percent_escapes_are_tidied() -> None:
    assert normalize_input_name("Thesis%20Final (1).PDF") == "Thesis-Final.pdf"
    assert normalize_input_name("  spaced   name .pdf") == "spaced-name.pdf"
    assert normalize_input_name("a--b__c.PDF") == "a-b-c.pdf"


def test_an_undecodable_escape_is_left_literal_rather_than_replaced() -> None:
    """Permissive decoding would lose the operator's original text irreversibly."""

    assert normalize_input_name("weird%zz.pdf") == "weird%zz.pdf"
    assert normalize_input_name("bad%FF.pdf") == "bad%FF.pdf"


def test_windows_hostile_names_become_storable() -> None:
    assert normalize_input_name("CON.pdf") == "CON-input.pdf"
    assert normalize_input_name("NUL") == "NUL-input"
    assert normalize_input_name("trailing...") == "trailing"
    assert normalize_input_name("a:b|c?.pdf") == "a-b-c.pdf"


def test_a_name_can_never_normalize_to_an_unusable_basename() -> None:
    for name in ("..", ".", "   ", "---", "%2e%2e"):
        stored = normalize_input_name(name)
        assert stored not in {"", ".", ".."}, name
        assert "/" not in stored and "\\" not in stored, name


def test_a_path_separator_in_a_name_cannot_escape_the_directory() -> None:
    assert normalize_input_name("../../etc/passwd") == "passwd"
    assert normalize_input_name("a/b/c.pdf") == "c.pdf"


def write_input(directory: Path, name: str, content: bytes) -> Path:
    path = directory / name
    path.write_bytes(content)
    return path


def test_identical_content_is_stored_once_and_every_occurrence_is_kept(tmp_path: Path) -> None:
    """Roles are load-bearing: assignment metadata filters by role, so both must survive."""

    thesis = write_input(tmp_path, "Thesis (1).pdf", b"%PDF-1.4\n")
    assignment = write_input(tmp_path, "zadani.pdf", b"%PDF-1.4\n")

    plan = plan_input_storage(
        [
            InputRequest(role="thesis_pdf", source=thesis, dest_dir_rel=PurePosixPath("inputs")),
            InputRequest(role="assignment_pdf", source=assignment, dest_dir_rel=PurePosixPath("inputs")),
        ]
    )

    assert len(plan.copies) == 1
    assert [record.role for record in plan.records] == ["thesis_pdf", "assignment_pdf"]
    assert {record.stored_rel for record in plan.records} == {"inputs/Thesis.pdf"}
    assert [record.is_first_occurrence for record in plan.records] == [True, False]


def test_different_content_under_one_normalized_name_is_refused(tmp_path: Path) -> None:
    first = write_input(tmp_path, "Report (1).pdf", b"one\n")
    second_dir = tmp_path / "other"
    second_dir.mkdir()
    second = write_input(second_dir, "Report.pdf", b"two\n")

    try:
        plan_input_storage(
            [
                InputRequest(role="input", source=first, dest_dir_rel=PurePosixPath("inputs")),
                InputRequest(role="input", source=second, dest_dir_rel=PurePosixPath("inputs")),
            ]
        )
    except ValueError as exc:
        assert "normalize to the same destination" in str(exc)
    else:  # pragma: no cover - the guard must fire
        raise AssertionError("a genuine collision must be refused")


def test_identical_content_with_different_suffixes_keeps_both_copies(tmp_path: Path) -> None:
    """Extraction filters on the stored suffix, so the PDF occurrence must stay a PDF."""

    without = write_input(tmp_path, "thesis", b"%PDF-1.4\n")
    with_suffix = write_input(tmp_path, "thesis.pdf", b"%PDF-1.4\n")

    plan = plan_input_storage(
        [
            InputRequest(role="input", source=without, dest_dir_rel=PurePosixPath("inputs")),
            InputRequest(role="thesis_pdf", source=with_suffix, dest_dir_rel=PurePosixPath("inputs")),
        ]
    )

    stored = {record.stored_rel for record in plan.records}
    assert stored == {"inputs/thesis", "inputs/thesis.pdf"}
    assert len(plan.copies) == 2


def test_identical_content_in_different_directories_is_stored_in_both(tmp_path: Path) -> None:
    source = write_input(tmp_path, "notes.md", b"same\n")

    plan = plan_input_storage(
        [
            InputRequest(role="input", source=source, dest_dir_rel=PurePosixPath("inputs")),
            InputRequest(
                role="previous_feedback", source=source, dest_dir_rel=PurePosixPath("inputs/previous-feedback")
            ),
        ]
    )

    assert len(plan.copies) == 2


def make_round(tmp_path: Path) -> Path:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "inputs").mkdir(parents=True)
    return round_dir


def test_provenance_is_written_only_when_inputs_exist(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)

    assert write_input_provenance(round_dir, case_id="case-a", round_id="round-a", records=()) is None
    assert not (round_dir / INPUT_PROVENANCE_REL).exists()


def test_a_written_record_validates_against_the_stored_files(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    source = write_input(tmp_path, "Thesis (1).pdf", b"%PDF-1.4\n")
    plan = plan_input_storage([InputRequest(role="thesis_pdf", source=source, dest_dir_rel=PurePosixPath("inputs"))])
    for copy_source, destination in plan.copies:
        (round_dir / destination).write_bytes(copy_source.read_bytes())
    written = write_input_provenance(round_dir, case_id="case-a", round_id="round-a", records=plan.records)

    assert written is not None
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert validate_input_provenance_payload(payload, round_dir=round_dir) == []
    assert payload["generated_at"], "the work-artifact envelope requires generated_at"


def test_validation_rejects_a_fabricated_hash_a_missing_file_and_an_escaping_ref(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs" / "thesis.pdf").write_bytes(b"%PDF-1.4\n")
    base = {
        "role": "thesis_pdf",
        "original_name": "thesis.pdf",
        "stored_ref": "inputs/thesis.pdf",
        "sha256": "0" * 64,
        "size_bytes": 9,
        "deduplicated": False,
    }
    payload = build_input_provenance_payload(
        case_id="case-a", round_id="round-a", generated_at="2026-09-07T00:00:00Z", records=()
    )

    payload["inputs"] = [dict(base)]
    assert any(
        "sha256 does not match" in error for error in validate_input_provenance_payload(payload, round_dir=round_dir)
    )

    payload["inputs"] = [{**base, "stored_ref": "inputs/absent.pdf"}]
    assert any("does not exist" in error for error in validate_input_provenance_payload(payload, round_dir=round_dir))

    for unsafe in ("../outside.pdf", "/etc/passwd", "work/code/main.py"):
        payload["inputs"] = [{**base, "stored_ref": unsafe}]
        errors = validate_input_provenance_payload(payload, round_dir=round_dir)
        assert any("safe round-relative path under inputs/" in error for error in errors), unsafe

    payload["inputs"] = [{k: v for k, v in base.items() if k != "deduplicated"}]
    assert any("deduplicated must be a boolean" in error for error in validate_input_provenance_payload(payload))

    payload["inputs"] = [{**base, "size_bytes": -1}]
    assert any("size_bytes" in error for error in validate_input_provenance_payload(payload))


def test_the_record_is_registered_as_a_known_work_artifact() -> None:
    """Registration buys the envelope check; the record validator is wired beside it."""

    assert INPUT_PROVENANCE_REL in KNOWN_JSON_ARTIFACT_SCHEMAS


def test_case_only_clashes_follow_each_entrypoint_s_existing_guarantee(tmp_path: Path) -> None:
    """import-round refused these outright; bootstrap stored both and let the workspace report.

    Preserving both keeps `code_workspace.CaseInsensitivePathRegistry`'s tested collision
    path reachable while `import-round` keeps its Windows guard.
    """
    upper = write_input(tmp_path, "Code.zip", b"upper\n")
    lower_dir = tmp_path / "lower"
    lower_dir.mkdir()
    lower = write_input(lower_dir, "code.zip", b"lower\n")
    requests = [
        InputRequest(role="source_archive", source=upper, dest_dir_rel=PurePosixPath("inputs/source")),
        InputRequest(role="source_archive", source=lower, dest_dir_rel=PurePosixPath("inputs/source")),
    ]

    permissive = plan_input_storage(requests)
    assert {record.stored_rel for record in permissive.records} == {
        "inputs/source/Code.zip",
        "inputs/source/code.zip",
    }

    try:
        plan_input_storage(requests, refuse_case_insensitive_clash=True)
    except ValueError as exc:
        assert "differ only by case on Windows" in str(exc)
    else:  # pragma: no cover - the guard must fire
        raise AssertionError("the refusing policy must reject a case-only clash")


def test_import_round_itself_refuses_a_case_only_clash(capsys, monkeypatch, tmp_path: Path) -> None:
    """The library policy is worthless if the entrypoint never asks for it.

    The review found exactly that: the flag existed, defaulted to permissive, and no
    production caller passed it, so the guard this slice replaced was silently gone.
    """
    root = tmp_path / "repo"
    case_dir = root / "cases" / "case-a"
    (case_dir / "rounds").mkdir(parents=True)
    (root / "templates").mkdir()
    for template in (
        "round-notes.md",
        "assignment.md",
        "supervisor-intake.md",
        "opponent-intake.md",
        "opponent-report-review-intake.md",
        "supervisor-report-intake.md",
    ):
        (root / "templates" / template).write_text(f"# {template}\nRound:\nDate:\n", encoding="utf-8")
    upper = write_input(tmp_path, "Thesis.pdf", b"AAA\n")
    lower_dir = tmp_path / "lower"
    lower_dir.mkdir()
    lower = write_input(lower_dir, "thesis.pdf", b"BBB\n")
    monkeypatch.setattr(import_round, "repo_root", lambda: root)

    result = import_round.main(["import-round", "case-a", "clash", str(upper), str(lower)])

    assert result == 1
    assert "differ only by case on Windows" in capsys.readouterr().err
    assert not any((case_dir / "rounds").iterdir()), "a refused import must leave no round behind"


def test_identical_content_with_case_only_names_is_still_deduplicated(tmp_path: Path) -> None:
    upper = write_input(tmp_path, "Code.zip", b"same\n")
    lower_dir = tmp_path / "lower"
    lower_dir.mkdir()
    lower = write_input(lower_dir, "code.zip", b"same\n")

    plan = plan_input_storage(
        [
            InputRequest(role="source_archive", source=upper, dest_dir_rel=PurePosixPath("inputs/source")),
            InputRequest(role="source_archive", source=lower, dest_dir_rel=PurePosixPath("inputs/source")),
        ]
    )

    assert len(plan.copies) == 1
    assert [record.is_first_occurrence for record in plan.records] == [True, False]


def test_a_later_occurrence_of_a_claimed_destination_is_not_copied_again(tmp_path: Path) -> None:
    """Copying one stored file twice would extract it twice, the measured defect itself."""

    without = write_input(tmp_path, "thesis", b"%PDF-1.4\n")
    first_dir = tmp_path / "one"
    first_dir.mkdir()
    second_dir = tmp_path / "two"
    second_dir.mkdir()
    first = write_input(first_dir, "thesis.pdf", b"%PDF-1.4\n")
    second = write_input(second_dir, "thesis.pdf", b"%PDF-1.4\n")

    plan = plan_input_storage(
        [
            InputRequest(role="input", source=without, dest_dir_rel=PurePosixPath("inputs")),
            InputRequest(role="input", source=first, dest_dir_rel=PurePosixPath("inputs")),
            InputRequest(role="input", source=second, dest_dir_rel=PurePosixPath("inputs")),
        ]
    )

    assert [destination for _, destination in plan.copies] == ["inputs/thesis", "inputs/thesis.pdf"]
    assert [record.is_first_occurrence for record in plan.records] == [True, True, False]


def test_empty_files_are_not_deduplicated_into_one(tmp_path: Path) -> None:
    """Every empty file shares a digest; collapsing two hides two failed downloads."""

    first = write_input(tmp_path, "thesis.pdf", b"")
    second = write_input(tmp_path, "zadani.pdf", b"")

    plan = plan_input_storage(
        [
            InputRequest(role="thesis_pdf", source=first, dest_dir_rel=PurePosixPath("inputs")),
            InputRequest(role="assignment_pdf", source=second, dest_dir_rel=PurePosixPath("inputs")),
        ]
    )

    assert [destination for _, destination in plan.copies] == ["inputs/thesis.pdf", "inputs/zadani.pdf"]


def test_normalization_never_produces_an_unstorable_name() -> None:
    """NFC composition can expand a name, so a legal source name could become too long."""

    expanding = "क़" * 80 + ".pdf"
    stored = normalize_input_name(expanding)

    assert len(expanding.encode("utf-8")) > 240
    assert len(stored.encode("utf-8")) <= 120
    assert stored.endswith(".pdf")

    assert normalize_input_name("a" * 400 + ".pdf").endswith(".pdf")
    assert len(normalize_input_name("a" * 400 + ".pdf").encode("utf-8")) <= 120


def test_bidi_controls_cannot_reverse_a_stored_name() -> None:
    assert normalize_input_name("thesis‮pdf.exe") == "thesispdf.exe"
    assert "‮" not in normalize_input_name("a‮b.pdf")


def test_a_directory_record_carries_no_digest_and_still_validates(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs" / "student-repo").mkdir()
    record = directory_input_record(tmp_path / "student repo (1)", "inputs/student-repo")

    written = write_input_provenance(round_dir, case_id="case-a", round_id="round-a", records=(record,))

    assert written is not None
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["inputs"][0]["original_name"] == "student repo (1)"
    assert validate_input_provenance_payload(payload, round_dir=round_dir) == []


def test_a_missing_digest_on_a_non_directory_is_still_an_error(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs" / "thesis.pdf").write_bytes(b"%PDF-1.4\n")
    payload = build_input_provenance_payload(
        case_id="case-a", round_id="round-a", generated_at="2026-09-07T00:00:00Z", records=()
    )
    payload["inputs"] = [
        {
            "role": "input",
            "original_name": "thesis.pdf",
            "stored_ref": "inputs/thesis.pdf",
            "sha256": "",
            "size_bytes": 0,
            "deduplicated": False,
        }
    ]

    errors = validate_input_provenance_payload(payload, round_dir=round_dir)

    assert any("no digest but is not a directory" in error for error in errors)
