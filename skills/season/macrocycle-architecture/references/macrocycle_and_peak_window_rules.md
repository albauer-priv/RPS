# Macrocycle and Peak Window Rules

## Macrocycle method
- reverse-plan from the highest-priority event windows
- use base -> build -> specificity intent -> taper intent progression where feasible
- emit only schema-valid cycle values: `Base`, `Build`, `Peak`, `Transition`
- represent specificity as late-Build or Peak emphasis, not as a `Specificity` cycle
- represent taper inside `Peak`, not as a `Taper` cycle
- if the horizon is compressed, shorten lower-priority phases before sacrificing taper clarity

## Multiple A-event handling
- either use clearly separated peaks with rebuild space
- or use one protected peak and one supported secondary expression
- never imply two full peaks inside one unresolved fatigue wave

## Backward planning from A event (mandatory)
Build the macrocycle backward from the primary A event anchor:
1. Anchor the A event week as the endpoint of the Peak phase
2. Allocate the Peak phase backward: the phase containing (or ending at) the A event week = `Peak`
3. Preceding phases: `Build` (event-specific then progressive durability) → `Base` (aerobic foundation) → `Transition` (recovery / re-entry blocks)
4. If a B event falls in the same phase as the A event: the B event marks the final specificity stimulus; all weeks after the B event in that phase are taper; the phase as a whole is `Peak`
5. If the phase length requires it, allow the early portion of the season to absorb shortened or transition phases to fit the total planning horizon — never shorten the Peak phase or the phase immediately before it to accommodate a horizon fit

## Taper rules
- taper must be explicit and visible in the macrocycle
- a taper cannot coexist with aggressive overload ramping
- if the event cluster is too dense, reduce ambition instead of faking taper adequacy
- minimum effective taper window for ultra/brevet events: 2–3 weeks including the event week;
  a single event-week taper is insufficient for events longer than ~12 hours
- the last cadence role of the phase **immediately preceding** a TAPER/A-event phase must not be
  `RELOAD`; flag `RELOAD → A-event phase` adjacency as a structural **warning** and recommend
  restructuring the preceding phase's final week to `MINI_RESET` or `DELOAD` — it is a warning,
  not a hard blocker, unless the taper phase itself is shorter than the minimum effective window
- cadence week roles (`LOAD_1`, `LOAD_2`, `MINI_RESET`, `RELOAD`) are **planning context labels**;
  inside a `Peak` phase they are overridden by event-driven taper semantics — do not use the
  cadence label to assess taper adequacy within a `Peak` phase; the `Peak` designation and the
  macrocycle architect's explicit taper narrative are the authoritative taper signal

## Taper week content (research-backed general rules)
Evidence: `tap_core_001` (Bosquet et al. 2007 meta-analysis, 27 studies), `tap_core_002` (Mujika & Padilla 2003) — see `taper_and_peaking_evidence.md`.

The taper achieves supercompensation by clearing accumulated fatigue while preserving the fitness already built:
- **Volume**: reduce 41–60% from pre-taper peak load progressively — a sudden cut is less effective than a stepped reduction (`tap_core_001`)
- **Intensity**: MAINTAIN at or near pre-taper level — this is the single most critical taper rule; reducing intensity by 30–60% causes a 20–30% performance loss and negates the taper benefit; short sharp efforts at race pace are encouraged to keep the neuromuscular system sharp (`tap_core_001`, `tap_core_002`)
- **Frequency**: maintain ≥ 80% of pre-taper session count; shorten individual sessions rather than removing training days (`tap_core_002`)
- **Duration**: 1–3 weeks for most events; ultra/brevet events (> 12 hours): 2–3 weeks minimum including the event week — duration scales with event length (`tap_core_002`)
- **Fitness is held, not built ("halten")**: the taper window cannot generate new training adaptations — its sole purpose is fatigue clearance and supercompensation; any high-volume overload stimulus in this window carries fatigue into the event start line (`tap_applied_002`)
- **B event as final high-load stimulus**: when a B event falls 2–4 weeks before the A event, it is the last full specificity stimulus; all weeks after the B event are taper — near-peak form can be maintained for 2–4 weeks with correct taper structure, so this is physiologically sound (`tap_applied_001`, `tap_applied_002`)
- **B+A in the same Peak phase**: valid when (a) B event is the final specificity dose, (b) ≥ 2 full taper weeks follow the B event before the A event, (c) the phase as a whole is designated `Peak`; the B event week itself is NOT a taper week — it is the last hard event/training week

## Cadence week-role override in Peak phases
When the macrocycle architect designates a phase as `Peak` containing the A event:
- A event week (regardless of cadence role: `RELOAD`, `MINI_RESET`, etc.) = **event week** (zero training load + the event)
- Week(s) immediately before the A event week = taper week(s) (minimal volume, maintain neuromuscular feel)
- If a B event is in week 1 of the Peak phase and the A event is in week 4, the structure is:
  - Week 1: B event (final specificity rehearsal)
  - Week 2: recovery only (post-B, begin taper)
  - Week 3: pre-event taper (light + keep feel)
  - Week 4: A event week
  This constitutes a **valid 3-week taper window** (B event week through A event week inclusive); ≥ 2 cadence-role slots between B event and A event is sufficient for ultra/brevet events when the architect explicitly documents the override

## Progressive brevet event sequencing
- when a season targets a long-distance ultra (e.g. 600 km), shorter preparatory brevets
  (200 km → 300 km → 400 km) function as **stress-plus-recovery milestones**, not independent peaks
- each preparatory brevet deserves a brief recovery window (3–7 days easy) rather than a full
  re-entry or rebuild block; that window is a `Transition` behavior inside the existing structure
- a B-priority brevet 2–3 weeks before the A-event peak should be treated as a specificity
  confirmation + fueling rehearsal: apply minor load reduction in the B-event week, then recovery
  only, then proceed directly to final taper for the A event
- do not insert a new Build or reload block between the final B-event and the A-event taper when
  spacing is ≤ 3 weeks

## Kinzlbauer-like ultra/brevet template
- permitted at season architecture level only
- order: aerobic ceiling/VO2 tolerance first, then economy/durability and VLamax-lowering emphasis with volume stabilization
- weekday time-crunch compatibility means weekend long-duration exposure is the main volume lever
- volume expansion is conditional on KPI/governance compatibility and recovery stability
- the archetype shapes phase intent and allowed/suppressed domains, not workouts or numeric overload rules
