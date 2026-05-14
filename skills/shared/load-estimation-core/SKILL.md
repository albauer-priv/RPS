---
name: load-estimation-core
description: Shared load-estimation math and invariants for planning corridors and workout estimates.
metadata:
  author: rps
  version: "5.0"
---
Use one consistent load-estimation method across season, phase, week, and workout export contexts.

Core semantics:
- `planned_kj`: mechanical work estimate
- `planned_if`: session intensity factor
- `planned_load_kj`: governance load metric used for corridors and weekly bands
- all `weekly_kj_bands` and week-level corridors refer to `planned_load_kj`, not raw `planned_kj`

Required inputs:
- `ftp_watts` from the zone model
- zone-model or fallback domain IF values
- availability hours for corridor derivation
- athlete `endurance_anchor_w` when available
- KPI/body-mass inputs only when KPI gating is actually enabled

Per-workout algorithm:
1. Parse planned duration and segment targets deterministically.
2. For each segment, resolve `r_i` from `%FTP`, midpoint of a range, or deterministic domain default.
3. Compute `r_mean = sum(t_i * r_i) / sum(t_i)`.
4. Compute `r_eq = (sum(t_i * r_i^4) / sum(t_i))^(1/4)`.
5. Clamp segment factors to `[0.0, 1.5]` before the power term and clamp `planned_if_raw = clamp(r_eq, 0.0, 1.3)`.
6. Compute `planned_kj_raw = ftp_watts * r_mean * T_sec / 1000`.
7. Resolve `IF_ref_load` in order:
   - athlete `endurance_anchor_w / ftp_watts`, clamped to `[0.55, 0.80]`
   - zone-model endurance typical IF, clamped to `[0.55, 0.80]`
   - fallback constant `0.68`
8. Compute governance load with `alpha = 1.3`:
   - `planned_load_kj_raw = planned_kj_raw * (planned_if_raw / IF_ref_load)^1.3`
9. Round only at output:
   - `planned_if = round(planned_if_raw, 3)`
   - `planned_kj = round(planned_kj_raw)`
   - `planned_load_kj = round(planned_load_kj_raw)`

IF-direct fallback:
- use only when segment structure is missing or unparseable
- set `planned_if_raw = IF_default(domain)`
- then compute `planned_kj_raw` and `planned_load_kj_raw` with the same formulas

Default IF fallback table:
- `REST=0.00`
- `RECOVERY=0.55`
- `ENDURANCE_LOW=0.65`
- `ENDURANCE_HIGH=0.70`
- `TEMPO=0.80`
- `SWEET_SPOT=0.90`
- `THRESHOLD=1.00`
- `VO2MAX=1.10`
- `ANAEROBIC=1.15`

Trace and invariants:
- preserve `IF_ref_load` and its source
- preserve whether IF-direct fallback was used
- preserve segment-parse status when available
- IF is applied exactly once
- round only at final output

Hard rules:
- never apply IF twice
- never merge mechanical work and governance load semantics
- use segment math when available; IF-direct fallback only when structure is missing
- zero duration produces zero outputs
- negative durations or invalid totals are hard invalid states
