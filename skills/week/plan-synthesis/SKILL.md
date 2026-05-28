---
name: plan-synthesis
description: Synthesize week specialist drafts into one bounded internal week plan candidate.
metadata:
  author: rps
  version: "3.0"
---
Synthesize specialist outputs into one internal week bundle.

Definitions:
- `planned_kj`: mechanical work estimate at workout/day level
- `planned_weekly_load_kj`: governance week-load metric used for corridor compliance
- `active_weekly_kj_band`: binding target-week governance band
- `weekly_load_corridor_kj`: week-summary mirror of the binding governance band
- `phase_role`: active deterministic phase role
- `phase_week_role` / `week_role`: inherited deterministic role for the target week
- `reload`: controlled return near prior build load
- `re-entry`: baseline-anchored controlled return after deload or unresolved fatigue

Authority / injected sources:
- `active_weekly_kj_band`, dates, fixed rest days, day availability, and target-week role context come from `workspace_get_week_calendar_context`
- inherited phase semantics come from `workspace_get_phase_execution_context`
- inherited week-shaping posture comes from `inherited_planning_posture`; use recovery margin, pressure stance, specificity density, and legal domain ceiling directly
- this layer synthesizes a week bundle; it must not invent new legality, new cadence families, or new workout-policy exceptions

Method:
1. Pass 1 - structural draft: preserve authoritative constraints, the binding active weekly corridor, and the active phase week role from deterministic context.
2. Pass 2 - semantic finalization: resolve conflicts in favor of recovery protection, canonical phase semantics, availability, and event/taper semantics.
3. Keep workout authoring subordinate to week role, day role, load distribution, and export syntax.
4. Emit exactly one coherent candidate that is ready for review, not a list of alternatives.
5. Review should mostly confirm. Resolve all context-decidable agenda, availability, role, domain, and export-intent contradictions before handoff.
6. Apply the full week-side policy stack during finalize:
   - load-estimation semantics
   - active band authority
   - inherited progressive-overload role semantics
   - durability-first repeatability
   - workout-policy legality and exportability
7. Pass 3 - planner self-audit: before handoff, confirm that:
   - Mon..Sun agenda structure is complete
   - active-band vs mechanical-work semantics are explicit
   - duration-first reconciliation is explicit
   - overload-role meaning is explicit
   - durability-first tradeoffs are explicit
   - workout legality and export-safe readiness are explicit
   - writer-ready week summary is complete
   - if agenda/day/workout blueprint structure or deterministic week authority alignment is wrong, return to Pass 1
   - if structure is valid but load semantics, reconciliation, legality framing, or writer-ready summary is incomplete, return to Pass 2

Progression axes:
- duration / total governance work
- frequency when explicitly allowed by week shape
- density / complexity
- intensity last

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
- `planned_weekly_load_kj` is governance load, not raw workout/day mechanical work; keep the distinction explicit in reasoning and trace
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

Week-policy translation rules:
- preserve the inherited overload-role meaning:
  - deload = meaningful load/quality reduction
  - mini-reset = smaller reduction than full deload
  - reload = controlled return near prior build load
  - re-entry = baseline-anchored controlled return after fatigue or true deload
- if a nominal reload is actually baseline-anchored because readiness is poor, label and reason about it as re-entry
- duration-first reconciliation comes before intensity escalation
- if the week is slightly under target after safe reconciliation, preserve safety and explain the miss
- no catch-up logic on recovery or fixed-rest days
- workout construction must stay inside workout-policy family rules and export-safe subset rules

Output format:
- Return the task expected_output as one consolidated planning bundle or synthesis contribution.
- Include day/workout blueprints, selected inputs, decisions, unresolved risks, and writer-ready summary needed by the next task.
- Preserve task boundaries and emit competing variants only when the task explicitly asks for them.
