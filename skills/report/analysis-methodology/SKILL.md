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
- If durability is inconclusive because readiness/context conditions were not met, mark it `inconclusive` and do not let it drive phase health.
- Recovery red yields red if durability is not red.
- Energetic red without durability/recovery red does not automatically imply structural failure.
- Intensity density and execution are subordinate/contextual domains.

Inconclusive logic:
- A durability red is structural only if residual high-intensity fatigue is absent, environment is comparable, and energetic pre-load criteria are met.
- Otherwise label it `inconclusive (context-limited)`.
- Inconclusive results are null diagnostic results. They are not yellow or red and must not influence overall status.

Authority separation:
- this policy may justify status labels and narrative interpretation
- this policy must not mandate deloads, progression, phase termination, or week changes
- workout types and KPI signal mappings provide evidence context, not governance decisions

Hard rules:
- do not prescribe direct planning rewrites
- do not overstate certainty beyond the evidence
- distinguish observation, interpretation, and recommendation clearly
- recommendations must stay `advisory`, scoped to `Season-Planner`, and explicitly not a `direct_phase_change` or `weekly_intervention`
