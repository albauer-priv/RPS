---
name: load-estimation-core
description: Shared load-estimation math and invariants for planning corridors and workout estimates.
metadata:
  author: rps
  version: "7.0"
---
Use one consistent load-estimation method across season, phase, week, and workout export contexts.

Core semantics:
- `planned_kj`: mechanical work estimate stored at workout/agenda level where supported
- `planned_if`: session intensity factor, derived from planned segments
- `planned_weekly_load_kj`: week-summary governance load metric used for constraints and corridor compliance
- `planned_load_kj_raw`: internal calculation term for governance load before weekly aggregation/output rounding
- all `weekly_kj_bands`, `weekly_load_corridor_kj`, and upstream `weekly_kJ` corridor names refer to `planned_weekly_load_kj`, not raw `planned_kj`
- use this skill for planning/governance corridors and workout load estimates; route nutrition, fueling, and recovery prescriptions to their responsible skills or evidence paths

kJ-first steering hierarchy:
- primary steering/comparison metric: kJ/load-kJ at session, week, phase, and season level
- secondary context metrics: CTL, ATL, TSB as tolerance/trend context only
- tertiary characterization metrics: IF and intensity distribution
- Keep kJ-first governance as the leading durability metric; use CTL/ATL/TSB only as supporting context.
- Use IF/intensity distribution to characterize work while preserving kJ-first load governance.
- fueling is not planned as an independent training prescription here; it is derived from energetic load outside this skill's authority

Required inputs:
- `ftp_watts` from `ZONE_MODEL.data.model_metadata`
- zone-model trace identifiers: `meta.schema_version` and `data.model_metadata.filename` when available
- zone-model or fallback domain IF values
- `availability.data.weekly_hours.min/typical/max` for corridor derivation
- athlete `endurance_anchor_w` when available
- athlete `ambition_if_range` only as QUALITY intent/policy envelope, never as a replacement for segment-derived IF
- selected KPI moving-time-rate guidance values only when scenario selection provides them
- KPI/body-mass inputs only when KPI gating is actually enabled

Per-workout algorithm:
1. Parse planned duration and segment targets deterministically.
2. For each segment, resolve `r_i` from `%FTP`, midpoint of a range, or deterministic domain default.
3. Compute `r_mean = sum(t_i * r_i) / sum(t_i)`.
4. Clamp each `r_i` to `[0.0, 1.5]` before the power term.
5. Compute `r_eq = (sum(t_i * r_i^4) / sum(t_i))^(1/4)`.
6. Clamp `planned_if_raw = clamp(r_eq, 0.0, 1.3)`.
7. Compute `planned_kj_raw = ftp_watts * r_mean * T_sec / 1000`.
8. Resolve `IF_ref_load` in order:
   - athlete `endurance_anchor_w / ftp_watts`, clamped to `[0.55, 0.80]`
   - zone-model endurance typical IF, clamped to `[0.55, 0.80]`
   - fallback constant `0.68`
9. Compute governance load with `alpha = 1.3`:
   - `planned_load_kj_raw = planned_kj_raw * (planned_if_raw / IF_ref_load)^1.3`
10. Round only at output:
   - `planned_if = round(planned_if_raw, 3)`
   - `planned_kj = int(round(planned_kj_raw))`
   - `planned_weekly_load_kj = int(round(planned_load_kj_raw))` at week-summary level

IF-direct fallback:
- use only when segment structure is missing, unparseable, or intent-only
- set `planned_if_raw = IF_default(domain)`
- then compute `planned_kj_raw` and `planned_load_kj_raw` with the same formulas

Default IF fallback table:
- `REST=0.00`
- `RECOVERY=0.55`
- `ENDURANCE=0.70`
- `TEMPO=0.80`
- `SWEET_SPOT=0.90`
- `THRESHOLD=1.00`
- `VO2MAX=1.10`
- `ANAEROBIC=1.15`

Trace and invariants:
- preserve zone-model `meta.schema_version` and `data.model_metadata.filename` when available
- preserve `IF_ref_load` and its source
- preserve whether IF-direct fallback was used
- preserve `segment_parse_status` as `OK` or `FAIL` when available
- IF is applied exactly once
- round only at final output

Hard rules:
- never apply IF twice
- never merge mechanical work and governance load semantics
- use segment math when available; IF-direct fallback only when structure is missing, unparseable, or intent-only
- zero duration produces zero outputs
- require non-negative durations and availability, valid FTP, at least one allowed domain, and valid totals for deterministic load derivation
- if KPI gating is enabled and `body_mass_kg` is missing, STOP with `missing_body_mass_for_kpi_rate`
