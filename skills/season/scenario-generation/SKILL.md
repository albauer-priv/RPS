---
name: scenario-generation
description: Generate three advisory season scenarios with coherent cadence, selection gates, future-only event logic, and advisory intensity narrative.
metadata:
  author: rps
  version: "4.8"
---
Generate `SEASON_SCENARIOS` as three advisory alternatives only.

Purpose and contract:
The scenario layer defines the qualitative character of each season option — what drives load progression (duration-led, frequency-led, or quality/intensity-led), how phases feel across their length, and what the recovery rhythm means for the athlete's week. The season planning layer executes that character as numbers: kJ targets, TSS progressions, and phase-by-phase structure. The handoff is the `scenario_guidance` block (machine-readable parameters the season planner reads directly) plus the narrative fields (human-readable explanation for the athlete and coach evaluating the options). The scenario layer must make the character choice fully explicit — load philosophy, progression direction, recovery rhythm, and qualitative session feel are ALL this layer's job. Do not defer any of these to season planning.

The foundational principles behind all scenario decisions are documented in `references/kj_first_durability_philosophy.md` (kJ-first principle, progression order, decision hierarchy) and in `skills/shared/durability-methodology/SKILL.md` (full durability decision rules). Use them as justification when writing `decision_notes`, `load_philosophy`, and `risk_profile` — they are the "why" behind each scenario's structure.

Field completion contract:

ORDERING: For each scenario, determine `scenario_guidance` values (`deload_cadence`, `phase_length_weeks`, `phase_count_expected`, `season_archetype`) FIRST. Then derive each narrative field by filling its template from those exact values. The narrative fields summarize the guidance — they must NOT be written independently from it.

Each scenario has structured fields (`deload_cadence`, `phase_length_weeks`, `phase_count_expected`, `season_archetype`) that are already concrete facts. The narrative fields below must translate those facts into plain language. Use the mandatory sentence templates below — fill in the bracketed slots from `scenario_guidance`. Do not substitute abstract planning prose for the template slots.

- `scenario_guidance.recovery_margin` = explicit recovery stance as a non-empty string — required sentence pattern: `[high/moderate/lower] — [one concrete sentence describing what disruption this scenario can absorb before it needs to downshift]`
  - example: `moderate — one disrupted week is absorbable; two in a row require a posture correction before continuing the block`
- `scenario_guidance.fatigue_exposure` = explicit fatigue posture as a non-empty string — required sentence pattern: `[low/moderate/high but conditional] — [one concrete sentence describing how fatigue accumulates across the loading block]`
  - example: `moderate — useful fatigue builds across two loading weeks; the mini-reset week restores quality before the next block starts`
- `scenario_guidance.specificity_density` = explicit specificity posture as a non-empty string — required sentence pattern: `[sparse/controlled/dense] — [one concrete sentence describing when and how event-specific work appears]`
  - example: `controlled — long-ride duration and event-pace work increase progressively in the second half of the season; early phases stay aerobic`

- `core_idea` = one-sentence scenario promise — MANDATORY TEMPLATE: `[phase_count_expected] phases, [deload_cadence] cadence — [one concrete sentence about what training outcome this season builds toward].`
  - fill in phase count and cadence from the structured fields; write the outcome in terms the athlete would recognize
  - example: `18 phases, 2:1 cadence — build consistent aerobic durability through frequent shorter blocks without deep fatigue accumulation.`
  - example: `13 phases, 2:1:1 cadence — develop event-readiness systematically over 4-week blocks with a mid-block reload to preserve quality.`
  - example: `13 phases, 3:1 cadence — train event-specific pacing discipline under real accumulated fatigue across three loading weeks before each reset.`

- `load_philosophy` — MANDATORY TEMPLATE: `[deload_cadence] cadence, [phase_length_weeks]-week phases: [describe shorter session days character in loading week 1]. [Describe what changes in loading week 2 if different — or omit if identical]. [Describe primary long session character and how it changes across the season]. [One sentence on what drives load progression in this scenario — duration, frequency, or quality].`
  - fill slot values from the scenario's `deload_cadence`, the intensity character in `intensity_guidance`, and the athlete's availability structure
  - example: `2:1 cadence, 3-week phases: both loading weeks are aerobic — endurance and tempo on shorter session days, a progressively longer aerobic ride on the primary long session day. No threshold or interval work appears. Load grows through longer long sessions and slightly higher weekly volume, not through intensity escalation.`
  - example: `2:1:1 cadence, 4-week phases: loading week 1 keeps all sessions aerobic; loading week 2 adds a threshold or sweet-spot session on one shorter session day. The primary long ride grows progressively and includes event-pace work as the A-event approaches. The reload week preserves the quality achieved without adding more fatigue.`
  - example: `3:1 cadence, 4-week phases: all three loading weeks carry deliberate quality on both shorter session days and the primary long session day. Long sessions in weeks 2–3 are started with real prior-day fatigue already in the legs — intentional specificity, not a scheduling accident. The reset week is the only recovery window per phase.`

- `risk_profile` — MANDATORY TEMPLATE: `[Lowest/Moderate/Highest] structural risk. [One concrete sentence about the specific failure mode for this scenario]. [One sentence on what to watch for].`
  - example: `Lowest structural risk. A lost week resets into the next 3-week block cleanly. The real failure mode is under-adaptation: frequent resets limit sustained overload and the athlete may arrive underprepared for 400–600 km specificity.`
  - example: `Moderate structural risk. The scenario weakens when the reload week doesn't actually restore quality — watch subjective fatigue and TSB; if the reload week feels like more loading, adjust before the next block.`
  - example: `Highest structural risk. A disrupted week in the second or third week of a 3:1 block wastes the accumulated loading context of the entire block. Travel or illness late in a block turns planned fatigue into unmanaged fatigue.`

- `key_differences` — MANDATORY TEMPLATE: `[This scenario's cadence/phase structure vs. the other two, as concrete facts]. [One sentence on what the domain permission means for session character]. [One sentence on which scenario to choose if you want more, and which if you want less].`
  - example (horizon < 20 w, no ceiling-first): `A: 2:1 / 3-week → 18 phases, ENDURANCE+TEMPO only. B: 2:1:1 / 4-week → 13 phases, adds THRESHOLD. C: 3:1 / 4-week → 13 phases, adds THRESHOLD+VO2MAX. A resets most often and asks for the least intensity precision; C loads longest and asks for the most execution consistency.`
  - example (ceiling-first, horizon ≥ 20 w): `A: 2:1 / 3-week → 18 phases, ceiling-first Kinzlbauer sequence, conservative kJ / highest recovery margin. B: 2:1:1 / 4-week → 13 phases, ceiling-first, target kJ / balanced posture. C: 3:1 / 4-week → 13 phases, ceiling-first, upper kJ / more B2B fatigue exposure. All three follow vo2_base → vo2_build → vlamax_lowering → durability; A resets most often with least accumulated fatigue per block, C loads longest and exposes the most.`

- `typical_week_feel` — MANDATORY TEMPLATE: `Shorter session days are [intensity character: e.g. steady endurance / endurance with one quality session in loading week 2 / deliberately hard on multiple days]. The primary long session is [long session character: e.g. purely aerobic, growing longer each phase / progressively event-specific in the second half / started with prior-day fatigue by design]. The athlete closes most loading weeks feeling [absorbed / carrying useful fatigue / with productive strain].`
  - fill in the slots based on the scenario's intensity narrative and `deload_cadence` — derive session character from the availability structure, not from assumed day names
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
- `event_alignment_notes` = future-only active event logic — how this scenario specifically prepares for the athlete's in-horizon A/B events; future-only, concrete
- `constraint_summary` — MANDATORY: scenario-specific string array, NOT a repetition of the static availability table; each entry must describe how this scenario's cadence/phase structure interacts with the athlete's actual constraints
  - entry 1 template: `At [cadence] / [phase_length_weeks]-week, [one concrete implication for how disruptions interact with the block structure].`
  - entry 2 template: `[Domain permission] means weekday sessions are [execution character: low execution risk / capable of carrying a focused quality session / demanding on multiple days].`
  - entry 3 (if applicable): `[Indoor/outdoor or logistics constraint and how it specifically affects this scenario's structure].`
  - example entries for a 2:1 / 3-week / ENDURANCE+TEMPO scenario: `["At 2:1 / 3-week, a disrupted week costs one 3-week block then resets cleanly — no cascading damage to a longer block.", "ENDURANCE+TEMPO only means every session day is low execution risk; no intensity precision is required on shorter session days.", "Indoor fallback preserves most long-ride aerobic value in winter months without requiring outdoor conditions."]`
  - `constraint_summary` entry patterns (structural guidance; do not copy sentences):
    - fixed rest-day constraint pattern: short operational sentence naming non-training anchors; valid examples: `Monday and Friday remain fixed no-ride days.` / `The weekly structure keeps Monday and Friday as fixed rest days.`
    - weekday vs weekend availability asymmetry pattern: short sentence explaining compact weekday windows and longer weekend capacity; valid examples: `Weekday training has to fit into compact Tue-Thu windows, with longer work shifting to the weekend.` / `The load-bearing time budget sits mainly on the weekend because weekday availability stays compressed.`
    - indoor / weather / travel continuity pattern: short sentence explaining fallback continuity when outdoor execution is disrupted; valid examples: `Indoor trainer access preserves continuity when weather or travel disrupts outdoor riding.` / `Travel or poor weather can be absorbed more safely because indoor fallback remains available.`

- `kpi_guardrail_notes` = pacing and metabolic guardrails specific to this scenario — not generic KPI prose
- `decision_notes` = why this cadence and posture were chosen; structured string array
- `assumptions` = what must stay true for this scenario to remain valid
- `unknowns` = what could change scenario choice later
- `data.notes` = global scenario-layer clarifications (future-only event scope, objective mismatch handling, etc.)

Method:
1. Respect the injected deterministic horizon context, future-only A/B/C event inventory, athlete profile, availability, logistics, and KPI context.
1a. **CEILING-FIRST PRE-CHECK — do this before generating any scenario:**
    - Is `inclusive_planning_horizon_weeks` ≥ 20?
    - If YES: ALL three scenarios (A, B, C) MUST use `season_archetype: "ceiling_first_durability"`. Ceiling-first is the RPS default methodology — no athlete objective check required. The Kinzlbauer sequence is the base structure for every scenario; differentiation across A/B/C comes from kJ envelope, cadence, recovery margin, and fatigue exposure only.
    - If NO (< 20 weeks): use `season_archetype: "none"` — insufficient runway for the full Kinzlbauer sequence.
    - Shape every scenario to support the ceiling-first archetype from the start. Do NOT generate generic scenarios and then patch the `season_archetype` field afterward — this produces internally inconsistent outputs that will be rejected by the guardrail.
    - Carry this decision into steps 2–3: Scenario A = ceiling-first with conservative kJ and high recovery margin; Scenario B = ceiling-first with target kJ and balanced posture; Scenario C = ceiling-first with upper kJ, higher specificity under fatigue, and more B2B work in the durability phase.
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
- use top-level `data.notes` for global scenario-layer clarifications such as warning-only objective mismatch handling

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
  - lower feasible kJ-envelope, high recovery margin, low density, minimal intensity allowance
  - high executability under work stress, illness risk, or masters recovery limits
  - `best_suited_if` must name `continuity priority`, `uncertain recovery`, `recoverability`, or `logistics robustness`
  - preferred example: `Choose when continuity priority and uncertain recovery dominate.`
  - `risk_flags` must name `under-deliver` or `too conservative` (required in all contexts — in ceiling-first the conservatism is in kJ load and recovery margin, not domain selection)
  - preferred example: `May under-deliver if high load tolerance is available.`
- **Scenario B = durability-forward target plan**
  - realistic target kJ-envelope, systematic long-ride progression, selected `TEMPO` / optional `SWEET_SPOT`, balanced recovery risk
  - `best_suited_if` must say `stable recovery` supports `systematic progression`
  - preferred example: `Choose when stable recovery supports systematic progression.`
  - `risk_flags` must name `continuity break` or `recovery slip`
  - preferred example: `Less forgiving than A if continuity break or recovery slip appears.`
- **Scenario C = ambitious performance-forward long build**
  - upper plausible kJ-envelope, higher specificity under fatigue, more B2B / hard-late / event simulation
  - in ceiling-first: highest-kJ ceiling-first variant — more B2B and durability-phase load, same Kinzlbauer phase sequence as A and B
  - `best_suited_if` must say `stable recovery`, `high load tolerance`, or `fatigue exposure tolerance`
  - preferred example: `Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.`
  - `risk_flags` must name `too aggressive` when `fatigue risk`, `travel disruption`, `logistics disruption`, or `insufficient tolerance` appears
  - preferred example: `Too aggressive if fatigue risk or travel disruption appears.`
  - ambition comes from specificity and fatigue exposure, not from automatic high-intensity escalation

Scenario math rules:
- `planning_horizon_weeks` must match the inclusive week span of `meta.iso_week_range`.
- if deterministic horizon context is present, it is the source of truth for scenario horizon math
- `phase_count_expected`, `shortening_budget_weeks`, `phase_plan_summary`, and `max_shortened_phases` must stay consistent with horizon length and declared phase length.
- `deload_cadence` is part of the scenario identity, not decorative structure metadata.
- If `shortening_budget_weeks = 0`, then `max_shortened_phases = 0`.
- `intensity_guidance` must use canonical agenda intensity domains only: `NONE`, `RECOVERY`, `ENDURANCE`, `TEMPO`, `SWEET_SPOT`, `THRESHOLD`, `VO2MAX`.
- Keep `avoid_domains` to trainable intensity domains; use `NONE` and `RECOVERY` only for availability/recovery semantics.

Intensity-domain semantics:
- `intensity_guidance.allowed_domains` is **documentary and advisory only** — all canonical intensity domains are permitted at the season level; the phase layer owns intensity gating via canonical phase-intent semantics. The field remains in the JSON for narrative coherence.
- `allowed_domains` are permissions, not obligations — they describe the expected session-intensity character, not a requirement to use every listed domain in every phase.
- Write `allowed_domains` to honestly reflect which intensity domains the scenario's session character draws on. This keeps `typical_week_feel` and the rest of the scenario narrative coherent.
- `ENDURANCE` is the core domain of every scenario.
- `TEMPO` is in many ultra/brevet contexts the most likely first additional domain because it supports sub-threshold economy and long stable duration, but it is not dogma.
- `SWEET_SPOT` is optional when time budget limits kJ separation or when economy / sustained sub-threshold work is part of the scenario story.
- `THRESHOLD` and `VO2MAX` are special-case entries, not default markers of ambition.
- Scenario C is not defined by `VO2MAX`.
- Scenarios may share identical `deload_cadence` only when the stored scenario fields explicitly say cadence is intentionally held constant and explain which other axes carry the differentiation.
- Cluster wording (`cluster`, `event cluster`, `B-event cluster`, `peak cluster`) requires multiple relevant in-horizon events; otherwise use singular event wording.

Ceiling-first as RPS default methodology:
- Ceiling-first is the default RPS planning approach for any season with `inclusive_planning_horizon_weeks` ≥ 20. No athlete objective check required — this applies to every athlete, every plan.
- The Kinzlbauer phase sequence is the base structure for ALL scenarios: `aerobic_base` (GPP) → `vo2_base` (VO2 Foundation) → `vo2_build` (VO2 Build) → `vlamax_lowering` (economy/VLamax-lowering) → `durability_build` (specific durability). Scenarios A/B/C share this sequence and differ in kJ envelope, cadence, recovery margin, and fatigue exposure only.
- **Guardrail correction rule**: when a guardrail rejects scenarios for missing `ceiling_first_durability`, the correct fix is to add the archetype to ALL scenarios and write the required rationale — do NOT remove it from any scenario. Removing it from any scenario is a hard error.
- VO2MAX must be framed as early-season ceiling-support in ALL scenarios: fresh-only, time-limited to the `vo2_base` + `vo2_build` phases, and not a season-wide permission. From `vlamax_lowering` onward the emphasis shifts to economy and durability in all scenarios.
- Write the `season_archetype_rationale` using concrete context facts (planning runway in weeks, weekday vs. weekend availability asymmetry, remaining horizon after VO2 phases) so the rationale is unambiguous to the macrocycle-architecture task.
- POSITIVE EXAMPLE — how all three scenarios look:
  - **Shared across A/B/C**: `season_archetype: "ceiling_first_durability"`, same Kinzlbauer phase sequence: `aerobic_base` → `vo2_base` → `vo2_build` → `vlamax_lowering` → `durability_build`.
  - **Differentiation axis**: Scenario A = conservative kJ envelope, 2:1 cadence, high recovery margin; Scenario B = target kJ envelope, 2:1:1 or 3:1 cadence, balanced recovery margin; Scenario C = upper kJ envelope, 3:1 cadence, more B2B and specificity in the durability phase.
  - `season_archetype_rationale` (same substance for all three, adapted to each scenario's posture): `["52-week planning runway provides enough horizon for VO2 Foundation (Base/vo2_base, ~4 weeks) + concentrated VO2 peak (Build/vo2_build, ~4 weeks) before the durability block, leaving ≥ 30 weeks for economy, VLamax-lowering (Build/vlamax_lowering), specific durability (Build/durability_build), and specificity/taper. Weekend leverage (up to 8h outdoor / 4h indoor) can support fresh VO2max intervals within compact weekday windows. VO2MAX is permitted only in the early Base/vo2_base and Build/vo2_build phases; from the vlamax_lowering phase onward the emphasis shifts to durability, economy, and VLamax-lowering."]`
  - `intensity_guidance.allowed_domains`: `["RECOVERY", "ENDURANCE", "TEMPO", "VO2MAX"]` (documentary: VO2MAX active in early phases, THRESHOLD suppressed in the VO2 block; the macrocycle layer maps these to canonical phase-intent semantics: `vo2_base` for VO2 Foundation Base phase, `vo2_build` for concentrated VO2 Build phase)
  - `decision_notes` must include in each scenario: "VO2MAX is permitted as early-season aerobic-ceiling support (Base/vo2_base + Build/vo2_build) only; from the vlamax_lowering phase onward the emphasis shifts to durability, economy, and VLamax-lowering."

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
- NOTE: VO2max development language in athlete objectives is never an objective mismatch — it is consistent with the RPS ceiling-first methodology. Do not bundle it with competitive-ambition mismatches.

Internal consistency checks:
- Ask whether the scenario is more than just a different weekly-kJ number.
- Ensure `risk_profile`, `load_philosophy`, `decision_notes`, `deload_cadence`, and `intensity_guidance` tell the same story.
- Ensure `best_suited_if` is a real positive selection gate and `risk_flags` are real caution markers, not marketing prose.
- Ensure `best_suited_if` contains guardrail-visible selection words, not vague phrases like `good default` or `nice option`.
- Ensure `risk_flags` contain guardrail-visible words, not vague phrases like `general caution` or `watch recovery`.
- Make cadence rationale visible in stored scenario fields such as `decision_notes`, `risk_flags`, `event_alignment_notes`, or `kpi_guardrail_notes`.
- If multiple scenarios share the same cadence, say directly that cadence is intentionally shared and that differentiation comes from other axes such as specificity-under-fatigue, recovery margin, or risk posture.
- If Scenario B is the performance-default option, make economy/sub-threshold logic plausible in the scenario story.
- Make Scenario C ambition visible through B2B, hard-late, pre-load, event simulation, or other specificity-under-fatigue markers.

3-pass verification (mandatory before returning):

Pass 1 — Contract alignment: do the narrative fields fulfill the scenario layer's job?
- For each scenario: does `load_philosophy` explicitly name what drives load progression — duration-led, frequency-led, or quality/intensity-led? If not, rewrite it. This is the primary character handoff to season planning.
- Does `core_idea` state the phase count, cadence, and the season outcome the athlete is building toward? If it reads like a mood word or abstract goal instead of a structural description, rewrite it.
- Does `typical_week_feel` describe session character (what intensity domains appear, when, how the legs feel across the week) derived from the scenario's intensity narrative and cadence — not from assumed day names? If it reads like scheduling language instead of session feel, rewrite it.
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
  - GOOD (horizon < 20 w, no ceiling-first): "Scenario A uses 2:1 cadence with 3-week phases and excludes THRESHOLD and VO2MAX — a tighter reset rhythm and narrower domain ceiling than both B (2:1:1, THRESHOLD permitted) and C (3:1, THRESHOLD + VO2MAX). The shorter phase length means 18 phases vs 13 in B and C, with more frequent adaptation checkpoints but less sustained overload per block."
  - GOOD (ceiling-first, horizon ≥ 20 w): "All three scenarios follow the same ceiling-first Kinzlbauer phase sequence (vo2_base → vo2_build → vlamax_lowering → durability). Scenario A uses 2:1 cadence with 3-week phases → conservative kJ envelope and highest recovery margin. B uses 2:1:1 / 4-week with target kJ and balanced posture. C uses 3:1 / 4-week with upper kJ and more B2B fatigue exposure. The scenarios differ in how much fatigue load is carried and how long each loading block runs — not in which phases or domains are used."
- `typical_week_feel` must follow the MANDATORY TEMPLATE exactly: start with "Shorter session days are [character]", then "The primary long session is [character]", then end with the absorbed/fatigue clause. Generic mood words are not acceptable substitutes.
  - BAD: "Structured but manageable; the athlete should usually finish the week feeling contained rather than stretched."
  - BAD: "Purposeful and progressive; work is clearly present, but recovery remains visible and usable."
  - GOOD (no ceiling-first, Scenario A / 2:1 / 3-week / ENDURANCE+TEMPO): "Shorter session days are steady endurance or tempo — no intervals, no threshold work in any loading week. The primary long session is purely aerobic, growing progressively longer each phase. The athlete closes most loading weeks feeling absorbed."
  - GOOD (ceiling-first, Scenario A / 2:1 / 3-week): "Shorter session days are steady endurance in most loading weeks; the VO2 Foundation Base phase adds short-interval VO2 work on one shorter day per loading week. The primary long session is purely aerobic, growing longer each phase. The athlete closes most loading weeks feeling absorbed."
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
- CEILING-FIRST MANDATE: if `athlete_profile.objectives.secondary` or `objectives.priority_order` contains VO2max development language AND planning runway ≥ 20 weeks, emitting `season_archetype: "none"` for ANY scenario is a hard error — ALL THREE scenarios MUST use `ceiling_first_durability`; check this before returning and revise every scenario that is missing it
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
- do not claim that objective mismatch is resolved in this layer
- do not invent fake kJ separation when the actual time budget cannot support it

Pre-return self-check (mandatory):
- Does `inclusive_planning_horizon_weeks` ≥ 20? If yes, ALL three scenarios must have `season_archetype: "ceiling_first_durability"`. If any still has `none`, stop — revise before returning.
- Are `recovery_margin`, `fatigue_exposure`, and `specificity_density` non-empty explicit strings in all three `scenario_guidance` blocks?
- Would a reader know which scenario they are reading without seeing the `scenario_id`? If not, rewrite the generic sentences.

Output format:
- Return the task expected_output with scenario or scenario-interpretation fields filled explicitly.
- Include decision logic, cadence/horizon facts, event alignment, risk flags, and assumptions where available.
- Keep scenario guidance informational unless the active task makes it binding.
