---
Type: Template
Template-For: SEASON_SCENARIO_SELECTION
Template-ID: SeasonScenarioSelectionTemplate
Version: 1.0

Scope: Agent
Authority: Informational
Implements:
  Interface-ID: SeasonScenarioSelectionInterface
  Version: 1.0

Owner-Agent: Season-Scenario-Agent
Dependencies:
  - Specification-ID: SeasonScenariosInterface
    Version: 1.0
Notes: >
  Schema-aligned blueprint for SEASON_SCENARIO_SELECTION. Replace every <!--- FILL --->
  marker with concrete values before output.
---

# Season Scenario Selection Template (Envelope)

Use this JSON envelope shape for `SEASON_SCENARIO_SELECTION`. Fill all markers.

```json
{
  "meta": {
    "artifact_type": "SEASON_SCENARIO_SELECTION",
    "schema_id": "SeasonScenarioSelectionInterface",
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
    "season_scenarios_ref": "<!--- FILL --->",
    "selected_scenario_id": "A",
    "selection_source": "user",
    "selection_rationale": "<!--- FILL --->",
    "notes": ["<!--- FILL --->"]
  }
}
```
