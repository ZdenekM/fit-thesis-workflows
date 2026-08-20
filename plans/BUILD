files(
    name="plan_documents",
    # `*.md` rather than `*_plan.md`: the contract gate also asserts that a generic `plans/PLAN.md`
    # does not exist, and a narrower glob would make that check pass vacuously in the sandbox.
    sources=["*.md"],
)
