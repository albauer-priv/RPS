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
- no compression pattern forces unsafe week density
- cadence and deload logic align with the weekly bands
- fixed recovery and logistics constraints are not used as hidden load buckets

Block approval when:
- a weekly band differs from S5 without an explicit code-owned fallback trace
- a band is widened above availability capacity
- a week relies on load compression to recover from an infeasible season corridor
- deload intent contradicts the season-owned cadence
