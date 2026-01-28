# Mandatory Output Chapter

Purpose
This chapter defines how to produce **schema‑valid SEASON_PHASE_FEED_FORWARD JSON**.

---

## ARTIFACT: SEASON_PHASE_FEED_FORWARD

### WHICH SCHEMA TO USE AND HOW TO FIND
- Schema: `season_phase_feed_forward.schema.json`
  - Filter: `{"type":"eq","key":"schema_id","value":"season_phase_feed_forward.schema.json"}`
- You MUST validate output against this schema before calling `store_season_phase_feed_forward`.

### HOW TO FILL (BINDING)

#### 1) Envelope (top‑level)
- Output MUST be a **top‑level object** with only:
  - `meta`
  - `data`

#### 2) `meta` (required fields)
- Must satisfy `artefact_meta.schema.json`.
- Required constants:
  - `artifact_type`: `"SEASON_PHASE_FEED_FORWARD"`
  - `schema_id`: `"SeasonPhaseFeedForwardInterface"`
  - `schema_version`: `"1.0"`
  - `authority`: `"Binding"`
  - `owner_agent`: `"Season-Planner"`
- `iso_week` required.

#### 3) `data.source_context`
Required:
- `season_plan_ref` (string)
- `des_analysis_report_ref` (string)
- `affected_phase_id` (string)

#### 4) `data.decision_summary`
Required:
- `conclusion`: `no_change|adjust_phase|reweight_season`
- `rationale` (array, min 1)

#### 5) `data.explicit_non_actions`
- Array of **exactly 3** items:
  1) `No weekly workout changes`
  2) `No week-level intervention`
  3) `No KPI threshold enforcement`

#### 6) `data.phase_adjustment`
Required:
- `applies_to_weeks` (array of ISO weeks)
- `adjustments.kj_corridor`:
  - `direction`: `increase|decrease`
  - `percent` (number)
- `adjustments.quality_density`:
  - `action`: `allow|restrict`
  - `details` (string)

#### 7) Validation & Stop (Binding)
- Use the store tool with a top-level `{ "meta": ..., "data": ... }` envelope only.
- Do NOT output raw JSON in chat; only the store tool call is allowed.
- Before output: confirm the Mandatory Output Chapter was read in full and followed exactly.
- Validate against `season_phase_feed_forward.schema.json` before calling the store tool.
- If validation fails or any required field is missing/unknown: STOP.
- Do not use empty strings for required string fields (including citations). If required info is missing: STOP.
- Validate against schema before calling `store_season_phase_feed_forward`.
- On any error: **STOP** and report schema errors.

---

### EXAMPLE: SEASON_PHASE_FEED_FORWARD (minimal valid)

```json
{
  "meta": {
    "artifact_type": "SEASON_PHASE_FEED_FORWARD",
    "schema_id": "SeasonPhaseFeedForwardInterface",
    "schema_version": "1.0",
    "version": "1.0",
    "authority": "Binding",
    "owner_agent": "Season-Planner",
    "run_id": "example_season_phase_ff_2026_w04",
    "created_at": "2026-01-26T00:00:00Z",
    "scope": "Season",
    "iso_week": "2026-04",
    "iso_week_range": "2026-04--2026-04",
    "temporal_scope": { "from": "2026-01-19", "to": "2026-01-25" },
    "trace_upstream": [],
    "trace_data": [],
    "trace_events": [],
    "notes": "Example only."
  },
  "data": {
    "source_context": {
      "season_plan_ref": "season_plan_2026_w04",
      "des_analysis_report_ref": "des_analysis_report_2026-04",
      "affected_phase_id": "P01"
    },
    "decision_summary": {
      "conclusion": "adjust_phase",
      "rationale": ["Load corridor infeasible under availability"]
    },
    "explicit_non_actions": [
      "No weekly workout changes",
      "No week-level intervention",
      "No KPI threshold enforcement"
    ],
    "phase_adjustment": {
      "applies_to_weeks": ["2026-04"],
      "adjustments": {
        "kj_corridor": { "direction": "decrease", "percent": 5 },
        "quality_density": { "action": "restrict", "details": "Reduce quality days to 0" }
      }
    }
  }
}
```
