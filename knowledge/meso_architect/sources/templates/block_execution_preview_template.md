---
Type: Template
Template-For: BLOCK_EXECUTION_PREVIEW
Template-ID: BlockExecutionPreviewTemplate
Version: 1.0

Scope: Agent
Authority: Binding
Implements:
  Interface-ID: BlockExecutionPreviewInterface
  Version: 1.0

Owner-Agent: Meso-Architect
Dependencies:
  - Specification-ID: AgendaEnumSpec
    Version: 1.0
Notes: >
  Schema-aligned blueprint for BLOCK_EXECUTION_PREVIEW. Replace every <!--- FILL --->
  marker with concrete values before output. Derived strictly from the execution
  architecture (no workouts).
---

# Block Execution Preview Template (Envelope)

Use this JSON envelope shape for `BLOCK_EXECUTION_PREVIEW`. Fill all markers.
Traceability (binding): `data.traceability.derived_from` must include the
`block_execution_arch_*.json` filename.

```json
{
  "meta": {
    "artifact_type": "BLOCK_EXECUTION_PREVIEW",
    "schema_id": "BlockExecutionPreviewInterface",
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
    "block_intent_summary": {
      "block_type": "<!--- FILL --->",
      "primary_objective": "<!--- FILL --->",
      "non_negotiables": ["<!--- FILL --->"],
      "key_risks_warnings": ["<!--- FILL --->"]
    },
    "feel_overview": {
      "dominant_theme": "<!--- FILL --->",
      "intensity_handling_conceptual": "<!--- FILL --->",
      "recovery_protection_conceptual": "<!--- FILL --->"
    },
    "weekly_agenda_preview": [
      {
        "week": "<!--- FILL --->",
        "days": [
          { "day_of_week": "Mon", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Tue", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Wed", "day_role": "RECOVERY", "intensity_domain": "RECOVERY", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Fri", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Sat", "day_role": "QUALITY", "intensity_domain": "SST", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Sun", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "<!--- FILL --->" }
        ]
      },
      {
        "week": "<!--- FILL --->",
        "days": [
          { "day_of_week": "Mon", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Tue", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Wed", "day_role": "RECOVERY", "intensity_domain": "RECOVERY", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Fri", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Sat", "day_role": "QUALITY", "intensity_domain": "SST", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Sun", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "<!--- FILL --->" }
        ]
      },
      {
        "week": "<!--- FILL --->",
        "days": [
          { "day_of_week": "Mon", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Tue", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Wed", "day_role": "RECOVERY", "intensity_domain": "RECOVERY", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Fri", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Sat", "day_role": "QUALITY", "intensity_domain": "SST", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Sun", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "<!--- FILL --->" }
        ]
      },
      {
        "week": "<!--- FILL --->",
        "days": [
          { "day_of_week": "Mon", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Tue", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Wed", "day_role": "RECOVERY", "intensity_domain": "RECOVERY", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Fri", "day_role": "REST", "intensity_domain": "NONE", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Sat", "day_role": "QUALITY", "intensity_domain": "SST", "load_modality": "NONE", "notes": "<!--- FILL --->" },
          { "day_of_week": "Sun", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE", "notes": "<!--- FILL --->" }
        ]
      }
    ],
    "week_to_week_narrative": {
      "direction": "<!--- FILL --->",
      "what_will_not_change": "<!--- FILL --->",
      "what_is_flexible": "<!--- FILL --->"
    },
    "deviation_rules": ["<!--- FILL --->"],
    "traceability": {
      "derived_from": ["<!--- FILL block_execution_arch filename --->"],
      "conflict_resolution": ["<!--- FILL --->"]
    }
  }
}
```
