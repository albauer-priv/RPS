---
name: macrocycle-architecture
description: Reverse-plan season macrocycles, peak windows, and taper structure from event anchors.
metadata:
  author: rps
  version: "5.3"
---
Build macrocycle structure backward from priority events.

Core planning rule:
- all season architecture is backplanned from one or more priority `A` event anchors; forward-only planning is invalid
- schema-valid cycle values are only `Base`, `Build`, `Peak`, and `Transition`
- emit only schema-valid phase/cycle values: `Base`, `Build`, `Peak`, and `Transition`
- old `Specificity` intent is represented as event-specific emphasis inside schema-valid `Peak` or late `Build`, not as a new cycle value
- old `Taper` intent is represented narratively and structurally inside `Peak` rather than as a standalone cycle value

Backplanning algorithm:
1. classify each `A` event as primary, secondary, equal-priority, or cluster-member
2. if `A` events are too close for recovery, re-entry, build, and taper, group them into one explicit `A`-event cluster / peak window
3. if spacing is sufficient, create a separate target macrocycle for each `A` event anchor
4. place peak/taper behavior directly before each target `A` event or clustered peak window inside a schema-valid `Peak` cycle
5. allocate `Peak -> Build -> Base` backward from each anchor, then place `Transition` where recovery or post-event reset is required
6. if backplanned macrocycles overlap, resolve by event priority instead of stacking overlapping taper/build demands
7. after an `A` event, require `Transition` or re-entry before a new Build unless the next `A` event stays inside the same peak cluster
8. map those cycle decisions onto the injected deterministic phase slots without changing slot ids, order, lengths, or ISO-week ranges
9. fit `B` and `C` events into the existing structure instead of rebuilding around them
10. return a macrocycle map, event-priority table, and explicit peak windows

Cycle semantics:
- `Base`: durability, aerobic foundation, repeatability, and low-risk volume development
- `Build`: progressive event-relevant load while preserving durability-first ramp limits
- `Peak`: final event-specific sharpening and any necessary taper behavior without introducing a separate `Taper` cycle
- `Transition`: recovery, re-entry, reset, or post-event restoration

Permitted ultra/brevet archetype:
- a Kinzlbauer-like season template is allowed at season architecture level only
- it sequences aerobic ceiling/VO2 tolerance before major volume expansion, then shifts toward economy, VLamax-lowering emphasis, and durability
- use it to shape phase intent and domain eligibility while keeping workout prescription and governance corridors in their responsible components
- durability-first is not intensity-free: `RECOVERY` and `ENDURANCE` protect repeatability, while `TEMPO` or other scenario-permitted quality may be used as tightly bounded phase intent when recovery and event specificity justify it
- do not introduce free `THRESHOLD` or `VO2MAX` blocks in the Season Plan artifact; if aerobic-ceiling work is relevant, express it as high-level phase intent only when the selected scenario permits the domain
- once a scenario is selected, refer to it neutrally as the selected scenario or user-selected scenario; do not re-argue the choice with evaluative language

Ultra/brevet durability anchors (apply when using Kinzlbauer-like template):
- kJ/kg milestones: early economy phase 20–25 kJ/kg preload; mid economy/durability 28–32 kJ/kg; late durability 35–40 kJ/kg back-to-back; use athlete body mass to convert to absolute kJ targets
- taper readiness: last major preload stimulus ≥ 4 weeks before A event; no new durability milestones inside the taper window
- fueling progression (carbohydrate/hour on long rides): early season 40–60 g/h; economy/durability phases 60–75 g/h; specific durability phase 70–90 g/h; event weeks — trained protocols only, no new foods
- HR late-suppression: a drop in HR response at constant power late in a long session is an autonomic fatigue marker, not improved efficiency; do not cue power increases; use as a readiness signal — if HR suppression onset moves earlier session-to-session, recovery is incomplete

Seasonal availability context:
- When `seasonal_context` is present in the injected context, read `outdoor_season_months`, `indoor_dominant_months`, `indoor_weekend_max_hours`, and `outdoor_weekend_max_hours`.
- For each phase, check whether its ISO-week range falls predominantly inside `indoor_dominant_months` or `outdoor_season_months` and annotate the phase with that character.
- Indoor-dominant phases: cap weekend long-ride volume at `indoor_weekend_max_hours` in the phase narrative; describe the phase as trainer-based with higher relative intensity density potential; do not assign outdoor durability volumes that cannot be realistically achieved indoors.
- Outdoor phases: weekend long rides may reach `outdoor_weekend_max_hours`; terrain, elevation, and pacing variation are available overload levers.
- Express the seasonal character in phase-level `rationale`, `description`, or `intent` fields where they exist; downstream tasks and the writer use this to adjust session prescriptions.
- Do not alter kJ-band math or deterministic load corridor values; `seasonal_context` is advisory narrative shaping only.
- If `seasonal_context` is absent, do not invent seasonal annotations — proceed with the static availability table only.

Ceiling-first archetype activation (mandatory when scenario uses it):
- when the selected scenario has `season_archetype: "ceiling_first_durability"` and `VO2MAX` in its `allowed_intensity_domains`, the macrocycle MUST map the first one or two phases (typically the opening 6–10 weeks of the horizon) to `vo2_build` intent with `VO2MAX` permitted — this is mandatory, not optional, when the scenario explicitly activates the archetype
- after the VO2 foundation block, from the third phase onward, transition to `durability_build` intent and suppress `VO2MAX` — economy, VLamax-lowering, and long-ride volume become the primary overload axis from that point
- size the VO2 block to leave enough horizon for at least three durability-build phases plus specificity and taper; do not extend it so far that the durability runway is compromised
- cite the selected scenario's `season_archetype_rationale` when explaining why the first phases use `vo2_build` intent

Allowed multi-`A` models:
- `multiple macrocycles`: only when `A` events are separated enough for full recovery and rebuild
- `A-event cluster / peak window`: one build and one peak window with a single taper strategy
- `equal-priority A-events`: valid only when spacing supports separate recovery, build, peak, and taper structure

Excluded architecture patterns:
- use one coherent peak window for tightly grouped priority events
- preserve fitness and freshness across tightly clustered `A` events
- keep macrocycles sequential and non-overlapping
- do not force a second independent macrocycle when the calendar only supports one peak cluster

Taper rules:
- taper exists only for `A` events
- taper is represented narratively/structurally inside `Peak`; it is not a separate cycle enum
- `B` events may get minor load adjustment only; `C` events get none
- taper depth and duration scale with event duration, accumulated fatigue, and athlete resilience
- a `B` event constraint must read as rehearsal, pacing/fueling validation, or minor load adjustment; it must not imply a full taper or independent peak
- minimum effective taper window for ultra/brevet events (events > 12 hours): **2–3 weeks including the event week**; a single event-week taper is insufficient for events of this duration
- the last cadence role of the phase immediately preceding a TAPER/A-event phase must not be `RELOAD`; flag `RELOAD → A-event phase` adjacency as a structural **warning** and recommend restructuring the preceding phase's final week to `MINI_RESET` or `DELOAD`; it is a **warning**, not a hard blocker, unless the taper phase itself is shorter than the minimum effective window
- taper week content (see `references/taper_and_peaking_evidence.md` for sources): **volume** reduced 41–60% from peak load (`tap_core_001`); **intensity** MAINTAINED — reducing intensity by >30% causes 20–30% performance loss, "halten" principle: fitness is held not built (`tap_core_001`, `tap_core_002`); **frequency** maintained at ≥ 80% of pre-taper sessions (`tap_core_002`); no new high-volume stimuli inside the taper window

Cadence week-role override in `Peak` phases (mandatory when A event is in the phase):
- cadence week roles (`LOAD_1`, `LOAD_2`, `MINI_RESET`, `RELOAD`) are deterministic PLANNING CONTEXT only; they describe a generic load pattern
- when a phase is designated as `Peak` cycle type and contains the A event week, the cadence week roles MUST be overridden by event-driven taper semantics in the phase narrative and intent
- the A event week — regardless of its cadence role label (`MINI_RESET`, `RELOAD`, or other) — is the **event week**: zero training load before the start, the event itself
- weeks between the last B event and the A event week within the `Peak` phase represent recovery + taper, NOT regular load weeks — do not treat `LOAD_2` or `RELOAD` role labels as training load prescriptions when they fall within the taper window of a `Peak` phase
- explicitly state the cadence role override in the phase description: e.g., "Week 1 (B_EVENT): B event + immediate recovery; Week 2 (POST_B_RECOVERY): recovery only, taper deepening; Week 3 (PRE_EVENT_TAPER): minimal volume, maintain feel; Week 4 (A_EVENT): race day"
- this override must be visible in the phase rationale so the constraint specialist can recognise it as valid taper structure

Backward planning from A event (mandatory):
- all season architecture is anchored at the A event week: the final phase ends at (or includes) the A event week
- allocate backward: Peak phase (taper + A event) → Build 2 (event-specific) → Build 1 (progressive durability) → Base (aerobic foundation)
- assign cycle types working backward from the A event: the phase containing the A event = `Peak`; preceding phases = `Build` until aerobic foundation work begins = `Base`; recovery/re-entry blocks = `Transition`
- if a phase boundary does not naturally land at the A event week, the phase immediately containing the A event is still the Peak phase; do not split the taper across two phases
- if the calendar is compressed (B event in same phase as A event), use the B event as the final specificity stimulus and start the taper from the week immediately after the B event; the phase as a whole is `Peak` cycle type

Progressive brevet / ultra sequencing:
- shorter preparatory brevets (e.g. 200 → 300 → 400 km) are stress-plus-recovery milestones, not independent peaks
- each preparatory brevet deserves a brief recovery window (3–7 days easy) inside the existing structure — not a full re-entry or rebuild block
- a B-priority brevet 2–3 weeks before the A-event peak: the B event week is the final specificity rehearsal; subsequent weeks are recovery-only, then direct taper; do not insert any new loading or reload stimulus
- when a B event and the A event are in the same phase (spacing ≤ 4 weeks): designate the full phase as `Peak`, assign the B event week as final specificity stimulus, and treat all remaining weeks of the phase as taper — this is a valid taper structure as long as there are ≥ 2 weeks between the B event week and the A event week (inclusive of the A event week)
- do not insert a new Build or reload block between the final B-event and the A-event taper when spacing is ≤ 3 weeks

Hard rules:
- keep peak decisions at season architecture level
- preserve taper clarity by prioritizing events according to their declared priority
- if the calendar is compressed, shorten lower-priority build content before collapsing the peak model
- model clustered `A` events as one peak window unless the calendar supports separate macrocycles
- if equal-priority `A` events do not have enough spacing, merge them into one peak cluster or downgrade one event to secondary-A behavior

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
