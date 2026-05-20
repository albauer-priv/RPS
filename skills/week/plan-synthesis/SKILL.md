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

When exact deterministic execution values are needed, use the contract tools directly:
- `workspace_get_week_calendar_context`
- `workspace_get_phase_execution_context`

Final synthesis is integration work, not rediscovery. Do not ask coworkers to re-derive active week role, active weekly band, availability caps, fixed rest days, or allowed domains during this step.

Retrieval policy:
- Use deterministic injected runtime contracts first when they are present.
- Use `workspace_get_week_calendar_context` and `workspace_get_phase_execution_context` for exact authoritative week values.
- Use `workspace_get_latest` for latest authoritative planning artefacts and runtime snapshots only when direct retrieval is still needed.
- Use `workspace_get_input` only for athlete-managed inputs.
- Use `workspace_get_version` only for explicit week-sensitive historical artefacts.

Required bundle semantics:
- `day_blueprints` must cover exactly Mon..Sun of the target ISO week in order.
- Each day blueprint must state fixed-rest status, availability cap, phase role, phase week role, day role, intended domain, duration, kJ, workout reference, and warnings.
- `workout_blueprints` must exist for every planned workout and state target day role, intensity domain, duration, kJ, required sections, syntax profile, and exportability status.
- `weekly_load_corridor_kj` must mirror the active Phase/S5 band; do not invent a separate week corridor.
- If the active band, availability, fixed rest days, and recovery constraints cannot be reconciled, emit blocking issues or replan instructions instead of hiding the conflict.
- week shape must reflect inherited `phase_intent`
  - `ceiling_support`: limited fresh VO2-oriented quality only when allowed
  - `transition_coupling`: bridge week with endurance-dominant support
  - `durability_build`: duration/kJ, B2B, preload, hard-late emphasis
  - `specificity_build`: pacing/fueling/terrain/cadence/logistics realism before peak
  - `b_event_rehearsal`: real rehearsal anchor, not just generic specificity
  - `peak_preparation`: sharpening and execution readiness without accumulation drift
  - `a_event_peak_taper`: freshness and primer/openers only

Output format:
- Return the task expected_output as one consolidated planning bundle or synthesis contribution.
- Include day/workout blueprints, selected inputs, decisions, unresolved risks, and writer-ready summary needed by the next task.
- Preserve task boundaries and emit competing variants only when the task explicitly asks for them.
