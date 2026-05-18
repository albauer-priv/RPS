---
name: scenario-generation
description: Generate three advisory season scenarios with coherent cadence, structure pressure, and event emphasis.
metadata:
  author: rps
  version: "3.0"
---
Generate `SEASON_SCENARIOS` as three advisory alternatives only.

Method:
1. Respect the injected deterministic horizon context, A/B/C event inventory, athlete profile, availability, logistics, and KPI context.
2. Produce exactly three coherent scenarios with ids `A`, `B`, and `C`.
3. Vary scenarios by cadence pressure, macrocycle compression, event emphasis, and intensity guidance rather than by arbitrary narrative style.
4. Keep every scenario internally consistent with durability-first planning, progressive-overload policy, and agenda intensity vocabulary.
5. Express scenario guidance as advisory planning intent only; leave scenario selection and binding season planning to their dedicated tasks.

Deterministic horizon context:
- use `last_event_date`, `last_event_iso_week`, `weeks_until_last_event_from_target_week_start`, `inclusive_planning_horizon_weeks`, and `season_iso_week_range` directly when provided
- use the deterministic last-event horizon block when present
- scenario `planning_horizon_weeks` must align with `inclusive_planning_horizon_weeks`

Deterministic cadence options context:
- use `Deterministic Cadence Options Context` as the source of truth for `2:1`, `3:1`, and `2:1:1` phase math
- copy only supported cadence-derived values into `scenario_guidance`
- use injected cadence options for phase lengths, phase counts, and shortening budgets

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
- if deterministic horizon context is present, it is the source of truth for scenario horizon math
- `phase_count_expected`, `shortening_budget_weeks`, `phase_plan_summary`, and `max_shortened_phases` must stay consistent with horizon length and declared phase length.
- If `shortening_budget_weeks = 0`, then `max_shortened_phases = 0`.
- `intensity_guidance` must use canonical agenda intensity domains only: `NONE`, `RECOVERY`, `ENDURANCE_LOW`, `ENDURANCE_HIGH`, `TEMPO`, `SWEET_SPOT`, `THRESHOLD`, `VO2MAX`.
- Keep `avoid_domains` to trainable intensity domains; use `NONE` and `RECOVERY` only for availability/recovery semantics.

Hard rules:
- output exactly three scenarios
- keep numeric weekly kJ targets for season/phase planning tasks
- use canonical intensity domains
- keep scenarios advisory until selection and season planning
- use the injected deterministic planning horizon

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Positive execution pattern:
- Build three distinct scenario options from the injected horizon, cadence options, event priorities, and athlete constraints.
- Describe each scenario with a clear purpose, load philosophy, cadence structure, event alignment, risk profile, and best-fit condition.
- Include assumptions and unknowns so selection can happen without recomputing dates or phase counts.
- Produce scenario guidance that helps Season Planning choose a coherent direction while preserving informational authority.
- Use the precomputed phase math, event-distance facts, and availability context to set realistic scenario structure.
- Explain the tradeoff between conservative, balanced, and assertive choices in terms the selection task can compare.
- Return scenarios that are complete, differentiated, traceable, and ready for direct selection.

Output format:
- Return the task expected_output with scenario or scenario-interpretation fields filled explicitly.
- Include decision logic, cadence/horizon facts, event alignment, risk flags, and assumptions where available.
- Keep scenario guidance informational unless the active task makes it binding.
