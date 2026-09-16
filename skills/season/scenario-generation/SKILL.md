---
name: scenario-generation
description: Generate three advisory season scenarios with coherent cadence, selection gates, future-only event logic, and bounded intensity semantics.
metadata:
  author: rps
  version: "4.2"
---
Generate `SEASON_SCENARIOS` as three advisory alternatives only.

Purpose and contract:
The scenario layer defines the qualitative character of each season option — what drives load progression (duration-led, frequency-led, or quality/intensity-led), how phases feel across their length, and what the recovery rhythm means for the athlete's week. The season planning layer executes that character as numbers: kJ targets, TSS progressions, and phase-by-phase structure. The handoff is the `scenario_guidance` block (machine-readable parameters the season planner reads directly) plus the narrative fields (human-readable explanation for the athlete and coach evaluating the options). The scenario layer must make the character choice fully explicit — load philosophy, progression direction, recovery rhythm, and qualitative session feel are ALL this layer's job. Do not defer any of these to season planning.

Field completion contract:

ORDERING: For each scenario, determine `scenario_guidance` values (`deload_cadence`, `phase_length_weeks`, `phase_count_expected`, `allowed_domains`, `season_archetype`) FIRST. Then derive each narrative field by filling its template from those exact values. The narrative fields summarize the guidance — they must NOT be written independently from it.

Each scenario has structured fields (`deload_cadence`, `phase_length_weeks`, `phase_count_expected`, `allowed_domains`, `season_archetype`) that are already concrete facts. The narrative fields below must translate those facts into plain language. Use the mandatory sentence templates below — fill in the bracketed slots from `scenario_guidance`. Do not substitute abstract planning prose for the template slots.

- `scenario_guidance.recovery_margin` — required sentence pattern: `[high/moderate/lower] — [one concrete sentence describing what disruption this scenario can absorb before it needs to downshift]`
  - example: `moderate — one disrupted week is absorbable; two in a row require a posture correction before continuing the block`
- `scenario_guidance.fatigue_exposure` — required sentence pattern: `[low/moderate/high but conditional] — [one concrete sentence describing how fatigue accumulates across the loading block]`
  - example: `moderate — useful fatigue builds across two loading weeks; the mini-reset week restores quality before the next block starts`
- `scenario_guidance.specificity_density` — required sentence pattern: `[sparse/controlled/dense] — [one concrete sentence describing when and how event-specific work appears]`
  - example: `controlled — long-ride duration and event-pace work increase progressively in the second half of the season; early phases stay aerobic`

- `core_idea` — MANDATORY TEMPLATE: `[phase_count_expected] phases, [deload_cadence] cadence — [one concrete sentence about what training outcome this season builds toward].`
  - fill in phase count and cadence from the structured fields; write the outcome in terms the athlete would recognize
  - example: `18 phases, 2:1 cadence — build consistent aerobic durability through frequent shorter blocks without deep fatigue accumulation.`
  - example: `13 phases, 2:1:1 cadence — develop event-readiness systematically over 4-week blocks with a mid-block reload to preserve quality.`
  - example: `13 phases, 3:1 cadence — train event-specific pacing discipline under real accumulated fatigue across three loading weeks before each reset.`

- `load_philosophy` — MANDATORY TEMPLATE: `[deload_cadence] cadence, [phase_length_weeks]-week phases: [describe shorter session days character in loading week 1]. [Describe what changes in loading week 2 if different — or omit if identical]. [Describe primary long session character and how it changes across the season]. [One sentence on what drives load progression in this scenario — duration, frequency, or quality].`
  - fill slot values from the scenario's `allowed_domains`, `deload_cadence`, and the athlete's availability structure
  - example: `2:1 cadence, 3-week phases: both loading weeks are aerobic — endurance and tempo on shorter session days, a progressively longer aerobic ride on the primary long session day. No threshold or interval work appears. Load grows through longer long sessions and slightly higher weekly volume, not through intensity escalation.`
  - example: `2:1:1 cadence, 4-week phases: loading week 1 keeps all sessions aerobic; loading week 2 adds a threshold or sweet-spot session on one shorter session day. The primary long ride grows progressively and includes event-pace work as the A-event approaches. The reload week preserves the quality achieved without adding more fatigue.`
  - example: `3:1 cadence, 4-week phases: all three loading weeks carry deliberate quality on both shorter session days and the primary long session day. Long sessions in weeks 2–3 are started with real prior-day fatigue already in the legs — intentional specificity, not a scheduling accident. The reset week is the only recovery window per phase.`

- `risk_profile` — MANDATORY TEMPLATE: `[Lowest/Moderate/Highest] structural risk. [One concrete sentence about the specific failure mode for this scenario]. [One sentence on what to watch for].`
  - example: `Lowest structural risk. A lost week resets into the next 3-week block cleanly. The real failure mode is under-adaptation: frequent resets limit sustained overload and the athlete may arrive underprepared for 400–600 km specificity.`
  - example: `Moderate structural risk. The scenario weakens when the reload week doesn't actually restore quality — watch subjective fatigue and TSB; if the reload week feels like more loading, adjust before the next block.`
  - example: `Highest structural risk. A disrupted week in the second or third week of a 3:1 block wastes the accumulated loading context of the entire block. Travel or illness late in a block turns planned fatigue into unmanaged fatigue.`

- `key_differences` — MANDATORY TEMPLATE: `[This scenario's cadence/phase structure vs. the other two, as concrete facts]. [One sentence on what the domain permission means for session character]. [One sentence on which scenario to choose if you want more, and which if you want less].`
  - example: `A: 2:1 / 3-week → 18 phases, ENDURANCE+TEMPO only. B: 2:1:1 / 4-week → 13 phases, adds THRESHOLD. C: 3:1 / 4-week → 13 phases, adds THRESHOLD+VO2MAX. A resets most often and asks for the least intensity precision; C loads longest and asks for the most execution consistency.`

- `typical_week_feel` — MANDATORY TEMPLATE: `Shorter session days are [intensity character: e.g. steady endurance / endurance with one quality session in loading week 2 / deliberately hard on multiple days]. The primary long session is [long session character: e.g. purely aerobic, growing longer each phase / progressively event-specific in the second half / started with prior-day fatigue by design]. The athlete closes most loading weeks feeling [absorbed / carrying useful fatigue / with productive strain].`
  - fill in the slots based on the scenario's `allowed_domains` and `deload_cadence` — derive session character from the availability structure, not from assumed day names
  - example: `Shorter session days are steady endurance or tempo — no intervals, no threshold work in any loading week. The primary long session is purely aerobic, growing longer as the season progresses. The athlete closes most loading weeks feeling absorbed, not stretched.`
  - example: `Shorter session days are mostly endurance; loading week 2 adds threshold or sweet-spot quality on one of them. The primary long ride becomes progressively event-specific in the second half of the season. The athlete carries useful fatigue at the end of loading weeks but the mid-week quality session remains consistently executable.`
  - example: `Shorter session days are deliberately hard in all loading weeks — quality appears on multiple days, not just one. The primary long session is started with prior-day fatigue already in the legs, training pacing discipline under real conditions. The athlete closes most loading weeks carrying productive strain; the deload week is the recovery, not the last day's rest.`

- `main_payoff` — one concrete sentence about what this scenario delivers that the other two do not deliver as well; must be false if applied to either of the other two scenarios
  - example: `More uninterrupted training weeks than any other option — a travel week or a sick day costs one 3-week block, not a 4-week one.`
  - example: `The reload week inside each block means quality weeks stay achievable even when loading weeks are imperfect — the adaptation rhythm is never fully broken.`
  - example: `The highest event-specific hardness — repeated long rides under accumulated fatigue build the pacing resilience needed for 400–600 km conditions.`

- `main_cost` — one concrete sentence about the specific tradeoff of this scenario relative to the others; must be false if applied to either of the other two scenarios
  - example: `Frequent resets limit sustained overload — the athlete may arrive at the 600 km having done more total weeks but fewer truly demanding loading blocks than in B or C.`
  - example: `Two poor weeks in the same 4-week block cost more than the same disruption in Scenario A, because the reload week cannot fully compensate for two missed loading weeks.`
  - example: `Three consecutive loading weeks require reliable execution every week — one travel week in the third week of a block undoes most of the block's fatigue context.`

- `what_gets_prioritized` = concrete session types and training qualities that get more emphasis in this scenario
- `what_gets_de_emphasized` = concrete session types and training qualities that get less emphasis
- `event_alignment_notes` = how this scenario specifically prepares for the athlete's in-horizon A/B events — future-only, concrete
- `constraint_summary` — MANDATORY: scenario-specific string array, NOT a repetition of the static availability table; each entry must describe how this scenario's cadence/phase structure interacts with the athlete's actual constraints
  - entry 1 template: `At [cadence] / [phase_length_weeks]-week, [one concrete implication for how disruptions interact with the block structure].`
  - entry 2 template: `[Domain permission] means weekday sessions are [execution character: low execution risk / capable of carrying a focused quality session / demanding on multiple days].`
  - entry 3 (if applicable): `[Indoor/outdoor or logistics constraint and how it specifically affects this scenario's structure].`
  - example entries for a 2:1 / 3-week / ENDURANCE+TEMPO scenario: `["At 2:1 / 3-week, a disrupted week costs one 3-week block then resets cleanly — no cascading damage to a longer block.", "ENDURANCE+TEMPO only means every session day is low execution risk; no intensity precision is required on shorter session days.", "Indoor fallback preserves most long-ride aerobic value in winter months without requiring outdoor conditions."]`

- `kpi_guardrail_notes` = pacing and metabolic guardrails specific to this scenario — not generic KPI prose
- `decision_notes` = why this cadence and posture were chosen; structured string array
- `assumptions` = what must stay true for this scenario to remain valid
- `unknowns` = what could change scenario choice later
- `data.notes` = global scenario-layer clarifications (future-only event scope, allowed_domains as eligibility not obligation, etc.)

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
- Scenario C VO2MAX hard rule: Scenario C may include `VO2MAX` only when it is explicitly justified as `sparse ceiling-support`, `fresh-only`, `not primary identity`, and ambition sourced from `specificity-under-fatigue`, `density`, `event simulation`, or `load posture` — OR when `season_archetype: "ceiling_first_durability"` applies (see "Athlete VO2max development objectives" below), in which case VO2MAX is a deliberate early-phase build intent, not sparse ceiling-support, and the framing must reflect that.
- If that rationale cannot be stated explicitly in `decision_notes` and/or `kpi_guardrail_notes`, omit `VO2MAX` from Scenario C `allowed_domains`.
- Preferred copyable sentence when Scenario C allows `VO2MAX` without `ceiling_first_durability`: `VO2MAX remains sparse ceiling-support only when fresh-only, not primary identity; the scenario ambition comes from specificity-under-fatigue, density, and event simulation.`
- Preferred copyable sentence when Scenario uses `ceiling_first_durability`: `VO2MAX is permitted as an early-season aerobic-ceiling build in the first two phases only; from phase 3 onward the emphasis shifts to durability, economy, and VLamax-lowering.`
- Scenarios B and C may legitimately share identical `allowed_domains` when their kJ-envelope, specificity, fatigue exposure, density, and risk contract are clearly different.
- Scenarios may share identical `deload_cadence` only when the stored scenario fields explicitly say cadence is intentionally held constant and explain which other axes carry the differentiation.
- Cluster wording (`cluster`, `event cluster`, `B-event cluster`, `peak cluster`) requires multiple relevant in-horizon events; otherwise use singular event wording.
- If Scenario C includes `VO2MAX`, the scenario story must explicitly say it is a sparse / limited / occasional ceiling-support or fresh-only permission, include the exact phrase `not primary identity`, and say that the ambition instead comes from `specificity-under-fatigue`, `density`, `event simulation`, or `load posture`.

Season archetype semantics:
- `season_archetype` is a normalized scenario-level semantic, not a new cycle type.
- Use `none` by default — EXCEPT when the "Athlete VO2max development objectives" rule below mandates `ceiling_first_durability` for at least one scenario.
- Use `ceiling_first_durability` when: (a) the athlete profile mandates it (see below) OR (b) the scenario explicitly supports a ceiling-first then economy/durability sequence on other grounds.
- `ceiling_first_durability` is supported by:
  - enough planning runway before peak (≥ 20 weeks)
  - explicit aerobic ceiling development goal in athlete profile
  - weekday time-crunch / weekend leverage
  - recovery tolerance that can support conditional early VO2
- When the athlete profile mandates ceiling_first, the scenario IS the mechanism that justifies it — shape the scenario to support the archetype, not the other way around.
- If `season_archetype = ceiling_first_durability`, `season_archetype_rationale` must state why early ceiling support is permitted and why later durability/specificity work still has enough runway.

Athlete VO2max development objectives:
- When `athlete_profile.objectives.secondary` or `objectives.priority_order` contains explicit VO2max development language AND the planning runway is ≥ 20 weeks, the scenario layer MUST generate at least one scenario with `season_archetype: "ceiling_first_durability"` and `VO2MAX` in `intensity_guidance.allowed_domains`.
- This is not an objective mismatch — it is a direct and binding planning directive from the athlete profile that must be honoured in at least one scenario.
- The ceiling-first scenario typically shapes Scenario C; it may shape Scenario B when Scenario C is already differentiated by higher specificity-under-fatigue and load rather than intensity archetype.
- Apply the `ceiling_first_durability` rationale as: long planning runway (≥ 20 weeks), explicit aerobic ceiling development goal, weekday time-crunch with weekend leverage all support conditional early VO2max work before durability volume expansion — with sufficient horizon remaining for the economy/durability block after the VO2 phase.
- VO2MAX in the ceiling-first scenario must still be framed as early-season ceiling-support: fresh-only, time-limited to the first two phases, and not a season-wide permission.
- Write the `season_archetype_rationale` using concrete athlete-profile facts (planning runway in weeks, explicit VO2max objective text, weekday vs. weekend availability asymmetry) so the rationale is unambiguous to the macrocycle-architecture task.
- POSITIVE EXAMPLE — what a correct ceiling_first_durability scenario C looks like:
  - `season_archetype: "ceiling_first_durability"`
  - `season_archetype_rationale`: `["52-week planning runway provides enough horizon for 2 VO2-build phases (~8 weeks) before the durability block, leaving ≥ 30 weeks for economy, VLamax-lowering, and specificity. Athlete profile explicitly states 'Increase aerobic capacity (VO2max)' and 'Increase VO2max, lower VLamax' as priority 3. Weekend leverage (up to 8h outdoor / 4h indoor) can support fresh VO2max intervals within compact weekday windows. VO2MAX is permitted only in phases 1–2 as an early aerobic ceiling build; from phase 3 onward the emphasis shifts to durability, economy, and VLamax-lowering."]`
  - `intensity_guidance.allowed_domains`: `["RECOVERY", "ENDURANCE", "TEMPO", "VO2MAX"]` (VO2MAX active, THRESHOLD suppressed in the VO2 block; THRESHOLD may return in later durability/build phases)
  - `decision_notes` must include: "VO2MAX is permitted as an early-season aerobic-ceiling build in the first two phases only; from phase 3 onward the emphasis shifts to durability, economy, and VLamax-lowering."

Seasonal availability context:
- When `seasonal_context` is present in the injected context, read `outdoor_season_months`, `indoor_dominant_months`, `indoor_weekend_max_hours`, and `outdoor_weekend_max_hours`.
- For phases whose ISO-week range falls predominantly inside `indoor_dominant_months`: describe lower practical volume ceilings for weekend long rides (cap at `indoor_weekend_max_hours` rather than the static table max), note the indoor-trainer character of those sessions, and reflect that intensity density relative to volume may be higher than in outdoor months.
- For phases inside `outdoor_season_months`: weekend long rides may reach `outdoor_weekend_max_hours`; describe outdoor riding character, terrain leverage, and durability volume potential.
- Carry this distinction into the scenario's `load_philosophy`, `event_alignment_notes`, and `decision_notes` where season character differs meaningfully between indoor and outdoor phases.
- Do not alter the weekly `hours_min/typical/max` aggregate figures; `seasonal_context` is advisory shaping context only.
- If `seasonal_context` is absent, do not invent seasonal character — proceed with the static availability table only.

Objective mismatch semantics:
- If the scenario layer notices a mismatch between upstream objective language and active event hierarchy, treat it as unresolved upstream input context only.
- You may name that mismatch in notes, assumptions, unknowns, or caution fields.
- Do not claim that the scenario layer resolved or replaced the objective/event hierarchy.
- CRITICAL EXCEPTION — VO2max development objective is NOT an objective mismatch: language like "Increase aerobic capacity (VO2max)", "Increase VO2max", or similar in `objectives.secondary` or `objectives.priority_order` is a physiological training directive, categorically different from a competitive-ambition mismatch. DO NOT bundle VO2max development into the same mismatch note as competitive ambition. Treat it as an active, binding planning directive and honour it in the ceiling-first scenario. Surfacing VO2max development as a warning-only note or mismatch when the planning runway supports ceiling-first is a skill error.

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

3-pass verification (mandatory before returning):

Pass 1 — Contract alignment: do the narrative fields fulfill the scenario layer's job?
- For each scenario: does `load_philosophy` explicitly name what drives load progression — duration-led, frequency-led, or quality/intensity-led? If not, rewrite it. This is the primary character handoff to season planning.
- Does `core_idea` state the phase count, cadence, and the season outcome the athlete is building toward? If it reads like a mood word or abstract goal instead of a structural description, rewrite it.
- Does `typical_week_feel` describe session character (what intensity domains appear, when, how the legs feel across the week) derived from `allowed_domains` and cadence — not from assumed day names? If it reads like scheduling language instead of session feel, rewrite it.
- Are `recovery_margin`, `fatigue_exposure`, and `specificity_density` in `scenario_guidance` non-empty explicit strings? These are the machine-readable character parameters the season planner reads directly. If any is empty or deferred, fill it now.

Pass 2 — Template compliance: do the fields open correctly?
- Each scenario's `core_idea` must start with a number, e.g. "18 phases, 2:1 cadence —". If any starts with anything else (e.g. "Protect…", "Progress…", "Use…"), rewrite it using the phase count and cadence from `scenario_guidance`.
- Each scenario's `load_philosophy` must start with the cadence string, e.g. "2:1 cadence, 3-week phases:". If any starts with a mood word or generic description, rewrite it.
- Each scenario's `typical_week_feel` must start with "Shorter session days are". If any starts with anything else, rewrite it.
- `constraint_summary` entries must follow the entry templates (see below). If any entry reads as the static availability table instead of cadence-specific interaction, rewrite it.

Pass 3 — Cross-scenario differentiation: would a reader know which scenario they're reading?
- For each narrative field across all three scenarios, ask: "Could this sentence be moved to a different scenario without the reader noticing?" If yes, rewrite it with concrete scenario-specific content.
- Hard: if any two scenarios share word-for-word identical sentences in `constraint_summary`, `typical_week_feel`, or `main_payoff`, those must be rewritten before returning.
- `main_payoff` and `main_cost` must be scenario-specific claims that would be false if applied to one of the other two scenarios.
  - BAD payoff: "Best balance of adaptation, control, and practical execution." (could fit any scenario)
  - GOOD payoff (Scenario A): "Highest number of uninterrupted training weeks across the season — the 2:1/3-week rhythm is the most resilient to travel, fatigue spikes, or single-week disruptions."
  - GOOD cost (Scenario C): "The 3:1 block commits three weeks of loading before any reset — one disrupted week near the end of a block costs more accumulated quality than in A or B."
- `key_differences` must name concrete structural facts: cadence (e.g. 2:1 vs 2:1:1), phase length, domain breadth (e.g. "no THRESHOLD"), and what that means in practice.
  - BAD: "Compared with B and C, this scenario keeps week-to-week pressure more controlled and asks for less fatigue exposure."
  - GOOD: "Scenario A uses 2:1 cadence with 3-week phases and excludes THRESHOLD and VO2MAX — a tighter reset rhythm and narrower domain ceiling than both B (2:1:1, THRESHOLD permitted) and C (3:1, THRESHOLD + VO2MAX). The shorter phase length means 18 phases vs 13 in B and C, with more frequent adaptation checkpoints but less sustained overload per block."
- `typical_week_feel` must follow the MANDATORY TEMPLATE exactly: start with "Shorter session days are [character]", then "The primary long session is [character]", then end with the absorbed/fatigue clause. Generic mood words are not acceptable substitutes.
  - BAD: "Structured but manageable; the athlete should usually finish the week feeling contained rather than stretched."
  - BAD: "Purposeful and progressive; work is clearly present, but recovery remains visible and usable."
  - GOOD (Scenario A / 2:1 / 3-week / ENDURANCE+TEMPO): "Shorter session days are steady endurance or tempo — no intervals, no threshold work in any loading week. The primary long session is purely aerobic, growing progressively longer each phase. The athlete closes most loading weeks feeling absorbed."
  - GOOD (Scenario B / 2:1:1 / 4-week / adds THRESHOLD): "Shorter session days are mostly endurance; loading week 2 adds a threshold or sweet-spot session on one of them. The primary long session grows progressively and includes event-pace work in the second half. The athlete closes most loading weeks carrying useful fatigue but the quality session remains consistently executable."
  - GOOD (Scenario C / 3:1 / 4-week / THRESHOLD): "Shorter session days are deliberately quality-focused in all three loading weeks — threshold or sweet-spot work appears on at least one shorter session day every week. The primary long session is started with prior-day fatigue already in the legs. The athlete closes most loading weeks carrying productive strain; the deload week is the only recovery window."
- `constraint_summary` must NOT be identical across scenarios. It must describe how this scenario's specific cadence, phase structure, and domain permission interact with the athlete's available time budget — not just list the static availability table.
  - BAD (same for all three): "Monday and Friday remain fixed no-ride days. Typical availability is 14 hours per week, with a practical range of 10.5 to 25 hours."
  - GOOD (Scenario A / 2:1 / 3-week): "At 2:1 / 3-week, a disrupted week resets into the next block cleanly — two loading weeks then a reset is a short enough cycle that one missed week never cascades. ENDURANCE+TEMPO only means shorter session days carry low execution risk; no intensity precision is required on any weekday."
  - GOOD (Scenario B / 2:1:1 / 4-week): "At 2:1:1 / 4-week, two loading weeks then a reload mean the reload week is the continuity safety valve — one poor loading week can still be salvaged if the reload restores quality. THRESHOLD permission means loading week 2 shorter sessions carry a quality ask; if those sessions are missed the reload may not fully compensate."
  - GOOD (Scenario C / 3:1 / 4-week): "At 3:1 / 4-week, three consecutive loading weeks mean a disrupted week near the end of a block wastes the accumulated loading context of the whole block — there is no mid-block reload. THRESHOLD permission means shorter session days in all three loading weeks carry a quality ask; execution reliability on those sessions directly determines whether the fatigue load is useful or just damaging."

Hard rules:
- the active scenario-generation layer is the front-loaded source of operational posture; do not defer recovery, fatigue, or specificity stance to Selection, Season planning, review, writer, or renderer
- the active scenario-generation layer must be self-contained for operational posture: define `recovery_margin`, `fatigue_exposure`, and `specificity_density` locally here and serialize them directly
- examples illustrate structure and specificity only; do not mechanically reuse example sentences in `constraint_summary`, and apply the same principle to `event_alignment_notes`, `risk_flags`, `kpi_guardrail_notes`, and `decision_notes`
- CEILING-FIRST MANDATE: if `athlete_profile.objectives.secondary` or `objectives.priority_order` contains VO2max development language AND planning runway ≥ 20 weeks, emitting `season_archetype: "none"` for all three scenarios is a hard error — at least one scenario MUST use `ceiling_first_durability` with `VO2MAX` in `allowed_domains`; check this before returning and revise if violated
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
- Before returning, run this self-check: (1) Does the athlete profile contain VO2max development language? (2) Is the planning runway ≥ 20 weeks? If both are true and all three scenarios still have `season_archetype: "none"`, stop — revise the highest-ambition scenario to use `ceiling_first_durability` before returning. This check is mandatory, not optional.
- Return scenarios that are complete, differentiated, traceable, and ready for direct selection.

Output format:
- Return the task expected_output with scenario or scenario-interpretation fields filled explicitly.
- Include decision logic, cadence/horizon facts, event alignment, risk flags, and assumptions where available.
- Keep scenario guidance informational unless the active task makes it binding.
