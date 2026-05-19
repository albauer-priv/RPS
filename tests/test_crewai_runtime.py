from __future__ import annotations

import json
import logging
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace

from rps.agents import runtime as agent_runtime
from rps.agents.crewai_backend import (
    _TASK_BLUEPRINT_BY_AGENT_TASK,
    _build_crewai_task,
    _coerce_artifact_envelope,
    _contract_context_blocks_for_task,
    _emit_crew_task_prepared_events,
    _task_tools_for_blueprint,
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
    phase_s5_band_match,
    phase_week_role_load_coherence,
    phase_weeks_match_range,
    resolve_task_policy,
    season_bundle_integrity,
    season_phase_load_feasibility,
    season_scenario_selection_shape,
    week_active_corridor_match,
    week_agenda_shape_and_calendar_check,
    week_corridor_and_capacity_check,
    week_daily_availability_check,
    week_phase_role_alignment_check,
    week_recovery_day_load_check,
    week_workout_structure_policy_check,
)
from rps.crewai_runtime.knowledge import (
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
    LoadGovernanceAuditModel,
    PendingResolutionResultModel,
    PhaseBundleModel,
    PhaseReviewDecisionModel,
    PhaseWeekBlueprintModel,
    PlanningDraftModel,
    ReportReviewDecisionModel,
    SeasonEventAnchorModel,
    SeasonMacrocycleDraftModel,
    SeasonPhaseBlueprintModel,
    SeasonPlanAuditModel,
    SeasonPlanBundleModel,
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
from rps.orchestrator.coach_operations import (
    preview_feed_forward_operation,
    preview_report_operation,
    preview_scoped_week_replan_operation,
)
from rps.orchestrator.resolved_context import build_resolved_load_governance_context_block
from rps.planning.deterministic_context import build_week_calendar_context
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
    assert bundle.runtime_profiles["agents"]["macrocycle_architect"]["model"] == "gpt-5.4"
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
    assert tasks["phase_bundle_finalize"].output_kind == "phase_bundle"
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
        "phase_bundle_matches_context",
        "phase_week_role_load_coherence",
    )


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
        "season_plan_bundle",
        "season_review_decision",
        "phase_guardrails_payload",
        "phase_structure_payload",
        "phase_preview_payload",
        "constraint_audit",
        "load_governance_audit",
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

    class FakeStringKnowledgeSource:
        def __init__(self, *, content: str):
            self.content = content

    fake_module = types.ModuleType("crewai.knowledge.source.string_knowledge_source")
    fake_module.StringKnowledgeSource = FakeStringKnowledgeSource
    monkeypatch.setitem(sys.modules, "crewai.knowledge.source.string_knowledge_source", fake_module)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-rps-key")

    kwargs = build_crewai_knowledge_kwargs(
        root=skill_root,
        profile={"sources": [{"path": "sample.md"}], "knowledge_config": {}},
    )

    assert "knowledge_sources" in kwargs
    assert os.environ["OPENAI_API_KEY"] == "test-rps-key"


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
    bibliography = Path("skills/conversation/guarded-operations/references/durability_bibliography.md")

    assert bibliography.exists()
    assert "references/durability_bibliography.md" in coach_skill
    assert "doi.org" in coach_skill
    assert "Maunder/Seiler/Kilding/Plews" in coach_skill
    assert "available web-search result" in recommendation_skill
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
        phase_blueprints=[
            SeasonPhaseBlueprintModel(
                phase_id="P03",
                iso_week_range="2026-26--2026-29",
                scenario_cadence="2:1:1",
                cadence_week_roles=["LOAD_1", "LOAD_2", "MINI_RESET", "RELOAD"],
                cycle="Build",
                event_constraints=[],
                load_corridor_min=7600,
                load_corridor_max=9300,
                availability_cap_kj=10000,
                baseline_load_kj=8000,
                season_phase_role="build_progression",
                role_week_load_bands=["2026-26 LOAD_1 min 7600 max 8400"],
                progression_trace=["source deterministic season phase load context"],
                load_feasibility_status="feasible",
                taper_intent="none",
                allowed_domains=["RECOVERY", "ENDURANCE", "TEMPO"],
            )
        ],
    )

    assert model.phase_blueprints[0].scenario_cadence == "2:1:1"
    assert model.phase_blueprints[0].cadence_week_roles == ["LOAD_1", "LOAD_2", "MINI_RESET", "RELOAD"]
    assert model.phase_blueprints[0].availability_cap_kj == 10000


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
        phase_execution_context={"phase_id": "P01", "phase_s5_bands": []},
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
    assert any("Deterministic Week Calendar Contract" in block for block in week_blocks)
    assert any("Deterministic Phase Execution Contract" in block for block in week_blocks)
    assert any("Do not delegate or rediscover active week role" in block for block in week_blocks)


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
    assert any("Deterministic Phase Execution Contract" in block for block in phase_blocks)
    assert any("Phase review rule" in block for block in phase_blocks)
    assert any("Deterministic Week Calendar Contract" in block for block in week_blocks)
    assert any("Week review rule" in block for block in week_blocks)


def test_review_managers_disable_free_delegation_via_yaml_override() -> None:
    bundle = load_crewai_config_bundle(root=Path(__file__).resolve().parents[1])
    agent_blueprints = build_agent_blueprints(bundle)

    assert agent_blueprints["season_review_manager"].config["allow_delegation"] is False
    assert agent_blueprints["phase_review_manager"].config["allow_delegation"] is False
    assert agent_blueprints["week_review_manager"].config["allow_delegation"] is False


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
    assert output_model_for_kind("constraint_audit") is ConstraintAuditModel
    assert output_model_for_kind("load_governance_audit") is LoadGovernanceAuditModel
    assert output_model_for_kind("phase_bundle") is PhaseBundleModel


def test_crewai_runtime_status_reports_python_compatibility() -> None:
    status = crewai_runtime_status()

    if sys.version_info >= (3, 14):
        assert status.python_supported is False
        assert status.ok is False
        assert "unsupported" in status.message.lower()
    else:
        assert status.python_supported is True


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
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "crew=season_planning" in log_text
    assert "task=season_plan_finalize" in log_text
    assert "agent=season_plan_manager" in log_text


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
            ("season_context_read", "season_context_specialist"),
            ("season_plan_finalize", "season_plan_manager"),
        ],
        athlete_id="athlete",
        run_id="run-prepared",
        component="crew:season_plan_finalize",
    )

    events = load_events(tmp_path, "athlete", "run-prepared")
    assert [event["type"] for event in events] == ["CREW_TASK_PREPARED", "CREW_TASK_PREPARED"]
    assert events[0]["task"] == "season_context_read"
    assert events[0]["agent"] == "season_context_specialist"
    assert events[0]["status"] == "1/2"
    assert events[1]["task"] == "season_plan_finalize"
    assert events[1]["agent"] == "season_plan_manager"
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
            elif model_cls is SeasonPlanBundleModel:
                model = model_cls(
                    event_priority=SeasonEventAnchorModel(),
                    macrocycle=SeasonMacrocycleDraftModel(),
                    phase_blueprints=[
                        SeasonPhaseBlueprintModel(
                            phase_id="P01",
                            iso_week_range="2026-20--2026-22",
                            scenario_cadence="2:1",
                            cadence_week_roles=["LOAD_1", "LOAD_2", "DELOAD"],
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
    assert captured_crew["manager_agent"] is not None
    planning_crews = [crew for crew in captured_crew["crews"] if crew.get("planning") is True]
    assert planning_crews == []
    macrocycle_agent = next(agent for agent in created_agents if agent["role"] == "Reverse-plan season macrocycles")
    assert macrocycle_agent["reasoning"] is True
    assert macrocycle_agent["max_reasoning_attempts"] == 2
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
            if model_cls is PhaseBundleModel:
                model = model_cls(
                    phase_range="2026-17--2026-19",
                    phase_id="P01",
                    phase_type="Base",
                    cadence_source="season_plan",
                    week_blueprints=[
                        {
                            "week": "2026-17",
                            "phase_role": "Base",
                            "week_role": "LOAD_1",
                            "s5_band_min": 5000,
                            "s5_band_max": 6000,
                        }
                    ],
                    guardrails={},
                    structure={},
                    preview={},
                    constraint_audit={},
                    load_governance_audit={},
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
    assert captured_crew["manager_agent"] is not None
    planning_crews = [crew for crew in captured_crew["crews"] if crew.get("planning") is True]
    assert planning_crews == []
    band_agent = next(agent for agent in created_agents if agent["role"] == "Phase weekly corridor specialist")
    assert band_agent["reasoning"] is True
    assert band_agent["max_reasoning_attempts"] == 2
    assert getattr(band_agent["llm"], "kwargs", {}).get("model") == "gpt-5.4-mini"
    writer_agent = next(agent for agent in created_agents if agent["role"] == "Persisted phase artefact serializer")
    assert "reasoning" not in writer_agent
    assert writer_agent["allow_delegation"] is False
    assert writer_agent["max_iter"] == 2
    assert writer_agent["respect_context_window"] is True
    assert getattr(writer_agent["llm"], "kwargs", {}).get("model") == "gpt-5.4-mini"


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

    def _fake_run_agent_multi_output(*args, **kwargs):
        captured["tasks"] = kwargs["tasks"]
        return {"ok": True, "produced": {"store_week_plan": {"run_id": kwargs["run_id"]}}}

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

    result = run_week_flow(
        runtime_for=lambda _name: runtime,
        agent_name="week_planner",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_WEEK_PLAN],
        user_input="Create week plan.",
        run_id="week-flow-run",
    )

    assert result["ok"] is True
    assert captured["tasks"] == [AgentTask.CREATE_WEEK_PLAN]


def test_run_week_flow_preview_only_dispatches_preview_runner(monkeypatch) -> None:
    _install_fake_flow_module(monkeypatch)
    captured: dict[str, object] = {}

    def _fake_run_agent_multi_output_preview(*args, **kwargs):
        captured["tasks"] = kwargs["tasks"]
        captured["preview_only"] = True
        return {"ok": True, "artifact_type": "WEEK_PLAN", "document": {"meta": {}, "data": {}}}

    monkeypatch.setattr("rps.crewai_runtime.flows.run_agent_multi_output_preview", _fake_run_agent_multi_output_preview)

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
        user_input="Preview week plan.",
        run_id="week-flow-preview-run",
        preview_only=True,
    )

    assert result["ok"] is True
    assert captured["tasks"] == [AgentTask.CREATE_WEEK_PLAN]
    assert captured["preview_only"] is True


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
