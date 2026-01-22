---
Type: Template
Template-For: BLOCK_GOVERNANCE
Template-ID: BlockGovernanceTemplate
Version: 1.0

Scope: Agent
Authority: Binding
Implements:
  Interface-ID: BlockGovernanceInterface
  Version: 1.0

Owner-Agent: Meso-Architect
Dependencies:
  - Specification-ID: AgendaEnumSpec
    Version: 1.0
  - Specification-ID: LoadEstimationSpec
    Version: 1.0
Notes: >
  Schema-aligned blueprint for BLOCK_GOVERNANCE. Replace every <!--- FILL --->
  marker with concrete values before output. Placeholders may violate enums until replaced.
  Weekly kJ/TSS bands must reflect a progression pattern (e.g., 3:1 build/deload)
  and include intent notes per week.
---

# Block Governance Template (Envelope)

Use this JSON envelope shape for `BLOCK_GOVERNANCE`. Fill all markers.
Macro constraint mapping (binding):
- Copy every `macro_overview.data.global_constraints.availability_assumptions`
  string verbatim into `block_summary.non_negotiables`.
- Copy every `macro_overview.data.global_constraints.risk_constraints`
  string verbatim into `block_summary.key_risks_warnings`.
- Copy every `macro_overview.data.global_constraints.planned_event_windows`
  string verbatim into `block_summary.non_negotiables` (or embed verbatim in
  `events_constraints.events[].constraint` if you can map window/type).
- Copy every `macro_overview.data.global_constraints.recovery_protection.notes`
  string verbatim into `execution_non_negotiables.recovery_protection_rules`
  (along with any existing recovery rules).

```json
{
  "meta": {
    "artifact_type": "BLOCK_GOVERNANCE",
    "schema_id": "BlockGovernanceInterface",
    "schema_version": "1.0",
    "version": "1.0",
    "authority": "Binding",
    "owner_agent": "Meso-Architect",
    "run_id": "<!--- FILL --->",
    "created_at": "<!--- FILL --->",
    "scope": "Meso",
    "iso_week": "<!--- FILL --->",
    "iso_week_range": "<!--- FILL --->",
    "temporal_scope": {
      "from": "<!--- FILL --->",
      "to": "<!--- FILL --->"
    },
    "trace_upstream": [
      {
        "artifact": "<!--- FILL --->",
        "version": "<!--- FILL --->",
        "run_id": "<!--- FILL --->"
      }
    ],
    "trace_data": [],
    "trace_events": [],
    "notes": "<!--- FILL --->"
  },
  "data": {
    "body_metadata": {
      "block_id": "<!--- FILL --->",
      "block_type": "<!--- FILL --->",
      "block_status": "<!--- FILL --->",
      "change_type": "<!--- FILL --->",
      "derived_from": "<!--- FILL --->",
      "upstream_inputs": ["<!--- FILL --->"]
    },
    "block_summary": {
      "primary_objective": "<!--- FILL --->",
      "secondary_objectives": ["<!--- FILL --->"],
      "key_risks_warnings": [
        "<!--- FILL macro risk constraints (verbatim; one entry per constraint) --->",
        "<!--- FILL other risks --->"
      ],
      "non_negotiables": [
        "<!--- FILL macro availability assumptions (verbatim; one entry per assumption) --->",
        "<!--- FILL macro planned event windows (verbatim; one entry per window) --->",
        "<!--- FILL other non-negotiables --->"
      ]
    },
    "load_guardrails": {
      "weekly_kj_bands": [
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL build/progression notes --->" } },
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL build/progression notes --->" } },
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL peak/progression notes --->" } },
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL deload notes (lower than week 3) --->" } }
      ],
      "weekly_tss_bands": [
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL build/progression notes --->" } },
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL build/progression notes --->" } },
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL peak/progression notes --->" } },
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL deload notes (lower than week 3) --->" } }
      ],
      "confidence_assumptions": {
        "kj_estimation_method": "<!--- FILL --->",
        "confidence": { "kj": "<!--- FILL --->", "tss": "<!--- FILL --->" },
        "ftp_watts_used": 0,
        "zone_model_version": "<!--- FILL --->"
      }
    },
    "allowed_forbidden_semantics": {
      "allowed_day_roles": ["<!--- FILL --->"],
      "forbidden_day_roles": ["<!--- FILL OPTIONAL --->"],
      "allowed_intensity_domains": ["<!--- FILL --->"],
      "forbidden_intensity_domains": ["<!--- FILL OPTIONAL --->"],
      "allowed_load_modalities": ["<!--- FILL --->"],
      "forbidden_load_modalities": ["<!--- FILL OPTIONAL --->"],
      "quality_density": {
        "max_quality_days_per_week": 0,
        "quality_intent": "<!--- FILL --->",
        "forbidden_patterns": ["<!--- FILL OPTIONAL --->"]
      }
    },
    "events_constraints": {
      "events": [],
      "logistics_time_constraints": {
        "travel_days": "<!--- FILL --->",
        "work_constraints": "<!--- FILL --->",
        "weather_or_indoor_constraints": "<!--- FILL --->"
      }
    },
    "execution_non_negotiables": {
      "recovery_protection_rules": "<!--- FILL --->",
      "long_endurance_anchor_protection": "<!--- FILL --->",
      "minimum_recovery_opportunities": "<!--- FILL --->",
      "no_catch_up_rule": "<!--- FILL --->"
    },
    "escalation_change_control": {
      "warning_signals": ["<!--- FILL --->"],
      "required_response": {
        "micro_planner_must": ["<!--- FILL --->"],
        "micro_planner_must_not": ["<!--- FILL --->"],
        "meso_architect_decides": "<!--- FILL --->"
      }
    },
    "explicit_forbidden_content": [
      "day-by-day plans",
      "workouts or interval prescriptions",
      "durations, zones (Z1-Z7), %FTP",
      "daily kJ/TSS targets",
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
