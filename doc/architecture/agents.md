---
Version: 1.0
Status: Updated
Last-Updated: 2026-05-14
Owner: Architecture
---
# Agents and Responsibilities

This document is the canonical registry of:
- top-level surfaces and persisted-artifact authorities
- internal specialist agents used by the CrewAI runtime
- the current planning/review/writer split for Season, Phase, Week, and Report

RPS now distinguishes between:
- surface agents/controllers that own a user-visible planning/report action
- internal specialists that draft, review, or serialize artifacts inside a CrewAI flow
- writer agents that own final envelope serialization only

## Top-Level Surfaces and Artifact Authorities

| Surface / authority | Purpose | Modes | Required inputs | Writes | Notes |
| --- | --- | --- | --- | --- | --- |
| Season‑Scenario‑Agent | Generate scenarios and scenario selection scaffolding. | CREATE_SEASON_SCENARIOS, CREATE_SEASON_SCENARIO_SELECTION | athlete_profile, planning_events, logistics, kpi_profile, availability, wellness (as required) | season_scenarios, season_scenario_selection | Advisory only; scenario cadence and phase shaping are informational inputs to Season‑Planner. |
| Season‑Planner | Create binding season plans and season→phase feed forward. | CREATE_SEASON_PLAN, CREATE_SEASON_PHASE_FEED_FORWARD | athlete_profile, planning_events, logistics, kpi_profile, availability, wellness, season_scenarios (optional), season_scenario_selection (optional), des_analysis_report (for feed forward) | season_plan, season_phase_feed_forward | Runs a planning crew, a review crew, then a writer stage before persistence. |
| Phase‑Architect | Produce binding phase governance, preview, and phase→week feed forward. | CREATE_PHASE_GUARDRAILS, CREATE_PHASE_STRUCTURE, CREATE_PHASE_PREVIEW, CREATE_PHASE_FEED_FORWARD | season_plan, availability, wellness, zone_model, planning_events, logistics, season_phase_feed_forward (optional) | phase_guardrails, phase_structure, phase_preview, phase_feed_forward | Runs a planning crew, a review crew, then a writer stage before persistence. |
| Week‑Planner | Produce a week plan within phase guardrails. | CREATE_WEEK_PLAN, REVISE_WEEK_PLAN | phase_guardrails, phase_structure, availability, wellness, zone_model, planning_events, logistics, week_plan (optional) | week_plan | Runs a planning crew, a review crew, then a writer stage before persistence. Revised week plan includes coach input. |
| Workout Export | Build Intervals export from week plan. | WORKOUT_EXPORT | week_plan | workout_export | Local deterministic export; posting happens in UI. |
| Performance‑Analyst | Create diagnostic performance reports. | CREATE_REPORT | activities_actual, activities_trend, wellness, season_plan (optional) | des_analysis_report | Diagnostic only. Runs planning/review/writer stages but does not own planning artefacts or governance changes. |
| Coach | Conversational coaching, bounded plan edits, scoped replans, and advisory triggers. | COACH_CHAT, COACH_PLAN_OPS | chat history, athlete context, selected-week plan context, current-week status snapshot | week_plan, intervals_workouts, des_analysis_report, season_phase_feed_forward, phase_feed_forward | Preview-first orchestration surface; triggers planner/report flows but is not a planning artefact author. |
| Workout Editor | Bounded chat-based edits for an existing week plan. | WEEK_PLAN_EDIT_CHAT | selected-week week_plan, chat history | week_plan, intervals_workouts | Narrow specialized surface; active Coach now reuses the same bounded edit patterns. |

## Internal Specialist Crews

### Season

| Crew | Agents | Purpose |
| --- | --- | --- |
| `season_planning` | `season_context_specialist`, `scenario_interpreter`, `event_priority_specialist`, `peak_window_specialist`, `macrocycle_architect`, `season_constraint_specialist`, `season_historical_context_specialist`, `season_kpi_guidance_specialist`, `season_load_corridor_specialist`, `season_progression_specialist`, `season_plan_manager` | Draft one internal `SeasonPlanBundle` or scenario-driven season planning state. |
| `season_review` | `season_plan_auditor`, `season_governance_auditor`, `season_constraints_reviewer`, `season_review_manager` | Approve, reject, or request bounded replan for season planning output. |
| `season_writer` | `season_artifact_writer` | Serialize only the final season artifact envelope. |

### Phase

| Crew | Agents | Purpose |
| --- | --- | --- |
| `phase_planning` | `phase_context_specialist`, `phase_guardrail_band_specialist`, `phase_execution_rules_specialist`, `phase_structure_specialist`, `phase_cadence_recovery_specialist`, `phase_intensity_distribution_specialist`, `phase_event_integration_specialist`, `phase_preview_synthesizer`, `phase_bundle_manager` | Draft one internal `PhaseBundle` for the selected exact phase range. |
| `phase_review` | `phase_constraint_auditor`, `phase_governance_auditor`, `phase_structure_reviewer`, `phase_preview_reviewer`, `phase_review_manager` | Approve, reject, or request bounded replan for phase planning output. |
| `phase_writer` | `phase_artifact_writer` | Serialize only the final phase artifact envelopes. |

### Week

| Crew | Agents | Purpose |
| --- | --- | --- |
| `week_planning` | `week_context_specialist`, `week_constraint_specialist`, `week_load_target_specialist`, `week_recommendation_specialist`, `week_revision_specialist`, `week_workout_authoring_specialist`, `week_plan_manager` | Draft one internal `WeekPlanBundle` or preview candidate. |
| `week_review` | `week_consistency_auditor`, `week_load_governance_reviewer`, `week_workout_syntax_reviewer`, `week_review_manager` | Approve, reject, or request bounded replan for week planning output. |
| `week_writer` | `week_artifact_writer` | Serialize only the final `WEEK_PLAN` envelope. |

### Report

| Crew | Agents | Purpose |
| --- | --- | --- |
| `report_planning` | `performance_context_specialist`, `des_diagnostic_specialist` | Build one advisory diagnostic bundle for a completed week. |
| `report_review` | `des_review_manager` | Approve, reject, or request bounded rework before report writing. |
| `report_writer` | `report_artifact_writer` | Serialize only the final advisory report envelope. |

### Conversational

| Crew | Agents | Purpose |
| --- | --- | --- |
| `coach_conversation` | `conversation_manager`, `week_context_specialist`, `week_recommendation_specialist`, `week_revision_specialist`, `pending_resolution_specialist` | Route one Coach turn and optionally create/apply bounded preview operations. |
| `workout_editor_conversation` | `conversation_manager`, `week_context_specialist`, `week_workout_authoring_specialist`, `week_revision_specialist`, `pending_resolution_specialist` | Route one Workout Editor turn and optionally create/apply bounded workout-edit previews. |

## Mode and Runtime Notes

- Modes are referenced by orchestrators and UI run scopes.
- Prompts are in [prompts/agents/*.md](prompts/agents/*.md).
- Static factual knowledge is mapped in `config/crewai/knowledge_sources.yaml`.
- Methodology and guidance now come from repo-local skills configured in `config/crewai/skills.yaml`.
- RPS uses a local one-method-skill-per-agent rule; crew-level skills are operational only.
- Prompt files are reduced to runtime-local scope and no longer act as the primary knowledge-delivery mechanism.
- CrewAI runtime now executes internal specialist roles for Season, Phase, Week, and Report. These sub-roles are not independent top-level artefact authorities.
- Outer Season, Phase, Week, Report, Feed-Forward, and Coach orchestration is wrapped in CrewAI Flows.
- Season, Phase, Week, and Report all use an explicit planning/review/writer staging model.
- CrewAI task execution policy is now explicit per task family via `config/crewai/task_policies.yaml`, including output mode and function guardrails.
- CrewAI shared and scoped memory policy is now explicit via `config/crewai/memory_policy.yaml`; memory remains assistive and must not replace artifact truth.
- Crew-level planning / agent-level reasoning / model routing policy is explicit in `config/crewai/runtime_profiles.yaml`.
- Coach turn execution now routes through a dedicated CrewAI Flow wrapper before falling back to the tool-driven chat turn, so explicit confirm/discard/status messages are first-class flow routes.
- Coach now consumes a dedicated `CURRENT_WEEK_STATUS_SNAPSHOT` for current-week actuals and plan-vs-actual status, while the planning snapshot keeps the last complete historical reference week for stable planning context.
- Flow/Crew runtime telemetry now uses a central CrewAI `BaseEventListener` adapter into per-run `events.jsonl`, with compact normalized crew/task/tool labels surfaced in Plan Hub, System Status, and System History.

## Related Docs

- CrewAI flow catalog: [doc/architecture/crewai_flows.md](crewai_flows.md)
- UI flows: [doc/ui/ui_spec.md](../ui/ui_spec.md)
- Orchestration flow: [doc/overview/artefact_flow.md](../overview/artefact_flow.md)
- Planning sequence: [doc/overview/how_to_plan.md](../overview/how_to_plan.md)
