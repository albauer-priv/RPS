---
name: macrocycle-architecture
description: Reverse-plan season macrocycles, peak windows, and taper structure from event anchors.
metadata:
  author: rps
  version: "5.0"
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
- `B` events may get minor load adjustment only
- `C` events get none
- taper depth and duration scale with event duration, accumulated fatigue, and athlete resilience
- a `B` event constraint must read as rehearsal, pacing/fueling validation, or minor load adjustment; it must not imply a full taper or independent peak

Hard rules:
- keep peak decisions at season architecture level
- preserve taper clarity by prioritizing events according to their declared priority
- if the calendar is compressed, shorten lower-priority build content before collapsing the peak model
- model clustered `A` events as one peak window unless the calendar supports separate macrocycles
- if equal-priority `A` events do not have enough spacing, merge them into one peak cluster or downgrade one event to secondary-A behavior

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
