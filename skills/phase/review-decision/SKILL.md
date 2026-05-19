---
name: review-decision
description: Integrate phase review outputs into approve, reject, or bounded replan decisions.
metadata:
  author: rps
  version: "1.0"
---
Turn phase review outputs into one explicit decision.

Method:
1. Treat guardrail, governance, and exact-range violations as approval gates.
2. Keep replan scope as small as possible.
3. Preserve approved upstream decisions and unaffected phase sections.
4. Use deterministic phase contract tools directly when exact contract values are needed:
   - `workspace_get_phase_execution_context`
   - `workspace_get_phase_slot_contract`
5. Final review is decision work, not rediscovery. Do not ask coworkers to re-derive phase-range, week-role, or S5 contract authority during this step.

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
