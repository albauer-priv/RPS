---
name: review-decision
description: Integrate week review findings into approve, reject, or bounded replan decisions.
metadata:
  author: rps
  version: "1.0"
---
Combine week review outputs into one explicit decision.

Decision order:
1. Any syntax or load-safety blocker can stop approval.
2. Preserve must-keep constraints and identify smallest acceptable replan scope.
3. Return either `approved`, `replan_required`, or `rejected`.
4. Replan instructions must name target specialists, issues to fix, and what must stay unchanged.

Output format:
- Return the task expected_output with a clear decision status: `approved`, `replan_required`, or `rejected`.
- Include blocking issues, warnings, replan instructions, and writer-ready summary when applicable.
- State the concrete change needed before approval when the decision is not approved.
