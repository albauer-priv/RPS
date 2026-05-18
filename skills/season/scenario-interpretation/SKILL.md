---
name: scenario-interpretation
description: Interpret the selected season scenario as advisory planning intent without overriding binding context.
metadata:
  author: rps
  version: "3.0"
---
Interpret `SEASON_SCENARIO_SELECTION` conservatively.

Method:
1. Read the referenced `SEASON_SCENARIOS` artefact and the selected `A|B|C` scenario.
2. Preserve the selection as advisory planning intent only.
3. Translate the chosen scenario into implications for event emphasis, cadence pressure, compression tolerance, and intensity emphasis.
4. Keep planning-event truth, athlete constraints, availability, and logistics above scenario preference whenever they conflict.
5. Carry any selected KPI moving-time-rate guidance as advisory context while keeping gating decisions in their dedicated governance tasks.

Selection semantics:
- `selected_scenario_id` must be `A`, `B`, or `C`.
- `selection_source` is `user` or `system`; preserve it explicitly.
- `season_scenarios_ref` must remain traceable.
- `selection_rationale` and `notes` explain preference, not new authority.
- `kpi_moving_time_rate_guidance_selection` may be present or null. If present, it remains advisory.

Hard rules:
- scenario selection is informational, not binding
- keep explicit A/B/C event truth above scenario preference
- interpret the selected scenario as provided
- emit scenario interpretation only; leave binding week, phase, and workout directives to their tasks

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the task expected_output with scenario or scenario-interpretation fields filled explicitly.
- Include decision logic, cadence/horizon facts, event alignment, risk flags, and assumptions where available.
- Keep scenario guidance informational unless the active task makes it binding.
