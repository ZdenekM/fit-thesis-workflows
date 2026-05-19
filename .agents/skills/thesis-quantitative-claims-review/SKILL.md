---
name: thesis-quantitative-claims-review
description: Semantic BP/DP review of quantitative, evaluation, experiment, metric, performance, scale, count, and result claims into a structured work/quantitative_claims.json handoff.
---

# Thesis Quantitative Claims Review

Command routing: treat `scripts/<tool>` examples below as logical workflow
command names. On Windows, use the packaged
`dist\workflow-tools\bin\<tool>.cmd` or `.ps1` launcher from `README.md`; do
not run or click extensionless `scripts/<tool>` files.

Use this skill when quantitative or result claims materially affect supervisor
feedback, opponent materials, or final report defensibility.

This is a semantic evidence review. Deterministic helpers may validate the JSON
shape, but they must not decide what a metric means from raw text matching.

## Inputs

Use the active round unless the user specifies another:

```text
cases/<case-id>/rounds/<round-id>/
  notes/assignment.md
  notes/round-notes.md
  inputs/
  extracted/
  work/
  outputs/
```

Prefer compact packet handoffs when available:

- `work/supervisor_packets/quantitative_claims.md`
- `work/supervisor_report_packets/quantitative_claims.md`
- `work/opponent_packets/quantitative_claims.md`
- `work/review_materiality/<workflow-profile>/index.json`
- `work/current_evidence_snapshot.json`
- `work/context/claim_review_basis.json`
- `work/reuse/reuse_index.json`
- `outputs/code_consistency.md`
- `outputs/figure_media_review.md`
- `work/code_reproducibility.json`

Open full thesis/result/code artifacts only to verify a material claim, resolve a
contradiction, fill a missing anchor, respond to reviewer challenge, or
calibrate grade-impacting risk. Reuse and capsule state route context; they do
not replace the semantic quantitative review or downstream independent review.

## Process

1. Resolve the active case and round.
2. Confirm that the user explicitly authorized agent use in the current request
   before writing evidence that feeds supervisor/opponent synthesis. If
   authorization is missing, stop and ask for it.
3. Identify material quantitative claims from available structured inputs,
   role packets, materiality next actions, prior reviews, thesis extracts,
   tables, result figures, README/configs, logs, notebooks, and code evidence.
4. For each material claim, check:
   - unit and scale,
   - baseline, comparator, or "not applicable" status,
   - sample size, data split, scenario, or workload context when available,
   - practical magnitude and whether the thesis interpretation is proportionate,
   - reproducibility references such as scripts, configs, datasets, logs, seeds,
     README instructions, or missing artifacts,
   - evidence anchors and conflicting evidence,
   - overclaim risk for supervisor action or opponent report wording.
5. Write `work/quantitative_claims.json` using the schema below.
6. Run `scripts/check-evaluation-claims <case-id> [round-id]`.
7. Register the artifact through the current `work/review_role_plan.json` preset
   when available, usually with `scripts/register-review-artifact <case-id>
   <round-id> work/quantitative_claims.json --role quantitative_claims`,
   including source refs, checks, limitations, and downstream synthesis use.
8. If the artifact will be used as standalone final evidence, run an independent
   evidence-calibration review before relying on it. A downstream synthesis
   review certifies only the findings it actually uses.

## Evidence Rules

- Cite concrete evidence refs: `extracted/<file>.txt`, `outputs/*.md`,
  `work/*.json`, `inputs/*`, code paths, README/config/test/log paths, or
  figure/media review refs.
- Do not claim that code, notebooks, or experiments ran unless you actually ran
  a specific command.
- Absence of a baseline, unit, data split, seed, or script is a limitation or
  verification risk, not proof that the numerical result is false.
- Use `requires_reviewer_verification: true` when the claim may affect
  supervisor P0/P1 action, opponent grade/report wording, or a defense question.
- Keep "unsupported" and "inconsistent" for evidence-backed problems. Use
  "needs_context" when the number may be valid but lacks interpretive context.
- Keep result-table readability, axis labels, and visual inspection in
  `thesis-figure-media-review`; reference that evidence here when it affects
  quantitative meaning.

## Schema

Write UTF-8 JSON to `work/quantitative_claims.json`:

```json
{
  "schema_version": "quantitative-claims-v1",
  "case_id": "<case-id>",
  "round_id": "<round-id>",
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "producer_type": "agent",
  "producer_role": "quantitative-claims-reviewer",
  "producer_agent": "<agent-or-model-id>",
  "authorization_note": "Current request explicitly authorized agents.",
  "source_refs": [
    "extracted/thesis.txt",
    "outputs/code_consistency.md"
  ],
  "claims": [
    {
      "claim_id": "Q1",
      "summary": "Short semantic summary of the reviewed claim.",
      "kind": "metric",
      "status": "needs_context",
      "unit": "%",
      "baseline_status": "missing",
      "practical_context": "weak",
      "scale_context": "The denominator or scale behind the percentage is not explicit.",
      "sample_context": "Sample size, workload, split, or scenario is not stated.",
      "practical_magnitude": "The thesis does not explain whether this magnitude matters in practice.",
      "overclaim_risk": "moderate",
      "reproducibility_refs": [],
      "evidence_refs": [
        "extracted/thesis.txt"
      ],
      "requires_reviewer_verification": true
    }
  ],
  "limitations": []
}
```

Allowed `kind` values:

- `metric`
- `experiment`
- `performance`
- `scale`
- `count`
- `statistic`
- `other`

Allowed `status` values:

- `plausible`
- `needs_context`
- `unsupported`
- `inconsistent`
- `not_verifiable`

`unit`, `scale_context`, `sample_context`, and `practical_magnitude` are
required strings. Use `not_applicable` or `not_verifiable` as text when that is
the honest status, rather than omitting the field.

Allowed `baseline_status` values:

- `stated`
- `missing`
- `not_applicable`
- `not_verifiable`

Allowed `overclaim_risk` values:

- `low`
- `moderate`
- `high`
- `not_applicable`
- `not_verifiable`

Allowed `practical_context` values:

- `sufficient`
- `weak`
- `missing`
- `not_applicable`
- `not_verifiable`

## Synthesis Handoff

The synthesis agent should use `work/quantitative_claims.json` and the packet's
`## Quantitative Claims Handoff` first. Open full result artifacts only for
claim verification, contradictions, missing anchors, reviewer challenges, or
wording calibration.

For supervisor feedback, translate material issues into student actions: add a
baseline, explain unit/scale, qualify a conclusion, include reproducibility
evidence, or remove/soften an unsupported claim.

For opponent materials, translate material issues into evidence labels,
grade/report defensibility, limitations, defense questions, or manual checks.

## Model And Reasoning

Use `gpt-5.5` with `model_reasoning_effort = "xhigh"`. Do not downshift this
role to Spark or another mechanical helper model: the first pass over unit,
scale, baseline, reproducibility, practical magnitude, and overclaim risk is a
semantic review.

## Agent Final Response Contract

When acting as a workflow agent, write the JSON artifact to disk and keep the
chat final response compact. Use the default handoff shape in
`docs/agent-scheduling.md#subagent-handoffs`, plus the top material claim risks,
the `work/quantitative_claims.json` path, checks run, explicit limitations, and
whether `scripts/check-evaluation-claims` passed.
