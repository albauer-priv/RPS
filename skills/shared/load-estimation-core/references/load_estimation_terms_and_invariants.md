# Load Estimation Terms and Invariants

## Terms
- `planned_kj`: mechanical work estimate, unweighted, in kJ
- `planned_if`: session intensity factor, dimensionless
- `planned_load_kj_raw`: internal unrounded governance-load calculation for one workout/session estimate
- `planned_weekly_load_kj`: week-summary governance load metric for constraints and corridor compliance
- `weekly_kj_bands[w]`: phase-level band for ISO week `w`, always in `planned_weekly_load_kj`
- `weekly_load_corridor_kj`: week-plan mirror of the active phase/S5 corridor
- upstream names such as `weekly_kJ` must be interpreted as governance load, not raw mechanical work

## Invariants
- `weekly_kj_bands`, `weekly_load_corridor_kj`, and `weekly_kJ` corridors refer to `planned_weekly_load_kj`, not raw mechanical work
- `IF_ref_load` is a normalization constant, not a second intensity factor
- intensity weighting is applied exactly once
- kJ/load-kJ is the primary steering metric for ultra/brevet planning
- CTL/ATL/TSB are secondary trend/tolerance context and must not lead durability decisions
- IF and intensity distribution are tertiary characterization metrics
- fueling semantics are derived from energetic load elsewhere; this load-estimation skill must not prescribe nutrition
- rounding happens only at output, never in intermediate math
- negative availability, negative durations, invalid FTP, missing allowed domains, and KPI gating without body mass are invalid deterministic states
