---
name: review-decision
description: Integrate season review findings into approve, reject, or bounded replan decisions.
metadata:
  author: rps
  version: "1.0"
---
Turn season review outputs into one binding decision.

Method:
1. Treat macrocycle, governance, and constraint blockers as approval gates.
2. Prefer bounded replan over broad restarts.
3. Replan instructions must preserve valid event anchors and unaffected macrocycle decisions.
4. If cadence, phase count, phase length, or ISO-week coverage conflicts with the selected Scenario, choose `replan_required` and target the Season synthesis/review specialists.
5. If the final writer-ready summary lacks phase blueprint semantics, including inherited cadence roles and A/B event treatment, choose `replan_required` rather than approving a vague artifact handoff.
6. Use deterministic season contract tools directly when exact contract values are needed:
   - `workspace_get_phase_slot_contract`
   - `workspace_get_season_phase_load_context`
7. Final review is decision work, not rediscovery. Do not ask coworkers to re-derive cadence, phase-slot, or phase-load contract authority during this step.
8. Treat the injected Candidate Season Bundle as the authoritative review subject. Do not reload or expect a synthetic `candidate_season_bundle` workspace artefact.

Positive operating guidance:
- Use the active task, injected context, and configured skill role to choose the smallest coherent contribution.
- Read the available evidence, check the governing constraints, and explain the decision path in direct operational language.
- Produce actionable content that helps the next task continue without recomputing or guessing.
- Include required facts, assumptions, warnings, and trace cues when they are available.
- Return a concise result that supports the task expected_output and preserves the authoritative runtime context.

Output format:
- Return the task expected_output with a clear decision status: `approved`, `replan_required`, or `rejected`.
- Include blocking issues, warnings, replan instructions, and writer-ready summary when applicable.
- State the concrete change needed before approval when the decision is not approved.
