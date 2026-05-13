import tomllib
from pathlib import Path

from thesis_review_workflow import agent_profiles
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


def test_configured_codex_agent_profiles_match_registry_contract() -> None:
    routes = {route.profile_id: route for route in agent_profiles.profile_routes()}
    config_entries = codex_agent_config_entries()

    assert config_entries
    assert set(config_entries) <= set(routes)

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
        else:
            assert "Do not write files in normal use." in developer_instructions
