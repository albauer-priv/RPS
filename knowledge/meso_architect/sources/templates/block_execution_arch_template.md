---
Type: Template
Template-For: BLOCK_EXECUTION_ARCH
Template-ID: BlockExecutionArchTemplate
Version: 1.0

Scope: Agent
Authority: Binding
Implements:
  Interface-ID: BlockExecutionArchInterface
  Version: 1.0

Owner-Agent: Meso-Architect
Dependencies:
  - Specification-ID: AgendaEnumSpec
    Version: 1.0
  - Specification-ID: LoadEstimationSpec
    Version: 1.0
Notes: >
  Schema-aligned blueprint for BLOCK_EXECUTION_ARCH. Replace every <!--- FILL --->
  marker with concrete values before output. Use macro constraints verbatim and
  mirror block_governance load ranges exactly.
---

# Block Execution Architecture Template (Envelope)

Use this JSON envelope shape for `BLOCK_EXECUTION_ARCH`. Fill all markers.
Macro constraint mapping (binding):
- Copy every `macro_overview.data.global_constraints.*` constraint verbatim into
  `data.upstream_intent.constraints` (availability, risk, planned windows, recovery notes).
- Set `data.execution_principles.recovery_protection.fixed_non_training_days` from
  `macro_overview.data.global_constraints.recovery_protection.fixed_rest_days`.
- Mirror `block_governance.data.load_guardrails.weekly_kj_bands` and
  `weekly_tss_bands` into `data.load_ranges` (same weeks, min/max, notes).
- Set `data.load_ranges.source` to the block_governance filename.

```json
{
  "meta": {
    "artifact_type": "BLOCK_EXECUTION_ARCH",
    "schema_id": "BlockExecutionArchInterface",
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
    "upstream_intent": {
      "block_type": "<!--- FILL --->",
      "primary_objective": "<!--- FILL --->",
      "block_status": "<!--- FILL --->",
      "non_negotiables": ["<!--- FILL --->"],
      "constraints": [
        "<!--- FILL macro constraints (verbatim; one entry per constraint) --->"
      ],
      "key_risks_warnings": ["<!--- FILL --->"]
    },
    "load_ranges": {
      "weekly_kj_bands": [
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL --->" } },
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL --->" } },
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL --->" } },
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL --->" } }
      ],
      "weekly_tss_bands": [
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL --->" } },
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL --->" } },
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL --->" } },
        { "week": "<!--- FILL --->", "band": { "min": 0, "max": 0, "notes": "<!--- FILL --->" } }
      ],
      "source": "<!--- FILL block_governance filename --->"
    },
    "execution_principles": {
      "load_intensity_handling": {
        "max_quality_days_per_week": 0,
        "quality_intent": "<!--- FILL --->",
        "allowed_intensity_domains": ["<!--- FILL --->"],
        "forbidden_intensity_domains": ["<!--- FILL OPTIONAL --->"],
        "load_modality_constraints": ["<!--- FILL --->"]
      },
      "recovery_protection": {
        "fixed_non_training_days": ["<!--- FILL --->"],
        "mandatory_recovery_spacing_rules": ["<!--- FILL --->"],
        "forbidden_sequences": ["<!--- FILL --->"],
        "long_endurance_anchor_protection": "<!--- FILL --->"
      },
      "consistency_over_optimization": {
        "statements": ["<!--- FILL --->"]
      }
    },
    "structural_building_blocks": {
      "allowed_day_roles": ["<!--- FILL --->"],
      "allowed_intensity_domains": ["<!--- FILL --->"],
      "allowed_load_modalities": ["<!--- FILL --->"]
    },
    "week_skeleton_logic": {
      "week_roles": {
        "week_1_role": "<!--- FILL --->",
        "week_2_role": "<!--- FILL --->",
        "week_3_role": "<!--- FILL --->",
        "week_4_role": "<!--- FILL --->",
        "allowed_role_set": ["Base Build", "Recovery", "Race", "Taper"]
      },
      "mandatory_elements": {
        "recovery_opportunities_min": 0,
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
      "forbidden_patterns": ["<!--- FILL --->"]
    },
    "adaptation_rules": ["<!--- FILL --->"],
    "relationships": {
      "guides": ["<!--- FILL block_governance filename --->"],
      "does_not_replace": ["<!--- FILL OPTIONAL --->"]
    },
    "self_check": {
      "block_status_respected": true,
      "four_week_range_covered": true,
      "week_roles_defined_for_all_weeks": true,
      "no_new_decision_introduced": true,
      "no_numeric_target_introduced": true,
      "no_kpi_gate_inferred": true
    }
  }
}
```
