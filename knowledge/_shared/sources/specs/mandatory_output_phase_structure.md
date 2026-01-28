# Mandatory Output Chapter

Purpose
This chapter defines how to produce **schema‑valid PHASE_STRUCTURE JSON**.

---

## ARTIFACT: PHASE_STRUCTURE

### WHICH SCHEMA TO USE AND HOW TO FIND
- Schema: `phase_structure.schema.json`
  - Filter: `{"type":"eq","key":"schema_id","value":"phase_structure.schema.json"}`
- You MUST validate output against this schema before calling `store_phase_structure`.

### HOW TO FILL (BINDING)

#### 1) Envelope (top‑level)
- Output MUST be a **top‑level object** with only:
  - `meta`
  - `data`

#### 2) `meta` (required fields)
- Must satisfy `artefact_meta.schema.json`.
- Required constants:
  - `artifact_type`: `"PHASE_STRUCTURE"`
  - `schema_id`: `"PhaseStructureInterface"`
  - `schema_version`: `"1.0"`
  - `authority`: `"Binding"`
  - `owner_agent`: `"Meso-Architect"`
- `iso_week_range` required.
- `iso_week` MUST be the **first** ISO week in `iso_week_range`.
- `temporal_scope` MUST be copied from an upstream artefact (prefer stored PHASE_GUARDRAILS for
  the same range; otherwise use the Season Plan phase `date_range`). **Do NOT compute dates.**

#### 3) `data.upstream_intent`
Required:
- `block_type`, `primary_objective` (strings)
- `block_status`: `Green|Yellow|Red`
- `non_negotiables` (array, min 1)
- `constraints` (array, min 1)
- `key_risks_warnings` (array, min 1)

#### 3.1) Macro constraint propagation (binding)
Map macro constraints into `upstream_intent`:
- `upstream_intent.constraints` MUST include (verbatim) all of:
  - `season_plan.data.global_constraints.availability_assumptions`
  - `season_plan.data.global_constraints.risk_constraints`
  - `season_plan.data.global_constraints.planned_event_windows`
  - `season_plan.data.global_constraints.recovery_protection.notes`
- `upstream_intent.key_risks_warnings` MUST be copied from
  `phase_guardrails.block_summary.key_risks_warnings` (verbatim).

#### 4) `data.load_ranges`
Required:
- `weekly_kj_bands` (array of `{week, band}`)
- `source` (string; e.g., filename of phase_guardrails)

#### 4.1) Load range source (binding)
- `load_ranges.weekly_kj_bands` MUST be copied exactly from
  `phase_guardrails.load_guardrails.weekly_kj_bands` (same weeks, min/max, notes).
- `load_ranges.source` MUST be the stored phase guardrails filename:
  `phase_guardrails_YYYY-WW.json` (use the artifact version key, not the iso_week_range).
- `load_ranges` MUST NOT include any fields beyond `weekly_kj_bands` and `source`.

#### 5) `data.execution_principles`
Required:
- `load_intensity_handling` object:
  - `max_quality_days_per_week` (int)
  - `quality_intent` (`Stabilization|Build|Overload`)
  - `allowed_intensity_domains` (array)
  - `forbidden_intensity_domains` (array)
  - `load_modality_constraints` (array)
- `recovery_protection` object:
  - `mandatory_recovery_spacing_rules` (array, min 1)
  - `forbidden_sequences` (array, min 1)
  - `long_endurance_anchor_protection` (string)
  - `fixed_non_training_days` (array of weekdays)
- `consistency_over_optimization.statements` (array, min 1)

#### 6) `data.structural_building_blocks`
Required arrays:
- `allowed_day_roles`
- `allowed_intensity_domains`
- `allowed_load_modalities`

#### 7) `data.week_skeleton_logic`
Required:
- `week_roles`:
  - `week_roles` (array of `{week, role}`)
  - `allowed_role_set` (array)
- `mandatory_elements`:
  - `recovery_opportunities_min` (int)
  - `endurance_anchor_required` (bool)
- `optional_elements`:
  - `quality_days` object (`capped_by_upstream_limits`, `never_adjacent_unless_allowed`)
  - `optional_flex_days` object (`removable_without_compensation`)
- `forbidden_patterns` (array, min 1)

#### 7.1) Week role coverage (binding)
- `week_skeleton_logic.week_roles.week_roles` MUST cover every ISO week in `meta.iso_week_range`
  (no missing or extra weeks).

#### 8) `data.adaptation_rules`
- Array of strings (min 1)

#### 9) `data.relationships`
- `guides` (array, min 1)
- `does_not_replace` (array, min 1)

#### 10) `data.self_check`
All required booleans must be present and set to `true`:
- `block_status_respected`
- `block_range_covered`
- `week_roles_defined_for_block_range`
- `no_new_decision_introduced`
- `no_numeric_target_introduced`
- `no_kpi_gate_inferred`

#### 10.1) Recovery protection sourcing (binding)
- `execution_principles.recovery_protection.fixed_non_training_days` MUST be sourced from:
  1) `season_plan.data.global_constraints.recovery_protection.fixed_rest_days`, else
  2) parse weekday names from `availability_assumptions`.
  If none are specified upstream, set `fixed_non_training_days` to `[]` and add a constraint
  note stating none were specified.
- `execution_principles.recovery_protection.forbidden_sequences` MUST be non-empty.
  If none specified upstream, add:
  `"None specified upstream; do not introduce new forbidden sequences."`
- `execution_principles.recovery_protection.mandatory_recovery_spacing_rules` and
  `forbidden_sequences` must reflect any recovery protection notes in macro constraints.
  Do not invent new rules.

#### 11) Validation & Stop (Binding)
- Use the store tool with a top-level `{ "meta": ..., "data": ... }` envelope only.
- Do NOT output raw JSON in chat; only the store tool call is allowed.
- Do NOT include workouts, interval structures, %FTP targets, zones (Z1–Z7), or day‑by‑day kJ targets.
- Before output: confirm the Mandatory Output Chapter was read in full and followed exactly.
- Validate against `phase_structure.schema.json` before calling the store tool.
- If validation fails or any required field is missing/unknown: STOP.
- Do not use empty strings for required string fields (including citations). If required info is missing: STOP.
- Validate against schema before calling `store_phase_structure`.
- On any error: **STOP** and report schema errors.

Additional hard stops (binding):
- STOP if producing `PHASE_STRUCTURE` and `data.self_check.no_numeric_target_introduced`
  is missing or false.
- STOP if `load_ranges.source` is not exactly `phase_guardrails_YYYY-WW.json`
  (artifact version key, not iso_week_range).
- STOP if `week_skeleton_logic.week_roles.week_roles` is missing, empty, or does not
  match the number of ISO weeks in `meta.iso_week_range`.

---

### EXAMPLE: PHASE_STRUCTURE (minimal valid)

```json
{
  "meta": {
    "artifact_type": "PHASE_STRUCTURE",
    "schema_id": "PhaseStructureInterface",
    "schema_version": "1.0",
    "version": "1.0",
    "authority": "Binding",
    "owner_agent": "Meso-Architect",
    "run_id": "example_phase_structure_2026_w04",
    "created_at": "2026-01-26T00:00:00Z",
    "scope": "Meso",
    "iso_week": "2026-04",
    "iso_week_range": "2026-04--2026-05",
    "temporal_scope": { "from": "2026-01-19", "to": "2026-02-01" },
    "trace_upstream": [
      { "artifact": "PHASE_GUARDRAILS", "version": "1.0", "run_id": "phase_guardrails_2026_w04" }
    ],
    "trace_data": [],
    "trace_events": [],
    "notes": "Example only. Replace with real trace references."
  },
  "data": {
    "upstream_intent": {
      "block_type": "Base",
      "primary_objective": "Build durability",
      "block_status": "Green",
      "non_negotiables": ["Fixed rest days"],
      "constraints": ["No back-to-back quality"],
      "key_risks_warnings": ["Travel risk"]
    },
    "load_ranges": {
      "weekly_kj_bands": [
        { "week": "2026-04", "band": { "min": 7000, "max": 8500, "notes": "Example band." } }
      ],
      "source": "phase_guardrails_2026-04.json"
    },
    "execution_principles": {
      "load_intensity_handling": {
        "max_quality_days_per_week": 1,
        "quality_intent": "Stabilization",
        "allowed_intensity_domains": ["ENDURANCE_LOW"],
        "forbidden_intensity_domains": ["VO2MAX"],
        "load_modality_constraints": ["NONE"]
      },
      "recovery_protection": {
        "mandatory_recovery_spacing_rules": ["No quality on consecutive days"],
        "forbidden_sequences": ["Quality then quality"],
        "long_endurance_anchor_protection": "Preserve weekend long ride",
        "fixed_non_training_days": ["Mon", "Fri"]
      },
      "consistency_over_optimization": {
        "statements": ["Prefer repeatability over aggressive overload"]
      }
    },
    "structural_building_blocks": {
      "allowed_day_roles": ["ENDURANCE"],
      "allowed_intensity_domains": ["ENDURANCE_LOW"],
      "allowed_load_modalities": ["NONE"]
    },
    "week_skeleton_logic": {
      "week_roles": {
        "week_roles": [
          { "week": "2026-04", "role": "Build" }
        ],
        "allowed_role_set": ["Build", "Deload"]
      },
      "mandatory_elements": {
        "recovery_opportunities_min": 2,
        "endurance_anchor_required": true
      },
      "optional_elements": {
        "quality_days": {
          "capped_by_upstream_limits": true,
          "never_adjacent_unless_allowed": true
        },
        "optional_flex_days": {
          "removable_without_compensation": true
        }
      },
      "forbidden_patterns": ["Back-to-back quality days"]
    },
    "adaptation_rules": ["Reduce load if recovery signals worsen"],
    "relationships": {
      "guides": ["meso__micro_contract.md"],
      "does_not_replace": ["phase_guardrails"]
    },
    "self_check": {
      "block_status_respected": true,
      "block_range_covered": true,
      "week_roles_defined_for_block_range": true,
      "no_new_decision_introduced": true,
      "no_numeric_target_introduced": true,
      "no_kpi_gate_inferred": true
    }
  }
}
```
