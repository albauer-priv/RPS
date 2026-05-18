---
name: event-priority-anchoring
description: Define season event hierarchy and anchor windows for reverse planning.
metadata:
  author: rps
  version: "4.0"
---
Anchor the season on explicit event hierarchy.

Event classes:
- `A`: primary performance objective; receives a dedicated taper; defines macrocycle structure
- `B`: secondary event supporting the `A` event; use small local adjustment while preserving full taper allocation for `A` events
- `C`: training event; keep it inside normal season structure without taper allocation

Event state labels:
- use unambiguous labels such as `A1`, `A2`, `A_block`, `Peak_Window_1`, `B_support_event`, and `C_training_event`
- labels like "important race" or "key event" are invalid unless they also carry an explicit `A/B/C` class

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
- separated `A` events require explicit multi-macrocycle or A-cluster handling
- integrate `B` events while preserving progression and peak logic
- integrate `C` events as training events within the existing taper and recovery budget
- ambiguous labels like "important race" are invalid; every event must have a priority class

Output format:
- Return the active task expected_output with clear sections for facts, decision, rationale, warnings, and next action when applicable.
- Include only information needed by the active task and downstream consumer.
