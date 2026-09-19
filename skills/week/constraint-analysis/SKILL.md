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
- keep week redesign in the plan-synthesis or revision task
- use wellness as context that requires governance-aware interpretation
- distinguish soft preferences from hard constraints explicitly
- preserve exact-week scope

Retrieval policy:
- Athlete-managed inputs (`planning_events`, `availability`, `logistics`), authoritative week execution values, and latest authoritative planning artefacts/snapshots are already provided as injected context. No workspace tools are available or needed for this task.


Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
