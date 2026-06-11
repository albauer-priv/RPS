---
name: evidence-alignment
description: Convert exact previous-week report and activity evidence into early phase-planning implications.
metadata:
  author: rps
  version: "1.0"
---
Interpret phase evidence before synthesis.

Inputs:
- exact previous-week `des_analysis_report`
- exact previous-week `activities_actual`
- exact previous-week `activities_trend`
- deterministic phase execution context

Return:
- continuity/disruption signal
- recovery/fatigue and durability caution
- compact phase-shaping implications
- prohibited overreach

Hard rules:
- use only previous-week weekly evidence, never target-week evidence
- evidence may make phase shaping more conservative or stabilization-oriented
- do not rewrite exact legality, exact role-week load bands, or phase-local objective
- this task is not the final phase planner and not a late reviewer

Good implication examples:
- `Recent fatigue evidence supports stabilization semantics inside the current phase intent rather than extra density.`
- `Continuity is weak enough that reload/re-entry handling should stay conservative across the opening week roles.`
- `Report urgency constrains specificity density, but it does not widen or narrow exact legality.`
