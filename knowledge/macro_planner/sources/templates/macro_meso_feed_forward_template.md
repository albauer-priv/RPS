---
Type: Template
Template-For: MACRO_MESO_FEED_FORWARD
Template-ID: MacroMesoFeedForwardTemplate
Version: 1.0

Scope: Agent
Authority: Binding
Implements:
  Interface-ID: MacroMesoFeedForwardInterface
  Version: 1.0

Owner-Agent: Macro-Planner
Notes: >
  Schema-aligned blueprint for MACRO_MESO_FEED_FORWARD. Replace every <!--- FILL --->
  marker with concrete values before output.
---

# Macro Meso Feed Forward Template (Envelope)

```json
{
  "meta": {
    "artifact_type": "MACRO_MESO_FEED_FORWARD",
    "schema_id": "MacroMesoFeedForwardInterface",
    "schema_version": "1.0",
    "version": "1.0",
    "authority": "Binding",
    "owner_agent": "Macro-Planner",
    "run_id": "<!--- FILL --->",
    "created_at": "<!--- FILL --->",
    "scope": "Macro",
    "iso_week": "<!--- FILL --->",
    "iso_week_range": "<!--- FILL --->",
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
    "source_context": {
      "macro_overview_ref": "<!--- FILL --->",
      "des_analysis_report_ref": "<!--- FILL --->",
      "affected_block_id": "<!--- FILL --->"
    },
    "decision_summary": {
      "conclusion": "no_change",
      "rationale": ["<!--- FILL --->"]
    },
    "explicit_non_actions": [
      "No weekly workout changes",
      "No micro-level intervention",
      "No KPI threshold enforcement"
    ],
    "block_adjustment": {
      "applies_to_weeks": ["<!--- FILL --->"],
      "adjustments": {
        "kj_corridor": { "direction": "decrease", "percent": 0 },
        "quality_density": { "action": "restrict", "details": "<!--- FILL --->" }
      }
    }
  }
}
```
