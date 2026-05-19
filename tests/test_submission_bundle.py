import io
import json
import zipfile
from pathlib import Path

from thesis_review_workflow.submission_bundle import (
    BundleInventoryLimits,
    build_submission_bundle_inventory,
    materialize_submission_bundle_candidate,
    render_inventory_markdown,
    write_submission_bundle_inventory,
)
from thesis_review_workflow.work_artifacts import collect_supporting_work_artifacts, validate_supporting_work_artifacts


def nested_zip(entries: dict[str, bytes | str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as handle:
        for name, payload in entries.items():
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
            handle.writestr(name, data)
    return buffer.getvalue()


def make_round(tmp_path: Path) -> Path:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "inputs").mkdir(parents=True)
    return round_dir


def candidate_by_class(payload: dict, artifact_class: str) -> list[dict]:
    return [item for item in payload["candidates"] if item["artifact_class"] == artifact_class]


def test_nextcloud_style_bundle_inventory_discovers_nested_artifacts(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    code_archive = nested_zip(
        {
            "project/pyproject.toml": "[project]\nname = 'synthetic'\n",
            "project/src/main.py": "print('synthetic')\n",
            "project/tests/test_main.py": "def test_main():\n    assert True\n",
        }
    )
    thesis_source = nested_zip(
        {
            "thesis/main.tex": "\\section{Synthetic}\n",
            "thesis/zadani.pdf": b"%PDF-1.4\n",
        }
    )
    bundle = round_dir / "inputs" / "submission.zip"
    with zipfile.ZipFile(bundle, "w") as handle:
        handle.writestr("Nextcloud export/code archive.zip", code_archive)
        handle.writestr("Nextcloud export/thesis-source.zip", thesis_source)
        handle.writestr("Nextcloud export/README.md", "# Synthetic\n")
        handle.writestr("Nextcloud export/app.apk", b"apk placeholder")
        handle.writestr("Nextcloud export/demo video.mp4", b"mp4 placeholder")

    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/submission.zip"],
        producer="scripts/review-round-start",
        generated_at="2026-05-19T12:00:00Z",
    )
    rerun = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/submission.zip"],
        producer="scripts/review-round-start",
        generated_at="2026-05-19T12:00:00Z",
    )

    assert payload["schema_version"] == "submission-bundle-inventory-v1"
    assert payload["source_bundles"][0]["source_bundle_ref"] == "inputs/submission.zip"
    assert {item["candidate_id"] for item in payload["candidates"]} == {
        item["candidate_id"] for item in rerun["candidates"]
    }
    assert candidate_by_class(payload, "code_archive_candidate")
    assert candidate_by_class(payload, "thesis_source_archive_candidate")
    assert candidate_by_class(payload, "readme_candidate")
    assert candidate_by_class(payload, "executable_artifact")
    assert candidate_by_class(payload, "media_artifact")
    assignment = candidate_by_class(payload, "assignment_pdf_candidate")[0]
    assert assignment["nested_path_chain"] == ["Nextcloud export/thesis-source.zip", "thesis/zadani.pdf"]
    assert assignment["expected_extract_ref"].startswith("extracted/submission_bundle/")
    code_candidate = candidate_by_class(payload, "code_archive_candidate")[0]
    assert code_candidate["summary"]["code_like"] is True
    assert code_candidate["summary"]["test_count"] == 1
    assert "archive_contains_code_evidence" in code_candidate["reason_codes"]
    assert {item["state"] for item in payload["candidates"]} == {"materialize_candidate"}
    assert "Nextcloud export/code archive.zip" in render_inventory_markdown(payload)


def test_large_archive_records_bounded_unknown_state_without_code_absence_claim(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    bundle = round_dir / "inputs" / "large.zip"
    with zipfile.ZipFile(bundle, "w") as handle:
        handle.writestr("project/src/main.py", "print('synthetic')\n")

    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/large.zip"],
        limits=BundleInventoryLimits(max_archive_bytes=1),
        generated_at="2026-05-19T12:00:00Z",
    )

    assert len(payload["candidates"]) == 1
    candidate = payload["candidates"][0]
    assert candidate["state"] == "not_listed_due_to_size"
    assert candidate["source_bundle_sha256"] == payload["source_bundles"][0]["source_bundle_sha256"]
    assert candidate["size_bytes"] == bundle.stat().st_size
    assert "absence" not in json.dumps(payload)
    assert payload["summary"]["not_listed_due_to_size_count"] == 1


def test_inventory_rejects_zip_slip_and_case_insensitive_collisions(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    bundle = round_dir / "inputs" / "unsafe.zip"
    with zipfile.ZipFile(bundle, "w") as handle:
        handle.writestr("../evil.txt", "unsafe\n")
        handle.writestr("project/Foo.py", "print('upper')\n")
        handle.writestr("project/foo.py", "print('lower')\n")
        handle.writestr("project\\windows.txt", "unsafe separator\n")

    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/unsafe.zip"],
        generated_at="2026-05-19T12:00:00Z",
    )
    skipped = payload["skipped_entries"]

    assert any("unsafe_archive_member_path" in item["reason_codes"] for item in skipped)
    assert any("case_insensitive_path_collision" in item["reason_codes"] for item in skipped)
    assert [item["candidate_ref"] for item in payload["candidates"]] == ["inputs/unsafe.zip!project/Foo.py"]


def test_inventory_rejects_windows_invalid_member_names(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    bundle = round_dir / "inputs" / "windows-invalid.zip"
    with zipfile.ZipFile(bundle, "w") as handle:
        handle.writestr("project/CON.txt", "reserved\n")
        handle.writestr("project/bad:name.txt", "colon\n")
        handle.writestr("project/trailingdot.", "dot\n")

    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/windows-invalid.zip"],
        generated_at="2026-05-19T12:00:00Z",
    )

    assert payload["candidates"] == []
    details = " ".join(item["detail"] for item in payload["skipped_entries"])
    assert "reserved Windows device name CON" in details
    assert "invalid on Windows" in details
    assert "dot or space" in details


def test_nested_archive_depth_limit_is_recorded_recursively(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    inner = nested_zip({"deep/README.md": "# deep\n"})
    middle = nested_zip({"middle/inner.zip": inner})
    bundle = round_dir / "inputs" / "nested.zip"
    with zipfile.ZipFile(bundle, "w") as handle:
        handle.writestr("outer/middle.zip", middle)

    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/nested.zip"],
        limits=BundleInventoryLimits(max_archive_depth=1),
        generated_at="2026-05-19T12:00:00Z",
    )

    limited = [item for item in payload["candidates"] if item["state"] == "nested_archive_depth_limit"]
    assert limited
    assert limited[0]["nested_path_chain"] == ["outer/middle.zip", "middle/inner.zip"]


def test_directory_bundle_skips_symlinks_before_hashing(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    outside = tmp_path / "private-outside.txt"
    outside.write_text("do not hash\n", encoding="utf-8")
    bundle_dir = round_dir / "inputs" / "bundle-dir"
    bundle_dir.mkdir()
    try:
        (bundle_dir / "external.txt").symlink_to(outside)
    except OSError:
        return
    (bundle_dir / "README.md").write_text("# Synthetic\n", encoding="utf-8")

    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/bundle-dir"],
        generated_at="2026-05-19T12:00:00Z",
    )

    assert candidate_by_class(payload, "readme_candidate")
    assert any("directory_symlink_skipped" in item["reason_codes"] for item in payload["skipped_entries"])
    assert all("private-outside" not in json.dumps(item) for item in payload["skipped_entries"])


def test_archive_inventory_enforces_total_read_budget(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    bundle = round_dir / "inputs" / "many-small.zip"
    with zipfile.ZipFile(bundle, "w") as handle:
        handle.writestr("one/README.md", "a" * 20)
        handle.writestr("two/README.md", "b" * 20)

    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/many-small.zip"],
        limits=BundleInventoryLimits(max_read_bytes=25),
        generated_at="2026-05-19T12:00:00Z",
    )

    assert any("read_budget_limit_reached" in item["reason_codes"] for item in payload["skipped_entries"])


def test_multiple_bundle_inventory_preserves_all_sources_and_cross_bundle_ambiguity(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    for name, text in (("part-a.zip", "# a\n"), ("part-b.zip", "# b\n")):
        with zipfile.ZipFile(round_dir / "inputs" / name, "w") as handle:
            handle.writestr("README.md", text)

    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/part-a.zip", "inputs/part-b.zip"],
        producer="scripts/review-round-start",
        generated_at="2026-05-19T12:00:00Z",
    )

    assert [item["source_bundle_ref"] for item in payload["source_bundles"]] == [
        "inputs/part-a.zip",
        "inputs/part-b.zip",
    ]
    readmes = candidate_by_class(payload, "readme_candidate")
    assert {item["source_bundle_ref"] for item in readmes} == {"inputs/part-a.zip", "inputs/part-b.zip"}
    assert {item["state"] for item in readmes} == {"needs_operator_selection"}


def test_generated_executables_are_not_promoted_to_actionable_leaf_evidence(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    bundle = round_dir / "inputs" / "build-output.zip"
    with zipfile.ZipFile(bundle, "w") as handle:
        handle.writestr("project/bin/app.exe", b"binary")
        handle.writestr("project/obj/generated.dll", b"binary")

    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/build-output.zip"],
        generated_at="2026-05-19T12:00:00Z",
    )

    assert payload["candidates"] == []


def test_inventory_records_unsupported_archives_and_utf8_names(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    unsupported = round_dir / "inputs" / "řešení.7z"
    unsupported.write_bytes(b"not really 7z")
    bundle = round_dir / "inputs" / "utf8 bundle.zip"
    inner = nested_zip({"projekt/řešení.py": "print('synthetic')\n"})
    with zipfile.ZipFile(bundle, "w") as handle:
        handle.writestr("odevzdání/zdrojový kód.zip", inner)

    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/řešení.7z", "inputs/utf8 bundle.zip"],
        generated_at="2026-05-19T12:00:00Z",
    )

    unsupported_candidates = candidate_by_class(payload, "unsupported_archive")
    assert unsupported_candidates[0]["state"] == "unsupported_archive_type"
    assert any("odevzdání/zdrojový kód.zip" in item["candidate_ref"] for item in payload["candidates"])


def test_directory_bundle_inventory_stays_diagnostic_until_manifest_slice(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    bundle_dir = round_dir / "inputs" / "bundle dir"
    (bundle_dir / "src").mkdir(parents=True)
    (bundle_dir / "README.md").write_text("# Synthetic\n", encoding="utf-8")
    (bundle_dir / "src" / "main.py").write_text("print('synthetic')\n", encoding="utf-8")

    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/bundle dir"],
        generated_at="2026-05-19T12:00:00Z",
    )
    write_submission_bundle_inventory(round_dir=round_dir, payload=payload)
    records = collect_supporting_work_artifacts(round_dir)

    assert candidate_by_class(payload, "readme_candidate")
    assert candidate_by_class(payload, "first_party_candidate")
    assert "work/submission_bundle_inventory.json" not in {record["path"] for record in records}
    assert (round_dir / "work/submission_bundle_inventory.json").is_file()
    assert (round_dir / "work/submission_bundle_inventory.md").is_file()
    assert validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a") == []


def test_materialize_selected_nested_code_archive_records_manifest(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    code_archive = nested_zip({"project/pyproject.toml": "[project]\nname = 'synthetic'\n"})
    bundle = round_dir / "inputs" / "submission.zip"
    with zipfile.ZipFile(bundle, "w") as handle:
        handle.writestr("export/code.zip", code_archive)
    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/submission.zip"],
        producer="scripts/review-round-start",
        generated_at="2026-05-19T12:00:00Z",
    )
    write_submission_bundle_inventory(round_dir=round_dir, payload=payload)
    candidate_id = candidate_by_class(payload, "code_archive_candidate")[0]["candidate_id"]

    result = materialize_submission_bundle_candidate(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        candidate_id=candidate_id,
        generated_at="2026-05-19T12:01:00Z",
    )

    assert result.materialized_ref.startswith("inputs/")
    assert len(result.materialized_ref.split("/")) == 2
    assert zipfile.is_zipfile(result.materialized_path)
    updated_inventory = json.loads((round_dir / "work/submission_bundle_inventory.json").read_text(encoding="utf-8"))
    updated_candidate = candidate_by_class(updated_inventory, "code_archive_candidate")[0]
    assert updated_candidate["materialized_ref"] == result.materialized_ref
    manifest = json.loads((round_dir / "work/submission_bundle_materialization.json").read_text(encoding="utf-8"))
    [record] = manifest["materializations"]
    assert record["candidate_id"] == candidate_id
    assert record["source_bundle_ref"] == "inputs/submission.zip"
    assert record["nested_path_chain"] == ["export/code.zip"]
    assert record["materialized_ref"] == result.materialized_ref
    assert record["artifact_class"] == "code_archive_candidate"
    assert record["action"] == "materialized"
    assert record["selected_at"] == "2026-05-19T12:01:00Z"
    assert record["producer"] == "scripts/materialize-submission-bundle-candidate"
    assert record["state_at_selection"] == "materialize_candidate"
    assert record["source_inventory_ref"] == "work/submission_bundle_inventory.json"
    assert record["source_inventory_sha256"]
    assert record["source_member_sha256"] == record["materialized_sha256"]
    assert record["size_bytes"] == result.materialized_path.stat().st_size
    assert isinstance(record["reason_codes"], list)

    reused = materialize_submission_bundle_candidate(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        candidate_id=candidate_id,
        output_ref=result.materialized_ref,
        generated_at="2026-05-19T12:02:00Z",
    )
    assert reused.action == "reused_existing"
    manifest = json.loads((round_dir / "work/submission_bundle_materialization.json").read_text(encoding="utf-8"))
    assert len(manifest["materializations"]) == 1

    collision = "inputs/collision-code.zip"
    (round_dir / collision).write_text("different\n", encoding="utf-8")
    try:
        materialize_submission_bundle_candidate(
            case_id="case-a",
            round_id="round-a",
            round_dir=round_dir,
            candidate_id=candidate_id,
            output_ref=collision,
            generated_at="2026-05-19T12:03:00Z",
        )
    except ValueError as exc:
        assert "different content" in str(exc)
    else:
        raise AssertionError("materialization overwrote a different existing output")


def test_materialize_rejects_non_portable_explicit_output_names(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    bundle = round_dir / "inputs" / "submission.zip"
    with zipfile.ZipFile(bundle, "w") as handle:
        handle.writestr("README.md", "# synthetic\n")
    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/submission.zip"],
        producer="scripts/review-round-start",
        generated_at="2026-05-19T12:00:00Z",
    )
    write_submission_bundle_inventory(round_dir=round_dir, payload=payload)
    candidate_id = candidate_by_class(payload, "readme_candidate")[0]["candidate_id"]

    for output_ref in ("inputs/CON.zip", "inputs/bad:name.zip", "inputs/trailingdot."):
        try:
            materialize_submission_bundle_candidate(
                case_id="case-a",
                round_id="round-a",
                round_dir=round_dir,
                candidate_id=candidate_id,
                output_ref=output_ref,
                generated_at="2026-05-19T12:01:00Z",
            )
        except ValueError as exc:
            assert "not portable" in str(exc)
        else:
            raise AssertionError(f"non-portable output ref was accepted: {output_ref}")


def test_directory_materialization_rejects_symlinked_parent_escape(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "README.md").write_text("# outside\n", encoding="utf-8")
    bundle_dir = round_dir / "inputs" / "bundle-dir"
    bundle_dir.mkdir()
    try:
        (bundle_dir / "linked").symlink_to(outside, target_is_directory=True)
    except OSError:
        return
    payload = {
        "schema_version": "submission-bundle-inventory-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-19T12:00:00Z",
        "producer": "scripts/review-round-start",
        "limits": BundleInventoryLimits().as_record(),
        "source_bundles": [
            {
                "source_bundle_ref": "inputs/bundle-dir",
                "source_bundle_sha256": "0" * 64,
                "kind": "directory",
                "size_bytes": 0,
            }
        ],
        "candidates": [
            {
                "candidate_id": "sb-symlink",
                "source_bundle_ref": "inputs/bundle-dir",
                "source_bundle_sha256": "0" * 64,
                "nested_path_chain": ["linked/README.md"],
                "candidate_ref": "inputs/bundle-dir!linked/README.md",
                "artifact_class": "readme_candidate",
                "reason_codes": ["readme_candidate"],
                "confidence": "high",
                "state": "materialize_candidate",
                "materialized_ref": "",
                "limits": BundleInventoryLimits().as_record(),
                "next_action": "candidate is visible for the existing review-round intake boundary",
                "archive_depth": 0,
            }
        ],
        "skipped_entries": [],
        "summary": {},
    }
    write_submission_bundle_inventory(round_dir=round_dir, payload=payload)

    try:
        materialize_submission_bundle_candidate(
            case_id="case-a",
            round_id="round-a",
            round_dir=round_dir,
            candidate_id="sb-symlink",
            generated_at="2026-05-19T12:01:00Z",
        )
    except ValueError as exc:
        assert "symlink" in str(exc)
    else:
        raise AssertionError("directory symlink parent was materialized")


def test_materialization_preserves_ambiguous_candidates_until_explicitly_allowed(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    bundle = round_dir / "inputs" / "ambiguous.zip"
    with zipfile.ZipFile(bundle, "w") as handle:
        handle.writestr("one/README.md", "# one\n")
        handle.writestr("two/README.md", "# two\n")
    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/ambiguous.zip"],
        producer="scripts/review-round-start",
        generated_at="2026-05-19T12:00:00Z",
    )
    write_submission_bundle_inventory(round_dir=round_dir, payload=payload)
    candidate_id = candidate_by_class(payload, "readme_candidate")[0]["candidate_id"]

    try:
        materialize_submission_bundle_candidate(
            case_id="case-a",
            round_id="round-a",
            round_dir=round_dir,
            candidate_id=candidate_id,
            generated_at="2026-05-19T12:01:00Z",
        )
    except ValueError as exc:
        assert "--allow-ambiguous" in str(exc)
    else:
        raise AssertionError("ambiguous candidate was materialized without explicit selection")

    result = materialize_submission_bundle_candidate(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        candidate_id=candidate_id,
        allow_ambiguous=True,
        generated_at="2026-05-19T12:01:00Z",
    )
    assert (round_dir / result.materialized_ref).is_file()


def test_materialization_rejects_diagnostic_inventory_owner(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    bundle = round_dir / "inputs" / "diagnostic.zip"
    with zipfile.ZipFile(bundle, "w") as handle:
        handle.writestr("README.md", "# diagnostic\n")
    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/diagnostic.zip"],
        generated_at="2026-05-19T12:00:00Z",
    )
    write_submission_bundle_inventory(round_dir=round_dir, payload=payload)
    candidate_id = candidate_by_class(payload, "readme_candidate")[0]["candidate_id"]

    try:
        materialize_submission_bundle_candidate(
            case_id="case-a",
            round_id="round-a",
            round_dir=round_dir,
            candidate_id=candidate_id,
            generated_at="2026-05-19T12:01:00Z",
        )
    except ValueError as exc:
        assert "review-round-start" in str(exc)
    else:
        raise AssertionError("diagnostic inventory was accepted for materialization")
