---
name: plan-synthesis
description: Synthesize week specialist drafts into one bounded internal week plan candidate.
metadata:
  author: rps
  version: "2.0"
---
Synthesize specialist outputs into one internal week bundle.

Method:
1. Preserve authoritative constraints, the binding active weekly corridor, and the active phase week role from deterministic context.
2. Resolve conflicts in favor of recovery protection, canonical phase semantics, availability, and event/taper semantics.
3. Keep workout authoring subordinate to week role, day role, load distribution, and export syntax.
4. Emit exactly one coherent candidate that is ready for review, not a list of alternatives.
5. Review should mostly confirm. Resolve all context-decidable agenda, availability, role, domain, and export-intent contradictions before handoff.

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
- `weekly_load_corridor_kj` must mirror the binding active weekly band; do not invent a separate week corridor.
- If the active band, availability, fixed rest days, and recovery constraints cannot be reconciled, emit blocking issues or replan instructions instead of hiding the conflict.
- do not assume the writer will repair structural or semantic defects that are already decidable here
- week shape must reflect inherited `phase_type`, `phase_intent`, and `build_subtype`
  - `shortened_re_entry`: one true quality day, Z2 anchor, endurance support
  - `general_base` / `aerobic_base`: endurance-dominant support with conservative moderate work
  - `strength_endurance_base`: torque/K3-capable support only when legal
  - `sweet_spot_base`: moderate SST support without drifting into build density
  - `vo2_build`: limited fresh VO2-oriented quality when allowed; `build_subtype` is authoritative
  - `threshold_build`: threshold-oriented quality, not generic VO2 or SST drift
  - `sst_build`: extensive sub-threshold structure with density control
  - `durability_build`: duration/kJ, B2B, preload, hard-late emphasis
  - `specificity_build`: pacing/fueling/terrain/cadence/logistics realism before peak
  - `vlamax_lowering`: efficiency-oriented endurance/SST bias without anaerobic drift
  - `peak_sharpening`: sharpening and execution readiness without accumulation drift
  - `taper_freshening`: freshness and primer/openers only
  - `race_execution`: event week, logistics, pacing, recovery protection

Output format:
- Return the task expected_output as one consolidated planning bundle or synthesis contribution.
- Include day/workout blueprints, selected inputs, decisions, unresolved risks, and writer-ready summary needed by the next task.
- Preserve task boundaries and emit competing variants only when the task explicitly asks for them.
