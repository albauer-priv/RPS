# Mandatory Output Chapter

Purpose
This chapter defines how to produce **schema‑valid SEASON_PLAN JSON**. It is the
single source of truth for filling the mandatory output fields, including the
required schema, field sources, and a minimal valid example.

---

## ARTIFACT: SEASON_PLAN

### WHICH SCHEMA TO USE AND HOW TO FIND
- Schema: `season_plan.schema.json`
  - Filter: `{"type":"eq","key":"schema_id","value":"season_plan.schema.json"}`
- You MUST validate output against this schema before calling `store_season_plan`.

### HOW TO FILL (BINDING)

#### 1) Envelope (top‑level)
- Output MUST be a **top‑level object** with only:
  - `meta`
  - `data`
- Call `store_season_plan` with this envelope only. No wrappers, no extra keys.

#### 2) `meta` (required fields)
- `artifact_type`: `"SEASON_PLAN"`
- `schema_id`: `"SeasonPlanInterface"`
- `schema_version`: `"1.0"`
- `version`: `"1.0"`
- `authority`: `"Binding"`
- `owner_agent`: `"Season-Planner"`
- `run_id`: provided by runner
- `created_at`: ISO‑8601 timestamp (UTC)
- `scope`: `"Season"`
- `iso_week`: ISO week string `YYYY-WW` (use first week of `iso_week_range`)
- `iso_week_range`: `YYYY-WW--YYYY-WW` (string, inclusive)
- `temporal_scope`: `{ "from": "YYYY-MM-DD", "to": "YYYY-MM-DD" }`
  - Must align to `iso_week_range` (no month inference).
- `trace_upstream`: list of upstream artefacts (ATHLETE_PROFILE, PLANNING_EVENTS, LOGISTICS, KPI_PROFILE, SEASON_SCENARIOS or SEASON_SCENARIO_SELECTION, AVAILABILITY, WELLNESS, ACTIVITIES_TREND when used).
- `trace_data`, `trace_events`: include inputs (planning_events must be in `trace_events`, logistics in `trace_data`).
- `notes`: non‑empty string.

#### 3) `data.body_metadata`
Required:
- `planning_horizon_weeks` (integer, **8–32**)
- `season_brief_ref` (legacy field; populate with Athlete Profile run_id or version key)
- `kpi_profile_ref` (KPI_PROFILE id)
- `moving_time_rate_guidance`:
  - `segment` (string label used, e.g., `"fast_competitive"`)
  - `w_per_kg` `{ "min": number, "max": number }`
  - `kj_per_kg_per_hour` `{ "min": number, "max": number }`
  - `notes` (string)
- `athlete_profile_ref` (Athlete Profile run_id or profile id)
- `body_mass_kg` (number, from WELLNESS or Athlete Profile fallback)
Notes:
- If the caller specifies a moving_time_rate_band, `moving_time_rate_guidance.segment` MUST match it.

#### 4) `data.season_intent_principles`
Required:
- `season_objective` (string)
- `success_definition` (string enum: `event-focused` | `durability-focused` | `mixed`)
- `non_negotiable_principles` (array, min 1)
- `kJ_corridor_design_notes` (array, min 1)

#### 5) `data.phases` (array, min 1)
Each phase MUST include:
- `phase_id` (string)
- `name` (string)
- `date_range` `{ "from": "YYYY-MM-DD", "to": "YYYY-MM-DD" }`
- `iso_week_range` `YYYY-WW--YYYY-WW`
- `cycle` one of: `Base | Build | Peak | Transition`
- `deload` (boolean)
- `deload_rationale` (string; may be empty if deload=false)
- `narrative` (string)
- `overview` (object, required keys):
  - `core_focus_and_characteristics` (array, min 1)
  - `phase_goals` (object with `primary` (string, required) and `secondary` (string, optional))
  - `metabolic_focus` (string)
  - `expected_adaptations` (array, min 1)
  - `evaluation_focus` (array, min 1)
  - `phase_exit_assumptions` (array, min 1)
  - `typical_duration_intensity_pattern` (string)
  - `non_negotiables` (array, min 1)
- `weekly_load_corridor`:
  - `weekly_kj` object with:
    - `min` (number)
    - `max` (number)
    - `kj_per_kg_min` (number)
    - `kj_per_kg_max` (number)
    - `notes` (string)
- `allowed_forbidden_semantics`:
  - `allowed_intensity_domains` (array, min 1)
  - `allowed_load_modalities` (array; use `NONE` and optional `K3`)
  - `forbidden_intensity_domains` (array; may be empty)
- `structural_emphasis`:
  - `typical_focus` (string)
  - `not_emphasized` (string)
- `events_constraints`:
  - array of objects `{ "window": "YYYY-MM-DD", "type": "A|B|C", "constraint": "string" }`
  - Use `[]` if none apply.

**Rules**
- `weekly_load_corridor.weekly_kj` is required and must be fully populated.
- `deload` and `deload_rationale` MUST be derived from `progressive_overload_policy.md`
  and the selected cadence (`deload_cadence` / `phase_length_weeks`); do not invent
  alternate cadence logic.
- No extra keys at phase level.
- Events: every Planning Events A/B/C event must appear in exactly one phase’s `events_constraints`.

#### 6) `data.global_constraints`
Required:
- `availability_assumptions` (array, min 1)
- `risk_constraints` (array, min 1)
- `planned_event_windows` (array; may be empty)
- `recovery_protection`:
  - `fixed_rest_days` (array; e.g., `["Mon","Fri"]`)
  - `notes` (string)

#### 7) `data.season_load_envelope`
Required:
- `expected_average_weekly_kj_range` `{ "min": number, "max": number }`
- `expected_high_load_weeks_count` (int)
- `expected_deload_or_low_load_weeks_count` (int)

#### 8) `data.assumptions_unknowns`
Required:
- `assumptions` (array, min 1)
- `uncertainties` (array, min 1)
- `revisit_items` (array, min 1)

#### 9) `data.phase_transitions_guardrails`
Required:
- `expected_progression` (string)
- `conservative_triggers` (array, min 1)
- `absolute_no_go_rules` (array, min 1)

#### 10) `data.justification`
Required:
- `summary` (string)
- `citations` (array, min 1) — **each item must be an object**:
  - `{ "source_type": "principles|evidence|policy|spec|contract", "source_id": "string", "section": "string", "rationale": "string" }`
- `phase_justifications` (array, min 1)
  - Each item must include:
    - `phase_id`
    - `intensity_distribution`
    - `overload_pattern`
    - `kJ_first_statement`
    - `citations` (array, min 1, **strings only**)

#### 11) `data.principles_scientific_foundation`
Required:
- `principle_applications` (array, min 1)
  - Each item: `{ "principle": "string", "influence": "string" }`
- `scientific_foundation`:
  - `publications` (array, min 1) each with:
    - `authors` (string)
    - `year` (int)
    - `title` (string)
    - `link` (string, **non‑empty**; may be an internal reference)
  - `plan_alignment_check` (string)
  - `rationale` (string)

#### 12) `data.explicit_forbidden_content`
Must contain **exactly 6** items (from schema enum):
1. `phase definitions (phase plans)`
2. `weekly schedules`
3. `day-by-day structure`
4. `workouts or interval prescriptions`
5. `numeric progression rules`
6. `daily or session-level kJ targets`

#### 13) `data.self_check`
All required booleans must be present. Set to `true` only if valid:
- `planning_horizon_is_at_least_8_weeks`
- `every_phase_defines_weekly_kj_corridor`
- `every_phase_includes_kj_per_kg_guardrails_and_reference_mass`
- `every_phase_maps_to_cycle_and_deload_intent`
- `every_phase_includes_narrative_and_metabolic_focus`
- `every_phase_includes_evaluation_focus_and_exit_assumptions`
- `season_load_envelope_and_assumptions_documented`
- `principles_and_scientific_foundation_documented`
- `allowed_forbidden_domains_listed`
- `no_phase_or_week_planning_content`
- `header_includes_implements_iso_week_range_trace`

#### 14) Validation & Stop (Binding)
- Use the store tool with a top-level `{ "meta": ..., "data": ... }` envelope only.
- Do NOT output raw JSON in chat; only the store tool call is allowed.
- Before output: confirm the Mandatory Output Chapter was read in full and followed exactly.
- Validate against `season_plan.schema.json` before calling the store tool.
- If validation fails or any required field is missing/unknown: STOP.
- Do not use empty strings for required string fields (including citations). If required info is missing: STOP.
- You MUST run schema validation locally (in reasoning) before calling `store_season_plan`.
- If any field fails type/enum/shape requirements, **STOP** and report the schema errors. Do not guess or retry with a different shape.
- Only call `store_season_plan` when all required fields match the schema.

---

### EXAMPLE: SEASON_PLAN (minimal valid)

```json
{
  "meta": {
    "artifact_type": "SEASON_PLAN",
    "schema_id": "SeasonPlanInterface",
    "schema_version": "1.0",
    "version": "1.0",
    "authority": "Binding",
    "owner_agent": "Season-Planner",
    "run_id": "example_season_plan_2026_w04",
    "created_at": "2026-01-26T00:00:00Z",
    "scope": "Season",
    "iso_week": "2026-04",
    "iso_week_range": "2026-04--2026-11",
    "temporal_scope": { "from": "2026-01-19", "to": "2026-03-15" },
    "trace_upstream": [
      { "artifact": "athlete_profile", "version": "1.0", "run_id": "athlete_profile_2026" },
      { "artifact": "logistics", "version": "1.0", "run_id": "logistics_2026" },
      { "artifact": "planning_events", "version": "1.0", "run_id": "planning_events_2026" },
      { "artifact": "KPI_PROFILE", "version": "1.0", "run_id": "KPI_Profile_Example" },
      { "artifact": "AVAILABILITY", "version": "1.0", "run_id": "availability_2026-04" }
    ],
    "trace_data": [],
    "trace_events": [],
    "notes": "Example only. Replace with real trace references."
  },
  "data": {
    "body_metadata": {
      "planning_horizon_weeks": 8,
      "season_brief_ref": "athlete_profile_2026",
      "kpi_profile_ref": "KPI_Profile_Example",
      "moving_time_rate_guidance": {
        "segment": "fast_competitive",
        "w_per_kg": { "min": 2.2, "max": 3.2 },
        "kj_per_kg_per_hour": { "min": 7.9, "max": 10.1 },
        "notes": "Example guidance band."
      },
      "athlete_profile_ref": "athlete_profile_2026",
      "body_mass_kg": 90.0
    },
    "season_intent_principles": {
      "season_objective": "Build durable endurance for A‑event.",
      "success_definition": "event-focused",
      "non_negotiable_principles": ["Protect recovery anchors."],
      "kJ_corridor_design_notes": ["Use moving_time_rate_guidance as corridor anchor."]
    },
    "phases": [
      {
        "phase_id": "P01",
        "name": "Base 1",
        "date_range": { "from": "2026-01-19", "to": "2026-02-15" },
        "iso_week_range": "2026-04--2026-07",
        "cycle": "Base",
        "deload": true,
        "deload_rationale": "3:1 cadence within a 4-week base phase.",
        "narrative": "Foundational aerobic base with conservative overload.",
        "overview": {
          "core_focus_and_characteristics": ["Steady endurance volume and consistency."],
          "phase_goals": { "primary": "Build weekly durability tolerance.", "secondary": "" },
          "metabolic_focus": "Aerobic efficiency",
          "expected_adaptations": ["Improved steady-state endurance."],
          "evaluation_focus": ["Completion of long steady rides."],
          "phase_exit_assumptions": ["Stable recovery and adherence."],
          "typical_duration_intensity_pattern": "Mostly ENDURANCE_LOW with brief TEMPO.",
          "non_negotiables": ["Fixed rest days preserved."]
        },
        "weekly_load_corridor": {
          "weekly_kj": {
            "min": 7000,
            "max": 8500,
            "kj_per_kg_min": 7.8,
            "kj_per_kg_max": 9.5,
            "notes": "Example corridor."
          }
        },
        "allowed_forbidden_semantics": {
          "allowed_intensity_domains": ["ENDURANCE_LOW", "TEMPO"],
          "allowed_load_modalities": ["NONE"],
          "forbidden_intensity_domains": ["VO2MAX", "THRESHOLD"]
        },
        "structural_emphasis": {
          "typical_focus": "Endurance volume",
          "not_emphasized": "High-intensity density"
        },
        "events_constraints": []
      },
      {
        "phase_id": "P02",
        "name": "Base 2",
        "date_range": { "from": "2026-02-16", "to": "2026-03-15" },
        "iso_week_range": "2026-08--2026-11",
        "cycle": "Build",
        "deload": true,
        "deload_rationale": "3:1 cadence within a 4-week build phase.",
        "narrative": "Continued endurance progression with conservative specificity.",
        "overview": {
          "core_focus_and_characteristics": ["Progressive endurance with controlled tempo."],
          "phase_goals": { "primary": "Increase long-ride tolerance.", "secondary": "" },
          "metabolic_focus": "Aerobic economy",
          "expected_adaptations": ["Improved fatigue resistance."],
          "evaluation_focus": ["Stable long-ride completion."],
          "phase_exit_assumptions": ["No excessive fatigue accumulation."],
          "typical_duration_intensity_pattern": "Endurance-dominant with modest TEMPO.",
          "non_negotiables": ["Fixed rest days preserved."]
        },
        "weekly_load_corridor": {
          "weekly_kj": {
            "min": 7400,
            "max": 8800,
            "kj_per_kg_min": 8.2,
            "kj_per_kg_max": 9.8,
            "notes": "Example corridor."
          }
        },
        "allowed_forbidden_semantics": {
          "allowed_intensity_domains": ["ENDURANCE_LOW", "TEMPO"],
          "allowed_load_modalities": ["NONE"],
          "forbidden_intensity_domains": ["VO2MAX", "THRESHOLD"]
        },
        "structural_emphasis": {
          "typical_focus": "Endurance volume, Tempo support",
          "not_emphasized": "High-intensity density"
        },
        "events_constraints": []
      }
    ],
    "global_constraints": {
      "availability_assumptions": ["Typical weekly hours 8–10."],
      "risk_constraints": ["Masters recovery sensitivity."],
      "planned_event_windows": [],
      "recovery_protection": {
        "fixed_rest_days": ["Mon", "Fri"],
        "notes": "Fixed rest days are non‑negotiable."
      }
    },
    "season_load_envelope": {
      "expected_average_weekly_kj_range": { "min": 7000, "max": 8500 },
      "expected_high_load_weeks_count": 6,
      "expected_deload_or_low_load_weeks_count": 2
    },
    "assumptions_unknowns": {
      "assumptions": ["Stable availability."],
      "uncertainties": ["Exact travel weeks."],
      "revisit_items": ["Update after events schedule confirmed."]
    },
    "phase_transitions_guardrails": {
      "expected_progression": "Hold or progress if KPIs are stable.",
      "conservative_triggers": ["Illness", "excess fatigue"],
      "absolute_no_go_rules": ["Missed recovery weeks"]
    },
    "justification": {
      "summary": "Durability‑first season structure aligned to constraints.",
      "citations": [
        {
          "source_type": "principles",
          "source_id": "principles_durability_first_cycling.md",
          "section": "3.2",
          "rationale": "Backplanning and cadence guidance for season structure."
        }
      ],
      "phase_justifications": [
        {
          "phase_id": "P01",
          "intensity_distribution": "Endurance‑dominant with minimal tempo.",
          "overload_pattern": "Conservative linear progression.",
          "kJ_first_statement": "Weekly load corridors set before intensity details.",
          "citations": ["load_estimation_spec.md#Season"]
        }
      ]
    },
    "principles_scientific_foundation": {
      "principle_applications": [
        { "principle": "Durability‑first", "influence": "Base emphasizes endurance volume." }
      ],
      "scientific_foundation": {
        "publications": [
          {
            "authors": "Rønnestad et al.",
            "year": 2021,
            "title": "Example endurance training study",
            "link": "durability_bibliography.md#Ronnestad2021"
          }
        ],
        "plan_alignment_check": "Plan aligns with durability‑first evidence.",
        "rationale": "Evidence supports endurance‑dominant base for long events."
      }
    },
    "explicit_forbidden_content": [
      "phase definitions (phase plans)",
      "weekly schedules",
      "day-by-day structure",
      "workouts or interval prescriptions",
      "numeric progression rules",
      "daily or session-level kJ targets"
    ],
    "self_check": {
      "planning_horizon_is_at_least_8_weeks": true,
      "every_phase_defines_weekly_kj_corridor": true,
      "every_phase_includes_kj_per_kg_guardrails_and_reference_mass": true,
      "every_phase_maps_to_cycle_and_deload_intent": true,
      "every_phase_includes_narrative_and_metabolic_focus": true,
      "every_phase_includes_evaluation_focus_and_exit_assumptions": true,
      "season_load_envelope_and_assumptions_documented": true,
      "principles_and_scientific_foundation_documented": true,
      "allowed_forbidden_domains_listed": true,
      "no_phase_or_week_planning_content": true,
      "header_includes_implements_iso_week_range_trace": true
    }
  }
}
```
