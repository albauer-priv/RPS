---
Version: 1.1
Status: Updated
Last-Updated: 2026-05-27
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

## Reading Guide

Third parties should read the runtime in this order:

1. Top-level surfaces and artifact authorities
2. Crew-level planning/review/writer stages
3. Agent-to-task mapping
4. Skills and knowledge bundles

This keeps the distinction clear between:
- who owns a user-visible action
- which crew performs the internal work
- which specialist agent executes a concrete task
- which skill and knowledge sources guide that agent

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

## Crew Stage Map

This table answers the question "which crew takes over which part of planning?"

| Domain | Crew | Stage | Internal purpose | Main tasks | Main result |
| --- | --- | --- | --- | --- | --- |
| Conversation | `coach_conversation` | Route / operate | Route one user turn and execute bounded preview/apply operations | `classify_turn`, `finalize_reply`, `coach_preview_*`, `coach_apply_*`, `resolve_pending_operation` | reply, preview, or confirmed bounded change |
| Evidence | `evidence_curation` | Curate / gate-ready | Convert one verified source package into an RPS-specific structured brief before activation | `evidence_curate_source` | typed evidence curation payload for deterministic quality gate + activation |
| Season scenarios | none, single-agent persisted task | Direct write | Generate advisory scenario alternatives | `season_scenarios` | `SEASON_SCENARIOS` |
| Season | `season_planning` | Planning | Build internal season planning bundle from context, scenario intent, event anchors, constraints, KPI, and load logic | `season_context_read`, `season_scenario_interpretation`, `season_event_priority_review`, `season_peak_window_review`, `season_macrocycle_draft`, `season_constraint_review`, `season_historical_context_review`, `season_kpi_guidance_review`, `season_load_corridor_draft`, `season_progression_review`, `season_plan_finalize` | internal `SeasonPlanBundle` |
| Season | `season_review` | Review | Audit season planning bundle for authority, governance, and constraint compliance | `season_governance_review`, `season_constraints_review`, `season_plan_audit`, `season_review` | approve / reject / bounded replan |
| Season | `season_writer` | Writer | Serialize approved season outputs only | `season_plan`, `season_phase_feed_forward` | persisted season artefacts |
| Phase | `phase_planning` | Planning | Convert season governance into phase guardrails, structure, and preview | `phase_context_read`, `phase_guardrail_band_draft`, `phase_execution_rules_draft`, `phase_structure_draft`, `phase_cadence_recovery_draft`, `phase_intensity_distribution_draft`, `phase_event_integration_draft`, `phase_preview_draft`, `phase_bundle_finalize` | internal Phase draft bundle, then Python-normalized `PhaseBundle` |
| Phase | `phase_review` | Review | Audit phase bundle for constraints, load governance, structure, and preview correctness | `phase_constraint_audit`, `phase_governance_review`, `phase_structure_review`, `phase_preview_review`, `phase_review` | approve / reject / bounded replan |
| Phase | `phase_writer` | Writer | Serialize approved phase outputs only | `phase_guardrails`, `phase_structure`, `phase_preview`, `phase_feed_forward` | persisted phase artefacts |
| Week | `week_planning` | Planning | Convert week context and phase authority into a concrete week candidate | `week_context_read`, `week_constraint_review`, `week_load_target_draft`, `week_revision_draft`, `week_workout_text_draft`, `week_plan_finalize` | internal `WeekPlanBundle` |
| Week | `week_review` | Review | Audit week candidate for coherence, corridor compliance, and workout syntax safety | `week_consistency_review`, `week_load_governance_review`, `week_workout_syntax_review`, `week_review` | approve / reject / bounded replan |
| Week | `week_writer` | Writer | Serialize approved week output only | `week_plan` | persisted `WEEK_PLAN` |
| Report | `report_planning` | Planning | Build advisory diagnostic bundle for a completed week | `report_context_read`, `des_diagnostic_draft` | internal DES analysis bundle |
| Report | `report_review` | Review | Approve or reject advisory diagnostic output | `report_review` | approve / reject / bounded rework |
| Report | `report_writer` | Writer | Serialize approved advisory report only | `des_analysis_report` | persisted `DES_ANALYSIS_REPORT` |

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
| `phase_planning` | `phase_context_specialist`, `phase_guardrail_band_specialist`, `phase_execution_rules_specialist`, `phase_structure_specialist`, `phase_cadence_recovery_specialist`, `phase_intensity_distribution_specialist`, `phase_event_integration_specialist`, `phase_preview_synthesizer`, `phase_bundle_manager` | Draft one internal Phase bundle for the selected exact phase range, then normalize it in Python before review/writer handoff. |
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

## Agent, Task, Goal, and Skill Map

This is the main system table for answering:
- which agents belong to which crew
- which concrete task each agent runs
- what the agent is supposed to achieve
- which skill package supplies the method

| Domain | Crew | Agent | Role in crew | Task(s) executed | Goal / responsibility | Primary skill |
| --- | --- | --- | --- | --- | --- | --- |
| Conversation | `coach_conversation` | `conversation_manager` | Router / finalizer | `classify_turn`, `finalize_reply` | classify one turn, choose the right specialist path, and produce one final answer without domain rewriting | `skills/conversation/routing-and-finalization` |
| Conversation | `coach_conversation` | `coach` | Preview/apply operations surface | `coach_read_context`, `coach_preview_artifact_edit`, `coach_apply_artifact_edit`, `coach_preview_scoped_replan`, `coach_apply_scoped_replan`, `coach_preview_report`, `coach_apply_report`, `coach_preview_feed_forward`, `coach_apply_feed_forward` | safely execute bounded operations and planner/report triggers behind preview-first semantics | `skills/conversation/guarded-operations` |
| Conversation | `coach_conversation` | `pending_resolution_specialist` | Pending lifecycle handler | `resolve_pending_operation` | inspect, apply, or discard one existing pending preview | `skills/conversation/pending-resolution` |
| Season scenarios | direct task | `season_scenario` | Advisory generator | `season_scenarios` | produce exactly the advisory scenario artefact for the active horizon | `skills/season/scenario-generation` |
| Season | `season_planning` | `season_context_specialist` | Context reader | `season_context_read` | summarize authoritative season context and upstream state | `skills/season/context-analysis` |
| Season | `season_planning` | `scenario_interpreter` | Scenario translator | `season_scenario_interpretation` | convert selected scenario into season planning intent without making it binding by itself | `skills/season/scenario-interpretation` |
| Season | `season_planning` | `event_priority_specialist` | Event anchor specialist | `season_event_priority_review` | define A/B/C priorities and event anchors | `skills/season/event-priority-anchoring` |
| Season | `season_planning` | `peak_window_specialist` | Peak/taper specialist | `season_peak_window_review` | define peak windows, taper placement, and event clustering logic | `skills/season/macrocycle-architecture` |
| Season | `season_planning` | `macrocycle_architect` | Reverse planner | `season_macrocycle_draft` | build one or more target macrocycles backward from priority A-events or peak clusters | `skills/season/macrocycle-architecture` |
| Season | `season_planning` | `season_constraint_specialist` | Constraint synthesizer | `season_constraint_review` | preserve athlete, availability, logistics, and event constraints in season governance | `skills/season/constraint-synthesis` |
| Season | `season_planning` | `season_historical_context_specialist` | Historical interpreter | `season_historical_context_review` | ground season planning in recent load, tolerance, and recovery evidence | `skills/season/historical-context` |
| Season | `season_planning` | `season_kpi_guidance_specialist` | KPI interpreter | `season_kpi_guidance_review` | align season logic with KPI profile guidance | `skills/season/kpi-guidance` |
| Season | `season_planning` | `season_load_corridor_specialist` | Corridor specialist | `season_load_corridor_draft` | derive season corridor logic and realism checks | `skills/season/load-governance` |
| Season | `season_planning` | `season_progression_specialist` | Progression specialist | `season_progression_review` | translate overload, deload, and cadence rules into season progression guidance | `skills/season/load-governance` |
| Season | `season_planning` | `season_plan_manager` | Planning synthesizer | `season_plan_finalize` | consolidate all season drafts into one internal season bundle that may contain one or more target macrocycles | `skills/season/plan-synthesis` |
| Season | `season_review` | `season_governance_auditor` | Governance reviewer | `season_governance_review` | verify realism and progression compliance | `skills/season/governance-review` |
| Season | `season_review` | `season_constraints_reviewer` | Constraint reviewer | `season_constraints_review` | verify athlete, event, and logistics compliance | `skills/season/constraint-synthesis` |
| Season | `season_review` | `season_plan_auditor` | Authority auditor | `season_plan_audit` | verify macrocycle coherence and authority consistency | `skills/season/audit` |
| Season | `season_review` | `season_review_manager` | Review decider | `season_review` | integrate review outputs and decide approve, reject, or bounded replan | `skills/season/review-decision` |
| Season | `season_writer` | `season_artifact_writer` | Artefact serializer | `season_plan`, `season_phase_feed_forward` | emit final season-level artefact envelopes only | `skills/season/artifact-writing` |
| Season | feed-forward path | `season_feed_forward_manager` | Feed-forward authority | indirect feed-forward orchestration | convert completed-week evidence into season-to-phase guidance | `skills/season/feed-forward` |
| Phase | `phase_planning` | `phase_context_specialist` | Context reader | `phase_context_read` | summarize exact phase-range authority and upstream context | `skills/phase/context-analysis` |
| Phase | `phase_planning` | `phase_guardrail_band_specialist` | Band author | `phase_guardrail_band_draft` | derive weekly load bands for the exact phase range | `skills/phase/guardrails-authoring` |
| Phase | `phase_planning` | `phase_execution_rules_specialist` | Semantics author | `phase_execution_rules_draft` | define allowed/forbidden semantics and non-negotiables | `skills/phase/execution-rules` |
| Phase | `phase_planning` | `phase_structure_specialist` | Structure author | `phase_structure_draft` | define week roles and skeleton logic | `skills/phase/structure-authoring` |
| Phase | `phase_planning` | `phase_cadence_recovery_specialist` | Cadence applicator | `phase_cadence_recovery_draft` | apply season cadence and recovery rhythm to the phase | `skills/phase/cadence-recovery` |
| Phase | `phase_planning` | `phase_intensity_distribution_specialist` | Intensity specialist | `phase_intensity_distribution_draft` | shape phase intensity handling and density inside guardrails | `skills/phase/intensity-distribution` |
| Phase | `phase_planning` | `phase_event_integration_specialist` | Event propagation specialist | `phase_event_integration_draft` | integrate B/C event implications into phase structure | `skills/phase/event-integration` |
| Phase | `phase_planning` | `phase_preview_synthesizer` | Preview author | `phase_preview_draft` | produce a preview-only narrative with no new planning decisions | `skills/phase/preview-synthesis` |
| Phase | `phase_planning` | `phase_bundle_manager` | Planning synthesizer | `phase_bundle_finalize` | consolidate all phase drafts into one internal Phase draft bundle | `skills/phase/bundle-synthesis` |
| Phase | `phase_review` | `phase_constraint_auditor` | Constraint auditor | `phase_constraint_audit` | check availability, logistics, events, and feed-forward consistency | `skills/phase/constraint-audit` |
| Phase | `phase_review` | `phase_governance_auditor` | Load-governance auditor | `phase_governance_review` | check corridor coherence, durability-first policy, and compression risk | `skills/phase/load-governance-audit` |
| Phase | `phase_review` | `phase_structure_reviewer` | Structure reviewer | `phase_structure_review` | check consistency across structure, cadence, guardrails, and event integration | `skills/phase/structure-review` |
| Phase | `phase_review` | `phase_preview_reviewer` | Preview reviewer | `phase_preview_review` | ensure preview remains purely derived | `skills/phase/preview-review` |
| Phase | `phase_review` | `phase_review_manager` | Review decider | `phase_review` | integrate phase reviews and decide approve, reject, or bounded replan | `skills/phase/review-decision` |
| Phase | `phase_writer` | `phase_artifact_writer` | Artefact serializer | `phase_guardrails`, `phase_structure`, `phase_preview`, `phase_feed_forward` | emit final phase-level artefact envelopes only | `skills/phase/artifact-writing` |
| Phase | feed-forward path | `phase_feed_forward_manager` | Feed-forward authority | indirect feed-forward orchestration | convert completed-week evidence into phase guidance | `skills/phase/feed-forward` |
| Week | `week_planning` | `week_context_specialist` | Context reader | `analyze_week_context`, `week_context_read` | inspect selected-week plan, actuals, and constraints | `skills/week/context-analysis` |
| Week | `week_planning` | `week_constraint_specialist` | Constraint interpreter | `week_constraint_review` | summarize binding week constraints from upstream artefacts | `skills/week/constraint-analysis` |
| Week | `week_planning` | `week_recommendation_specialist` | Advisory / intent specialist | `form_coaching_recommendation`, `form_adjustment_intent` | turn context into coaching advice or a clean adjustment intent | `skills/week/recommendation-and-adjustment` |
| Week | `week_planning` | `week_load_target_specialist` | Corridor-to-target translator | `week_load_target_draft` | convert corridor into day and workout target logic | `skills/week/load-estimation-week` |
| Week | `week_planning` | `week_revision_specialist` | Week candidate author | `create_week_preview`, `week_revision_draft` | build a bounded preview or candidate week revision | `skills/week/revision-methodology` |
| Week | `week_planning` | `week_workout_authoring_specialist` | Workout construction author | `week_workout_text_draft` | build valid workout construction and syntax | `skills/week/workout-construction` |
| Week | `week_planning` | `week_plan_manager` | Planning synthesizer | `week_plan_finalize` | consolidate week drafts into one internal `WeekPlanBundle` | `skills/week/plan-synthesis` |
| Week | `week_review` | `week_consistency_auditor` | Consistency reviewer | `week_consistency_review` | verify role, duration, and load coherence | `skills/week/consistency-audit` |
| Week | `week_review` | `week_load_governance_reviewer` | Corridor reviewer | `week_load_governance_review` | verify corridor compliance and reconciliation behavior | `skills/week/load-governance-review` |
| Week | `week_review` | `week_workout_syntax_reviewer` | Syntax reviewer | `week_workout_syntax_review` | verify syntax subset and export safety | `skills/week/workout-syntax-review` |
| Week | `week_review` | `week_review_manager` | Review decider | `week_review` | integrate week reviews and decide approve, reject, or bounded replan | `skills/week/review-decision` |
| Week | `week_writer` | `week_artifact_writer` | Artefact serializer | `week_plan` | emit final `WEEK_PLAN` envelope only | `skills/week/artifact-writing` |
| Report | `report_planning` | `performance_context_specialist` | Context reader | `report_context_read` | summarize report-week context and diagnostic inputs | `skills/report/context-analysis` |
| Report | `report_planning` | `des_diagnostic_specialist` | Diagnostic specialist | `des_diagnostic_draft` | produce advisory DES findings for the selected week | `skills/report/analysis-methodology` |
| Report | `report_review` | `des_review_manager` | Review decider | `report_review` | approve, reject, or request bounded rework | `skills/report/review-decision` |
| Report | `report_writer` | `report_artifact_writer` | Artefact serializer | `des_analysis_report` | emit final DES report envelope only | `skills/report/artifact-writing` |

## Shared Skills and Knowledge

These mappings explain what is reused across crews beyond each agent's primary method skill.

### Shared Crew-Level Skills

| Crew family | Shared skills | Why they are attached |
| --- | --- | --- |
| `*_planning` | `skills/shared/runtime-boundaries`, `skills/shared/resolved-context-consumption`, `skills/shared/traceability-and-naming` | planning agents must stay inside authority boundaries, consume resolved orchestrator context first, and emit traceable output |
| `*_review` | `skills/shared/runtime-boundaries`, `skills/shared/traceability-and-naming`, `skills/shared/replan-instruction-authoring` | reviewers must reject or request bounded rework without inventing new planning authority |
| `*_writer` | `skills/shared/runtime-boundaries`, `skills/shared/traceability-and-naming` | writers serialize only final schema-compliant envelopes |
| `coach_conversation` and `workout_editor_conversation` | `skills/shared/runtime-boundaries`, `skills/shared/resolved-context-consumption`, `skills/shared/traceability-and-naming` | conversational operations still obey the same planning safety model |

### Shared Knowledge Bundles

| Bundle | Contents | Used for |
| --- | --- | --- |
| `factual_interfaces` | canonical interface specs for athlete profile, planning events, logistics, availability, wellness, season scenarios, scenario selection | artefact contract truth and field semantics |
| `factual_evidence` | canonical local evidence library manifest plus generated core/applied reference tables | evidence-backed planning and review rationale with fail-closed locator handling |
| `factual_week_refs` | workout JSON spec, workout syntax and validation, Intervals workout EBNF | week planning, workout authoring, syntax review, export safety |

### Crew-to-Knowledge Map

| Crew | Bundles | Interpretation |
| --- | --- | --- |
| `season_planning`, `phase_planning`, `report_planning` | `factual_interfaces`, `factual_evidence` | planning specialists work from contracts plus evidence |
| `week_planning` | `factual_interfaces`, `factual_evidence`, `factual_week_refs` | week specialists additionally need workout/export rules |
| `season_review`, `phase_review`, `report_review` | `factual_interfaces`, `factual_evidence` | reviewers audit against contracts and evidence-backed methodology |
| `week_review` | `factual_interfaces`, `factual_week_refs` | week review focuses on contracts and export-safe syntax |
| `season_writer`, `phase_writer`, `report_writer` | `factual_interfaces` | writers need contract truth, not broad evidence |
| `week_writer` | `factual_interfaces`, `factual_week_refs` | week writer needs both envelope and workout/export constraints |
| `coach_conversation` | `factual_interfaces`, `factual_evidence` | coaching needs planning contracts and evidence-backed framing |
| `workout_editor_conversation` | `factual_interfaces`, `factual_evidence`, `factual_week_refs` | workout editing additionally needs syntax constraints |

## Architectural Notes and Current Gaps

| Topic | Current design note |
| --- | --- |
| Evidence curation | Weekly literature refresh now separates bibliographic verification from content readiness: verified sources pass through a dedicated CrewAI evidence-curation task, then deterministic quality-gate and activation logic before they appear in operative evidence surfaces. |
| Crew definition source | The canonical crew stage groupings are defined in `src/rps/agents/crewai_task_execution.py` via task tuples such as `_SEASON_PLANNING_TASKS`, `_PHASE_REVIEW_TASKS`, and `_WEEK_PLANNING_TASKS` (moved from `crewai_backend.py` in ADR-060 Phase 6). |
| Outer orchestration | Season, Phase, Week, Report, Feed-Forward, and Coach are wrapped by outer flows in `src/rps/crewai_runtime/flows.py`. |
| Skill attachment model | One primary method skill is attached per agent; crew-level skills are operational and cross-cutting, not domain-method replacements. |
| Writer discipline | Writer agents do not re-plan. They serialize the approved result into the final artifact envelope only. |
| Review discipline | Review crews do not own final artifacts. They only approve, reject, or request bounded replan. |
| Scenario selection routing | `CREATE_SEASON_SCENARIO_SELECTION` uses the dedicated `season_scenario_selection` persisted-artifact task blueprint and `season_scenario_selection_shape` guardrail; it must emit only the selected scenario envelope and must not include Season/Phase/Week planning payloads. |
| Deterministic load context | Season, Phase, and Week orchestrators inject code-owned availability capacity and S5 bands from `src/rps/planning/load_bands.py`; agents may explain and apply these values but must not recompute, widen, or overwrite them. |
| Deterministic planning context registry | `src/rps/planning/deterministic_context.py` centralizes prompt blocks for event horizon, cadence options, selected-scenario structure, phase slots, phase execution, week calendar/availability, report evidence, and Coach operation boundaries. Agents use these as runtime truth instead of recalculating dates, phase counts, ranges, or operation state. |

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
