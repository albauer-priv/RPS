from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

from rps.agents import runtime as agent_runtime
from rps.agents.crewai_backend import run_agent_multi_output_crewai
from rps.agents.runtime import AgentRuntime
from rps.agents.tasks import AgentTask
from rps.crewai_runtime import crewai_runtime_status, load_crewai_config_bundle
from rps.crewai_runtime import telemetry as crewai_telemetry
from rps.crewai_runtime.bindings import (
    build_agent_blueprints,
    build_task_blueprints,
    output_model_for_kind,
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
    build_task_guardrail_kwargs,
    resolve_task_policy,
)
from rps.crewai_runtime.knowledge import (
    resolve_agent_knowledge_profile,
    resolve_crew_knowledge_profile,
)
from rps.crewai_runtime.memory import resolve_agent_memory_profile, resolve_crew_memory_profile
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
    PlanningDraftModel,
    ReportReviewDecisionModel,
    SeasonEventAnchorModel,
    SeasonMacrocycleDraftModel,
    SeasonPlanAuditModel,
    SeasonPlanBundleModel,
    SeasonReviewDecisionModel,
    TurnModeModel,
    WeekContextAssessmentModel,
    WeekPlanBundleModel,
    WeekReviewDecisionModel,
)
from rps.crewai_runtime.provider import build_crewai_llm_kwargs, resolve_crewai_provider_config
from rps.crewai_runtime.skills import render_skill_prompt_block, resolve_agent_skill_profile
from rps.orchestrator.coach_operations import (
    preview_feed_forward_operation,
    preview_report_operation,
    preview_scoped_week_replan_operation,
)
from rps.prompts.loader import PromptLoader
from rps.ui.run_store import load_events
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
    assert task_defs["classify_turn"]["agent"] == "conversation_manager"
    assert task_defs["create_week_preview"]["agent"] == "week_revision_specialist"
    assert task_defs["week_plan"]["agent"] == "week_artifact_writer"
    assert task_defs["season_plan"]["agent"] == "season_artifact_writer"
    assert task_defs["phase_guardrails"]["agent"] == "phase_artifact_writer"


def test_crewai_blueprints_build_from_yaml() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    agents = build_agent_blueprints(bundle)
    tasks = build_task_blueprints(bundle)

    assert agents["conversation_manager"].goal
    assert agents["season_plan_auditor"].goal
    assert agents["season_plan_auditor"].config["prompt_agent"] == "season_plan_auditor"
    assert agents["phase_guardrail_band_specialist"].config["prompt_agent"] == "guardrails_specialist"
    assert agents["week_recommendation_specialist"].knowledge_profile["sources"]
    assert agents["week_recommendation_specialist"].skill_profile["paths"]
    assert tasks["classify_turn"].output_kind == "turn_mode"
    assert tasks["form_adjustment_intent"].output_kind == "adjustment_intent"
    assert tasks["week_plan"].output_kind == "artifact_envelope"
    assert tasks["phase_bundle_finalize"].output_kind == "phase_bundle"
    assert tasks["phase_bundle_finalize"].execution_policy["guardrails"] == ("typed_output_present", "phase_bundle_integrity")


def test_task_policy_resolution_and_guardrail_kwargs() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    tasks = build_task_blueprints(bundle)

    preview_policy = resolve_task_policy(tasks["create_week_preview"], bundle.task_policies)
    artifact_policy = resolve_task_policy(tasks["week_plan"], bundle.task_policies)

    assert preview_policy.output_mode == "pydantic"
    assert "coach_preview_summary_complete" in preview_policy.guardrails
    assert artifact_policy.output_mode == "json"
    kwargs = build_task_guardrail_kwargs(tasks["week_plan"], bundle.task_policies)
    assert kwargs["guardrail_max_retries"] == 2
    assert callable(kwargs["guardrails"][0]) or callable(kwargs["guardrail"])


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
    assert specialist_memory["mode"] == "slice_read_only"
    assert "/athlete/i150546/coach/accepted_patterns" in specialist_memory["additional_read_scopes"]


def test_skill_prompt_block_renders_configured_skills() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    profile = resolve_agent_skill_profile(bundle, agent_name="week_revision_specialist", crew_name="coach_conversation")
    skill_block = render_skill_prompt_block(root=Path("."), profile=profile)
    assert "skills/week/revision-methodology/SKILL.md" in skill_block
    assert "skills/shared/runtime-boundaries/SKILL.md" in skill_block


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
        vs_resolver=SimpleNamespace(id_for_store_name=lambda name: name),
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
        vs_resolver=SimpleNamespace(id_for_store_name=lambda name: name),
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


def test_event_listener_compacts_task_and_crew_labels(monkeypatch, tmp_path: Path) -> None:
    events_module = _install_fake_crewai_events(monkeypatch)
    crewai_telemetry.ensure_crewai_event_listener()
    bus = events_module.crewai_event_bus

    task = SimpleNamespace(
        id="12345678-abcdef",
        description="System instructions:\n# giant injected prompt body that must never be copied into telemetry",
    )
    crew = SimpleNamespace(name="crew")

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


def test_runtime_gateway_defaults_to_crewai(monkeypatch) -> None:
    monkeypatch.delenv("RPS_AGENT_RUNTIME", raising=False)
    selection = agent_runtime.resolve_agent_runtime_selection()

    assert selection.requested_backend == "crewai"
    assert selection.effective_backend == "crewai"
    assert selection.is_fallback is False


def test_runtime_gateway_rejects_unknown_backend(monkeypatch) -> None:
    monkeypatch.setenv("RPS_AGENT_RUNTIME", "legacy")
    selection = agent_runtime.resolve_agent_runtime_selection()

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

    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.output_pydantic = kwargs.get("output_pydantic")
            self.output = None

    captured_crew: dict[str, object] = {}

    class FakeCrew:
        def __init__(self, *, tasks, **kwargs):
            self.tasks = tasks
            self.kwargs = kwargs
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
                )
            elif model_cls is SeasonReviewDecisionModel:
                model = model_cls(status="approved", writer_ready_summary="ready")
            elif model_cls is PlanningDraftModel:
                model = model_cls()
            elif model_cls is WeekPlanBundleModel:
                model = model_cls()
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
        vs_resolver=SimpleNamespace(id_for_store_name=lambda name: name),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_agent_multi_output_crewai(
        runtime,
        agent_name="season_planner",
        agent_vs_name="vs_rps_all_agents",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_SEASON_PLAN],
        user_input="Create the season plan.",
        run_id="run-1",
    )

    assert result["ok"] is True
    assert result["produced"]["store_season_plan"] == saved
    assert isinstance(captured_crew["agents"], list)
    assert int(captured_crew["max_agents"]) >= 7
    assert captured_crew["manager_agent"] is not None


def test_run_agent_multi_output_crewai_phase_bundle_split(monkeypatch) -> None:
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
            self.description = kwargs["description"]
            self.output = None

    captured_crew: dict[str, object] = {}

    class FakeCrew:
        def __init__(self, *, tasks, **kwargs):
            self.tasks = tasks
            self.kwargs = kwargs
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
                    guardrails={},
                    structure={},
                    preview={},
                    guardrails_document={
                        "meta": {
                            "artifact_type": "PHASE_GUARDRAILS",
                            "schema_id": "PhaseGuardrailsInterface",
                            "schema_version": "1.0",
                            "owner_agent": "Phase-Architect",
                        },
                        "data": {},
                    },
                    structure_document={
                        "meta": {
                            "artifact_type": "PHASE_STRUCTURE",
                            "schema_id": "PhaseStructureInterface",
                            "schema_version": "1.0",
                            "owner_agent": "Phase-Architect",
                        },
                        "data": {},
                    },
                    preview_document={
                        "meta": {
                            "artifact_type": "PHASE_PREVIEW",
                            "schema_id": "PhasePreviewInterface",
                            "schema_version": "1.0",
                            "owner_agent": "Phase-Architect",
                        },
                        "data": {},
                    },
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
        vs_resolver=SimpleNamespace(id_for_store_name=lambda name: name),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_agent_multi_output_crewai(
        runtime,
        agent_name="phase_architect",
        agent_vs_name="vs_rps_all_agents",
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
        vs_resolver=SimpleNamespace(id_for_store_name=lambda name: name),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_agent_multi_output_crewai(
        runtime,
        agent_name="season_planner",
        agent_vs_name="vs_rps_all_agents",
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
        vs_resolver=SimpleNamespace(id_for_store_name=lambda name: name),
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
        vs_resolver=SimpleNamespace(id_for_store_name=lambda name: name),
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
        vs_resolver=SimpleNamespace(id_for_store_name=lambda name: name),
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
        vs_resolver=SimpleNamespace(id_for_store_name=lambda name: name),
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
    monkeypatch.setenv("RPS_LLM_API_KEY_COACH", "coach-key")
    monkeypatch.setenv("RPS_LLM_MODEL_COACH", "openai/gpt-5-nano")

    config = resolve_crewai_provider_config("coach")
    kwargs = build_crewai_llm_kwargs("coach")

    assert config.api_key == "coach-key"
    assert config.model == "openai/gpt-5-nano"
    assert kwargs["api_key"] == "coach-key"
    assert kwargs["model"] == "openai/gpt-5-nano"
