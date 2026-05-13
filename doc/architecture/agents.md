---
Version: 1.0
Status: Updated
Last-Updated: 2026-05-12
Owner: Architecture
---
# Agents and Responsibilities

This document is the canonical registry of agents, their roles, modes, and artifact IO.

## Agent Registry

| Agent | Purpose | Modes | Required inputs | Writes | Notes |
| --- | --- | --- | --- | --- | --- |
| Season‑Scenario‑Agent | Generate scenarios and scenario selection scaffolding. | CREATE_SEASON_SCENARIOS, CREATE_SEASON_SCENARIO_SELECTION | athlete_profile, planning_events, logistics, kpi_profile, availability, wellness (as required) | season_scenarios, season_scenario_selection | Advisory only; scenario cadence and phase shaping are informational inputs to Season‑Planner. |
| Season‑Planner | Create binding season plans and season→phase feed forward. | CREATE_SEASON_PLAN, CREATE_SEASON_PHASE_FEED_FORWARD | athlete_profile, planning_events, logistics, kpi_profile, availability, wellness, season_scenarios (optional), season_scenario_selection (optional), des_analysis_report (for feed forward) | season_plan, season_phase_feed_forward | Binding planning authority for season cadence, macrocycle structure, and season-level phase adjustments. |
| Phase‑Architect | Produce binding phase governance, preview, and phase→week feed forward. | CREATE_PHASE_GUARDRAILS, CREATE_PHASE_STRUCTURE, CREATE_PHASE_PREVIEW, CREATE_PHASE_FEED_FORWARD | season_plan, availability, wellness, zone_model, planning_events, logistics, season_phase_feed_forward (optional) | phase_guardrails, phase_structure, phase_preview, phase_feed_forward | Applies season-selected cadence inside the exact phase range; may not redefine cadence defaults. |
| Week‑Planner | Produce a week plan within phase guardrails. | CREATE_WEEK_PLAN, REVISE_WEEK_PLAN | phase_guardrails, phase_structure, availability, wellness, zone_model, planning_events, logistics, week_plan (optional) | week_plan | Revised week plan includes coach input. |
| Workout Export | Build Intervals export from week plan. | WORKOUT_EXPORT | week_plan | workout_export | Local deterministic export; posting happens in UI. |
| Performance‑Analyst | Create diagnostic performance reports. | CREATE_REPORT | activities_actual, activities_trend, wellness, season_plan (optional) | des_analysis_report | Diagnostic only; may inform feed-forward flows but does not own planning artefacts or governance changes. |
| Coach | Conversational coaching, bounded plan edits, scoped replans, and advisory triggers. | COACH_CHAT, COACH_PLAN_OPS | chat history, athlete context, selected-week plan context, current-week status snapshot | week_plan, intervals_workouts, des_analysis_report, season_phase_feed_forward, phase_feed_forward | Preview-first orchestration surface; triggers planner/report flows but is not a planning artefact author. |
| Workout Editor | Bounded chat-based edits for an existing week plan. | WEEK_PLAN_EDIT_CHAT | selected-week week_plan, chat history | week_plan, intervals_workouts | Narrow specialized surface; active Coach now reuses the same bounded edit patterns. |

## Mode Notes

- Modes are referenced by orchestrators and UI run scopes.
- Prompts are in [prompts/agents/*.md](prompts/agents/*.md) and knowledge injection is configured in `config/agent_knowledge_injection.yaml`.
- CrewAI runtime now executes internal specialist roles for `Season-Planner` and `Phase-Architect`; these sub-roles are not independent top-level artefact authorities and only feed manager-authored persisted outputs.
- Season and Phase specialists now use dedicated prompt slices instead of reusing the top-level planner prompts.
- Outer Season and Phase orchestration is wrapped in CrewAI Flows; grouped Phase runs reuse one internal `PhaseBundle` before deterministic public artefact persistence.
- Outer Week, Report, and Feed-Forward orchestration now also uses CrewAI Flow wrappers.
- Coach turn execution now routes through a dedicated CrewAI Flow wrapper before falling back to the tool-driven chat turn, so explicit confirm/discard/status messages are first-class flow routes.
- Coach now consumes a dedicated `CURRENT_WEEK_STATUS_SNAPSHOT` for current-week actuals and plan-vs-actual status, while the planning snapshot keeps the last complete historical reference week for stable planning context.
- Season and Phase specialist work now runs inside one hierarchical CrewAI crew per run instead of repeated one-task crew executions.
- Flow/Crew runtime telemetry now uses a central CrewAI `BaseEventListener` adapter into per-run `events.jsonl`, with compact normalized crew/task/tool labels surfaced in Plan Hub, System Status, and System History.

## Related Docs

- UI flows: [doc/ui/ui_spec.md](../ui/ui_spec.md)
- Orchestration flow: [doc/overview/artefact_flow.md](../overview/artefact_flow.md)
- Planning sequence: [doc/overview/how_to_plan.md](../overview/how_to_plan.md)
