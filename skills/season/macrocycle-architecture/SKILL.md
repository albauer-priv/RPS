---
name: macrocycle-architecture
description: Reverse-plan season macrocycles, peak windows, and taper structure from event anchors.
metadata:
  author: rps
  version: "5.0"
---
Build macrocycle structure backward from priority events.

Core planning rule:
- all season architecture is backplanned from the highest-priority `A` event; forward-only planning is invalid
- schema-valid cycle values are only `Base`, `Build`, `Peak`, and `Transition`
- emit only schema-valid phase/cycle values: `Base`, `Build`, `Peak`, and `Transition`
- old `Specificity` intent is represented as event-specific emphasis inside schema-valid `Peak` or late `Build`, not as a new cycle value
- old `Taper` intent is represented narratively and structurally inside `Peak` rather than as a standalone cycle value

Backplanning algorithm:
1. start from the selected `A` event or explicit `A` cluster
2. place peak/taper behavior directly before the `A` event or peak window inside a schema-valid `Peak` cycle
3. allocate `Peak -> Build -> Base` backward from that anchor, then place `Transition` where recovery or post-event reset is required
4. map those cycle decisions onto the injected deterministic phase slots without changing slot ids, order, lengths, or ISO-week ranges
5. fit `B` and `C` events into the existing structure instead of rebuilding around them
6. return a macrocycle map, event-priority table, and explicit peak windows

Cycle semantics:
- `Base`: durability, aerobic foundation, repeatability, and low-risk volume development
- `Build`: progressive event-relevant load while preserving durability-first ramp limits
- `Peak`: final event-specific sharpening and any necessary taper behavior without introducing a separate `Taper` cycle
- `Transition`: recovery, re-entry, reset, or post-event restoration

Permitted ultra/brevet archetype:
- a Kinzlbauer-like season template is allowed at season architecture level only
- it sequences aerobic ceiling/VO2 tolerance before major volume expansion, then shifts toward economy, VLamax-lowering emphasis, and durability
- use it to shape phase intent and domain eligibility while keeping workout prescription and governance corridors in their responsible components

Allowed multi-`A` models:
- `multiple macrocycles`: only when `A` events are separated enough for full recovery and rebuild
- `A-event cluster / peak window`: one build and one peak window with a single taper strategy

Excluded architecture patterns:
- use one coherent peak window for tightly grouped priority events
- preserve fitness and freshness across tightly clustered `A` events
- keep macrocycles sequential and non-overlapping

Taper rules:
- taper exists only for `A` events
- taper is represented narratively/structurally inside `Peak`; it is not a separate cycle enum
- `B` events may get minor load adjustment only
- `C` events get none
- taper depth and duration scale with event duration, accumulated fatigue, and athlete resilience

Hard rules:
- keep peak decisions at season architecture level
- preserve taper clarity by prioritizing events according to their declared priority
- if the calendar is compressed, shorten lower-priority build content before collapsing the peak model
- model clustered `A` events as one peak window unless the calendar supports separate macrocycles

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
