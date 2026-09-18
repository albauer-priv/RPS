---
name: periodization-methodology
description: General periodization methodology for season and phase planning — phase structure, backward planning from A event, taper rules, and event hierarchy.
metadata:
  author: rps
  version: "1.1"
---
Structure a training season backward from priority events.

This skill defines the general methodology that all season and phase planning layers must follow.
It is the single authoritative source for phase semantics, backward planning logic, event hierarchy,
and taper week content. Skill-specific layers may extend or narrow this methodology but must not
contradict it.

## Phase semantics

Four schema-valid cycle types:
- `Base`: aerobic foundation, durability, repeatability, and volume tolerance; primary goal is to
  safely raise the aerobic ceiling; may include `vo2_base` sub-intent (Kinzlbauer VO2 Foundation:
  short VO2-interval work on a protected ENDURANCE base, no SWEET_SPOT/THRESHOLD) or the standard
  `aerobic_base` sub-intent (GPP, robustness, no high-intensity); event-specific intensity is low
  in `aerobic_base` but VO2MAX intervals are valid in `vo2_base`
- `Build`: progressive event-relevant load; event-specific emphasis increases; durability-first
  ramp limits apply; intensity is the last overload lever, not the first
- `Peak`: final event-specific sharpening and mandatory taper behavior before the A event; taper
  is represented structurally inside `Peak`, never as a separate cycle type; last hard stimulus
  precedes the taper window
- `Transition`: recovery, re-entry, reset, or post-event restoration; no meaningful overload;
  mandatory after an A event unless the next A event is inside the same peak cluster

Old `Specificity` intent = late-Build or Peak emphasis (not a separate cycle value).
Old `Taper` intent = structural narrative inside `Peak` (not a separate cycle value).

## Event hierarchy

- `A` event: the season's primary goal — deserves full peak window, explicit taper, and explicit
  backward-planned macrocycle; maximum 2–3 A events per season with ≥ 12 weeks between them if
  separate macrocycles are required; tightly clustered A events are treated as one peak cluster
- `B` event: important secondary event — gets minor load adjustment and may serve as specificity
  rehearsal; no independent peak or full taper; when a B event is 2–4 weeks before the A event
  it becomes the final specificity stimulus and the direct entry point into A-event taper
- `C` event: training event — fits inside existing phase structure without load adjustment; does
  not receive any taper or deload treatment

## Backward planning from A event (mandatory)

All season architecture is anchored at the A event week. Forward-only planning is invalid.

1. Place the A event week as the endpoint of the `Peak` phase
2. Work backward: the phase containing the A event = `Peak`; preceding phases = `Build` (event-
   specific then progressive durability) → `Base` (aerobic foundation) → `Transition` (re-entry
   or recovery blocks where needed)
3. If two A events are too close for separate peaks, group them into one peak cluster with one
   taper strategy
4. Fit B and C events into the existing structure; never rebuild the macrocycle around them
5. If the planning horizon is compressed, shorten lower-priority phases first — never shorten
   the Peak phase or the phase immediately before it

## Taper week content (mandatory in Peak phases)

Evidence: tap_core_001 (Bosquet et al. 2007), tap_core_002 (Mujika & Padilla 2003) —
see `references/taper_and_peaking_evidence.md`.

- **Volume**: reduce 41–60% from pre-taper peak load progressively (`tap_core_001`)
- **Intensity**: MAINTAIN at or near pre-taper level — this is the single most critical rule;
  reducing intensity >30% causes 20–30% performance loss; short race-pace efforts preserve
  neuromuscular sharpness (`tap_core_001`, `tap_core_002`)
- **Frequency**: maintain ≥ 80% of pre-taper session count; shorten sessions, do not remove them
  (`tap_core_002`)
- **Duration**: 1–3 weeks for most events; ultra/brevet events (> 12 hours): 2–3 weeks minimum
  including the event week — duration scales with event length
- **Fitness is held, not built ("halten")**: the taper window cannot produce new training
  adaptations; its sole purpose is fatigue clearance and supercompensation; any high-volume
  overload in this window carries fatigue to the start line
- **No new stimuli**: no new milestones, new distances, new loads, or new intensity patterns
  inside the taper window

## B+A event in the same Peak phase

When a B event and the A event both fall within one phase (spacing ≤ 4 weeks):
- designate the full phase as `Peak`
- the B event week = final specificity stimulus (race-intensity rehearsal)
- all weeks after the B event in that phase = taper toward the A event
- valid when: (a) ≥ 2 taper weeks between B event week and A event week (inclusive of A event
  week), and (b) the macrocycle architect explicitly documents the taper-override in the phase
  narrative
- near-peak form can be maintained for 2–4 weeks with correct taper structure; the B event
  provides the last hard stimulus and the body enters supercompensation during the taper weeks
  that follow (`tap_applied_002`)

## Cadence week-role labels inside Peak phases

Cadence week roles (`LOAD_1`, `LOAD_2`, `MINI_RESET`, `RELOAD`) are deterministic planning
context — they describe a generic load pattern for non-event phases. Inside a `Peak` phase
containing the A event they are OVERRIDDEN by event-driven taper semantics:
- A event week regardless of its cadence label = event week (zero pre-race load + the event)
- Weeks between the last B event and the A event = taper weeks, regardless of cadence label
- `RELOAD` or `LOAD_2` in a `Peak` phase A-event week is NOT evidence of taper collapse
- The phase's `Peak` designation and the macrocycle architect's explicit taper narrative are
  the authoritative taper signal — cadence labels are not

Any skill assessing constraint validity must apply this override before flagging a blocker.

## Minimum taper adequacy standards

- All events: taper must be explicit and visible; cannot coexist with aggressive overload ramping
- Ultra/brevet events (> 12 hours): minimum 2–3 weeks including event week; a single event-week
  taper is insufficient
- The `RELOAD → A-event phase` adjacency (last cadence role of the phase immediately preceding
  the Peak phase) is a structural **warning**, not a blocker, unless the Peak phase itself is
  shorter than the minimum effective window
- Raising a constraint blocker for taper structure within a correctly designated `Peak` phase
  is invalid — the `Peak` designation is the authority

## Authority and scope

- This methodology defines correct periodization structure; it does not override deterministic
  load bands, schema governance, or availability constraints
- Phase-level and week-level agents extend this methodology in their layer; they do not redefine it
- Skill-specific layers (macrocycle-architecture, constraint-synthesis, structure-authoring) may
  add implementation detail on top of this methodology; none may contradict it

Reference files:
- `references/phase_structure_and_event_hierarchy.md` — extended phase and event detail
- `references/taper_and_peaking_evidence.md` — verified scientific sources for taper rules
