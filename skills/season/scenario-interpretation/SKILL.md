---
name: scenario-interpretation
description: Interpret the selected season scenario as binding Season planning posture input without reconstructing structural authority.
metadata:
  author: rps
  version: "3.0"
---
Interpret `SEASON_SCENARIO_SELECTION` strictly against the bound latest `SEASON_SCENARIOS`.

Method:
1. Read the referenced `SEASON_SCENARIOS` artefact and the selected `A|B|C` scenario.
2. Preserve the selection as binding Season posture once chosen by the athlete.
3. Translate the chosen scenario into implications for event emphasis, cadence pressure, compression tolerance, recovery margin, fatigue exposure, specificity density, and legal intensity emphasis.
4. Keep planning-event truth, athlete constraints, availability, and logistics above scenario preference whenever they conflict.
5. Carry any selected KPI moving-time-rate guidance as advisory context while keeping gating decisions in their dedicated governance tasks.

Selection semantics:
- `selected_scenario_id` must be `A`, `B`, or `C`.
- `selection_source` is `user` or `system`; preserve it explicitly.
- `season_scenarios_ref` must remain traceable.
- `selection_rationale` and `notes` explain the user choice and must remain visible in Season-operational posture.
- `kpi_moving_time_rate_guidance_selection` may be present or null. If present, it remains advisory.

Hard rules:
- scenario selection is binding once chosen and bound to the latest scenarios artifact
- keep explicit A/B/C event truth above scenario preference
- interpret the selected scenario as provided
- emit scenario interpretation only; leave phase-slot math, week math, and workout directives to their tasks
- do not soften selected posture into generic advisory prose
- do not recommend a different scenario in this layer

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the task expected_output with scenario or scenario-interpretation fields filled explicitly.
- Include decision logic, cadence/horizon facts, selection rationale, event alignment, risk flags, and assumptions where available.
- Keep structural planning decisions out of this layer while preserving the selected contract as binding Season posture.
