---
name: load-governance-audit
description: Audit phase corridor realism, compression risk, and durability-first load governance.
metadata:
  author: rps
  version: "3.0"
---
Review the phase candidate for load-governance safety.

Checklist:
- corridor is feasible for the exact phase
- each `weekly_kj_bands` entry matches the injected deterministic S5 band and trace
- emitted week keys match `Deterministic Phase Execution Context.required_phase_weeks`
- overload progression is realistic
- compression patterns preserve safe week density
- cadence and deload logic align with the weekly bands
- fixed recovery and logistics constraints are not used as hidden load buckets

Block approval when:
- a weekly band differs from S5 without an explicit code-owned fallback trace
- a band is widened above availability capacity
- a week relies on load compression to recover from an infeasible season corridor
- deload intent contradicts the season-owned cadence

Output format:
- Return the task expected_output as a structured review contribution.
- Include approved findings, blocking issues, warnings, and required adjustments in separate fields or clearly separated sections.
- Tie each issue to the relevant context, policy, phase/week range, load band, or artifact field.
