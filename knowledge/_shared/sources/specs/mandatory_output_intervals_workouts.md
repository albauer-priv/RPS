# Mandatory Output Chapter

Purpose
This chapter defines how to produce **schema‑valid INTERVALS_WORKOUTS JSON**.

---

## ARTIFACT: INTERVALS_WORKOUTS

### WHICH SCHEMA TO USE AND HOW TO FIND
- Schema: `workouts.schema.json`
  - Filter: `{"type":"eq","key":"schema_id","value":"workouts.schema.json"}`
- You MUST validate output against this schema before calling `store_intervals_workouts_export`.

### HOW TO FILL (BINDING)

#### 1) Output shape
- **Top‑level value is an array**, not an object.
- Do NOT include `meta` or `data` keys.
- The store tool expects the array directly (no envelope).

#### 2) Each item (workout)
Required fields:
- `start_date_local` (string `YYYY-MM-DDTHH:MM:SS`)
- `category` (const `WORKOUT`)
- `type` (const `Ride`)
- `name` (string, min 1)
- `description` (string; may be empty)

#### 3) Validation & Stop (Binding)
- Before output: confirm the Mandatory Output Chapter was read in full and followed exactly.
- Validate against `workouts.schema.json` before calling the store tool.
- If validation fails or any required field is missing/unknown: STOP.
- Do not use empty strings for required string fields (including citations). If required info is missing: STOP.
- Call `store_intervals_workouts_export` with the JSON array only (no envelope).
- Do NOT output raw JSON in chat; only the store tool call is allowed.
- On any error: **STOP** and report schema errors.

---

### EXAMPLE: INTERVALS_WORKOUTS (minimal valid)

```json
[
  {
    "start_date_local": "2026-01-20T07:00:00",
    "category": "WORKOUT",
    "type": "Ride",
    "name": "Endurance Ride",
    "description": "- 1h30m 65% 90rpm"
  }
]
```
