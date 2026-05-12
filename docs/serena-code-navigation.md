# Serena Code Navigation

Serena MCP is the default code-navigation aid for non-trivial code work and
tracked workflow Markdown navigation in this repository, and for prepared thesis
code workspaces.

Use Serena when you need symbol-aware understanding or edits:

- overview of Python modules, classes, functions, and CLI entry points,
- finding definitions, implementations, and references,
- scoped edits to a function or class body,
- checking whether a helper is still used before deleting or moving it,
- navigating larger submitted code roots after `scripts/prepare-code-workspace`,
- section-level navigation and edits in long tracked Markdown files such as
  `README.md`, `docs/*.md`, `plans/*.md`, and `.agents/skills/*/SKILL.md`.

For this workflow repository, the tracked `.serena/project.yml` is configured for
Python and Markdown and ignores `cases/**`. Use Serena primarily for Python
under `src/`, `scripts`, tests, and `.codex/hooks`, and for larger tracked
Markdown files when outline or section scoping avoids loading full documents
into chat context. Use normal text tools for TOML, YAML, shell wrappers,
generated text, small Markdown files, and small one-off searches.

Do not treat Markdown language-server support as semantic review. For thesis
feedback, supervisor reports, opponent materials, and internal evidence
artifacts, Serena may help locate sections or edit a bounded region, but it does
not replace workflow skills, agent review requirements, evidence citations,
manifest checks, or private-data rules.

For submitted student code, do not activate Serena on the whole `cases/`
directory or an entire round. First prepare the code workspace, then activate
Serena on one concrete root listed in `work/serena_roots.json`. If the submitted
code is not Python, use Serena when the language server is available and the root
is scoped safely. Practical candidates include TypeScript/JavaScript, Java, Go,
Rust, PHP, Ruby, C/C++, C#, Kotlin, Swift, and similar supported language-server
roots. If the language is unsupported or setup is too heavy for the review, state
that limitation and use read-only file inspection instead.

Serena is an aid for code structure. It does not replace evidence rules: cite
concrete files/functions/configs, do not claim code was run unless a command was
actually run, and keep private case data under ignored paths.
