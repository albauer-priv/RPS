---
name: constraint-analysis
description: Interpret binding week-level constraints from upstream artifacts, availability, logistics, wellness, and completed load.
metadata:
  author: rps
  version: "2.0"
---
Read the selected week as a constrained execution window.

Method:
1. Extract hard constraints from phase guardrails, any active phase feed-forward, availability, logistics, event placement, and recovery-protection semantics.
2. Use wellness and recent completed-load context only as informational modifiers unless an approved feed-forward already turned them into binding deltas.
3. Distinguish hard blockers from soft guidance.
4. State what must be preserved by any recommendation or revision: phase intent, corridor realism, event placement, recovery protection, and no-catch-up semantics.

What to capture:
- fixed non-training days and time ceilings
- travel/work/weather/health constraints affecting the week
- event days and anchor sessions that must remain protected
- low-confidence or missing-data caveats that limit interpretation
- any valid temporary overrides from feed-forward

Hard rules:
- do not redesign the week here
- do not treat wellness as automatic authority
- do not reinterpret soft preference as hard constraint
- do not lose exact-week scope
