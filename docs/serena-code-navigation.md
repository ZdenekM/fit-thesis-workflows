# Serena Code Navigation

Serena MCP is the first tool for code navigation and symbol-level edits in this
repository. Reach for it before reading a source file, not after.

Order of operations for a code question:

1. `get_symbols_overview` for the shape of a module,
2. `find_symbol` with `include_body` for the one symbol you need,
3. `find_referencing_symbols` / `find_declaration` / `find_implementations` for
   call sites, definitions, and implementations.

`rg` and `Glob` stay the right tools for discovery: they find *where* something
lives. Serena reads *what* it says. A whole-file read is for confirming something
already located, never for finding it, and "I already know the path" is not a
reason to skip Serena, because most of the saving is in the follow-up reads it
makes unnecessary.

Typical uses: overview of Python modules, classes, functions, and CLI entry
points; finding definitions, implementations, and references; scoped edits to a
function or class body; checking whether a helper is still used before deleting
or moving it.

## Scope in this repository

The tracked `.serena/project.yml` configures Python and Markdown and lists
`cases/**` under `ignored_paths`. Use Serena for Python under `src/`, `scripts`,
tests, and `.codex/hooks`. Use normal text tools for TOML, YAML, shell wrappers,
and generated text.

## Long Markdown goes to local RAG, not Serena

Prose - plans, docs, skills, reviewer profiles, generated Markdown - is a
retrieval problem, not a symbol problem. Use `local-rag` `query_documents` when
you do not know which file or section answers the question, and `rg` plus a
targeted read when you do. See `docs/local-rag-usage.md`.

Serena's Markdown support is outline navigation, not semantic retrieval, and it
costs a separate `marksman` language server. Do not route long documents through
it. Editing a bounded region of a Markdown file you have already located is
still fine.

Whatever the tool, Markdown navigation is not semantic review. For thesis
feedback, supervisor reports, opponent materials, and internal evidence
artifacts, locating a section does not replace workflow skills, agent review
requirements, evidence citations, manifest checks, or private-data rules.

## Submitted student code is outside Serena's scope

Review submitted code under `cases/**` with `rg` and targeted reads. Serena
cannot reach it, and this is deliberate rather than a gap to work around:

- `cases/**` is listed in `ignored_paths` in the tracked `.serena/project.yml`,
  which is also what keeps private case data out of the index.
- The server is single-project by design. `activate_project` is not exposed, so
  no client can point Serena at a per-case root at runtime. This has always been
  true here: the `claude-code` context sets `single_project: true`, and
  `ide-assistant`, used by the earlier configuration, is an alias for it.

The evidence rules are unchanged: cite concrete files, functions, and configs,
and keep private case data under ignored paths.

## Cost and lifecycle

Serena runs as one shared server for this project
(`mcp-serena@diplomky_v2`, `http://127.0.0.1:8769/mcp`), started by a
`systemd --user` unit. Its cost is per server instance, not per call, and it is
already paid once a session is open, so declining to use it saves nothing.

If the project's language configuration changes, restart that unit
(`systemctl --user restart mcp-serena@diplomky_v2`) rather than trying to
reactivate the project. The workstation-level setup, port map, and rationale are
documented in `~/.claude/docs/mcp-bridges.md`.

Serena is an aid for code structure. It does not replace evidence rules: cite
concrete files/functions/configs, do not claim code was run unless a command was
actually run, and keep private case data under ignored paths.
