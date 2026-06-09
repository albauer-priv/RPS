---
name: scenario-generation
description: Generate three advisory season scenarios with coherent cadence, selection gates, future-only event logic, and bounded intensity semantics.
metadata:
  author: rps
  version: "4.2"
---
Generate `SEASON_SCENARIOS` as three advisory alternatives only.

Field completion contract:
- `scenario_guidance.recovery_margin` = explicit recovery stance as a non-empty string
  - define it locally as how much schedule, fatigue, and continuity disruption the scenario can absorb before it should downshift
  - preferred examples: `high`, `medium`, `lower but usable`
- `scenario_guidance.fatigue_exposure` = explicit fatigue posture as a non-empty string
  - define it locally as how much accumulated fatigue the scenario intentionally tolerates while still remaining coherent
  - preferred examples: `low`, `moderate`, `high but conditional`
- `scenario_guidance.specificity_density` = explicit specificity posture as a non-empty string
  - define it locally as how dense and how fatigue-coupled the scenario's event-specific work becomes
  - preferred examples: `sparse`, `controlled`, `dense`
- `name` = short chooser label
  - preferred examples: `Durability-first, frequent reset`, `Balanced build, controlled pressure`, `Specificity-under-fatigue, higher ambition`
- `core_idea` = one-sentence scenario promise
  - preferred example: `Protect continuity and keep the athlete fresh enough to absorb work reliably across the full horizon.`
- `load_philosophy` = how load, recovery, and specificity are balanced
  - preferred example: `Moderate load with frequent recovery rhythm; prioritize repeatable execution, freshness, and consistency over aggressive build pressure.`
- `risk_profile` = relative risk plus why
  - preferred example: `Lowest risk option; best when travel volatility, fatigue sensitivity, or durability uncertainty need more protection.`
- `key_differences` = explicit comparison against the other two scenarios
  - preferred example: `Compared with B and C, this scenario keeps week-to-week pressure more controlled and asks for less fatigue exposure.`
- `typical_week_feel` = how a representative week feels
  - preferred example: `Structured but manageable; the athlete should usually finish the week feeling contained rather than stretched.`
- `main_payoff` = main gain, singular and concrete
  - preferred example: `High consistency and low disruption risk across the season.`
- `main_cost` = main tradeoff, singular and concrete
  - preferred example: `Less aggressive overload pressure and slower emergence of race-specific hardness.`
- `what_gets_prioritized` = short phrase naming what gets more emphasis
  - preferred example: `Aerobic durability, repeatability, recovery quality, and keeping training momentum intact.`
- `what_gets_de_emphasized` = short phrase naming what gets toned down
  - preferred example: `High density, deep fatigue exposure, and more ambitious freshness-to-fatigue tradeoffs.`
- `event_alignment_notes` = future-only active event logic
  - preferred example: `Matches the target horizon well by supporting a steadier progression toward the September A event.`
- `constraint_summary` = binding practical constraints
  - keep it as a structured string array, not one joined paragraph
  - preferred examples: `Fixed rest days are Monday and Friday.`, `Weekly availability remains limited on weekdays and higher on the weekend.`
- `kpi_guardrail_notes` = pacing / efficiency / metabolic guardrails, not sales prose
  - keep it as a structured string array
  - preferred example: `Keep long-ride pacing aligned with the brevet-ultra sustainable to fast-competitive boundary rather than chasing intensity for its own sake.`
- `decision_notes` = why this cadence and posture were chosen
  - keep it as a structured string array
  - preferred examples: `This is the control scenario: it emphasizes stability and recoverability.`, `Cadence is intentionally held as 2:1 here to maintain frequent resets; differentiation comes from lower load ambition and lower fatigue exposure.`
- `assumptions` = what must stay true for the scenario to remain valid
  - preferred example: `Weekend training remains the primary place for longer work.`
- `unknowns` = what could change scenario choice later
  - preferred example: `Whether future travel or fatigue will be more disruptive than the recent pattern suggests.`
- `data.notes` = global scenario-layer clarifications
  - preferred examples: `Historical or pre-horizon events are out of scope for active scenario event alignment.`, `allowed_domains define eligibility for later assignment only; they do not authorize every domain in every phase.`

Method:
1. Respect the injected deterministic horizon context, future-only A/B/C event inventory, athlete profile, availability, logistics, and KPI context.
2. Produce exactly three coherent scenarios with ids `A`, `B`, and `C`.
3. Vary scenarios first by kJ-envelope, fatigue exposure, specificity, density, cadence rhythm, recovery tolerance, and risk contract; use intensity guidance only as a downstream permission layer.
4. Recommendation-default cadence hard rule: deterministic recommendation cadence is advisory for one scenario, not the default cadence for all scenarios.
5. A/B/C must not all mirror the recommendation-default cadence unless the stored scenario fields explicitly justify that cadence is intentionally shared.
6. When cadence is intentionally shared, the stored scenario fields must explicitly say that differentiation instead comes from `load philosophy`, `specificity-under-fatigue`, `recovery margin` and/or `recovery tolerance`, `intensity permissions`, or `risk posture`.
7. If that rationale cannot be stated explicitly in `decision_notes`, `risk_flags`, `event_alignment_notes`, and/or `kpi_guardrail_notes`, at least one scenario must use a different `deload_cadence`.
8. Emit `recovery_margin`, `fatigue_exposure`, and `specificity_density` directly in `scenario_guidance`; do not expect later Season planning to infer them from prose.
9. Keep every scenario internally consistent with durability-first planning, progressive-overload policy, and agenda intensity vocabulary.
10. Express scenario guidance as advisory planning intent only; leave scenario selection and binding season planning to their dedicated tasks.
11. Write `best_suited_if` as a short concrete selection sentence, not generic praise. Use explicit positive markers such as `stable recovery`, `uncertain recovery`, `continuity priority`, `recoverability`, `load tolerance`, `fatigue exposure tolerance`, `travel`, `logistics`, `lower recovery margin`, or `recovery margin`.
12. Write `risk_flags` as short concrete caution sentences, not generic labels. Use explicit caution markers such as `under-deliver`, `continuity break`, `recovery slip`, `fatigue risk`, `travel disruption`, `logistics disruption`, `insufficient tolerance`, `too conservative`, or `too aggressive`.

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
- only future / in-horizon events are provided to the scenario agent; do not infer active scenario logic from past or completed events

Deterministic cadence options context:
- use `Deterministic Cadence Options Context` as the source of truth for `2:1`, `3:1`, and `2:1:1` phase math
- copy only supported cadence-derived values into `scenario_guidance`
- use injected cadence options for phase lengths, phase counts, and shortening budgets

Deterministic recommendation context:
- when `Deterministic Season Scenario Recommendation Context` is present, treat it as code-owned advisory evidence
- preserve the recommended cadence and core evidence in `data.notes`
- reflect recommendation-specific rationale in the matching scenario's `scenario_guidance.decision_notes`
- keep the recommendation advisory; selection still belongs to the user/selection task
- preserve recommendation context as advisory evidence only; do not mirror its cadence or posture blindly into all three scenarios
- use top-level `data.notes` for global scenario-layer clarifications such as eligibility-not-authorization and warning-only objective mismatch handling

Required content per scenario:
- `scenario_id`, `name`, `core_idea`, `load_philosophy`, `risk_profile`, `key_differences`, `best_suited_if`
- `typical_week_feel`, `main_payoff`, `main_cost`, `what_gets_prioritized`, `what_gets_de_emphasized`
- `scenario_guidance` with:
  - `recovery_margin`
  - `fatigue_exposure`
  - `specificity_density`
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
  - `season_archetype`
  - `season_archetype_rationale`
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
  - `best_suited_if` must say `continuity priority`, `uncertain recovery`, `recoverability`, or `logistics robustness` are the reason to choose it
  - preferred example: `Choose when continuity priority and uncertain recovery dominate.`
  - `risk_flags` must say the scenario may `under-deliver` or be `too conservative` if the athlete can tolerate more load
  - preferred example: `May under-deliver if high load tolerance is available.`
  - `ENDURANCE` is the core domain; `TEMPO` is optional and sparse only when the scenario still reads completion-first
- **Scenario B = durability-forward target plan**
  - realistic target kJ-envelope
  - systematic long-ride progression
  - selected `TEMPO` / optional `SWEET_SPOT` economy work
  - balanced recovery risk
  - `best_suited_if` must say `stable recovery` supports `systematic progression`
  - preferred example: `Choose when stable recovery supports systematic progression.`
  - `risk_flags` must say the scenario is less forgiving than A if `continuity break` or `recovery slip` appears
  - preferred example: `Less forgiving than A if continuity break or recovery slip appears.`
  - default shape for many brevet/ultra seasons when performance should improve without compromising robustness
- **Scenario C = ambitious performance-forward long build**
  - upper plausible kJ-envelope
  - higher specificity under fatigue
  - more B2B / hard-late / event simulation
  - optional `THRESHOLD` or `VO2MAX` only if explicitly justified
  - `best_suited_if` must say `stable recovery`, `high load tolerance`, or `fatigue exposure tolerance` are already demonstrably present
  - preferred example: `Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.`
  - `risk_flags` must say the scenario becomes `too aggressive` when `fatigue risk`, `travel disruption`, `logistics disruption`, or `insufficient tolerance` appears
  - preferred example: `Too aggressive if fatigue risk or travel disruption appears.`
  - ambition comes primarily from specificity and fatigue exposure, not from automatic high-intensity escalation

Scenario math rules:
- `planning_horizon_weeks` must match the inclusive week span of `meta.iso_week_range`.
- if deterministic horizon context is present, it is the source of truth for scenario horizon math
- `phase_count_expected`, `shortening_budget_weeks`, `phase_plan_summary`, and `max_shortened_phases` must stay consistent with horizon length and declared phase length.
- `deload_cadence` is part of the scenario identity, not decorative structure metadata.
- If `shortening_budget_weeks = 0`, then `max_shortened_phases = 0`.
- `intensity_guidance` must use canonical agenda intensity domains only: `NONE`, `RECOVERY`, `ENDURANCE`, `TEMPO`, `SWEET_SPOT`, `THRESHOLD`, `VO2MAX`.
- Keep `avoid_domains` to trainable intensity domains; use `NONE` and `RECOVERY` only for availability/recovery semantics.

Intensity-domain semantics:
- `allowed_domains` are permissions, not obligations.
- `allowed_domains` define eligibility for later assignment only; they do not authorize every domain in every phase.
- `ENDURANCE` is the core domain of every scenario.
- `TEMPO` is in many ultra/brevet contexts the most likely first additional domain because it supports sub-threshold economy and long stable duration, but it is not dogma.
- `SWEET_SPOT` is optional when time budget limits kJ separation or when economy / sustained sub-threshold work is part of the scenario story.
- `THRESHOLD` and `VO2MAX` are special-case permissions, not default markers of ambition.
- Scenario C is not defined by `VO2MAX`.
- Scenario C VO2MAX hard rule: Scenario C may include `VO2MAX` only when it is explicitly justified as `sparse ceiling-support`, `fresh-only`, `not primary identity`, and ambition sourced from `specificity-under-fatigue`, `density`, `event simulation`, or `load posture`.
- If that rationale cannot be stated explicitly in `decision_notes` and/or `kpi_guardrail_notes`, omit `VO2MAX` from Scenario C `allowed_domains`.
- Preferred copyable sentence when Scenario C allows `VO2MAX`: `VO2MAX remains sparse ceiling-support only when fresh-only, not primary identity; the scenario ambition comes from specificity-under-fatigue, density, and event simulation.`
- Scenarios B and C may legitimately share identical `allowed_domains` when their kJ-envelope, specificity, fatigue exposure, density, and risk contract are clearly different.
- Scenarios may share identical `deload_cadence` only when the stored scenario fields explicitly say cadence is intentionally held constant and explain which other axes carry the differentiation.
- Cluster wording (`cluster`, `event cluster`, `B-event cluster`, `peak cluster`) requires multiple relevant in-horizon events; otherwise use singular event wording.
- If Scenario C includes `VO2MAX`, the scenario story must explicitly say it is a sparse / limited / occasional ceiling-support or fresh-only permission, include the exact phrase `not primary identity`, and say that the ambition instead comes from `specificity-under-fatigue`, `density`, `event simulation`, or `load posture`.

Season archetype semantics:
- `season_archetype` is a normalized scenario-level semantic, not a new cycle type.
- Use `none` by default.
- Use `ceiling_first_durability` only when the scenario explicitly supports a ceiling-first then economy/durability sequence.
- `ceiling_first_durability` must stay optional and context-justified through:
  - enough planning runway before peak
  - long-duration durability objective
  - weekday time-crunch / weekend leverage
  - recovery tolerance that can support conditional early VO2
- If `season_archetype = ceiling_first_durability`, `season_archetype_rationale` must state why early ceiling support is permitted and why later durability/specificity work still has enough runway.
- If the scenario does not clearly justify that sequence, emit `season_archetype = none`.

Objective mismatch semantics:
- If the scenario layer notices a mismatch between upstream objective language and active event hierarchy, treat it as unresolved upstream input context only.
- You may name that mismatch in notes, assumptions, unknowns, or caution fields.
- Do not claim that the scenario layer resolved or replaced the objective/event hierarchy.

Internal consistency checks:
- Ask whether the scenario is more than just a different weekly-kJ number.
- Ensure `risk_profile`, `load_philosophy`, `decision_notes`, `deload_cadence`, and `intensity_guidance` tell the same story.
- Ensure `best_suited_if` is a real positive selection gate and `risk_flags` are real caution markers, not marketing prose.
- Ensure `best_suited_if` contains guardrail-visible selection words, not vague phrases like `good default` or `nice option`.
- Ensure `risk_flags` contain guardrail-visible words, not vague phrases like `general caution` or `watch recovery`.
- Make cadence rationale visible in stored scenario fields such as `decision_notes`, `risk_flags`, `event_alignment_notes`, or `kpi_guardrail_notes`.
- If multiple scenarios share the same cadence, say directly that cadence is intentionally shared and that differentiation comes from other axes such as specificity-under-fatigue, recovery margin, or risk posture.
- If `VO2MAX` is allowed, explain the ceiling-support role explicitly in `decision_notes` or `kpi_guardrail_notes`.
- Use explicit wording such as `ceiling-support`, `fresh`, `high-intensity`, `support`, or `VO2` so the rationale is unambiguous.
- Put the explanation in the actual stored scenario fields, not only in surrounding prose.
- If you cannot write that explanation cleanly, remove `VO2MAX` from `allowed_domains`.
- If Scenario B is the performance-default option, make economy/sub-threshold logic plausible in the scenario story.
- If Scenario C uses no additional domains beyond `ENDURANCE` or `TEMPO`, make the ambition visible through B2B, hard-late, pre-load, event simulation, or other specificity-under-fatigue markers.

Hard rules:
- the active scenario-generation layer is the front-loaded source of operational posture; do not defer recovery, fatigue, or specificity stance to Selection, Season planning, review, writer, or renderer
- the active scenario-generation layer must be self-contained for operational posture: define `recovery_margin`, `fatigue_exposure`, and `specificity_density` locally here and serialize them directly
- output exactly three scenarios
- keep numeric weekly kJ targets for season/phase planning tasks
- use canonical intensity domains
- keep scenarios advisory until selection and season planning
- use the injected deterministic planning horizon
- do not define scenarios primarily by domain breadth
- do not infer active scenario logic from past events
- do not let recommendation-default cadence silently flatten all scenarios
- do not emit A/B/C with the same `deload_cadence` unless the stored scenario fields clearly justify why cadence is intentionally held constant
- do not let Scenario C become "the VO2 scenario" by default
- do not keep `VO2MAX` in Scenario C without an explicit ceiling-support explanation in `decision_notes` or `kpi_guardrail_notes`
- do not describe `allowed_domains` as blanket legality for all phases
- do not claim that objective mismatch is resolved in this layer
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
- Fill every required narrative field with concrete scenario content; do not leave any field as generic filler that could fit all three scenarios equally.
- Keep event alignment future-only: active rehearsal, anchor, and cluster language may refer only to injected in-horizon events.
- Treat cadence as an explicit scenario dimension: even when two scenarios share cadence, explain why that is intentional and where the real differentiation sits.
- Add five short user-facing differentiators that make scenario selection easier without reading the whole prose:
  - `typical_week_feel`
  - `main_payoff`
  - `main_cost`
  - `what_gets_prioritized`
  - `what_gets_de_emphasized`
- Include assumptions and unknowns so selection can happen without recomputing dates or phase counts.
- Produce scenario guidance that helps Season Planning choose a coherent direction while preserving informational authority.
- Serialize operational posture directly in `scenario_guidance`: emit `recovery_margin`, `fatigue_exposure`, and `specificity_density` as explicit non-empty strings.
- Keep `constraint_summary`, `event_alignment_notes`, `risk_flags`, `kpi_guardrail_notes`, and `decision_notes` as structured string arrays.
- Use the precomputed phase math, event-distance facts, and availability context to set realistic scenario structure.
- Explain the tradeoff between robust, balanced, and ambitious choices in terms of exposure, recovery margin, specificity, and failure tolerance.
- Carry the code-owned recommendation into scenario notes so the selection page can explain why one cadence is currently favored, but do not mirror the recommendation cadence blindly into all scenarios.
- Return scenarios that are complete, differentiated, traceable, and ready for direct selection.

Output format:
- Return the task expected_output with scenario or scenario-interpretation fields filled explicitly.
- Include decision logic, cadence/horizon facts, event alignment, risk flags, and assumptions where available.
- Keep scenario guidance informational unless the active task makes it binding.
