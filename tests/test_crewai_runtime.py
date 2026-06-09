from __future__ import annotations

import json
import logging
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from rps.agents import runtime as agent_runtime
from rps.agents.crewai_backend import (
    _TASK_BLUEPRINT_BY_AGENT_TASK,
    _build_crewai_task,
    _build_internal_task_description,
    _coerce_artifact_envelope,
    _compact_internal_user_input,
    _contract_context_blocks_for_task,
    _emit_crew_task_prepared_events,
    _execute_crewai_multiagent_crew,
    _extract_authoritative_runtime_blocks,
    _normalize_final_season_plan_semantics,
    _normalize_publication_link,
    _phase_bundle_finalize_authority_freeze_block,
    _phase_bundle_finalize_has_bound_contracts,
    _phase_writer_authority_context_block,
    _run_multicrew_cycle,
    _run_phase_bundle_document,
    _task_tools_for_blueprint,
    normalize_phase_draft_bundle,
    normalize_season_plan_draft_bundle,
    run_agent_multi_output_crewai,
)
from rps.agents.runtime import AgentRuntime
from rps.agents.tasks import AgentTask
from rps.core.config import load_app_settings
from rps.crewai_runtime import crewai_runtime_status, load_crewai_config_bundle
from rps.crewai_runtime import guardrails as crewai_guardrails
from rps.crewai_runtime import telemetry as crewai_telemetry
from rps.crewai_runtime.bindings import (
    build_agent_blueprints,
    build_task_blueprints,
    collect_native_agent_kwargs,
    configured_task_context_names,
    output_model_for_kind,
    output_model_for_task,
)
from rps.crewai_runtime.compat import crewai_runtime_status as compat_crewai_runtime_status
from rps.crewai_runtime.flows import (
    run_coach_flow,
    run_feed_forward_flow,
    run_phase_flow,
    run_report_flow,
    run_season_flow,
    run_week_flow,
)
from rps.crewai_runtime.guardrails import (
    artifact_envelope_basic,
    artifact_schema_valid,
    build_task_guardrail_kwargs,
    des_diagnostic_only,
    guardrail_runtime_context,
    phase_bundle_matches_context,
    phase_bundle_review_readiness,
    phase_s5_band_match,
    phase_week_role_load_coherence,
    phase_weeks_match_range,
    resolve_task_policy,
    review_decision_integrity,
    season_bundle_integrity,
    season_bundle_matches_contract,
    season_bundle_review_readiness,
    season_phase_load_context_match,
    season_phase_load_feasibility,
    season_scenario_selection_shape,
    season_scenarios_profile_quality,
    season_scenarios_selection_contract_complete,
    season_writer_bundle_match,
    week_active_corridor_match,
    week_agenda_shape_and_calendar_check,
    week_bundle_domain_legality_check,
    week_bundle_review_readiness,
    week_corridor_and_capacity_check,
    week_daily_availability_check,
    week_phase_role_alignment_check,
    week_recovery_day_load_check,
    week_workout_structure_policy_check,
)
from rps.crewai_runtime.knowledge import (
    _compact_knowledge_query,
    build_crewai_knowledge_kwargs,
    resolve_agent_knowledge_profile,
    resolve_crew_knowledge_profile,
)
from rps.crewai_runtime.memory import (
    build_agent_memory_value,
    build_crew_memory_kwargs,
    build_memory_instance,
    resolve_agent_memory_profile,
    resolve_crew_memory_profile,
)
from rps.crewai_runtime.models import (
    AdjustmentIntentModel,
    ArtifactEnvelopeModel,
    CoachingRecommendationModel,
    CoachOperationApplyResultModel,
    CoachOperationPreviewModel,
    ConstraintAuditModel,
    DESAnalysisBundleModel,
    EvidenceCurationModel,
    LoadGovernanceAuditModel,
    PendingResolutionResultModel,
    PhaseBundleModel,
    PhaseDraftBundleModel,
    PhaseReviewDecisionModel,
    PhaseWeekBlueprintModel,
    PhaseWeekDraftBlueprintModel,
    PlanningDraftModel,
    ReportReviewDecisionModel,
    SeasonEventAnchorModel,
    SeasonLoadEnvelopeModel,
    SeasonMacrocycleDraftModel,
    SeasonPhaseBlueprintModel,
    SeasonPhaseDraftBlueprintModel,
    SeasonPhaseSemanticContractModel,
    SeasonPlanAuditModel,
    SeasonPlanBundleModel,
    SeasonPlanDraftBundleModel,
    SeasonReviewDecisionModel,
    TurnModeModel,
    WeekContextAssessmentModel,
    WeekDayBlueprintModel,
    WeekPlanBundleModel,
    WeekReviewDecisionModel,
    WeekWorkoutBlueprintModel,
)
from rps.crewai_runtime.provider import (
    build_crewai_llm_kwargs,
    build_crewai_planning_llm_kwargs,
    resolve_crewai_planning_enabled,
    resolve_crewai_provider_config,
)
from rps.crewai_runtime.skills import build_crewai_skill_kwargs, resolve_agent_skill_profile
from rps.orchestrator import season_flow
from rps.orchestrator.coach_operations import (
    preview_feed_forward_operation,
    preview_report_operation,
    preview_scoped_week_replan_operation,
)
from rps.orchestrator.resolved_context import build_resolved_load_governance_context_block
from rps.planning.deterministic_context import (
    build_week_calendar_context,
    render_week_calendar_context_block,
)
from rps.prompts.loader import PromptLoader
from rps.ui.run_store import load_events
from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


def _install_fake_crewai_events(monkeypatch) -> object:
    """Install a minimal CrewAI events module with a singleton event bus."""

    events_module = types.ModuleType("crewai.events")

    class FakeEventBus:
        def __init__(self):
            self.handlers: dict[type[object], list[object]] = {}

        def on(self, event_cls):
            def _decorate(fn):
                self.handlers.setdefault(event_cls, []).append(fn)
                return fn

            return _decorate

        def emit(self, event):
            for handler in self.handlers.get(type(event), []):
                handler(None, event)

    bus = FakeEventBus()

    class BaseEventListener:
        def __init__(self):
            self.setup_listeners(bus)

        def setup_listeners(self, crewai_event_bus):
            return None

    class _BaseEvent:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    for name in [
        "CrewKickoffStartedEvent",
        "CrewKickoffCompletedEvent",
        "CrewKickoffFailedEvent",
        "TaskStartedEvent",
        "TaskCompletedEvent",
        "TaskFailedEvent",
        "ToolUsageStartedEvent",
        "ToolUsageFinishedEvent",
        "ToolUsageErrorEvent",
        "FlowStartedEvent",
        "FlowFinishedEvent",
        "MethodExecutionStartedEvent",
        "MethodExecutionFinishedEvent",
        "MethodExecutionFailedEvent",
    ]:
        setattr(events_module, name, type(name, (_BaseEvent,), {}))
    events_module.BaseEventListener = BaseEventListener
    events_module.crewai_event_bus = bus
    monkeypatch.setitem(sys.modules, "crewai.events", events_module)
    crewai_telemetry._LISTENER_READY = False
    crewai_telemetry._LISTENER_INIT_FAILED = False
    return events_module


def _install_fake_flow_module(monkeypatch) -> None:
    """Install a minimal CrewAI Flow module for unit tests."""

    flow_module = types.ModuleType("crewai.flow.flow")
    events_module = sys.modules.get("crewai.events")
    bus = getattr(events_module, "crewai_event_bus", None)

    def start(*_args, **_kwargs):
        def _decorate(func):
            func._flow_start = True
            return func

        return _decorate

    def router(trigger):
        def _decorate(func):
            func._flow_router = trigger
            return func

        return _decorate

    def listen(trigger):
        def _decorate(func):
            func._flow_listen = trigger
            return func

        return _decorate

    class FakeFlow:
        @classmethod
        def __class_getitem__(cls, _item):
            return cls

        def __init__(self):
            self.state = SimpleNamespace(action="", result={}, requested_tasks=[])

        def kickoff(self):
            if bus is not None:
                bus.emit(events_module.FlowStartedEvent(flow_name=type(self).__name__))
            start_method = None
            router_method = None
            listeners: list[tuple[object, object]] = []
            for name in dir(self):
                candidate = getattr(self, name)
                func = getattr(type(self), name, None)
                if callable(candidate) and getattr(func, "_flow_start", False):
                    start_method = candidate
                if callable(candidate) and hasattr(func, "_flow_router"):
                    router_method = candidate
                if callable(candidate) and hasattr(func, "_flow_listen"):
                    listeners.append((getattr(func, "_flow_listen"), candidate))
            if start_method is None:
                raise AssertionError("FakeFlow requires a @start method")
            if bus is not None:
                bus.emit(events_module.MethodExecutionStartedEvent(flow_name=type(self).__name__, method_name=getattr(start_method, "__name__", "")))
            current_result = start_method()
            if bus is not None:
                bus.emit(events_module.MethodExecutionFinishedEvent(flow_name=type(self).__name__, method_name=getattr(start_method, "__name__", "")))
            current_name = getattr(start_method, "__name__", "")
            if router_method is not None:
                route_label = router_method(current_result)
                for trigger, listener_method in listeners:
                    if trigger == route_label:
                        if bus is not None:
                            bus.emit(events_module.MethodExecutionStartedEvent(flow_name=type(self).__name__, method_name=getattr(listener_method, "__name__", "")))
                        current_result = listener_method()
                        if bus is not None:
                            bus.emit(events_module.MethodExecutionFinishedEvent(flow_name=type(self).__name__, method_name=getattr(listener_method, "__name__", "")))
                        current_name = getattr(listener_method, "__name__", "")
                        break
                else:
                    if bus is not None:
                        bus.emit(events_module.FlowFinishedEvent(flow_name=type(self).__name__))
                    return None
            while True:
                next_listener = None
                for trigger, listener_method in listeners:
                    trigger_name = getattr(trigger, "__name__", None)
                    if trigger_name == current_name:
                        next_listener = listener_method
                        break
                if next_listener is None:
                    if bus is not None:
                        bus.emit(events_module.FlowFinishedEvent(flow_name=type(self).__name__))
                    return current_result
                if bus is not None:
                    bus.emit(events_module.MethodExecutionStartedEvent(flow_name=type(self).__name__, method_name=getattr(next_listener, "__name__", "")))
                current_result = next_listener(current_result)
                if bus is not None:
                    bus.emit(events_module.MethodExecutionFinishedEvent(flow_name=type(self).__name__, method_name=getattr(next_listener, "__name__", "")))
                current_name = getattr(next_listener, "__name__", "")

    flow_module.Flow = FakeFlow
    flow_module.start = start
    flow_module.listen = listen
    flow_module.router = router
    monkeypatch.setitem(sys.modules, "crewai.flow.flow", flow_module)


def test_crewai_config_bundle_loads_known_agents_and_tasks() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))

    agent_defs = bundle.agents["agents"]
    task_defs = bundle.tasks["tasks"]
    knowledge_defs = bundle.knowledge_sources["agents"]
    flow_defs = bundle.flow_persistence["flows"]
    assert "conversation_manager" in agent_defs
    assert "week_recommendation_specialist" in agent_defs
    assert "week_planner" in agent_defs
    assert "season_plan_manager" in agent_defs
    assert "phase_bundle_manager" in agent_defs
    assert "week_plan_manager" in knowledge_defs
    assert flow_defs["season"]["persist"] is True
    assert flow_defs["coach"]["persist"] is False
    assert bundle.runtime_profiles["crews"]["season_planning"]["planning"]["enabled"] is False
    assert bundle.runtime_profiles["crews"]["phase_planning"]["planning"]["enabled"] is False
    assert bundle.runtime_profiles["crews"]["phase_planning"]["planning"]["model"] == "gpt-5.4-mini"
    assert bundle.runtime_profiles["agents"]["season_plan_manager"]["model"] == "gpt-5.4-mini"
    assert bundle.runtime_profiles["agents"]["season_plan_manager"]["reasoning"]["enabled"] is False
    assert bundle.runtime_profiles["agents"]["macrocycle_architect"]["model"] == "gpt-5.4"
    assert bundle.runtime_profiles["agents"]["macrocycle_architect"]["reasoning"]["enabled"] is False
    assert bundle.runtime_profiles["agents"]["week_artifact_writer"]["reasoning"]["enabled"] is False
    assert bundle.skills["agents"]["week_revision_specialist"]["skill"] == "skills/week/revision-methodology"
    assert bundle.skills["crews"]["coach_conversation"]["skills"] == [
        "skills/shared/runtime-boundaries",
        "skills/shared/resolved-context-consumption",
        "skills/shared/traceability-and-naming",
    ]
    assert task_defs["classify_turn"]["agent"] == "conversation_manager"
    assert task_defs["create_week_preview"]["agent"] == "week_revision_specialist"
    assert task_defs["season_scenario_selection"]["agent"] == "season_scenario"
    assert task_defs["season_scenario_selection"]["kind"] == "persisted_artifact"
    assert task_defs["week_plan"]["agent"] == "week_artifact_writer"
    assert task_defs["season_plan"]["agent"] == "season_artifact_writer"
    assert task_defs["phase_guardrails"]["agent"] == "phase_artifact_writer"
    assert _TASK_BLUEPRINT_BY_AGENT_TASK[AgentTask.CREATE_SEASON_SCENARIO_SELECTION] == "season_scenario_selection"


def test_coerce_artifact_envelope_extracts_wrapped_raw_payload() -> None:
    envelope = {
        "meta": {"artifact_type": "SEASON_SCENARIOS"},
        "data": {"scenarios": []},
    }
    wrapped = {
        "raw": json.dumps(envelope),
        "pydantic": None,
        "json_dict": None,
        "tasks_output": [
            {
                "raw": json.dumps(envelope),
            }
        ],
        "token_usage": {"prompt_tokens": 123},
    }

    assert _coerce_artifact_envelope(wrapped) == envelope


def test_crewai_blueprints_build_from_yaml() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    agents = build_agent_blueprints(bundle)
    tasks = build_task_blueprints(bundle)

    assert agents["conversation_manager"].goal
    assert agents["season_plan_auditor"].goal
    assert agents["season_plan_auditor"].config["prompt_agent"] == "season_plan_auditor"
    assert agents["phase_guardrail_band_specialist"].config["prompt_agent"] == "guardrails_specialist"
    assert agents["week_recommendation_specialist"].knowledge_profile["sources"]
    assert agents["week_recommendation_specialist"].skill_profile["agent_skill"] == "skills/week/recommendation-and-adjustment"
    assert agents["week_recommendation_specialist"].skill_profile["paths"] == ["skills/week/recommendation-and-adjustment"]
    assert tasks["classify_turn"].output_kind == "turn_mode"
    assert tasks["form_adjustment_intent"].output_kind == "adjustment_intent"
    assert tasks["week_plan"].output_kind == "artifact_envelope"
    assert tasks["phase_bundle_finalize"].output_kind == "phase_bundle_draft"
    assert tasks["phase_bundle_finalize"].context_names == (
        "phase_context_read",
        "phase_guardrail_band_draft",
        "phase_execution_rules_draft",
        "phase_structure_draft",
        "phase_cadence_recovery_draft",
        "phase_intensity_distribution_draft",
        "phase_event_integration_draft",
        "phase_preview_draft",
    )
    assert tasks["phase_bundle_finalize"].execution_policy["guardrails"] == (
        "typed_output_present",
        "phase_bundle_integrity",
        "phase_week_role_load_coherence",
        "phase_bundle_review_readiness",
    )
    assert tasks["season_plan_finalize"].output_kind == "season_plan_draft_bundle"


def test_task_policy_resolution_and_guardrail_kwargs() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    tasks = build_task_blueprints(bundle)

    preview_policy = resolve_task_policy(tasks["create_week_preview"], bundle.task_policies)
    artifact_policy = resolve_task_policy(tasks["week_plan"], bundle.task_policies)

    assert preview_policy.output_mode == "pydantic"
    assert "coach_preview_summary_complete" in preview_policy.guardrails
    assert artifact_policy.output_mode == "json"
    assert "artifact_schema_valid" in artifact_policy.guardrails
    assert "week_corridor_and_capacity_check" in artifact_policy.guardrails
    assert "week_active_corridor_match" in artifact_policy.guardrails
    assert "week_recovery_day_load_check" in artifact_policy.guardrails
    assert "week_agenda_shape_and_calendar_check" in artifact_policy.guardrails
    assert "week_daily_availability_check" in artifact_policy.guardrails
    assert "week_phase_role_alignment_check" in artifact_policy.guardrails
    assert "week_workout_structure_policy_check" in artifact_policy.guardrails
    assert "week_exportability_check" in artifact_policy.guardrails
    assert "season_scenario_selection_shape" in resolve_task_policy(
        tasks["season_scenario_selection"], bundle.task_policies
    ).guardrails
    assert "artifact_schema_valid" in resolve_task_policy(
        tasks["season_scenario_selection"], bundle.task_policies
    ).guardrails
    assert "phase_s5_band_match" in resolve_task_policy(tasks["phase_guardrails"], bundle.task_policies).guardrails
    assert "phase_weeks_match_range" in resolve_task_policy(tasks["phase_structure"], bundle.task_policies).guardrails
    assert "season_phase_load_feasibility" in resolve_task_policy(
        tasks["season_plan_finalize"], bundle.task_policies
    ).guardrails
    assert "phase_week_role_load_coherence" in resolve_task_policy(
        tasks["phase_structure"], bundle.task_policies
    ).guardrails
    kwargs = build_task_guardrail_kwargs(tasks["week_plan"], bundle.task_policies)
    assert kwargs["guardrail_max_retries"] == 2
    assert callable(kwargs["guardrails"][0]) or callable(kwargs["guardrail"])
    guardrail = kwargs["guardrails"][0] if "guardrails" in kwargs else kwargs["guardrail"]
    assert "return" not in getattr(guardrail, "__annotations__", {})


def test_planning_draft_model_schema_is_openai_strict_compatible() -> None:
    schema = PlanningDraftModel.model_json_schema()

    assert schema["additionalProperties"] is False
    assert schema["properties"]["details"]["type"] == "array"
    assert "additionalProperties" not in schema["properties"]["details"]


def _open_object_schema_findings(schema: object, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            additional = schema.get("additionalProperties", "<missing>")
            if additional is not False:
                findings.append(f"{path}: additionalProperties={additional!r}")
        if "additionalProperties" in schema and schema.get("additionalProperties") is not False:
            findings.append(f"{path}: explicit additionalProperties={schema.get('additionalProperties')!r}")
        for key, value in schema.items():
            if isinstance(value, (dict, list)) and key not in {"default", "examples"}:
                findings.extend(_open_object_schema_findings(value, f"{path}.{key}"))
    elif isinstance(schema, list):
        for index, item in enumerate(schema):
            findings.extend(_open_object_schema_findings(item, f"{path}[{index}]"))
    return findings


def test_crewai_output_models_are_openai_strict_compatible() -> None:
    output_kinds = {
        "turn_mode",
        "planning_draft",
        "week_context_assessment",
        "coaching_recommendation",
        "adjustment_intent",
        "pending_resolution_result",
        "coach_preview_summary",
        "artifact_envelope",
        "coach_preview",
        "coach_apply",
        "season_event_anchor",
        "season_macrocycle_draft",
        "season_plan_audit",
        "season_plan_draft_bundle",
        "season_plan_bundle",
        "season_review_decision",
        "phase_guardrails_payload",
        "phase_structure_payload",
        "phase_preview_payload",
        "constraint_audit",
        "load_governance_audit",
        "phase_bundle_draft",
        "phase_bundle",
        "phase_review_decision",
        "week_plan_bundle",
        "week_review_decision",
        "des_analysis_bundle",
        "report_review_decision",
        "replan_instruction",
    }

    findings: list[str] = []
    for output_kind in sorted(output_kinds):
        model = output_model_for_kind(output_kind)
        for finding in _open_object_schema_findings(model.model_json_schema()):
            findings.append(f"{output_kind}.{model.__name__}: {finding}")

    bundle = load_crewai_config_bundle(root=Path("."))
    for task in build_task_blueprints(bundle).values():
        model = output_model_for_task(task)
        for finding in _open_object_schema_findings(model.model_json_schema()):
            findings.append(f"task:{task.name}.{model.__name__}: {finding}")

    assert findings == []


def test_guardrail_failure_emits_runtime_event(monkeypatch) -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    tasks = build_task_blueprints(bundle)
    emitted: list[dict[str, object]] = []

    def _emit(**kwargs):
        emitted.append(kwargs)

    monkeypatch.setattr(crewai_guardrails, "emit_runtime_event", _emit)
    kwargs = build_task_guardrail_kwargs(tasks["season_scenario_selection"], bundle.task_policies)
    invalid = {
        "meta": {"artifact_type": "SEASON_SCENARIO_SELECTION", "schema_id": "SeasonScenarioSelectionInterface"},
        "data": {"selected_scenario_id": "D", "season_scenarios_ref": "season_scenarios/latest.json"},
    }

    with guardrail_runtime_context(root=Path("."), athlete_id="i150546", run_id="run-1", component="test"):
        failed = [guardrail(invalid) for guardrail in kwargs["guardrails"]]

    assert any(ok is False for ok, _payload in failed)
    assert any(event["event_type"] == "CREW_TASK_GUARDRAIL_FAILED" for event in emitted)
    assert any(event["guardrail"] == "season_scenario_selection_shape" for event in emitted)


def test_create_season_plan_aborts_before_crew_when_selection_binding_fails(
    monkeypatch, tmp_path: Path
) -> None:
    invoked = False

    def _fake_run_agent_multi_output(*args, **kwargs):
        nonlocal invoked
        invoked = True
        return {"ok": True}

    monkeypatch.setattr(season_flow, "run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "i150546"
    store.ensure_workspace(athlete_id)
    store.save_document(
        athlete_id,
        ArtifactType.ATHLETE_PROFILE,
        "2026-22",
        {"data": {}},
        producer_agent="test",
        run_id="profile",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.AVAILABILITY,
        "2026-22",
        {"data": {"weekly_hours": {"typical": 12.0}, "fixed_rest_days": ["Mon", "Fri"]}},
        producer_agent="test",
        run_id="availability",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_SCENARIOS,
        "2026-22__new",
        {
            "meta": {"version_key": "2026-22__new", "run_id": "scenarios-new"},
            "data": {
                "planning_horizon_weeks": 16,
                "scenarios": [
                    {
                        "scenario_id": "B",
                        "name": "Balanced build",
                        "load_philosophy": "balanced_progressive",
                        "risk_profile": "medium",
                        "best_suited_if": "Stable recovery",
                        "key_differences": "Balanced pressure",
                        "main_payoff": "Repeatable progression",
                        "main_cost": "Less conservative than A",
                        "scenario_guidance": {
                            "recovery_margin": "medium",
                            "fatigue_exposure": "moderate",
                            "specificity_density": "controlled",
                            "constraint_summary": ["Preserve continuity."],
                            "event_alignment_notes": ["B-event rehearsal"],
                            "risk_flags": [],
                            "kpi_guardrail_notes": ["Stay repeatable."],
                            "decision_notes": ["Selected for test."],
                            "deload_cadence": "2:1:1",
                            "phase_length_weeks": 4,
                            "phase_count_expected": 4,
                            "phase_plan_summary": {"full_phases": 4, "shortened_phases": []},
                            "max_shortened_phases": 0,
                            "shortening_budget_weeks": 0,
                            "intensity_guidance": {"allowed_domains": ["ENDURANCE", "TEMPO"], "avoid_domains": ["VO2MAX"]},
                        },
                    }
                ],
            },
        },
        producer_agent="test",
        run_id="scenarios-new",
        update_latest=True,
    )
    store.save_document(
        athlete_id,
        ArtifactType.SEASON_SCENARIO_SELECTION,
        "2026-22__sel",
        {
            "meta": {
                "version_key": "2026-22__sel",
                "run_id": "selection",
                "trace_upstream": [
                    {"artifact": "SEASON_SCENARIOS", "version": "2026-22__old", "version_key": "2026-22__old", "run_id": "scenarios-old"}
                ],
            },
            "data": {
                "season_scenarios_ref": "2026-22__old",
                "selected_scenario_id": "B",
                "selection_source": "user",
                "selection_rationale": "Balanced choice",
                "notes": ["stale selection"],
                "kpi_moving_time_rate_guidance_selection": None,
            },
        },
        producer_agent="test",
        run_id="selection",
        update_latest=True,
    )

    result = season_flow.create_season_plan(
        lambda _agent_name: SimpleNamespace(workspace_root=tmp_path),
        athlete_id=athlete_id,
        year=2026,
        week=22,
        run_id="season-plan",
        selected=None,
    )

    assert result["ok"] is False
    assert result["reason_code"] == "selection_stale_vs_scenarios"
    assert invoked is False


def test_emit_runtime_exception_event_records_structured_llm_failure(tmp_path: Path) -> None:
    try:
        raise RuntimeError(
            "Error code: 429 - {'error': {'message': 'You exceeded your current quota.', 'type': 'insufficient_quota', 'code': 'insufficient_quota'}}"
        )
    except RuntimeError as exc:
        crewai_telemetry.emit_runtime_exception_event(
            root=tmp_path,
            athlete_id="athlete",
            run_id="run-llm-failure",
            exc=exc,
            crew="season_planning",
            task="season_plan",
        )

    events = load_events(tmp_path, "athlete", "run-llm-failure")
    assert events[-1]["type"] == "LLM_REQUEST_FAILED"
    assert events[-1]["error_code"] == "insufficient_quota"
    assert events[-1]["error_type"] == "insufficient_quota"
    assert events[-1]["status_code"] == "429"
    assert "current quota" in str(events[-1]["reason"])


def test_build_memory_instance_injects_rps_openai_credentials(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeMemory:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    crewai_module = SimpleNamespace(Memory=FakeMemory)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-rps-key")
    monkeypatch.setenv("RPS_LLM_BASE_URL", "https://example.invalid/v1")

    memory = build_memory_instance(
        crewai_module,
        storage="runtime/athletes/i150546/memory/test",
        embedder={"provider": "openai", "config": {"model_name": "text-embedding-3-small"}},
        llm=None,
    )

    assert memory is not None
    embedder = captured["embedder"]
    assert isinstance(embedder, dict)
    assert embedder["config"]["api_key"] == "test-rps-key"
    assert embedder["config"]["base_url"] == "https://example.invalid/v1"
    assert embedder["config"]["api_base"] == "https://example.invalid/v1"
    assert os.environ["OPENAI_API_KEY"] == "test-rps-key"


def test_build_crew_memory_kwargs_normalizes_top_level_embedder(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeMemory:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    crewai_module = SimpleNamespace(Memory=FakeMemory)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-rps-key")
    monkeypatch.setenv("RPS_LLM_BASE_URL", "https://example.invalid/v1")

    kwargs = build_crew_memory_kwargs(
        crewai_module,
        profile={
            "enabled": True,
            "storage": "runtime/athletes/i150546/memory/test",
            "embedder": {"provider": "openai", "config": {"model_name": "text-embedding-3-small"}},
            "llm": None,
        },
    )

    embedder = kwargs["embedder"]
    assert isinstance(embedder, dict)
    assert embedder["config"]["api_key"] == "test-rps-key"
    assert embedder["config"]["base_url"] == "https://example.invalid/v1"
    assert embedder["config"]["api_base"] == "https://example.invalid/v1"


def test_build_crewai_knowledge_kwargs_mirrors_rps_openai_env(monkeypatch, tmp_path: Path) -> None:
    skill_root = tmp_path
    source = skill_root / "sample.md"
    source.write_text("knowledge", encoding="utf-8")
    monkeypatch.setattr("rps.crewai_runtime.knowledge._KNOWLEDGE_SEARCH_GUARDS_READY", False)

    class FakeStringKnowledgeSource:
        def __init__(self, *, content: str):
            self.content = content

    class FakeKnowledgeStorage:
        def search(self, query, *args, **kwargs):
            self.last_query = query
            return []

    fake_module = types.ModuleType("crewai.knowledge.source.string_knowledge_source")
    fake_module.StringKnowledgeSource = FakeStringKnowledgeSource
    fake_storage_module = types.ModuleType("crewai.knowledge.storage.knowledge_storage")
    fake_storage_module.KnowledgeStorage = FakeKnowledgeStorage
    monkeypatch.setitem(sys.modules, "crewai.knowledge.source.string_knowledge_source", fake_module)
    monkeypatch.setitem(sys.modules, "crewai.knowledge.storage.knowledge_storage", fake_storage_module)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-rps-key")

    kwargs = build_crewai_knowledge_kwargs(
        root=skill_root,
        profile={"sources": [{"path": "sample.md"}], "knowledge_config": {}},
    )

    assert "knowledge_sources" in kwargs
    assert os.environ["OPENAI_API_KEY"] == "test-rps-key"
    storage = FakeKnowledgeStorage()
    storage.search("System and agent instructions: " + ("x " * 5000) + "Current Task: compact me")
    assert isinstance(storage.last_query, str)
    assert len(storage.last_query) <= 4000


def test_knowledge_and_memory_profiles_resolve_from_config() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))

    coach_knowledge = resolve_agent_knowledge_profile(bundle, agent_name="week_recommendation_specialist")
    season_knowledge = resolve_crew_knowledge_profile(bundle, crew_name="season_planning")
    coach_memory = resolve_crew_memory_profile(
        bundle,
        crew_name="coach_conversation",
        athlete_id="i150546",
        surface="coach",
    )
    season_memory = resolve_crew_memory_profile(
        bundle,
        crew_name="season_planning",
        athlete_id="i150546",
        surface="default",
    )
    specialist_memory = resolve_agent_memory_profile(
        bundle,
        agent_name="week_recommendation_specialist",
        athlete_id="i150546",
        surface="coach",
    )

    assert coach_knowledge["sources"]
    assert season_knowledge["sources"]
    assert coach_memory["enabled"] is True
    assert coach_memory["scope"] == "/athlete/i150546/coach/shared"
    assert season_memory["enabled"] is False
    assert specialist_memory["mode"] == "slice_read_only"
    assert "/athlete/i150546/coach/accepted_patterns" in specialist_memory["additional_read_scopes"]
    writer_memory = resolve_agent_memory_profile(
        bundle,
        agent_name="week_artifact_writer",
        athlete_id="i150546",
        surface="default",
    )
    assert writer_memory["mode"] == "read_only"


def test_planning_specialists_resolve_without_static_knowledge() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))

    for agent_name in (
        "season_context_specialist",
        "season_plan_manager",
        "phase_context_specialist",
        "phase_bundle_manager",
        "week_context_specialist",
        "week_plan_manager",
    ):
        profile = resolve_agent_knowledge_profile(bundle, agent_name=agent_name)
        assert profile["sources"] == []


def test_compact_knowledge_query_caps_large_prompt_text() -> None:
    giant = (
        "System and agent instructions:\n# System prompt\n"
        + ("boilerplate " * 5000)
        + "\nCurrent Task: Summarize the active season constraints and event anchors."
    )

    compacted = _compact_knowledge_query(giant)

    assert isinstance(compacted, str)
    assert "Current Task:" in compacted
    assert len(compacted) <= 4000
    assert len(compacted.split()) <= 600


def test_compact_internal_user_input_preserves_priority_markers() -> None:
    giant = (
        "## Task Context The following is the full task you are helping complete. "
        + ("boilerplate " * 2500)
        + "Current Task: Define peak window logic for the selected season. "
        + ("filler " * 1500)
        + "Current Step Extract the primary anchor event and taper placement constraints. "
        + "Context from previous steps: Scenario C selected. "
        + "Use the latest season-level SEASON_SCENARIO_SELECTION and SEASON_SCENARIOS as context."
    )

    compacted = _compact_internal_user_input(giant)

    assert "Current Task:" in compacted
    assert "Current Step" in compacted
    assert "Context from previous steps:" in compacted
    assert "Use the latest" in compacted
    assert len(compacted) <= 2800
    assert len(compacted.split()) <= 450


def test_extract_authoritative_runtime_blocks_preserves_snapshot_and_resolved_context() -> None:
    user_input = """
## Task Context
boilerplate text

**Athlete State Snapshot**
snapshot_ref: athlete_state_snapshot_2026-21__20260519_122903.json
event_candidates:
- A event

## Current Step
Use the event list.

**Resolved Planning Event Context**
- Event 1
- Event 2

**Deterministic Season Phase Slot Context**
- slot data
""".strip()

    blocks = _extract_authoritative_runtime_blocks(user_input)

    assert len(blocks) == 3
    assert blocks[0].startswith("**Athlete State Snapshot**")
    assert "snapshot_ref:" in blocks[0]
    assert blocks[1].startswith("**Resolved Planning Event Context**")
    assert blocks[2].startswith("**Deterministic Season Phase Slot Context**")


def test_internal_task_description_is_tool_first_and_compact() -> None:
    runtime = AgentRuntime(
        model="gpt-5.4-mini",
        temperature=0.2,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime"),
    )
    bundle = load_crewai_config_bundle(root=Path("."))
    task_blueprints = build_task_blueprints(bundle)

    description = _build_internal_task_description(
        runtime,
        agent_name="peak_window_specialist",
        prompt_agent="event_priority_anchor_specialist",
        bundle=bundle,
        crew_name="season_planning",
        task_blueprint=task_blueprints["season_peak_window_review"],
        user_input=(
            "## Task Context The following is the full task you are helping complete. "
            + ("boilerplate " * 2000)
            + "Current Task: Define peak-window and taper-window logic for the season plan. "
            + "Current Step Use the selected scenario, planning events, and season context."
            + "\n\n**Athlete State Snapshot**\n"
            + "snapshot_ref: athlete_state_snapshot_2026-21__20260519_122903.json\n"
            + "event_candidates:\n- A event\n"
            + "\n**Resolved Planning Event Context**\n"
            + "- Event 1\n- Event 2\n"
        ),
    )

    assert "Shared system instructions for all agents." not in description
    assert "payload_json" in description
    assert "call the tool instead of asking the user for it" in description
    assert "If prior specialist context already contains the needed facts" in description
    assert "Do not create, write, or verify workspace files unless the active task explicitly exposes a write-capable tool" in description
    assert "If you are blocked after relevant tool attempts" in description
    assert "Current Task: Define peak-window and taper-window logic for the season plan." in description
    assert "Authoritative runtime context:" in description
    assert "**Athlete State Snapshot**" in description
    assert "**Resolved Planning Event Context**" in description


def test_season_event_and_peak_tasks_expose_workspace_read_tools() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    task_blueprints = build_task_blueprints(bundle)

    event_tools = task_blueprints["season_event_priority_review"].config.get("tools")
    peak_tools = task_blueprints["season_peak_window_review"].config.get("tools")
    macrocycle_tools = task_blueprints["season_macrocycle_draft"].config.get("tools")

    assert event_tools == ["workspace_get_input", "workspace_get_latest", "workspace_get_version"]
    assert peak_tools == ["workspace_get_input", "workspace_get_latest", "workspace_get_version"]
    assert macrocycle_tools == [
        "workspace_get_input",
        "workspace_get_latest",
        "workspace_get_phase_slot_contract",
    ]


def test_season_specialist_task_scopes_are_explicitly_separated() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    task_blueprints = build_task_blueprints(bundle)

    constraint_description = task_blueprints["season_constraint_review"].description
    historical_description = task_blueprints["season_historical_context_review"].description
    kpi_description = task_blueprints["season_kpi_guidance_review"].description

    assert "hard and soft constraints only" in constraint_description
    assert "historical continuity" in constraint_description
    assert "recent tolerance, disruption risk, and continuity evidence only" in historical_description
    assert "Do not restate fixed rest days, phase corridors, event taper handling, or KPI pacing semantics as primary findings" in historical_description
    assert "Keep the output centered on pacing/rate-band interpretation" in kpi_description
    assert "Do not restate fixed rest days, availability bounds, phase corridors, load caps, event-anchor/taper handling, or historical continuity as primary findings" in kpi_description


def test_agent_memory_read_only_mode_uses_slice() -> None:
    class FakeMemory:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def slice(self, **kwargs):
            self.calls.append(kwargs)
            return {"slice": kwargs}

        def scope(self, scope: str):
            raise AssertionError(f"read_only mode must not request writable scope {scope}")

    shared = FakeMemory()
    value = build_agent_memory_value(
        shared_memory=shared,
        profile={"mode": "read_only", "scope": "/athlete/i150546/planning/week/writer"},
    )

    assert value == {
        "slice": {
            "scopes": ["/athlete/i150546/planning/week/writer"],
            "read_only": True,
        }
    }
    assert shared.calls


def test_native_agent_kwargs_defaults_and_yaml_override() -> None:
    writer_kwargs = collect_native_agent_kwargs("week_artifact_writer", {})
    assert writer_kwargs["allow_delegation"] is False
    assert writer_kwargs["max_iter"] == 2
    assert writer_kwargs["respect_context_window"] is True
    assert writer_kwargs["cache"] is False

    manager_kwargs = collect_native_agent_kwargs("week_plan_manager", {"max_iter": 7})
    assert manager_kwargs["allow_delegation"] is True
    assert manager_kwargs["max_iter"] == 7
    assert manager_kwargs["respect_context_window"] is True


def test_configured_task_context_names_normalizes_yaml_values() -> None:
    assert configured_task_context_names({"context": "task_a"}) == ("task_a",)
    assert configured_task_context_names({"context": ["task_a", "task_b"]}) == ("task_a", "task_b")


def test_task_scoped_tools_and_callback_are_attached() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    tasks = build_task_blueprints(bundle)
    tool_map = {
        name: SimpleNamespace(name=name)
        for name in [
            "workspace_get_input",
            "workspace_get_latest",
            "workspace_get_version",
            "workspace_get_phase_slot_contract",
            "workspace_get_phase_context",
            "workspace_get_week_calendar_context",
            "workspace_get_phase_execution_context",
        ]
    }

    assert _task_tools_for_blueprint(
        tasks["week_context_read"], tool_map
    ) == [
        tool_map["workspace_get_input"],
        tool_map["workspace_get_latest"],
        tool_map["workspace_get_version"],
        tool_map["workspace_get_phase_context"],
        tool_map["workspace_get_week_calendar_context"],
        tool_map["workspace_get_phase_execution_context"],
    ]
    assert _task_tools_for_blueprint(tasks["week_plan"], tool_map) == []
    assert _task_tools_for_blueprint(tasks["season_macrocycle_draft"], tool_map) == [
        tool_map["workspace_get_input"],
        tool_map["workspace_get_latest"],
        tool_map["workspace_get_phase_slot_contract"],
    ]

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    task = _build_crewai_task(
        task_cls=FakeTask,
        bundle=bundle,
        task_blueprint=tasks["week_context_read"],
        agent=object(),
        description="test",
        runtime=SimpleNamespace(workspace_root=Path(".")),
        crew_name="week_planning",
        athlete_id="i150546",
        run_id="run-1",
        tools=tool_map,
    )

    assert task.kwargs["tools"] == [
        tool_map["workspace_get_input"],
        tool_map["workspace_get_latest"],
        tool_map["workspace_get_version"],
        tool_map["workspace_get_phase_context"],
        tool_map["workspace_get_week_calendar_context"],
        tool_map["workspace_get_phase_execution_context"],
    ]
    assert task.kwargs["name"] == "week_context_read"
    assert callable(task.kwargs["callback"])


def test_build_crewai_task_tools_override_takes_precedence() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    tasks = build_task_blueprints(bundle)
    tool_map = {
        name: SimpleNamespace(name=name)
        for name in [
            "workspace_get_phase_execution_context",
            "workspace_get_phase_slot_contract",
        ]
    }

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    task = _build_crewai_task(
        task_cls=FakeTask,
        bundle=bundle,
        task_blueprint=tasks["phase_bundle_finalize"],
        agent=SimpleNamespace(llm=None),
        description="test",
        runtime=AgentRuntime(
            model="openai/gpt-5-mini",
            temperature=1.0,
            reasoning_effort="medium",
            reasoning_summary="auto",
            max_completion_tokens=8000,
            prompt_loader=PromptLoader(Path("prompts")),
            schema_dir=Path("specs/schemas"),
            workspace_root=Path("runtime/athletes"),
        ),
        crew_name="phase_planning",
        tools=tool_map,
        tools_override=[],
    )

    assert "tools" not in task.kwargs


def test_skill_kwargs_resolve_native_crewai_skill_paths() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    profile = resolve_agent_skill_profile(bundle, agent_name="week_revision_specialist", crew_name="coach_conversation")
    kwargs = build_crewai_skill_kwargs(root=Path("."), profile=profile)
    assert profile["agent_skill"] == "skills/week/revision-methodology"
    assert profile["crew_skills"] == [
        "skills/shared/runtime-boundaries",
        "skills/shared/resolved-context-consumption",
        "skills/shared/traceability-and-naming",
    ]
    skill_paths = [Path(path) for path in kwargs["skills"]]
    assert Path("skills/week/revision-methodology").resolve() in skill_paths
    assert Path("skills/shared/runtime-boundaries").resolve() in skill_paths


def test_coach_evidence_source_guidance_is_in_active_skills() -> None:
    coach_skill = Path("skills/conversation/guarded-operations/SKILL.md").read_text(encoding="utf-8")
    recommendation_skill = Path("skills/week/recommendation-and-adjustment/SKILL.md").read_text(encoding="utf-8")
    manifest = Path("skills/shared/durability-methodology/references/evidence_library_manifest.md")
    core_table = Path("skills/shared/durability-methodology/references/durability_reference_table_core.md")
    applied_table = Path("skills/shared/durability-methodology/references/durability_reference_table_applied.md")

    assert manifest.exists()
    assert core_table.exists()
    assert applied_table.exists()
    assert "references/library/" in coach_skill
    assert "evidence_library_manifest.md" in manifest.read_text(encoding="utf-8") or "canonical local evidence library" in manifest.read_text(encoding="utf-8")
    assert "durability_reference_table_core.md" in coach_skill
    assert "durability_reference_table_applied.md" in coach_skill
    assert "omit it instead of inventing" in coach_skill
    assert "pubmed.ncbi.nlm.nih.gov" in coach_skill
    assert "Maunder/Seiler/Kilding/Plews" in coach_skill
    assert "available primary-source result" in recommendation_skill
    assert "omit it instead of inventing PMID, DOI, URL, journal, or year details" in recommendation_skill
    assert "use only verified study conclusions" in recommendation_skill


def test_coach_recommendation_answer_discipline_is_configured() -> None:
    recommendation_skill = Path("skills/week/recommendation-and-adjustment/SKILL.md").read_text(encoding="utf-8")
    finalizer_skill = Path("skills/conversation/routing-and-finalization/SKILL.md").read_text(encoding="utf-8")
    coach_chat_source = Path("src/rps/crewai_runtime/coach_chat.py").read_text(encoding="utf-8")

    assert "Answer like an experienced cycling coach" in recommendation_skill
    assert "Finalize replies as an experienced cycling coach" in finalizer_skill
    assert "Answer like an experienced cycling coach" in coach_chat_source
    assert "Write as an experienced cycling coach" in coach_chat_source
    assert "Answer simple why-questions with compact coach prose" in recommendation_skill
    assert "Answer simple advisory questions with compact coach prose" in finalizer_skill
    assert "Answer simple why-questions with compact coach prose" in coach_chat_source
    assert "Use domain calculations, IF targets, thresholds, citations, and source claims only when" in coach_chat_source
    assert "finalize_reply_style_repair" in coach_chat_source
    assert "Use natural coach language and reserve DONE, READY, OUTPUT" in coach_chat_source


def test_normalize_final_season_plan_semantics_enriches_trace_and_guardrails() -> None:
    def _input_payload(artifact: str, version_key: str, run_id: str) -> dict[str, object]:
        return {
            "meta": {
                "artifact_type": artifact,
                "version": "1.0",
                "schema_version": "1.0",
                "version_key": version_key,
                "run_id": run_id,
            }
        }

    document = {
        "meta": {
            "artifact_type": "SEASON_PLAN",
            "data_confidence": "HIGH",
            "trace_data": [
                {
                    "artifact": "ACTIVITIES_ACTUAL",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "2026-21",
                    "run_id": "run-actual",
                }
            ],
            "trace_events": [],
        },
        "data": {
            "season_intent_principles": {
                "season_objective": "Strong execution over 200 km with durability reserve for longer brevet demands."
            },
            "phases": [
                {
                    "phase_id": "P02",
                    "phase_intent": "durability_build",
                    "phase_type": "BUILD",
                    "build_subtype": "durability_build",
                    "weekly_load_corridor": {"weekly_kj": {"notes": ""}},
                    "overview": {"non_negotiables": []},
                },
                {
                    "phase_id": "P04",
                    "phase_intent": "taper_freshening",
                    "phase_type": "TAPER",
                    "build_subtype": None,
                    "weekly_load_corridor": {"weekly_kj": {"notes": ""}},
                    "overview": {"non_negotiables": []},
                },
            ],
            "assumptions_unknowns": {"revisit_items": []},
            "justification": {"phase_justifications": []},
            "principles_scientific_foundation": {
                "principle_applications": [{"principle": "Durability-first", "influence": "Season remains durability-led."}],
                "scientific_foundation": {
                    "publications": [
                        {
                            "authors": "Mujika, I., & Padilla, S.",
                            "year": 2003,
                            "title": "Scientific bases for precompetition tapering strategies",
                            "link": "https://pubmed.ncbi.nlm.nih.gov/12495777/",
                        },
                        {
                            "authors": "Stöggl, T. L., & Sperlich, B.",
                            "year": 2014,
                            "title": "Polarized training has greater impact on key endurance variables than threshold, high intensity, or high volume training",
                            "link": "https://pubmed.ncbi.nlm.nih.gov/24549140/",
                        },
                    ]
                },
            },
            "phase_transitions_guardrails": {
                "conservative_triggers": [],
                "absolute_no_go_rules": [],
            },
        },
    }
    season_phase_load_context = {
        "season_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
        "phases": [
            {
                "phase_id": "P02",
                "phase_intent": "durability_build",
                "phase_type": "BUILD",
                "build_subtype": "durability_build",
                "role_week_load_bands": [],
                "event_taper_trace": {"events": []},
            },
            {
                "phase_id": "P04",
                "phase_intent": "taper_freshening",
                "phase_type": "TAPER",
                "build_subtype": None,
                "role_week_load_bands": [],
                "event_taper_trace": {"events": [{"date": "2026-09-12", "type": "A"}]},
            },
        ],
    }
    approved_planning_bundle = {
        "phase_blueprints": [
            {
                "phase_id": "P02",
                "allowed_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "forbidden_domains": ["VO2MAX"],
                "allowed_load_modalities": ["NONE", "K3"],
            },
            {
                "phase_id": "P04",
                "allowed_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                "forbidden_domains": ["THRESHOLD", "VO2MAX"],
                "allowed_load_modalities": ["NONE"],
            },
        ]
    }
    with guardrail_runtime_context(
        season_phase_load_context=season_phase_load_context,
        selected_scenario_contract={
            "selected_scenario_id": "B",
            "load_posture": "balanced_progressive",
            "recovery_margin": "medium",
            "fatigue_exposure": "moderate",
            "specificity_density": "controlled",
        },
        approved_planning_bundle=approved_planning_bundle,
        athlete_profile_payload=_input_payload("ATHLETE_PROFILE", "profile_v1", "run-profile"),
        kpi_profile_payload=_input_payload("KPI_PROFILE", "kpi_v1", "run-kpi"),
        availability_payload=_input_payload("AVAILABILITY", "avail_v1", "run-avail"),
        logistics_payload=_input_payload("LOGISTICS", "log_v1", "run-log"),
        planning_events_payload=_input_payload("PLANNING_EVENTS", "events_v1", "run-events"),
        zone_model_payload=_input_payload("ZONE_MODEL", "zone_v1", "run-zone"),
    ):
        normalized = _normalize_final_season_plan_semantics(document)

    trace_data_artifacts = {entry["artifact"] for entry in normalized["meta"]["trace_data"]}
    trace_event_artifacts = {entry["artifact"] for entry in normalized["meta"]["trace_events"]}
    assert {"ATHLETE_PROFILE", "KPI_PROFILE", "AVAILABILITY", "LOGISTICS", "ZONE_MODEL"}.issubset(trace_data_artifacts)
    assert "PLANNING_EVENTS" in trace_event_artifacts
    publications = normalized["data"]["principles_scientific_foundation"]["scientific_foundation"]["publications"]
    assert any(pub["link"] == "https://pubmed.ncbi.nlm.nih.gov/12840640/" for pub in publications)
    assert any(pub["link"] == "https://pubmed.ncbi.nlm.nih.gov/24550842/" for pub in publications)
    durability_non_negotiables = normalized["data"]["phases"][0]["overview"]["non_negotiables"]
    taper_non_negotiables = normalized["data"]["phases"][1]["overview"]["non_negotiables"]
    assert any("readiness" in item.lower() for item in durability_non_negotiables)
    assert any("load-band labels only" in item.lower() for item in taper_non_negotiables)
    assert any(
        "first Build phase" in item or "first Build" in item
        for item in normalized["data"]["phase_transitions_guardrails"]["conservative_triggers"]
    )
    assert any(
        "load-band labels only" in item.lower()
        for item in normalized["data"]["phase_transitions_guardrails"]["absolute_no_go_rules"]
    )
    assert normalized["data"]["selected_scenario_contract"]["selected_scenario_id"] == "B"


def test_normalize_final_season_plan_semantics_deduplicates_trace_data_by_artifact_and_version_key() -> None:
    document = {
        "meta": {
            "artifact_type": "SEASON_PLAN",
            "trace_data": [
                {
                    "artifact": "ATHLETE_PROFILE",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "profile_v1",
                    "run_id": "raw-run",
                },
                {
                    "artifact": "AVAILABILITY",
                    "version": "1.0",
                    "schema_version": "1.0",
                    "version_key": "avail_v1",
                    "run_id": "raw-avail-run",
                },
            ],
            "trace_events": [],
        },
        "data": {
            "season_intent_principles": {"season_objective": "Strong 200 km A-event execution."},
            "phases": [],
            "assumptions_unknowns": {"revisit_items": []},
        },
    }

    def _input_payload(artifact: str, version_key: str, run_id: str) -> dict[str, object]:
        return {
            "meta": {
                "artifact_type": artifact,
                "version": "1.0",
                "schema_version": "1.0",
                "version_key": version_key,
                "run_id": run_id,
            }
        }

    with guardrail_runtime_context(
        athlete_profile_payload=_input_payload("ATHLETE_PROFILE", "profile_v1", "resolved-run"),
        availability_payload=_input_payload("AVAILABILITY", "avail_v1", "resolved-avail-run"),
    ):
        normalized = _normalize_final_season_plan_semantics(document)

    trace_data = normalized["meta"]["trace_data"]
    assert len([entry for entry in trace_data if entry["artifact"] == "ATHLETE_PROFILE"]) == 1
    assert len([entry for entry in trace_data if entry["artifact"] == "AVAILABILITY"]) == 1
    assert next(entry for entry in trace_data if entry["artifact"] == "ATHLETE_PROFILE")["run_id"] == "resolved-run"
    assert next(entry for entry in trace_data if entry["artifact"] == "AVAILABILITY")["run_id"] == "resolved-avail-run"


def test_taper_selection_rules_block_sweet_spot_extensive() -> None:
    rules_text = Path("config/planning/week_workout_selection_rules.yaml").read_text(encoding="utf-8")

    assert "row_id: TAPER-BLOCK-SST-EXTENSIVE" in rules_text
    assert "protocol_variant: SWEET_SPOT_EXTENSIVE" in rules_text
    assert "phase_intent: taper_freshening" in rules_text
    assert "allowed: false" in rules_text


def test_unknown_publication_links_fail_closed() -> None:
    assert _normalize_publication_link("Unverified study title", "https://example.com/paper") == ""


def test_skill_config_validation_rejects_non_operational_crew_skill(tmp_path: Path) -> None:
    root = tmp_path
    crewai_dir = root / "config" / "crewai"
    crewai_dir.mkdir(parents=True)
    (root / "skills").symlink_to(Path("skills").resolve(), target_is_directory=True)
    source_dir = Path("config/crewai")
    for name in [
        "agents.yaml",
        "tasks.yaml",
        "skills.yaml",
        "knowledge_sources.yaml",
        "memory_policy.yaml",
        "task_policies.yaml",
        "flow_persistence.yaml",
        "runtime_profiles.yaml",
    ]:
        (crewai_dir / name).write_text((source_dir / name).read_text(encoding="utf-8"), encoding="utf-8")
    skills_path = crewai_dir / "skills.yaml"
    skills_path.write_text(
        skills_path.read_text(encoding="utf-8").replace(
            "skills/shared/runtime-boundaries",
            "skills/week/revision-methodology",
            1,
        ),
        encoding="utf-8",
    )

    try:
        load_crewai_config_bundle(root=root)
    except ValueError as exc:
        assert "non-operational skills" in str(exc)
    else:  # pragma: no cover - defensive failure path
        raise AssertionError("Expected load_crewai_config_bundle() to reject a crew-level method skill.")


def test_runtime_profile_validation_rejects_unknown_model(tmp_path: Path) -> None:
    root = tmp_path
    crewai_dir = root / "config" / "crewai"
    crewai_dir.mkdir(parents=True)
    (root / "skills").symlink_to(Path("skills").resolve(), target_is_directory=True)
    source_dir = Path("config/crewai")
    for name in [
        "agents.yaml",
        "tasks.yaml",
        "skills.yaml",
        "knowledge_sources.yaml",
        "memory_policy.yaml",
        "task_policies.yaml",
        "flow_persistence.yaml",
        "runtime_profiles.yaml",
    ]:
        (crewai_dir / name).write_text((source_dir / name).read_text(encoding="utf-8"), encoding="utf-8")
    runtime_profiles_path = crewai_dir / "runtime_profiles.yaml"
    runtime_profiles_path.write_text(
        runtime_profiles_path.read_text(encoding="utf-8").replace("gpt-5.4-mini", "bad-model", 1),
        encoding="utf-8",
    )

    try:
        load_crewai_config_bundle(root=root)
    except ValueError as exc:
        assert "Unknown model references in runtime_profiles.yaml" in str(exc)
    else:  # pragma: no cover - defensive failure path
        raise AssertionError("Expected load_crewai_config_bundle() to reject an unknown runtime-profile model.")


def test_artifact_envelope_guardrail_rejects_missing_meta_and_accepts_basic_shape() -> None:
    ok, payload = artifact_envelope_basic(
        SimpleNamespace(
            raw=json.dumps({"meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface"}, "data": {}})
        )
    )
    assert ok is True
    assert payload["meta"]["artifact_type"] == "WEEK_PLAN"

    failed, message = artifact_envelope_basic(SimpleNamespace(raw=json.dumps({"data": {}})))
    assert failed is False
    assert "top-level 'meta' and 'data'" in message


def test_artifact_schema_valid_guardrail_uses_concrete_json_schema() -> None:
    payload = {
        "meta": {
            "artifact_type": "SEASON_SCENARIO_SELECTION",
            "schema_id": "SeasonScenarioSelectionInterface",
            "schema_version": "1.1",
            "version": "1.0",
            "authority": "Informational",
            "owner_agent": "Season-Scenario-Agent",
            "run_id": "run-1",
            "created_at": "2026-05-17T16:07:25Z",
            "scope": "Season",
            "iso_week": "2026-20",
            "iso_week_range": "2026-20--2026-37",
            "temporal_scope": {"from": "2026-05-11", "to": "2026-09-13"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {
            "season_scenarios_ref": "season_scenarios/latest.json",
            "selected_scenario_id": "B",
            "selection_source": "system",
            "selection_rationale": "Balanced choice.",
            "notes": ["ok"],
            "kpi_moving_time_rate_guidance_selection": None,
        },
    }

    ok, validated = artifact_schema_valid(payload)
    assert ok is True
    assert validated["data"]["selected_scenario_id"] == "B"

    invalid = json.loads(json.dumps(payload))
    invalid["data"]["selected_scenario_id"] = "D"
    failed, message = artifact_schema_valid(invalid)
    assert failed is False
    assert "season_scenario_selection.schema.json" in message
    assert "selected_scenario_id" in message


def test_artifact_schema_valid_normalizes_schema_sensitive_meta_before_validation() -> None:
    payload = {
        "meta": {
            "artifact_type": "SEASON_SCENARIO_SELECTION",
            "schema_id": "SeasonPlanInterface",
            "schema_version": "20260518_175726",
            "version": "2026-20",
            "authority": "Binding",
            "owner_agent": "Season-Planner",
            "run_id": "run-1",
            "created_at": "2026-05-17T16:07:25Z",
            "scope": "Season",
            "iso_week": "2026-20",
            "iso_week_range": "2026-20--2026-37",
            "temporal_scope": {"from": "2026-05-11", "to": "2026-09-13"},
            "trace_upstream": [
                {"artifact": "SEASON_SCENARIOS", "version": "20260518_103858", "run_id": "run-a"},
            ],
            "trace_data": [
                {"artifact": "ATHLETE_PROFILE", "version": "20260315_091949", "run_id": "run-b"},
            ],
            "trace_events": [
                {"artifact": "PLANNING_EVENTS", "version": "2026-20", "run_id": "run-c"},
            ],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {
            "season_scenarios_ref": "season_scenarios/latest.json",
            "selected_scenario_id": "B",
            "selection_source": "system",
            "selection_rationale": "Balanced choice.",
            "notes": ["ok"],
            "kpi_moving_time_rate_guidance_selection": None,
        },
    }

    ok, validated = artifact_schema_valid(payload)

    assert ok is True
    meta = validated["meta"]
    assert meta["schema_id"] == "SeasonScenarioSelectionInterface"
    assert meta["schema_version"] == "1.1"
    assert meta["authority"] == "Informational"
    assert meta["owner_agent"] == "Season-Scenario-Agent"
    assert meta["version"] == "1.0"
    assert meta["trace_upstream"][0]["version"] == "1.0"
    assert meta["trace_upstream"][0]["version_key"] == "20260518_103858"
    assert meta["trace_data"][0]["version"] == "1.0"
    assert meta["trace_data"][0]["version_key"] == "20260315_091949"
    assert meta["trace_events"][0]["version"] == "1.0"
    assert meta["trace_events"][0]["version_key"] == "2026-20"


def test_season_plan_bundle_accepts_phase_blueprints_with_inherited_cadence_roles() -> None:
    model = SeasonPlanBundleModel(
        event_priority=SeasonEventAnchorModel(),
        macrocycle=SeasonMacrocycleDraftModel(deload_cadence="2:1:1", phase_length_weeks=4),
        season_load_envelope=SeasonLoadEnvelopeModel(
            expected_average_weekly_kj_range={"min": 7600, "max": 9300},
            expected_high_load_weeks_count=2,
            expected_deload_or_low_load_weeks_count=1,
        ),
        season_semantic_notes=["Frame the objective against the A event."],
        phase_blueprints=[
            SeasonPhaseBlueprintModel(
                phase_id="P03",
                iso_week_range="2026-26--2026-29",
                scenario_cadence="2:1:1",
                cadence_week_roles=["LOAD_1", "LOAD_2", "MINI_RESET", "RELOAD"],
                phase_type="BUILD",
                phase_intent="sst_build",
                build_subtype="sst_build",
                phase_taxonomy_version="canonical_phase_taxonomy_v1",
                event_constraints=[],
                load_corridor_min=7600,
                load_corridor_max=9300,
                availability_cap_kj=10000,
                baseline_load_kj=8000,
                season_phase_role="sst_build",
                role_week_load_bands=["2026-26 LOAD_1 min 7600 max 8400"],
                progression_trace=["source deterministic season phase load context"],
                load_feasibility_status="feasible",
                taper_intent="none",
                allowed_domains=["RECOVERY", "ENDURANCE", "TEMPO"],
                forbidden_domains=["THRESHOLD", "VO2MAX"],
                semantic_contract=SeasonPhaseSemanticContractModel(
                    methodology_family="extensive_subthreshold_build",
                    threshold_role="secondary",
                    event_load_policy="event_load_support_only",
                    taper_policy="not_applicable",
                    writer_semantic_notes=["Keep threshold secondary to SST-led work."],
                ),
            )
        ],
    )

    assert model.phase_blueprints[0].scenario_cadence == "2:1:1"
    assert model.phase_blueprints[0].cadence_week_roles == ["LOAD_1", "LOAD_2", "MINI_RESET", "RELOAD"]
    assert model.phase_blueprints[0].availability_cap_kj == 10000


def test_draft_bundle_models_accept_legacy_semantic_hints_before_normalization() -> None:
    season_model = SeasonPlanDraftBundleModel(
        event_priority=SeasonEventAnchorModel(),
        macrocycle=SeasonMacrocycleDraftModel(deload_cadence="2:1:1"),
        phase_blueprints=[
            SeasonPhaseDraftBlueprintModel(
                phase_id="P01",
                iso_week_range="2026-21--2026-23",
                scenario_cadence="2:1:1",
                phase_type="PREPARATION",
                phase_intent="base_preparation",
                role_week_load_bands=["legacy"],
            )
        ],
    )
    phase_model = PhaseDraftBundleModel(
        phase_range="2026-21--2026-23",
        phase_type="PREPARATION",
        phase_intent="base_preparation",
        week_blueprints=[
            PhaseWeekDraftBlueprintModel(
                week="2026-21",
                week_role="LOAD_2",
            )
        ],
        guardrails={"phase_summary": []},
        structure={"upstream_intent": []},
        preview={"phase_intent_summary": []},
        constraint_audit={"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "applied_sources": []},
        load_governance_audit={
            "blocking_issues": [],
            "warnings": [],
            "recommended_adjustments": [],
            "cadence_authority_preserved": True,
            "durability_first_respected": True,
        },
        decision_summary={"cadence_application_notes": [], "override_rationale": []},
    )

    assert season_model.phase_blueprints[0].phase_intent == "base_preparation"
    assert phase_model.week_blueprints[0].week_role == "LOAD_2"


def test_season_plan_finalize_declares_deterministic_contract_tools() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert blueprints["season_plan_finalize"].config["tools"] == [
        "workspace_get_phase_slot_contract",
        "workspace_get_season_phase_load_context",
    ]


def test_contract_context_blocks_for_season_finalize_include_bound_contracts() -> None:
    with guardrail_runtime_context(
        phase_slot_context={"phase_slots": [{"phase_id": "P01"}]},
        season_phase_load_context={"phases": [{"phase_id": "P01"}]},
    ):
        blocks = _contract_context_blocks_for_task(
            crew_name="season_planning",
            task_name="season_plan_finalize",
        )

    assert any("Deterministic Season Phase Slot Contract" in block for block in blocks)
    assert any("Deterministic Season Phase Load Contract" in block for block in blocks)
    assert any("Do not search the workspace" in block for block in blocks)


def test_season_plan_manager_disables_free_delegation_via_yaml_override() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    agent_blueprints = build_agent_blueprints(bundle)

    assert agent_blueprints["season_plan_manager"].config["allow_delegation"] is False


def test_season_macrocycle_and_finalize_guidance_support_multi_a_event_backplanning() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    macrocycle_description = blueprints["season_macrocycle_draft"].description
    season_finalize_description = blueprints["season_plan_finalize"].description
    season_finalize_expected_output = blueprints["season_plan_finalize"].expected_output

    assert "multiple target macrocycles" in macrocycle_description
    assert "A-event peak cluster" in macrocycle_description
    assert "final A-event is the only reverse-planning anchor" in season_finalize_description
    assert "backplanned macrocycles overlap" in season_finalize_description
    assert "season justification must classify each A-event" in season_finalize_expected_output


def test_phase_and_week_finalizers_declare_deterministic_contract_tools() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert blueprints["phase_bundle_finalize"].config["tools"] == [
        "workspace_get_phase_execution_context",
        "workspace_get_phase_slot_contract",
    ]
    assert blueprints["week_plan_finalize"].config["tools"] == [
        "workspace_get_week_calendar_context",
        "workspace_get_phase_execution_context",
    ]


def test_contract_context_blocks_for_phase_and_week_finalizers_include_bound_contracts() -> None:
    with guardrail_runtime_context(
        phase_slot_context={"phase_slots": [{"phase_id": "P01"}]},
        phase_execution_context={
            "phase_id": "P01",
            "phase_range": "2026-24--2026-25",
            "phase_type": "BUILD",
            "phase_intent": "shortened_re_entry",
            "build_subtype": "durability_build",
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE"],
            "phase_role_week_load_bands": [
                {"week": "2026-24", "role": "LOAD_1", "band": {"min": 7200, "max": 8200}}
            ],
            "week_role_by_iso_week": {"2026-24": "LOAD_1", "2026-25": "RELOAD"},
            "phase_primary_objective": "Rebuild load tolerance.",
            "phase_s5_bands": [],
        },
        week_calendar_context={"target_iso_week": "2026-21", "phase_week_role": "LOAD_1"},
    ):
        phase_blocks = _contract_context_blocks_for_task(
            crew_name="phase_planning",
            task_name="phase_bundle_finalize",
        )
        week_blocks = _contract_context_blocks_for_task(
            crew_name="week_planning",
            task_name="week_plan_finalize",
        )

    assert any("Deterministic Phase Execution Contract" in block for block in phase_blocks)
    assert any("Deterministic Season Phase Slot Contract" in block for block in phase_blocks)
    assert any("Do not delegate or rediscover week roles" in block for block in phase_blocks)
    assert any("Phase Finalizer Authority Freeze" in block for block in phase_blocks)
    assert any("do not call workspace tools to rediscover them" in block for block in phase_blocks)
    assert any("Deterministic Week Calendar Contract" in block for block in week_blocks)
    assert any("Deterministic Phase Execution Contract" in block for block in week_blocks)
    assert any("Do not delegate or rediscover active week role" in block for block in week_blocks)


def test_phase_bundle_finalize_authority_freeze_block_contains_exact_fields() -> None:
    with guardrail_runtime_context(
        phase_slot_context={"phase_id": "P01", "phase_range": "2026-24--2026-25"},
        phase_execution_context={
            "phase_id": "P01",
            "phase_range": "2026-24--2026-25",
            "phase_type": "BUILD",
            "phase_intent": "shortened_re_entry",
            "build_subtype": "durability_build",
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE"],
            "phase_role_week_load_bands": [
                {"week": "2026-24", "role": "LOAD_1", "band": {"min": 7200, "max": 8200}}
            ],
            "week_role_by_iso_week": {"2026-24": "LOAD_1", "2026-25": "RELOAD"},
            "phase_primary_objective": "Rebuild load tolerance.",
        },
    ):
        block = _phase_bundle_finalize_authority_freeze_block()

    assert "Phase Finalizer Authority Freeze" in block
    assert "\"phase_allowed_intensity_domains\"" in block
    assert "\"phase_forbidden_intensity_domains\"" in block
    assert "\"phase_allowed_load_modalities\"" in block
    assert "\"phase_role_week_load_bands\"" in block
    assert "\"week_role_by_iso_week\"" in block
    assert "\"phase_primary_objective\": \"Rebuild load tolerance.\"" in block


def test_phase_bundle_finalize_bound_contract_detector_requires_both_contexts() -> None:
    with guardrail_runtime_context(
        phase_execution_context={"phase_id": "P01"},
        phase_slot_context={"phase_id": "P01"},
    ):
        assert _phase_bundle_finalize_has_bound_contracts() is True
    with guardrail_runtime_context(
        phase_execution_context={"phase_id": "P01"},
        phase_slot_context={},
    ):
        assert _phase_bundle_finalize_has_bound_contracts() is False


def test_run_phase_bundle_document_narrows_only_finalizer_tools_with_bound_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )
    bundle = load_crewai_config_bundle(root=Path("."))
    task_blueprints = build_task_blueprints(bundle)
    agent_blueprints = build_agent_blueprints(bundle)
    captured: dict[str, object] = {}

    def _fake_execute(**kwargs):
        captured["tools_override_by_task"] = kwargs.get("tools_override_by_task")
        return {"guardrails": {}, "structure": {}, "preview": {}}

    monkeypatch.setattr("rps.agents.crewai_backend._execute_crewai_multiagent_crew", _fake_execute)
    tool_map = {
        name: SimpleNamespace(name=name)
        for name in [
            "workspace_get_latest",
            "workspace_get_phase_context",
            "workspace_get_phase_execution_context",
            "workspace_get_phase_slot_contract",
        ]
    }

    with guardrail_runtime_context(
        phase_execution_context={"phase_id": "P01"},
        phase_slot_context={"phase_id": "P01"},
    ):
        _run_phase_bundle_document(
            runtime=runtime,
            bundle=bundle,
            user_input="Create phase bundle.",
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=object,
            crewai_llm_cls=object,
            crew_cls=object,
            task_cls=object,
            process_cls=object,
            tools=tool_map,
            athlete_id="i150546",
            run_id="run-phase",
        )

    assert captured["tools_override_by_task"] == {"phase_bundle_finalize": []}


def test_run_phase_bundle_document_keeps_finalizer_tools_without_bound_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )
    bundle = load_crewai_config_bundle(root=Path("."))
    task_blueprints = build_task_blueprints(bundle)
    agent_blueprints = build_agent_blueprints(bundle)
    captured: dict[str, object] = {}

    def _fake_execute(**kwargs):
        captured["tools_override_by_task"] = kwargs.get("tools_override_by_task")
        return {"guardrails": {}, "structure": {}, "preview": {}}

    monkeypatch.setattr("rps.agents.crewai_backend._execute_crewai_multiagent_crew", _fake_execute)

    with guardrail_runtime_context(
        phase_execution_context={"phase_id": "P01"},
        phase_slot_context={},
    ):
        _run_phase_bundle_document(
            runtime=runtime,
            bundle=bundle,
            user_input="Create phase bundle.",
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=object,
            crewai_llm_cls=object,
            crew_cls=object,
            task_cls=object,
            process_cls=object,
            tools={},
            athlete_id="i150546",
            run_id="run-phase",
        )

    assert captured["tools_override_by_task"] is None
    with guardrail_runtime_context(
        phase_execution_context={},
        phase_slot_context={"phase_id": "P01"},
    ):
        assert _phase_bundle_finalize_has_bound_contracts() is False


def test_phase_and_week_managers_disable_free_delegation_via_yaml_override() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    agent_blueprints = build_agent_blueprints(bundle)

    assert agent_blueprints["phase_bundle_manager"].config["allow_delegation"] is False
    assert agent_blueprints["week_plan_manager"].config["allow_delegation"] is False


def test_review_finalizers_declare_deterministic_contract_tools() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert blueprints["season_review"].config["tools"] == [
        "workspace_get_phase_slot_contract",
        "workspace_get_season_phase_load_context",
    ]
    assert blueprints["phase_review"].config["tools"] == [
        "workspace_get_phase_execution_context",
        "workspace_get_phase_slot_contract",
    ]
    assert blueprints["week_review"].config["tools"] == [
        "workspace_get_week_calendar_context",
        "workspace_get_phase_execution_context",
    ]


def test_contract_context_blocks_for_review_finalizers_include_bound_contracts() -> None:
    with guardrail_runtime_context(
        phase_slot_context={"phase_slots": [{"phase_id": "P01"}]},
        season_phase_load_context={"phases": [{"phase_id": "P01"}]},
        phase_execution_context={"phase_id": "P01", "phase_s5_bands": []},
        week_calendar_context={"target_iso_week": "2026-21", "phase_week_role": "LOAD_1"},
    ):
        season_blocks = _contract_context_blocks_for_task(
            crew_name="season_review",
            task_name="season_review",
        )
        phase_blocks = _contract_context_blocks_for_task(
            crew_name="phase_review",
            task_name="phase_review",
        )
        week_blocks = _contract_context_blocks_for_task(
            crew_name="week_review",
            task_name="week_review",
        )

    assert any("Deterministic Season Phase Slot Contract" in block for block in season_blocks)
    assert any("Deterministic Season Phase Load Contract" in block for block in season_blocks)
    assert any("Season review rule" in block for block in season_blocks)
    assert any("Candidate Season Bundle is the authoritative review subject" in block for block in season_blocks)
    assert any("Deterministic Phase Execution Contract" in block for block in phase_blocks)
    assert any("Phase review rule" in block for block in phase_blocks)
    assert any("Candidate Phase Bundle is the authoritative review subject" in block for block in phase_blocks)
    assert any("Deterministic Week Calendar Contract" in block for block in week_blocks)
    assert any("Week review rule" in block for block in week_blocks)
    assert any("Candidate Week Bundle is the authoritative review subject" in block for block in week_blocks)


def test_season_review_tasks_reference_injected_candidate_bundle() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert "injected candidate season bundle" in blueprints["season_governance_review"].config["description"]
    assert "injected candidate season bundle" in blueprints["season_constraints_review"].config["description"]
    assert "injected candidate season bundle" in blueprints["season_plan_audit"].config["description"]
    assert "synthetic `candidate_season_bundle`" in blueprints["season_review"].config["description"]


def test_phase_and_week_review_tasks_reference_injected_candidate_bundle() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert "injected candidate phase bundle" in blueprints["phase_structure_review"].config["description"]
    assert "synthetic `candidate_phase_bundle`" in blueprints["phase_contract_review"].config["description"]
    assert "synthetic `candidate_phase_bundle`" in blueprints["phase_review"].config["description"]
    assert "injected candidate week bundle" in blueprints["week_contract_review"].config["description"]
    assert "synthetic `candidate_week_bundle`" in blueprints["week_review"].config["description"]


def test_review_managers_disable_free_delegation_via_yaml_override() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    agent_blueprints = build_agent_blueprints(bundle)

    assert agent_blueprints["season_review_manager"].config["allow_delegation"] is False
    assert agent_blueprints["phase_review_manager"].config["allow_delegation"] is False
    assert agent_blueprints["week_review_manager"].config["allow_delegation"] is False


def test_season_review_manager_disables_reasoning_agent_path() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    review_manager = bundle.runtime_profiles["agents"]["season_review_manager"]
    assert review_manager["model"] == "gpt-5.4-mini"
    assert review_manager["reasoning"]["enabled"] is False


def test_phase_and_week_review_managers_disable_reasoning_agent_path() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    profiles = bundle.runtime_profiles["agents"]

    phase_review_manager = profiles["phase_review_manager"]
    week_review_manager = profiles["week_review_manager"]

    assert phase_review_manager["model"] == "gpt-5.4-mini"
    assert phase_review_manager["reasoning"]["enabled"] is False
    assert week_review_manager["model"] == "gpt-5.4-mini"
    assert week_review_manager["reasoning"]["enabled"] is False


def test_bounded_phase_and_week_specialists_disable_reasoning_agent_path() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    profiles = bundle.runtime_profiles["agents"]

    for agent_name in (
        "phase_guardrail_band_specialist",
        "phase_structure_specialist",
        "phase_cadence_recovery_specialist",
        "phase_intensity_distribution_specialist",
        "phase_event_integration_specialist",
        "phase_constraint_auditor",
        "phase_governance_auditor",
        "phase_structure_reviewer",
        "week_recommendation_specialist",
        "week_load_target_specialist",
        "week_revision_specialist",
        "week_consistency_auditor",
        "week_load_governance_reviewer",
    ):
        assert profiles[agent_name]["reasoning"]["enabled"] is False, agent_name


def test_context_read_and_contract_review_tasks_use_narrow_tool_scopes() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert blueprints["season_context_read"].config["tools"] == [
        "workspace_get_input",
        "workspace_get_latest",
        "workspace_get_version",
        "workspace_get_phase_slot_contract",
        "workspace_get_season_phase_load_context",
    ]
    assert blueprints["phase_context_read"].config["tools"] == [
        "workspace_get_input",
        "workspace_get_latest",
        "workspace_get_version",
        "workspace_get_phase_context",
        "workspace_get_phase_execution_context",
        "workspace_get_phase_slot_contract",
    ]
    assert blueprints["week_context_read"].config["tools"] == [
        "workspace_get_input",
        "workspace_get_latest",
        "workspace_get_version",
        "workspace_get_phase_context",
        "workspace_get_week_calendar_context",
        "workspace_get_phase_execution_context",
    ]
    assert blueprints["report_context_read"].config["tools"] == [
        "workspace_get_input",
        "workspace_get_latest",
        "workspace_get_version",
    ]
    assert blueprints["season_contract_review"].config["tools"] == [
        "workspace_get_phase_slot_contract",
        "workspace_get_season_phase_load_context",
    ]
    assert blueprints["phase_contract_review"].config["tools"] == [
        "workspace_get_phase_execution_context",
        "workspace_get_phase_slot_contract",
    ]
    assert blueprints["week_contract_review"].config["tools"] == [
        "workspace_get_week_calendar_context",
        "workspace_get_phase_execution_context",
    ]


def test_feed_forward_and_report_review_managers_disable_free_delegation() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    agent_blueprints = build_agent_blueprints(bundle)

    assert agent_blueprints["conversation_manager"].config["allow_delegation"] is False
    assert agent_blueprints["season_feed_forward_manager"].config["allow_delegation"] is False
    assert agent_blueprints["phase_feed_forward_manager"].config["allow_delegation"] is False
    assert agent_blueprints["des_review_manager"].config["allow_delegation"] is False


def test_feed_forward_tasks_use_dedicated_manager_agents() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)

    assert blueprints["season_phase_feed_forward"].config["agent"] == "season_feed_forward_manager"
    assert blueprints["phase_feed_forward"].config["agent"] == "phase_feed_forward_manager"


def test_review_managers_use_dedicated_review_prompts() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    agent_blueprints = build_agent_blueprints(bundle)

    assert agent_blueprints["season_review_manager"].config["prompt_agent"] == "season_review_manager"
    assert agent_blueprints["phase_review_manager"].config["prompt_agent"] == "phase_review_manager"
    assert agent_blueprints["week_review_manager"].config["prompt_agent"] == "week_review_manager"
    assert agent_blueprints["des_review_manager"].config["prompt_agent"] == "des_review_manager"


def test_week_workout_authoring_specialist_uses_dedicated_prompt() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    agent_blueprints = build_agent_blueprints(bundle)

    assert agent_blueprints["week_workout_authoring_specialist"].config["prompt_agent"] == "week_workout_authoring_specialist"


def test_phase_week_blueprint_model_accepts_role_aware_s5_band() -> None:
    model = PhaseWeekBlueprintModel(
        week="2026-26",
        phase_role="Build",
        week_role="LOAD_1",
        s5_band_min=7600,
        s5_band_max=8400,
        role_progression_band="min 7500 max 8500",
        allowed_domains=["RECOVERY", "ENDURANCE", "TEMPO"],
        event_implication="none",
    )

    assert model.week_role == "LOAD_1"
    assert model.s5_band_max == 8400


def test_season_bundle_integrity_requires_phase_blueprints() -> None:
    failed, message = season_bundle_integrity(
        {
            "event_priority": {},
            "macrocycle": {},
            "phase_blueprints": [],
        }
    )
    ok, payload = season_bundle_integrity(
        {
            "event_priority": {},
            "macrocycle": {},
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "scenario_cadence": "2:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                }
            ],
        }
    )

    assert failed is False
    assert "at least one phase blueprint" in message
    assert ok is True
    assert payload["phase_blueprints"][0]["scenario_cadence"] == "2:1"


def test_season_phase_load_feasibility_rejects_unavailable_corridor_and_flat_roles() -> None:
    failed, message = season_phase_load_feasibility(
        {
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "cycle": "Build",
                    "scenario_cadence": "2:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                    "load_corridor_max": 12000,
                    "availability_cap_kj": 9000,
                    "load_feasibility_status": "feasible",
                }
            ]
        }
    )

    assert failed is False
    assert "exceeds availability_cap_kj" in message


def test_phase_week_role_load_coherence_rejects_flat_deload() -> None:
    failed, message = phase_week_role_load_coherence(
        {
            "week_blueprints": [
                {"week": "2026-20", "week_role": "LOAD_1", "s5_band_min": 7000, "s5_band_max": 8000},
                {"week": "2026-21", "week_role": "DELOAD", "s5_band_min": 7000, "s5_band_max": 7900},
            ]
        }
    )

    assert failed is False
    assert "must reduce materially" in message


def test_season_bundle_matches_contract_rejects_domains_outside_semantic_profile() -> None:
    with guardrail_runtime_context(
        phase_slot_context={
            "phase_slots": [
                {"phase_id": "P01", "iso_week_range": "2026-21--2026-23", "length_weeks": 3, "phase_intent": "shortened_re_entry"}
            ]
        },
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_intent": "shortened_re_entry",
                    "recommended_phase_corridor": {"min": 7000, "max": 9000},
                    "event_taper_trace": {},
                }
            ],
        },
    ):
        failed, message = season_bundle_matches_contract(
            {
                "event_priority": {},
                "macrocycle": {},
                "season_load_envelope": {"expected_average_weekly_kj_range": {"min": 7000, "max": 9000}},
                "season_semantic_notes": ["Frame the objective against the A event."],
                "phase_blueprints": [
                    {
                        "phase_id": "P01",
                        "iso_week_range": "2026-21--2026-23",
                        "scenario_cadence": "2:1",
                        "phase_type": "BASE",
                        "phase_intent": "shortened_re_entry",
                        "build_subtype": None,
                        "phase_taxonomy_version": "canonical_phase_taxonomy_v1",
                        "load_corridor_min": 7000,
                        "load_corridor_max": 9000,
                        "allowed_domains": ["ENDURANCE", "THRESHOLD"],
                        "forbidden_domains": ["VO2MAX"],
                        "semantic_contract": {
                            "methodology_family": "compressed_reentry",
                            "threshold_role": "forbidden",
                            "event_load_policy": "no_event_load_exception",
                            "taper_policy": "not_applicable",
                            "writer_semantic_notes": ["Keep the phase recovery-protective."],
                        },
                    }
                ],
            }
        )

    assert failed is False
    assert "season_bundle_phase_domains_outside_semantic_contract" in message


def test_normalize_season_plan_draft_bundle_overwrites_raw_semantics() -> None:
    draft_bundle = {
        "event_priority": {"primary_a_events": ["A Event"]},
        "macrocycle": {"deload_cadence": "2:1:1"},
        "phase_blueprints": [
            {
                "phase_id": "P01",
                "iso_week_range": "2026-21--2026-23",
                "scenario_cadence": "2:1:1",
                "phase_type": "PREPARATION",
                "phase_intent": "base_preparation",
                "build_subtype": None,
                "allowed_domains": ["ENDURANCE", "THRESHOLD"],
                "role_week_load_bands": ["legacy"],
            }
        ],
    }
    with guardrail_runtime_context(
        selected_scenario_contract={
            "selected_scenario_id": "B",
            "scenario_name": "Balanced build",
            "selection_source": "athlete",
            "selection_rationale": "Controlled progression",
            "load_posture": "balanced_progressive",
            "recovery_margin": "medium",
            "fatigue_exposure": "moderate",
            "specificity_density": "controlled",
            "load_philosophy": "balanced_progressive",
            "risk_profile": "medium",
            "constraint_summary": ["preserve continuity"],
            "event_alignment_notes": ["B rehearsal"],
            "risk_flags": ["stable recovery required"],
            "kpi_guardrail_notes": ["repeatable load"],
            "decision_notes": ["athlete selected B"],
            "season_archetype": "none",
            "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "forbidden_intensity_domains": ["VO2MAX"],
            "deload_cadence": "2:1:1",
        },
        phase_slot_context={
            "phase_slots": [
                {"phase_id": "P01", "iso_week_range": "2026-21--2026-23", "length_weeks": 3, "phase_intent": "shortened_re_entry"}
            ]
        },
        season_phase_load_context={
            "selected_scenario_contract": {
                "selected_scenario_id": "B",
                "scenario_name": "Balanced build",
                "selection_source": "athlete",
                "selection_rationale": "Controlled progression",
                "load_posture": "balanced_progressive",
                "recovery_margin": "medium",
                "fatigue_exposure": "moderate",
                "specificity_density": "controlled",
                "load_philosophy": "balanced_progressive",
                "risk_profile": "medium",
                "constraint_summary": ["preserve continuity"],
                "event_alignment_notes": ["B rehearsal"],
                "risk_flags": ["stable recovery required"],
                "kpi_guardrail_notes": ["repeatable load"],
                "decision_notes": ["athlete selected B"],
                "season_archetype": "none",
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "forbidden_intensity_domains": ["VO2MAX"],
                "deload_cadence": "2:1:1",
            },
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "season_phase_role": "shortened_re_entry",
                    "scenario_cadence": "2:1:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "MINI_RESET"],
                    "availability_cap_kj": {"typical": 10000, "max": 11000},
                    "baseline_load_kj": 8200,
                    "recommended_phase_corridor": {"min": 7800, "max": 9800},
                    "role_week_load_bands": [
                        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}},
                    ],
                    "progression_trace": {"source": "deterministic"},
                }
            ],
        }
    ):
        normalized = normalize_season_plan_draft_bundle(draft_bundle)
        ok, _ = season_bundle_matches_contract(normalized)

    blueprint = normalized["phase_blueprints"][0]
    assert blueprint["phase_type"] == "BASE"
    assert blueprint["phase_intent"] == "shortened_re_entry"
    assert blueprint["allowed_domains"] == ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"]
    assert blueprint["allowed_load_modalities"] == ["NONE", "K3"]
    assert "THRESHOLD" in blueprint["forbidden_domains"]
    assert "VO2MAX" in blueprint["forbidden_domains"]
    assert blueprint["phase_taxonomy_version"] == "canonical_phase_taxonomy_v1"
    assert blueprint["role_week_load_bands"] == [
        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}}
    ]
    assert normalized["season_load_envelope"]["expected_average_weekly_kj_range"] == {"min": 7800, "max": 9800}
    assert normalized["selected_scenario_contract"]["selected_scenario_id"] == "B"
    assert ok is True


def test_season_bundle_matches_contract_accepts_selected_scenario_contract_in_synthetic_candidate() -> None:
    normalized = {
        "event_priority": {"primary_a_events": ["A Event"]},
        "macrocycle": {"deload_cadence": "2:1:1"},
        "season_load_envelope": {"expected_average_weekly_kj_range": {"min": 7800, "max": 9800}},
        "season_semantic_notes": ["Frame the objective against the A event."],
        "phase_blueprints": [
            {
                "phase_id": "P01",
                "iso_week_range": "2026-21--2026-23",
                "scenario_cadence": "2:1:1",
                "phase_type": "BASE",
                "phase_intent": "shortened_re_entry",
                "build_subtype": None,
                "phase_taxonomy_version": "canonical_phase_taxonomy_v1",
                "load_corridor_min": 7800,
                "load_corridor_max": 9800,
                "allowed_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                "allowed_load_modalities": ["NONE", "K3"],
                "forbidden_domains": ["THRESHOLD", "VO2MAX"],
                "role_week_load_bands": [
                    {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}}
                ],
                "semantic_contract": {
                    "methodology_family": "compressed_reentry",
                    "threshold_role": "forbidden",
                    "event_load_policy": "no_event_load_exception",
                    "taper_policy": "not_applicable",
                    "writer_semantic_notes": ["Keep the phase recovery-protective."],
                },
            }
        ],
        "selected_scenario_contract": {
            "selected_scenario_id": "B",
            "scenario_name": "Balanced build",
            "selection_source": "athlete",
            "selection_rationale": "Controlled progression",
            "load_posture": "balanced_progressive",
            "recovery_margin": "medium",
            "fatigue_exposure": "moderate",
            "specificity_density": "controlled",
            "load_philosophy": "balanced_progressive",
            "risk_profile": "medium",
            "constraint_summary": ["preserve continuity"],
            "event_alignment_notes": ["B rehearsal"],
            "risk_flags": ["stable recovery required"],
            "kpi_guardrail_notes": ["repeatable load"],
            "decision_notes": ["athlete selected B"],
            "season_archetype": "none",
            "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "forbidden_intensity_domains": ["VO2MAX"],
            "deload_cadence": "2:1:1",
        },
    }
    with guardrail_runtime_context(
        phase_slot_context={
            "phase_slots": [
                {"phase_id": "P01", "iso_week_range": "2026-21--2026-23", "length_weeks": 3, "phase_intent": "shortened_re_entry"}
            ]
        },
        selected_scenario_contract=normalized["selected_scenario_contract"],
        season_phase_load_context={
            "selected_scenario_contract": normalized["selected_scenario_contract"],
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "season_phase_role": "shortened_re_entry",
                    "scenario_cadence": "2:1:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "MINI_RESET"],
                    "availability_cap_kj": {"typical": 10000, "max": 11000},
                    "baseline_load_kj": 8200,
                    "recommended_phase_corridor": {"min": 7800, "max": 9800},
                    "role_week_load_bands": [
                        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}},
                    ],
                    "progression_trace": {"source": "deterministic"},
                    "event_taper_trace": {},
                }
            ],
        },
    ):
        ok, message = season_bundle_matches_contract(normalized)

    assert ok is True, message


def test_normalize_season_plan_draft_bundle_supports_variable_phase_counts() -> None:
    draft_bundle = {
        "event_priority": {"primary_a_events": ["A1", "A2"]},
        "macrocycle": {"deload_cadence": "2:1:1"},
        "phase_blueprints": [
            {"phase_id": f"P0{idx}", "iso_week_range": f"2026-{20 + idx}--2026-{20 + idx}", "scenario_cadence": "2:1:1"}
            for idx in range(1, 7)
        ],
    }
    context_phases = []
    intents = [
        ("BASE", "shortened_re_entry"),
        ("BASE", "general_base"),
        ("BUILD", "durability_build"),
        ("TAPER", "taper_freshening"),
        ("BASE", "shortened_re_entry"),
        ("TAPER", "taper_freshening"),
    ]
    for idx, (phase_type, phase_intent) in enumerate(intents, start=1):
        context_phases.append(
            {
                "phase_id": f"P0{idx}",
                "iso_week_range": f"2026-{20 + idx}--2026-{20 + idx}",
                "phase_type": phase_type,
                "phase_intent": phase_intent,
                "build_subtype": phase_intent if phase_type == "BUILD" else None,
                "season_phase_role": phase_intent,
                "scenario_cadence": "2:1:1",
                "cadence_week_roles": ["LOAD_1"],
                "availability_cap_kj": {"typical": 10000, "max": 11000},
                "baseline_load_kj": 8000 + idx,
                "recommended_phase_corridor": {"min": 7000 + idx, "max": 9000 + idx},
                "role_week_load_bands": [{"week": f"2026-{20 + idx}", "role": "LOAD_1", "band": {"min": 7000 + idx, "max": 9000 + idx}}],
                "progression_trace": {"index": idx},
            }
        )
    with guardrail_runtime_context(
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": context_phases,
        }
    ):
        normalized = normalize_season_plan_draft_bundle(draft_bundle)

    assert len(normalized["phase_blueprints"]) == 6
    assert normalized["phase_blueprints"][2]["build_subtype"] == "durability_build"
    assert normalized["phase_blueprints"][5]["phase_intent"] == "taper_freshening"
    assert normalized["season_load_envelope"]["expected_high_load_weeks_count"] == 0
    assert normalized["season_load_envelope"]["expected_deload_or_low_load_weeks_count"] == 0


def test_normalize_season_plan_draft_bundle_derives_envelope_counts_when_missing() -> None:
    draft_bundle = {
        "event_priority": {"primary_a_events": ["A1"]},
        "macrocycle": {"deload_cadence": "2:1:1"},
        "season_load_envelope": {"expected_average_weekly_kj_range": {"min": 1, "max": 2}},
        "phase_blueprints": [
            {"phase_id": "P01", "iso_week_range": "2026-21--2026-23", "scenario_cadence": "2:1:1"},
            {"phase_id": "P02", "iso_week_range": "2026-24--2026-27", "scenario_cadence": "2:1:1"},
        ],
    }
    with guardrail_runtime_context(
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "season_phase_role": "shortened_re_entry",
                    "scenario_cadence": "2:1:1",
                    "cadence_week_roles": ["SHORTENED_RE_ENTRY", "SHORTENED_CONSOLIDATION", "SHORTENED_MINI_RESET"],
                    "availability_cap_kj": {"typical": 10000, "max": 11000},
                    "baseline_load_kj": 8200,
                    "recommended_phase_corridor": {"min": 7800, "max": 9800},
                    "role_week_load_bands": [],
                    "progression_trace": {"source": "deterministic"},
                },
                {
                    "phase_id": "P02",
                    "iso_week_range": "2026-24--2026-27",
                    "phase_type": "BUILD",
                    "phase_intent": "durability_build",
                    "build_subtype": "durability_build",
                    "season_phase_role": "durability_build",
                    "scenario_cadence": "2:1:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "MINI_RESET", "RELOAD"],
                    "availability_cap_kj": {"typical": 12000, "max": 13000},
                    "baseline_load_kj": 9200,
                    "recommended_phase_corridor": {"min": 9000, "max": 12000},
                    "role_week_load_bands": [],
                    "progression_trace": {"source": "deterministic"},
                },
            ],
        }
    ):
        normalized = normalize_season_plan_draft_bundle(draft_bundle)

    envelope = normalized["season_load_envelope"]
    assert envelope["expected_high_load_weeks_count"] == 2
    assert envelope["expected_deload_or_low_load_weeks_count"] == 3


def test_normalize_season_plan_draft_bundle_canonicalizes_invalid_deterministic_phase_type() -> None:
    draft_bundle = {
        "event_priority": {"primary_a_events": ["A1"]},
        "macrocycle": {"deload_cadence": "2:1:1"},
        "phase_blueprints": [
            {
                "phase_id": "P02",
                "iso_week_range": "2026-24--2026-25",
                "scenario_cadence": "2:1:1",
            }
        ],
    }
    with guardrail_runtime_context(
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
            "phases": [
                {
                    "phase_id": "P02",
                    "iso_week_range": "2026-24--2026-25",
                    "phase_type": "PREPARATION",
                    "phase_intent": "general_base",
                    "build_subtype": None,
                    "season_phase_role": "general_base",
                    "scenario_cadence": "2:1:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2"],
                    "availability_cap_kj": {"typical": 10000, "max": 11000},
                    "baseline_load_kj": 8200,
                    "recommended_phase_corridor": {"min": 7800, "max": 9800},
                    "role_week_load_bands": [],
                    "progression_trace": {"source": "deterministic"},
                }
            ],
        }
    ):
        normalized = normalize_season_plan_draft_bundle(draft_bundle)
        ok, message = season_bundle_matches_contract(normalized)

    blueprint = normalized["phase_blueprints"][0]
    assert blueprint["phase_type"] == "BASE"
    assert blueprint["phase_intent"] == "general_base"
    assert any("canonicalized phase_type" in warning for warning in blueprint["warnings"])
    assert ok is True, message


def test_normalize_phase_draft_bundle_overwrites_top_level_semantics_and_week_contracts() -> None:
    draft_bundle = {
        "phase_range": "2026-21--2026-23",
        "phase_type": "PREPARATION",
        "phase_intent": "base_preparation",
        "week_blueprints": [
            {"week": "2026-21", "week_role": "LOAD_2", "s5_band_min": 7000, "s5_band_max": 9000},
        ],
        "guardrails": {"phase_summary": []},
        "structure": {"upstream_intent": []},
        "preview": {"phase_intent_summary": []},
        "constraint_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "applied_sources": []},
        "load_governance_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "cadence_authority_preserved": True, "durability_first_respected": True},
        "decision_summary": {"cadence_application_notes": [], "override_rationale": []},
    }
    with guardrail_runtime_context(
        phase_execution_context={
            "phase_id": "P01",
            "phase_iso_week_range": "2026-21--2026-23",
            "phase_type": "BASE",
            "phase_role": "BASE",
            "phase_intent": "shortened_re_entry",
            "build_subtype": None,
            "inherited_scenario_contract": {"selected_scenario_id": "B", "load_posture": "balanced_progressive"},
            "week_role_by_iso_week": {"2026-21": "LOAD_1"},
            "phase_s5_bands": [{"week": "2026-21", "band": {"min": 7800, "max": 8600}}],
        }
    ):
        normalized = normalize_phase_draft_bundle(draft_bundle)

    assert normalized["phase_id"] == "P01"
    assert normalized["phase_type"] == "BASE"
    assert normalized["phase_intent"] == "shortened_re_entry"
    assert normalized["inherited_scenario_contract"]["selected_scenario_id"] == "B"
    assert normalized["guardrails"]["phase_intent"] == "shortened_re_entry"
    assert normalized["structure"]["phase_intent"] == "shortened_re_entry"
    assert normalized["preview"]["phase_intent"] == "shortened_re_entry"
    assert normalized["week_blueprints"][0]["week_role"] == "LOAD_1"
    assert normalized["week_blueprints"][0]["s5_band_min"] == 7800
    assert normalized["week_blueprints"][0]["s5_band_max"] == 8600


def test_normalize_phase_draft_bundle_rewrites_nested_narrative_phase_intents() -> None:
    draft_bundle = {
        "phase_range": "2026-24--2026-25",
        "phase_type": "BASE",
        "phase_intent": "wrong",
        "week_blueprints": [
            {"week": "2026-24", "week_role": "LOAD_2", "s5_band_min": 7000, "s5_band_max": 9000},
        ],
        "guardrails": {
            "phase_intent": "Re-establish stable training continuity under moderated load.",
            "phase_summary": ["summary"],
        },
        "structure": {
            "phase_intent": "Controlled re-entry narrative",
            "upstream_intent": ["x"],
        },
        "preview": {
            "phase_intent": "Keep the weeks feeling stable and aerobic.",
            "phase_intent_summary": ["summary"],
        },
        "constraint_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "applied_sources": []},
        "load_governance_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "cadence_authority_preserved": True, "durability_first_respected": True},
        "decision_summary": {"cadence_application_notes": [], "override_rationale": []},
    }
    with guardrail_runtime_context(
        phase_execution_context={
            "phase_id": "P01",
            "phase_iso_week_range": "2026-24--2026-25",
            "phase_type": "BASE",
            "phase_role": "BASE",
            "phase_intent": "shortened_re_entry",
            "build_subtype": None,
            "week_role_by_iso_week": {"2026-24": "SHORTENED_RE_ENTRY"},
            "phase_s5_bands": [{"week": "2026-24", "band": {"min": 7893, "max": 10148}}],
        }
    ):
        normalized = normalize_phase_draft_bundle(draft_bundle)

    assert normalized["phase_intent"] == "shortened_re_entry"
    assert normalized["guardrails"]["phase_intent"] == "shortened_re_entry"
    assert normalized["structure"]["phase_intent"] == "shortened_re_entry"
    assert normalized["preview"]["phase_intent"] == "shortened_re_entry"
    assert normalized["week_blueprints"][0]["phase_intent"] == "shortened_re_entry"


def test_normalize_phase_draft_bundle_raises_when_canonical_phase_intent_missing() -> None:
    draft_bundle = {
        "phase_range": "2026-24--2026-25",
        "guardrails": {"phase_summary": ["summary"]},
        "structure": {"upstream_intent": ["x"]},
        "preview": {"phase_intent_summary": ["summary"]},
        "constraint_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "applied_sources": []},
        "load_governance_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "cadence_authority_preserved": True, "durability_first_respected": True},
        "decision_summary": {"cadence_application_notes": [], "override_rationale": []},
    }
    with guardrail_runtime_context(
        phase_execution_context={
            "phase_id": "P01",
            "phase_iso_week_range": "2026-24--2026-25",
            "phase_type": "BASE",
            "phase_role": "BASE",
            "phase_intent": "",
        }
    ):
        with pytest.raises(RuntimeError, match="phase_execution_context\\.phase_intent"):
            normalize_phase_draft_bundle(draft_bundle)


def test_phase_bundle_matches_context_accepts_inherited_scenario_contract_in_synthetic_candidate() -> None:
    draft_bundle = {
        "phase_range": "2026-21--2026-23",
        "phase_type": "PREPARATION",
        "phase_intent": "base_preparation",
        "week_blueprints": [
            {"week": "2026-21", "week_role": "LOAD_2", "s5_band_min": 7000, "s5_band_max": 9000},
        ],
        "guardrails": {"phase_summary": []},
        "structure": {"upstream_intent": []},
        "preview": {"phase_intent_summary": []},
        "constraint_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "applied_sources": []},
        "load_governance_audit": {"blocking_issues": [], "warnings": [], "recommended_adjustments": [], "cadence_authority_preserved": True, "durability_first_respected": True},
        "decision_summary": {"cadence_application_notes": [], "override_rationale": []},
    }
    with guardrail_runtime_context(
        phase_execution_context={
            "phase_id": "P01",
            "phase_iso_week_range": "2026-21--2026-23",
            "phase_type": "BASE",
            "phase_role": "BASE",
            "phase_intent": "shortened_re_entry",
            "build_subtype": None,
            "inherited_scenario_contract": {"selected_scenario_id": "B", "load_posture": "balanced_progressive"},
            "week_role_by_iso_week": {"2026-21": "LOAD_1"},
            "phase_s5_bands": [{"week": "2026-21", "band": {"min": 7800, "max": 8600}}],
        }
    ):
        normalized = normalize_phase_draft_bundle(draft_bundle)
        ok, message = phase_bundle_matches_context(normalized)

    assert normalized["inherited_scenario_contract"]["selected_scenario_id"] == "B"
    assert ok is True, message


def test_phase_bundle_matches_context_does_not_require_missing_authority_contract() -> None:
    mapping = {
        "week_blueprints": [
            {"week": "2026-21", "week_role": "LOAD_1", "s5_band_min": 7800, "s5_band_max": 8600},
        ]
    }
    with guardrail_runtime_context(
        phase_execution_context={
            "week_role_by_iso_week": {"2026-21": "LOAD_1"},
            "phase_s5_bands": [{"week": "2026-21", "band": {"min": 7800, "max": 8600}}],
        }
    ):
        ok, message = phase_bundle_matches_context(mapping)

    assert ok is True, message


def test_phase_structure_writer_guardrails_pre_normalize_exact_phase_authority() -> None:
    candidate = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "inherited_scenario_contract": {"selected_scenario_id": "B"},
            "upstream_intent": {"primary_objective": "Wrong objective"},
            "structural_phase_elements": {
                "allowed_day_roles": ["ENDURANCE", "QUALITY"],
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "allowed_load_modalities": ["NONE", "K3"],
            },
            "execution_principles": {
                "load_intensity_handling": {"forbidden_intensity_domains": ["VO2MAX"]},
            },
            "load_ranges": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 6000, "max": 7000}},
                    {"week": "2026-25", "band": {"min": 6100, "max": 7100}},
                ],
                "source": "wrong.json",
            },
            "week_skeleton_logic": {
                "week_roles": {
                    "week_roles": [
                        {"week": "2026-24", "role": "LOAD_1"},
                        {"week": "2026-25", "role": "RELOAD"},
                    ]
                }
            },
        },
    }
    phase_guardrails = {
        "meta": {"artifact_type": "PHASE_GUARDRAILS", "version_key": "2026-24--2026-25__20260608_090000"},
        "data": {
            "load_guardrails": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
                    {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
                ]
            }
        },
    }
    wrapped_context_match = crewai_guardrails._with_guardrail_telemetry(
        "phase_structure",
        "phase_execution_context_match",
        crewai_guardrails.phase_execution_context_match,
    )
    wrapped_weeks_match = crewai_guardrails._with_guardrail_telemetry(
        "phase_structure",
        "phase_weeks_match_range",
        crewai_guardrails.phase_weeks_match_range,
    )
    wrapped_load_coherence = crewai_guardrails._with_guardrail_telemetry(
        "phase_structure",
        "phase_week_role_load_coherence",
        crewai_guardrails.phase_week_role_load_coherence,
    )

    with guardrail_runtime_context(
        artifact_type="PHASE_STRUCTURE",
        loaded_inputs={
            "phase_guardrails": {
                "ok": True,
                "document": phase_guardrails,
                "version_key": "2026-24--2026-25__20260608_090000",
            },
        },
        phase_execution_context={
            "inherited_scenario_contract": {"selected_scenario_id": "B"},
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE"],
            "phase_primary_objective": "Rebuild load tolerance with controlled sweet spot support.",
            "week_role_by_iso_week": {"2026-24": "LOAD_1", "2026-25": "RELOAD"},
            "phase_role_week_load_bands": [
                {"week": "2026-24", "role": "LOAD_1", "band": {"min": 7200, "max": 8200}},
                {"week": "2026-25", "role": "RELOAD", "band": {"min": 7300, "max": 8300}},
            ],
        },
    ):
        ok_context, repaired_context = wrapped_context_match(candidate)
        ok_weeks, repaired_weeks = wrapped_weeks_match(candidate)
        ok_coherence, repaired_coherence = wrapped_load_coherence(candidate)

    assert ok_context is True, repaired_context
    assert ok_weeks is True, repaired_weeks
    assert ok_coherence is True, repaired_coherence
    assert repaired_context["data"]["structural_phase_elements"]["allowed_intensity_domains"] == [
        "RECOVERY",
        "ENDURANCE",
        "TEMPO",
        "SWEET_SPOT",
    ]
    assert repaired_context["data"]["structural_phase_elements"]["allowed_load_modalities"] == ["NONE"]
    assert repaired_context["data"]["execution_principles"]["load_intensity_handling"][
        "forbidden_intensity_domains"
    ] == ["THRESHOLD", "VO2MAX"]
    assert repaired_context["data"]["upstream_intent"]["primary_objective"] == (
        "Rebuild load tolerance with controlled sweet spot support."
    )
    assert repaired_context["data"]["load_ranges"]["weekly_kj_bands"] == [
        {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
        {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
    ]
    assert (
        repaired_context["data"]["load_ranges"]["source"]
        == "phase_guardrails_2026-24--2026-25__20260608_090000.json"
    )


def test_phase_structure_writer_guardrails_fail_cleanly_without_execution_context_authority() -> None:
    candidate = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "structural_phase_elements": {
                "allowed_day_roles": ["ENDURANCE", "QUALITY"],
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "allowed_load_modalities": ["NONE", "K3"],
            },
            "load_ranges": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
                    {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
                ]
            },
        },
    }
    wrapped = crewai_guardrails._with_guardrail_telemetry(
        "phase_structure",
        "phase_execution_context_match",
        crewai_guardrails.phase_execution_context_match,
    )

    with guardrail_runtime_context(
        artifact_type="PHASE_STRUCTURE",
        loaded_inputs={
            "phase_guardrails": {
                "ok": True,
                "document": {
                    "data": {
                        "load_guardrails": {
                            "weekly_kj_bands": [
                                {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
                                {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
                            ]
                        }
                    }
                },
                "version_key": "2026-24--2026-25__20260608_090000",
            }
        },
        phase_execution_context={},
    ):
        ok, message = wrapped(candidate)

    assert ok is False
    assert "pre_guardrail_normalization_failed" in message
    assert "phase_execution_context.phase_allowed_intensity_domains" in message


def test_phase_structure_writer_guardrails_fail_cleanly_without_phase_guardrails_bands() -> None:
    candidate = {
        "meta": {"artifact_type": "PHASE_STRUCTURE", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "structural_phase_elements": {
                "allowed_day_roles": ["ENDURANCE", "QUALITY"],
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "allowed_load_modalities": ["NONE", "K3"],
            },
            "load_ranges": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 7200, "max": 8200}},
                    {"week": "2026-25", "band": {"min": 7300, "max": 8300}},
                ]
            },
        },
    }
    wrapped = crewai_guardrails._with_guardrail_telemetry(
        "phase_structure",
        "phase_execution_context_match",
        crewai_guardrails.phase_execution_context_match,
    )

    with guardrail_runtime_context(
        artifact_type="PHASE_STRUCTURE",
        loaded_inputs={},
        phase_execution_context={
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE"],
            "week_role_by_iso_week": {"2026-24": "LOAD_1", "2026-25": "RELOAD"},
            "phase_role_week_load_bands": [
                {"week": "2026-24", "role": "LOAD_1", "band": {"min": 7200, "max": 8200}},
                {"week": "2026-25", "role": "RELOAD", "band": {"min": 7300, "max": 8300}},
            ],
        },
    ):
        ok, message = wrapped(candidate)

    assert ok is False
    assert "pre_guardrail_normalization_failed" in message
    assert "phase_guardrails.data.load_guardrails.weekly_kj_bands" in message


def test_phase_writer_authority_context_block_frontloads_exact_phase_fields() -> None:
    phase_structure = {
        "meta": {"version_key": "2026-24--2026-25__20260608_091500"},
        "data": {
            "upstream_intent": {
                "phase_type": "BUILD",
                "phase_intent": "shortened_re_entry",
                "build_subtype": "durability_build",
                "phase_taxonomy_version": "v2",
                "primary_objective": "Rebuild load tolerance.",
            }
        },
    }

    with guardrail_runtime_context(
        phase_execution_context={
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE"],
            "phase_primary_objective": "Rebuild load tolerance.",
            "week_role_by_iso_week": {"2026-24": "LOAD_1", "2026-25": "RELOAD"},
            "phase_role_week_load_bands": [
                {"week": "2026-24", "role": "LOAD_1", "band": {"min": 7200, "max": 8200}},
                {"week": "2026-25", "role": "RELOAD", "band": {"min": 7300, "max": 8300}},
            ],
        }
    ):
        structure_block = _phase_writer_authority_context_block(
            AgentTask.CREATE_PHASE_STRUCTURE,
            {
                "phase_guardrails": {
                    "version_key": "2026-24--2026-25__20260608_090000",
                }
            },
        )
        preview_block = _phase_writer_authority_context_block(
            AgentTask.CREATE_PHASE_PREVIEW,
            {
                "phase_structure": {
                    "document": phase_structure,
                    "version_key": "2026-24--2026-25__20260608_091500",
                }
            },
        )

    assert "Exact writer authority" in structure_block
    assert "\"allowed_intensity_domains\"" in structure_block
    assert "\"phase_guardrails_source\": \"phase_guardrails_2026-24--2026-25__20260608_090000.json\"" in structure_block
    assert "\"phase_role_week_load_bands\"" in structure_block
    assert "Exact writer authority" in preview_block
    assert "\"rest_days\": \"REST -> NONE/NONE\"" in preview_block
    assert "\"recovery_days\": \"RECOVERY -> RECOVERY\"" in preview_block
    assert "\"phase_structure_source\": \"phase_structure_2026-24--2026-25__20260608_091500.json\"" in preview_block


def test_phase_active_files_frontload_exact_legality_and_operational_none_rules() -> None:
    tasks_text = Path("config/crewai/tasks.yaml").read_text(encoding="utf-8")
    guardrails_skill_text = Path("skills/phase/guardrails-authoring/SKILL.md").read_text(encoding="utf-8")
    structure_skill_text = Path("skills/phase/structure-authoring/SKILL.md").read_text(encoding="utf-8")
    writer_skill_text = Path("skills/phase/artifact-writing/SKILL.md").read_text(encoding="utf-8")
    preview_skill_text = Path("skills/phase/preview-synthesis/SKILL.md").read_text(encoding="utf-8")
    finalizer_prompt_text = Path("prompts/agents/phase_bundle_manager.md").read_text(encoding="utf-8")
    finalizer_skill_text = Path("skills/phase/bundle-synthesis/SKILL.md").read_text(encoding="utf-8")

    assert "do not add `NONE`" in tasks_text
    assert "do not include `NONE` in `PHASE_STRUCTURE.allowed_intensity_domains`" in tasks_text
    assert "do not call `workspace_get_phase_execution_context` or `workspace_get_phase_slot_contract`" in tasks_text
    assert "Exact week bands come from persisted Season phase authority and must be copied, not recomputed from S5." in tasks_text
    assert "canonical `quality_intent` is `Stabilization`" in tasks_text
    assert "must formally trace the exact stored `PHASE_GUARDRAILS`" in tasks_text
    assert "must formally trace the exact stored `PHASE_STRUCTURE`" in tasks_text
    assert "Treat inherited scenario contract as season posture ceiling only" in guardrails_skill_text
    assert "allowed_intensity_domains" in structure_skill_text
    assert "do not add `NONE`" in structure_skill_text
    assert "must not include `NONE`" in writer_skill_text
    assert "weekly_kj_bands` must be copied from injected deterministic phase authority" in writer_skill_text
    assert "phase legality fields remain separate from the scenario ceiling" in writer_skill_text
    assert "Preview may use `NONE` only on `REST` or fixed non-training days" in preview_skill_text
    assert "Phase Finalizer Authority Freeze" in finalizer_prompt_text
    assert "do not call `workspace_get_phase_execution_context` or `workspace_get_phase_slot_contract`" in finalizer_prompt_text
    assert "Compact authority-freeze example" in finalizer_skill_text
    assert "use tools only as fallback for genuinely missing authority fields" in finalizer_skill_text


def test_phase_guardrails_writer_guardrails_pre_normalize_exact_phase_authority() -> None:
    candidate = {
        "meta": {"artifact_type": "PHASE_GUARDRAILS", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "phase_summary": {"primary_objective": "Wrong objective"},
            "load_guardrails": {
                "weekly_kj_bands": [
                    {"week": "2026-24", "band": {"min": 7893, "max": 8626}},
                ]
            },
            "allowed_forbidden_semantics": {
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "forbidden_intensity_domains": ["VO2MAX"],
                "allowed_load_modalities": ["NONE"],
                "quality_density": {"quality_intent": "Build"},
            },
            "inherited_scenario_contract": {
                "allowed_intensity_domains": ["ENDURANCE"],
                "forbidden_intensity_domains": ["VO2MAX", "THRESHOLD"],
            },
        },
    }
    season_plan = {
        "data": {
            "selected_scenario_contract": {
                "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT", "THRESHOLD"],
                "forbidden_intensity_domains": ["VO2MAX"],
            }
        }
    }
    with guardrail_runtime_context(
        artifact_type="PHASE_GUARDRAILS",
        loaded_inputs={"season_plan": {"ok": True, "document": season_plan}},
        phase_execution_context={
            "phase_type": "BASE",
            "phase_intent": "shortened_re_entry",
            "phase_primary_objective": "Re-establish stable training continuity without overreaching.",
            "phase_allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phase_forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "phase_allowed_load_modalities": ["NONE", "K3"],
            "phase_role_week_load_bands": [
                {"week": "2026-24", "role": "SHORTENED_RE_ENTRY", "band": {"min": 7893, "max": 10148}},
                {"week": "2026-25", "role": "SHORTENED_CONSOLIDATION", "band": {"min": 9020, "max": 11275}},
            ],
        },
    ):
        repaired = crewai_guardrails.normalize_artifact_candidate_for_task_guardrails(candidate)

    assert repaired["data"]["load_guardrails"]["weekly_kj_bands"][0]["band"]["max"] == 10148
    assert repaired["data"]["load_guardrails"]["weekly_kj_bands"][0]["band"]["notes"] == (
        "role SHORTENED_RE_ENTRY; S5 deterministic band is 7893-10148; feasible band max is 10148"
    )
    assert "role" not in repaired["data"]["load_guardrails"]["weekly_kj_bands"][0]
    assert repaired["data"]["phase_summary"]["primary_objective"] == (
        "Re-establish stable training continuity without overreaching."
    )
    assert repaired["data"]["allowed_forbidden_semantics"]["allowed_intensity_domains"] == [
        "RECOVERY",
        "ENDURANCE",
        "TEMPO",
        "SWEET_SPOT",
    ]
    assert repaired["data"]["allowed_forbidden_semantics"]["forbidden_intensity_domains"] == [
        "THRESHOLD",
        "VO2MAX",
    ]
    assert repaired["data"]["allowed_forbidden_semantics"]["quality_density"]["quality_intent"] == "Stabilization"
    assert repaired["data"]["inherited_scenario_contract"] == season_plan["data"]["selected_scenario_contract"]


def test_phase_preview_writer_guardrails_pre_normalize_shared_skeleton_semantics() -> None:
    candidate = {
        "meta": {"artifact_type": "PHASE_PREVIEW", "iso_week_range": "2026-24--2026-25"},
        "data": {
            "phase_intent_summary": {"primary_objective": "Wrong objective"},
            "weekly_agenda_preview": [
                {
                    "week": "2026-24",
                    "days": [
                        {"day_of_week": "Mon", "day_role": "REST", "intensity_domain": "TEMPO", "load_modality": "K3"},
                        {"day_of_week": "Tue", "day_role": "RECOVERY", "intensity_domain": "ENDURANCE", "load_modality": "K3"},
                        {"day_of_week": "Wed", "day_role": "QUALITY", "intensity_domain": "THRESHOLD", "load_modality": "NONE"},
                        {"day_of_week": "Thu", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                        {"day_of_week": "Fri", "day_role": "REST", "intensity_domain": "SWEET_SPOT", "load_modality": "K3"},
                        {"day_of_week": "Sat", "day_role": "QUALITY", "intensity_domain": "SWEET_SPOT", "load_modality": "NONE"},
                        {"day_of_week": "Sun", "day_role": "ENDURANCE", "intensity_domain": "ENDURANCE", "load_modality": "NONE"},
                    ],
                }
            ],
        },
    }
    phase_structure = {
        "meta": {"artifact_type": "PHASE_STRUCTURE"},
        "data": {
            "upstream_intent": {
                "phase_intent": "shortened_re_entry",
                "build_subtype": None,
                "primary_objective": "Rebuild load tolerance with controlled sweet spot support.",
            },
            "structural_phase_elements": {
                "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
                "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                "allowed_load_modalities": ["NONE"],
            },
            "execution_principles": {
                "load_intensity_handling": {"max_quality_days_per_week": 1},
                "recovery_protection": {"fixed_non_training_days": ["Mon", "Fri"]},
            },
            "week_skeleton_logic": {
                "week_roles": {
                    "week_roles": [
                        {"week": "2026-24", "role": "LOAD_1"},
                        {"week": "2026-25", "role": "RELOAD"},
                    ]
                }
            },
        },
    }
    with guardrail_runtime_context(
        artifact_type="PHASE_PREVIEW",
        loaded_inputs={
            "phase_structure": {
                "ok": True,
                "document": phase_structure,
                "version_key": "2026-24--2026-25__20260608_091500",
            }
        },
    ):
        repaired = crewai_guardrails.normalize_artifact_candidate_for_task_guardrails(candidate)

    assert repaired["data"]["phase_intent_summary"]["primary_objective"] == (
        "Rebuild load tolerance with controlled sweet spot support."
    )
    days = repaired["data"]["weekly_agenda_preview"][0]["days"]
    assert days[0]["intensity_domain"] == "NONE"
    assert days[0]["load_modality"] == "NONE"
    assert days[1]["day_role"] == "QUALITY"
    assert days[1]["intensity_domain"] == "TEMPO"
    assert days[2]["day_role"] == "RECOVERY"
    assert days[2]["intensity_domain"] == "RECOVERY"
    assert days[2]["load_modality"] == "NONE"
    assert days[5]["day_role"] == "ENDURANCE"
    assert days[5]["intensity_domain"] == "ENDURANCE"


def test_season_writer_bundle_match_repairs_deterministic_writer_drift() -> None:
    approved_bundle = {
        "season_load_envelope": {
            "expected_average_weekly_kj_range": {"min": 9516, "max": 12892},
            "expected_high_load_weeks_count": 7,
            "expected_deload_or_low_load_weeks_count": 5,
        },
        "phase_blueprints": [
            {
                "phase_id": "P01",
                "phase_type": "BASE",
                "phase_intent": "shortened_re_entry",
                "build_subtype": None,
                "phase_taxonomy_version": "canonical_phase_taxonomy_v1",
                "allowed_domains": ["ENDURANCE", "TEMPO"],
                "allowed_load_modalities": ["NONE", "K3"],
                "forbidden_domains": ["THRESHOLD", "VO2MAX"],
            }
        ],
    }
    output = {
        "data": {
            "body_metadata": {"phase_taxonomy_version": "canonical_phase_taxonomy_v1"},
            "season_load_envelope": {
                "expected_average_weekly_kj_range": {"min": 9000, "max": 14000},
                "expected_high_load_weeks_count": 7,
                "expected_deload_or_low_load_weeks_count": 5,
            },
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
                        "allowed_load_modalities": ["NONE", "K3"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    },
                }
            ],
        }
    }

    with guardrail_runtime_context(approved_planning_bundle=approved_bundle):
        ok, repaired = season_writer_bundle_match(output)

    assert ok is True
    assert repaired["data"]["season_load_envelope"] == approved_bundle["season_load_envelope"]
    phase = repaired["data"]["phases"][0]
    assert phase["phase_type"] == "BASE"
    assert phase["phase_intent"] == "shortened_re_entry"
    assert phase["allowed_forbidden_semantics"]["allowed_intensity_domains"] == ["ENDURANCE", "TEMPO"]
    assert phase["allowed_forbidden_semantics"]["allowed_load_modalities"] == ["NONE", "K3"]
    assert phase["allowed_forbidden_semantics"]["forbidden_intensity_domains"] == ["THRESHOLD", "VO2MAX"]


def test_normalize_final_season_plan_semantics_projects_events_guardrails_and_warning() -> None:
    document = {
        "meta": {"artifact_type": "SEASON_PLAN"},
        "data": {
            "season_intent_principles": {
                "season_objective": "Stable long-duration performance over 300-400 km."
            },
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "weekly_load_corridor": {"weekly_kj": {"min": 7800, "max": 9800, "notes": "Base corridor."}},
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["ENDURANCE"],
                        "allowed_load_modalities": ["K3"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    },
                    "events_constraints": [{"window": "2026-21--2026-23", "type": "B", "constraint": "stale"}],
                },
                {
                    "phase_id": "P02",
                    "phase_type": "TAPER",
                    "phase_intent": "taper_freshening",
                    "build_subtype": None,
                    "weekly_load_corridor": {"weekly_kj": {"min": 7000, "max": 8800, "notes": "Taper corridor."}},
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["ENDURANCE"],
                        "allowed_load_modalities": ["K3"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    },
                    "events_constraints": [],
                },
            ],
            "justification": {
                "summary": "Summary.",
                "citations": [{"source_type": "contract", "source_id": "x", "section": "y", "rationale": "z"}],
                "phase_justifications": [
                    {"phase_id": "P01", "intensity_distribution": "x", "overload_pattern": "y", "kJ_first_statement": "P01 corridor.", "citations": ["c1"]},
                    {"phase_id": "P02", "intensity_distribution": "x", "overload_pattern": "y", "kJ_first_statement": "P02 corridor.", "citations": ["c1"]},
                ],
            },
            "principles_scientific_foundation": {
                "principle_applications": [{"principle": "Durability-first progression", "influence": "x"}],
                "scientific_foundation": {
                    "publications": [{"authors": "Seiler, S.", "year": 2010, "title": "Intensity distribution", "link": "https://example.com"}],
                    "plan_alignment_check": "Aligned",
                    "rationale": "x",
                },
            },
            "assumptions_unknowns": {
                "assumptions": ["a"],
                "uncertainties": ["u"],
                "revisit_items": ["r"],
            },
        },
    }
    with guardrail_runtime_context(
        approved_planning_bundle={
            "phase_blueprints": [
                {"phase_id": "P01", "allowed_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"], "allowed_load_modalities": ["NONE", "K3"], "forbidden_domains": ["THRESHOLD", "VO2MAX"]},
                {"phase_id": "P02", "allowed_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"], "allowed_load_modalities": ["NONE"], "forbidden_domains": ["THRESHOLD", "VO2MAX"]},
            ]
        },
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "role_week_load_bands": [{"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}}],
                    "event_taper_trace": {"events": []},
                },
                {
                    "phase_id": "P02",
                    "phase_type": "TAPER",
                    "phase_intent": "taper_freshening",
                    "build_subtype": None,
                    "role_week_load_bands": [{"week": "2026-37", "role": "EVENT", "band": {"min": 7000, "max": 8800}}],
                    "event_taper_trace": {
                        "events": [{"date": "2026-09-12", "week": "2026-37", "type": "A", "name": "Brevet 200 km"}]
                    },
                },
            ],
        },
    ):
        normalized = _normalize_final_season_plan_semantics(document)

    p01 = normalized["data"]["phases"][0]
    p02 = normalized["data"]["phases"][1]
    assert p01["allowed_forbidden_semantics"]["allowed_load_modalities"] == ["NONE", "K3"]
    assert p02["allowed_forbidden_semantics"]["allowed_load_modalities"] == ["NONE"]
    assert p01["events_constraints"] == []
    assert p02["events_constraints"] == [
        {
            "window": "2026-09-12",
            "type": "A",
            "constraint": "A event receives dedicated taper-contained event handling.",
        }
    ]
    assert "2026-21: LOAD_1 7800-8600" in p01["weekly_load_corridor"]["weekly_kj"]["notes"]
    assert any("Warning:" in item for item in normalized["data"]["assumptions_unknowns"]["revisit_items"])
    assert any(
        "Durability" in publication["title"]
        for publication in normalized["data"]["principles_scientific_foundation"]["scientific_foundation"]["publications"]
    )


def test_season_phase_load_context_match_repairs_missing_role_week_notes_before_validation() -> None:
    output = {
        "data": {
            "body_metadata": {"phase_taxonomy_version": "canonical_phase_taxonomy_v1"},
            "season_intent_principles": {"season_objective": "Strong 200 km A-event execution."},
            "phases": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "weekly_load_corridor": {"weekly_kj": {"min": 7800, "max": 9800, "notes": "Base corridor."}},
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                        "allowed_load_modalities": ["K3"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    },
                    "events_constraints": [],
                }
            ],
            "season_load_envelope": {"expected_average_weekly_kj_range": {"min": 7800, "max": 9800}},
            "assumptions_unknowns": {"assumptions": ["a"], "uncertainties": ["u"], "revisit_items": ["r"]},
            "justification": {"phase_justifications": []},
        }
    }

    with guardrail_runtime_context(
        approved_planning_bundle={
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "allowed_load_modalities": ["NONE", "K3"],
                    "role_week_load_bands": [
                        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}}
                    ],
                }
            ]
        },
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_intent": "shortened_re_entry",
                    "recommended_phase_corridor": {"min": 7800, "max": 9800},
                    "role_week_load_bands": [
                        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}}
                    ],
                    "event_taper_trace": {"events": []},
                }
            ],
        },
    ):
        ok, repaired = season_phase_load_context_match(output)

    assert ok is True
    notes = repaired["data"]["phases"][0]["weekly_load_corridor"]["weekly_kj"]["notes"]
    assert "Inherited role-week load guardrails" in notes
    assert "2026-21: LOAD_1 7800-8600" in notes
    assert repaired["data"]["phases"][0]["allowed_forbidden_semantics"]["allowed_load_modalities"] == ["NONE", "K3"]


def test_season_phase_load_context_match_clears_stale_event_constraints_and_ignores_narrative_semantics() -> None:
    output = {
        "data": {
            "body_metadata": {"phase_taxonomy_version": "canonical_phase_taxonomy_v1"},
            "season_intent_principles": {"season_objective": "Strong 200 km A-event execution."},
            "phases": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-21--2026-23",
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "build_subtype": None,
                    "narrative": "Controlled threshold support stays available in this phase.",
                    "weekly_load_corridor": {"weekly_kj": {"min": 7800, "max": 9800, "notes": "Base corridor."}},
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["RECOVERY", "ENDURANCE", "TEMPO", "SWEET_SPOT"],
                        "allowed_load_modalities": ["K3"],
                        "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
                    },
                    "events_constraints": [
                        {
                            "window": "2026-21",
                            "type": "B",
                            "constraint": "No target-week event.",
                        }
                    ],
                }
            ],
            "season_load_envelope": {"expected_average_weekly_kj_range": {"min": 7800, "max": 9800}},
            "assumptions_unknowns": {"assumptions": ["a"], "uncertainties": ["u"], "revisit_items": ["r"]},
            "justification": {"phase_justifications": []},
        }
    }

    with guardrail_runtime_context(
        approved_planning_bundle={
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "allowed_load_modalities": ["NONE", "K3"],
                    "role_week_load_bands": [
                        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}}
                    ],
                }
            ]
        },
        season_phase_load_context={
            "season_allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "phases": [
                {
                    "phase_id": "P01",
                    "phase_intent": "shortened_re_entry",
                    "recommended_phase_corridor": {"min": 7800, "max": 9800},
                    "role_week_load_bands": [
                        {"week": "2026-21", "role": "LOAD_1", "band": {"min": 7800, "max": 8600}}
                    ],
                    "event_taper_trace": {"events": []},
                }
            ],
        },
    ):
        ok, repaired = season_phase_load_context_match(output)

    assert ok is True
    assert repaired["data"]["phases"][0]["events_constraints"] == []


def test_season_bundle_review_readiness_rejects_phantom_event_placeholders() -> None:
    for placeholder in (
        "No target-week event.",
        "No logistics exception.",
        "No event-driven load exception.",
    ):
        ok, message = season_bundle_review_readiness(
            {
                "event_priority": {},
                "macrocycle": {},
                "phase_blueprints": [
                    {
                        "phase_id": "P01",
                        "iso_week_range": "2026-21--2026-23",
                        "scenario_cadence": "2:1",
                        "event_constraints": [placeholder],
                    }
                ],
            }
        )

        assert ok is False
        assert "synthetic no-event semantics" in message


def test_phase_bundle_review_readiness_rejects_unready_bundle() -> None:
    ok, message = phase_bundle_review_readiness(
        {
            "phase_intent": "general_base",
            "guardrails": {"phase_intent": "general_base", "phase_summary": []},
            "structure": {"phase_intent": "specificity_build"},
            "preview": {"phase_intent": "general_base", "phase_intent_summary": []},
            "constraint_audit": {"blocking_issues": []},
            "load_governance_audit": {"blocking_issues": []},
        }
    )

    assert ok is False
    assert "does not match bundle phase_intent" in message or "must provide guardrails.phase_summary" in message


def test_phase_bundle_review_readiness_accepts_normalized_nested_phase_intents() -> None:
    ok, payload = phase_bundle_review_readiness(
        {
            "phase_intent": "shortened_re_entry",
            "guardrails": {"phase_intent": "shortened_re_entry", "phase_summary": ["summary"]},
            "structure": {"phase_intent": "shortened_re_entry"},
            "preview": {"phase_intent": "shortened_re_entry", "phase_intent_summary": ["summary"]},
            "constraint_audit": {"blocking_issues": []},
            "load_governance_audit": {"blocking_issues": []},
        }
    )

    assert ok is True
    assert payload["phase_intent"] == "shortened_re_entry"


def test_week_bundle_review_readiness_rejects_loaded_fixed_rest_day() -> None:
    ok, message = week_bundle_review_readiness(
        {
            "day_blueprints": [
                {
                    "day": "Mon",
                    "date": "2026-05-11",
                    "fixed_rest_day": True,
                    "planned_duration_minutes": 45,
                    "planned_kj": 250,
                    "workout_id": "W1",
                }
            ],
            "workout_blueprints": [],
        }
    )

    assert ok is False
    assert "Fixed rest day still carries duration" in message


def test_scenario_selection_guardrail_accepts_only_selection_shape() -> None:
    ok, payload = season_scenario_selection_shape(
        {
            "meta": {"artifact_type": "SEASON_SCENARIO_SELECTION", "schema_id": "SeasonScenarioSelectionInterface"},
            "data": {"selected_scenario_id": "B", "season_scenarios_ref": "season_scenarios/latest.json"},
        }
    )
    failed, message = season_scenario_selection_shape(
        {
            "meta": {"artifact_type": "SEASON_SCENARIO_SELECTION", "schema_id": "SeasonScenarioSelectionInterface"},
            "data": {
                "selected_scenario_id": "B",
                "season_scenarios_ref": "season_scenarios/latest.json",
                "weekly_kj_bands": [],
            },
        }
    )

    assert ok is True
    assert payload["data"]["selected_scenario_id"] == "B"
    assert failed is False
    assert "must not contain" in message


def _season_scenario_item(
    *,
    scenario_id: str,
    load_philosophy: str,
    risk_profile: str,
    key_differences: str,
    cadence: str,
    allowed_domains: list[str],
    decision_notes: list[str],
    best_suited_if: str,
    risk_flags: list[str],
    constraint_summary: list[str] | None = None,
    event_alignment_notes: list[str] | None = None,
    kpi_guardrail_notes: list[str] | None = None,
    season_archetype: str = "none",
    season_archetype_rationale: list[str] | None = None,
    recovery_margin: str = "medium",
    fatigue_exposure: str = "moderate",
    specificity_density: str = "controlled",
) -> dict:
    return {
        "scenario_id": scenario_id,
        "name": f"Scenario {scenario_id}",
        "core_idea": key_differences,
        "load_philosophy": load_philosophy,
        "risk_profile": risk_profile,
        "key_differences": key_differences,
        "best_suited_if": best_suited_if,
        "scenario_guidance": {
            "recovery_margin": recovery_margin,
            "fatigue_exposure": fatigue_exposure,
            "specificity_density": specificity_density,
            "deload_cadence": cadence,
            "risk_flags": risk_flags,
            "event_alignment_notes": event_alignment_notes or [],
            "constraint_summary": constraint_summary or [],
            "kpi_guardrail_notes": kpi_guardrail_notes or [],
            "decision_notes": decision_notes,
            "season_archetype": season_archetype,
            "season_archetype_rationale": season_archetype_rationale or [],
            "intensity_guidance": {"allowed_domains": allowed_domains},
        },
    }


def _season_scenarios_payload(*scenarios: dict, notes: list[str] | None = None) -> dict:
    return {
        "meta": {"artifact_type": "SEASON_SCENARIOS", "schema_id": "SeasonScenariosInterface"},
        "data": {
            "notes": notes
            or [
                "allowed_domains define eligibility for later assignment only; they do not authorize every domain in every phase.",
                "objective mismatch remains unresolved upstream input context and is not resolved in the scenario layer.",
            ],
            "scenarios": list(scenarios),
        },
    }


def test_season_scenarios_profile_quality_accepts_same_domains_with_distinct_profiles() -> None:
    ok, payload = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Highest executability and lowest density.",
                key_differences="Completion-first with minimal fatigue exposure.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when continuity priority and uncertain recovery dominate.",
                risk_flags=["May under-deliver if high load tolerance is available."],
                constraint_summary=["Low density."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with systematic long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 2:1:1 cadence to absorb tempo economy work and long-ride progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
                constraint_summary=["Long-ride progression."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                risk_profile="Ambitious performance-forward long build with higher specificity under fatigue.",
                key_differences="More back-to-back and hard-late specificity.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for a longer build with back-to-back and hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Fatigue risk rises quickly if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
            ),
        )
    )

    assert ok is True
    assert payload["data"]["scenarios"][2]["scenario_id"] == "C"


def test_season_scenarios_selection_contract_complete_rejects_missing_operational_posture() -> None:
    failed, message = season_scenarios_selection_contract_complete(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Highest executability and lowest density.",
                key_differences="Completion-first with minimal fatigue exposure.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when continuity priority and uncertain recovery dominate.",
                risk_flags=["May under-deliver if high load tolerance is available."],
                constraint_summary=["Low density."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with systematic long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 2:1:1 cadence to absorb tempo economy work and long-ride progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
                constraint_summary=["Long-ride progression."],
                recovery_margin="",
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                risk_profile="Ambitious performance-forward long build with higher specificity under fatigue.",
                key_differences="More back-to-back and hard-late specificity.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for a longer build with back-to-back and hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Fatigue risk rises quickly if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
            ),
        )
    )

    assert failed is False
    assert "scenario_guidance.recovery_margin" in message


def test_season_scenarios_profile_quality_accepts_vo2_rationale_from_kpi_guardrail_notes() -> None:
    ok, payload = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Highest executability and lowest density.",
                key_differences="Completion-first with minimal fatigue exposure.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when continuity priority and uncertain recovery dominate.",
                risk_flags=["May under-deliver if high load tolerance is available."],
                constraint_summary=["Low density."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with systematic long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 2:1:1 cadence to absorb tempo economy work."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
                constraint_summary=["Long-ride progression."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                risk_profile="Ambitious performance-forward long build with higher specificity under fatigue.",
                key_differences="More back-to-back and hard-late specificity.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "VO2MAX"],
                decision_notes=["Use 3:1 cadence for back-to-back and hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Fatigue risk rises quickly if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
                kpi_guardrail_notes=[
                    "3:1 cadence supports the longer build, and VO2MAX is allowed only as sparse ceiling-support work when fresh-only, not primary identity, while ambition comes from specificity-under-fatigue and load posture."
                ],
            ),
        )
    )

    assert ok is True
    assert payload["data"]["scenarios"][2]["scenario_id"] == "C"


def test_season_scenarios_profile_quality_rejects_weak_scenario_c() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope.",
                risk_profile="Low risk.",
                key_differences="Conservative.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope.",
                risk_profile="Balanced risk.",
                key_differences="Default.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Higher weekly kJ only.",
                risk_profile="Higher risk.",
                key_differences="More kJ.",
                cadence="3:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 3:1 cadence for a bigger build."],
                best_suited_if="Choose only when stable recovery and high load tolerance support lower recovery margin.",
                risk_flags=["Too aggressive if fatigue risk appears."],
            ),
        )
    )

    assert failed is False
    assert "Scenario C must express ambitious specificity" in message


def test_season_scenarios_profile_quality_rejects_shared_cadence_without_explicit_justification() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Lowest risk profile.",
                key_differences="Completion-first with sparse tempo.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1:1 cadence for high recovery margin."],
                best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                risk_profile="Higher specificity and fatigue exposure.",
                key_differences="More back-to-back and hard-late specificity.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 2:1:1 cadence for harder event-simulation weeks and back-to-back specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Too aggressive if travel disruption appears."],
                constraint_summary=["Fatigue exposure and event simulation."],
            ),
        )
    )

    assert failed is False
    assert message == "Season scenarios collapse cadence across A/B/C without explicit justification."


def test_season_scenarios_profile_quality_accepts_shared_cadence_with_explicit_justification() -> None:
    ok, payload = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Lowest risk profile.",
                key_differences="Completion-first with sparse tempo.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=[
                    "Use 2:1:1 cadence and keep cadence constant across scenarios because differentiation comes from recovery margin and load philosophy."
                ],
                best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=[
                    "Use 2:1:1 cadence and keep cadence constant while differentiation comes from specificity-under-fatigue and balanced risk posture."
                ],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                risk_profile="Higher specificity and fatigue exposure.",
                key_differences="More back-to-back and hard-late specificity.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=[
                    "Use 2:1:1 cadence and keep cadence constant while differentiation comes from event simulation, fatigue exposure, and risk profile."
                ],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Too aggressive if travel disruption appears."],
                constraint_summary=["Fatigue exposure and event simulation."],
            ),
        )
    )

    assert ok is True
    assert payload["data"]["scenarios"][0]["scenario_guidance"]["deload_cadence"] == "2:1:1"


def test_season_scenarios_profile_quality_rejects_recommendation_mirrored_cadence_without_rationale() -> None:
    with guardrail_runtime_context(season_scenario_recommendation_context={"recommended_cadence": "2:1:1"}):
        failed, message = season_scenarios_profile_quality(
            _season_scenarios_payload(
                _season_scenario_item(
                    scenario_id="A",
                    load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                    risk_profile="Lowest risk profile.",
                    key_differences="Completion-first with sparse tempo.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE"],
                    decision_notes=["Use 2:1:1 cadence for high recovery margin."],
                    best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                    risk_flags=["May under-deliver if high load tolerance is available."],
                ),
                _season_scenario_item(
                    scenario_id="B",
                    load_philosophy="Realistic target kJ-envelope with long-ride progression.",
                    risk_profile="Balanced recovery risk.",
                    key_differences="Durability-forward target plan.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE", "TEMPO"],
                    decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                    best_suited_if="Choose when stable recovery supports systematic progression.",
                    risk_flags=["Less forgiving than A if continuity break appears."],
                ),
                _season_scenario_item(
                    scenario_id="C",
                    load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                    risk_profile="Higher specificity and fatigue exposure.",
                    key_differences="More back-to-back and hard-late specificity.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                    decision_notes=["Use 2:1:1 cadence for harder event-simulation weeks and back-to-back specificity under fatigue."],
                    best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                    risk_flags=["Too aggressive if travel disruption appears."],
                    constraint_summary=["Fatigue exposure and event simulation."],
                ),
            )
        )

    assert failed is False
    assert message == "Recommendation-default cadence was mirrored across all scenarios without scenario differentiation."


def test_season_scenarios_profile_quality_accepts_mixed_cadence_with_advisory_recommendation_context() -> None:
    with guardrail_runtime_context(season_scenario_recommendation_context={"recommended_cadence": "2:1:1"}):
        ok, payload = season_scenarios_profile_quality(
            _season_scenarios_payload(
                _season_scenario_item(
                    scenario_id="A",
                    load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                    risk_profile="Lowest risk profile.",
                    key_differences="Completion-first with sparse tempo.",
                    cadence="2:1",
                    allowed_domains=["ENDURANCE"],
                    decision_notes=["Use 2:1 cadence for the most recovery-protective option despite the advisory recommendation."],
                    best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                    risk_flags=["May under-deliver if high load tolerance is available."],
                ),
                _season_scenario_item(
                    scenario_id="B",
                    load_philosophy="Realistic target kJ-envelope with long-ride progression.",
                    risk_profile="Balanced recovery risk.",
                    key_differences="Durability-forward target plan.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE", "TEMPO"],
                    decision_notes=["Use 2:1:1 cadence because the advisory recommendation fits the balanced durability profile."],
                    best_suited_if="Choose when stable recovery supports systematic progression.",
                    risk_flags=["Less forgiving than A if continuity break appears."],
                ),
                _season_scenario_item(
                    scenario_id="C",
                    load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                    risk_profile="Higher specificity and fatigue exposure.",
                    key_differences="More back-to-back and hard-late specificity.",
                    cadence="3:1",
                    allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                    decision_notes=["Use 3:1 cadence for a longer build with event simulation and back-to-back specificity under fatigue."],
                    best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                    risk_flags=["Too aggressive if travel disruption appears."],
                    constraint_summary=["Fatigue exposure and event simulation."],
                ),
            )
        )

    assert ok is True
    assert payload["data"]["scenarios"][1]["scenario_guidance"]["deload_cadence"] == "2:1:1"


def test_season_scenarios_profile_quality_rejects_cluster_wording_without_multiple_future_events() -> None:
    with guardrail_runtime_context(
        season_scenario_event_context={
            "future_events": [{"type": "B", "date": "2026-08-02", "event_name": "Summer 200"}],
            "all_events": [{"type": "B", "date": "2026-08-02", "event_name": "Summer 200"}],
        }
    ):
        failed, message = season_scenarios_profile_quality(
            _season_scenarios_payload(
                _season_scenario_item(
                    scenario_id="A",
                    load_philosophy="Low envelope.",
                    risk_profile="Low risk.",
                    key_differences="Conservative.",
                    cadence="2:1",
                    allowed_domains=["ENDURANCE"],
                    decision_notes=["Use 2:1 cadence to protect recovery margin."],
                    best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                    risk_flags=["May under-deliver if high load tolerance is available."],
                    event_alignment_notes=["Use the B-event cluster as a rehearsal platform."],
                ),
                _season_scenario_item(
                    scenario_id="B",
                    load_philosophy="Balanced envelope.",
                    risk_profile="Balanced risk.",
                    key_differences="Default.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE", "TEMPO"],
                    decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                    best_suited_if="Choose when stable recovery supports systematic progression.",
                    risk_flags=["Less forgiving than A if continuity break appears."],
                ),
                _season_scenario_item(
                    scenario_id="C",
                    load_philosophy="Higher envelope with event simulation.",
                    risk_profile="Higher fatigue exposure.",
                    key_differences="Specificity under fatigue.",
                    cadence="3:1",
                    allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                    decision_notes=["Use 3:1 cadence for hard-late specificity under fatigue."],
                    best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                    risk_flags=["Too aggressive if travel disruption appears."],
                    constraint_summary=["Event simulation and fatigue exposure."],
                ),
            )
        )

    assert failed is False
    assert message == "Cluster wording requires multiple relevant in-horizon events."


def test_season_scenarios_profile_quality_accepts_cluster_wording_with_multiple_future_events() -> None:
    with guardrail_runtime_context(
        season_scenario_event_context={
            "future_events": [
                {"type": "B", "date": "2026-08-02", "event_name": "Summer 200"},
                {"type": "B", "date": "2026-08-16", "event_name": "Late Summer 200"},
            ],
            "all_events": [
                {"type": "B", "date": "2026-08-02", "event_name": "Summer 200"},
                {"type": "B", "date": "2026-08-16", "event_name": "Late Summer 200"},
            ],
        }
    ):
        ok, payload = season_scenarios_profile_quality(
            _season_scenarios_payload(
                _season_scenario_item(
                    scenario_id="A",
                    load_philosophy="Low envelope.",
                    risk_profile="Low risk.",
                    key_differences="Conservative.",
                    cadence="2:1",
                    allowed_domains=["ENDURANCE"],
                    decision_notes=["Use 2:1 cadence to protect recovery margin."],
                    best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                    risk_flags=["May under-deliver if high load tolerance is available."],
                    event_alignment_notes=["Use the B-event cluster as a low-risk rehearsal path."],
                ),
                _season_scenario_item(
                    scenario_id="B",
                    load_philosophy="Balanced envelope.",
                    risk_profile="Balanced risk.",
                    key_differences="Default.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE", "TEMPO"],
                    decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                    best_suited_if="Choose when stable recovery supports systematic progression.",
                    risk_flags=["Less forgiving than A if continuity break appears."],
                ),
                _season_scenario_item(
                    scenario_id="C",
                    load_philosophy="Higher envelope with event simulation.",
                    risk_profile="Higher fatigue exposure.",
                    key_differences="Specificity under fatigue.",
                    cadence="3:1",
                    allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                    decision_notes=["Use 3:1 cadence for hard-late specificity under fatigue."],
                    best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                    risk_flags=["Too aggressive if travel disruption appears."],
                    constraint_summary=["Event simulation and fatigue exposure."],
                ),
            )
        )

    assert ok is True
    assert payload["data"]["scenarios"][0]["scenario_id"] == "A"


def test_season_scenarios_profile_quality_rejects_pre_horizon_event_as_active_logic() -> None:
    with guardrail_runtime_context(
        season_scenario_event_context={
            "future_events": [{"type": "B", "date": "2026-08-02", "event_name": "Summer 200"}],
            "all_events": [
                {"type": "B", "date": "2026-04-11", "event_name": "Spring 200"},
                {"type": "B", "date": "2026-08-02", "event_name": "Summer 200"},
            ],
        }
    ):
        failed, message = season_scenarios_profile_quality(
            _season_scenarios_payload(
                _season_scenario_item(
                    scenario_id="A",
                    load_philosophy="Low envelope.",
                    risk_profile="Low risk.",
                    key_differences="Conservative.",
                    cadence="2:1",
                    allowed_domains=["ENDURANCE"],
                    decision_notes=["Use 2:1 cadence and Spring 200 as an active rehearsal anchor."],
                    best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                    risk_flags=["May under-deliver if high load tolerance is available."],
                ),
                _season_scenario_item(
                    scenario_id="B",
                    load_philosophy="Balanced envelope.",
                    risk_profile="Balanced risk.",
                    key_differences="Default.",
                    cadence="2:1:1",
                    allowed_domains=["ENDURANCE", "TEMPO"],
                    decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                    best_suited_if="Choose when stable recovery supports systematic progression.",
                    risk_flags=["Less forgiving than A if continuity break appears."],
                ),
                _season_scenario_item(
                    scenario_id="C",
                    load_philosophy="Higher envelope with event simulation.",
                    risk_profile="Higher fatigue exposure.",
                    key_differences="Specificity under fatigue.",
                    cadence="3:1",
                    allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                    decision_notes=["Use 3:1 cadence for hard-late specificity under fatigue."],
                    best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                    risk_flags=["Too aggressive if travel disruption appears."],
                    constraint_summary=["Event simulation and fatigue exposure."],
                ),
            )
        )

    assert failed is False
    assert message == "Season scenarios must not describe pre-horizon events as active rehearsal/anchor/peak logic."


def test_season_scenarios_profile_quality_rejects_resolved_objective_mismatch_claim() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Low envelope.",
                risk_profile="Low risk.",
                key_differences="Conservative.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Balanced envelope.",
                risk_profile="Balanced risk.",
                key_differences="Default.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Higher envelope with event simulation.",
                risk_profile="Higher fatigue exposure.",
                key_differences="Specificity under fatigue.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Too aggressive if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
            ),
            notes=[
                "allowed_domains define eligibility for later assignment only; they do not authorize every domain in every phase.",
                "objective reconciled for the new event hierarchy here.",
            ],
        )
    )

    assert failed is False
    assert message == "Scenario layer must not claim that objective mismatch is already resolved."


def test_season_scenarios_profile_quality_rejects_ceiling_first_without_full_rationale() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Low envelope.",
                risk_profile="Low risk.",
                key_differences="Conservative.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Balanced envelope.",
                risk_profile="Balanced risk.",
                key_differences="Default.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Higher envelope with event simulation.",
                risk_profile="Higher fatigue exposure.",
                key_differences="Specificity under fatigue.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for early ceiling support."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Too aggressive if travel disruption appears."],
                season_archetype="ceiling_first_durability",
                season_archetype_rationale=["Early ceiling support is permitted."],
                constraint_summary=["Event simulation and fatigue exposure."],
            ),
        )
    )

    assert failed is False
    assert message == "Scenario C may use ceiling_first_durability only with explicit rationale and preserved runway."


def test_season_scenarios_profile_quality_rejects_missing_selection_gate_semantics() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Low envelope.",
                risk_profile="Low risk.",
                key_differences="Conservative.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="A nice option for many athletes.",
                risk_flags=["General caution."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Balanced envelope.",
                risk_profile="Balanced risk.",
                key_differences="Default.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Higher envelope with event simulation.",
                risk_profile="Higher fatigue exposure.",
                key_differences="Specificity under fatigue.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Too aggressive if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
            ),
        )
    )

    assert failed is False
    assert message == "Scenario A must include a meaningful best_suited_if selection gate."


def test_season_scenarios_profile_quality_rejects_missing_risk_flag_semantics() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Low envelope.",
                risk_profile="Low risk.",
                key_differences="Conservative.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when continuity priority and uncertain recovery dominate.",
                risk_flags=["General caution if things get hard."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Balanced envelope.",
                risk_profile="Balanced risk.",
                key_differences="Default.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Higher envelope with event simulation.",
                risk_profile="Higher fatigue exposure.",
                key_differences="Specificity under fatigue.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Too aggressive if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
            ),
        )
    )

    assert failed is False
    assert message == "Scenario A must include concrete caution markers in risk_flags."


def test_season_scenarios_profile_quality_rejects_vo2_rationale_missing_primary_identity_clause() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Lowest risk profile.",
                key_differences="Completion-first with sparse tempo.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when continuity priority and uncertain recovery dominate.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with systematic long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 2:1:1 cadence to absorb tempo economy work."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break or recovery slip appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with more event simulation.",
                risk_profile="Ambitious performance-forward long build with higher specificity under fatigue.",
                key_differences="More back-to-back and hard-late specificity.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "VO2MAX"],
                decision_notes=["Use 3:1 cadence for back-to-back and hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Fatigue risk rises quickly if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
                kpi_guardrail_notes=[
                    "3:1 cadence supports the longer build, and VO2MAX is allowed only as sparse ceiling-support work when fresh-only, while ambition comes from specificity-under-fatigue and load posture."
                ],
            ),
        )
    )

    assert failed is False
    assert message == "Scenario C may allow VO2MAX only with explicit sparse ceiling-support rationale."


def test_season_scenarios_profile_quality_rejects_vo2_rationale_missing_specificity_source() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Lower feasible kJ-envelope with high recovery margin.",
                risk_profile="Lowest risk profile.",
                key_differences="Completion-first with sparse tempo.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when continuity priority and uncertain recovery dominate.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Realistic target kJ-envelope with systematic long-ride progression.",
                risk_profile="Balanced recovery risk.",
                key_differences="Durability-forward target plan.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 2:1:1 cadence to absorb tempo economy work."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break or recovery slip appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Upper plausible kJ-envelope with a larger workload envelope.",
                risk_profile="Ambitious performance-forward long build with lower recovery margin.",
                key_differences="More specificity and less recovery margin.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "VO2MAX"],
                decision_notes=["Use 3:1 cadence for a longer specificity build."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Fatigue risk rises quickly if travel disruption appears."],
                constraint_summary=["Longer overload build with reduced recovery margin."],
                kpi_guardrail_notes=[
                    "3:1 cadence supports the longer build, and VO2MAX is allowed only as sparse ceiling-support work when fresh-only, not primary identity, while ambition comes from durability ambition and general race readiness."
                ],
            ),
        )
    )

    assert failed is False
    assert message == "Scenario C may allow VO2MAX only with explicit sparse ceiling-support rationale."


def test_season_scenarios_profile_quality_rejects_phase_wide_domain_authorization_wording() -> None:
    failed, message = season_scenarios_profile_quality(
        _season_scenarios_payload(
            _season_scenario_item(
                scenario_id="A",
                load_philosophy="Low envelope.",
                risk_profile="Low risk.",
                key_differences="Conservative.",
                cadence="2:1",
                allowed_domains=["ENDURANCE"],
                decision_notes=["Use 2:1 cadence to protect recovery margin."],
                best_suited_if="Choose when uncertain recovery makes continuity priority essential.",
                risk_flags=["May under-deliver if high load tolerance is available."],
            ),
            _season_scenario_item(
                scenario_id="B",
                load_philosophy="Balanced envelope.",
                risk_profile="Balanced risk.",
                key_differences="Default.",
                cadence="2:1:1",
                allowed_domains=["ENDURANCE", "TEMPO"],
                decision_notes=["Use 2:1:1 cadence for balanced durability progression."],
                best_suited_if="Choose when stable recovery supports systematic progression.",
                risk_flags=["Less forgiving than A if continuity break appears."],
            ),
            _season_scenario_item(
                scenario_id="C",
                load_philosophy="Higher envelope with event simulation.",
                risk_profile="Higher fatigue exposure.",
                key_differences="Specificity under fatigue.",
                cadence="3:1",
                allowed_domains=["ENDURANCE", "TEMPO", "SWEET_SPOT"],
                decision_notes=["Use 3:1 cadence for hard-late specificity under fatigue."],
                best_suited_if="Choose only when stable recovery and high load tolerance support fatigue exposure tolerance.",
                risk_flags=["Too aggressive if travel disruption appears."],
                constraint_summary=["Event simulation and fatigue exposure."],
            ),
            notes=["allowed_domains are globally authorized for all phases."],
        )
    )

    assert failed is False
    assert message == "Season scenarios must state that allowed_domains are eligibility only, not phase-wide authorization."


def test_season_scenarios_task_policy_uses_profile_quality_guardrail() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)
    policy = resolve_task_policy(blueprints["season_scenarios"], bundle.task_policies)

    assert "season_scenarios_profile_quality" in policy.guardrails
    assert "season_scenarios_selection_contract_complete" in policy.guardrails


def test_season_scenarios_task_uses_narrow_workspace_tools() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    blueprints = build_task_blueprints(bundle)
    task = blueprints["season_scenarios"]

    assert task.config["tools"] == ["workspace_get_input", "workspace_get_latest"]


def test_phase_s5_band_guardrail_rejects_explicit_s5_mismatch() -> None:
    failed, message = phase_s5_band_match(
        {
            "meta": {"artifact_type": "PHASE_GUARDRAILS", "schema_id": "PhaseGuardrailsInterface"},
            "data": {
                "load_guardrails": {
                    "weekly_kj_bands": [
                        {"week": "2026-20", "band": {"min": 1000, "max": 1500, "notes": "S5 band: 1100-1500"}}
                    ]
                }
            },
        }
    )

    assert failed is False
    assert "does not match deterministic S5 band" in message


def test_phase_weeks_match_range_rejects_missing_phase_week() -> None:
    failed, message = phase_weeks_match_range(
        {
            "meta": {
                "artifact_type": "PHASE_STRUCTURE",
                "schema_id": "PhaseStructureInterface",
                "iso_week_range": "2026-20--2026-22",
            },
            "data": {
                "load_ranges": {
                    "weekly_kj_bands": [
                        {"week": "2026-20", "band": {"min": 1000, "max": 1200}},
                        {"week": "2026-22", "band": {"min": 1000, "max": 1200}},
                    ]
                }
            },
        }
    )

    assert failed is False
    assert "missing=['2026-21']" in message


def test_week_corridor_guardrail_rejects_load_outside_band() -> None:
    failed, message = week_corridor_and_capacity_check(
        {
            "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface"},
            "data": {
                "week_summary": {
                    "planned_weekly_load_kj": 2500,
                    "weekly_load_corridor_kj": {"min": 1000, "max": 2000},
                }
            },
        }
    )

    assert failed is False
    assert "exceeds weekly load corridor" in message


def test_week_calendar_context_uses_phase_structure_week_role() -> None:
    phase_info = SimpleNamespace(phase_id="P01", phase_type="Build", raw={"cycle": "Build"})
    context = build_week_calendar_context(
        target_week=IsoWeek(2026, 21),
        phase_info=phase_info,
        phase_range=SimpleNamespace(
            range_key="2026-20--2026-22",
            start=IsoWeek(2026, 20),
            end=IsoWeek(2026, 22),
        ),
        phase_structure_payload={
            "data": {
                "execution_principles": {"phase_role": "Build"},
                "week_skeleton_logic": {
                    "week_roles": {
                        "week_roles": [
                            {"week": "2026-20", "role": "LOAD_1"},
                            {"week": "2026-21", "role": "LOAD_2"},
                            {"week": "2026-22", "role": "DELOAD"},
                        ],
                        "allowed_role_set": ["LOAD_1", "LOAD_2", "DELOAD"],
                    }
                },
            }
        },
        phase_guardrails_payload={
            "data": {
                "load_guardrails": {
                    "weekly_kj_bands": [{"week": "2026-21", "band": {"min": 1000, "max": 2000}}]
                },
                "allowed_forbidden_semantics": {
                    "allowed_day_roles": ["REST", "ENDURANCE", "QUALITY"],
                    "forbidden_day_roles": [],
                    "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
                    "forbidden_intensity_domains": ["THRESHOLD"],
                    "allowed_load_modalities": ["NONE"],
                    "quality_density": {"max_quality_days_per_week": 1},
                },
            }
        },
    )

    assert context["phase_week_role"] == "LOAD_2"
    assert context["phase_week_role_source"] == "PHASE_STRUCTURE.week_skeleton_logic.week_roles"
    assert context["active_weekly_kj_band"] == {"min": 1000, "max": 2000}
    assert context["quality_day_cap"] == 1


def test_render_week_calendar_context_marks_active_weekly_band_as_binding() -> None:
    text = render_week_calendar_context_block(
        {
            "target_iso_week": "2026-21",
            "week_start_date": "2026-05-18",
            "week_end_date": "2026-05-24",
            "phase_id": "P01",
            "phase_iso_week_range": "2026-21--2026-23",
            "phase_cycle": "Base",
            "phase_role": "Base",
            "phase_intent": "shortened_re_entry",
            "phase_week_role": "SHORTENED_RE_ENTRY",
            "phase_week_role_source": "PHASE_STRUCTURE.week_skeleton_logic.week_roles",
            "phase_role_for_week": "SHORTENED_RE_ENTRY",
            "allowed_day_roles": ["REST", "ENDURANCE", "QUALITY"],
            "forbidden_day_roles": [],
            "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
            "allowed_load_modalities": ["NONE", "K3"],
            "quality_day_cap": 2,
            "active_weekly_kj_band": {"min": 7329, "max": 8372},
            "phase_weekly_kj_band": {"min": 7329, "max": 8372},
            "active_s5_band": {"min": 10175, "max": 11275},
            "week_skeleton_mandatory_elements": {"recovery_opportunities_min": 2, "endurance_anchor_required": True},
            "fixed_rest_days": ["Mon", "Fri"],
            "day_matrix": [],
            "event_proximity": {},
        }
    )

    assert "binding active weekly band" in text
    assert "active_weekly_kj_band: min 7329, max 8372 (binding target-week corridor)" in text
    assert "active_s5_band: min 10175, max 11275 (fallback/broader S5 context)" in text


def test_resolved_load_context_finds_mid_phase_season_band() -> None:
    block = build_resolved_load_governance_context_block(
        target_week=IsoWeek(2026, 21),
        season_plan_payload={
            "data": {
                "phases": [
                    {
                        "iso_week_range": "2026-20--2026-22",
                        "weekly_load_corridor": {"weekly_kj": {"min": 1000, "max": 2000, "notes": "build"}},
                    }
                ]
            }
        },
        phase_structure_payload={
            "data": {
                "week_skeleton_logic": {
                    "week_roles": {
                        "week_roles": [{"week": "2026-21", "role": "LOAD_2"}],
                        "allowed_role_set": ["LOAD_2"],
                    }
                }
            }
        },
    )

    assert "season_phase.weekly_load_corridor.weekly_kj: min 1000, max 2000" in block
    assert "phase_structure.active_week_role (2026-21): LOAD_2" in block


def test_week_active_corridor_guardrail_rejects_context_mismatch() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "week_summary": {
                "planned_weekly_load_kj": 1500,
                "weekly_load_corridor_kj": {"min": 1000, "max": 2000},
            }
        },
    }

    with guardrail_runtime_context(
        week_calendar_context={"active_weekly_kj_band": {"min": 1200, "max": 2200}},
        target_week=IsoWeek(2026, 20),
    ):
        failed, message = week_active_corridor_match(week_plan)

    assert failed is False
    assert "must exactly mirror active Phase/S5 band" in message


def test_week_recovery_day_guardrail_rejects_load_on_rest_day() -> None:
    failed, message = week_recovery_day_load_check(
        {
            "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface"},
            "data": {
                "agenda": [
                    {
                        "day": "Mon",
                        "date": "2026-05-11",
                        "day_role": "REST",
                        "planned_duration": "01:00",
                        "planned_kj": 400,
                        "workout_id": "W1",
                    }
                ]
            },
        }
    )

    assert failed is False
    assert "REST day Mon" in message


def test_week_daily_availability_guardrail_rejects_duration_above_day_max() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "week_summary": {"planned_weekly_load_kj": 1200},
            "agenda": [
                {
                    "day": "Mon",
                    "date": "2026-05-11",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Tue",
                    "date": "2026-05-12",
                    "day_role": "ENDURANCE",
                    "planned_duration": "02:00",
                    "planned_kj": 600,
                    "workout_id": "W1",
                },
                {
                    "day": "Wed",
                    "date": "2026-05-13",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Thu",
                    "date": "2026-05-14",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Fri",
                    "date": "2026-05-15",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Sat",
                    "date": "2026-05-16",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
                {
                    "day": "Sun",
                    "date": "2026-05-17",
                    "day_role": "REST",
                    "planned_duration": "00:00",
                    "planned_kj": 0,
                    "workout_id": None,
                },
            ],
        },
    }
    availability = {
        "data": {
            "availability_table": [
                {
                    "weekday": "Tue",
                    "hours_min": 1.0,
                    "hours_typical": 1.0,
                    "hours_max": 1.5,
                }
            ]
        }
    }

    with guardrail_runtime_context(availability_payload=availability, target_week=IsoWeek(2026, 20)):
        failed, message = week_daily_availability_check(week_plan)

    assert failed is False
    assert "exceeds availability hours_max" in message


def test_week_agenda_shape_guardrail_rejects_non_monday_start() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "agenda": [
                {"day": "Tue", "date": "2026-05-12", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None}
            ]
        },
    }

    failed, message = week_agenda_shape_and_calendar_check(week_plan)

    assert failed is False
    assert "agenda must contain exactly seven Mon-Sun entries" in message


def test_week_phase_role_alignment_blocks_quality_in_mini_reset() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "agenda": [
                {"day": "Mon", "date": "2026-05-11", "day_role": "QUALITY", "planned_duration": "01:00", "planned_kj": 500, "workout_id": "W1"}
            ],
            "workouts": [{"workout_id": "W1", "title": "Endurance", "notes": "", "workout_text": ""}],
        },
    }

    with guardrail_runtime_context(
        week_calendar_context={
            "phase_week_role": "MINI_RESET",
            "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
            "quality_day_cap": 1,
            "allowed_intensity_domains": ["RECOVERY", "ENDURANCE"],
            "forbidden_intensity_domains": ["THRESHOLD", "VO2MAX"],
        }
    ):
        failed, message = week_phase_role_alignment_check(week_plan)

    assert failed is False
    assert "MINI_RESET week must not schedule QUALITY days" in message


def test_week_workout_structure_guardrail_rejects_missing_cooldown() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "week_summary": {"planned_weekly_load_kj": 500, "weekly_load_corridor_kj": {"min": 1, "max": 1000}},
            "agenda": [
                {"day": "Mon", "date": "2026-05-11", "day_role": "ENDURANCE", "planned_duration": "00:20", "planned_kj": 100, "workout_id": "W1"},
                {"day": "Tue", "date": "2026-05-12", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Wed", "date": "2026-05-13", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Thu", "date": "2026-05-14", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Fri", "date": "2026-05-15", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Sat", "date": "2026-05-16", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
                {"day": "Sun", "date": "2026-05-17", "day_role": "REST", "planned_duration": "00:00", "planned_kj": 0, "workout_id": None},
            ],
            "workouts": [
                {
                    "workout_id": "W1",
                    "title": "Endurance",
                    "date": "2026-05-11",
                    "start": "07:00",
                    "duration": "00:20:00",
                    "workout_text": "Warmup\n- 5m ramp 50%-60% 85rpm\n\nMain Set\n- 15m 65% 85rpm",
                    "notes": "planned_kJ 100",
                }
            ],
        },
    }

    failed, message = week_workout_structure_policy_check(week_plan)

    assert failed is False
    assert "missing required section: Cooldown" in message


def test_week_phase_role_alignment_reports_forbidden_domain_workout_ids() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "agenda": [
                {"day": "Thu", "date": "2026-05-14", "day_role": "RECOVERY", "planned_duration": "00:45", "planned_kj": 250, "workout_id": "REC-1"}
            ],
            "workouts": [
                {
                    "workout_id": "REC-1",
                    "title": "Recovery Spin",
                    "notes": "RECOVERY",
                    "workout_text": "Warmup\n- 5m 55% 85rpm\n\nMain Set\n- 30m 60% 85rpm\n\nCooldown\n- 5m 55% 80rpm",
                }
            ],
        },
    }

    with guardrail_runtime_context(
        week_calendar_context={
            "phase_week_role": "LOAD",
            "allowed_day_roles": ["REST", "RECOVERY", "ENDURANCE", "QUALITY"],
            "quality_day_cap": 2,
            "allowed_intensity_domains": ["ENDURANCE", "TEMPO"],
            "forbidden_intensity_domains": ["RECOVERY", "THRESHOLD", "VO2MAX"],
        }
    ):
        failed, message = week_phase_role_alignment_check(week_plan)

        assert failed is True
        assert message == week_plan


def test_week_bundle_domain_legality_check_rejects_forbidden_workout_domains() -> None:
    bundle = {
        "context_summary": {},
        "constraint_summary": [],
        "load_target_summary": [],
        "revision_summary": [],
        "day_blueprints": [
            {"day": day, "date": date_value, "day_role": "REST" if day in {"Mon", "Fri"} else "ENDURANCE"}
            for day, date_value in [
                ("Mon", "2026-05-18"),
                ("Tue", "2026-05-19"),
                ("Wed", "2026-05-20"),
                ("Thu", "2026-05-21"),
                ("Fri", "2026-05-22"),
                ("Sat", "2026-05-23"),
                ("Sun", "2026-05-24"),
            ]
        ],
        "workout_blueprints": [
            {
                "workout_id": "REC-1",
                "date": "2026-05-19",
                "day_role": "ENDURANCE",
                "intensity_domain": "RECOVERY",
                "workout_family": "RECOVERY",
                "phase_legality_status": "illegal",
                "planned_duration_minutes": 60,
                "planned_kj": 500,
            },
            {
                "workout_id": "THR-1",
                "date": "2026-05-23",
                "day_role": "QUALITY",
                "intensity_domain": "THRESHOLD",
                "workout_family": "THRESHOLD",
                "phase_legality_status": "illegal",
                "planned_duration_minutes": 90,
                "planned_kj": 900,
            },
        ],
    }

    with guardrail_runtime_context(
        week_calendar_context={
            "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "forbidden_intensity_domains": ["RECOVERY", "THRESHOLD", "VO2MAX"],
        }
    ):
        failed, message = week_bundle_domain_legality_check(bundle)

    assert failed is False
    assert "forbidden intensity domains: RECOVERY (REC-1), THRESHOLD (THR-1)" in message


def test_week_phase_role_alignment_uses_approved_bundle_before_text_only_inference() -> None:
    week_plan = {
        "meta": {"artifact_type": "WEEK_PLAN", "schema_id": "WeekPlanInterface", "iso_week": "2026-20"},
        "data": {
            "agenda": [
                {"day": "Tue", "date": "2026-05-19", "day_role": "ENDURANCE", "planned_duration": "01:00", "planned_kj": 500, "workout_id": "W1"}
            ],
            "workouts": [
                {
                    "workout_id": "W1",
                    "title": "Endurance Ride",
                    "notes": "Threshold-like feel",
                    "workout_text": "Warmup\n- 5m 55% 85rpm\n\nMain Set\n- 30m 90% 85rpm\n\nCooldown\n- 5m 55% 80rpm",
                }
            ],
        },
    }

    with guardrail_runtime_context(
        week_calendar_context={
            "phase_week_role": "LOAD",
            "allowed_day_roles": ["REST", "ENDURANCE", "QUALITY"],
            "quality_day_cap": 2,
            "allowed_intensity_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"],
            "forbidden_intensity_domains": ["RECOVERY", "THRESHOLD", "VO2MAX"],
        },
        approved_planning_bundle={
            "workout_blueprints": [
                {
                    "workout_id": "W1",
                    "intensity_domain": "ENDURANCE",
                    "workout_family": "ENDURANCE",
                    "phase_legality_status": "legal",
                }
            ]
        },
    ):
        failed, message = week_phase_role_alignment_check(week_plan)

    assert failed is True
    assert message == week_plan


def test_runtime_profiles_keep_week_crews_planning_disabled_but_manager_reasoning_enabled() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])

    assert bundle.runtime_profiles["crews"]["week_planning"]["planning"]["enabled"] is False
    assert bundle.runtime_profiles["crews"]["week_review"]["planning"]["enabled"] is False
    assert bundle.runtime_profiles["crews"]["week_writer"]["planning"]["enabled"] is False
    assert bundle.runtime_profiles["agents"]["week_plan_manager"]["reasoning"]["enabled"] is True


def test_des_guardrail_rejects_non_diagnostic_recommendation() -> None:
    failed, message = des_diagnostic_only(
        {
            "meta": {"artifact_type": "DES_ANALYSIS_REPORT", "schema_id": "DESAnalysisReportInterface"},
            "data": {"recommendation": {"type": "intervention", "scope": "Week-Planner"}},
        }
    )

    assert failed is False
    assert "must remain advisory" in message


def test_output_model_registry_resolves_known_output_kinds() -> None:
    assert output_model_for_kind("turn_mode") is TurnModeModel
    assert output_model_for_kind("week_context_assessment") is WeekContextAssessmentModel
    assert output_model_for_kind("coaching_recommendation") is CoachingRecommendationModel
    assert output_model_for_kind("adjustment_intent") is AdjustmentIntentModel
    assert output_model_for_kind("pending_resolution_result") is PendingResolutionResultModel
    assert output_model_for_kind("artifact_envelope") is ArtifactEnvelopeModel
    assert output_model_for_kind("coach_preview") is CoachOperationPreviewModel
    assert output_model_for_kind("coach_apply") is CoachOperationApplyResultModel
    assert output_model_for_kind("season_event_anchor") is SeasonEventAnchorModel
    assert output_model_for_kind("season_macrocycle_draft") is SeasonMacrocycleDraftModel
    assert output_model_for_kind("season_plan_audit") is SeasonPlanAuditModel
    assert output_model_for_kind("season_plan_draft_bundle") is SeasonPlanDraftBundleModel
    assert output_model_for_kind("constraint_audit") is ConstraintAuditModel
    assert output_model_for_kind("load_governance_audit") is LoadGovernanceAuditModel
    assert output_model_for_kind("phase_bundle_draft") is PhaseDraftBundleModel
    assert output_model_for_kind("phase_bundle") is PhaseBundleModel
    assert output_model_for_kind("evidence_curation") is EvidenceCurationModel


def test_crewai_runtime_status_reports_python_compatibility() -> None:
    status = crewai_runtime_status()

    if sys.version_info >= (3, 14):
        assert status.python_supported is False
        assert status.ok is False
        assert "unsupported" in status.message.lower()
    else:
        assert status.python_supported is True


def test_crewai_runtime_status_compat_shim_matches_runtime_status_module() -> None:
    active = crewai_runtime_status()
    compat = compat_crewai_runtime_status()

    assert compat == active


def test_preview_scoped_week_replan_requires_message() -> None:
    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )
    preview = preview_scoped_week_replan_operation(
        lambda _name: runtime,
        store=LocalArtifactStore(root=Path("runtime/athletes")),
        athlete_id="i150546",
        year=2026,
        week=19,
        message="",
        run_id="preview-run",
    )
    assert preview.ok is False
    assert preview.requires_confirmation is True
    assert preview.issues


def test_preview_scoped_week_replan_returns_true_preview_metadata(monkeypatch, tmp_path: Path) -> None:
    athlete_id = "i150546"
    store = LocalArtifactStore(root=tmp_path)
    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=tmp_path,
    )
    base_document = {
        "meta": {
            "artifact_type": "WEEK_PLAN",
            "schema_id": "WeekPlanInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "test",
            "run_id": "base-run",
            "created_at": "2026-05-13T06:00:00Z",
            "scope": "Shared",
            "iso_week": "2026-19",
            "iso_week_range": "2026-19--2026-19",
            "temporal_scope": {"from": "2026-05-04", "to": "2026-05-10"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "HIGH",
            "notes": "test",
        },
        "data": {
            "agenda": [
                {
                    "day": "Tue",
                    "date": "2026-05-05",
                    "day_role": "ENDURANCE",
                    "planned_duration": "01:30",
                    "planned_kj": 900,
                    "workout_id": "w1",
                }
            ],
            "workouts": [
                {
                    "workout_id": "w1",
                    "title": "Aerobic Endurance",
                    "date": "2026-05-05",
                    "start": "18:00",
                    "duration": "01:30:00",
                }
            ],
        },
    }
    preview_document = {
        **base_document,
        "data": {
            "agenda": [
                {
                    "day": "Tue",
                    "date": "2026-05-05",
                    "day_role": "ENDURANCE",
                    "planned_duration": "01:10",
                    "planned_kj": 780,
                    "workout_id": "w1",
                }
            ],
            "workouts": [
                {
                    "workout_id": "w1",
                    "title": "Aerobic Endurance",
                    "date": "2026-05-05",
                    "start": "18:00",
                    "duration": "01:10:00",
                }
            ],
        },
    }
    store.save_document(
        athlete_id,
        ArtifactType.WEEK_PLAN,
        "2026-19",
        base_document,
        producer_agent="test",
        run_id="base-run",
        update_latest=True,
    )
    monkeypatch.setattr(
        "rps.orchestrator.coach_operations.preview_week_plan_revision",
        lambda *args, **kwargs: {"ok": True, "document": preview_document},
    )
    monkeypatch.setattr("rps.orchestrator.coach_operations.validate_document", lambda *args, **kwargs: None)

    preview = preview_scoped_week_replan_operation(
        lambda _name: runtime,
        store=store,
        athlete_id=athlete_id,
        year=2026,
        week=19,
        message="Reduce Tuesday slightly.",
        run_id="preview-run",
    )

    assert preview.ok is True
    assert preview.document == preview_document
    metadata = preview.metadata
    assert metadata["change_rows"]
    assert "| Date | Day | Workout | Before | After |" in metadata["change_table_markdown"]
    first_change = metadata["change_rows"][0]
    assert first_change["workout"] == "Aerobic Endurance"
    assert "Workout: Aerobic Endurance;" in first_change["before"]
    assert "Duration: 01:10:00;" in first_change["after"]
    assert "before.json" in metadata["diff_text"]


def test_preview_report_and_feed_forward_operations_are_typed() -> None:
    report_preview = preview_report_operation(year=2026, week=19)
    feed_forward_preview = preview_feed_forward_operation(year=2026, week=19)

    assert report_preview.operation == "preview_report"
    assert report_preview.requires_confirmation is True
    assert "DES_ANALYSIS_REPORT" in report_preview.affected_artifacts

    assert feed_forward_preview.operation == "preview_feed_forward"
    assert feed_forward_preview.requires_confirmation is True
    assert "PHASE_FEED_FORWARD" in feed_forward_preview.affected_artifacts


def test_coach_flow_routes_confirmation_and_records_events(monkeypatch, tmp_path: Path) -> None:
    _install_fake_crewai_events(monkeypatch)
    _install_fake_flow_module(monkeypatch)

    result = run_coach_flow(
        workspace_root=tmp_path,
        athlete_id="athlete",
        run_id="run-1",
        user_message="confirm",
        chat_runner=lambda: "chat",
    )

    assert result["route"] == "conversational_turn"
    assert result["response"] == "chat"
    events = load_events(tmp_path, "athlete", "run-1")
    event_types = [str(event.get("type")) for event in events]
    assert "FLOW_STARTED" in event_types
    assert "FLOW_ROUTED" in event_types
    assert "FLOW_STEP_FINISHED" in event_types
    assert "FLOW_FINISHED" in event_types


def test_event_listener_compacts_task_and_crew_labels(monkeypatch, tmp_path: Path, caplog) -> None:
    events_module = _install_fake_crewai_events(monkeypatch)
    crewai_telemetry.ensure_crewai_event_listener()
    bus = events_module.crewai_event_bus

    task = SimpleNamespace(
        id="12345678-abcdef",
        description="System instructions:\n# giant injected prompt body that must never be copied into telemetry",
    )
    crew = SimpleNamespace(name="crew")

    caplog.set_level(logging.INFO, logger="rps.crewai_runtime.telemetry")
    with crewai_telemetry.runtime_event_scope(
        root=tmp_path,
        athlete_id="athlete",
        run_id="run-compact",
        component="coach_turn",
    ):
        bus.emit(events_module.CrewKickoffStartedEvent(crew=crew))
        bus.emit(events_module.TaskStartedEvent(task=task))
        bus.emit(events_module.ToolUsageStartedEvent(tool=SimpleNamespace(name="read_current_plan_context")))

    events = load_events(tmp_path, "athlete", "run-compact")
    assert events[0]["type"] == "CREW_STARTED"
    assert events[0]["crew"] == "coach_turn"
    assert events[1]["type"] == "CREW_TASK_STARTED"
    assert events[1]["task"] == "SimpleNamespace#12345678"
    assert "System instructions:" not in events[1]["task"]
    assert events[2]["type"] == "TOOL_STARTED"
    assert events[2]["tool"] == "read_current_plan_context"
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "CrewAI runtime type=CREW_TASK_STARTED" in log_text
    assert "run_id=run-compact" in log_text
    assert "component=coach_turn" in log_text
    assert "task=SimpleNamespace#12345678" in log_text
    assert "System instructions:" not in log_text


def test_event_listener_uses_registered_runtime_labels(monkeypatch, tmp_path: Path, caplog) -> None:
    events_module = _install_fake_crewai_events(monkeypatch)
    crewai_telemetry.ensure_crewai_event_listener()
    bus = events_module.crewai_event_bus

    task = SimpleNamespace(name="Task")
    crew = SimpleNamespace(name="crew")
    agent = SimpleNamespace(role="Task Execution Planner")
    crewai_telemetry.register_runtime_label(task, kind="task", label="season_plan_finalize")
    crewai_telemetry.register_runtime_label(crew, kind="crew", label="season_planning")
    crewai_telemetry.register_runtime_label(agent, kind="agent", label="season_plan_manager")
    crewai_telemetry.register_runtime_metadata(
        task, assigned_agent="season_plan_manager", assigned_model="gpt-5.4-mini"
    )
    crewai_telemetry.register_runtime_metadata(agent, model="gpt-5.4-mini")

    caplog.set_level(logging.INFO, logger="rps.crewai_runtime.telemetry")
    with crewai_telemetry.runtime_event_scope(
        root=tmp_path,
        athlete_id="athlete",
        run_id="run-labelled",
        component="crew:season_plan_finalize",
    ):
        bus.emit(events_module.CrewKickoffStartedEvent(crew=crew))
        bus.emit(events_module.TaskStartedEvent(task=task, agent=agent))

    events = load_events(tmp_path, "athlete", "run-labelled")
    assert events[0]["crew"] == "season_planning"
    assert events[1]["task"] == "season_plan_finalize"
    assert events[1]["agent"] == "season_plan_manager"
    assert events[1]["assigned_agent"] == "season_plan_manager"
    assert events[1]["model"] == "gpt-5.4-mini"
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "crew=season_planning" in log_text
    assert "task=season_plan_finalize" in log_text
    assert "agent=season_plan_manager" in log_text
    assert "model=gpt-5.4-mini" in log_text


def test_crewai_backend_emits_task_prepared_events_before_kickoff(tmp_path: Path, caplog) -> None:
    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=tmp_path,
    )

    caplog.set_level(logging.INFO, logger="rps.crewai_runtime.telemetry")
    _emit_crew_task_prepared_events(
        runtime=runtime,
        crew_name="season_planning",
        tasks=[
            ("season_context_read", "season_context_specialist", "gpt-5.4-nano"),
            ("season_plan_finalize", "season_plan_manager", "gpt-5.4-mini"),
        ],
        athlete_id="athlete",
        run_id="run-prepared",
        component="crew:season_plan_finalize",
    )

    events = load_events(tmp_path, "athlete", "run-prepared")
    assert [event["type"] for event in events] == ["CREW_TASK_PREPARED", "CREW_TASK_PREPARED"]
    assert events[0]["task"] == "season_context_read"
    assert events[0]["agent"] == "season_context_specialist"
    assert events[0]["model"] == "gpt-5.4-nano"
    assert events[0]["status"] == "1/2"
    assert events[1]["task"] == "season_plan_finalize"
    assert events[1]["agent"] == "season_plan_manager"
    assert events[1]["model"] == "gpt-5.4-mini"
    assert events[1]["status"] == "2/2"
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "type=CREW_TASK_PREPARED" in log_text
    assert "crew=season_planning" in log_text
    assert "task=season_context_read" in log_text


def test_runtime_gateway_defaults_to_crewai(monkeypatch) -> None:
    monkeypatch.delenv("RPS_AGENT_RUNTIME", raising=False)
    selection = agent_runtime.resolve_agent_runtime_selection()

    assert selection.requested_backend == "crewai"
    assert selection.effective_backend == "crewai"
    assert selection.is_fallback is False


def test_runtime_gateway_rejects_unknown_backend(monkeypatch) -> None:
    monkeypatch.setenv("RPS_AGENT_RUNTIME", "legacy")
    selection = agent_runtime.resolve_agent_runtime_selection(requested_backend="legacy")

    assert selection.requested_backend == "crewai"
    assert selection.effective_backend == "crewai"


def test_runtime_gateway_dispatches_to_crewai_backend(monkeypatch) -> None:
    marker = {"called": False}

    def _fake_selection():
        return agent_runtime.AgentRuntimeSelection(
            requested_backend="crewai",
            effective_backend="crewai",
            can_execute=True,
            is_fallback=False,
            reason="ok",
            crewai_status=crewai_runtime_status(),
        )

    def _fake_backend(*args, **kwargs):
        marker["called"] = True
        return {"ok": True, "produced": {}}

    monkeypatch.setattr(agent_runtime, "resolve_agent_runtime_selection", _fake_selection)
    module = types.ModuleType("rps.agents.crewai_backend")
    module.run_agent_multi_output_crewai = _fake_backend
    monkeypatch.setitem(sys.modules, "rps.agents.crewai_backend", module)

    result = agent_runtime.run_agent_multi_output()
    assert result["ok"] is True
    assert marker["called"] is True


def test_run_agent_multi_output_crewai_persists_typed_output(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "openai/gpt-5-mini")
    fake_crewai = types.ModuleType("crewai")
    fake_tools = types.ModuleType("crewai.tools")

    class FakeLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    created_agents: list[dict[str, object]] = []

    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.llm = kwargs.get("llm")
            created_agents.append(kwargs)

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.output_pydantic = kwargs.get("output_pydantic")
            self.output_json = kwargs.get("output_json")
            self.output = None

    captured_crew: dict[str, object] = {"crews": []}

    class FakeCrew:
        def __init__(self, *, tasks, **kwargs):
            self.tasks = tasks
            self.kwargs = kwargs
            captured_crew["crews"].append(kwargs)
            captured_crew["agents"] = kwargs.get("agents", [])
            captured_crew["max_agents"] = max(
                int(captured_crew.get("max_agents", 0)),
                len(kwargs.get("agents", [])),
            )
            captured_crew["tasks"] = tasks
            if kwargs.get("manager_agent") is not None:
                captured_crew["manager_agent"] = kwargs.get("manager_agent")
            captured_crew["process"] = kwargs.get("process")

        def kickoff(self):
            task = self.tasks[-1]
            model_cls = task.output_pydantic
            if model_cls is None:
                payload = {
                    "meta": {
                        "artifact_type": "SEASON_PLAN",
                        "schema_id": "SeasonPlanInterface",
                        "schema_version": "1.0",
                    },
                    "data": {},
                }
                task.output = SimpleNamespace(pydantic=None, raw=json.dumps(payload))
                return task.output
            if model_cls is ArtifactEnvelopeModel:
                model = model_cls(
                    meta={
                        "artifact_type": "SEASON_PLAN",
                        "schema_id": "SeasonPlanInterface",
                        "schema_version": "1.0",
                    },
                    data={},
                )
            elif model_cls is SeasonPlanDraftBundleModel:
                model = model_cls(
                    event_priority=SeasonEventAnchorModel(),
                    macrocycle=SeasonMacrocycleDraftModel(),
                    phase_blueprints=[
                        SeasonPhaseDraftBlueprintModel(
                            phase_id="P01",
                            iso_week_range="2026-20--2026-22",
                            scenario_cadence="2:1",
                            cadence_week_roles=["LOAD_1", "LOAD_2", "DELOAD"],
                            phase_type="BASE",
                            phase_intent="shortened_re_entry",
                        )
                    ],
                )
            elif model_cls is SeasonReviewDecisionModel:
                model = model_cls(status="approved", writer_ready_summary="ready")
            elif model_cls is PlanningDraftModel:
                model = model_cls()
            elif model_cls is WeekPlanBundleModel:
                model = model_cls(
                    day_blueprints=[
                        WeekDayBlueprintModel(
                            day=day,
                            date=date_value,
                            day_role="REST",
                        )
                        for day, date_value in [
                            ("Mon", "2026-05-11"),
                            ("Tue", "2026-05-12"),
                            ("Wed", "2026-05-13"),
                            ("Thu", "2026-05-14"),
                            ("Fri", "2026-05-15"),
                            ("Sat", "2026-05-16"),
                            ("Sun", "2026-05-17"),
                        ]
                    ],
                    workout_blueprints=[
                        WeekWorkoutBlueprintModel(
                            workout_id="W1",
                            date="2026-05-12",
                            day_role="ENDURANCE",
                            planned_duration_minutes=60,
                            planned_kj=500,
                        )
                    ],
                )
            elif model_cls is WeekReviewDecisionModel:
                model = model_cls(status="approved", writer_ready_summary="ready")
            elif model_cls is DESAnalysisBundleModel:
                model = model_cls()
            elif model_cls is ReportReviewDecisionModel:
                model = model_cls(status="approved", writer_ready_summary="ready")
            else:
                model = model_cls()
            task.output = SimpleNamespace(pydantic=model, raw=model.model_dump_json())
            return task.output

    class FakeProcess:
        sequential = "sequential"
        hierarchical = "hierarchical"

    def _tool(name: str):
        def _decorate(func):
            func.tool_name = name
            return func

        return _decorate

    fake_crewai.LLM = FakeLLM
    fake_crewai.Agent = FakeAgent
    fake_crewai.Task = FakeTask
    fake_crewai.Crew = FakeCrew
    fake_crewai.Process = FakeProcess
    fake_tools.tool = _tool

    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    monkeypatch.setitem(sys.modules, "crewai.tools", fake_tools)

    saved = {"ok": True, "path": "/tmp/out.json", "version_key": "2026-19__x", "run_id": "run-1"}

    def _fake_guard_put_validated(self, **kwargs):
        return saved

    monkeypatch.setattr(
        "rps.agents.crewai_backend.GuardedValidatedStore.guard_put_validated",
        _fake_guard_put_validated,
    )
    monkeypatch.setattr(
        "rps.agents.crewai_backend.normalize_season_plan_draft_bundle",
        lambda _bundle: {
            "event_priority": {"primary_a_events": ["A Event"]},
            "macrocycle": {"deload_cadence": "2:1"},
            "season_load_envelope": {"expected_average_weekly_kj_range": {"min": 7000, "max": 9000}},
            "season_semantic_notes": ["Frame the objective against the A event."],
            "phase_blueprints": [
                {
                    "phase_id": "P01",
                    "iso_week_range": "2026-20--2026-22",
                    "scenario_cadence": "2:1",
                    "cadence_week_roles": ["LOAD_1", "LOAD_2", "DELOAD"],
                    "phase_type": "BASE",
                    "phase_intent": "shortened_re_entry",
                    "phase_taxonomy_version": "canonical_phase_taxonomy_v1",
                    "allowed_domains": ["ENDURANCE", "TEMPO"],
                    "forbidden_domains": ["THRESHOLD", "VO2MAX"],
                    "semantic_contract": {
                        "methodology_family": "compressed_reentry",
                        "threshold_role": "forbidden",
                        "event_load_policy": "no_event_load_exception",
                        "taper_policy": "not_applicable",
                        "writer_semantic_notes": ["Keep the phase recovery-protective."],
                    },
                }
            ],
        },
    )
    monkeypatch.setattr(
        "rps.agents.crewai_backend._validate_normalized_season_bundle",
        lambda planning_bundle, **kwargs: planning_bundle,
    )

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_agent_multi_output_crewai(
        runtime,
        agent_name="season_planner",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_SEASON_PLAN],
        user_input="Create the season plan.",
        run_id="run-1",
        model_override="gpt-5.4-nano",
    )

    assert result["ok"] is True
    assert result["produced"]["store_season_plan"] == saved
    assert isinstance(captured_crew["agents"], list)
    assert int(captured_crew["max_agents"]) >= 7
    assert captured_crew["crews"][0].get("manager_agent") is None
    assert captured_crew["crews"][0].get("process") == "sequential"
    assert captured_crew["crews"][1].get("manager_agent") is None
    assert captured_crew["crews"][1].get("process") == "sequential"
    planning_crews = [crew for crew in captured_crew["crews"] if crew.get("planning") is True]
    assert planning_crews == []
    macrocycle_agent = next(agent for agent in created_agents if agent["role"] == "Reverse-plan season macrocycles")
    assert "reasoning" not in macrocycle_agent
    assert "max_reasoning_attempts" not in macrocycle_agent
    assert getattr(macrocycle_agent["llm"], "kwargs", {}).get("model") == "gpt-5.4"
    writer_agent = next(agent for agent in created_agents if agent["role"] == "Persisted season artefact serializer")
    assert "reasoning" not in writer_agent
    assert writer_agent["allow_delegation"] is False
    assert writer_agent["max_iter"] == 2
    assert writer_agent["respect_context_window"] is True
    assert writer_agent["cache"] is False
    assert getattr(writer_agent["llm"], "kwargs", {}).get("model") == "gpt-5.4-mini"
    manager_agent = next(agent for agent in created_agents if agent["role"] == "Internal season planning synthesizer")
    assert manager_agent["allow_delegation"] is False
    assert manager_agent["max_iter"] == 5


def test_run_agent_multi_output_crewai_phase_bundle_split(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "openai/gpt-5-mini")
    fake_crewai = types.ModuleType("crewai")
    fake_tools = types.ModuleType("crewai.tools")

    class FakeLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    created_agents: list[dict[str, object]] = []

    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.llm = kwargs.get("llm")
            created_agents.append(kwargs)

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.output_pydantic = kwargs.get("output_pydantic")
            self.description = kwargs["description"]
            self.output = None

    captured_crew: dict[str, object] = {"crews": []}

    class FakeCrew:
        def __init__(self, *, tasks, **kwargs):
            self.tasks = tasks
            self.kwargs = kwargs
            captured_crew["crews"].append(kwargs)
            captured_crew["agents"] = kwargs.get("agents", [])
            captured_crew["max_agents"] = max(
                int(captured_crew.get("max_agents", 0)),
                len(kwargs.get("agents", [])),
            )
            captured_crew["tasks"] = tasks
            if kwargs.get("manager_agent") is not None:
                captured_crew["manager_agent"] = kwargs.get("manager_agent")
            captured_crew["process"] = kwargs.get("process")

        def kickoff(self):
            task = self.tasks[-1]
            model_cls = task.output_pydantic
            if model_cls is PhaseDraftBundleModel:
                model = model_cls(
                    phase_range="2026-17--2026-19",
                    phase_id="P01",
                    phase_type="Base",
                    phase_intent="general_base",
                    cadence_source="season_plan",
                    week_blueprints=[
                        PhaseWeekDraftBlueprintModel(
                            week="2026-17",
                            phase_role="Base",
                            week_role="LOAD_1",
                            s5_band_min=5000,
                            s5_band_max=6000,
                        )
                    ],
                    guardrails={"phase_intent": "general_base", "phase_summary": ["Conservative base support."]},
                    structure={"phase_intent": "general_base"},
                    preview={"phase_intent": "general_base", "phase_intent_summary": ["Stable aerobic build."]},
                    constraint_audit={"blocking_issues": []},
                    load_governance_audit={"blocking_issues": []},
                    decision_summary={},
                )
            elif model_cls is PhaseReviewDecisionModel:
                model = model_cls(status="approved", writer_ready_summary="ready")
            elif model_cls is PlanningDraftModel:
                model = model_cls()
            elif model_cls is None:
                payload = {
                    "meta": {
                        "artifact_type": "PHASE_GUARDRAILS",
                        "schema_id": "PhaseGuardrailsInterface",
                        "schema_version": "1.0",
                        "owner_agent": "Phase-Artifact-Writer",
                    },
                    "data": {},
                }
                task.output = SimpleNamespace(pydantic=None, raw=json.dumps(payload))
                return task.output
            else:
                model = model_cls()
            task.output = SimpleNamespace(pydantic=model, raw=model.model_dump_json())
            return task.output

    class FakeProcess:
        sequential = "sequential"
        hierarchical = "hierarchical"

    def _tool(name: str):
        def _decorate(func):
            func.tool_name = name
            return func

        return _decorate

    fake_crewai.LLM = FakeLLM
    fake_crewai.Agent = FakeAgent
    fake_crewai.Task = FakeTask
    fake_crewai.Crew = FakeCrew
    fake_crewai.Process = FakeProcess
    fake_tools.tool = _tool

    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    monkeypatch.setitem(sys.modules, "crewai.tools", fake_tools)

    captured: dict[str, object] = {}

    def _fake_guard_put_validated(self, **kwargs):
        captured.update(kwargs)
        return {"ok": True, "path": "/tmp/phase.json", "version_key": "2026-17__x", "run_id": "run-phase"}

    monkeypatch.setattr(
        "rps.agents.crewai_backend.GuardedValidatedStore.guard_put_validated",
        _fake_guard_put_validated,
    )
    monkeypatch.setattr(
        "rps.agents.crewai_backend.normalize_phase_draft_bundle",
        lambda payload: payload,
    )
    monkeypatch.setattr(
        "rps.agents.crewai_backend._validate_normalized_phase_bundle",
        lambda payload, **_: payload,
    )

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_agent_multi_output_crewai(
        runtime,
        agent_name="phase_architect",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_PHASE_GUARDRAILS],
        user_input="Create phase guardrails.",
        run_id="run-phase",
    )

    assert result["ok"] is True
    document = captured["document"]
    assert isinstance(document, dict)
    meta = document["meta"]
    assert meta["artifact_type"] == "PHASE_GUARDRAILS"
    assert meta["owner_agent"] == "Phase-Artifact-Writer"
    assert isinstance(captured_crew["agents"], list)
    assert int(captured_crew["max_agents"]) >= 7
    assert captured_crew["crews"][0].get("manager_agent") is None
    assert captured_crew["crews"][0].get("process") == "sequential"
    assert captured_crew["crews"][1].get("manager_agent") is None
    assert captured_crew["crews"][1].get("process") == "sequential"
    planning_crews = [crew for crew in captured_crew["crews"] if crew.get("planning") is True]
    assert planning_crews == []
    band_agent = next(agent for agent in created_agents if agent["role"] == "Phase weekly corridor specialist")
    assert "reasoning" not in band_agent
    assert "max_reasoning_attempts" not in band_agent
    assert getattr(band_agent["llm"], "kwargs", {}).get("model") == "gpt-5.4-mini"
    writer_agent = next(agent for agent in created_agents if agent["role"] == "Persisted phase artefact serializer")
    assert "reasoning" not in writer_agent
    assert writer_agent["allow_delegation"] is False
    assert writer_agent["max_iter"] == 2
    assert writer_agent["respect_context_window"] is True
    assert getattr(writer_agent["llm"], "kwargs", {}).get("model") == "gpt-5.4-mini"


def test_run_agent_multi_output_crewai_week_plan_uses_sequential_specialist_execution(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "openai/gpt-5-mini")
    fake_crewai = types.ModuleType("crewai")
    fake_tools = types.ModuleType("crewai.tools")

    class FakeLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    created_agents: list[dict[str, object]] = []

    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.llm = kwargs.get("llm")
            created_agents.append(kwargs)

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.output_pydantic = kwargs.get("output_pydantic")
            self.output_json = kwargs.get("output_json")
            self.output = None

    captured_crew: dict[str, object] = {"crews": []}

    class FakeCrew:
        def __init__(self, *, tasks, **kwargs):
            self.tasks = tasks
            self.kwargs = kwargs
            captured_crew["crews"].append(kwargs)

        def kickoff(self):
            task = self.tasks[-1]
            model_cls = task.output_pydantic or task.output_json
            if model_cls is WeekPlanBundleModel:
                model = model_cls(
                    day_blueprints=[
                        WeekDayBlueprintModel(day="Mon", date="2026-05-11", day_role="REST"),
                        WeekDayBlueprintModel(day="Tue", date="2026-05-12", day_role="QUALITY"),
                        WeekDayBlueprintModel(day="Wed", date="2026-05-13", day_role="ENDURANCE"),
                        WeekDayBlueprintModel(day="Thu", date="2026-05-14", day_role="ENDURANCE"),
                        WeekDayBlueprintModel(day="Fri", date="2026-05-15", day_role="REST"),
                        WeekDayBlueprintModel(day="Sat", date="2026-05-16", day_role="LONG"),
                        WeekDayBlueprintModel(day="Sun", date="2026-05-17", day_role="ENDURANCE"),
                    ],
                    workout_blueprints=[
                        WeekWorkoutBlueprintModel(
                            workout_id="W1",
                            date="2026-05-12",
                            day_role="QUALITY",
                            planned_duration_minutes=75,
                            planned_kj=650,
                        )
                    ],
                )
            elif model_cls is WeekReviewDecisionModel:
                model = model_cls(status="approved", writer_ready_summary="ready")
            elif model_cls is ArtifactEnvelopeModel:
                model = model_cls(
                    meta={
                        "artifact_type": "WEEK_PLAN",
                        "schema_id": "WeekPlanInterface",
                        "schema_version": "1.2",
                    },
                    data={"workouts": []},
                )
            else:
                model = model_cls()
            task.output = SimpleNamespace(
                pydantic=model if task.output_pydantic is not None else None,
                json_dict=model.model_dump() if hasattr(model, "model_dump") else None,
                raw=model.model_dump_json(),
            )
            return task.output

    class FakeProcess:
        sequential = "sequential"
        hierarchical = "hierarchical"

    def _tool(name: str):
        def _decorate(func):
            func.tool_name = name
            return func

        return _decorate

    fake_crewai.LLM = FakeLLM
    fake_crewai.Agent = FakeAgent
    fake_crewai.Task = FakeTask
    fake_crewai.Crew = FakeCrew
    fake_crewai.Process = FakeProcess
    fake_tools.tool = _tool

    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    monkeypatch.setitem(sys.modules, "crewai.tools", fake_tools)

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    bundle = load_crewai_config_bundle(root=Path.cwd())
    agent_blueprints = build_agent_blueprints(bundle)
    task_blueprints = build_task_blueprints(bundle)
    tools = {
        name: SimpleNamespace(name=name)
        for name in (
            "workspace_get_input",
            "workspace_get_latest",
            "workspace_get_version",
            "workspace_get_phase_context",
            "workspace_get_week_calendar_context",
            "workspace_get_phase_execution_context",
        )
    }

    result = _execute_crewai_multiagent_crew(
        agent_cls=FakeAgent,
        crewai_llm_cls=FakeLLM,
        crew_cls=FakeCrew,
        task_cls=FakeTask,
        process_cls=FakeProcess,
        runtime=runtime,
        bundle=bundle,
        manager_agent_name="week_plan_manager",
        crew_name="week_planning",
        crew_task_names=(
            "week_context_read",
            "week_constraint_review",
            "week_load_target_draft",
            "week_revision_draft",
            "week_workout_text_draft",
            "week_plan_finalize",
        ),
        final_task_name="week_plan_finalize",
        task_blueprints=task_blueprints,
        agent_blueprints=agent_blueprints,
        tools=tools,
        user_input="Create week plan.",
        athlete_id="i150546",
        run_id="run-week",
        execution_mode="sequential",
    )

    assert result.model_dump()["day_blueprints"]
    assert captured_crew["crews"][0].get("manager_agent") is None
    assert captured_crew["crews"][0].get("process") == "sequential"
    manager_agent = next(agent for agent in created_agents if agent["role"] == "Internal week bundle synthesizer")
    assert getattr(manager_agent["llm"], "kwargs", {}).get("model") == "gpt-5.4-mini"


def test_run_multicrew_cycle_replays_only_sanitized_replan_context(tmp_path) -> None:
    captured_inputs: list[str] = []

    def _planning_runner(loop_input: str) -> dict[str, object]:
        captured_inputs.append(loop_input)
        return {"bundle": "candidate", "warnings": []}

    decisions = iter(
        [
            {
                "status": "replan_required",
                "blocking_issues": ["Old blocker that must not be replayed wholesale."],
                "warnings": ["Stale warning that should not be forwarded."],
                "replan_instructions": [
                    {
                        "target_specialists": ["Week Planner"],
                        "issues_to_fix": ["Reduce weekly kJ into active band."],
                        "must_preserve": ["Fixed rest days Mon and Fri."],
                        "priority_order": ["Bring weekly kJ into band first."],
                        "max_scope_of_change": "Adjust durations only.",
                    }
                ],
                "writer_ready_summary": "Use the repaired draft only.",
            },
            {
                "status": "approved",
                "warnings": [],
                "blocking_issues": [],
                "replan_instructions": [],
                "writer_ready_summary": "",
            },
        ]
    )

    def _review_runner(loop_input: str, planning_bundle: dict[str, object]) -> dict[str, object]:
        return next(decisions)

    planning_bundle, review_decision = _run_multicrew_cycle(
        runtime=AgentRuntime(
            model="gpt-5.4-mini",
            temperature=None,
            reasoning_effort=None,
            reasoning_summary=None,
            max_completion_tokens=None,
            prompt_loader=SimpleNamespace(),
            schema_dir=tmp_path,
            workspace_root=tmp_path,
        ),
        bundle=SimpleNamespace(),
        user_input="Create week plan.",
        planning_runner=_planning_runner,
        review_runner=_review_runner,
        max_replan_rounds=2,
    )

    assert planning_bundle == {"bundle": "candidate", "warnings": []}
    assert review_decision["status"] == "approved"
    assert len(captured_inputs) == 2
    second_input = captured_inputs[1]
    assert "Active replan instructions" in second_input
    assert "Reduce weekly kJ into active band." in second_input
    assert "Stale warning that should not be forwarded." not in second_input
    assert "Old blocker that must not be replayed wholesale." not in second_input


def test_review_decision_integrity_rejects_approved_blocking_issues() -> None:
    ok, message = review_decision_integrity(
        {
            "status": "approved",
            "blocking_issues": ["Still broken."],
            "warnings": [],
            "replan_instructions": [],
            "writer_ready_summary": "ready",
        }
    )

    assert ok is False
    assert "must not include blocking_issues" in message


def test_review_decision_integrity_requires_writer_ready_summary_for_approval() -> None:
    ok, message = review_decision_integrity(
        {
            "status": "approved",
            "blocking_issues": [],
            "warnings": [],
            "replan_instructions": [],
            "writer_ready_summary": "",
        }
    )

    assert ok is False
    assert "must include non-empty writer_ready_summary" in message


def test_review_decision_integrity_requires_replan_instructions_for_replan() -> None:
    ok, message = review_decision_integrity(
        {
            "status": "replan_required",
            "blocking_issues": ["Needs repair."],
            "warnings": [],
            "replan_instructions": [],
            "writer_ready_summary": "fix it",
        }
    )

    assert ok is False
    assert "must include replan_instructions" in message


def test_run_agent_multi_output_crewai_normalizes_feed_forward_owner(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "openai/gpt-5-mini")
    fake_crewai = types.ModuleType("crewai")
    fake_tools = types.ModuleType("crewai.tools")

    class FakeLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.output_pydantic = kwargs.get("output_pydantic")
            self.output = None

    class FakeCrew:
        def __init__(self, *, tasks, **kwargs):
            self.tasks = tasks
            self.kwargs = kwargs

        def kickoff(self):
            task = self.tasks[0]
            model_cls = task.output_pydantic
            payload = {
                "meta": {
                    "artifact_type": "SEASON_PHASE_FEED_FORWARD",
                    "schema_id": "SeasonPhaseFeedForwardInterface",
                    "schema_version": "1.0",
                    "owner_agent": "Performance-Analyst",
                },
                "data": {},
            }
            if model_cls is None:
                task.output = SimpleNamespace(pydantic=None, raw=json.dumps(payload))
                return task.output
            envelope = model_cls(**payload)
            task.output = SimpleNamespace(pydantic=envelope, raw=envelope.model_dump_json())
            return task.output

    class FakeProcess:
        sequential = "sequential"

    def _tool(name: str):
        def _decorate(func):
            func.tool_name = name
            return func

        return _decorate

    fake_crewai.LLM = FakeLLM
    fake_crewai.Agent = FakeAgent
    fake_crewai.Task = FakeTask
    fake_crewai.Crew = FakeCrew
    fake_crewai.Process = FakeProcess
    fake_tools.tool = _tool

    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    monkeypatch.setitem(sys.modules, "crewai.tools", fake_tools)

    captured: dict[str, object] = {}

    def _fake_guard_put_validated(self, **kwargs):
        captured.update(kwargs)
        return {"ok": True, "path": "/tmp/out.json", "version_key": "2026-19__x", "run_id": "run-ff"}

    monkeypatch.setattr(
        "rps.agents.crewai_backend.GuardedValidatedStore.guard_put_validated",
        _fake_guard_put_validated,
    )

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_agent_multi_output_crewai(
        runtime,
        agent_name="season_planner",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_SEASON_PHASE_FEED_FORWARD],
        user_input="Create season-phase feed-forward.",
        run_id="run-ff",
    )

    assert result["ok"] is True
    document = captured["document"]
    assert isinstance(document, dict)
    meta = document["meta"]
    assert meta["owner_agent"] == "Season-Artifact-Writer"


def test_decorate_persist_supports_factory_style(monkeypatch) -> None:
    from rps.crewai_runtime import flows as flow_module

    monkeypatch.setattr(flow_module, '_flow_should_persist', lambda _name: True)

    class DummyFlow:
        pass

    def _persist_factory():
        def _decorate(target):
            class Persisted(target):
                persisted_style = 'factory'

            return Persisted

        return _decorate

    decorated = flow_module._decorate_persist(DummyFlow, 'season', _persist_factory)

    assert decorated is not DummyFlow
    assert getattr(decorated, 'persisted_style', None) == 'factory'


def test_decorate_persist_supports_direct_style(monkeypatch) -> None:
    from rps.crewai_runtime import flows as flow_module

    monkeypatch.setattr(flow_module, '_flow_should_persist', lambda _name: True)

    class DummyFlow:
        pass

    def _persist_direct(target):
        class Persisted(target):
            persisted_style = 'direct'

        return Persisted

    decorated = flow_module._decorate_persist(DummyFlow, 'season', _persist_direct)

    assert decorated is not DummyFlow
    assert getattr(decorated, 'persisted_style', None) == 'direct'


def test_decorate_persist_fails_open_on_unexpected_shape(monkeypatch) -> None:
    from rps.crewai_runtime import flows as flow_module

    monkeypatch.setattr(flow_module, '_flow_should_persist', lambda _name: True)

    class DummyFlow:
        pass

    def _persist_weird(target):
        return lambda missing: missing

    decorated = flow_module._decorate_persist(DummyFlow, 'season', _persist_weird)

    assert decorated is DummyFlow


def test_run_season_flow_routes_to_requested_task(monkeypatch) -> None:
    _install_fake_flow_module(monkeypatch)

    captured: dict[str, object] = {}

    def _fake_run_agent_multi_output(*args, **kwargs):
        captured["task"] = kwargs["tasks"][0]
        return {"ok": True, "produced": {"store": {"run_id": kwargs["run_id"]}}}

    monkeypatch.setattr("rps.crewai_runtime.flows.run_agent_multi_output", _fake_run_agent_multi_output)

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_season_flow(
        runtime_for=lambda _name: runtime,
        agent_name="season_planner",
        athlete_id="i150546",
        task=AgentTask.CREATE_SEASON_PLAN,
        user_input="Create season plan.",
        run_id="season-flow-run",
    )

    assert result["ok"] is True
    assert captured["task"] == AgentTask.CREATE_SEASON_PLAN


def test_run_phase_flow_executes_bundle_once(monkeypatch) -> None:
    _install_fake_flow_module(monkeypatch)
    marker = {"calls": 0}

    def _fake_run_phase_bundle_crewai(*args, **kwargs):
        marker["calls"] += 1
        return {"ok": True, "produced": {"store_phase_guardrails": {"run_id": kwargs["run_id"]}}}

    monkeypatch.setattr("rps.crewai_runtime.flows.run_phase_bundle_crewai", _fake_run_phase_bundle_crewai)

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_phase_flow(
        runtime,
        agent_name="phase_architect",
        athlete_id="i150546",
        tasks=[
            AgentTask.CREATE_PHASE_GUARDRAILS,
            AgentTask.CREATE_PHASE_STRUCTURE,
            AgentTask.CREATE_PHASE_PREVIEW,
        ],
        user_input="Create phase bundle.",
        run_id="phase-flow-run",
    )

    assert result["ok"] is True
    assert marker["calls"] == 1


def test_run_week_flow_dispatches_week_task(monkeypatch) -> None:
    _install_fake_flow_module(monkeypatch)
    captured: dict[str, object] = {}

    def _fake_execute_week_engine(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "produced": {"store_week_plan": {"run_id": kwargs["run_id"]}}}

    monkeypatch.setattr("rps.crewai_runtime.flows.execute_week_engine", _fake_execute_week_engine)

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_week_flow(
        runtime_for=lambda _name: runtime,
        agent_name="week_planner",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_WEEK_PLAN],
        user_input="Target ISO week: year=2026, week=21. Message: ",
        run_id="week-flow-run",
    )

    assert result["ok"] is True
    assert captured["target_year"] == 2026
    assert captured["target_week"] == 21
    assert captured["preview_only"] is False


def test_run_week_flow_preview_only_dispatches_preview_runner(monkeypatch) -> None:
    _install_fake_flow_module(monkeypatch)
    captured: dict[str, object] = {}

    def _fake_execute_week_engine(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "artifact_type": "WEEK_PLAN", "document": {"meta": {}, "data": {}}}

    monkeypatch.setattr("rps.crewai_runtime.flows.execute_week_engine", _fake_execute_week_engine)

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_week_flow(
        runtime_for=lambda _name: runtime,
        agent_name="week_planner",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_WEEK_PLAN],
        user_input="Target ISO week: year=2026, week=21. Message: make it easier",
        run_id="week-flow-preview-run",
        preview_only=True,
    )

    assert result["ok"] is True
    assert captured["preview_only"] is True
    assert captured["user_message"] == "make it easier"


def test_run_report_flow_executes_runner(monkeypatch) -> None:
    _install_fake_flow_module(monkeypatch)
    marker = {"calls": 0}

    def _runner():
        marker["calls"] += 1
        return {"ok": True, "produced": {"store_des_analysis_report": {"run_id": "report-run"}}}

    result = run_report_flow(_runner)

    assert result["ok"] is True
    assert marker["calls"] == 1


def test_run_report_flow_converts_runner_exception_to_failure_state(monkeypatch) -> None:
    _install_fake_flow_module(monkeypatch)

    def _runner():
        raise RuntimeError("schema store failed")

    result = run_report_flow(_runner)

    assert result == {"ok": False, "error": "schema store failed"}


def test_run_feed_forward_flow_runs_chain(monkeypatch) -> None:
    _install_fake_flow_module(monkeypatch)
    marker = {"report": 0, "season": 0, "phase": 0}

    def _report():
        marker["report"] += 1
        return {"ok": True}

    def _season():
        marker["season"] += 1
        return {"ok": True}

    def _phase():
        marker["phase"] += 1
        return {"ok": True}

    result = run_feed_forward_flow(
        report_runner=_report,
        season_phase_runner=_season,
        phase_runner=_phase,
    )

    assert result["report_result"]["ok"] is True
    assert result["season_phase_result"]["ok"] is True
    assert result["phase_result"]["ok"] is True
    assert marker == {"report": 1, "season": 1, "phase": 1}


def test_direct_crewai_provider_config_uses_env_without_litellm(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "global-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "openai/gpt-5-mini")
    monkeypatch.setenv("RPS_LLM_BASE_URL", "https://api.openai.com/v1")

    config = resolve_crewai_provider_config("coach")
    kwargs = build_crewai_llm_kwargs("coach")

    assert config.api_key == "global-key"
    assert config.model == "openai/gpt-5-mini"
    assert kwargs["api_key"] == "global-key"
    assert kwargs["model"] == "openai/gpt-5-mini"


def test_app_settings_default_model_uses_gpt54_family(monkeypatch) -> None:
    monkeypatch.delenv("RPS_LLM_MODEL", raising=False)
    monkeypatch.delenv("RPS_LLM_BASE_URL", raising=False)

    settings = load_app_settings()

    assert settings.openai_model == "gpt-5.4-mini"


def test_planning_provider_overrides_and_app_settings(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "global-key")
    monkeypatch.setenv("RPS_LLM_BASE_URL", "https://api.openai.com/v1")

    assert resolve_crewai_planning_enabled("season_planning", default_enabled=True) is True
    planning_kwargs = build_crewai_planning_llm_kwargs(
        "season_planning",
        default_model="gpt-5.4",
    )
    assert planning_kwargs is not None
    assert planning_kwargs["model"] == "gpt-5.4"
    assert planning_kwargs["api_key"] == "global-key"

    settings = load_app_settings()
    assert settings.planning_enabled_for_crew("season_planning", True) is True
    assert settings.planning_model_for_crew("season_planning", "gpt-5.4") == "gpt-5.4"


def test_app_settings_ignore_agent_and_crew_scoped_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "global-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("RPS_LLM_MODEL_COACH", "gpt-5.4")
    monkeypatch.setenv("RPS_LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("RPS_LLM_TEMPERATURE_COACH", "0.9")
    monkeypatch.setenv("RPS_CREW_PLANNING_SEASON_PLANNING", "false")
    monkeypatch.setenv("RPS_CREW_PLANNING_LLM_SEASON_PLANNING", "gpt-5.4-nano")

    settings = load_app_settings()

    assert settings.model_for_agent("coach") == "gpt-5.4-mini"
    assert settings.temperature_for_agent("coach") == 0.2
    assert settings.planning_enabled_for_crew("season_planning", True) is True
    assert settings.planning_model_for_crew("season_planning", "gpt-5.4") == "gpt-5.4"
    provider = resolve_crewai_provider_config("coach")
    assert provider.model == "gpt-5.4-mini"
    assert provider.temperature == 0.2
