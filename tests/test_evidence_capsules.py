from thesis_review_workflow.evidence_capsules import (
    EVIDENCE_CAPSULE_SCHEMA,
    EVIDENCE_CAPSULES_REL,
    source_sha256_for_refs,
    validate_evidence_capsules_payload,
)


def assert_raises_value_error(message_fragment, factory):
    try:
        factory()
    except ValueError as exc:
        assert message_fragment in str(exc)
        return
    raise AssertionError("expected ValueError")


def valid_capsules(round_dir):
    thesis = round_dir / "extracted" / "thesis.txt"
    thesis.parent.mkdir(parents=True, exist_ok=True)
    thesis.write_text("Section 1 says the prototype supports import.\n", encoding="utf-8")
    source_hashes = source_sha256_for_refs(round_dir, ["extracted/thesis.txt"])
    return {
        "schema_version": EVIDENCE_CAPSULE_SCHEMA,
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-13T12:00:00Z",
        "producer_type": "agent",
        "producer_role": "text-structure-reader",
        "producer_agent": "agent-a",
        "source_refs": ["extracted/thesis.txt"],
        "source_sha256": source_hashes,
        "capsules": [
            {
                "capsule_id": "cap-1",
                "source_ref": "extracted/thesis.txt",
                "source_sha256": source_hashes["extracted/thesis.txt"],
                "anchor_refs": [
                    {
                        "anchor_id": "a1",
                        "source_ref": "extracted/thesis.txt",
                        "anchor_type": "section",
                        "locator": "Section 1",
                    }
                ],
                "summary": "The section describes the import capability.",
                "extracted_facts": [
                    {
                        "fact_id": "f1",
                        "summary": "Prototype import is described.",
                        "anchor_refs": ["a1"],
                    }
                ],
                "candidate_claims": [
                    {
                        "claim_id": "c1",
                        "claim_text": "Prototype supports import.",
                        "anchor_refs": ["a1"],
                    }
                ],
                "uncertainties": [],
                "limitations": [],
                "open_raw_source_if": ["p0_p1_verification", "reviewer_challenge"],
            }
        ],
        "limitations": [],
    }


def test_valid_evidence_capsules_are_hash_bound(tmp_path):
    round_dir = tmp_path / "round-a"
    payload = valid_capsules(round_dir)

    errors = validate_evidence_capsules_payload(
        payload,
        EVIDENCE_CAPSULES_REL,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == []


def test_evidence_capsules_reject_stale_source_hash(tmp_path):
    round_dir = tmp_path / "round-a"
    payload = valid_capsules(round_dir)
    (round_dir / "extracted" / "thesis.txt").write_text("Changed.\n", encoding="utf-8")

    errors = validate_evidence_capsules_payload(payload, EVIDENCE_CAPSULES_REL, round_dir=round_dir)

    assert any("source_sha256 is stale for extracted/thesis.txt" in error for error in errors)


def test_evidence_capsules_reject_undefined_anchor_and_unknown_raw_source_trigger(tmp_path):
    round_dir = tmp_path / "round-a"
    payload = valid_capsules(round_dir)
    capsule = payload["capsules"][0]
    capsule["extracted_facts"][0]["anchor_refs"] = ["missing"]
    capsule["open_raw_source_if"] = ["free_text_reason"]

    errors = validate_evidence_capsules_payload(payload, EVIDENCE_CAPSULES_REL, round_dir=round_dir)

    assert any("anchor ref is not defined" in error for error in errors)
    assert any("open_raw_source_if item 1" in error for error in errors)


def test_evidence_capsules_require_nested_source_refs_in_top_level_hash_inventory(tmp_path):
    round_dir = tmp_path / "round-a"
    payload = valid_capsules(round_dir)
    appendix = round_dir / "extracted" / "appendix.txt"
    appendix.write_text("Appendix anchor.\n", encoding="utf-8")
    payload["capsules"][0]["anchor_refs"][0]["source_ref"] = "extracted/appendix.txt"

    errors = validate_evidence_capsules_payload(payload, EVIDENCE_CAPSULES_REL, round_dir=round_dir)

    assert any("ref must be listed in top-level source_refs" in error for error in errors)


def test_evidence_capsules_reject_stale_hash_for_nested_anchor_source(tmp_path):
    round_dir = tmp_path / "round-a"
    payload = valid_capsules(round_dir)
    appendix = round_dir / "extracted" / "appendix.txt"
    appendix.write_text("Appendix anchor.\n", encoding="utf-8")
    hashes = source_sha256_for_refs(round_dir, ["extracted/thesis.txt", "extracted/appendix.txt"])
    payload["source_refs"].append("extracted/appendix.txt")
    payload["source_sha256"] = hashes
    payload["capsules"][0]["anchor_refs"][0]["source_ref"] = "extracted/appendix.txt"
    appendix.write_text("Changed appendix.\n", encoding="utf-8")

    errors = validate_evidence_capsules_payload(payload, EVIDENCE_CAPSULES_REL, round_dir=round_dir)

    assert any("source_sha256 is stale for extracted/appendix.txt" in error for error in errors)


def test_source_hash_helper_rejects_unsafe_or_missing_refs(tmp_path):
    round_dir = tmp_path / "round-a"

    assert_raises_value_error("safe round-relative", lambda: source_sha256_for_refs(round_dir, ["../private.txt"]))
    assert_raises_value_error("existing file", lambda: source_sha256_for_refs(round_dir, ["extracted/missing.txt"]))
