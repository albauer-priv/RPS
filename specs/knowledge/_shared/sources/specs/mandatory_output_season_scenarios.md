# Mandatory Output Chapter

Purpose
This chapter defines how to produce **schema‑valid SEASON_SCENARIOS JSON**. It is the
single source of truth for filling the mandatory output fields, including the
required schema, field sources, and a minimal valid example.

---

## ARTIFACT: SEASON_SCENARIOS

### WHICH SCHEMA TO USE AND HOW TO FIND
- Schema: `season_scenarios.schema.json`
  - Filter: `{"type":"eq","key":"schema_id","value":"season_scenarios.schema.json"}`
- You MUST validate output against this schema before calling `store_season_scenarios`.

### HOW TO FILL (BINDING)

#### 1) Envelope (top‑level)
- Output MUST be a **top‑level object** with only:
  - `meta`
  - `data`
- Call `store_season_scenarios` with this envelope only. No wrappers, no extra keys.

#### 2) `meta` (required fields)
- `artifact_type`: `"SEASON_SCENARIOS"`
- `schema_id`: `"SeasonScenariosInterface"`
- `schema_version`: `"1.0"`
- `version`: `"1.0"`
- `authority`: `"Informational"`
- `owner_agent`: `"Season-Scenario-Agent"`
- `run_id`: provided by runner
- `created_at`: ISO‑8601 timestamp (UTC)
- `scope`: `"Season"`
- `iso_week`: ISO week string `YYYY-WW`
- `iso_week_range`: `YYYY-WW--YYYY-WW` (string, inclusive)
- `temporal_scope`: `{ "from": "YYYY-MM-DD", "to": "YYYY-MM-DD" }`
- `trace_upstream`: include ATHLETE_PROFILE + PLANNING_EVENTS + LOGISTICS + KPI_PROFILE + AVAILABILITY (if loaded)
- `trace_data`, `trace_events`: include inputs if used
- `notes`: non‑empty string

#### 3) `data` (required fields)
- `kpi_profile_ref`: loaded KPI Profile id (exact string)
- `athlete_profile_ref`: Athlete Profile run_id or profile id
- `planning_horizon_weeks`: integer (>=1)
- `scenarios`: **array of exactly three scenarios** (`A`, `B`, `C`)
- `notes`: array of non‑empty strings (at least 1)

#### 4) `data.scenarios[]` (required fields)
Each scenario MUST include:
- `scenario_id`: `"A"`, `"B"`, or `"C"`
- `name`: string
- `core_idea`: string
- `load_philosophy`: string
- `risk_profile`: string
- `key_differences`: string
- `best_suited_if`: string
- `scenario_guidance` (object; all fields required):
  - `deload_cadence` (string, e.g., `"3:1"`)
  - `phase_length_weeks` (int)
  - `phase_count_expected` (int)
  - `max_shortened_phases` (int)
  - `shortening_budget_weeks` (int)
  - `phase_plan_summary`:
    - `full_phases` (int)
    - `shortened_phases` (array; items `{ "len": int, "count": int }`)
  - `event_alignment_notes` (array of strings; may be empty)
  - `risk_flags` (array of strings; may be empty)
  - `fixed_rest_days` (array of strings; may be empty)
  - `constraint_summary` (array of strings; may be empty)
  - `kpi_guardrail_notes` (array of strings; may be empty)
  - `decision_notes` (array of strings; may be empty)
  - `intensity_guidance`:
    - `allowed_domains` (array, min 1)
    - `avoid_domains` (array; may be empty)
  - `assumptions` (array; may be empty)
  - `unknowns` (array; may be empty)

Notes:
- `deload_cadence` and `phase_length_weeks` must be consistent with
  `progressive_overload_policy.md`. Scenarios must not define numeric weekly kJ
  targets or cadence overrides outside that policy.
- Runtime canonicalizes deterministic horizon/math fields before store:
  - `meta.iso_week_range`
  - `meta.temporal_scope`
  - `data.planning_horizon_weeks`
  - `scenario_guidance.phase_count_expected`
  - `scenario_guidance.shortening_budget_weeks`
  - `scenario_guidance.phase_plan_summary`
  Emit best-effort schema-valid values, but qualitative scenario content is the primary agent responsibility.

---

### EXAMPLE: SEASON_SCENARIOS (minimal valid)

```json
{
  "meta": {
    "artifact_type": "SEASON_SCENARIOS",
    "schema_id": "SeasonScenariosInterface",
    "schema_version": "1.0",
    "version": "1.0",
    "authority": "Informational",
    "owner_agent": "Season-Scenario-Agent",
    "run_id": "example_scenarios_2026_w04",
    "created_at": "2026-01-26T00:00:00Z",
    "scope": "Season",
    "iso_week": "2026-04",
    "iso_week_range": "2026-04--2026-19",
    "temporal_scope": { "from": "2026-01-19", "to": "2026-05-17" },
    "trace_upstream": [
      { "artifact": "athlete_profile", "version": "1.0", "run_id": "athlete_profile_2026" },
      { "artifact": "planning_events", "version": "1.0", "run_id": "planning_events_2026" },
      { "artifact": "KPI_PROFILE", "version": "1.0", "run_id": "KPI_Profile_Example" },
      { "artifact": "AVAILABILITY", "version": "1.0", "run_id": "availability_2026-04" }
    ],
    "trace_data": [],
    "trace_events": [],
    "notes": "Example only. Replace with real trace references."
  },
  "data": {
    "kpi_profile_ref": "KPI_Profile_Example",
    "athlete_profile_ref": "athlete_profile_2026",
    "planning_horizon_weeks": 16,
    "scenarios": [
      {
        "scenario_id": "A",
        "name": "Conservative Base",
        "core_idea": "Prioritise durability and consistency.",
        "load_philosophy": "Endurance-heavy progression with protected deloads.",
        "risk_profile": "Low risk, slower VO2 gains.",
        "key_differences": "Lower peak load, conservative intensity.",
        "best_suited_if": "Athlete prioritises completion and low risk.",
        "scenario_guidance": {
          "deload_cadence": "3:1",
          "phase_length_weeks": 4,
          "phase_count_expected": 4,
          "max_shortened_phases": 2,
          "shortening_budget_weeks": 0,
          "phase_plan_summary": {
            "full_phases": 4,
            "shortened_phases": []
          },
          "event_alignment_notes": ["A-event inside final phase."],
          "risk_flags": ["Masters recovery sensitivity."],
          "fixed_rest_days": ["Mon", "Fri"],
          "constraint_summary": ["Typical weekly hours 8-10."],
          "kpi_guardrail_notes": ["Weekly kJ increase <= 10%."],
          "decision_notes": ["Prioritise durability over speed."],
          "intensity_guidance": {
            "allowed_domains": ["ENDURANCE_LOW", "TEMPO"],
            "avoid_domains": ["VO2MAX"]
          },
          "assumptions": ["Stable availability."],
          "unknowns": ["Exact travel weeks."]
        }
      },
      {
        "scenario_id": "B",
        "name": "Balanced Progression",
        "core_idea": "Balance durability with moderate intensity.",
        "load_philosophy": "Mixed endurance and tempo with regular deloads.",
        "risk_profile": "Moderate risk, faster gains.",
        "key_differences": "More tempo exposure than A.",
        "best_suited_if": "Athlete seeks performance gains with guardrails.",
        "scenario_guidance": {
          "deload_cadence": "2:1",
          "phase_length_weeks": 3,
          "phase_count_expected": 6,
          "max_shortened_phases": 2,
          "shortening_budget_weeks": 2,
          "phase_plan_summary": {
            "full_phases": 5,
            "shortened_phases": [{ "len": 2, "count": 1 }]
          },
          "event_alignment_notes": ["B-events in build phases."],
          "risk_flags": ["Travel weeks may disrupt quality."],
          "fixed_rest_days": ["Mon", "Fri"],
          "constraint_summary": ["Indoor trainer available."],
          "kpi_guardrail_notes": ["Progression capped at 10%."],
          "decision_notes": ["Maintain recovery anchors."],
          "intensity_guidance": {
            "allowed_domains": ["ENDURANCE_LOW", "TEMPO", "SWEET_SPOT"],
            "avoid_domains": ["VO2MAX"]
          },
          "assumptions": ["Reliable weekday sessions."],
          "unknowns": ["Exact event logistics."]
        }
      },
      {
        "scenario_id": "C",
        "name": "Aggressive Specificity",
        "core_idea": "Shorter phases with higher intensity focus.",
        "load_philosophy": "Higher intensity density and shorter deloads.",
        "risk_profile": "Higher risk, faster gains.",
        "key_differences": "More intensity than A/B.",
        "best_suited_if": "Athlete accepts higher fatigue risk.",
        "scenario_guidance": {
          "deload_cadence": "2:1:1",
          "phase_length_weeks": 4,
          "phase_count_expected": 4,
          "max_shortened_phases": 2,
          "shortening_budget_weeks": 0,
          "phase_plan_summary": {
            "full_phases": 4,
            "shortened_phases": []
          },
          "event_alignment_notes": ["A-event in Peak phase."],
          "risk_flags": ["Higher fatigue accumulation."],
          "fixed_rest_days": ["Mon", "Fri"],
          "constraint_summary": ["Travel weeks need adjustments."],
          "kpi_guardrail_notes": ["Hold or deload on red KPI."],
          "decision_notes": ["Prioritise specificity near events."],
          "intensity_guidance": {
            "allowed_domains": ["ENDURANCE_LOW", "TEMPO", "VO2MAX"],
            "avoid_domains": []
          },
          "assumptions": ["Short-term intensity tolerance."],
          "unknowns": ["Exact recovery response."]
        }
      }
    ],
    "notes": ["Example only. Replace with real scenario content."]
  }
}
```

#### Validation & Stop (Binding)
- Use the store tool with a top-level `{ "meta": ..., "data": ... }` envelope only.
- Do NOT output raw JSON in chat; only the store tool call is allowed.
- Tool call arguments MUST be valid JSON only (no markdown, no comments, no trailing commas, no control tokens).
- Before output: confirm the Mandatory Output Chapter was read in full and followed exactly.
- Validate against `season_scenarios.schema.json` before calling the store tool.
- If validation fails or any required field is missing/unknown: STOP.
- Validate against schema before calling store.
- Do not use empty strings for required string fields (including citations). If required info is missing: STOP.
