---
name: review-decision
description: Integrate phase review outputs into approve, reject, or bounded replan decisions.
metadata:
  author: rps
  version: "2.0"
---
Turn phase review outputs into one explicit decision.

Definitions:
- `BL_kJ`: baseline weekly governance-load anchor for the exact phase range
- `prior_week_kJ`: previous comparable build-week governance load
- `DL_kJ`: deload governance-load target
- `RE_kJ`: re-entry governance-load target
- `MR_kJ`: mini-reset governance-load target
- `W1_kJ`, `W2_kJ`, `W3_kJ`, `W4_kJ`: cadence-step governance-load targets used to review exact-range overload interpretation
- `weekly_kj_bands`: exact-range governance-load bands for the phase weeks
- `week_role`: inherited deterministic week-role labels for the exact phase range

Authority / injected sources:
- exact-range week roles and phase execution authority come from `workspace_get_phase_execution_context`
- exact phase-slot contract context comes from `workspace_get_phase_slot_contract`
- this layer reviews exact-range overload calculations; it does not author new cadence math

Method:
1. Treat guardrail, governance, and exact-range violations as approval gates.
2. Keep replan scope as small as possible.
3. Preserve approved upstream decisions and unaffected phase sections.
4. Use deterministic phase contract tools directly when exact contract values are needed:
   - `workspace_get_phase_execution_context`
   - `workspace_get_phase_slot_contract`
5. Final review is decision work, not rediscovery. Do not ask coworkers to re-derive phase-range, week-role, or S5 contract authority during this step.
6. Review is primarily a formal approval gate. Default to `approved` when finalize already produced a contract-clean, semantically coherent bundle.
7. Gate inherited overload-policy execution explicitly:
   - cadence family is visible in structure
   - deload / mini-reset / reload / re-entry semantics are correct and distinct
   - fallback behavior is applied when readiness/fatigue makes the nominal pattern unsafe
   - Build-entry logic remains conservative after shortened/base/re-entry context
   - week-role/load-shape does not violate inherited season overload policy
8. If phase intent contradicts legal allowed/forbidden domain authority, choose `replan_required`.
9. Objective mismatch remains warning-only and input-owned. Surface it, but do not require approval solely to force a rewrite.

Progression rules under review:
- one overload axis at a time unless an explicit bounded exception exists
- duration / work before density, density before intensity where relevant
- no hidden catch-up or recovery compression

Operational checks for exact-range phase review:
- the emitted phase structure must show which exact weeks are:
  - build
  - deload
  - mini-reset
  - reload
  - re-entry
- `reload` is valid only when the week is intended to return near prior build load
- `re-entry` is required when the week is baseline-anchored, lower, and explicitly controlled after fatigue or true deload
- `2:1:1` phases must show:
  - two build weeks
  - one mini-reset week at roughly `W2 * 0.80-0.90`
  - one reload week at roughly `W2 * 0.95-1.05`
- if poor readiness turns the mini-reset into true deload, W4 must be reviewed as re-entry instead of reload
- `3:1` phases must show three progressive build exposures plus one materially reduced deload week
- `2:1` phases must show two progressive build exposures plus one materially reduced deload week

Failure triggers:
- if phase guardrails or structure use the cadence label but the weekly semantics do not match it, choose `replan_required`
- if week-role/load-shape implies threshold-led work while `THRESHOLD` is suppressed upstream, choose `replan_required`
- if early Build entry is too aggressive for the inherited shortened/base/re-entry context and no explicit readiness gate is carried, choose `replan_required`

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
