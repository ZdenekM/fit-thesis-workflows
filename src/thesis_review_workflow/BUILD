python_sources(
    name="workflow_core",
    overrides={
        # Loaded through importlib.resources, which dependency inference cannot see.
        "pdf_render.py": {"dependencies": ["src/thesis_review_workflow/render:pdf_render"]},
    },
)
