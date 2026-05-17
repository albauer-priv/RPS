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
6. Verify that phase count and ISO-week coverage match the season date range without gaps or overlaps.
7. Apply the selected cadence pattern (`2:1`, `3:1`, or `2:1:1`) to phase deload intent and rationale.
8. Keep every emitted `cycle` schema-valid: `Base`, `Build`, `Peak`, or `Transition`.
9. Emit one review-ready season bundle, not multiple competing variants.

Hard rules:
- do not emit competing macrocycle variants in the final bundle
- do not invent alternate phase-length math when deterministic selected-scenario structure context is present
- do not add, remove, resize, or move deterministic phase slots
- do not mark coverage/cadence self-checks true unless they have actually been verified
- do not hide an infeasible load corridor inside optimistic wording
