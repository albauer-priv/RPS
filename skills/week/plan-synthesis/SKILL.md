---
name: plan-synthesis
description: Synthesize week specialist drafts into one bounded internal week plan candidate.
metadata:
  author: rps
  version: "2.0"
---
Synthesize specialist outputs into one internal week bundle.

Method:
1. Preserve authoritative constraints, active Phase/S5 corridor, and the active phase week role from deterministic context.
2. Resolve conflicts in favor of recovery protection, phase intent, availability, and event-taper semantics.
3. Keep workout authoring subordinate to week role, day role, load distribution, and export syntax.
4. Emit exactly one coherent candidate that is ready for review, not a list of alternatives.

Use only existing upstream authority and injected deterministic context.

Required bundle semantics:
- `day_blueprints` must cover exactly Mon..Sun of the target ISO week in order.
- Each day blueprint must state fixed-rest status, availability cap, phase role, phase week role, day role, intended domain, duration, kJ, workout reference, and warnings.
- `workout_blueprints` must exist for every planned workout and state target day role, intensity domain, duration, kJ, required sections, syntax profile, and exportability status.
- `weekly_load_corridor_kj` must mirror the active Phase/S5 band; do not invent a separate week corridor.
- If the active band, availability, fixed rest days, and recovery constraints cannot be reconciled, emit blocking issues or replan instructions instead of hiding the conflict.

Output format:
- Return the task expected_output as one consolidated planning bundle or synthesis contribution.
- Include day/workout blueprints, selected inputs, decisions, unresolved risks, and writer-ready summary needed by the next task.
- Preserve task boundaries and emit competing variants only when the task explicitly asks for them.
