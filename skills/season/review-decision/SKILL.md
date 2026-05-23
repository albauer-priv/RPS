---
name: review-decision
description: Integrate season review findings into approve, reject, or bounded replan decisions.
metadata:
  author: rps
  version: "2.0"
---
Turn season review outputs into one binding decision.

Definitions:
- `BL_kJ`: baseline weekly governance-load anchor used by the approved overload policy
- `prior_week_kJ`: previous comparable build-week governance load
- `DL_kJ`: deload governance-load target
- `RE_kJ`: re-entry governance-load target
- `MR_kJ`: mini-reset governance-load target
- `W1_kJ`, `W2_kJ`, `W3_kJ`, `W4_kJ`: cadence-step governance-load targets used for review of season progression semantics
- `planned_weekly_load_kj`: governance week-load metric used for corridor semantics

Authority / injected sources:
- exact phase-slot and phase-load contract values come from:
  - `workspace_get_phase_slot_contract`
  - `workspace_get_season_phase_load_context`
- this layer reviews overload semantics; it does not create new cadence math or compute workout-level work

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
9. Review is primarily a formal approval gate. Default to `approved` when finalize already produced a contract-clean, semantically coherent bundle.
10. Use `replan_required` only for real residual defects that finalize did not resolve.
11. Gate the full progressive overload policy explicitly:
   - cadence-family coherence
   - ramp class plausibility
   - deload / mini-reset / reload / re-entry semantics
   - fallback correctness for `2:1`, `3:1`, and `2:1:1`
   - conservative next-baseline handling
   - readiness-gated first Build entry after shortened/base/re-entry context
12. Objective mismatch remains warning-only and input-owned. Surface it, but do not require approval solely to force a rewrite of the user objective.
13. If any Build intent contradicts its legal intensity domains, choose `replan_required`.

Progression rules under review:
- one overload axis at a time unless an explicit bounded exception exists
- duration / total governance work before density, density before intensity where relevant
- no hidden catch-up progression after missed load

Operational overload-policy checks:
- `3:1` is coherent only when the bundle visibly supports:
  - `W1 = BL * 1.00-1.05`
  - `W2 = W1 * 1.08-1.12`
  - `W3 = W2 * 1.06-1.10`
  - then a materially reduced deload
- `2:1` is coherent only when the bundle visibly supports:
  - `W1 = BL * 1.00-1.05`
  - `W2 = W1 * 1.08-1.15`
  - then a materially reduced deload
- `2:1:1` is coherent only when the bundle visibly supports:
  - `W1 = BL * 1.00-1.05`
  - `W2 = W1 * 1.08-1.12`
  - `MR = W2 * 0.80-0.90`
  - `W4 = W2 * 0.95-1.05`
- deload targets should follow one of:
  - `DL = BL * 0.60-0.80`
  - `DL = prior_build_week * 0.55-0.75`
- re-entry targets should follow one of:
  - default `RE = BL * 0.90-1.00`
  - high-fatigue `RE = BL * 0.85-0.95`
  - robust/fresh only `RE = BL * 0.95-1.05`

Fallback decision rules:
- if a `3:1` bundle still shows repeated week-3 collapse risk without switching to a more conservative cadence or explicit risk handling, choose `replan_required`
- if a `2:1` bundle repeatedly deloads without need and still does not progress baseline logic, require explicit cadence reconsideration or choose `replan_required`
- if a `2:1:1` bundle shows poor readiness after W2/W3, the mini-reset must be allowed to become true deload and W4 must be treated as re-entry; otherwise choose `replan_required`
- if the first Build week after shortened/base/re-entry context jumps aggressively without explicit readiness gating, choose `replan_required`

Review classification rules:
- approve when the overload-policy semantics are explicit, coherent, and inherited cleanly by the bundle
- replan when overload-policy semantics are missing, contradictory, or hidden only in prose
- warn, but do not block solely, when the objective is mismatched to the highest A-event

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
