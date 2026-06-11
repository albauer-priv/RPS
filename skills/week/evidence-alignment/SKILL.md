---
name: evidence-alignment
description: Convert exact previous-week report and activity evidence into early week-planning implications.
metadata:
  author: rps
  version: "1.0"
---
Interpret week evidence before synthesis.

Inputs:
- exact previous-week `des_analysis_report`
- exact previous-week `activities_actual`
- exact previous-week `activities_trend`
- deterministic week calendar and phase execution context

Return:
- continuity/disruption signal
- recovery/fatigue and durability caution
- compact week-planning implications
- prohibited overreach

Hard rules:
- use only previous-week weekly evidence, never target-week evidence
- evidence may reduce load ambition or quality density inside the active week band
- do not rewrite fixed rest days, exact legality, or active weekly band authority
- this task is not the final week planner and not a late reviewer

Good implication examples:
- `Previous-week recovery evidence supports conservative load placement inside the active band.`
- `Continuity is disrupted, so avoid stacked quality or catch-up compression this week.`
- `Durability caution allows a legal week plan, but quality density should stay below the optimistic edge of the band.`
