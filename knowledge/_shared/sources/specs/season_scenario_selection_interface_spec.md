---
Type: InterfaceSpecification
Interface-ID: SeasonScenarioSelectionInterface
Version: 1.0
Scope: Agent
Authority: Informational
Owner: Governance
---

# Season Scenario Selection Interface Spec

## Purpose
Define the required structure for `SEASON_SCENARIO_SELECTION` capturing the
user-chosen scenario (A/B/C) derived from `SEASON_SCENARIOS`.

## Required Structure
The artefact MUST be a JSON envelope with `meta` and `data` fields.

### meta (ArtefactMeta)
Must include:
- `artifact_type`: `SEASON_SCENARIO_SELECTION`
- `schema_id`: `SeasonScenarioSelectionInterface`
- `schema_version`: `1.0`
- `version`
- `authority`: `Informational`
- `owner_agent`: `Season-Scenario-Agent`
- `run_id`, `created_at`, `scope`, `iso_week`, `iso_week_range`,
  `temporal_scope`, `trace_upstream`, `trace_data`, `trace_events`, `notes`

### data
Required fields:
- `season_scenarios_ref` (string)
- `selected_scenario_id` (A|B|C)
- `selection_source` (`user` or `system`)

Optional fields:
- `selection_rationale` (string)
- `notes` (array of strings)

## Authority Notes
`SEASON_SCENARIO_SELECTION` is informational; Macro-Planner remains binding.
