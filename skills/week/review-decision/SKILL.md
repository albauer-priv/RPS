---
name: review-decision
description: Integrate week review findings into approve, reject, or bounded replan decisions.
metadata:
  author: rps
  version: "1.0"
---
Combine week review outputs into one explicit decision.

Decision order:
1. Any syntax, workout-policy semantic, or load-safety blocker can stop approval.
1a. Any mismatch between inherited canonical phase semantics (`phase_type`, `phase_intent`, `build_subtype`) and the candidate week shape or workout family mix is a blocker unless explicitly bounded and justified.
2. Preserve must-keep constraints and identify smallest acceptable replan scope.
3. Return either `approved`, `replan_required`, or `rejected`.
4. Replan instructions must name target specialists, issues to fix, and what must stay unchanged.
5. Use deterministic week contract tools directly when exact contract values are needed:
   - `workspace_get_week_calendar_context`
   - `workspace_get_phase_execution_context`
6. Final review is decision work, not rediscovery. Do not ask coworkers to re-derive active week role, active band, availability caps, or recovery-day authority during this step.
7. Review is primarily a formal approval gate. Default to `approved` when finalize already produced a contract-clean, export-safe bundle.

Output format:
- Return the task expected_output with a clear decision status: `approved`, `replan_required`, or `rejected`.
- Include blocking issues, warnings, replan instructions, and writer-ready summary when applicable.
- State the concrete change needed before approval when the decision is not approved.
