---
name: load-governance-audit
description: Audit phase corridor realism, compression risk, and durability-first load governance.
metadata:
  author: rps
  version: "4.0"
---
Review the phase candidate for load-governance safety.

Definitions:
- `weekly_kj_bands`: exact-range governance-load bands, not raw mechanical work
- `phase_role`: deterministic exact-range phase role
- `week_role`: deterministic inherited cadence role for a week inside the range
- `deload`, `mini-reset`, `reload`, `re-entry`: overload-policy meanings that must remain visible in the exact-range bands and structure

Authority / injected sources:
- `weekly_kj_bands`, `phase_role`, `week_role`, and S5 traces come from deterministic phase execution context and approved guardrails
- this layer audits exact-range governance realism; it does not invent new overload targets

Checklist:
- corridor is feasible for the exact phase
- each `weekly_kj_bands` entry matches the injected deterministic S5 band and trace
- emitted week keys match `Deterministic Phase Execution Context.required_phase_weeks`
- overload progression is realistic
- compression patterns preserve safe week density
- cadence and deload logic align with the weekly bands
- phase role and week role both align with weekly bands
- Build load weeks are allowed to progress only within policy limits and availability feasibility
- Base load weeks remain conservative relative to Build, and Peak load weeks do not behave like Build ramps
- Deload, mini-reset, shortened re-entry, reload, and taper semantics are numerically visible unless S5 fallback trace explains the conflict
- fixed recovery and logistics constraints are not used as hidden load buckets
- governance-load semantics remain distinct from raw mechanical work semantics
- durability-first repeatability is preserved under the exact-range weekly bands

Block approval when:
- a weekly band differs from S5 without an explicit code-owned fallback trace
- a band is widened above availability capacity
- a week relies on load compression to recover from an infeasible season corridor
- deload intent contradicts the season-owned cadence
- week-role bands contradict inherited cadence roles
- phase role and week role disagree, e.g. Peak + LOAD_2 creates a Build-style ramp
- weekly bands are only explainable by hidden catch-up or recovery compression
- a threshold-shaped progression survives while `THRESHOLD` is suppressed upstream

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
