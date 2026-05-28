---
name: plan-synthesis
description: Synthesize season specialist drafts into one internal season bundle.
metadata:
  author: rps
  version: "3.0"
---
Consolidate season drafts into one candidate bundle.

Definitions:
- `planned_kj`: mechanical work estimate at workout/day level; not the season corridor metric
- `planned_weekly_load_kj`: governance week-load metric used for season corridor/band semantics
- `BL_kJ`: baseline weekly governance-load anchor used to interpret overload, deload, and re-entry in season reasoning
- `prior_week_kJ`: previous comparable build-week governance load
- `DL_kJ`: deload governance-load target
- `RE_kJ`: re-entry governance-load target
- `MR_kJ`: mini-reset governance-load target
- `W1_kJ`, `W2_kJ`, `W3_kJ`, `W4_kJ`: cadence-step governance-load targets
- `BL_kJ_next`: conservative next-baseline anchor after a completed cadence sequence
- `phase_role`: deterministic seasonal role attached to a phase slot
- `cadence_week_roles`: inherited deterministic week-role sequence for the slot
- `allowed_domains`: season- or phase-authorized intensity-domain permissions
- `forbidden_domains`: explicit domains excluded for the phase blueprint

Authority / injected sources:
- phase-slot geometry and `cadence_week_roles` come from `Deterministic Season Phase Slot Context`
- phase-role, availability cap, baseline, recommended corridor, and role-week load bands come from `Deterministic Season Phase Load Context`
- load-estimation math and `IF_ref_load` semantics remain owned by `skills/shared/load-estimation-core/SKILL.md`
- if `BL_kJ` is not directly surfaced, use the deterministic baseline/progression information already embedded in the phase load context; do not derive it ad hoc from prose
- this layer must not compute workout-level load math

Method:
1. Pass 1 - structural draft: preserve event hierarchy and macrocycle logic while assembling a structurally coherent candidate bundle.
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
17a. Carry the full progressive overload policy into the season bundle:
   - choose and explain cadence-family rationale from robustness, recovery, and risk context
   - keep ramp class explicit (`conservative`, `standard`, or rare `aggressive`)
   - keep deload, mini-reset, reload, and re-entry semantically distinct
   - if `2:1:1` mini-reset becomes a true deload, treat the following week as re-entry
   - if `3:1` shows repeated week-3 collapse risk, push toward a more conservative cadence framing
   - if `2:1` repeatedly over-recovers or stalls, note that more productive cadence families may need reconsideration
   - use conservative next-baseline logic rather than anchoring future progression to the single highest visible week
   - readiness-gate the first Build step after shortened, base, or re-entry context

Progression axes:
- duration / total governance work
- frequency where the deterministic slot structure permits it
- density / complexity of quality placement
- intensity last

Progression rules:
- progress only one overload axis per step unless an explicit bounded exception is stated
- do not use intensity first to repair corridor misses
- do not hide missed-load compensation inside later phases or later weeks

Operational overload-policy translation into season blueprints:
- if cadence is `3:1`, make the phase narrative and week-role meaning reflect three progressive load opportunities before the deload
- if cadence is `2:1`, make the phase narrative and week-role meaning reflect two progressive load opportunities before the deload
- if cadence is `2:1:1`, make the phase narrative and week-role meaning reflect:
  - W1 controlled build entry
  - W2 progressive build
  - W3 mini-reset
  - W4 reload near W2
- if fallback is needed:
  - W3 may become true deload
  - W4 must then be treated as re-entry
- do not leave these semantics implicit; they must be recoverable from phase blueprints, progression traces, and week-role notes
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
26. Pass 2 - semantic finalization: finalize must leave review with a nearly writer-ready bundle. Do not rely on the writer to repair semantic contradictions that are already decidable here.
27. Pass 3 - planner self-audit: before handoff, explicitly self-check:
   - no phantom event placeholders
   - no positive framing of forbidden domains
   - no unresolved scenario/phase authority drift
   - no unresolved cadence / reset / taper contradictions
   - no unresolved overload-policy contradictions around ramp class, fallback path, reload vs re-entry, or Build-entry readiness
   - no Build intent contradicts its legal intensity domains
   - objective mismatch, if present, surfaced only as warning/revisit item
   - if structure, macrocycle order, event anchoring, or phase-slot authority is wrong, return to Pass 1
   - if structure is valid but overload semantics, legality explanation, or writer-ready summary is incomplete, return to Pass 2
28. Treat `phase_blueprints[].event_constraints` as a compact real-event trace:
   - emit `[]` when a phase has no real event-linked constraint
   - emit short positive real-event lines when a phase does have one
   - never emit negative placeholder prose such as `No target-week event`, `No logistics exception`, or `No event-driven load exception`

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
| `PREPARATION` | `preparation_re_entry` | `null` | restore training rhythm and structural readiness before full base work | `RECOVERY`, `ENDURANCE` | very light `TEMPO` only if continuity is stable | `SWEET_SPOT`, `THRESHOLD`, `VO2MAX` | `NONE` | Pre-base re-entry and structural preparation. |
| `BASE` | `shortened_re_entry` | `null` | compressed re-entry with recovery protection and controlled continuity rebuild | `RECOVERY`, `ENDURANCE` | light `TEMPO`/`SWEET_SPOT` only if recovery is stable and re-entry is controlled | `THRESHOLD`, `VO2MAX` | `NONE`, `K3` | Compressed return after disruption or shortened horizon. |
| `BASE` | `general_base` | `null` | build broad aerobic base and repeatable training continuity without a narrow specialty focus | `RECOVERY`, `ENDURANCE`, `TEMPO` | `SWEET_SPOT` when recovery is stable or time budget is tight | frequent `THRESHOLD`, much `VO2MAX` | `NONE`, `K3` | Broad later-base groundwork with controlled pressure work. |
| `BASE` | `aerobic_base` | `null` | prioritize low-intensity aerobic development, routine, and low-risk load tolerance | `RECOVERY`, `ENDURANCE` | very light `TEMPO` only if clearly justified | `THRESHOLD`, `VO2MAX`, frequent `SWEET_SPOT` | `NONE`, `K3` | Aerobic routine, kJ tolerance, low density. |
| `BASE` | `strength_endurance_base` | `null` | develop torque, musculoskeletal robustness, and force endurance under controlled load | `RECOVERY`, `ENDURANCE`, `TEMPO` | `SWEET_SPOT` only if structurally coherent | `THRESHOLD`, repeated `VO2MAX` | `NONE`, `K3` | Torque/structure-oriented base with explicit K3 pathway. |
| `BASE` | `sweet_spot_base` | `null` | raise sustainable sub-threshold capacity while preserving base continuity | `RECOVERY`, `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | controlled SST only | `VO2MAX`, frequent `THRESHOLD` | `NONE`, `K3` | Sustainable-power base without broad build drift. |
| `BUILD` | `vo2_build` | `vo2_build` | raise aerobic ceiling as the primary build objective | `RECOVERY`, `ENDURANCE`, `VO2MAX` | sparse `TEMPO` support only | chronic threshold accumulation | `NONE`, `K3` | Aerobic-ceiling build; VO2 is primary. |
| `BUILD` | `threshold_build` | `threshold_build` | improve sustained threshold power and clearance under repeatable structure | `RECOVERY`, `ENDURANCE`, `TEMPO`, `THRESHOLD` | `SWEET_SPOT` support | broad VO2 escalation | `NONE`, `K3` | Sustained-power / threshold-oriented build. |
| `BUILD` | `sst_build` | `sst_build` | expand extensive sub-threshold capacity without tipping into broad high-intensity load | `RECOVERY`, `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted `THRESHOLD` only if explicitly justified | random HI density | `NONE`, `K3` | Extensive sub-threshold build. |
| `BUILD` | `durability_build` | `durability_build` | improve fatigue resistance, hard-late stability, and long-duration output under preload | `RECOVERY`, `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted `THRESHOLD` only | high HI density, VO2 escalation | `NONE`, `K3` | Hard-late, B2B, preload, long-ride kJ, specific work under fatigue. |
| `BUILD` | `specificity_build` | `specificity_build` | train event-near demands through pacing, fueling, terrain, cadence, and logistics specificity | `RECOVERY`, `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted `THRESHOLD` only when explicitly useful | broad new VO2 loading, generic build drift | `NONE`, `K3` | Event-near pacing, fueling, terrain, cadence, logistics realism without taper logic. |
| `BUILD` | `vlamax_lowering` | `vlamax_lowering` | reduce glycolytic contribution and improve metabolic efficiency for long steady work | `RECOVERY`, `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | targeted threshold only if coherent | anaerobic / VO2-heavy escalation | `NONE`, `K3` | Efficiency-oriented build; avoid needless glycolytic density. |
| `PEAK` | `peak_sharpening` | `null` | preserve readiness and sharpen event-specific execution without adding heavy new load | `RECOVERY`, `ENDURANCE`, `TEMPO`, `SWEET_SPOT` | short primers/openers only if already proven | new VO2 blocks, heavy threshold accumulation | `NONE` | Event-near sharpening and execution readiness. |
| `TAPER` | `taper_freshening` | `null` | reduce fatigue while preserving feel, timing, and event readiness | `RECOVERY`, `ENDURANCE` | short `TEMPO` or `SWEET_SPOT` primers only | new stimuli, long hard time-in-zone, VO2 blocks | `NONE` | Dedicated freshness phase. |
| `RACE` | `race_execution` | `null` | execute the event block with pacing, fueling, logistics, and recovery control | `RECOVERY`, `ENDURANCE`, `TEMPO` | short openers only if tied to event execution | new accumulation blocks | `NONE` | Event execution window, logistics, fueling, pacing, recovery. |

Reading rules:
- `allowed_intensity_domains` are permissions, not obligations.
- In `Transition`, `TEMPO` and `SWEET_SPOT` are conditional bridge tools, not default build work.
- `K3` appears only under `allowed_load_modalities`, not as an intensity domain.
- `RECOVERY` is a legal non-quality execution domain; it is never an obligation and never substitutes for `REST`.
- In `Peak`, `SWEET_SPOT` is low-dose maintenance/sharpening only.
- `sst_build` and `durability_build` may share intensity domains, but must differ through fatigue context, B2B, hard-late, preload, and long-ride kJ.
- `vo2_build` does not mean `VO2MAX` must dominate every week; it is still recovery-bounded.
- `specificity_build` is distinct from `durability_build` and `peak_sharpening`; it is event-near specificity without taper semantics.
- Phase intent may narrow scenario domains, but must not exceed scenario-level allowed domains.
- A Build intent whose defining domain is not legal must not be emitted.
- `threshold_build` requires legal `THRESHOLD` plus threshold-led narrative and structure.
- prefer `durability_build` when the block is driven by long-duration work, preload, hard-late stability, fatigue resistance, B2B structure, or long-ride kJ tolerance
- prefer `sst_build` only for true extensive sub-threshold capacity work rather than durability-first fatigue structure
- after shortened/base/re-entry context, early Build semantics should be conservative and readiness-gated rather than immediately maximal
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
- every phase blueprint must include `allowed_load_modalities` from canonical semantics; do not let `K3` become mandatory by omission of `NONE`
- every phase blueprint must include `phase_type`, `phase_intent`, and `phase_taxonomy_version`; include `build_subtype` whenever `phase_type = BUILD`
- every phase blueprint must include `forbidden_domains` and `semantic_contract`; do not leave method-critical season semantics in prose only
- the final season bundle must include deterministic `season_load_envelope` and `season_semantic_notes` so the writer can copy them directly
- the final season bundle must serialize real event constraints only; never emit synthetic “no event” placeholders into `events_constraints`
- for internal `phase_blueprints[].event_constraints`, prefer these shapes:
  - `[]`
  - `["2026-09-12 A event: dedicated taper-contained event handling."]`
  - `["2026-08-15 B event: rehearsal within ongoing build."]`
  Keep each line factual, short, and tied to a real planning event.
- if the objective appears materially misaligned with the highest in-horizon A event, surface that as a warning/revisit item; do not block synthesis solely for that mismatch
- objective mismatch is input-owned; do not rewrite, soften, or reinterpret the user objective during synthesis
- do not leave review to discover normal semantic cleanup that can be decided here
- do not assume the writer will improve or reinterpret bundle semantics
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
