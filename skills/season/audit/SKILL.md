---
name: audit
description: Audit season bundles for macrocycle coherence, taper validity, and durability-first governance.
metadata:
  author: rps
  version: "4.0"
---
Audit the candidate season bundle holistically.

Checklist:
- exactly one `A` event per macrocycle
- every taper behavior serves an `A` event and remains inside a schema-valid `Peak` cycle
- `B` and `C` events fit without breaking macrocycle structure
- recovery and transition phases are explicitly planned
- peak logic is consistent with event spacing
- load governance remains sustainable and durability-first
- phase ISO-week coverage is gap-free and overlap-free
- phase count, phase lengths, and cadence semantics match the selected Scenario and deterministic phase-slot context
- every phase blueprint preserves injected `cadence_week_roles`
- every phase has stable `phase_id`, schema-valid `cycle`, explicit `deload`, and cadence-based `deload_rationale`
- corridors above injected availability capacity are either rejected or escalated with explicit replan rationale
- final `A` event taper load is meaningfully lower than Build/Re-entry unless an explicit review rationale explains why not
- `B` event handling is rehearsal/minor adjustment only and never an independent full taper or peak

Block approval when:
- event hierarchy is contradictory
- a clustered-event plan tries to use repeated independent tapers
- a second peak is implied without an explicit multi-peak model
- season progression requires repeated catch-up or hidden overload
- Season Plan implies a different cadence than the selected Scenario
- deterministic phase-slot `blocking_issues` are present and unresolved
- `2:1:1` is inherited but mini-reset/reload semantics are missing from phase blueprint or final phase rationale
- corridors copy availability capacity across unrelated phases instead of expressing progression, re-entry, rehearsal, or taper intent
- durability-first is collapsed into intensity-free planning without `RECOVERY`/dominant `ENDURANCE` plus scenario-permitted targeted quality semantics
- a phase cycle is outside `Base | Build | Peak | Transition`
- deload rationale is missing where deload intent is present
- phase coverage has gaps, overlaps, or ambiguous week ownership
- an `A` event lacks coherent `Peak`/`Transition` handling
- `self_check.every_phase_maps_to_cycle_and_deload_intent` is true while cycle/cadence/deload evidence is missing

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
