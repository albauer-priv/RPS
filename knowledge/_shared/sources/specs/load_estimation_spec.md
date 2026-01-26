---
Type: Specification
Specification-For: LOAD_ESTIMATION
Specification-ID: LoadEstimationSpec
Version: 1.0

Scope: Shared
Authority: Binding

Applies-To:
  - Macro-Planner
  - Meso-Architect
  - Micro-Planner
  - Workout-Builder

Dependencies:
  - Interface-ID: ZoneModelInterface
    Version: 1.0

Notes: >
  Defines binding rules and formulas for estimating training load.
  Energy anchor = planned_kJ; governance metric = planned_Load_kJ.
---

# load_estimation_spec (kJ-first)

This specification defines **how to estimate training load** for planning and governance in RPS.

**Key idea (normative):**
- **Energy anchor:** `planned_kJ` (mechanical work / fueling demand).
- **Governance metric:** `planned_Load_kJ` (stress‑weighted load used for constraints).

> **Terminology note (binding):** When templates or corridors say “Weekly kJ”, they mean
> **planned_Load_kJ_week** (stress‑weighted load used for governance).
> Mechanical `planned_kJ_week` remains the energy/fueling anchor.

This spec is **binding** for all planning agents.

---

## Schema Reference (Normative)

Field locations and structural definitions are defined in the relevant JSON
schemas (e.g., `workouts_plan.schema.json`, `block_governance.schema.json`).
This spec defines calculations and decision rules only. If there is any
structure mismatch, the schema prevails.

---

## General

This section defines the **general, binding** load estimation rules shared by all layers.

### G1) Glossary and invariants (binding)
- `planned_kJ`: mechanical work (unweighted). **Energy anchor.**
- `planned_IF`: session intensity factor (dimensionless). Derived from segments.
- `planned_Load_kJ`: stress‑weighted load metric for governance.
- `weekly_kj_bands`: **always** a corridor in `planned_Load_kJ_week`.

**Invariant:** IF is applied **exactly once** (only in `planned_Load_kJ`).

### G2) Minimum inputs (binding)
- `FTP_W` (from Zone Model)
- `ZoneModelVersion` (exact version string)
- Planned session structure as segments:
  - `t_i_sec` (seconds)
  - `r_i` (target factor vs FTP)
- optional domain/intent label (ENDURANCE_LOW / ENDURANCE_HIGH / TEMPO / SWEET_SPOT / VO2MAX / RECOVERY / etc.)

### G3) Segment interpretation rules (binding)
- **%FTP:** `r_i = pct/100`
- **range target:** `r_i = (low + high) / 2`
- **domain label only:** map to a default IF for that domain and treat as `r_i`
  (zone model typical IF preferred; fallback table otherwise)
  
Determinism rule:
- If the workout is **segment‑structured** and a segment lacks %FTP but has a
  domain label → map **per‑segment** `r_i` using defaults.
- If the workout has **no segment structure** and only an intent/domain →
  use **Fallback mode** (G5), not per‑segment mapping.

### G4) Core formulas (binding)
1) **Mechanical work**
   - `r_mean = Σ(t_i × r_i) / Σ(t_i)`
   - `planned_kJ = (FTP_W × r_mean × T_sec) / 1000`

2) **Session IF (NP‑like, p=4)**
   - `r_eq = ( Σ(t_i × r_i^p) / Σ(t_i) )^(1/p)` with `p = 4`
   - `planned_IF = clamp(r_eq, 0.0, 1.3)`

3) **Stress‑weighted load**
   - `planned_Load_kJ = planned_kJ × planned_IF^α`
   - `α = 1.3` (global from this spec)

### G5) Fallback mode (IF‑direct) — binding
Use only when segments are missing/unparseable or intent‑only.
- `planned_IF = IF_default(intent/domain)`
- `planned_kJ = (FTP_W × planned_IF × T_sec) / 1000`
- `planned_Load_kJ = planned_kJ × planned_IF^α`

### G6) Parsing, clamps, and edge cases (binding)
- `T_sec ≥ 0`. If `T_sec = 0`, then `planned_kJ = planned_Load_kJ = 0`.
- Clamp `r_i` to `[0.0, 1.5]` before applying `r_i^p`.
- Clamp `planned_IF_raw` to `[0.0, 1.3]` **before** computing `planned_Load_kJ`.
- If `workout_text` exists but **no valid segments** can be extracted, use
  **Fallback mode** based on workout intent; if intent missing, default to ENDURANCE_LOW.
- If `Σ(t_i) = 0` (all segment durations zero): set `planned_IF = 0`, `planned_kJ = 0`,
  `planned_Load_kJ = 0`.
- Mixed notation segments (some %FTP, some zone/label): map all segments; do not skip.

### G7) Unit conventions (binding)
- `t_i` and `T_sec` are **seconds**.
- FTP is **watts**.
- `planned_kJ = (W × seconds) / 1000`.
- `planned_minutes` is minutes; convert to seconds before load calculation.

### G8) Default IF values (binding fallback table)
Use Zone Model typical IF values when available. If absent, use:

| Domain / Intent | planned_IF default |
| --- | ---: |
| REST / OFF | 0.000 |
| RECOVERY | 0.55 |
| ENDURANCE_LOW | 0.65 |
| ENDURANCE_HIGH | 0.70 |
| TEMPO | 0.80 |
| SWEET_SPOT | 0.90 |
| THRESHOLD | 1.00 |
| VO2MAX | 1.10 |
| ANAEROBIC / SPRINT | 1.15 |

Canonical domain identifiers (binding):
- `RECOVERY`, `ENDURANCE_LOW`, `ENDURANCE_HIGH`, `TEMPO`, `SWEET_SPOT`, `THRESHOLD`,
  `VO2MAX`, `ANAEROBIC`, `REST`.
- Aliases (normalize on read): `VO2` → `VO2MAX`, `SWEET SPOT` → `SWEET_SPOT`,
  `OFF` → `REST`, `ENDURANCE+` → `ENDURANCE_HIGH`, `ENDURANCE` → `ENDURANCE_LOW`.

### G9) Rounding rules (output only, binding)
Compute using **unrounded** floats and round only at output:
- `planned_IF_out = round(planned_IF_raw, 3)`
- `planned_kJ_out = int(round(planned_kJ_raw))`
- `planned_Load_kJ_out = int(round(planned_kJ_raw * planned_IF_raw**α))`

Do NOT round `planned_IF` before computing `planned_Load_kJ`.
Store `planned_kJ_out` and `planned_Load_kJ_out` as 64‑bit integers (or safe int).

### G10) Traceability flags (binding)
When the target schema supports it, include:
- `FTP_W`
- `ZoneModelVersion`
- `LoadEstimationSpecVersion`
- `used_fallback_IF_direct` (bool)
- `segment_parse_status` (`OK` / `FAIL`)

If the schema has no explicit fields, record them in `meta.notes` or another
schema‑compliant trace field. Do not invent new fields.

### G11) α source of truth (binding)
`α` MUST come from LoadEstimationSpec (global default).
No overrides exist unless an explicit override artefact is introduced.

### G12) Micro‑Planner responsibilities (binding constraints)
- Produce 7‑day `WORKOUTS_PLAN` such that:
  - `sum(planned_Load_kJ_day)` is within `weekly_kj_bands[w]`.
  - Allowed domains are respected.
  - No new rules are invented; only allocate duration/intensity within constraints.
- Adjust primarily via **duration** for ENDURANCE_LOW/ENDURANCE_HIGH/RECOVERY; do not invent intensity.
- Restdays produce zero load fields.

Micro STOP conditions:
- Weekly band missing → STOP.
- Weekly band infeasible under availability → STOP and report.
- Attempt to schedule forbidden domains → STOP.

### G13) Determinism & audit checklist (binding)
- No stochastic choices; all defaults are deterministic.
- Every fallback usage MUST set `used_fallback_IF_direct = true`.
- Weekly band derivation SHOULD emit (or log) a debug bundle when schema allows:
  `macro_band`, `feasible_band`, `kpi_load_band`, `progression_band`, `final_band`.

### G14) Minimal test matrix (recommended)
1) All ENDURANCE_LOW segments, 2h, FTP known → IF=0.65, kJ, Load check.
2) Mixed intervals with ranges → midpoint rule.
3) Unparseable workout_text with intent TEMPO → IF‑direct.
4) Allowed domains exclude ENDURANCE_LOW/ENDURANCE_HIGH → IF_ref selection uses median/other rule.
5) Availability too low vs macro_min → infeasible_corridor STOP.
6) Progression guardrail conflict → progression_guardrail_conflict STOP.

---

## Macro spezifisch

This section defines how the Macro‑Planner derives **weekly planned_Load_kJ corridors**
for each macro phase.

### M1) Required inputs (binding)
1) Season Brief (objectives, events, constraints)
2) Season Scenarios + Scenario Selection
3) KPI Profile (guardrails, moving‑time rate guidance kJ/kg/h)
4) Activities Trend (weekly aggregates)
5) Availability (weekly hours, rest days, travel risk)
6) Wellness (body mass) **or** Season Brief body mass
7) Macro Overview schema

If any required input is missing, STOP and request it (except body mass, see M2).

### M2) Body mass (binding)
- Primary source: Wellness `body_mass_kg`.
- If missing, fall back to Season Brief body mass.
- Only STOP if **both** sources are missing.
- Use a robust reference (median of last 14–28 days) when available; document method.
- If using Season Brief fallback, set `macro_assumption_body_mass_source = SEASON_BRIEF`
  and emit a warning.

### M3) Availability → moving‑time capacity (macro‑only)
- Use availability only to compute weekly moving‑time capacity:
  - weekly hours total (exclude fixed rest days)
  - apply a deterministic utilization factor
- Do NOT build weekly schedules.

Utilization authority (binding):
- Use `KPI.utilization_macro_default` if present, else default to `0.95`.

### M4) Baselines from Activities Trend (binding)
- Build eligible weeks table (work_kj, moving_time, activity_count).
- Exclude partial/anomalous weeks using explicit criteria; document exclusions.
  Eligible week criteria (binding):
  - `moving_time_hours >= 0.7 * median(moving_time_hours of last 12 candidate weeks)`
  - `activity_count >= 2`
- Use the most recent **8 eligible** weeks (from last 12) to compute baseline kJ range.

### M5) Convert baseline to planned_Load_kJ (binding)
Macro corridors MUST be expressed as planned_Load_kJ:
- choose a phase‑level `phase_reference_IF` deterministically:
  1) `Scenario.phase_reference_IF[phase]` if present
  2) else by phase intent and allowed domains:
     - Base → ENDURANCE_HIGH (0.70)
     - Build → TEMPO (0.80) or SWEET_SPOT (0.90) depending on scenario intensity allowance
     - Peak → THRESHOLD (1.00) if allowed, else SWEET_SPOT (0.90)
     - Taper → ENDURANCE_LOW (0.65) or RECOVERY (0.55)
  3) clamp to `[0.0, 1.3]`
- compute `planned_Load_kJ = planned_kJ × IF^α` (α from this spec),
- document chosen IF in assumptions.

If activities_trend is missing or unusable:
- Use KPI guidance + availability only and flag uncertainty.

Macro MUST NOT narrow weekly bands by feasibility/availability intersection.
That narrowing is strictly Meso (see Meso section).

### M6) Phase corridors (binding)
- Base: center around baseline.
- Build: shift toward ceiling indicator, respecting KPI guardrails.
- Peak/Taper: lower corridor for freshness.

### M7) Plausibility check (moving‑time rate guidance)
Compute implied kJ/kg/h:
`implied_kJ_kg_hr = weekly_kJ / (body_mass_kg * moving_time_capacity_hours)`

If implied values consistently exceed KPI guidance:
- emit a feasibility warning; Meso will narrow via intersection.

Never turn this into weekly prescriptions.

### M8) Scenario‑driven semantics (binding)
Use selected scenario to set allowed/forbidden domains and modalities.
Macro level only; no session detail.

### M9) Global constraints & guardrails (binding)
Populate:
- `global_constraints.availability_assumptions` (weekly hours, travel risk)
- `global_constraints.recovery_protection.fixed_rest_days`
- `global_constraints.planned_event_windows` (Season Brief)
- season load envelope and phase guardrails

No numeric progression rules beyond KPI guardrails.

---

## Meso spezifisch

This section defines how Meso derives **weekly_kj_bands** (planned_Load_kJ/week)
by intersecting macro corridors with feasibility and KPI metabolic capacity.

### S1) Inputs (per ISO week)
1) Macro corridor (planned_Load_kJ/week)
2) Availability hours
3) FTP and IF defaults (Zone Model; fallback table from Section G8)
4) Allowed domains (scenario/governance)
5) KPI moving‑time rate band (kJ/kg/h)
5a) `kpi_rate_band_selector` (LOW | MID | HIGH)
6) α (this spec)
7) Progression guardrails (optional)
8) prev_planned_Load_kJ_week (optional)

### S2) KPI band interpretation (binding)
- KPI kJ/kg/h bands are **planned_kJ_per_kg_per_hour** (mechanical work rate).
- They are **not** planned_Load_kJ/h.
- Meso maps KPI mechanical kJ → Load via a single reference IF.

### S3) Feasible load band (physics, binding)
```
T_cap_sec = availability_hours_w * 3600
T_max = T_cap_sec * utilization_max (default 1.0)
T_min = T_cap_sec * utilization_min (default 0.0)

IF_max = min(max(IF(domain) for allowed_domains), 1.3)
IF_min = max(min(IF(domain) for allowed_domains), 0.0)

exponent = alpha + 1.0   # 2.3
feasible_max = (ftp_w * T_max / 1000) * (IF_max ** exponent)
feasible_min = (ftp_w * T_min / 1000) * (IF_min ** exponent)
```
Authority (binding): `utilization_min/max` MUST be read from KPI profile
if present; otherwise defaults `(0.0, 1.0)` apply. No overrides exist unless
KPI profile defines them.

### S4) KPI band (mechanical → load, binding)
```
moving_time_capacity_hours = availability_hours_w * utilization_max
kpi_kJ_min = band_min_kJkgph * body_mass_kg * moving_time_capacity_hours
kpi_kJ_max = band_max_kJkgph * body_mass_kg * moving_time_capacity_hours
```

Band selection (binding):
- `kpi_rate_band_selector` MUST come from Scenario or KPI profile if present.
- If absent, default to `MID`.

Reference IF for mapping (deterministic):
1) `expected_weekly_avg_IF` if provided,
2) else if ENDURANCE_LOW allowed → 0.65,
3) else if ENDURANCE_HIGH allowed → 0.70,
4) else median IF of allowed domains (excluding REST).

Clamp `IF_ref` to `[IF_min, IF_max]` and `[0.0, 1.3]`.

```
kpi_load_min = kpi_kJ_min * (IF_ref ** alpha)
kpi_load_max = kpi_kJ_max * (IF_ref ** alpha)
```

### S5) Final band (intersection, binding)
```
band_min = max(macro_min, feasible_min, kpi_load_min)
band_max = min(macro_max, feasible_max, kpi_load_max)
```

Apply progression guardrails if present:
```
band_max = min(band_max, prev_load * (1 + max_weekly_increase_pct))
band_min = max(band_min, prev_load * (1 - max_weekly_decrease_pct))
```

Round to integers at output.

If `prev_planned_Load_kJ_week` is missing or ≤ 0, skip progression guardrails
and emit a trace note (or debug bundle flag) indicating the skip.

### S6) Stop conditions (binding)
- missing_or_invalid_ftp
- missing_body_mass_for_kpi_rate
- no_allowed_domains
- availability_negative
- infeasible_corridor (band_min > band_max)
- progression_guardrail_conflict

---

## End of load_estimation_spec
