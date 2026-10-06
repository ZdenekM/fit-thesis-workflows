python_sources(
    name="workflow_core",
    overrides={
        # Loaded through importlib.resources, which dependency inference cannot see.
        "feedback_render.py": {"dependencies": ["src/thesis_review_workflow/render:feedback_render"]},
    },
)
