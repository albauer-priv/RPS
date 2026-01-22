---
Type: Contract
Contract-Name: scenario__macro_contract
Version: 1.0
Scope: Agent
Authority: Informational
Owner: Governance
Parties:
  - Season-Scenario-Agent
  - Macro-Planner
Implements:
  Interface-ID: SeasonScenariosInterface
  Version: 1.0
---

# Scenario ↔ Macro Contract (Season Scenarios)

## 1) Purpose
Define the handoff between Season-Scenario-Agent and Macro-Planner for
scenario generation and selection. Season-Scenario output is advisory;
Macro-Planner retains binding decision authority.

## 2) Responsibilities
### Season-Scenario-Agent
- Produce exactly one `SEASON_SCENARIOS` artefact per run.
- When a scenario label is provided, also produce one `SEASON_SCENARIO_SELECTION` artefact.
- Use the Season Brief and KPI Profile as primary inputs.
- Provide three scenarios (A/B/C) with clear trade-offs.
- Do not create macro plans or governance decisions.

### Macro-Planner
- Load the latest `SEASON_SCENARIOS` artefact when available.
- Load the latest `SEASON_SCENARIO_SELECTION` when available and align planning to it.
- Use scenario content as advisory input only.
- Select one scenario (A/B/C) and proceed with `MACRO_OVERVIEW`.
- Do not treat scenario content as binding rules.

## 3) Output Authority
- `SEASON_SCENARIOS` is **Informational** authority.
- `SEASON_SCENARIO_SELECTION` is **Informational** authority.
- `MACRO_OVERVIEW` is **Binding** authority.

## 4) Required Fields
The `SEASON_SCENARIOS` artefact MUST include:
- `meta` envelope (SeasonScenariosInterface)
- `data.season_brief_ref`
- `data.kpi_profile_ref`
- `data.scenarios` with exactly three entries:
  - `scenario_id` in {A, B, C}
  - `name`, `core_idea`, `load_philosophy`, `risk_profile`,
    `key_differences`, `best_suited_if`, `scenario_guidance`

The `SEASON_SCENARIO_SELECTION` artefact MUST include:
- `meta` envelope (SeasonScenarioSelectionInterface)
- `data.season_scenarios_ref`
- `data.selected_scenario_id` (A|B|C)
- `data.selection_source` (`user` or `system`)

## 5) Handoff Rules
- Macro-Planner may request clarification if scenario content conflicts with
  Season Brief constraints or KPI Profile gates.
- If `SEASON_SCENARIOS` is missing, Macro-Planner may proceed using its own
  scenario generation rules.
- Scenario guidance (phase suggestions, deload cadence) is advisory and may be
  adjusted by Macro-Planner.
- Risk flags, event alignment, and intensity guidance are advisory and may be
  overridden by Macro-Planner.

## 6) Non-Goals
- No weekly planning, block design, or workout prescription.
- No KPI enforcement beyond referencing the selected KPI Profile.
