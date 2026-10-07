# Quarto defaults, Typst template partial, Lua filters and vendored fonts that
# the PDF renderers load through importlib.resources: `shared/` is used by every
# kind, `feedback/` by render-feedback and `brief/` by render-brief. Packaged into
# every workflow-tool PEX with thesis_review_workflow/pdf_render.py.
resources(
    name="pdf_render",
    sources=["shared/**/*", "feedback/**/*", "brief/**/*"],
)
