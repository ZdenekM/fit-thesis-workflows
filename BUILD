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
    name="codex_agent_profile_metadata",
    sources=[
        ".codex/config.toml",
        ".codex/agents/*.toml",
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

pex_binary(
    name="jscpd",
    description="Run a dev-only duplicate-code scan over workflow code.",
    entry_point="thesis_review_workflow.cli.dev_hygiene:console_main",
    dependencies=["src/thesis_review_workflow/cli:dev_hygiene"],
    args=["jscpd"],
    tags=["dev-hygiene"],
)

pex_binary(
    name="omen",
    description="Run a dev-only Omen codebase health overview.",
    entry_point="thesis_review_workflow.cli.dev_hygiene:console_main",
    dependencies=["src/thesis_review_workflow/cli:dev_hygiene"],
    args=["omen"],
    tags=["dev-hygiene"],
)
