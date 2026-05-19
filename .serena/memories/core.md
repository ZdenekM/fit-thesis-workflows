# Core

- Workflow repo for BP/DP supervision/opponent review; not a student-facing app.
- Primary operator surface is chat plus Markdown artifacts, not manual script-first runbooks.
- Always use DEEP mode; final/sendable artifacts require explicitly authorized role-agent review loops.
- Private case data belongs under ignored `cases/`; only workflow code, docs, skills, templates, profiles, and scripts belong in git.
- Use tracked plans for non-trivial multi-slice workflow/tooling changes: active under `plans/*_plan.md`, completed/superseded under `plans/archive/`.
- Source map: Python workflow library under `src/thesis_review_workflow`, POSIX wrappers under `scripts`, repo-local skills under `.agents/skills`, tests under `tests`, operator docs under `README.md` and `docs`.
- Read `mem:conventions` for workflow invariants and privacy rules, `mem:tech_stack` for build/runtime, and `mem:task_completion` before closing code/tooling changes.
