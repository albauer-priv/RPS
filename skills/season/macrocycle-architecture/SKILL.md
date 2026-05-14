---
name: macrocycle-architecture
description: Reverse-plan season macrocycles, peak windows, and taper structure from event anchors.
metadata:
  author: rps
  version: "3.0"
---
Build macrocycle structure backward from priority events.

Core planning rule:
- all season architecture is backplanned from the highest-priority `A` event; forward-only planning is invalid

Backplanning algorithm:
1. start from the selected `A` event or explicit `A` cluster
2. place taper directly before the `A` event or peak window
3. allocate `Specificity -> Build -> Base` backward from that anchor
4. fit `B` and `C` events into the existing structure instead of rebuilding around them
5. return a macrocycle map, event-priority table, and explicit peak windows

Allowed multi-`A` models:
- `multiple macrocycles`: only when `A` events are separated enough for full recovery and rebuild
- `A-event cluster / peak window`: one build, one peak window, no repeated tapers

Explicitly forbidden:
- multiple independent tapers inside a short interval
- rebuilding fitness between tightly clustered `A` events
- overlapping macrocycles

Taper rules:
- taper exists only for `A` events
- `B` events may get minor load adjustment only
- `C` events get none
- taper depth and duration scale with event duration, accumulated fatigue, and athlete resilience

Hard rules:
- do not introduce additional peaks at phase level
- do not sacrifice taper clarity just to keep all events equally satisfied
- if the calendar is compressed, shorten lower-priority build content before collapsing the peak model
