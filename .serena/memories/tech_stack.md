# Tech Stack

- Python workflow code targets Python 3.12 through Pants `interpreter_constraints = ["==3.12.*"]`.
- Pants 2.30.0 is the repo build/test/lint/typecheck entrypoint; invoke as `pants`, not `./pants`.
- Pants backends: Python, black, flake8, isort, mypy, shell, shfmt, shellcheck.
- Formatting config lives in `pants/pyproject.toml`: black/isort line length 120, black target `py312`, isort profile `black` over `scripts`, `src`, `tests`.
- Python sources are rooted at `.codex/hooks`, `scripts`, `src`, and `tests`.
- Logical `scripts/<tool>` commands are POSIX wrappers on Linux; Windows operator path is packaged launchers from `scripts\package-workflow-tools.cmd` or `.ps1` into `dist\workflow-tools\bin`.
- Dev-only hygiene includes `pants run :vulture`, `pants run :jscpd`, and `pants run :omen`; these are not thesis case pipeline gates.
