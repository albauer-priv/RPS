# Mandatory Output Chapter

Purpose
This chapter defines how to produce **schema-valid SEASON_SCENARIO_SELECTION JSON**. It is the
single source of truth for filling the mandatory output fields, including the
required schema, field sources, and a minimal valid example.

---

## ARTIFACT: SEASON_SCENARIO_SELECTION

### WHICH SCHEMA TO USE AND HOW TO FIND
- Schema: `season_scenario_selection.schema.json`
  - Filter: `{"type":"eq","key":"schema_id","value":"season_scenario_selection.schema.json"}`
- You MUST validate output against this schema before calling `store_season_scenario_selection`.

### HOW TO FILL (BINDING)

#### 1) Envelope (top-level)
- Output MUST be a **top-level object** with only:
  - `meta`
  - `data`
- Call `store_season_scenario_selection` with this envelope only. No wrappers, no extra keys.

#### 2) `meta` (required fields)
- `artifact_type`: `"SEASON_SCENARIO_SELECTION"`
- `schema_id`: `"SeasonScenarioSelectionInterface"`
- `schema_version`: `"1.1"`
- `version`: `"1.0"`
- `authority`: `"Informational"`
- `owner_agent`: `"Season-Scenario-Agent"`
- `run_id`: provided by runner
- `created_at`: ISO-8601 timestamp (UTC)
- `scope`: `"Season"`
- `iso_week`: ISO week string `YYYY-WW`
- `iso_week_range`: `YYYY-WW--YYYY-WW` (string, inclusive)
- `temporal_scope`: `{ "from": "YYYY-MM-DD", "to": "YYYY-MM-DD" }`
- `trace_upstream`: include SEASON_SCENARIOS + KPI_PROFILE + AVAILABILITY (if loaded)
- `trace_data`, `trace_events`: include inputs if used
- `notes`: non-empty string

#### 3) `data` (required fields)
- `season_scenarios_ref`: latest SEASON_SCENARIOS run_id or version key
- `selected_scenario_id`: `"A"`, `"B"`, or `"C"`
- `selection_source`: `"user"` or `"system"`
- `selection_rationale`: string (may be empty, but must be present)
- `notes`: array of non-empty strings (at least 1)
- `kpi_moving_time_rate_guidance_selection`: object or null
  - If present: must include `segment`, `w_per_kg {min,max}`, `kj_per_kg_per_hour {min,max}`

---

### EXAMPLE: SEASON_SCENARIO_SELECTION (minimal valid)

```json
{
  "meta": {
    "artifact_type": "SEASON_SCENARIO_SELECTION",
    "schema_id": "SeasonScenarioSelectionInterface",
    "schema_version": "1.1",
    "version": "1.0",
    "authority": "Informational",
    "owner_agent": "Season-Scenario-Agent",
    "run_id": "example_selection_2026_w05",
    "created_at": "2026-02-01T00:00:00Z",
    "scope": "Season",
    "iso_week": "2026-05",
    "iso_week_range": "2026-05--2026-20",
    "temporal_scope": { "from": "2026-01-26", "to": "2026-05-17" },
    "trace_upstream": [
      { "artifact": "SEASON_SCENARIOS", "version": "2026-05", "run_id": "scenarios_2026_w05" },
      { "artifact": "KPI_PROFILE", "version": "1.0", "run_id": "kpi_profile_2026" },
      { "artifact": "AVAILABILITY", "version": "2026-05", "run_id": "availability_2026_w05" }
    ],
    "trace_data": [],
    "trace_events": [],
    "notes": "Example only. Replace with real trace references."
  },
  "data": {
    "season_scenarios_ref": "scenarios_2026_w05",
    "selected_scenario_id": "B",
    "selection_source": "user",
    "selection_rationale": "Prefers balanced progression with recovery protection.",
    "notes": ["Selected by athlete after reviewing A/B/C."],
    "kpi_moving_time_rate_guidance_selection": {
      "segment": "fast_competitive",
      "w_per_kg": { "min": 2.2, "max": 2.8 },
      "kj_per_kg_per_hour": { "min": 7.9, "max": 10.1 }
    }
  }
}
```
