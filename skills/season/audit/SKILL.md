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
- every phase has stable `phase_id`, schema-valid `cycle`, explicit `deload`, and cadence-based `deload_rationale`
- corridors above injected availability capacity are either rejected or escalated with explicit replan rationale

Block approval when:
- event hierarchy is contradictory
- a clustered-event plan tries to use repeated independent tapers
- a second peak is implied without an explicit multi-peak model
- season progression requires repeated catch-up or hidden overload
- a phase cycle is outside `Base | Build | Peak | Transition`
- deload rationale is missing where deload intent is present
- phase coverage has gaps, overlaps, or ambiguous week ownership
- an `A` event has no coherent `Peak`/`Transition` handling
- `self_check.every_phase_maps_to_cycle_and_deload_intent` is true while cycle/cadence/deload evidence is missing
