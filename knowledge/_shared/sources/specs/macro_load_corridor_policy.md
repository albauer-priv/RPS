---
Type: Specification
Specification-For: MACRO_LOAD_CORRIDOR_POLICY
Specification-ID: MacroLoadCorridorPolicy
Version: 1.0

Scope: Shared
Authority: Binding

Applies-To:
  - Macro-Planner

Dependencies:
  - Interface-ID: MacroOverviewInterface
    Version: 1.0
  - Interface-ID: SeasonBriefInterface
    Version: 1.0
  - Interface-ID: SeasonScenariosInterface
    Version: 1.0
  - Interface-ID: SeasonScenarioSelectionInterface
    Version: 1.0
  - Interface-ID: KpiProfileInterface
    Version: 1.0
  - Interface-ID: ActivitiesTrendInterface
    Version: 1.0
  - Interface-ID: AvailabilityInterface
    Version: 1.0
  - Interface-ID: WellnessInterface
    Version: 1.0

Notes: >
  Defines the binding procedure for deriving weekly kJ corridors
  in Macro Overview artefacts using body mass, availability, KPI guidance,
  and recent activity trends. This policy is macro-only and forbids
  weekly scheduling or workout prescription.
---

# macro_load_corridor_policy

This policy defines how the Macro-Planner computes **weekly kJ corridors**
for each macro phase. It is **macro-only** and must never produce weekly schedules,
workouts, or progression rules. All output must conform to
`macro_overview.schema.json`.

**Primary metric:** mechanical kJ (kJ-first).

If any required input is missing, the Macro-Planner MUST stop and request it.

---

## 1) Required inputs (source of truth)

1. **Season Brief** (`season_brief_*.md`)
   - Objectives, event windows, constraints, athlete context.
2. **Season Scenarios** (`season_scenarios_*.json`)
   - Scenario guidance (A/B/C), cadence, phase recommendations, risk profile.
3. **Season Scenario Selection** (`season_scenario_selection_*.json`)
   - The single selected scenario to instantiate.
4. **KPI Profile** (`kpi_profile_des_*.json`)
   - Guardrails, progression limits, moving-time rate guidance (kJ/kg/h).
5. **Activities Trend** (`activities_trend_*.json`)
   - Weekly aggregates for kJ, moving time, counts.
6. **Availability** (`availability_*.json`)
   - Weekly hours capacity, weekday table, fixed rest days, travel risk.
7. **Wellness** (`wellness_*.json`)
   - Body mass; used to set `body_metadata.body_mass_kg`.
8. **Principles** (`principles_durability_first_cycling.md`)
   - Durability-first and kJ-first logic.
9. **Macro Overview schema** (`macro_overview.schema.json`)
   - Required fields, forbidden content list.

Optional:
- `zone_model.json` (naming consistency for intensity domains only).

---

## 2) Body mass (binding)

### 2.1 Primary source
Use **WELLNESS** for body mass:
- `body_mass_kg` MUST come from `WELLNESS.body_mass_kg`.
- If missing, STOP and request Wellness data.

### 2.2 Robust reference
Compute a robust reference from recent values:
- Preferred: median of the last 14–28 days of measurements.
- Record the chosen method in `assumptions_unknowns`.

If insufficient data:
- Fall back to Season Brief body mass if present.
- Mark the limitation in `assumptions_unknowns`.

---

## 3) Availability → moving-time capacity (macro-only)

Use **AVAILABILITY** only to compute weekly moving-time capacity:

1. **Weekly hours total**
   - Sum available hours across weekdays (exclude fixed rest days).
2. **Low/High range**
   - Apply a conservative travel buffer to medium/high travel-risk days.
3. **Utilization factor**
   - Convert availability to feasible moving-time:
     `moving_time_capacity_hours = weekly_hours * utilization_factor`
   - Use a conservative factor (e.g., 0.75–0.90). Document it.

**Do NOT** build a weekly schedule. This step is only for capacity checking.

---

## 4) Baselines from Activities Trend

1. **Build eligible weeks table**
   - Use weekly aggregates: work_kj, moving_time, activity_count.
2. **Exclude partial weeks**
   - Exclude weeks with too few days, very low moving_time, or anomalous activity_count.
   - Document exclusions in `assumptions_unknowns`.
3. **Baseline**
   - Use the last 8–12 eligible weeks to compute typical kJ ranges.
4. **Ceiling indicator**
   - Identify a high but stable week (not a one-off outlier) as a ceiling indicator.

If activities_trend is missing or unusable:
- Use KPI guidance + availability only and flag uncertainty.

---

## 5) Phase corridors (kJ-first)

For each phase in `macro_overview.phases`:

### 5.1 Initial corridor
- **Base:** center around baseline range.
- **Build:** shift upward toward the ceiling indicator, respecting KPI guardrails.
- **Peak/Taper:** lower corridor for freshness and tapering intent.

### 5.2 Plausibility check (moving-time rate guidance)
Compute implied kJ/kg/h and compare to KPI guidance:

`implied_kJ_kg_hr = weekly_kJ / (body_mass_kg * moving_time_capacity_hours)`

If implied values are consistently above KPI guidance:
- Adjust corridors downward or mark infeasible under availability constraints.

If implied values are well below KPI guidance:
- Allowed, but note potential under-stimulus vs phase intent.

**Never** convert this into weekly prescriptions or progression rules.

---

## 6) Scenario-driven intensity semantics

Use the **selected scenario** to define:
- `allowed_intensity_domains`
- `forbidden_intensity_domains`
- `allowed_load_modalities`

Macro-level only. No session detail.

---

## 7) Global constraints & season envelope

Populate:
- `global_constraints.availability_assumptions`
  - use AVAILABILITY weekly hours and travel risk notes.
- `global_constraints.recovery_protection.fixed_rest_days`
  - must match AVAILABILITY; reconcile conflicts and explain in notes.
- `global_constraints.planned_event_windows`
  - from Season Brief.
- `season_load_envelope`
  - expected average weekly kJ range and high/low load weeks count,
    aligned to phase structure and deload cadence.

---

## 8) Guardrails, assumptions, and self-checks

1. **phase_transitions_guardrails**
   - qualitative triggers only (no numeric progression rules).
2. **assumptions_unknowns**
   - missing data, exclusions, availability utilization, mass data limits.
3. **principles_scientific_foundation**
   - map principle influence + cite sources.
4. **explicit_forbidden_content**
   - must include the schema-required list verbatim.
5. **self_check**
   - set booleans true only if fully compliant.

---

## 9) Prohibited content (hard)

Macro Overview MUST NOT include:
- weekly schedules
- day-by-day structure
- workouts or intervals
- numeric progression rules
- daily/session kJ targets

Any violation is a hard failure.
