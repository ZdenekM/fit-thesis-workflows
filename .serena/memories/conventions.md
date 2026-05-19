# Conventions

- Prefer conceptual/root-cause workflow simplification over compatibility layers and local workarounds.
- Do not preserve older `~/code/diplomky` behavior unless explicitly asked.
- New workflow helpers must be general and context-aware; never encode one real thesis, dataset, metric value, filename, or expected conclusion as active workflow logic.
- Deterministic code must not infer semantic meaning from free-form thesis/code text via brittle substring heuristics. Use structured metadata, parsed schemas, explicit operator config, manifests, hashes, or agent-produced artifacts.
- Important negative thesis/code claims require concrete evidence anchors.
- Quantitative/result claims need unit, scale, baseline, practical magnitude, reproducibility, and proportional-interpretation checks.
- README stays chat-first and operator-facing; detailed procedures belong in skills, templates, or focused docs.
- Keep `AGENTS.md` short; promote long task procedures into skills/docs/templates.
- Windows is supported. Operator-facing helpers need Python/Pants/PEX or native `.cmd`/`.ps1`; POSIX shell may be a Linux convenience wrapper.
- Serena is the default aid for non-trivial code navigation/edits and large tracked Markdown section work when supported; see `docs/serena-code-navigation.md`.
- When a prompt/plan/skill explicitly requires Serena, Omen, or another named tool, preflight it at slice start, use it meaningfully on the intended scope, and record the observed result. If target inspection fails, repair/scope-adjust first; otherwise stop before substituting another evidence source unless the workflow explicitly permits an optional typed limitation.
- Omen is advisory for code-quality signals. Repo-dev Omen must not inspect `cases/`; case-code Omen must run only on a scoped prepared submitted-code root and failures are typed limitations.
