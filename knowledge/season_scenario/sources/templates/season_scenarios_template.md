---
Type: Template
Template-For: SEASON_SCENARIOS
Template-ID: SeasonScenariosTemplate
Version: 1.0

Scope: Agent
Authority: Informational
Implements:
  Interface-ID: SeasonScenariosInterface
  Version: 1.0

Owner-Agent: Season-Scenario-Agent
Dependencies:
  - Specification-ID: SeasonBriefInterface
    Version: 1.0
Notes: >
  Schema-aligned blueprint for SEASON_SCENARIOS. Replace every <!--- FILL --->
  marker with concrete values before output.
---

# Season Scenarios Template (Envelope)

Use this JSON envelope shape for `SEASON_SCENARIOS`. Fill all markers.

```json
{
  "meta": {
    "artifact_type": "SEASON_SCENARIOS",
    "schema_id": "SeasonScenariosInterface",
    "schema_version": "1.0",
    "version": "1.0",
    "authority": "Informational",
    "owner_agent": "Season-Scenario-Agent",
    "run_id": "<!--- FILL --->",
    "created_at": "<!--- FILL --->",
    "scope": "Macro",
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
    "season_brief_ref": "<!--- FILL --->",
    "kpi_profile_ref": "<!--- FILL --->",
    "athlete_profile_ref": "<!--- FILL --->",
    "planning_horizon_weeks": 0,
    "scenarios": [
      {
        "scenario_id": "A",
        "name": "<!--- FILL --->",
        "core_idea": "<!--- FILL --->",
        "load_philosophy": "<!--- FILL --->",
        "risk_profile": "<!--- FILL --->",
        "key_differences": "<!--- FILL --->",
        "best_suited_if": "<!--- FILL --->",
        "scenario_guidance": {
          "deload_cadence": "<!--- FILL --->",
          "phase_length_weeks": 0,
          "phase_recommendations": [
            {
              "phase_id": "<!--- FILL --->",
              "name": "<!--- FILL --->",
              "cycle": "Base",
              "date_range": { "from": "<!--- FILL --->", "to": "<!--- FILL --->" },
              "iso_week_range": "<!--- FILL --->",
              "focus": "<!--- FILL --->",
              "load_trend": "build",
              "key_constraints": ["<!--- FILL --->"],
              "notes": ["<!--- FILL --->"]
            }
          ],
          "event_alignment_notes": ["<!--- FILL --->"],
          "risk_flags": ["<!--- FILL --->"],
          "fixed_rest_days": ["<!--- FILL --->"],
          "constraint_summary": ["<!--- FILL --->"],
          "kpi_guardrail_notes": ["<!--- FILL --->"],
          "decision_notes": ["<!--- FILL --->"],
          "intensity_guidance": {
            "allowed_domains": ["<!--- FILL --->"],
            "avoid_domains": ["<!--- FILL --->"]
          },
          "assumptions": ["<!--- FILL --->"],
          "unknowns": ["<!--- FILL --->"]
        }
      },
      {
        "scenario_id": "B",
        "name": "<!--- FILL --->",
        "core_idea": "<!--- FILL --->",
        "load_philosophy": "<!--- FILL --->",
        "risk_profile": "<!--- FILL --->",
        "key_differences": "<!--- FILL --->",
        "best_suited_if": "<!--- FILL --->",
        "scenario_guidance": {
          "deload_cadence": "<!--- FILL --->",
          "phase_length_weeks": 0,
          "phase_recommendations": [
            {
              "phase_id": "<!--- FILL --->",
              "name": "<!--- FILL --->",
              "cycle": "Base",
              "date_range": { "from": "<!--- FILL --->", "to": "<!--- FILL --->" },
              "iso_week_range": "<!--- FILL --->",
              "focus": "<!--- FILL --->",
              "load_trend": "build",
              "key_constraints": ["<!--- FILL --->"],
              "notes": ["<!--- FILL --->"]
            }
          ],
          "event_alignment_notes": ["<!--- FILL --->"],
          "risk_flags": ["<!--- FILL --->"],
          "fixed_rest_days": ["<!--- FILL --->"],
          "constraint_summary": ["<!--- FILL --->"],
          "kpi_guardrail_notes": ["<!--- FILL --->"],
          "decision_notes": ["<!--- FILL --->"],
          "intensity_guidance": {
            "allowed_domains": ["<!--- FILL --->"],
            "avoid_domains": ["<!--- FILL --->"]
          },
          "assumptions": ["<!--- FILL --->"],
          "unknowns": ["<!--- FILL --->"]
        }
      },
      {
        "scenario_id": "C",
        "name": "<!--- FILL --->",
        "core_idea": "<!--- FILL --->",
        "load_philosophy": "<!--- FILL --->",
        "risk_profile": "<!--- FILL --->",
        "key_differences": "<!--- FILL --->",
        "best_suited_if": "<!--- FILL --->",
        "scenario_guidance": {
          "deload_cadence": "<!--- FILL --->",
          "phase_length_weeks": 0,
          "phase_recommendations": [
            {
              "phase_id": "<!--- FILL --->",
              "name": "<!--- FILL --->",
              "cycle": "Base",
              "date_range": { "from": "<!--- FILL --->", "to": "<!--- FILL --->" },
              "iso_week_range": "<!--- FILL --->",
              "focus": "<!--- FILL --->",
              "load_trend": "build",
              "key_constraints": ["<!--- FILL --->"],
              "notes": ["<!--- FILL --->"]
            }
          ],
          "event_alignment_notes": ["<!--- FILL --->"],
          "risk_flags": ["<!--- FILL --->"],
          "fixed_rest_days": ["<!--- FILL --->"],
          "constraint_summary": ["<!--- FILL --->"],
          "kpi_guardrail_notes": ["<!--- FILL --->"],
          "decision_notes": ["<!--- FILL --->"],
          "intensity_guidance": {
            "allowed_domains": ["<!--- FILL --->"],
            "avoid_domains": ["<!--- FILL --->"]
          },
          "assumptions": ["<!--- FILL --->"],
          "unknowns": ["<!--- FILL --->"]
        }
      }
    ],
    "notes": ["<!--- FILL --->"]
  }
}
```
