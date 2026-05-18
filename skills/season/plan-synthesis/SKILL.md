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
- emit one final macrocycle bundle
- use deterministic selected-scenario structure context for phase-length math
- preserve deterministic phase slots exactly
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
- Include the selected inputs, decisions, unresolved risks, and writer-ready summary needed by the next task.
- Preserve task boundaries and emit competing variants only when the task explicitly asks for them.
