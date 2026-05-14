---
name: event-priority-anchoring
description: Define season event hierarchy and anchor windows for reverse planning.
metadata:
  author: rps
  version: "3.0"
---
Anchor the season on explicit event hierarchy.

Event classes:
- `A`: primary performance objective; receives a dedicated taper; defines macrocycle structure
- `B`: secondary event supporting the `A` event; may receive small local adjustment but no full taper
- `C`: training event; no taper; must not distort season structure

Method:
1. Identify candidate events from the season context.
2. Classify every relevant event into `A`, `B`, or `C`.
3. Define which windows deserve peak protection and which only influence support structure.
4. Return explicit anchors that later macrocycle work must preserve.

Conflict hierarchy:
1. A-event integrity
2. macrocycle structure
3. recovery and fatigue tolerance
4. B events
5. C events

Hard rules:
- only one `A` event per macrocycle
- `B` events must not break progression or peak logic
- `C` events must not consume taper or recovery budget
- ambiguous labels like "important race" are invalid; every event must have a priority class
