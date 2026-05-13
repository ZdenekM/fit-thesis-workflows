import ast
import io
import json
import tarfile
import tomllib
import zipfile
from collections.abc import Iterator
from pathlib import Path

from thesis_review_workflow import agent_coverage, agent_profiles, code_workspace
from thesis_review_workflow.artifact_registry import (
    closeout_independent_review_required_paths,
    final_output_paths,
    known_output_labels,
    opponent_final_output_paths,
    output_defaults,
)
from thesis_review_workflow.case_doctor_summary import FINAL_OUTPUTS, KNOWN_OUTPUTS
from thesis_review_workflow.cli.package_workflow_tools import (
    launcher_listing_lines,
    workflow_tool_names_from_peek_payload,
)
from thesis_review_workflow.commands import WORKFLOW_COMMAND_MODULES
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.theses_similarity import (
    THESES_SIMILARITY_REPORT_REL,
    THESES_SIMILARITY_REVIEW_APPROVAL_REL,
    THESES_SIMILARITY_REVIEW_REL,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def build_tree(path: str) -> ast.Module:
    return ast.parse((REPO_ROOT / path).read_text(encoding="utf-8"))


def call_nodes(tree: ast.Module, name: str) -> Iterator[ast.Call]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name:
            yield node


def keyword_value(call: ast.Call, name: str) -> ast.expr:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    raise AssertionError(f"Missing {name} keyword")


def literal_keyword(call: ast.Call, name: str):
    return ast.literal_eval(keyword_value(call, name))


def assignment_literal(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"Missing {name} assignment")


def name_keyword(call: ast.Call, name: str) -> str:
    value = keyword_value(call, name)
    if not isinstance(value, ast.Name):
        raise AssertionError(f"{name} keyword should reference a name")
    return value.id


def scripts_shell_sources() -> set[str]:
    tree = build_tree("scripts/BUILD")
    [call] = list(call_nodes(tree, "shell_sources"))
    return set(literal_keyword(call, "sources"))


def workflow_pex_targets() -> dict[str, dict[str, str]]:
    tree = build_tree("scripts/BUILD")
    targets: dict[str, dict[str, str]] = {}
    for call in call_nodes(tree, "pex_binary"):
        tags = set(literal_keyword(call, "tags"))
        if "workflow-tool" not in tags:
            continue
        output_path = literal_keyword(call, "output_path")
        tool_name = Path(output_path).name
        targets[tool_name] = {
            "dependencies": name_keyword(call, "dependencies"),
            "entry_point": literal_keyword(call, "entry_point"),
            "output_path": output_path,
        }
    return targets


def cli_python_sources() -> dict[str, str]:
    tree = build_tree("src/thesis_review_workflow/cli/BUILD")
    return {
        literal_keyword(call, "name"): literal_keyword(call, "source") for call in call_nodes(tree, "python_source")
    }


def workflow_runtime_deps() -> set[str]:
    tree = build_tree("scripts/BUILD")
    return set(assignment_literal(tree, "WORKFLOW_CLI_RUNTIME_DEPS"))


def test_packaged_tool_listing_labels_extensionless_launchers_as_posix_only() -> None:
    lines = launcher_listing_lines(["init-review-manifest"])

    assert lines == [
        "Packaged tools:",
        "- POSIX launcher: dist/workflow-tools/bin/init-review-manifest",
        "  Windows cmd: dist\\workflow-tools\\bin\\init-review-manifest.cmd",
        "  PowerShell: .\\dist\\workflow-tools\\bin\\init-review-manifest.ps1",
    ]


def codex_agent_config() -> dict[str, object]:
    return tomllib.loads((REPO_ROOT / ".codex/config.toml").read_text(encoding="utf-8"))


def shell_loop_body(text: str, header: str) -> str:
    start = text.index(header)
    body_start = text.index("\n", start) + 1
    end = text.index("\ndone", body_start)
    return text[body_start:end]


def test_safe_relative_rejects_absolute_and_parent_paths() -> None:
    assert agent_coverage.is_safe_relative("outputs/oponent_podklady_revidovane.md")
    assert not agent_coverage.is_safe_relative("/tmp/oponent_podklady_revidovane.md")
    assert not agent_coverage.is_safe_relative("../outputs/oponent_podklady_revidovane.md")
    assert not agent_coverage.is_safe_relative("outputs\\oponent_podklady_revidovane.md")
    assert not agent_coverage.is_safe_relative("C:/Users/me/oponent_podklady_revidovane.md")
    assert not agent_coverage.is_safe_relative("//server/share/oponent_podklady_revidovane.md")
    assert not agent_coverage.is_safe_relative("outputs/./oponent_podklady_revidovane.md")


def test_shared_round_relative_path_validation_is_windows_aware() -> None:
    assert is_safe_round_relative_path("work/review_manifest.json")
    for value in [
        "",
        ".",
        "./work/review_manifest.json",
        "../work/review_manifest.json",
        "/tmp/review_manifest.json",
        "C:/Users/me/review_manifest.json",
        "C:relative/review_manifest.json",
        "//server/share/review_manifest.json",
        "work//review_manifest.json",
        "work\\review_manifest.json",
    ]:
        assert not is_safe_round_relative_path(value)


def test_archive_suffix_handles_compound_tar_suffixes() -> None:
    assert code_workspace.archive_suffix(Path("code.tar.gz")) == ".tar.gz"
    assert code_workspace.archive_suffix(Path("code.zip")) == ".zip"
    assert code_workspace.archive_suffix(Path("code.7z")) == ".7z"


def test_probe_archive_detects_python_project_zip(tmp_path: Path) -> None:
    archive = tmp_path / "submitted-code.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("project/pyproject.toml", "[project]\nname = 'demo'\n")
        handle.writestr("project/src/main.py", "print('demo')\n")

    probe = code_workspace.probe_archive(archive)

    assert probe.code_like
    assert probe.possible_code
    assert probe.entries_seen == 2


def test_extract_zip_reports_case_insensitive_path_collisions(tmp_path: Path) -> None:
    archive = tmp_path / "code.zip"
    target = tmp_path / "out"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("project/src/Foo.py", "print('upper')\n")
        handle.writestr("project/src/foo.py", "print('lower')\n")

    extracted, skipped = code_workspace.extract_zip(archive, target)

    assert extracted == 1
    assert (target / "project/src/Foo.py").is_file()
    assert not (target / "project/src/foo.py").exists()
    assert any("case-insensitive path collision with project/src/Foo.py" in item for item in skipped)


def test_extract_tar_reports_case_insensitive_path_collisions(tmp_path: Path) -> None:
    archive = tmp_path / "code.tar"
    target = tmp_path / "out"
    with tarfile.open(archive, "w") as handle:
        for name, text in [
            ("project/src/Foo.py", "print('upper')\n"),
            ("project/src/foo.py", "print('lower')\n"),
        ]:
            payload = text.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            handle.addfile(info, io.BytesIO(payload))

    extracted, skipped = code_workspace.extract_tar(archive, target)

    assert extracted == 1
    assert (target / "project/src/Foo.py").is_file()
    assert not (target / "project/src/foo.py").exists()
    assert any("case-insensitive path collision with project/src/Foo.py" in item for item in skipped)


def test_safe_copy_input_dir_reports_case_insensitive_path_collisions(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "out"
    source.mkdir()
    (source / "README.md").write_text("upper\n", encoding="utf-8")
    (source / "readme.md").write_text("lower\n", encoding="utf-8")
    if len(list(source.iterdir())) < 2:
        return

    copied, skipped = code_workspace.safe_copy_input_dir(source, target)

    assert copied == 1
    assert (target / "README.md").is_file()
    assert not (target / "readme.md").exists()
    assert any("case-insensitive path collision with README.md" in item for item in skipped)


def test_workspace_target_registry_reports_case_insensitive_collisions(tmp_path: Path) -> None:
    registry = code_workspace.CaseInsensitivePathRegistry(tmp_path)

    assert registry.register(tmp_path / "Code", label="inputs/Code.zip", kind="directory") is None
    collision = registry.register(tmp_path / "code", label="inputs/code.zip", kind="directory")

    assert collision is not None
    assert "case-insensitive path collision with Code" in collision


def test_workspace_manifest_exposes_reuse_fingerprints_without_rereading_inputs(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    workspace = round_dir / "work" / "code"
    workspace.mkdir(parents=True)
    code_workspace.write_workspace_manifest(
        workspace,
        {
            "sources": {
                "inputs/code.zip": {
                    "target": "work/code/code",
                    "fingerprint": "sha256:" + "a" * 64 + ";size:12",
                    "prepared_at": "2026-05-13T12:00:00Z",
                },
                "../unsafe.zip": {
                    "target": "work/code/unsafe",
                    "fingerprint": "sha256:" + "b" * 64 + ";size:12",
                },
            }
        },
    )

    records = code_workspace.workspace_source_fingerprint_records(round_dir)
    fingerprints = code_workspace.workspace_source_fingerprints(round_dir)

    assert len(records) == 1
    assert records[0]["source_ref"] == "inputs/code.zip"
    assert records[0]["target_ref"] == "work/code/code"
    assert records[0]["source_class"] == "submitted_code"
    assert records[0]["target_class"] == "code_workspace"
    assert len(fingerprints) == 2
    assert {item.source_ref for item in fingerprints} == {"inputs/code.zip", "work/code/code"}
    assert all(item.comparable for item in fingerprints)


def test_agent_coverage_code_trigger_uses_archive_entries_before_filename(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    final_output = round_dir / "outputs" / "feedback_student.md"
    final_output.parent.mkdir(parents=True)
    final_output.write_text("# Feedback\n", encoding="utf-8")
    inputs = round_dir / "inputs"
    inputs.mkdir(parents=True)

    code_named_thesis_archive = inputs / "code.zip"
    with zipfile.ZipFile(code_named_thesis_archive, "w") as handle:
        handle.writestr("thesis/main.tex", "\\section{Synthetic}\n")
    manifest = {"inputs": [{"path": "inputs/code.zip", "kind": "archive"}], "artifacts": []}

    specs = agent_coverage.inferred_role_specs(round_dir, manifest)

    assert "code_consistency" not in specs
    assert "code_quality" not in specs

    actual_code_archive = inputs / "thesis-overleaf.zip"
    with zipfile.ZipFile(actual_code_archive, "w") as handle:
        handle.writestr("project/pyproject.toml", "[project]\nname = 'synthetic'\n")
        handle.writestr("project/src/main.py", "print('synthetic')\n")
    manifest["inputs"] = [{"path": "inputs/thesis-overleaf.zip", "kind": "archive"}]

    specs = agent_coverage.inferred_role_specs(round_dir, manifest)

    assert specs["code_consistency"].trigger == "code evidence is available and feeds a final/synthesis artifact"
    assert specs["code_quality"].trigger == "code evidence is available and feeds a final/synthesis artifact"


def make_reuse_aware_code_round(tmp_path: Path, *, consistency_status: str = "unchanged_reusable") -> tuple[Path, dict]:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    final_output = round_dir / "outputs" / "feedback_student.md"
    code_consistency = round_dir / "outputs" / "code_consistency.md"
    code_quality = round_dir / "outputs" / "code_quality_review.md"
    final_output.parent.mkdir(parents=True)
    final_output.write_text("# Feedback\n", encoding="utf-8")
    code_consistency.write_text("# Code Consistency\n", encoding="utf-8")
    code_quality.write_text("# Code Quality\n", encoding="utf-8")
    role_source_paths = {
        "assignment": "inputs/assignment.md",
        "thesis_pdf": "inputs/thesis.pdf",
        "thesis_extract": "extracted/thesis.txt",
        "thesis_source": "inputs/thesis-source.zip",
        "submitted_code": "inputs/code.zip",
        "code_workspace": "work/code/app.py",
        "github_snapshot": "inputs/github-snapshot.json",
        "readme_config": "work/code/README.md",
        "experiment_result": "inputs/results.csv",
        "operator_note": "notes/operator.md",
    }
    for source_class, rel_path in role_source_paths.items():
        path = round_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if rel_path.endswith(".zip"):
            with zipfile.ZipFile(path, "w") as handle:
                handle.writestr("project/src/main.py", f"# synthetic {source_class}\n")
        else:
            path.write_text(f"synthetic {source_class}\n", encoding="utf-8")
    source_records = [
        {
            "source_ref": rel_path,
            "source_class": source_class,
            "sha256": agent_coverage.sha256_file(round_dir / rel_path),
            "available": True,
            "state": "comparable",
            "schema_version": "test-v1",
            "producer": "test",
        }
        for source_class, rel_path in role_source_paths.items()
    ]
    hashes_by_class = {
        str(record["source_class"]): {str(record["source_ref"]): str(record["sha256"])} for record in source_records
    }
    code_consistency_classes = [
        "assignment",
        "thesis_pdf",
        "thesis_extract",
        "thesis_source",
        "submitted_code",
        "code_workspace",
        "github_snapshot",
        "readme_config",
        "experiment_result",
        "operator_note",
    ]
    code_quality_classes = [
        "submitted_code",
        "code_workspace",
        "github_snapshot",
        "readme_config",
        "experiment_result",
        "operator_note",
    ]
    consistency_sources = {
        ref: digest
        for source_class in code_consistency_classes
        for ref, digest in hashes_by_class[source_class].items()
    }
    quality_sources = {
        ref: digest for source_class in code_quality_classes for ref, digest in hashes_by_class[source_class].items()
    }
    final_hash = agent_coverage.sha256_file(final_output)
    consistency_hash = agent_coverage.sha256_file(code_consistency)
    quality_hash = agent_coverage.sha256_file(code_quality)
    manifest = {
        "inputs": [{"path": "inputs/code.zip", "kind": "archive"}],
        "supporting_work_artifacts": [],
        "artifacts": [
            {
                "path": "outputs/feedback_student.md",
                "artifact_sha256": final_hash,
                "skills": ["thesis-supervisor-feedback-review"],
                "generated_by": [{"role": "thesis-supervisor-feedback-review", "agent": "reviewer-a"}],
                "independent_review": {
                    "reviewer_role": "thesis-supervisor-feedback-review",
                    "reviewer_agent": "reviewer-b",
                    "reviewed_hash": final_hash,
                },
            },
            {
                "path": "outputs/code_consistency.md",
                "artifact_sha256": consistency_hash,
                "skills": ["thesis-code-consistency"],
                "generated_by": [{"role": "thesis-code-consistency", "agent": "code-consistency-a"}],
                "independent_review": {
                    "reviewer_role": "thesis-code-consistency",
                    "reviewer_agent": "code-consistency-reviewer",
                    "reviewed_hash": consistency_hash,
                },
            },
            {
                "path": "outputs/code_quality_review.md",
                "artifact_sha256": quality_hash,
                "skills": ["thesis-code-quality-review"],
                "generated_by": [{"role": "thesis-code-quality-review", "agent": "code-quality-a"}],
                "independent_review": {
                    "reviewer_role": "thesis-code-quality-review",
                    "reviewer_agent": "code-quality-reviewer",
                    "reviewed_hash": quality_hash,
                },
            },
        ],
    }
    status_is_reusable = consistency_status == "unchanged_reusable"
    consistency_decision = {
        "artifact_role": "code_consistency",
        "status": consistency_status,
        "fresh_semantic_review_required": not status_is_reusable,
        "coverage_satisfied_by": "current_reviewed_artifact" if status_is_reusable else "not_satisfied",
        "next_action": "reuse_existing_review" if status_is_reusable else "delta_review",
        "relevant_source_classes": code_consistency_classes,
        "source_sha256": consistency_sources,
        "unchanged_refs": (
            sorted(set(consistency_sources) - {"extracted/thesis.txt"})
            if not status_is_reusable
            else sorted(consistency_sources)
        ),
        "changed_refs": ["extracted/thesis.txt"] if not status_is_reusable else [],
        "added_refs": [],
        "removed_refs": [],
        "missing_current_refs": [],
        "not_comparable_refs": [],
        "missing_current_source_classes": [],
        "missing_prior_source_classes": [],
        "reasons": (
            ["role-relevant source changed"]
            if not status_is_reusable
            else ["role-relevant sources unchanged and reviewed coverage is current"]
        ),
    }
    quality_decision = {
        "artifact_role": "code_quality",
        "status": "unchanged_reusable",
        "fresh_semantic_review_required": False,
        "coverage_satisfied_by": "current_reviewed_artifact",
        "next_action": "reuse_existing_review",
        "relevant_source_classes": code_quality_classes,
        "source_sha256": quality_sources,
        "unchanged_refs": sorted(quality_sources),
        "changed_refs": [],
        "added_refs": [],
        "removed_refs": [],
        "missing_current_refs": [],
        "not_comparable_refs": [],
        "missing_current_source_classes": [],
        "missing_prior_source_classes": [],
        "reasons": ["role-relevant sources unchanged and reviewed coverage is current"],
    }
    reuse_index = {
        "schema_version": agent_coverage.REUSE_INDEX_SCHEMA_VERSION,
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-13T00:00:00Z",
        "producer": "update-round-reuse-index",
        "current_source_fingerprints": source_records,
        "previous_round_candidates": [],
        "decisions": [consistency_decision, quality_decision],
        "limitations": [],
    }
    reuse_path = round_dir / agent_coverage.REUSE_INDEX_REL
    reuse_path.parent.mkdir(parents=True)
    reuse_path.write_text(json.dumps(reuse_index, indent=2) + "\n", encoding="utf-8")
    return round_dir, manifest


def test_agent_coverage_accepts_reuse_backed_code_roles_without_fresh_review(tmp_path: Path) -> None:
    round_dir, manifest = make_reuse_aware_code_round(tmp_path)

    coverage = agent_coverage.build_coverage("case-a", "round-a", round_dir, manifest)
    errors, warnings = agent_coverage.validate_coverage(coverage, manifest, "case-a", "round-a", round_dir)

    assert coverage is not None
    roles = {item["role"]: item for item in coverage["roles"]}
    assert roles["code_consistency"]["fresh_review_required"] is False
    assert roles["code_consistency"]["coverage_satisfied_by"] == "current_reviewed_artifact"
    assert roles["code_quality"]["fresh_review_required"] is False
    assert roles["code_quality"]["coverage_satisfied_by"] == "current_reviewed_artifact"
    assert errors == []
    assert warnings == []


def test_agent_coverage_rejects_incomplete_reuse_source_hashes(tmp_path: Path) -> None:
    round_dir, manifest = make_reuse_aware_code_round(tmp_path)
    reuse_path = round_dir / agent_coverage.REUSE_INDEX_REL
    reuse_index = json.loads(reuse_path.read_text(encoding="utf-8"))
    consistency = next(item for item in reuse_index["decisions"] if item["artifact_role"] == "code_consistency")
    consistency["source_sha256"].pop("extracted/thesis.txt")
    reuse_path.write_text(json.dumps(reuse_index, indent=2) + "\n", encoding="utf-8")

    coverage = agent_coverage.build_coverage("case-a", "round-a", round_dir, manifest)
    errors, _ = agent_coverage.validate_coverage(coverage, manifest, "case-a", "round-a", round_dir)

    assert any("source_sha256 must match current role source fingerprints" in error for error in errors)


def test_agent_coverage_keeps_changed_code_consistency_claims_on_delta_path(tmp_path: Path) -> None:
    round_dir, manifest = make_reuse_aware_code_round(tmp_path, consistency_status="changed_delta_required")

    coverage = agent_coverage.build_coverage("case-a", "round-a", round_dir, manifest)
    assert coverage is not None
    roles = {item["role"]: item for item in coverage["roles"]}
    assert roles["code_consistency"]["fresh_review_required"] is True
    assert roles["code_consistency"]["coverage_satisfied_by"] == "fresh_role_review"
    assert roles["code_consistency"]["reuse_status"] == "changed_delta_required"
    roles["code_consistency"]["fresh_review_required"] = False
    roles["code_consistency"]["coverage_satisfied_by"] = "current_reviewed_artifact"

    errors, _ = agent_coverage.validate_coverage(coverage, manifest, "case-a", "round-a", round_dir)

    assert any("reuse decision must be unchanged_reusable" in error for error in errors)


def test_agent_coverage_uses_supporting_quantitative_claims_artifact(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    final_output = round_dir / "outputs" / "feedback_student.md"
    thesis_text = round_dir / "extracted" / "thesis.txt"
    quantitative = round_dir / "work" / "quantitative_claims.json"
    final_output.parent.mkdir(parents=True)
    thesis_text.parent.mkdir(parents=True)
    quantitative.parent.mkdir(parents=True)
    final_output.write_text("# Feedback\n", encoding="utf-8")
    thesis_text.write_text("Metric claim.\n", encoding="utf-8")
    quantitative.write_text(
        json.dumps(
            {
                "schema_version": "quantitative-claims-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "generated_at": "2026-05-11T00:00:00Z",
                "producer_type": "agent",
                "producer_role": "quantitative-claims-reviewer",
                "producer_agent": "agent-q",
                "authorization_note": "Authorized in current request.",
                "source_refs": ["extracted/thesis.txt"],
                "claims": [
                    {
                        "claim_id": "Q1",
                        "summary": "Reported metric needs context.",
                        "kind": "metric",
                        "status": "needs_context",
                        "unit": "not_verifiable",
                        "baseline_status": "missing",
                        "practical_context": "weak",
                        "scale_context": "Metric scale is not verifiable from the available evidence.",
                        "sample_context": "Sample size is not verifiable from the available evidence.",
                        "practical_magnitude": "Practical magnitude is not verifiable from the available evidence.",
                        "overclaim_risk": "moderate",
                        "reproducibility_refs": [],
                        "evidence_refs": ["extracted/thesis.txt"],
                        "requires_reviewer_verification": True,
                    }
                ],
                "limitations": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    final_hash = agent_coverage.sha256_file(final_output)
    quantitative_hash = agent_coverage.sha256_file(quantitative)
    manifest = {
        "inputs": [],
        "supporting_work_artifacts": [
            {
                "path": "work/quantitative_claims.json",
                "kind": "structured_data",
                "artifact_sha256": quantitative_hash,
                "schema_version": "quantitative-claims-v1",
                "producer_role": "quantitative-claims-reviewer",
                "producer_agent": "agent-q",
            }
        ],
        "artifacts": [
            {
                "path": "outputs/feedback_student.md",
                "artifact_sha256": final_hash,
                "skills": ["thesis-supervisor-feedback-review"],
                "generated_by": [{"role": "thesis-supervisor-feedback-review", "agent": "reviewer-a"}],
                "independent_review": {
                    "reviewer_role": "thesis-supervisor-feedback-review",
                    "reviewer_agent": "reviewer-b",
                    "reviewed_hash": final_hash,
                },
            }
        ],
    }

    specs = agent_coverage.inferred_role_specs(round_dir, manifest)
    coverage = agent_coverage.build_coverage("case-a", "round-a", round_dir, manifest)
    errors, warnings = agent_coverage.validate_coverage(coverage, manifest, "case-a", "round-a", round_dir)

    assert specs["quantitative_claims"].skill == "thesis-quantitative-claims-review"
    assert coverage is not None
    role = next(item for item in coverage["roles"] if item["role"] == "quantitative_claims")
    assert role["output_evidence"] == ["work/quantitative_claims.json"]
    assert role["generator_role"] == "quantitative-claims-reviewer"
    assert role["generator_agent"] == "agent-q"
    assert errors == []
    assert warnings == []

    human_manifest = dict(manifest)
    supporting_records = manifest["supporting_work_artifacts"]
    assert isinstance(supporting_records, list)
    supporting_record = supporting_records[0]
    assert isinstance(supporting_record, dict)
    human_supporting = [dict(supporting_record)]
    human_supporting[0]["producer_type"] = "human"
    human_supporting[0]["producer_agent"] = None
    human_manifest["supporting_work_artifacts"] = human_supporting
    human_coverage = agent_coverage.build_coverage("case-a", "round-a", round_dir, human_manifest)
    assert human_coverage is not None
    human_errors, human_warnings = agent_coverage.validate_coverage(
        human_coverage, human_manifest, "case-a", "round-a", round_dir
    )
    human_role = next(item for item in human_coverage["roles"] if item["role"] == "quantitative_claims")

    assert human_role["generator_agent"] == "human_reviewer"
    assert human_errors == []
    assert human_warnings == []


def test_agent_coverage_requires_theses_similarity_review_for_final_outputs(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    final_output = round_dir / "outputs" / "feedback_student.md"
    theses_review = round_dir / THESES_SIMILARITY_REVIEW_REL
    report = round_dir / THESES_SIMILARITY_REPORT_REL
    final_output.parent.mkdir(parents=True)
    report.parent.mkdir(parents=True)
    final_output.write_text("# Feedback\n", encoding="utf-8")
    theses_review.write_text("# Theses.cz Similarity Review\n", encoding="utf-8")
    report.write_bytes(b"%PDF synthetic\n")
    final_hash = agent_coverage.sha256_file(final_output)
    theses_hash = agent_coverage.sha256_file(theses_review)
    manifest = {
        "inputs": [{"path": THESES_SIMILARITY_REPORT_REL, "kind": "pdf"}],
        "supporting_work_artifacts": [],
        "artifacts": [
            {
                "path": "outputs/feedback_student.md",
                "artifact_sha256": final_hash,
                "skills": ["thesis-supervisor-feedback-review"],
                "generated_by": [{"role": "thesis-supervisor-feedback-review", "agent": "reviewer-a"}],
                "independent_review": {
                    "reviewer_role": "thesis-supervisor-feedback-review",
                    "reviewer_agent": "reviewer-b",
                    "reviewed_hash": final_hash,
                },
            },
            {
                "path": THESES_SIMILARITY_REVIEW_REL,
                "artifact_sha256": theses_hash,
                "skills": ["thesis-theses-similarity-review"],
                "generated_by": [{"role": "thesis-theses-similarity-review", "agent": "agent-sim"}],
                "independent_review": {"status": "not_recorded"},
            },
        ],
    }

    specs = agent_coverage.inferred_role_specs(round_dir, manifest)
    coverage = agent_coverage.build_coverage("case-a", "round-a", round_dir, manifest)
    errors, warnings = agent_coverage.validate_coverage(coverage, manifest, "case-a", "round-a", round_dir)

    assert specs["theses_similarity"].skill == "thesis-theses-similarity-review"
    assert coverage is not None
    role = next(item for item in coverage["roles"] if item["role"] == "theses_similarity")
    assert role["output_evidence"] == [THESES_SIMILARITY_REVIEW_REL]
    assert role["generator_role"] == "thesis-theses-similarity-review"
    assert role["generator_agent"] == "agent-sim"
    assert errors == []
    assert warnings == []


def test_agent_coverage_ignores_orphan_theses_similarity_approval_record(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    final_output = round_dir / "outputs" / "feedback_student.md"
    approval = round_dir / THESES_SIMILARITY_REVIEW_APPROVAL_REL
    final_output.parent.mkdir(parents=True)
    approval.parent.mkdir(parents=True)
    final_output.write_text("# Feedback\n", encoding="utf-8")
    approval.write_text("{}\n", encoding="utf-8")
    manifest: dict[str, object] = {"inputs": [], "supporting_work_artifacts": [], "artifacts": []}

    specs = agent_coverage.inferred_role_specs(round_dir, manifest)

    assert "theses_similarity" not in specs


def test_workflow_tool_pex_targets_match_command_module_map() -> None:
    pex_targets = workflow_pex_targets()

    assert set(pex_targets) == set(WORKFLOW_COMMAND_MODULES)
    for tool_name, module in WORKFLOW_COMMAND_MODULES.items():
        target = pex_targets[tool_name]
        assert target["dependencies"] == "WORKFLOW_CLI_RUNTIME_DEPS"
        assert target["entry_point"] == f"{module}:console_main"
        assert target["output_path"] == f"workflow-tools/pex/{tool_name}"


def test_output_artifact_registry_is_shared_by_manifest_and_case_doctor() -> None:
    assert KNOWN_OUTPUTS == known_output_labels()
    assert FINAL_OUTPUTS >= {
        "feedback_student.md",
        "oponent_podklady_revidovane.md",
        "feedback_k_posudku.md",
    }
    assert agent_coverage.FINAL_OUTPUTS == final_output_paths()
    assert agent_coverage.OPPONENT_FINAL_OUTPUTS == opponent_final_output_paths()
    assert output_defaults("outputs/pr_contribution_review.md") == (
        "pr_contribution_review",
        ["thesis-github-code-intake"],
        "internal_only",
    )
    assert output_defaults("outputs/demo_artifacts_review.md") == (
        "demo_artifacts_review",
        [],
        "internal_only",
    )
    assert closeout_independent_review_required_paths() == {
        "outputs/reference_report_comparison.md",
        "outputs/opponent_reading_packet.md",
    }


def test_codex_agent_profiles_register_tracked_configs() -> None:
    config = codex_agent_config()
    agents = config["agents"]
    assert isinstance(agents, dict)
    registry_profile_ids = {route.profile_id for route in agent_profiles.profile_routes() if route.profile_id}
    configured_profile_ids = {
        profile_id for profile_id, profile_config in agents.items() if isinstance(profile_config, dict)
    }

    assert configured_profile_ids
    assert configured_profile_ids == registry_profile_ids
    for profile in configured_profile_ids:
        profile_config = agents[profile]
        assert isinstance(profile_config, dict)
        config_file = profile_config["config_file"]
        assert isinstance(config_file, str)
        assert (REPO_ROOT / ".codex" / config_file).is_file()


def test_workflow_command_modules_have_sources_runtime_deps_and_wrappers() -> None:
    cli_sources = cli_python_sources()
    runtime_deps = workflow_runtime_deps()
    shell_sources = scripts_shell_sources()

    for tool_name, module in WORKFLOW_COMMAND_MODULES.items():
        module_name = module.rsplit(".", 1)[-1]
        assert cli_sources[module_name] == f"{module_name}.py"
        assert f"src/thesis_review_workflow/cli:{module_name}" in runtime_deps
        assert tool_name in shell_sources


def test_package_workflow_tools_is_bootstrap_not_packaged_workflow_tool() -> None:
    cli_sources = cli_python_sources()
    shell_sources = scripts_shell_sources()
    pex_targets = workflow_pex_targets()

    assert cli_sources["package_workflow_tools"] == "package_workflow_tools.py"
    assert "package-workflow-tools" in shell_sources
    assert "package-workflow-tools" not in WORKFLOW_COMMAND_MODULES
    assert "package-workflow-tools" not in pex_targets


def test_package_smoke_covers_generated_launchers_and_posix_runtime() -> None:
    smoke = (REPO_ROOT / "scripts/smoke-package-workflow-tools").read_text(encoding="utf-8")
    tool_loop = shell_loop_body(smoke, 'for tool_name in "${tool_names[@]}"; do')

    assert 'mapfile -t tool_names < <(find "$repo_root/dist/workflow-tools/pex"' in smoke
    assert 'launcher="$repo_root/dist/workflow-tools/bin/$tool_name"' in tool_loop
    assert 'cmd_launcher="$repo_root/dist/workflow-tools/bin/$tool_name.cmd"' in tool_loop
    assert 'ps_launcher="$repo_root/dist/workflow-tools/bin/$tool_name.ps1"' in tool_loop
    assert '[[ ! -x "$launcher" ]]' in tool_loop
    assert '[[ ! -f "$cmd_launcher" ]]' in tool_loop
    assert '[[ ! -f "$ps_launcher" ]]' in tool_loop
    assert 'grep -Fq "..\\\\pex\\\\$tool_name" "$cmd_launcher"' in tool_loop
    assert 'grep -Fq "..\\\\pex\\\\$tool_name" "$ps_launcher"' in tool_loop
    assert 'grep -Fq "Get-Command" "$ps_launcher"' in tool_loop
    assert '"$launcher" --help' in tool_loop
    assert "thesis_review_workflow.cli.package_workflow_tools" in smoke


def test_workflow_tool_peek_parser_enforces_packaging_output_contract() -> None:
    payload = json.dumps(
        [
            {
                "address": "scripts:case_doctor_tool",
                "target_type": "pex_binary",
                "output_path": "workflow-tools/pex/case-doctor",
            },
            {
                "address": "src/thesis_review_workflow:lib",
                "target_type": "python_sources",
            },
            {
                "address": "scripts:check_tooling_tool",
                "target_type": "pex_binary",
                "output_path": "workflow-tools/pex/check-tooling",
            },
        ]
    )

    assert workflow_tool_names_from_peek_payload(payload) == ["case-doctor", "check-tooling"]


def test_workflow_tool_peek_parser_rejects_invalid_packaging_output_contract() -> None:
    missing_output = json.dumps([{"address": "scripts:bad_tool", "target_type": "pex_binary"}])
    wrong_directory = json.dumps(
        [
            {
                "address": "scripts:bad_tool",
                "target_type": "pex_binary",
                "output_path": "wrong-dir/bad-tool",
            }
        ]
    )
    duplicate_output = json.dumps(
        [
            {
                "address": "scripts:a_tool",
                "target_type": "pex_binary",
                "output_path": "workflow-tools/pex/dup-tool",
            },
            {
                "address": "scripts:b_tool",
                "target_type": "pex_binary",
                "output_path": "workflow-tools/pex/dup-tool",
            },
        ]
    )

    for payload in (missing_output, wrong_directory, duplicate_output):
        try:
            workflow_tool_names_from_peek_payload(payload)
        except RuntimeError:
            continue
        raise AssertionError("invalid workflow-tool payload was accepted")
