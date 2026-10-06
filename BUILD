DEV_HYGIENE_PATHS = [
    ".codex/hooks",
    "scripts",
    "src",
    "tests",
]

DEV_HYGIENE_IGNORE_GLOBS = (
    "**/.git/**,**/.pants.d/**,**/.mypy_cache/**,**/__pycache__/**,"
    "**/.pytest_cache/**,**/.venv/**,**/venv/**,**/cases/**,**/dist/**,"
    "**/work/**,**/outputs/**,**/extracted/**"
)

python_requirement(
    name="vulture_req",
    requirements=["vulture==2.16"],
)

files(
    name="omen_config",
    # Read by tests/test_omen_quality.py to pin the exclude key Omen actually honours.
    sources=["omen.toml"],
)

files(
    name="codex_agent_profile_metadata",
    sources=[
        ".codex/config.toml",
        ".codex/agents/*.toml",
    ],
)

files(
    name="agent_profile_registry_metadata",
    sources=[
        ".agents/roles/*.md",
        ".agents/skills/*/SKILL.md",
        ".claude/agents/*.md",
        ".claude/hooks/reviewer_write_policy.json",
        ".claude/settings.json",
        ".codex/hooks/session_start_context.py",
        "AGENTS.md",
        "docs/agent-profile-matrix.md",
    ],
)

files(
    name="assignment_authoring_metadata",
    # Listed one by one rather than globbed: `profiles/*.md` other than these two are ignored
    # private profiles, and a glob would pull them into the test sandbox.
    sources=[
        "docs/assignment-authoring.md",
        "profiles/README.md",
        "profiles/default.md",
    ],
)

pex_binary(
    name="vulture",
    description="Run a dev-only dead-code scan over workflow code.",
    script="vulture",
    dependencies=[":vulture_req"],
    args=DEV_HYGIENE_PATHS + [
        "--min-confidence",
        "85",
        "--exclude",
        DEV_HYGIENE_IGNORE_GLOBS,
    ],
    tags=["dev-hygiene"],
)
