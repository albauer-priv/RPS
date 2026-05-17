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
- do not emit `Specificity` or `Taper` as phase/cycle values
- old `Specificity` intent is represented as event-specific emphasis inside schema-valid `Peak` or late `Build`, not as a new cycle value
- old `Taper` intent is represented narratively and structurally inside `Peak`, never as a standalone cycle value

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
- it may shape phase intent and allowed/forbidden intensity domains, but it must not prescribe workouts or override governance corridors

Allowed multi-`A` models:
- `multiple macrocycles`: only when `A` events are separated enough for full recovery and rebuild
- `A-event cluster / peak window`: one build, one peak window, no repeated tapers

Explicitly forbidden:
- multiple independent tapers inside a short interval
- rebuilding fitness between tightly clustered `A` events
- overlapping macrocycles

Taper rules:
- taper exists only for `A` events
- taper is represented narratively/structurally inside `Peak`; it is not a separate cycle enum
- `B` events may get minor load adjustment only
- `C` events get none
- taper depth and duration scale with event duration, accumulated fatigue, and athlete resilience

Hard rules:
- do not introduce additional peaks at phase level
- do not sacrifice taper clarity just to keep all events equally satisfied
- if the calendar is compressed, shorten lower-priority build content before collapsing the peak model
- do not create implicit double peaks for clustered `A` events
