# Mandatory Output Chapter

Purpose
This chapter defines how to produce **schema‑valid BLOCK_FEED_FORWARD JSON**.

---

## ARTIFACT: BLOCK_FEED_FORWARD

### WHICH SCHEMA TO USE AND HOW TO FIND
- Schema: `block_feed_forward.schema.json`
- Retrieve with file_search (Knowledge Retrieval table):
  - Filter: `{"type":"eq","key":"schema_id","value":"block_feed_forward.schema.json"}`
- You MUST validate output against this schema before calling `store_block_feed_forward`.
- This Mandatory Output Chapter is already included in the prompt. **Do NOT file_search it.**

### HOW TO FILL (BINDING)

#### 1) Envelope (top‑level)
- Output MUST be a **top‑level object** with only:
  - `meta`
  - `data`

#### 2) `meta` (required fields)
- Must satisfy `artefact_meta.schema.json`.
- Required constants:
  - `artifact_type`: `"BLOCK_FEED_FORWARD"`
  - `schema_id`: `"BlockFeedForwardInterface"`
  - `schema_version`: `"1.0"`
  - `authority`: `"Binding"`
  - `owner_agent`: `"Meso-Architect"`
- `iso_week_range` required.

#### 3) `data.body_metadata`
Required:
- `applies_to_weeks` (array of ISO weeks)
- `valid_until` (date)
- `change_type`: `NEW|ADJUSTED|NONE`
- `derived_from` (string)
- `upstream_triggers` (array of strings)

#### 4) `data.reason_context`
Required strings:
- `trigger_summary`
- `observed_risk_deviation`
- `intent_of_adjustment`

#### 5) `data.delta_load_guardrails`
Required:
- `adjusted_weekly_kj_bands` (array of `{week, band, rationale, notes}`)

#### 6) `data.temporary_semantic_overrides`
Required object:
- `intensity_domain` with `newly_forbidden` and `newly_allowed` arrays
- `load_modality` with `newly_forbidden` and `newly_allowed` arrays
- `quality_density_override` with:
  - `max_quality_days_per_week` (int)
  - `additional_forbidden_patterns` (array)

#### 7) `data.temporary_non_negotiables`
Required strings:
- `recovery_protection_changes`
- `anchor_protection_changes`
- `explicit_expiry_condition`

#### 8) `data.micro_planner_operating_rules`
- Array of strings (min 1)

#### 9) `data.explicit_forbidden_content`
- Array (min 1) with values from enum:
  - `workouts or intervals`
  - `day-by-day schedules`
  - `numeric progression rules`
  - `instructions like +10min Z2`

#### 10) `data.self_check`
All required booleans must be present and set to `true`:
- `applies_to_weeks_specified`
- `valid_until_defined`
- `only_deltas_vs_baseline_included`
- `no_micro_content_present`

#### 11) Validation & Stop (Binding)
- Use the store tool with a top-level `{ "meta": ..., "data": ... }` envelope only.
- Do NOT output raw JSON in chat; only the store tool call is allowed.
- Before output: confirm the Mandatory Output Chapter was read in full and followed exactly.
- Validate against `block_feed_forward.schema.json` before calling the store tool.
- If validation fails or any required field is missing/unknown: STOP.
- Do not use empty strings for required string fields (including citations). If required info is missing: STOP.
- Validate against schema before calling `store_block_feed_forward`.
- On any error: **STOP** and report schema errors.

---

### EXAMPLE: BLOCK_FEED_FORWARD (minimal valid)

```json
{
  "meta": {
    "artifact_type": "BLOCK_FEED_FORWARD",
    "schema_id": "BlockFeedForwardInterface",
    "schema_version": "1.0",
    "version": "1.0",
    "authority": "Binding",
    "owner_agent": "Meso-Architect",
    "run_id": "example_block_feed_forward_2026_w04",
    "created_at": "2026-01-26T00:00:00Z",
    "scope": "Meso",
    "iso_week": "2026-04",
    "iso_week_range": "2026-04--2026-04",
    "temporal_scope": { "from": "2026-01-19", "to": "2026-01-25" },
    "trace_upstream": [
      { "artifact": "BLOCK_GOVERNANCE", "version": "1.0", "run_id": "block_governance_2026_w04" }
    ],
    "trace_data": [],
    "trace_events": [],
    "notes": "Example only. Replace with real trace references."
  },
  "data": {
    "body_metadata": {
      "applies_to_weeks": ["2026-04"],
      "valid_until": "2026-01-25",
      "change_type": "ADJUSTED",
      "derived_from": "block_governance_2026_w04",
      "upstream_triggers": ["Travel week"]
    },
    "reason_context": {
      "trigger_summary": "Travel reduces available time",
      "observed_risk_deviation": "Availability below baseline",
      "intent_of_adjustment": "Reduce weekly load band for affected week"
    },
    "delta_load_guardrails": {
      "adjusted_weekly_kj_bands": [
        {
          "week": "2026-04",
          "band": { "min": 5000, "max": 6500, "notes": "Adjusted band" },
          "rationale": "Reduced time available",
          "notes": "Applies only to this week"
        }
      ]
    },
    "temporary_semantic_overrides": {
      "intensity_domain": {
        "newly_forbidden": ["VO2MAX"],
        "newly_allowed": []
      },
      "load_modality": {
        "newly_forbidden": [],
        "newly_allowed": []
      },
      "quality_density_override": {
        "max_quality_days_per_week": 0,
        "additional_forbidden_patterns": ["Any quality day"]
      }
    },
    "temporary_non_negotiables": {
      "recovery_protection_changes": "Increase recovery emphasis",
      "anchor_protection_changes": "Protect long ride",
      "explicit_expiry_condition": "Expires after 2026-04"
    },
    "micro_planner_operating_rules": ["No catch-up sessions"],
    "explicit_forbidden_content": ["day-by-day schedules"],
    "self_check": {
      "applies_to_weeks_specified": true,
      "valid_until_defined": true,
      "only_deltas_vs_baseline_included": true,
      "no_micro_content_present": true
    }
  }
}
```
