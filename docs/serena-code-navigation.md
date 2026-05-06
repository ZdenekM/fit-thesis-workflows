# Serena Code Navigation

Serena MCP is the default code-navigation aid for non-trivial code work in this
repository and in prepared thesis code workspaces.

Use Serena when you need symbol-aware understanding or edits:

- overview of Python modules, classes, functions, and CLI entry points,
- finding definitions, implementations, and references,
- scoped edits to a function or class body,
- checking whether a helper is still used before deleting or moving it,
- navigating larger submitted code roots after `scripts/prepare-code-workspace`.

For this workflow repository, the tracked `.serena/project.yml` is configured for
Python and ignores `cases/**`. Use Serena primarily for Python under `src/`,
`scripts`, tests, and `.codex/hooks`. Use normal text tools for Markdown, TOML,
YAML, shell wrappers, generated text, and small one-off searches.

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
