---
Version: 1.0
Status: Updated
Last-Updated: 2026-02-03
Owner: Architecture
---
# Agents and Responsibilities

This document is the canonical registry of agents, their roles, modes, and artifact IO.

## Agent Registry

| Agent | Purpose | Modes | Required inputs | Writes | Notes |
| --- | --- | --- | --- | --- | --- |
| Season‑Scenario‑Agent | Generate scenarios and scenario selection scaffolding. | CREATE_SEASON_SCENARIOS, CREATE_SEASON_SCENARIO_SELECTION | season_brief, events, kpi_profile, availability, wellness (as required) | season_scenarios, season_scenario_selection | Uses KPI segment selection from UI. |
| Season‑Planner | Create season plan (weekly load corridors + phase outline). | CREATE_SEASON_PLAN | season_brief, events, kpi_profile, availability, wellness, season_scenarios (optional), season_scenario_selection (optional) | season_plan | Must follow LoadEstimationSpec. |
| Phase‑Architect | Produce phase guardrails, structure, and preview for a phase range. | CREATE_PHASE_GUARDRAILS, CREATE_PHASE_STRUCTURE, CREATE_PHASE_PREVIEW | season_plan, availability, wellness, zone_model, events, season_phase_feed_forward (optional) | phase_guardrails, phase_structure, phase_preview | Requires exact-range guardrails for structure; exact-range structure for preview. |
| Week‑Planner | Produce a week plan within phase guardrails. | CREATE_WEEK_PLAN, REVISE_WEEK_PLAN | phase_guardrails, phase_structure, availability, wellness, zone_model, week_plan (optional) | week_plan | Revised week plan includes coach input. |
| Workout‑Builder | Build Intervals export from week plan. | EXPORT_WORKOUTS | week_plan | intervals_workouts | Export only; posting happens in UI. |
| Performance‑Analyst | Create performance report and feed‑forward inputs. | CREATE_REPORT, FEED_FORWARD | activities_actual, activities_trend, wellness, season_plan (optional) | des_analysis_report, season_phase_feed_forward | Report is past-only. |
| Coach | Conversational coaching and guidance. | COACH_CHAT | chat history, athlete context | none (chat only) | UI chat surface; no artefact writes. |

## Mode Notes

- Modes are referenced by orchestrators and UI run scopes.
- Prompts are in `prompts/agents/*.md` and knowledge injection is configured in `config/agent_knowledge_injection.yaml`.

## Related Docs

- UI flows: `doc/ui/ui_spec.md`
- Orchestration flow: `doc/overview/artefact_flow.md`
- Planning sequence: `doc/overview/how_to_plan.md`
