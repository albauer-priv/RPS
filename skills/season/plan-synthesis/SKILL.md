---
name: plan-synthesis
description: Synthesize season specialist drafts into one internal season bundle.
metadata:
  author: rps
  version: "2.0"
---
Consolidate season drafts into one candidate bundle.

Method:
1. Preserve event hierarchy and macrocycle logic.
2. A season may contain one or more target macrocycles backplanned from distinct `A`-event anchors when spacing allows.
3. If multiple `A` events are present, classify each one in season justification as `primary A-event`, `secondary A-event`, `equal-priority A-event`, or `cluster-member`.
4. If `A` events are too close for recovery, re-entry, build, and taper, group them into one A-event peak cluster instead of forcing separate macrocycles.
5. If spacing is sufficient, create a separate target macrocycle for each `A`-event anchor.
6. If backplanned macrocycles overlap, resolve by event priority and spacing; never stack overlapping taper/build demands from two `A` events.
7. After an `A` event, require `TRANSITION / transition_recovery` or `PREPARATION / preparation_re_entry` before any new Build phase unless the next `A` event remains inside the same peak cluster.
8. Keep load governance aligned with durability-first planning.
9. Resolve conflicts in favor of sustainable structure and explicit constraint compliance.
10. Use the injected selected-scenario structure math as the reference for planning horizon weeks, phase length, expected phase count, full phases, and shortened phases.
11. Use `Deterministic Season Phase Slot Context` as the binding skeleton for phase ids, order, ISO-week ranges, and phase lengths.
12. Treat `deload_cadence`, `phase_length_weeks`, `phase_count_expected`, `shortened_phases`, and `shortening_budget_weeks` as inherited Scenario authority; never choose a replacement cadence in Season Plan synthesis.
13. Preserve each slot's injected `cadence_week_roles` in the internal phase blueprint and reflect them in deload intent, typical duration/intensity pattern, and load-corridor notes.
14. Use `Deterministic Season Phase Load Context` as the binding feasibility reference for phase role, availability cap, baseline, recommended phase corridor, and role-week load bands.
15. When numeric phase-slot or phase-load contract values are needed, use the deterministic contract tools directly:
   - `workspace_get_phase_slot_contract`
   - `workspace_get_season_phase_load_context`
   Never search the workspace for a synthetic recommendation artifact.
16. Verify that phase count and ISO-week coverage match the season date range without gaps or overlaps.
17. Apply the selected cadence pattern (`2:1`, `3:1`, or `2:1:1`) to phase deload intent and rationale.
   - `2:1:1` means two load weeks, one mini-reset, and one reload; do not collapse it into a generic deload phase.
   - `3:1` means three load weeks and a materially reduced deload week.
   - `2:1` means two load weeks and a materially reduced deload week.
   - Shortened slots keep their injected shortened roles and should read as re-entry/consolidation, not as full-length cadence cycles.
18. Set strategic phase corridors from phase role + availability + progression context, not by copying availability capacity or inventing desired load.
19. Keep every emitted `cycle` schema-valid: `Base`, `Build`, `Peak`, or `Transition`.
20. Emit one review-ready season bundle, not multiple competing variants.
21. Final synthesis is integration work, not coworker re-discovery. Do not ask other agents to re-derive deterministic contract values during this step.
22. Carry season-level intensity-domain authority from the selected scenario into phase blueprints. A phase may narrow downstream semantics, but you must not reconstruct season authority backward from Phase Guardrails or another narrower downstream example.
23. Emit explicit canonical phase semantics for every phase blueprint:
   - `phase_type`
   - `phase_intent`
   - `build_subtype` when `phase_type = BUILD`
   - `phase_taxonomy_version`
   - explicit `forbidden_domains`
   - explicit `semantic_contract`
24. Keep `phase_type`, `phase_intent`, and `build_subtype` coherent with cycle, event position, phase role, and allowed-domain narrowing.
25. Treat `season_archetype` from the selected scenario as advisory upper-order sequencing authority; if it is `ceiling_first_durability`, derive early `vo2_build` only when explicitly justified, then preserve `durability_build` / `specificity_build` runway only when the deterministic context permits it.

Phase intent and intensity semantics:
- Multi-A-event planning may create one or more target macrocycles and may use an A-event peak cluster when spacing is too short for separate recovery/build/taper structures.
- Keep these macrocycle decisions at the Season-planning layer; do not invent new phase-taxonomy values to express them.

Canonical phase semantics:
- Use canonical `phase_type` values only:
  - `TRANSITION`
  - `PREPARATION`
  - `BASE`
  - `BUILD`
  - `PEAK`
  - `TAPER`
  - `RACE`
- Use canonical `phase_intent` values only:
  - `transition_recovery`
  - `preparation_re_entry`
  - `shortened_re_entry`
  - `general_base`
  - `aerobic_base`
  - `strength_endurance_base`
  - `sweet_spot_base`
  - `vo2_build`
  - `threshold_build`
  - `sst_build`
  - `durability_build`
  - `specificity_build`
  - `vlamax_lowering`
  - `peak_sharpening`
  - `taper_freshening`
  - `race_execution`
- For `BUILD` phases, `build_subtype` is required and must equal `phase_intent`.
- Restrict planning semantics to the canonical values listed above.

| Phase type | Phase intent | Build subtype | Planner purpose | Allowed intensity domains | Optional / conditional | Default avoid | Allowed load modalities | Semantic notes |
|---|---|---|---|---|---|---|---|---|
| `TRANSITION` | `transition_recovery` | `null` | reduce accumulated fatigue and restore freshness without building new load | `RECOVERY`, `ENDURANCE` | very light activation only if clearly useful | `SWEET_SPOT`, `THRESHOLD`, `VO2MAX` | `NONE` | Recovery-first phase. Restore rhythm without building structural load. |
| `PREPARATION` | `preparation_re_entry` | `null` | restore training rhythm and structural readiness before full base work | `ENDURANCE` | very light `TEMPO` only if continuity is stable | `SWEET_SPOT`, `THRESHOLD`, `VO2MAX` | `NONE`, `K3` | Pre-base re-entry and structural preparation. |
| `BASE` | `shortened_re_entry` | `null` | compressed re-entry with recovery protection and controlled continuity rebuild | `ENDURANCE` | very light `TEMPO` only if recovery is stable and re-entry is controlled | `SWEET_SPOT`, `THRESHOLD`, `VO2MAX` | `NONE`, `K3` | Compressed return after disruption or shortened horizon. |
| `BASE` | `general_base` | `null` | build broad aerobic base and repeatable training continuity without a narrow specialty focus | `ENDURANCE`, `TEMPO` | `SWEET_SPOT` when recovery is stable or time budget is tight | frequent `THRESHOLD`, much `VO2MAX` | `NONE`, `K3` | Broad later-base groundwork with controlled pressure work. |
| `BASE` | `aerobic_base` | `null` | prioritize low-intensity aerobic development, routine, and low-risk load tolerance | `ENDURANCE` | very light `TEMPO` only if clearly justified | `THRESHOLD`, `VO2MAX`, frequent `SWEET_SPOT` | `NONE`, `K3` | Aerobic routine, kJ tolerance, low density. |
| `BASE` | `strength_endurance_base` | `null` | develop torque, musculoskeletal robustness, and force endurance under controlled load | `ENDURANCE`, `TEMPO` | `SWEET_SPOT` only if structurally coherent | `THRESHOLD`, repeated `VO2MAX` | `NONE`, `K3` | Torque/structure-oriented base with explicit K3 pathway. |
| `BASE` | `sweet_spot_base` | `null` | raise sustainable sub-threshold capacity while preserving base continuity | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | controlled SST only | `VO2MAX`, frequent `THRESHOLD` | `NONE`, `K3` | Sustainable-power base without broad build drift. |
| `BUILD` | `vo2_build` | `vo2_build` | raise aerobic ceiling as the primary build objective | `ENDURANCE`, `VO2MAX` | sparse `TEMPO`/`SWEET_SPOT` support only | chronic threshold accumulation | `NONE` | Aerobic-ceiling build; VO2 is primary. |
| `BUILD` | `threshold_build` | `threshold_build` | improve sustained threshold power and clearance under repeatable structure | `ENDURANCE`, `TEMPO`, `THRESHOLD` | `SWEET_SPOT` support | broad VO2 escalation | `NONE`, `K3` | Sustained-power / threshold-oriented build. |
| `BUILD` | `sst_build` | `sst_build` | expand extensive sub-threshold capacity without tipping into broad high-intensity load | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted `THRESHOLD` only if explicitly justified | random HI density | `NONE`, `K3` | Extensive sub-threshold build. |
| `BUILD` | `durability_build` | `durability_build` | improve fatigue resistance, hard-late stability, and long-duration output under preload | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted `THRESHOLD`; rare `VO2MAX` maintenance only | high HI density | `NONE`, `K3` | Hard-late, B2B, preload, long-ride kJ, specific work under fatigue. |
| `BUILD` | `specificity_build` | `specificity_build` | train event-near demands through pacing, fueling, terrain, cadence, and logistics specificity | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted `THRESHOLD`; sparse VO2 maintenance only when explicitly useful | broad new VO2 loading, generic build drift | `NONE`, `K3` | Event-near pacing, fueling, terrain, cadence, logistics realism without taper logic. |
| `BUILD` | `vlamax_lowering` | `vlamax_lowering` | reduce glycolytic contribution and improve metabolic efficiency for long steady work | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted threshold only if coherent | anaerobic / VO2-heavy escalation | `NONE`, `K3` | Efficiency-oriented build; avoid needless glycolytic density. |
| `PEAK` | `peak_sharpening` | `null` | preserve readiness and sharpen event-specific execution without adding heavy new load | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | short primers/openers only if already proven | new VO2 blocks, heavy threshold accumulation | `NONE`, `K3` | Event-near sharpening and execution readiness. |
| `TAPER` | `taper_freshening` | `null` | reduce fatigue while preserving feel, timing, and event readiness | `RECOVERY`, `ENDURANCE` | short `TEMPO` or `SWEET_SPOT` primers; rare short `VO2MAX` opener if already known to work | new stimuli, long hard time-in-zone | `NONE` | Dedicated freshness phase. |
| `RACE` | `race_execution` | `null` | execute the event block with pacing, fueling, logistics, and recovery control | `RECOVERY`, `ENDURANCE`, `TEMPO` | short openers only if tied to event execution | new accumulation blocks | `NONE` | Event execution window, logistics, fueling, pacing, recovery. |

Reading rules:
- `allowed_intensity_domains` are permissions, not obligations.
- In `Transition`, `TEMPO` and `SWEET_SPOT` are conditional bridge tools, not default build work.
- `K3` appears only under `allowed_load_modalities`, not as an intensity domain.
- In `Peak`, `SWEET_SPOT` is low-dose maintenance/sharpening only.
- `sst_build` and `durability_build` may share intensity domains, but must differ through fatigue context, B2B, hard-late, preload, and long-ride kJ.
- `vo2_build` does not mean `VO2MAX` must dominate every week; it is still recovery-bounded.
- `specificity_build` is distinct from `durability_build` and `peak_sharpening`; it is event-near specificity without taper semantics.
- Phase intent may narrow scenario domains, but must not exceed scenario-level allowed domains.
- Authority flows only downward:
  - `scenario.allowed_domains` = upper seasonal authority
  - `phase.allowed_domains` = narrower phase authority
  - `week.allowed_domains` = fatigue-/execution-filtered week authority

Hard rules:
- emit one final season bundle with one or more target macrocycles
- use deterministic selected-scenario structure context for phase-length math
- preserve deterministic phase slots exactly
- do not infer cadence from athlete age, preference, or durability principles once a scenario is selected
- do not invent or search for a persisted `PHASE_LOAD_RECOMMENDATION` artifact; season phase load authority is code-owned deterministic context
- if injected phase-slot `blocking_issues` are present, surface them as Season bundle blocking issues
- if injected season phase load `blocking_issues` are present, surface them as Season bundle blocking issues
- never set a phase corridor above the injected availability cap unless the blueprint marks a review-visible exception
- every phase blueprint must include phase role, availability cap, baseline, role-week load bands, progression trace, and load feasibility status
- every phase blueprint must include `allowed_domains`; use durability-first semantics as `ENDURANCE` dominant, not `ENDURANCE only`
- every phase blueprint must include `phase_type`, `phase_intent`, and `phase_taxonomy_version`; include `build_subtype` whenever `phase_type = BUILD`
- every phase blueprint must include `forbidden_domains` and `semantic_contract`; do not leave method-critical season semantics in prose only
- the final season bundle must include deterministic `season_load_envelope` and `season_semantic_notes` so the writer can copy them directly
- never guess or alias legacy phase-intent labels during synthesis
- if the selected scenario permits `TEMPO` or other quality domains, at least one suitable later-season phase must preserve that allowance unless the bundle makes a clear phase-specific exclusion case
- make multi-`A` event structure audit-visible through phase narratives, event constraints, phase transition guardrails, season justification, and assumptions / revisit items even though there are no explicit macrocycle id fields yet
- mark coverage/cadence self-checks true only after verification
- surface infeasible load corridors explicitly with review/replan guidance

Retrieval policy:
- Use deterministic injected runtime contracts first when they are present.
- Use `workspace_get_latest` for latest authoritative planning artefacts and runtime snapshots when a task still needs direct retrieval.
- Use `workspace_get_input` only for athlete-managed inputs.
- Use `workspace_get_version` only for explicit week-sensitive historical artefacts.

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the task expected_output as one consolidated planning bundle or synthesis contribution.
- Include the selected inputs, phase blueprints, decisions, unresolved risks, and writer-ready summary needed by the next task.
- Preserve task boundaries and emit competing variants only when the task explicitly asks for them.
