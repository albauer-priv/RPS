---
Type: InterfaceSpecification
Interface-ID: SeasonScenariosInterface
Version: 1.0
Scope: Agent
Authority: Informational
Owner: Governance
---

# Season Scenarios Interface Spec

## Purpose
Define the required structure for the `SEASON_SCENARIOS` artefact used to
capture three season planning scenarios for user selection.

## Required Structure
The artefact MUST be a JSON envelope with `meta` and `data` fields.

### meta (ArtefactMeta)
Must include:
- `artifact_type`: `SEASON_SCENARIOS`
- `schema_id`: `SeasonScenariosInterface`
- `schema_version`: `1.0`
- `version`
- `authority`: `Informational`
- `owner_agent`: `Season-Scenario-Agent`
- `run_id`, `created_at`, `scope`, `iso_week`, `iso_week_range`,
  `temporal_scope`, `trace_upstream`, `trace_data`, `trace_events`, `notes`

### data
Required fields:
- `season_brief_ref` (legacy; populate with Athlete Profile run_id/version key)
- `kpi_profile_ref` (string)
- `scenarios` (array of exactly three scenario objects)

Optional fields:
- `athlete_profile_ref` (string; preferred canonical reference)
- `planning_horizon_weeks` (integer)
- `notes` (array of strings)

`planning_horizon_weeks` MUST match the total weeks covered by `meta.iso_week_range`
(inclusive). Derive it from `iso_week_range` if needed.

#### Scenario object
Each scenario MUST include:
- `scenario_id`: `A`, `B`, or `C`
- `name`
- `core_idea`
- `load_philosophy`
- `risk_profile`
- `key_differences`
- `best_suited_if`
 - `scenario_guidance` (see below)

#### Scenario guidance (required)
Each scenario MUST include `scenario_guidance` with:
- `deload_cadence` (e.g., `3:1`, `2:1`, `2:1:1`)
- `phase_length_weeks` (integer)
- Planning math (advisory only):
  - `phase_count_expected` (integer; computed from planning horizon weeks)
  - `max_shortened_phases` (integer; default advisory cap)
  - `shortening_budget_weeks` (integer; total weeks that may be shortened)
- `phase_plan_summary` (object)
  - `full_phases` (integer)
  - `shortened_phases` (array of `{ len, count }`)
- `event_alignment_notes` (array)
- `risk_flags` (array)
- `fixed_rest_days` (array)
- `constraint_summary` (array)
- `kpi_guardrail_notes` (array)
- `decision_notes` (array)
- `intensity_guidance` with `allowed_domains` and `avoid_domains` (arrays)
- `assumptions` (array)
- `unknowns` (array)

## Authority Notes
`SEASON_SCENARIOS` is **informational**; Season-Planner must treat it as advisory
input only. Binding decisions are made in `SEASON_PLAN`.
