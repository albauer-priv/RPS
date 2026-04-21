---
Type: Specification
Specification-For: LOAD_ESTIMATION
Specification-ID: LoadEstimationSpec
Version: 2.0

Scope: Shared
Authority: Binding

Applies-To:
  - Season-Planner
  - Phase-Architect
  - Week-Planner
  - Workout Export

Dependencies:
  - Interface-ID: ZoneModelInterface
    Version: 1.0
  - Interface-ID: SeasonBriefInterface
    Version: 1.0
  - Interface-ID: AvailabilityInterface
    Version: 1.0
  - Interface-ID: WellnessInterface
    Version: 1.0
  - Interface-ID: KPIProfileInterface
    Version: 1.0

Notes: >
  Binding rules and formulas for estimating planning load corridors.
  This spec is strictly about planning and governance corridors (kJ bands) for execution.
  It intentionally excludes nutrition/fueling/recovery semantics.
---

# LoadEstimationSpec (Planning Corridors Only)

This specification defines the **single source of truth** for estimating training load metrics used to:

* compute per-workout load estimates,
* derive weekly governance corridors (`weekly_kj_bands`), and
* ensure consistency across Season/Phase/Week planning layers.

This spec is **strictly about planning load corridors**. It must not be used to infer nutrition, fueling, or recovery needs.

---

## 1) Terminology and Governance Semantics (Binding)

### 1.1 Metrics

* `planned_kj` — **mechanical work estimate** (unweighted). Unit: kJ. (Stored in Week Plan agenda/workouts.)
* `planned_if` — **session intensity factor** (dimensionless), derived from planned segments (computed; stored only when schema supports it).
* `planned_weekly_load_kj` — **governance load metric** for constraints. Unit: “load-kJ” (numerically in kJ units). (Stored in Week Plan `week_summary`.)

### 1.2 Corridors

* `weekly_kj_bands[w]` (Phase Guardrails/Structure) ALWAYS refers to **planned_weekly_load_kj** for ISO week `w`.
* Week Plan uses `weekly_load_corridor_kj` to mirror the phase corridor for that week.
* Any corridor or band named “weekly_kJ” in upstream artefacts MUST be treated as `planned_weekly_load_kj`.

### 1.3 Invariants

* **IF is applied exactly once** in the governance metric.
* `IF_ref_load` is a fixed **normalization constant** (athlete-aware), not a second intensity factor.

---

## 2) Required Inputs (Binding)

### 2.1 Zone Model (required)

* `data.model_metadata.ftp_watts` (watts)
* `meta.schema_version` + `data.model_metadata.filename` (version identifiers)
* Zone/domain typical IF values when available (`data.zones[].typical_if`)

### 2.2 Athlete Profile (optional but preferred)

* `endurance_anchor_w` (watts) — athlete sustainable endurance anchor (if present in Athlete Profile input)
* `ambition_if_range = [low, high]` — QUALITY intent envelope (policy input only, if present)
* If Athlete Profile fields are missing in the artefact, these values MUST be passed as **User Provided Data** in Phase-Architect and Week-Planner prompts when present.

### 2.3 Availability (required for weekly bands)

* `availability.data.weekly_hours.{min,typical,max}` (non-negative)

### 2.4 Wellness (optional)

* `body_mass_kg` (required only if KPI kJ/kg/h gating is enabled)

### 2.5 KPI Profile (optional)

* `durability.moving_time_rate_guidance.bands` (kJ/kg/h mechanical guidance)
  * Use `kj_per_kg_per_hour.min/max` for band bounds.
* `kpi_rate_band_selector` is the **selected segment** from Scenario Selection:
  * `kpi_rate_band_selector = "<segment>"`
  * Source: `season_scenario_selection.kpi_moving_time_rate_guidance_selection.segment`
  * Selected values (`w_per_kg`, `kj_per_kg_per_hour`) MUST be injected as **User Provided Data** when present.
* Optional KPI gating configuration (future schemas):
  * `kpi_mapping_utilization_override_allowed` (bool)
* Optional utilization/progression guardrails:
  * If present in schemas, use them.
  * Otherwise use defaults, and read progression limits from `progressive_overload_policy`:
    * `max_weekly_increase_pct`, `max_weekly_decrease_pct`.

---

## 3) Per-Workout Load Estimation (Binding)

### 3.1 Segment interpretation (Binding)

Planned workouts are represented as segments with:

* `t_i_sec` (seconds)
* `r_i` (target factor vs FTP)

Interpretation rules:

* **%FTP:** `r_i = pct/100`
* **range:** `r_i = (low + high) / 2` (midpoint)
* **domain label only (per segment):** map to a default IF for that domain (Zone Model typical IF preferred; fallback table otherwise)

Determinism:

* If segment structure exists, missing %FTP uses per-segment domain defaults.
* If no segments can be parsed, use **IF-direct fallback** (3.5).

### 3.2 Core intensity math (Binding)

Let `T_sec = Σ(t_i_sec)`.

* `r_mean = Σ(t_i × r_i) / Σ(t_i)`
* `r_eq = ( Σ(t_i × r_i^p) / Σ(t_i) )^(1/p)` with `p = 4`

Clamps:

* `r_i` MUST be clamped to `[0.0, 1.5]` before applying `r_i^p`.
* `planned_if_raw = clamp(r_eq, 0.0, 1.3)`

### 3.3 Mechanical work (Binding)

* `planned_kj_raw = (ftp_watts × r_mean × T_sec) / 1000`

### 3.4 Athlete-aware normalization (Binding): resolve `IF_ref_load`

`IF_ref_load` MUST be resolved deterministically:

1. **Athlete Profile anchor** (preferred):

* If `endurance_anchor_w` is present and `ftp_watts > 0`:

  * `IF_anchor = endurance_anchor_w / ftp_watts`
  * `IF_ref_load = clamp(IF_anchor, 0.55, 0.80)`
  * `IF_ref_load_source = ATHLETE_PROFILE_ANCHOR`

2. **Zone Model endurance typical** (fallback):

* Prefer Z2 typical IF (or ENDURANCE_LOW typical IF if exposed)

  * `IF_ref_load = clamp(IF_z2_typical, 0.55, 0.80)`
  * `IF_ref_load_source = ZONEMODEL_ENDURANCE_TYPICAL`

3. **Constant fallback** (last resort):

* `IF_ref_load = 0.68`
* `IF_ref_load_source = FALLBACK_CONST`

### 3.5 Governance load (Binding)

Global constant:

* `α = 1.3`

Definition:

* `planned_load_kj_raw = planned_kj_raw × (planned_if_raw / IF_ref_load)^α`

### 3.6 IF-direct fallback (Binding)

Use only if segments are missing/unparseable or intent-only.

* `planned_if_raw = IF_default(domain)`
* `planned_kj_raw = (ftp_watts × planned_if_raw × T_sec) / 1000`
* `planned_load_kj_raw = planned_kj_raw × (planned_if_raw / IF_ref_load)^α`

### 3.7 Output rounding (Binding)

Round at output only:

* `planned_if = round(planned_if_raw, 3)`
* `planned_kj = int(round(planned_kj_raw))`
* `planned_weekly_load_kj = int(round(planned_load_kj_raw))` (week summary field)

No rounding of IF before computing load.

### 3.8 Edge cases (Binding)

* If `T_sec = 0` → all outputs 0.
* If `Σ(t_i) = 0` → all outputs 0.
* Negative durations or availability are invalid.

### 3.9 Default IF table (Binding fallback)

Use Zone Model typical IFs when available. If absent:

| Domain / Intent | IF_default |
| --------------- | ---------: |
| REST / OFF      |      0.000 |
| RECOVERY        |       0.55 |
| ENDURANCE_LOW   |       0.65 |
| ENDURANCE_HIGH  |       0.70 |
| TEMPO           |       0.80 |
| SWEET_SPOT      |       0.90 |
| THRESHOLD       |       1.00 |
| VO2MAX          |       1.10 |
| ANAEROBIC       |       1.15 |

Canonical identifiers (binding):

* `RECOVERY`, `ENDURANCE_LOW`, `ENDURANCE_HIGH`, `TEMPO`, `SWEET_SPOT`, `THRESHOLD`, `VO2MAX`, `ANAEROBIC`, `REST`.

### 3.10 Trace flags (Binding)

When schemas support it, emit:

* `meta.schema_version`, `data.model_metadata.filename` (Zone Model identifiers)
* `IF_ref_load`, `IF_ref_load_source`
* `used_fallback_IF_direct` (bool)
* `segment_parse_status` (OK|FAIL)

---

## 4) Weekly Corridor Derivation (Phase-Architect) (Binding)

Phase-Architect MUST output `weekly_kj_bands[w]` in planned_weekly_load_kj/week.

### 4.1 Inputs (per ISO week w)

* `season_plan.phases[].weekly_load_corridor.weekly_kj` (Season-Planner corridor, kJ/kg/h bands)
* `availability.data.weekly_hours.{min,typical,max}`
* `data.model_metadata.ftp_watts` (from Zone Model)
* `phase_guardrails.allowed_forbidden_semantics.allowed_intensity_domains`
* KPI gating inputs (optional; from KPI profile moving_time_rate_guidance)
* optional `prev_planned_weekly_load_kj` (from previous Week Plan summary)

### 4.2 Feasible band from availability (Binding)

Definitions:

* `T_cap_sec = availability_hours_w * 3600` where `availability_hours_w` defaults to `weekly_hours.typical`
* `utilization_max` and `utilization_min` default to `(1.0, 0.0)` (not in current schemas)
* `T_max = T_cap_sec * utilization_max`
* `T_min = T_cap_sec * utilization_min`
* `IF_max = min(max(IF_default(domain) for domain in allowed_intensity_domains), 1.3)`
* `IF_min = max(min(IF_default(domain) for domain in allowed_intensity_domains), 0.0)`
* `exponent = α + 1.0`  # 2.3
* `norm = IF_ref_load ** α`

Feasible bounds:

```
feasible_max = (ftp_w * T_max / 1000) * (IF_max ** exponent) / norm
feasible_min = (ftp_w * T_min / 1000) * (IF_min ** exponent) / norm
```

### 4.3 KPI capacity band (optional, Binding if enabled)

KPI guidance bands are **mechanical** kJ/kg/h.

Mechanical KPI band:

```
moving_time_capacity_hours = availability_hours_w * utilization_max
kpi_kJ_min = band_min_kJkgph * body_mass_kg * moving_time_capacity_hours
kpi_kJ_max = band_max_kJkgph * body_mass_kg * moving_time_capacity_hours
```

Map to governance load:

* Select `IF_ref_week` deterministically:

  1. `phase_governance.expected_weekly_avg_IF` if present
  2. else `IF_ref_week = IF_ref_load`
  3. else median IF of allowed domains (excluding REST)

```
kpi_load_min = kpi_kJ_min * (IF_ref_week / IF_ref_load) ** α
kpi_load_max = kpi_kJ_max * (IF_ref_week / IF_ref_load) ** α
```

If KPI gating is enabled, `body_mass_kg` is required; else STOP with `missing_body_mass_for_kpi_rate`.

### 4.4 Progression band (optional)

If `prev_planned_weekly_load_kj > 0` and guardrails exist:

```
prog_min = prev * (1 - max_weekly_decrease_pct)
prog_max = prev * (1 + max_weekly_increase_pct)
```

### 4.5 Final band derivation (S5) (Binding)

Phase-Architect MUST apply the S5 ladder below.

#### S5.1 Normal intersection

```
base_min = max(season_min, feasible_min, kpi_load_min)
base_max = min(season_max, feasible_max, kpi_load_max)
```

If KPI gating is disabled, treat `kpi_load_min = 0` and `kpi_load_max = +INF`.

Apply progression overlay if eligible:

```
band_min = max(base_min, prog_min)
band_max = min(base_max, prog_max)
```

If not eligible, `band_min/base_min`, `band_max/base_max`.

If `band_min <= band_max` → output and `fallback_level=0`.

#### S5.2 Fallback ladder (deterministic)

If `band_min > band_max`, apply in order:

Level 1 — Drop progression overlay:

* Retry using `base_min/base_max`.

Level 2 — KPI rate band escalation (if enabled):

* Escalate selector LOW→MID→HIGH (or MID→HIGH), recompute KPI band and retry (with one retry without progression).

Level 3 — KPI utilization override (only if KPI profile allows):

* Recompute KPI mapping with utilization=1.0 for KPI mapping only.

Level 4 — Degenerate band at hard max:

* `hard_band = intersect(feasible_band, kpi_load_band_current)` if KPI enabled, else feasible_band.
* Output `[hard_band.max, hard_band.max]`.

Level 5 — Season corridor infeasible override:

* If season band has empty intersection with feasible band, output degenerate band at closest feasible point.

#### S5.3 STOP conditions

Phase-Architect MUST STOP if:

* missing/invalid FTP
* negative availability
* no allowed domains
* feasible band empty
* KPI enabled but missing body mass
* after Level 5 override, override band empty

#### S5.4 Output rounding and trace

* `weekly_kj_bands[w] = [int(round(band_min)), int(round(band_max))]`
* Emit trace: `fallback_level`, `fallback_reason`, `kpi_rate_band_selector_used` (if applicable).

---

## 5) Planner Responsibilities (Binding)

### 5.1 Season-Planner

* Produces season-level weekly corridors expressed in **planned_weekly_load_kj/week** via `season_plan.phases[].weekly_load_corridor.weekly_kj`.
* Must not schedule workouts.
* Must not narrow corridors by feasibility; feasibility is Phase-Architect.

May use `ambition_if_range` as intent to shape phase semantics (QUALITY emphasis), but must not override segment-derived IF.

### 5.2 Phase-Architect

* Produces per-week `weekly_kj_bands[w]` in **planned_weekly_load_kj/week**.
* Must apply feasibility from availability and allowed domains.
* Must apply KPI gating only if enabled.
* Must apply S5 fallback ladder deterministically.

### 5.3 Week-Planner

* Produces a 7-day plan whose `week_summary.planned_weekly_load_kj` lies within `weekly_kj_bands[w]`.
* Must respect allowed domains and modalities.
* Adjustment hierarchy:

  * primarily via duration within ENDURANCE/RECOVERY domains;
  * QUALITY allocation must remain within allowed domains.

STOP conditions:

* weekly_kj_bands missing
* infeasible under availability
* forbidden domains requested

---

## End of LoadEstimationSpec v2.0
