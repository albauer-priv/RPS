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
- mark coverage/cadence self-checks true only after verification
- surface infeasible load corridors explicitly with review/replan guidance

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
