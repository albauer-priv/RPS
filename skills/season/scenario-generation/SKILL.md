---
name: scenario-generation
description: Generate three advisory season scenarios with coherent cadence, structure pressure, and event emphasis.
metadata:
  author: rps
  version: "2.0"
---
Generate `SEASON_SCENARIOS` as three advisory alternatives only.

Method:
1. Respect the authoritative planning horizon, A/B/C event inventory, athlete profile, availability, logistics, and KPI context.
2. Produce exactly three coherent scenarios with ids `A`, `B`, and `C`.
3. Vary scenarios by cadence pressure, macrocycle compression, event emphasis, and intensity guidance rather than by arbitrary narrative style.
4. Keep every scenario internally consistent with durability-first planning, progressive-overload policy, and agenda intensity vocabulary.
5. Express scenario guidance as advisory planning intent only. Do not choose one scenario here and do not emit a binding season plan.

Required content per scenario:
- `scenario_id`, `name`, `core_idea`, `load_philosophy`, `risk_profile`, `key_differences`, `best_suited_if`
- `scenario_guidance` with:
  - `deload_cadence`
  - `phase_length_weeks`
  - `phase_count_expected`
  - `max_shortened_phases`
  - `shortening_budget_weeks`
  - `phase_plan_summary`
  - `event_alignment_notes`
  - `risk_flags`
  - `fixed_rest_days`
  - `constraint_summary`
  - `kpi_guardrail_notes`
  - `decision_notes`
  - `intensity_guidance.allowed_domains`
  - `intensity_guidance.avoid_domains`
  - `assumptions`
  - `unknowns`

Scenario math rules:
- `planning_horizon_weeks` must match the inclusive week span of `meta.iso_week_range`.
- `phase_count_expected`, `shortening_budget_weeks`, `phase_plan_summary`, and `max_shortened_phases` must stay consistent with horizon length and declared phase length.
- If `shortening_budget_weeks = 0`, then `max_shortened_phases = 0`.
- `intensity_guidance` must use canonical agenda intensity domains only: `NONE`, `RECOVERY`, `ENDURANCE_LOW`, `ENDURANCE_HIGH`, `TEMPO`, `SWEET_SPOT`, `THRESHOLD`, `VO2MAX`.
- `avoid_domains` must not contain `NONE` or `RECOVERY`.

Hard rules:
- do not output fewer or more than three scenarios
- do not emit numeric weekly kJ targets here
- do not use proxy labels instead of canonical intensity domains
- do not turn scenarios into binding commitments
