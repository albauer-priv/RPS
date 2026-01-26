# Mandatory Output Chapter

Purpose
This chapter defines how to produce **schema‑valid BLOCK_GOVERNANCE JSON**. It is the
single source of truth for filling the mandatory output fields, including the
required schema, field sources, and a minimal valid example.

---

## ARTIFACT: BLOCK_GOVERNANCE

### WHICH SCHEMA TO USE AND HOW TO FIND
- Schema: `block_governance.schema.json`
- Retrieve with file_search (Knowledge Retrieval table):
  - Filter: `{"type":"eq","key":"schema_id","value":"block_governance.schema.json"}`
- You MUST validate output against this schema before calling `store_block_governance`.
- This Mandatory Output Chapter is already included in the prompt. **Do NOT file_search it.**

### HOW TO FILL (BINDING)

#### 1) Envelope (top‑level)
- Output MUST be a **top‑level object** with only:
  - `meta`
  - `data`

#### 2) `meta` (required fields)
- Must satisfy `artefact_meta.schema.json`.
- Required constants:
  - `artifact_type`: `"BLOCK_GOVERNANCE"`
  - `schema_id`: `"BlockGovernanceInterface"`
  - `schema_version`: `"1.0"`
  - `authority`: `"Binding"`
  - `owner_agent`: `"Meso-Architect"`
- `iso_week_range` is required (string `YYYY-WW--YYYY-WW`).
- `iso_week` MUST be the **first** ISO week in `iso_week_range`.
- `temporal_scope` MUST be copied from an upstream artefact (e.g., Macro Overview phase
  `date_range` for the same block). **Do NOT compute calendar dates.**

#### 3) `data.body_metadata`
Required:
- `block_id`, `block_type` (strings)
- `block_status`: `Green|Yellow|Red`
- `change_type`: `NEW|ADJUSTED|NONE`
- `derived_from` (string)
- `upstream_inputs` (array of non‑empty strings)

#### 4) `data.block_summary`
Required:
- `primary_objective` (string)
- `secondary_objectives` (array of strings; can be empty)
- `key_risks_warnings` (array, min 1)
- `non_negotiables` (array, min 1)

#### 5) `data.load_guardrails`
Required:
- `weekly_kj_bands` (array of `{week, band}`)
  - `week` is ISO week string `YYYY-WW`.
  - `band` is `{min,max,notes}` (from `load_band.schema.json`).
- `confidence_assumptions`:
  - `kj_estimation_method`: `AvgPower-based|IF+r heuristic|Mixed`
  - `confidence.kj`: `HIGH|MED|LOW`
  - `ftp_watts_used` (number)
  - `zone_model_version` (string)

#### 5.2) Progression & deload shaping (binding)
- Use `progressive_overload_policy.md` to shape progression, deload, and re-entry rules.
- If Scenario/Macro provides `deload_cadence` or `phase_length_weeks`, treat them as **binding**.
- Do NOT invent a default cadence.

#### 5.1) Macro constraint propagation (binding)
Always import `macro_overview.data.global_constraints`:
- `availability_assumptions`, `risk_constraints`, `planned_event_windows`, `recovery_protection` (if present).

Mapping (must include, do not omit):
- Availability assumptions → `block_summary.non_negotiables` (verbatim).
  Every entry from `macro_overview.data.global_constraints.availability_assumptions`
  MUST appear verbatim in `block_summary.non_negotiables`.
- Risk constraints → `block_summary.key_risks_warnings` (verbatim).
  Every entry from `macro_overview.data.global_constraints.risk_constraints`
  MUST appear verbatim in `block_summary.key_risks_warnings`.
- Planned event windows → MUST be represented in `events_constraints.events[]`
  using the A/B/C types already defined in `macro_overview.data.phases[].events_constraints`.
  Do NOT source A/B/C event types from `events.md` (events.md is non-training logistics only).
  Also add a single summary line to `block_summary.non_negotiables`:
  `"Planned A/B/C windows included in events_constraints (from macro_overview)."`
- Recovery protection notes → `execution_non_negotiables.recovery_protection_rules` (verbatim).

#### 6) `data.allowed_forbidden_semantics`
Required:
- `allowed_day_roles` (array, min 1)
- `allowed_intensity_domains` (array, min 1)
- `allowed_load_modalities` (array)
- `quality_density` with:
  - `max_quality_days_per_week` (int)
  - `quality_intent`: `Stabilization|Build|Overload`
  - `forbidden_patterns` (array)
- `forbidden_day_roles`, `forbidden_intensity_domains`, `forbidden_load_modalities` (arrays; may be empty)

#### 7) `data.events_constraints`
Required:
- `events`: array of `{date, week, type, constraint}`
  - `date` format `YYYY-MM-DD`
  - `week` ISO week string `YYYY-WW`
  - `type` is `A|B|C`
- `logistics_time_constraints` object with:
  - `travel_days`, `work_constraints`, `weather_or_indoor_constraints` (strings)

#### 8) `data.execution_non_negotiables`
Required strings:
- `recovery_protection_rules`
- `long_endurance_anchor_protection`
- `minimum_recovery_opportunities`
- `no_catch_up_rule`

#### 9) `data.escalation_change_control`
Required:
- `warning_signals` (array, min 1)
- `required_response` object with:
  - `micro_planner_must` (array, min 1)
  - `micro_planner_must_not` (array, min 1)
  - `meso_architect_decides` (string)

#### 10) `data.explicit_forbidden_content`
- Must contain **exactly these 6 strings** (schema enum):
  1) `day-by-day plans`
  2) `workouts or interval prescriptions`
  3) `durations, zones (Z1-Z7), %FTP`
  4) `daily kJ targets`
  5) `numeric progression rules`
  6) `recommendations that effectively plan the micro level`

#### 11) `data.self_check`
All required booleans must be present and set to `true`:
- `weekly_kj_bands_present`
- `max_quality_days_specified`
- `allowed_forbidden_enums_specified`
- `no_micro_planning_content`
- `header_includes_implements_iso_week_range_trace`

#### 12) Validation & Stop (Binding)
- Use the store tool with a top-level `{ "meta": ..., "data": ... }` envelope only.
- Do NOT output raw JSON in chat; only the store tool call is allowed.
- Before output: confirm the Mandatory Output Chapter was read in full and followed exactly.
- Validate against `block_governance.schema.json` before calling the store tool.
- If validation fails or any required field is missing/unknown: STOP.
- Do not use empty strings for required string fields (including citations). If required info is missing: STOP.
- You MUST run schema validation locally (in reasoning) before calling `store_block_governance`.
- If any field fails type/enum/shape requirements, **STOP** and report the schema errors.

Additional hard stops (binding):
- STOP if any entry from `macro_overview.data.global_constraints.availability_assumptions`
  is not present verbatim in `block_summary.non_negotiables`.
- STOP if any entry from `macro_overview.data.global_constraints.risk_constraints`
  is not present verbatim in `block_summary.key_risks_warnings`.
- STOP if any date in `macro_overview.data.global_constraints.planned_event_windows`
  is not represented in `events_constraints.events[]` with matching date, correct ISO week,
  and A/B/C type from `macro_overview.data.phases[].events_constraints`.
- STOP if `macro_overview.data.global_constraints.recovery_protection.notes` is not
  present verbatim in `execution_non_negotiables.recovery_protection_rules`.
- STOP if any `weekly_kj_bands` entry is outside the intersection defined by
  LoadEstimationSpec (Macro corridor ∩ Feasible band ∩ KPI band; and progression guardrails
  when present). If a band cannot be narrowed to this intersection, STOP and report infeasibility.

---

### EXAMPLE: BLOCK_GOVERNANCE (minimal valid)

```json
{
  "meta": {
    "artifact_type": "BLOCK_GOVERNANCE",
    "schema_id": "BlockGovernanceInterface",
    "schema_version": "1.0",
    "version": "1.0",
    "authority": "Binding",
    "owner_agent": "Meso-Architect",
    "run_id": "example_block_governance_2026_w04",
    "created_at": "2026-01-26T00:00:00Z",
    "scope": "Meso",
    "iso_week": "2026-04",
    "iso_week_range": "2026-04--2026-05",
    "temporal_scope": { "from": "2026-01-19", "to": "2026-02-01" },
    "trace_upstream": [
      { "artifact": "MACRO_OVERVIEW", "version": "1.0", "run_id": "macro_overview_2026_w04" }
    ],
    "trace_data": [],
    "trace_events": [],
    "notes": "Example only. Replace with real trace references."
  },
  "data": {
    "body_metadata": {
      "block_id": "P01",
      "block_type": "Base",
      "block_status": "Green",
      "change_type": "NEW",
      "derived_from": "macro_overview_2026_w04",
      "upstream_inputs": ["MACRO_OVERVIEW"]
    },
    "block_summary": {
      "primary_objective": "Establish base durability.",
      "secondary_objectives": [],
      "key_risks_warnings": ["Avoid excessive intensity density."],
      "non_negotiables": ["Fixed rest days preserved."]
    },
    "load_guardrails": {
      "weekly_kj_bands": [
        {
          "week": "2026-04",
          "band": { "min": 7000, "max": 8500, "notes": "Example band." }
        }
      ],
      "confidence_assumptions": {
        "kj_estimation_method": "AvgPower-based",
        "confidence": { "kj": "MED" },
        "ftp_watts_used": 250,
        "zone_model_version": "1.0"
      }
    },
    "allowed_forbidden_semantics": {
      "allowed_day_roles": ["ENDURANCE"],
      "allowed_intensity_domains": ["ENDURANCE_LOW"],
      "allowed_load_modalities": ["NONE"],
      "quality_density": {
        "max_quality_days_per_week": 1,
        "quality_intent": "Stabilization",
        "forbidden_patterns": ["Back-to-back quality days"]
      },
      "forbidden_day_roles": [],
      "forbidden_intensity_domains": ["VO2MAX"],
      "forbidden_load_modalities": []
    },
    "events_constraints": {
      "events": [],
      "logistics_time_constraints": {
        "travel_days": "None",
        "work_constraints": "None",
        "weather_or_indoor_constraints": "None"
      }
    },
    "execution_non_negotiables": {
      "recovery_protection_rules": "Protect recovery anchors.",
      "long_endurance_anchor_protection": "Keep long endurance anchor.",
      "minimum_recovery_opportunities": "At least 2 recovery days.",
      "no_catch_up_rule": "No catch-up sessions."
    },
    "escalation_change_control": {
      "warning_signals": ["Repeated missed recovery"],
      "required_response": {
        "micro_planner_must": ["Hold load"],
        "micro_planner_must_not": ["Add make-up load"],
        "meso_architect_decides": "Escalate to Macro-Planner"
      }
    },
    "explicit_forbidden_content": [
      "day-by-day plans",
      "workouts or interval prescriptions",
      "durations, zones (Z1-Z7), %FTP",
      "daily kJ targets",
      "numeric progression rules",
      "recommendations that effectively plan the micro level"
    ],
    "self_check": {
      "weekly_kj_bands_present": true,
      "max_quality_days_specified": true,
      "allowed_forbidden_enums_specified": true,
      "no_micro_planning_content": true,
      "header_includes_implements_iso_week_range_trace": true
    }
  }
}
```
