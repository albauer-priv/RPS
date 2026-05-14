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
5. Carry any selected KPI moving-time-rate guidance as advisory context, never as an automatic gate.

Selection semantics:
- `selected_scenario_id` must be `A`, `B`, or `C`.
- `selection_source` is `user` or `system`; preserve it explicitly.
- `season_scenarios_ref` must remain traceable.
- `selection_rationale` and `notes` explain preference, not new authority.
- `kpi_moving_time_rate_guidance_selection` may be present or null. If present, it remains advisory.

Hard rules:
- scenario selection is informational, not binding
- do not override explicit A/B/C event truth with scenario preference
- do not infer a new scenario or merge scenarios
- do not emit binding week, phase, or workout directives here
