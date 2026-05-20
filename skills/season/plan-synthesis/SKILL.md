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
2. Keep load governance aligned with durability-first planning.
3. Resolve conflicts in favor of sustainable structure and explicit constraint compliance.
4. Use the injected selected-scenario structure math as the reference for planning horizon weeks, phase length, expected phase count, full phases, and shortened phases.
5. Use `Deterministic Season Phase Slot Context` as the binding skeleton for phase ids, order, ISO-week ranges, and phase lengths.
6. Treat `deload_cadence`, `phase_length_weeks`, `phase_count_expected`, `shortened_phases`, and `shortening_budget_weeks` as inherited Scenario authority; never choose a replacement cadence in Season Plan synthesis.
7. Preserve each slot's injected `cadence_week_roles` in the internal phase blueprint and reflect them in deload intent, typical duration/intensity pattern, and load-corridor notes.
8. Use `Deterministic Season Phase Load Context` as the binding feasibility reference for phase role, availability cap, baseline, recommended phase corridor, and role-week load bands.
9. When numeric phase-slot or phase-load contract values are needed, use the deterministic contract tools directly:
   - `workspace_get_phase_slot_contract`
   - `workspace_get_season_phase_load_context`
   Never search the workspace for a synthetic recommendation artifact.
10. Verify that phase count and ISO-week coverage match the season date range without gaps or overlaps.
11. Apply the selected cadence pattern (`2:1`, `3:1`, or `2:1:1`) to phase deload intent and rationale.
   - `2:1:1` means two load weeks, one mini-reset, and one reload; do not collapse it into a generic deload phase.
   - `3:1` means three load weeks and a materially reduced deload week.
   - `2:1` means two load weeks and a materially reduced deload week.
   - Shortened slots keep their injected shortened roles and should read as re-entry/consolidation, not as full-length cadence cycles.
12. Set strategic phase corridors from phase role + availability + progression context, not by copying availability capacity or inventing desired load.
13. Keep every emitted `cycle` schema-valid: `Base`, `Build`, `Peak`, or `Transition`.
14. Emit one review-ready season bundle, not multiple competing variants.
15. Final synthesis is integration work, not coworker re-discovery. Do not ask other agents to re-derive deterministic contract values during this step.
16. Carry season-level intensity-domain authority from the selected scenario into phase blueprints. A phase may narrow downstream semantics, but you must not reconstruct season authority backward from Phase Guardrails or another narrower downstream example.
17. Emit one normalized `phase_intent` for every phase blueprint and keep it coherent with cycle, event position, phase role, and allowed-domain narrowing.
18. Treat `season_archetype` from the selected scenario as advisory upper-order sequencing authority; if it is `ceiling_first_durability`, derive early `ceiling_support`, optional `transition_coupling`, later `durability_build`, and `specificity_build` only when the deterministic context permits it.

Phase intent and intensity semantics:
- Use only schema-valid cycles: `Base`, `Build`, `Peak`, `Transition`.
- Do not invent new cycle values such as `Specificity` or `Taper`.
- Represent finer planning intent through phase intent semantics inside the active cycle.

| Cycle | Phase intent | Existing / aligned repo term | Allowed intensity domains | Optional / conditional | Default avoid | Allowed load modalities | Semantic notes |
|---|---|---|---|---|---|---|---|
| `Transition` | `recovery_reset` | aligns with `Transition`; may include `re-entry`, `reset`, `post-event restoration` | `RECOVERY`, `ENDURANCE` | very light activation only if clearly useful | `SWEET_SPOT`, `THRESHOLD`, `VO2MAX` | `NONE` | Recovery-first phase. Restore rhythm without building structural load. |
| `Transition` | `shortened_re_entry` | `shortened_re_entry` | `ENDURANCE` | very light `TEMPO` only if recovery is stable and re-entry is clearly controlled | `SWEET_SPOT`, `THRESHOLD`, `VO2MAX` | `NONE`, `K3` | Shortened return after disruption or compressed horizon. Controlled load re-establishment, not full build logic. |
| `Transition` | `shortened_consolidation` | `shortened_consolidation` | `ENDURANCE` | selected `TEMPO` only if scenario-permitted and continuity is stable | `SWEET_SPOT`, `THRESHOLD`, `VO2MAX` | `NONE`, `K3` | Bridge phase after re-entry. Consolidate execution and preserve runway for later build phases. |
| `Transition` | `transition_consolidation` | `transition_consolidation` | `ENDURANCE` | `TEMPO`; `SWEET_SPOT` only as rare primer if scenario-permitted and recovery is coherent | `VO2MAX`, frequent `THRESHOLD`, accumulated `SWEET_SPOT` | `NONE`, `K3` | Controlled bridge phase, not hidden build work. Tempo/SST are bridge tools only, not default progression load. |
| `Base` | `foundation` | aligns with Base semantics in macrocycle architecture | `ENDURANCE` | very light `TEMPO` only if clearly justified | `THRESHOLD`, `VO2MAX`, frequent `SWEET_SPOT` | `NONE`, `K3` | Early groundwork: aerobic routine, kJ tolerance, passive structure preparation, low density. |
| `Base` | `general_build` | aligns with active Base/general-build wording | `ENDURANCE`, `TEMPO` | `SWEET_SPOT` when recovery is stable or time budget is tight | frequent `THRESHOLD`, much `VO2MAX` | `NONE`, `K3` | Later groundwork: still endurance-dominant, with first controlled pressure work. Pyramidal-leaning. |
| `Build` | `build_progression` | aligns with generic `Build` progression semantics | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | `THRESHOLD` only if explicitly justified by scenario and recovery | high HI density, random `VO2MAX` | `NONE`, `K3` | General build progression: more structure, controlled progression, event-relevant load growth without losing durability-first control. |
| `Build` | `ceiling_support` | repo-aligned semantic only | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | short `VO2MAX` support block only when fresh and explicitly useful | chronic `THRESHOLD` load, broad HI escalation | `NONE`, `K3` | Early/mid build where aerobic ceiling support may be useful. HI remains support capacity, not the main motor. |
| `Build` | `transition_coupling` | repo-aligned semantic only | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | rare short `VO2MAX` retention only when clearly justified | broad VO2 block, hidden threshold accumulation | `NONE`, `K3` | Bridge phase: maintain some ceiling support while shifting toward economy and durability. |
| `Build` | `durability_build` | repo-aligned semantic only | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted `THRESHOLD`; rare `VO2MAX` maintenance only | high HI density | `NONE`, `K3` | Later build focused on fatigue-resistant output: hard-late, B2B, preload, long-ride kJ, and specific work under fatigue. Intensity is not the main escalation lever; fatigue-context specificity is. |
| `Build` / `Peak` | `specificity_build` | repo-aligned semantic only | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted `THRESHOLD`; rehearsal-specific sharpening only when scenario-permitted | broad new VO2 loading, generic build drift | `NONE`, `K3` | Event-near but still non-taper build. Emphasize pacing, fueling, terrain, cadence, logistics, and race-like long-duration structure without full taper logic. |
| `Build` | `b_event_rehearsal` | `b_event_rehearsal` | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted rehearsal-specific sharpening only if scenario-permitted | full taper logic, broad new HI blocks | `NONE`, `K3` | B event is rehearsal/minor adjustment only. Preserve long-build continuity and A-event runway. |
| `Peak` | `peak_preparation` | `peak_preparation` | `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | short primers/openers only if already proven | new VO2 blocks, heavy threshold accumulation, new `SWEET_SPOT` accumulation | `NONE`, `K3` | Event-near sharpening and specificity through pacing, fueling, preload, and execution realism. Sweet spot here is maintenance/sharpening only, not a new accumulation block. |
| `Peak` | `a_event_peak_taper` | `a_event_peak_taper` | `RECOVERY`, `ENDURANCE` | short `TEMPO` or `SWEET_SPOT` primers; rare short `VO2MAX` opener if already known to work | new stimuli, long hard time-in-zone | `NONE` | Dedicated A-event taper. Freshness first; maintain feel without creating fatigue debt. |

Reading rules:
- `allowed_intensity_domains` are permissions, not obligations.
- In `Transition`, `TEMPO` and `SWEET_SPOT` are conditional bridge tools, not default build work.
- `K3` appears only under `allowed_load_modalities`, not as an intensity domain.
- In `Peak`, `SWEET_SPOT` is low-dose maintenance/sharpening only.
- `build_progression` and `durability_build` may share the same intensity domains, but must differ through fatigue context, B2B, hard-late, preload, and long-ride kJ.
- `ceiling_support` does not mean `VO2MAX` must appear.
- `specificity_build` is distinct from `durability_build`, `b_event_rehearsal`, and `peak_preparation`; it is event-near specificity without full rehearsal or taper semantics.
- Phase intent may narrow scenario domains, but must not exceed scenario-level allowed domains.
- Authority flows only downward:
  - `scenario.allowed_domains` = upper seasonal authority
  - `phase.allowed_domains` = narrower phase authority
  - `week.allowed_domains` = fatigue-/execution-filtered week authority

Hard rules:
- emit one final macrocycle bundle
- use deterministic selected-scenario structure context for phase-length math
- preserve deterministic phase slots exactly
- do not infer cadence from athlete age, preference, or durability principles once a scenario is selected
- do not invent or search for a persisted `PHASE_LOAD_RECOMMENDATION` artifact; season phase load authority is code-owned deterministic context
- if injected phase-slot `blocking_issues` are present, surface them as Season bundle blocking issues
- if injected season phase load `blocking_issues` are present, surface them as Season bundle blocking issues
- never set a phase corridor above the injected availability cap unless the blueprint marks a review-visible exception
- every phase blueprint must include phase role, availability cap, baseline, role-week load bands, progression trace, and load feasibility status
- every phase blueprint must include `allowed_domains`; use durability-first semantics as `ENDURANCE` dominant, not `ENDURANCE only`
- every phase blueprint must include `phase_intent`; do not leave it implicit in prose
- if the selected scenario permits `TEMPO` or other quality domains, at least one suitable later-season phase must preserve that allowance unless the bundle makes a clear phase-specific exclusion case
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
