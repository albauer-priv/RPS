---
name: analysis-methodology
description: Diagnostic-only DES interpretation for completed-week advisory reports.
metadata:
  author: rps
  version: "3.0"
---
Produce diagnostic analysis only, not planning authority.

Method:
1. Read the completed-week evidence and recent trend context.
2. Evaluate domains in the prescribed dominance order:
   - Durability
   - Recovery / Tolerability
   - Energetic Load
   - Intensity Density
   - Execution / Adherence
3. The weakest higher-ranked domain dominates lower-ranked green signals.
4. Keep recommendations advisory to the Season-Planner only.

Diagnostic rules:
- Durability is diagnostically dominant.
- Any valid `RED` durability signal yields overall red status.
- If durability is inconclusive because readiness/context conditions were not met, mark it `inconclusive` and keep it outside phase-health scoring.
- Recovery red yields red if durability is not red.
- Energetic red without durability/recovery red does not automatically imply structural failure.
- Intensity density and execution are subordinate/contextual domains.

Inconclusive logic:
- A durability red is structural only if residual high-intensity fatigue is absent, environment is comparable, and energetic pre-load criteria are met.
- Otherwise label it `inconclusive (context-limited)`.
- Treat inconclusive results as null diagnostic results: keep them outside yellow/red classification and overall-status scoring.

Authority separation:
- this policy may justify status labels and narrative interpretation
- keep deloads, progression, phase termination, and week changes governed by the active planning artifacts and review tasks
- workout types and KPI signal mappings provide evidence context, not governance decisions

Hard rules:
- keep outputs diagnostic and route planning rewrites to planning tasks
- calibrate certainty to the available evidence
- distinguish observation, interpretation, and recommendation clearly
- recommendations must stay `advisory`, scoped to `Season-Planner`, and explicitly not a `direct_phase_change` or `weekly_intervention`

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Positive execution pattern:
- Read the completed-week evidence, identify the strongest diagnostic signals, and summarize what they indicate.
- Explain durability, load, recovery, and KPI observations as diagnostic findings rather than plan changes.
- Include uncertainty and missing-data flags so the review manager can judge confidence.
- Produce a compact evidence-led analysis that supports the report expected_output and stays diagnostic-only.

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
