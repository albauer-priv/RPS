# Per-Workout Load Math

## Segment handling
- parse `t_i_sec` and target factor `r_i`
- percent targets become `pct/100`
- ranges use their midpoint
- domain-only targets use deterministic default IF values

## Core formulas
- `r_mean = sum(t_i * r_i) / sum(t_i)`
- `r_eq = (sum(t_i * r_i^4) / sum(t_i))^(1/4)`
- `planned_if_raw = clamp(r_eq, 0.0, 1.3)`
- `planned_kj_raw = ftp_watts * r_mean * T_sec / 1000`
- `planned_load_kj_raw = planned_kj_raw * (planned_if_raw / IF_ref_load)^1.3`

## Edge cases
- zero duration -> zero outputs
- invalid negative durations -> hard invalid
- use IF-direct fallback only when segment structure is unavailable
