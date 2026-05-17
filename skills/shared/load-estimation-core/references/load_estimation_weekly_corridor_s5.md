# Weekly Corridor S5 Method

Use this reference when explaining code-owned weekly governance-load bands.

## Feasible Band

Inputs:
- `availability_hours_w`, normally `AVAILABILITY.data.weekly_hours.typical` unless a week-specific value exists
- `ftp_watts`
- `allowed_intensity_domains`
- `IF_ref_load`
- `utilization_min`, default `0.0`
- `utilization_max`, default `1.0`
- `alpha = 1.3`

Formulas:
- `T_cap_sec = availability_hours_w * 3600`
- `T_min = T_cap_sec * utilization_min`
- `T_max = T_cap_sec * utilization_max`
- `IF_min = max(min(IF_default(domain)), 0.0)`
- `IF_max = min(max(IF_default(domain)), 1.3)`
- `norm = IF_ref_load ** alpha`
- `exponent = alpha + 1.0`
- `feasible_min = (ftp_watts * T_min / 1000) * (IF_min ** exponent) / norm`
- `feasible_max = (ftp_watts * T_max / 1000) * (IF_max ** exponent) / norm`

## KPI Capacity Band

KPI moving-time-rate guidance is mechanical `kJ/kg/h`.

If KPI gating is active:
- `body_mass_kg` is required
- `moving_time_capacity_hours = availability_hours_w * utilization_max`
- `kpi_kJ_min = band_min_kJkgph * body_mass_kg * moving_time_capacity_hours`
- `kpi_kJ_max = band_max_kJkgph * body_mass_kg * moving_time_capacity_hours`
- `kpi_load_min = kpi_kJ_min * (IF_ref_week / IF_ref_load) ** alpha`
- `kpi_load_max = kpi_kJ_max * (IF_ref_week / IF_ref_load) ** alpha`

`IF_ref_week` selection order:
1. `phase_governance.expected_weekly_avg_IF` if present
2. `IF_ref_load`
3. median IF of allowed non-REST domains

## Progression Band

If `prev_planned_weekly_load_kj > 0`:
- `prog_min = prev * (1 - max_weekly_decrease_pct)`
- `prog_max = prev * (1 + max_weekly_increase_pct)`

Use explicit guardrail values when present; otherwise use the active progressive-overload defaults.

## S5 Final Band

Normal intersection:
- `base_min = max(season_min, feasible_min, kpi_load_min)`
- `base_max = min(season_max, feasible_max, kpi_load_max)`
- with progression: `band_min = max(base_min, prog_min)` and `band_max = min(base_max, prog_max)`
- without progression: use `base_min/base_max`

If `band_min <= band_max`, output `[int(round(band_min)), int(round(band_max))]` with `fallback_level = 0`.

Fallback ladder:
1. Drop progression overlay.
2. Escalate KPI selector `LOW -> MID -> HIGH` when available.
3. Apply KPI utilization override only when allowed.
4. Output a degenerate band at hard max.
5. Override season corridor infeasibility to the closest feasible point.

STOP conditions:
- missing/invalid FTP
- negative availability
- no allowed domains
- feasible band empty
- KPI enabled but `body_mass_kg` missing
- Level 5 cannot produce a valid band

Agents may explain these values and their trace, but must not recompute, widen, or override code-owned S5 bands.
