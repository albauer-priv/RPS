---
name: scenario-generation
description: Generate three advisory season scenarios with coherent cadence, selection gates, future-only event logic, and bounded intensity semantics.
metadata:
  author: rps
  version: "4.2"
---
Generate `SEASON_SCENARIOS` as three advisory alternatives only.

Field completion contract:

Writing style for all narrative fields: write in plain, direct language as if explaining to the athlete in person. Concrete beats abstract. If a sentence could appear in all three scenarios, it is not good enough.

Connection between structured and narrative fields: each scenario already has concrete structured fields — `deload_cadence`, `phase_length_weeks`, `phase_count_expected`, `allowed_domains`, `season_archetype`, `recovery_margin`. The narrative fields (`core_idea`, `load_philosophy`, `typical_week_feel`, `key_differences`, etc.) are the plain-language explanation of what those structured values mean in practice. They must reference and reflect the structured fields — not float above them as abstract planning principles. A narrative field that could apply equally to a scenario with `deload_cadence: "2:1"` and one with `deload_cadence: "3:1"` has failed its purpose.

- `scenario_guidance.recovery_margin` = explicit recovery stance as a non-empty string
  - define it locally as how much schedule, fatigue, and continuity disruption the scenario can absorb before it should downshift
  - examples: `high — a missed week or a travel disruption resets cleanly without compromising the block`, `moderate — one disrupted week is absorbable but two in a row require a posture correction`, `lower — the 3:1 loading blocks depend on three consecutive execution weeks; one missed quality week late in a block is costly`
- `scenario_guidance.fatigue_exposure` = explicit fatigue posture as a non-empty string
  - examples: `low — the athlete should close most weeks feeling absorbed, not stretched`, `moderate — useful fatigue accumulates across two loading weeks; the mini-reset restores quality`, `high but conditional — three loading weeks produce real fatigue; the deload week is the recovery mechanism, not a bonus`
- `scenario_guidance.specificity_density` = explicit specificity posture as a non-empty string
  - examples: `sparse — long rides grow in duration but stay aerobic; event-pace rehearsal appears late in the season`, `controlled — long-ride specificity increases progressively around the spring B/A sequence`, `dense — repeated long rides under accumulated mid-week fatigue; Saturday rides are often started pre-fatigued by design`
- `name` = short chooser label (2–5 words, distinct across all three)
- `core_idea` = one sentence that says what this season delivers in plain terms — the outcome, not the process
  - BAD: `Protect continuity and keep the athlete fresh enough to absorb work reliably across the full horizon.` (process language, vague)
  - GOOD: `18 short phases, frequent resets — build consistent aerobic durability without deep fatigue accumulation.`
  - GOOD: `Build steadily over 4-week blocks with a mid-block reload — the reliable path to 600 km readiness.`
  - GOOD: `Three loading weeks then one full reset — highest event-specific hardness, highest execution demand.`
- `load_philosophy` = concrete description of how load is structured in this scenario: cadence rhythm, session character, what changes as the season progresses — qualitative, no invented kJ or watt numbers
  - BAD: `Moderate load with frequent recovery rhythm; prioritize repeatable execution, freshness, and consistency.` (abstract)
  - GOOD: `2:1 cadence, 3-week phases: two weeks build aerobic base and long-ride duration, one week resets. Session character stays aerobic — endurance and tempo are the main tools; no threshold or VO2MAX work appears. Load grows through longer Saturday rides and more weekly hours, not through intensity escalation. The season builds durability by accumulating many clean aerobic weeks.`
  - GOOD: `2:1:1 cadence, 4-week phases: two loading weeks, one reload week, one mini-reset. Weekday sessions stay aerobic in week 1; week 2 adds a threshold or sweet-spot session on one weekday. Saturday long rides grow progressively and include event-pace work as the 300/400 km season approaches. The reload week preserves quality without accumulating more fatigue.`
  - GOOD: `3:1 cadence, 4-week phases: three consecutive loading weeks then one full reset. Both weekday and weekend sessions carry deliberate quality across all three loading weeks. Saturday rides in loading weeks 2–3 are designed to be started with mid-week fatigue already in the legs — this is intentional specificity for long-event pacing, not a scheduling accident. The reset week is the recovery mechanism; there is no informal freshness between blocks.`
- `risk_profile` = this scenario's specific failure mode in plain language — what goes wrong and why
  - BAD: `Lowest risk option; best when travel volatility, fatigue sensitivity, or durability uncertainty need more protection.`
  - GOOD: `Lowest structural risk. If a week is lost to travel or illness, the next 3-week block starts clean. The real risk is under-adaptation: the conservative ceiling may leave the athlete underprepared for 400–600 km specificity if progression is never pushed.`
  - GOOD: `A recovery slip or two poor weeks in a row erodes the 2:1:1 rhythm. The scenario becomes less useful when the reload week doesn't actually reload — watch TSB and subjective fatigue for signs the reset week isn't recovering quality.`
  - GOOD: `High execution risk. A disrupted week in weeks 2–3 of a 3:1 block wastes two weeks of loading context. One travel week or illness near the peak of a block can turn planned fatigue into unmanaged fatigue.`
- `key_differences` = concrete structural comparison: name the cadence, phase count/length, domain breadth, and what those mean in practice
  - BAD: `Compared with B and C, this scenario keeps week-to-week pressure more controlled and asks for less fatigue exposure.`
  - GOOD: `A uses 2:1 / 3-week phases → 18 phases, resets every 3 weeks, no THRESHOLD or VO2MAX. B uses 2:1:1 / 4-week phases → 13 phases, THRESHOLD added. C uses 3:1 / 4-week phases → 13 phases, longest loading blocks, THRESHOLD + VO2MAX. A is the most interruptible; C is the least.`
- `typical_week_feel` = qualitative description of what session types appear during a representative loading week and how the athlete's legs feel across the week — no invented kJ or watt numbers, those come from downstream tasks; describe intensity character, session mix, and the end-of-week feeling
  - BAD: `Structured but manageable; the athlete should usually finish the week feeling contained rather than stretched.` (says nothing about session type or intensity)
  - GOOD (Scenario A): `Weekdays are steady endurance or tempo rides — no intervals, no threshold work. The Saturday long ride is purely aerobic, growing longer as the season progresses. The week ends with absorbed fatigue, not accumulating strain; Monday feels fresher than most of Saturday.`
  - GOOD (Scenario B): `Weekdays are mostly endurance; in loading week 2 a Thursday session adds threshold or sweet-spot quality. Saturday long rides include event-pace segments in the final portion as the season progresses. The athlete carries useful fatigue by Sunday but the mid-week quality session is consistently executable — not a stretch.`
  - GOOD (Scenario C): `Weekday sessions are deliberately harder than B — both Tuesday and Thursday carry quality in loading weeks. Saturday long rides are started with real mid-week fatigue already present, training pacing discipline under real conditions. The athlete should feel clear productive strain by Sunday, not just tiredness; the deload week is the recovery, not the Sunday rest.`
- `main_payoff` = the single most concrete gain of this scenario that the others do not deliver as well
  - BAD: `High consistency and low disruption risk across the season.` (generic, could apply to any)
  - GOOD: `More uninterrupted training weeks than any other option — a travel week or a sick day costs one 3-week block, not a 4-week one.`
  - GOOD: `The mid-block reload week means adaptation is never fully delayed — quality weeks stay achievable even when loading weeks are imperfect.`
  - GOOD: `The highest event-specific durability — repeated long rides under real fatigue develop the exact pacing resilience needed at 400–600 km.`
- `main_cost` = the single most concrete tradeoff of this scenario compared with the others
  - BAD: `Less aggressive overload pressure and slower emergence of race-specific hardness.`
  - GOOD: `Shorter phases and frequent resets limit sustained overload — the athlete may arrive at the 600 km having done more weeks but fewer truly demanding blocks than in B or C.`
  - GOOD: `Two missed quality weeks in the same four-week block erode more of the season's total loading quality than the same disruption in Scenario A.`
  - GOOD: `Three consecutive loading weeks require reliable execution every week. One travel week in the third week of a block undoes most of the block's fatigue context.`
- `what_gets_prioritized` = concrete session types and training qualities that get more emphasis in this scenario
- `what_gets_de_emphasized` = concrete session types and training qualities that get less emphasis
- `event_alignment_notes` = how this scenario specifically prepares for the athlete's in-horizon A/B events — future-only, concrete
- `constraint_summary` = how this scenario's specific structure sits inside the athlete's actual availability — scenario-specific, NOT a static repetition of the availability table
  - BAD (same for all three): `Monday and Friday remain fixed no-ride days. Typical availability is 14 hours per week.`
  - GOOD (Scenario A / 2:1 / 3-week): `At 2:1 / 3-week, the frequent reset rhythm means a disrupted week (travel, illness) costs at most one 3-week block before a clean restart — no cascading damage to longer blocks. The narrow domain ceiling (ENDURANCE + TEMPO only, no THRESHOLD) keeps every weekday session low execution-risk within the compressed Tue–Thu windows. The scenario asks for aerobic consistency, not intensity precision.`
  - GOOD (Scenario B / 2:1:1 / 4-week): `At 2:1:1 / 4-week, the reload week inside each phase means loading weeks can be genuinely demanding without the athlete needing to be fully fresh going in — the reload absorbs residual fatigue. The THRESHOLD permission makes weekday sessions purposeful in loading week 2; the compressed Tue–Thu window is enough for a focused quality session.`
  - GOOD (Scenario C / 3:1 / 4-week): `Three consecutive loading weeks require the weekend sessions to carry real training value even when weekday fatigue is present. Mon/Fri rest limits recovery within the week — the athlete must start Saturday with mid-week legs, not fresh legs. This is the training stimulus, not a constraint to work around. The planned deload week is the only guaranteed recovery point per phase.`
- `kpi_guardrail_notes` = pacing and metabolic guardrails specific to this scenario — not generic KPI prose
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

Differentiation self-test (mandatory before returning):
- For each narrative field across all three scenarios, ask: "Could this sentence be moved to a different scenario without the reader noticing?" If yes, rewrite it with concrete scenario-specific content.
- `constraint_summary` must NOT be identical across scenarios. It must describe how this scenario's specific cadence, phase structure, and domain permission interact with the athlete's available time budget — not just list the static availability table.
  - BAD (same for all three): "Monday and Friday remain fixed no-ride days. Typical availability is 14 hours per week, with a practical range of 10.5 to 25 hours."
  - GOOD (Scenario A / 2:1 / 3-week): "At 2:1 cadence with 3-week phases, the 14 h typical week produces two progressive weekends before each recovery reset — short enough to prevent deep fatigue accumulation but frequent enough to limit long-ride progression. Mon/Fri rest anchors constrain quality to Tue–Thu + Sat/Sun; the conservative domain ceiling (no THRESHOLD) keeps session density manageable within those windows."
  - GOOD (Scenario B / 2:1:1 / 4-week): "At 2:1:1 cadence with 4-week phases, two loading weekends followed by a mini-reset or reload allow progressive long-ride specificity before consolidation. The THRESHOLD permission widens the Sat/Sun session palette beyond pure endurance, supporting both durability volume and economy work within the 10.5–25 h range."
  - GOOD (Scenario C / 3:1 / 4-week): "At 3:1 cadence with 4-week phases, three consecutive loading weeks demand that weekend long rides are executed under accumulated mid-week fatigue. The 10.5–25 h range becomes the stress window, not just the budget ceiling; planned deloads are mandatory, not optional freshness."
- `key_differences` must name concrete structural facts: cadence (e.g. 2:1 vs 2:1:1), phase length, domain breadth (e.g. "no THRESHOLD"), and what that means in practice.
  - BAD: "Compared with B and C, this scenario keeps week-to-week pressure more controlled and asks for less fatigue exposure."
  - GOOD: "Scenario A uses 2:1 cadence with 3-week phases and excludes THRESHOLD and VO2MAX — a tighter reset rhythm and narrower domain ceiling than both B (2:1:1, THRESHOLD permitted) and C (3:1, THRESHOLD + VO2MAX). The shorter phase length means 18 phases vs 13 in B and C, with more frequent adaptation checkpoints but less sustained overload per block."
- `typical_week_feel` must name the dominant session type, duration range, or intensity character specific to this scenario.
  - BAD: "Structured but manageable; the athlete should usually finish the week feeling contained rather than stretched."
  - GOOD (Scenario A): "Two compact Tue–Thu sessions (1.5–3 h, ENDURANCE or TEMPO) and one longer Saturday ride (4–6 h, pure aerobic durability). Sunday is either a short recovery spin or rest. The week closes with clearly absorbed load, not accumulated strain."
  - GOOD (Scenario C): "Two focused weekday sessions (including at least one TEMPO or THRESHOLD touch) and a Saturday long ride designed to be started with mid-week fatigue already present. The athlete should feel productive strain rather than contained freshness by Sunday."
- `main_payoff` and `main_cost` must be scenario-specific claims that would be false if applied to one of the other two scenarios.
  - BAD payoff: "Best balance of adaptation, control, and practical execution." (could fit any scenario)
  - GOOD payoff (Scenario A): "Highest number of uninterrupted training weeks across the season — the 2:1/3-week rhythm is the most resilient to travel, fatigue spikes, or single-week disruptions."
  - GOOD cost (Scenario C): "The 3:1 block commits three weeks of loading before any reset — one disrupted week near the end of a block costs more accumulated quality than in A or B."
- Hard: if after reviewing all three scenarios any two share word-for-word identical sentences in `constraint_summary`, `typical_week_feel`, or `main_payoff`, those must be rewritten before returning.

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
