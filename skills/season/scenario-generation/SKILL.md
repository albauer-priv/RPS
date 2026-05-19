---
name: scenario-generation
description: Generate three advisory season scenarios with coherent cadence, structure pressure, and event emphasis.
metadata:
  author: rps
  version: "4.0"
---
Generate `SEASON_SCENARIOS` as three advisory alternatives only.

Method:
1. Respect the injected deterministic horizon context, A/B/C event inventory, athlete profile, availability, logistics, and KPI context.
2. Produce exactly three coherent scenarios with ids `A`, `B`, and `C`.
3. Vary scenarios first by kJ-envelope, fatigue exposure, specificity, density, recovery tolerance, and risk contract; use intensity guidance only as a downstream permission layer.
4. Keep every scenario internally consistent with durability-first planning, progressive-overload policy, and agenda intensity vocabulary.
5. Express scenario guidance as advisory planning intent only; leave scenario selection and binding season planning to their dedicated tasks.

kJ-first scenario methodology:
- In ultra/brevet planning, the planned kJ-envelope is the leading steering quantity for scenario identity.
- Scenario differentiation must consider:
  - `weekly kJ range`
  - `block kJ exposure`
  - `peak-week kJ`
  - `long-ride kJ`
  - `accumulated pre-load before quality work`
  - `density / complexity`
  - `recovery tolerance`
  - `specificity under fatigue`
- A/B/C must not be only `lower / medium / higher weekly kJ` variants.
- If time budget makes clear kJ separation unrealistic, scenarios must differ through risk contract, density, specificity, and recovery tolerance rather than artificial kJ inflation.
- Progression logic follows:
  - `time / kJ`
  - `frequency`
  - `density / complexity`
  - `intensity`
- Intensity is a later shaping lever, not the primary scenario identity.

Deterministic horizon context:
- use `last_event_date`, `last_event_iso_week`, `weeks_until_last_event_from_target_week_start`, `inclusive_planning_horizon_weeks`, and `season_iso_week_range` directly when provided
- use the deterministic last-event horizon block when present
- scenario `planning_horizon_weeks` must align with `inclusive_planning_horizon_weeks`

Deterministic cadence options context:
- use `Deterministic Cadence Options Context` as the source of truth for `2:1`, `3:1`, and `2:1:1` phase math
- copy only supported cadence-derived values into `scenario_guidance`
- use injected cadence options for phase lengths, phase counts, and shortening budgets

Deterministic recommendation context:
- when `Deterministic Season Scenario Recommendation Context` is present, treat it as code-owned advisory evidence
- preserve the recommended cadence and core evidence in `data.notes`
- reflect recommendation-specific rationale in the matching scenario's `scenario_guidance.decision_notes`
- keep the recommendation advisory; selection still belongs to the user/selection task

Required content per scenario:
- `scenario_id`, `name`, `core_idea`, `load_philosophy`, `risk_profile`, `key_differences`, `best_suited_if`
- `typical_week_feel`, `main_payoff`, `main_cost`, `what_gets_prioritized`, `what_gets_de_emphasized`
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

Required A/B/C target profiles:
- **Scenario A = robust completion-first**
  - lower feasible kJ-envelope
  - high recovery margin
  - low density
  - minimal intensity allowance
  - high executability under work stress, illness risk, or masters recovery limits
  - `ENDURANCE` is the core domain; `TEMPO` is optional and sparse only when the scenario still reads completion-first
- **Scenario B = durability-forward target plan**
  - realistic target kJ-envelope
  - systematic long-ride progression
  - selected `TEMPO` / optional `SWEET_SPOT` economy work
  - balanced recovery risk
  - default shape for many brevet/ultra seasons when performance should improve without compromising robustness
- **Scenario C = ambitious performance-forward long build**
  - upper plausible kJ-envelope
  - higher specificity under fatigue
  - more B2B / hard-late / event simulation
  - optional `THRESHOLD` or `VO2MAX` only if explicitly justified
  - ambition comes primarily from specificity and fatigue exposure, not from automatic high-intensity escalation

Scenario math rules:
- `planning_horizon_weeks` must match the inclusive week span of `meta.iso_week_range`.
- if deterministic horizon context is present, it is the source of truth for scenario horizon math
- `phase_count_expected`, `shortening_budget_weeks`, `phase_plan_summary`, and `max_shortened_phases` must stay consistent with horizon length and declared phase length.
- If `shortening_budget_weeks = 0`, then `max_shortened_phases = 0`.
- `intensity_guidance` must use canonical agenda intensity domains only: `NONE`, `RECOVERY`, `ENDURANCE`, `TEMPO`, `SWEET_SPOT`, `THRESHOLD`, `VO2MAX`.
- Keep `avoid_domains` to trainable intensity domains; use `NONE` and `RECOVERY` only for availability/recovery semantics.

Intensity-domain semantics:
- `allowed_domains` are permissions, not obligations.
- `ENDURANCE` is the core domain of every scenario.
- `TEMPO` is in many ultra/brevet contexts the most likely first additional domain because it supports sub-threshold economy and long stable duration, but it is not dogma.
- `SWEET_SPOT` is optional when time budget limits kJ separation or when economy / sustained sub-threshold work is part of the scenario story.
- `THRESHOLD` and `VO2MAX` are special-case permissions, not default markers of ambition.
- Scenario C is not defined by `VO2MAX`.
- Scenarios B and C may legitimately share identical `allowed_domains` when their kJ-envelope, specificity, fatigue exposure, density, and risk contract are clearly different.

Internal consistency checks:
- Ask whether the scenario is more than just a different weekly-kJ number.
- Ensure `risk_profile`, `load_philosophy`, `decision_notes`, and `intensity_guidance` tell the same story.
- If `VO2MAX` is allowed, explain the ceiling-support role explicitly in `decision_notes` or `kpi_guardrail_notes`.
- If Scenario B is the performance-default option, make economy/sub-threshold logic plausible in the scenario story.
- If Scenario C uses no additional domains beyond `ENDURANCE` or `TEMPO`, make the ambition visible through B2B, hard-late, pre-load, event simulation, or other specificity-under-fatigue markers.

Hard rules:
- output exactly three scenarios
- keep numeric weekly kJ targets for season/phase planning tasks
- use canonical intensity domains
- keep scenarios advisory until selection and season planning
- use the injected deterministic planning horizon
- do not define scenarios primarily by domain breadth
- do not let Scenario C become "the VO2 scenario" by default
- do not invent fake kJ separation when the actual time budget cannot support it

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Positive execution pattern:
- Build three distinct scenario options from the injected horizon, cadence options, event priorities, athlete constraints, and kJ-first risk/exposure logic.
- Describe each scenario with a clear purpose, load philosophy, cadence structure, event alignment, risk profile, and best-fit condition.
- Add five short user-facing differentiators that make scenario selection easier without reading the whole prose:
  - `typical_week_feel`
  - `main_payoff`
  - `main_cost`
  - `what_gets_prioritized`
  - `what_gets_de_emphasized`
- Include assumptions and unknowns so selection can happen without recomputing dates or phase counts.
- Produce scenario guidance that helps Season Planning choose a coherent direction while preserving informational authority.
- Use the precomputed phase math, event-distance facts, and availability context to set realistic scenario structure.
- Explain the tradeoff between robust, balanced, and ambitious choices in terms of exposure, recovery margin, specificity, and failure tolerance.
- Carry the code-owned recommendation into scenario notes so the selection page can explain why one cadence is currently favored.
- Return scenarios that are complete, differentiated, traceable, and ready for direct selection.

Output format:
- Return the task expected_output with scenario or scenario-interpretation fields filled explicitly.
- Include decision logic, cadence/horizon facts, event alignment, risk flags, and assumptions where available.
- Keep scenario guidance informational unless the active task makes it binding.
