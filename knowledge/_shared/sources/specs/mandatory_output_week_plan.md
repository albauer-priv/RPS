# Mandatory Output Chapter

Purpose
This chapter defines how to produce **schema‑valid WEEK_PLAN JSON**.

---

## ARTIFACT: WEEK_PLAN

### WHICH SCHEMA TO USE AND HOW TO FIND
- Schema: `week_plan.schema.json`
  - Filter: `{"type":"eq","key":"schema_id","value":"week_plan.schema.json"}`
- You MUST validate output against this schema before calling `store_week_plan`.

### HOW TO FILL (BINDING)

#### 1) Envelope (top‑level)
- Output MUST be a **top‑level object** with only:
  - `meta`
  - `data`

#### 2) `meta` (required fields)
- Must satisfy `artefact_meta.schema.json`.
- Required constants:
  - `artifact_type`: `"WEEK_PLAN"`
  - `schema_id`: `"WeekPlanInterface"`
  - `schema_version`: `"1.2"`
  - `authority`: `"Binding"`
  - `owner_agent`: `"Micro-Planner"`
- `iso_week` required (string `YYYY-WW`).

#### 3) `data.week_summary`
Required:
- `week_objective` (string)
- `weekly_load_corridor_kj` (object `{min,max,notes}` from `load_band.schema.json`)
- `planned_weekly_load_kj` (number)
- `notes` (string)

#### 4) `data.agenda`
- Array of **exactly 7** entries (Mon..Sun). Each entry:
  - `day` (Mon..Sun)
  - `date` (YYYY-MM-DD)
  - `day_role` (agenda enum)
  - `planned_duration` (HH:MM)
  - `planned_kj` (number >= 0)
  - `workout_id` (string or null)

#### 5) `data.workouts`
- Array of workout objects (can be empty if all days are rest)
- Each workout requires:
  - `workout_id` (string)
  - `title` (string)
  - `date` (YYYY-MM-DD)
  - `start` (HH:MM)
  - `duration` (HH:MM:SS)
  - `workout_text` (string, non‑empty)
  - `notes` (string)
- Any `workout_id` referenced in `agenda` MUST appear in `workouts`.

#### 6) Validation & Stop (Binding)
- Use the store tool with a top-level `{ "meta": ..., "data": ... }` envelope only.
- Do NOT output raw JSON in chat; only the store tool call is allowed.
- Before output: confirm the Mandatory Output Chapter was read in full and followed exactly.
- Validate against `week_plan.schema.json` before calling the store tool.
- If validation fails or any required field is missing/unknown: STOP.
- Do not use empty strings for required string fields (including citations). If required info is missing: STOP.
- Validate against schema before calling `store_week_plan`.
- On any error: **STOP** and report schema errors.

---

### EXAMPLE: WEEK_PLAN (minimal valid)

```json
{
  "meta": {
    "artifact_type": "WEEK_PLAN",
    "schema_id": "WeekPlanInterface",
    "schema_version": "1.2",
    "version": "1.0",
    "authority": "Binding",
    "owner_agent": "Micro-Planner",
    "run_id": "example_week_plan_2026_w04",
    "created_at": "2026-01-26T00:00:00Z",
    "scope": "Micro",
    "iso_week": "2026-04",
    "iso_week_range": "2026-04--2026-04",
    "temporal_scope": { "from": "2026-01-19", "to": "2026-01-25" },
    "trace_upstream": [
      { "artifact": "PHASE_STRUCTURE", "version": "1.0", "run_id": "phase_structure_2026_w04" }
    ],
    "trace_data": [],
    "trace_events": [],
    "notes": "Example only. Replace with real trace references."
  },
  "data": {
    "week_summary": {
      "week_objective": "Build consistent endurance volume.",
      "weekly_load_corridor_kj": { "min": 7000, "max": 8500, "notes": "Example corridor" },
      "planned_weekly_load_kj": 7400,
      "notes": "Example summary."
    },
    "agenda": [
      { "day": "Mon", "date": "2026-01-19", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": null },
      { "day": "Tue", "date": "2026-01-20", "day_role": "ENDURANCE", "planned_duration": "01:30", "planned_kj": 600, "workout_id": "W-2026-04-TUE" },
      { "day": "Wed", "date": "2026-01-21", "day_role": "ENDURANCE", "planned_duration": "01:00", "planned_kj": 400, "workout_id": "W-2026-04-WED" },
      { "day": "Thu", "date": "2026-01-22", "day_role": "RECOVERY", "planned_duration": "00:45", "planned_kj": 200, "workout_id": "W-2026-04-THU" },
      { "day": "Fri", "date": "2026-01-23", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": null },
      { "day": "Sat", "date": "2026-01-24", "day_role": "ENDURANCE", "planned_duration": "02:30", "planned_kj": 1200, "workout_id": "W-2026-04-SAT" },
      { "day": "Sun", "date": "2026-01-25", "day_role": "ENDURANCE", "planned_duration": "02:00", "planned_kj": 1000, "workout_id": "W-2026-04-SUN" }
    ],
    "workouts": [
      { "workout_id": "W-2026-04-TUE", "title": "Endurance Ride", "date": "2026-01-20", "start": "07:00", "duration": "01:30:00", "workout_text": "- 1h30m 65% 90rpm", "notes": "" },
      { "workout_id": "W-2026-04-WED", "title": "Endurance Ride", "date": "2026-01-21", "start": "07:00", "duration": "01:00:00", "workout_text": "- 1h 65% 90rpm", "notes": "" },
      { "workout_id": "W-2026-04-THU", "title": "Recovery Spin", "date": "2026-01-22", "start": "07:00", "duration": "00:45:00", "workout_text": "- 45m 55% 90rpm", "notes": "" },
      { "workout_id": "W-2026-04-SAT", "title": "Long Endurance", "date": "2026-01-24", "start": "08:00", "duration": "02:30:00", "workout_text": "- 2h30m 65% 90rpm", "notes": "" },
      { "workout_id": "W-2026-04-SUN", "title": "Endurance Ride", "date": "2026-01-25", "start": "08:00", "duration": "02:00:00", "workout_text": "- 2h 65% 90rpm", "notes": "" }
    ]
  }
}
```
