import tomllib
from pathlib import Path

from thesis_review_workflow import agent_coverage, agent_profiles, opponent_packets, review_profiles, supervisor_packets
from thesis_review_workflow.paths import is_safe_round_relative_path

REPO_ROOT = Path(__file__).resolve().parents[1]


def codex_agent_config_entries() -> dict[str, dict[str, object]]:
    config = tomllib.loads((REPO_ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
    agents = config["agents"]
    assert isinstance(agents, dict)
    return {
        profile_id: profile_config
        for profile_id, profile_config in agents.items()
        if isinstance(profile_config, dict) and "config_file" in profile_config
    }


def load_profile_config(config_file: str) -> dict[str, object]:
    return tomllib.loads((REPO_ROOT / ".codex" / config_file).read_text(encoding="utf-8"))


def test_agent_profile_registry_covers_every_repo_local_skill() -> None:
    skill_ids = agent_profiles.repo_local_skill_ids(REPO_ROOT)
    route_skill_ids = set(agent_profiles.routes_by_skill_id())

    assert skill_ids
    assert route_skill_ids == skill_ids


def test_agent_profile_registry_has_reviewable_route_shape() -> None:
    profile_ids = {route.profile_id for route in agent_profiles.profile_routes()}

    for route in agent_profiles.agent_profile_routes():
        assert route.role_source
        assert route.status in {"profile", "parent-owned", "deferred"}
        assert route.role_kind in {
            "generator",
            "evidence-producer",
            "standalone-evidence-reviewer",
            "final-reviewer",
            "calibrator",
            "parent-orchestration",
        }

        if route.status == "profile":
            assert route.profile_id
            assert route.profile_id in profile_ids
            assert route.sandbox_mode in {"read-only", "workspace-write"}
        else:
            assert route.profile_id is None

        if route.sandbox_mode == "workspace-write":
            assert route.allowed_writes
            for rel_path in route.allowed_writes:
                assert rel_path.endswith("/**") or is_safe_round_relative_path(rel_path)

        if route.standalone_review_profile is not None:
            assert route.standalone_review_profile in profile_ids
            assert route.standalone_review_profile != route.profile_id

        if route.independent_review_profile is not None:
            assert route.independent_review_profile in profile_ids


def test_packet_sidecar_roles_are_workspace_write_owned_outputs() -> None:
    routes = {route.profile_id: route for route in agent_profiles.profile_routes()}
    supervisor_roles = {role.key: role for role in supervisor_packets.PACKET_ROLES}
    opponent_roles = {role.key: role for role in opponent_packets.PACKET_ROLES}

    text_route = routes["thesis_text_reviewer"]
    assert text_route.sandbox_mode == "workspace-write"
    assert "work/opponent_packets/text_structure_assignment_findings.md" in text_route.owned_outputs
    assert supervisor_roles["text_assignment"].agent_profile_id == "thesis_text_reviewer"
    assert opponent_roles["text_structure_assignment"].agent_profile_id == "thesis_text_reviewer"

    calibration_route = routes["thesis_evidence_calibrator"]
    assert calibration_route.sandbox_mode == "workspace-write"
    assert "work/opponent_packets/evidence_calibration_findings.md" in calibration_route.owned_outputs
    assert supervisor_roles["evidence_calibration"].agent_profile_id == "thesis_evidence_calibrator"
    assert opponent_roles["evidence_calibration"].agent_profile_id == "thesis_evidence_calibrator"


def test_agent_profile_matrix_mentions_every_registry_route() -> None:
    matrix = (REPO_ROOT / "docs/agent-profile-matrix.md").read_text(encoding="utf-8")

    for route in agent_profiles.agent_profile_routes():
        assert f"`{route.status}`" in matrix
        if route.skill_id is not None:
            assert f"`{route.skill_id}`" in matrix
        if route.profile_id is not None:
            assert f"`{route.profile_id}`" in matrix
        if route.independent_review_profile is not None:
            assert f"`{route.independent_review_profile}`" in matrix


def test_agent_profile_matrix_row_contract_matches_registry() -> None:
    matrix = (REPO_ROOT / "docs/agent-profile-matrix.md").read_text(encoding="utf-8")

    for route in agent_profiles.agent_profile_routes():
        label = route.skill_id or route.role_source
        expected_cells = [
            f"| `{label}`",
            f"| `{route.status}`",
            f"| `{route.profile_id}`" if route.profile_id else "| none",
            f"| {route.role_kind}",
            f"| {route.sandbox_mode}",
        ]
        for cell in expected_cells:
            assert cell in matrix


def test_configured_codex_agent_profiles_match_registry_contract() -> None:
    routes = {route.profile_id: route for route in agent_profiles.profile_routes()}
    config_entries = codex_agent_config_entries()

    assert config_entries
    assert set(config_entries) == set(routes)

    for profile_id, config_entry in config_entries.items():
        route = routes[profile_id]
        config_file = config_entry["config_file"]
        assert isinstance(config_file, str)
        profile_path = REPO_ROOT / ".codex" / config_file
        assert profile_path.is_file()

        profile_config = load_profile_config(config_file)
        assert profile_config["model"] == "gpt-5.5"
        assert profile_config["model_reasoning_effort"] == "xhigh"
        assert profile_config["approval_policy"] == "never"
        assert profile_config["sandbox_mode"] == route.sandbox_mode

        developer_instructions = profile_config["developer_instructions"]
        assert isinstance(developer_instructions, str)
        assert f"Profile id: {profile_id}" in developer_instructions
        assert "Private case data stays under ignored cases/." in developer_instructions
        assert "Do not edit tracked workflow files." in developer_instructions
        assert "Return contract:" in developer_instructions
        if route.skill_id is None:
            assert f"Role source: {route.role_source}" in developer_instructions
        else:
            assert f"Owning skill: {route.skill_id}" in developer_instructions

        if route.sandbox_mode == "workspace-write":
            assert "Allowed writes:" in developer_instructions
            for allowed_write in route.allowed_writes:
                assert allowed_write.removesuffix("/**") in developer_instructions
                if profile_id in {"thesis_text_reviewer", "thesis_evidence_calibrator"} and allowed_write.startswith(
                    "work/"
                ):
                    assert f"cases/<case-id>/rounds/<round-id>/{allowed_write}" in developer_instructions
        else:
            assert "Do not write files in normal use." in developer_instructions


def test_agent_coverage_role_specs_are_routed_by_profile_registry(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "outputs").mkdir(parents=True)
    for name in [
        "feedback_student.md",
        "vedouci_posudek_revidovany.md",
        "oponent_podklady_revidovane.md",
        "feedback_k_posudku.md",
    ]:
        (round_dir / "outputs" / name).write_text("placeholder\n", encoding="utf-8")
    (round_dir / "inputs" / "code").mkdir(parents=True)
    (round_dir / "inputs" / "github").mkdir(parents=True)
    (round_dir / "inputs" / "media").mkdir(parents=True)
    (round_dir / "inputs" / "theses_similarity").mkdir(parents=True)
    (round_dir / "inputs" / "media" / "figure.png").write_bytes(b"png")
    (round_dir / "inputs" / "theses_similarity" / "report.pdf").write_bytes(b"pdf")
    (round_dir / "work").mkdir()
    (round_dir / "work" / "quantitative_claims.json").write_text("{}\n", encoding="utf-8")
    (round_dir / "notes").mkdir()
    (round_dir / "notes" / "literature.md").write_text("source map\n", encoding="utf-8")

    specs = agent_coverage.inferred_role_specs(round_dir, {})
    routes = agent_profiles.routes_by_skill_id()

    assert set(specs) == {
        "supervisor_feedback_review",
        "supervisor_report_review",
        "code_consistency",
        "code_quality",
        "github_intake",
        "quantitative_claims",
        "theses_similarity",
        "figure_media",
        "literature_citation",
        "typography_formal",
        "opponent_materials_review",
        "opponent_report_review",
    }
    for spec in specs.values():
        route = routes[spec.skill]
        assert route.status == "profile"
        assert route.profile_id is not None
        assert spec.evidence_path in route.owned_outputs


def test_workflow_review_profiles_cross_link_to_agent_profile_routes() -> None:
    routes = agent_profiles.profile_routes()

    for profile in review_profiles.workflow_review_profiles():
        matches = [
            route
            for route in routes
            if profile.final_artifact in route.owned_outputs and profile.approval_record in route.owned_outputs
        ]
        assert len(matches) == 1
        final_review_route = matches[0]
        assert final_review_route.status == "profile"
        assert "code_consistency" in profile.code_bearing_roles
        assert "code_quality" in profile.code_bearing_roles


def test_session_start_hook_points_to_profile_matrix_without_stale_role_subset() -> None:
    hook = (REPO_ROOT / ".codex/hooks/session_start_context.py").read_text(encoding="utf-8")

    assert "docs/agent-profile-matrix.md" in hook
    assert "supervisor feedback, opponent materials" not in hook
    assert "logical workflow command check-supervisor-ready" in hook
    assert "packaged .cmd/.ps1 launcher" in hook


def test_profile_routes_declare_valid_provider_sets() -> None:
    supported = set(agent_profiles.SUPPORTED_PROVIDERS)
    for route in agent_profiles.profile_routes():
        assert route.providers, f"{route.profile_id} must declare at least one provider"
        assert set(route.providers) <= supported, f"{route.profile_id} lists unsupported provider(s)"
        # Every current spawnable role ships a Codex adapter.
        assert "codex" in route.providers, f"{route.profile_id} must remain codex-capable"


def test_non_profile_routes_advertise_no_providers() -> None:
    # parent-owned and deferred routes are not spawned, so they must not claim a
    # provider adapter (capability discovery must not surface them).
    for route in agent_profiles.agent_profile_routes():
        if route.status != "profile":
            assert route.providers == (), f"{route.role_source} is {route.status}; providers must be empty"


def test_claude_capable_routes_have_a_matching_claude_adapter() -> None:
    # Drift guard (canary-first): a route may only advertise "claude" once its
    # `.claude/agents/<role>.md` adapter exists. This forces the registry flag
    # and the adapter file to land together.
    for route in agent_profiles.profile_routes():
        if route.profile_id and "claude" in route.providers:
            adapter = REPO_ROOT / ".claude" / "agents" / f"{route.profile_id.replace('_', '-')}.md"
            assert adapter.is_file(), (
                f"{route.profile_id} advertises the claude provider but " f"{adapter.relative_to(REPO_ROOT)} is missing"
            )


def test_claude_capable_profile_ids_matches_registry() -> None:
    expected = {
        route.profile_id
        for route in agent_profiles.profile_routes()
        if route.profile_id and "claude" in route.providers
    }
    assert agent_profiles.claude_capable_profile_ids() == expected


def test_role_fragments_match_codex_developer_instructions() -> None:
    # Drift guard: the shared provider-neutral role prompt body under
    # .agents/roles/<role>.md must stay byte-equal (modulo surrounding
    # whitespace) to the authoritative Codex adapter's developer_instructions.
    roles_dir = REPO_ROOT / ".agents" / "roles"
    fragments = sorted(roles_dir.glob("*.md")) if roles_dir.is_dir() else []
    assert fragments, "expected at least the canary role fragment"
    for frag in fragments:
        toml_path = REPO_ROOT / ".codex" / "agents" / f"{frag.stem}.toml"
        assert toml_path.is_file(), f"role fragment {frag.name} has no Codex adapter {toml_path.name}"
        codex_body = tomllib.loads(toml_path.read_text(encoding="utf-8"))["developer_instructions"].strip()
        assert codex_body == frag.read_text(encoding="utf-8").strip(), f"{frag.name} drifted from its Codex adapter"


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---", "adapter must start with a YAML frontmatter block"
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    body = "\n".join(lines[end + 1 :]).strip()
    return meta, body


def test_claude_adapters_match_fragments_and_are_safe() -> None:
    agents_dir = REPO_ROOT / ".claude" / "agents"
    adapters = sorted(agents_dir.glob("*.md")) if agents_dir.is_dir() else []
    # Only assert over adapters that exist; the registry drift guard elsewhere
    # forces a claude-capable route to have one.
    for adapter in adapters:
        meta, body = _parse_frontmatter(adapter.read_text(encoding="utf-8"))
        assert meta.get("name") == adapter.stem, f"{adapter.name}: frontmatter name must equal filename stem"
        assert meta.get("description"), f"{adapter.name}: description required"
        # Semantic reviewer roles must pin the strongest model and high effort
        # (never `inherit`, which can silently resolve to a weak parent model).
        assert meta.get("model") in {"opus"} or str(meta.get("model", "")).startswith(
            "claude-opus"
        ), f"{adapter.name}: semantic reviewer must pin a strong Opus model, not {meta.get('model')!r}"
        assert meta.get("effort") == "xhigh", f"{adapter.name}: semantic reviewer must set effort: xhigh"
        tools = {t.strip() for t in meta.get("tools", "").split(",") if t.strip()}
        assert tools, f"{adapter.name}: an explicit tools allowlist is required"
        # No nested spawning and no shell/write-escape for reviewer adapters.
        assert {"Task", "Agent", "Bash"}.isdisjoint(tools), f"{adapter.name}: must not grant Task/Agent/Bash"
        fragment = (REPO_ROOT / ".agents" / "roles" / adapter.name).read_text(encoding="utf-8").strip()
        assert body == fragment, f"{adapter.name}: body drifted from .agents/roles/{adapter.name}"


def test_reviewer_write_policy_matches_registry() -> None:
    # The write-guard policy file must stay in sync with the registry: keys are
    # the claude-capable roles (hyphenated), values are their allowed_writes.
    import json

    policy = json.loads((REPO_ROOT / ".claude/hooks/reviewer_write_policy.json").read_text(encoding="utf-8"))
    expected = {
        route.profile_id.replace("_", "-"): list(route.allowed_writes)
        for route in agent_profiles.profile_routes()
        if route.profile_id and "claude" in route.providers
    }
    assert policy == expected
