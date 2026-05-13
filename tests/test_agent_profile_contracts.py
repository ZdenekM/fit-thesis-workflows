from pathlib import Path

from thesis_review_workflow import agent_profiles
from thesis_review_workflow.paths import is_safe_round_relative_path

REPO_ROOT = Path(__file__).resolve().parents[1]


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
