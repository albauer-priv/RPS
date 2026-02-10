---
Type: Contract
Contract-Name: scenario__season_contract
Version: 1.1
Scope: Agent
Authority: Informational
Owner: Governance
Parties:
  - Season-Scenario-Agent
  - Season-Planner
Implements:
  Interface-ID: SeasonScenariosInterface
  Version: 1.0
---

# Scenario ↔ Season Contract (Season Scenarios)

## 1) Purpose
Define the handoff between Season-Scenario-Agent and Season-Planner for
scenario generation and selection. Season-Scenario output is advisory;
Season-Planner retains binding decision authority.

## 2) Responsibilities
### Season-Scenario-Agent
- Produce exactly one `SEASON_SCENARIOS` artefact per run.
- When a scenario label is provided, also produce one `SEASON_SCENARIO_SELECTION` artefact.
- Use the Athlete Profile and KPI Profile as primary inputs.
- Use the AVAILABILITY artefact (user-managed input) and fixed rest days.
  in scenario guidance (constraints summary and phase shaping).
- Provide three scenarios (A/B/C) with clear trade-offs.
- Do not create season plans or governance decisions.

### Season-Planner
- Load the latest `SEASON_SCENARIOS` artefact when available.
- Load the latest `SEASON_SCENARIO_SELECTION` when available and align planning to it.
- Use scenario content as advisory input only.
- Select one scenario (A/B/C) and proceed with `SEASON_PLAN`.
- Do not treat scenario content as binding rules.

## 3) Output Authority
- `SEASON_SCENARIOS` is **Informational** authority.
- `SEASON_SCENARIO_SELECTION` is **Informational** authority.
- `SEASON_PLAN` is **Binding** authority.

## 4) Required Fields
The `SEASON_SCENARIOS` artefact MUST include:
- `meta` envelope (SeasonScenariosInterface)
- `data.season_brief_ref` (legacy; populate from Athlete Profile ref)
- `data.kpi_profile_ref`
- `data.scenarios` with exactly three entries:
  - `scenario_id` in {A, B, C}
  - `name`, `core_idea`, `load_philosophy`, `risk_profile`,
    `key_differences`, `best_suited_if`, `scenario_guidance`
  - Scenario guidance planning math (advisory only):
    `phase_count_expected`, `max_shortened_phases`, `shortening_budget_weeks`
- `data.planning_horizon_weeks` must match the weeks implied by `meta.iso_week_range`.

The `SEASON_SCENARIO_SELECTION` artefact MUST include:
- `meta` envelope (SeasonScenarioSelectionInterface)
- `data.season_scenarios_ref`
- `data.selected_scenario_id` (A|B|C)
- `data.selection_source` (`user` or `system`)

## 5) Handoff Rules
- Season-Planner may request clarification if scenario content conflicts with
  Athlete Profile constraints or KPI Profile gates.
- If `SEASON_SCENARIOS` is missing, Season-Planner may proceed using its own
  scenario generation rules.
- Scenario guidance (phase suggestions, deload cadence) is advisory and may be
  adjusted by Season-Planner.
- If scenario guidance includes planning math fields, Season-Planner must
  compute its own phase count from the selected calendar range and cross-check.
- Risk flags, event alignment, and intensity guidance are advisory and may be
  overridden by Season-Planner.

## 6) Non-Goals
- No weekly planning, phase design, or workout prescription.
- No KPI enforcement beyond referencing the selected KPI Profile.
