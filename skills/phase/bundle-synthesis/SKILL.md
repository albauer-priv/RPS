---
name: bundle-synthesis
description: Synthesize phase specialist drafts into one internal PhaseBundle.
metadata:
  author: rps
  version: "1.0"
---
Combine phase drafts into one internal bundle.

Method:
1. Keep guardrails authoritative over structure.
2. Apply cadence/recovery as a constraint on structure, not as a separate plan.
3. Preserve event integration only where it does not violate season authority.
4. Use deterministic contract tools directly when exact phase-slot or phase-execution values are needed:
   - `workspace_get_phase_execution_context`
   - `workspace_get_phase_slot_contract`
5. Final synthesis is integration work, not rediscovery. Do not ask coworkers to re-derive deterministic week roles, exact phase range, or S5 bands during this step.
6. Emit one review-ready phase bundle.
7. Review should mostly confirm. Resolve all context-decidable role/load/structure/event contradictions before handoff.
8. Before handoff, explicitly self-check:
   - week roles complete and coherent
   - S5/load-band logic coherent
   - guardrails / structure / preview agree
   - phase semantics and domain shaping contain no unresolved contradictions
   - no assumption that the writer will repair bundle semantics

Retrieval policy:
- Use deterministic injected runtime contracts first when they are present.
- Use `workspace_get_phase_execution_context` and `workspace_get_phase_slot_contract` for exact authoritative phase values.
- Use `workspace_get_latest` for latest authoritative planning artefacts and runtime snapshots only when direct retrieval is still needed.
- Use `workspace_get_input` only for athlete-managed inputs.

Output format:
- Return the task expected_output as one consolidated planning bundle or synthesis contribution.
- Include the selected inputs, decisions, unresolved risks, and writer-ready summary needed by the next task.
- Preserve task boundaries and emit competing variants only when the task explicitly asks for them.
