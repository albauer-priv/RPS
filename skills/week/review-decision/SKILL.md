---
name: review-decision
description: Integrate week review findings into approve, reject, or bounded replan decisions.
metadata:
  author: rps
  version: "2.0"
---
Combine week review outputs into one explicit decision.

Definitions:
- `planned_kj`: mechanical workout/day work estimate
- `planned_weekly_load_kj`: governance week-load metric used for active-band compliance
- `active_weekly_kj_band`: binding target-week governance band
- `reload`: controlled return near prior build load
- `re-entry`: baseline-anchored controlled return after deload or unresolved fatigue

Authority / injected sources:
- exact target-week authority comes from:
  - `workspace_get_week_calendar_context`
  - `workspace_get_phase_execution_context`
- this layer makes an approval decision only; it does not invent new week math or workout legality

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
8. Formal review confirmation checklist:
   - contract-clean or not
   - writer-ready or not
   - Pass 1 return vs Pass 2 return classification if not clean
   - bounded replan instructions only
   - no semantic rewriting in review
9. Use Pass 1 return when agenda/day/workout blueprint structure or deterministic week authority alignment is wrong.
10. Use Pass 2 return when structure is intact but load semantics, reconciliation, durability-first tradeoffs, legality framing, or writer-ready summary is incomplete.
11. Gate the full week-policy stack explicitly:
   - governance-load semantics vs mechanical-work semantics
   - active week-band compliance
   - duration-first reconciliation
   - inherited progressive-overload role semantics
   - durability-first repeatability and no catch-up behavior
   - workout-policy legality and export-safe syntax

Operational approval rules:
- approve only when the week is structurally coherent, not merely numerically close
- require replan when:
  - recovery/fixed-rest protection was used as hidden catch-up space
  - intensity was escalated mainly to force corridor compliance
  - deload / mini-reset / reload / re-entry semantics are inconsistent with the active week role
  - workout family legality/exportability is still unresolved

Output format:
- Return the task expected_output with a clear decision status: `approved`, `replan_required`, or `rejected`.
- Include blocking issues, warnings, replan instructions, and writer-ready summary when applicable.
- State the concrete change needed before approval when the decision is not approved.
