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
