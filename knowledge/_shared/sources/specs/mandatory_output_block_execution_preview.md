# Mandatory Output Chapter

Purpose
This chapter defines how to produce **schema‑valid BLOCK_EXECUTION_PREVIEW JSON**.

---

## ARTIFACT: BLOCK_EXECUTION_PREVIEW

### WHICH SCHEMA TO USE AND HOW TO FIND
- Schema: `block_execution_preview.schema.json`
- Retrieve with file_search (Knowledge Retrieval table):
  - Filter: `{"type":"eq","key":"schema_id","value":"block_execution_preview.schema.json"}`
- You MUST validate output against this schema before calling `store_block_execution_preview`.
- This Mandatory Output Chapter is already included in the prompt. **Do NOT file_search it.**

### HOW TO FILL (BINDING)

#### 1) Envelope (top‑level)
- Output MUST be a **top‑level object** with only:
  - `meta`
  - `data`

#### 2) `meta` (required fields)
- Must satisfy `artefact_meta.schema.json`.
- Required constants:
  - `artifact_type`: `"BLOCK_EXECUTION_PREVIEW"`
  - `schema_id`: `"BlockExecutionPreviewInterface"`
  - `schema_version`: `"1.0"`
  - `authority`: `"Binding"`
  - `owner_agent`: `"Meso-Architect"`
- `iso_week_range` required.

#### 3) `data.block_intent_summary`
Required:
- `block_type` (string)
- `primary_objective` (string)
- `non_negotiables` (array, min 1)
- `key_risks_warnings` (array, min 1)

#### 4) `data.feel_overview`
Required strings:
- `dominant_theme`
- `intensity_handling_conceptual`
- `recovery_protection_conceptual`

#### 5) `data.weekly_agenda_preview`
- Array of week objects (min 1):
  - `week` (ISO week string)
  - `days` (array of **exactly 7** agenda_day entries)
- Each agenda_day requires:
  - `day_of_week` (`Mon..Sun`)
  - `day_role` (agenda enum)
  - `intensity_domain` (agenda enum)
  - `load_modality` (agenda enum)
  - `notes` (string)

#### 6) `data.week_to_week_narrative`
Required strings:
- `direction`
- `what_will_not_change`
- `what_is_flexible`

#### 7) `data.deviation_rules`
- Array of strings (min 1)

#### 8) `data.traceability`
- `derived_from` (array, min 1)
- `conflict_resolution` (array, min 1)

#### 9) Validation & Stop (Binding)
- Use the store tool with a top-level `{ "meta": ..., "data": ... }` envelope only.
- Do NOT output raw JSON in chat; only the store tool call is allowed.
- Before output: confirm the Mandatory Output Chapter was read in full and followed exactly.
- Validate against `block_execution_preview.schema.json` before calling the store tool.
- If validation fails or any required field is missing/unknown: STOP.
- Do not use empty strings for required string fields (including citations). If required info is missing: STOP.
- Validate against schema before calling `store_block_execution_preview`.
- On any error: **STOP** and report schema errors.

---

### EXAMPLE: BLOCK_EXECUTION_PREVIEW (minimal valid)

```json
{
  "meta": {
    "artifact_type": "BLOCK_EXECUTION_PREVIEW",
    "schema_id": "BlockExecutionPreviewInterface",
    "schema_version": "1.0",
    "version": "1.0",
    "authority": "Binding",
    "owner_agent": "Meso-Architect",
    "run_id": "example_block_execution_preview_2026_w04",
    "created_at": "2026-01-26T00:00:00Z",
    "scope": "Meso",
    "iso_week": "2026-04",
    "iso_week_range": "2026-04--2026-05",
    "temporal_scope": { "from": "2026-01-19", "to": "2026-02-01" },
    "trace_upstream": [
      { "artifact": "BLOCK_EXECUTION_ARCH", "version": "1.0", "run_id": "block_execution_arch_2026_w04" }
    ],
    "trace_data": [],
    "trace_events": [],
    "notes": "Example only. Replace with real trace references."
  },
  "data": {
    "block_intent_summary": {
      "block_type": "Base",
      "primary_objective": "Establish durability",
      "non_negotiables": ["Fixed rest days preserved."],
      "key_risks_warnings": ["Travel risk"]
    },
    "feel_overview": {
      "dominant_theme": "Consistency",
      "intensity_handling_conceptual": "Low density, controlled intensity",
      "recovery_protection_conceptual": "Recovery anchors preserved"
    },
    "weekly_agenda_preview": [
      {
        "week": "2026-04",
        "days": [
          { "day_of_week": "Mon", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "Fixed rest" },
          { "day_of_week": "Tue", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE_LOW", "load_modality": "NONE", "notes": "Steady endurance" },
          { "day_of_week": "Wed", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE_LOW", "load_modality": "NONE", "notes": "Steady endurance" },
          { "day_of_week": "Thu", "day_role": "QUALITY", "intensity_domain": "TEMPO", "load_modality": "NONE", "notes": "One focused session" },
          { "day_of_week": "Fri", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "Fixed rest" },
          { "day_of_week": "Sat", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE_HIGH", "load_modality": "NONE", "notes": "Long ride" },
          { "day_of_week": "Sun", "day_role": "RECOVERY", "intensity_domain": "RECOVERY", "load_modality": "NONE", "notes": "Recovery spin" }
        ]
      }
    ],
    "week_to_week_narrative": {
      "direction": "Slight increase then recovery",
      "what_will_not_change": "Fixed rest days",
      "what_is_flexible": "Placement of quality day"
    },
    "deviation_rules": ["If travel occurs, drop optional day without compensation"],
    "traceability": {
      "derived_from": ["block_execution_arch_2026-04.json"],
      "conflict_resolution": ["Escalate to Macro-Planner if conflicts arise"]
    }
  }
}
```
