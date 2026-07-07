from __future__ import annotations

import logging
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from rps.agents import runtime as agent_runtime
from rps.agents.crewai_builders import _emit_crew_task_prepared_events
from rps.agents.runtime import AgentRuntime
from rps.agents.tasks import AgentTask
from rps.crewai_runtime import crewai_runtime_status
from rps.crewai_runtime import telemetry as crewai_telemetry
from rps.crewai_runtime.flows import (
    run_coach_flow,
    run_feed_forward_flow,
    run_phase_flow,
    run_report_flow,
    run_season_flow,
    run_week_flow,
)
from rps.prompts.loader import PromptLoader
from rps.ui.run_store import load_events


def _set_module_attrs(module: types.ModuleType, **attrs: Any) -> None:
    for key, value in attrs.items():
        setattr(module, key, value)


def _install_fake_crewai_events(monkeypatch) -> types.ModuleType:
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
    _set_module_attrs(events_module, BaseEventListener=BaseEventListener, crewai_event_bus=bus)
    monkeypatch.setitem(sys.modules, "crewai.events", events_module)
    crewai_telemetry._LISTENER_READY = False
    crewai_telemetry._LISTENER_INIT_FAILED = False
    return events_module


def _install_fake_flow_module(monkeypatch) -> None:
    """Install a minimal CrewAI Flow module for unit tests."""

    flow_module = types.ModuleType("crewai.flow.flow")
    events_module = sys.modules.get("crewai.events")
    events_module_any = cast(Any, events_module)
    bus = getattr(events_module_any, "crewai_event_bus", None)

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

    _set_module_attrs(flow_module, Flow=FakeFlow, start=start, listen=listen, router=router)
    monkeypatch.setitem(sys.modules, "crewai.flow.flow", flow_module)


def _install_strict_state_flow_module(monkeypatch) -> None:
    """Install a fake Flow module that reproduces the dict-state regression."""

    flow_module = types.ModuleType("crewai.flow.flow")

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
        _state_model = None

        @classmethod
        def __class_getitem__(cls, item):
            class TypedFakeFlow(cls):
                _state_model = item

            return TypedFakeFlow

        def __init__(self):
            if getattr(type(self), "_state_model", None) is None:
                self.state = {}
            else:
                self.state = SimpleNamespace(action="", result={}, requested_tasks=[])

        def kickoff(self):
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
            current_result = start_method()
            current_name = getattr(start_method, "__name__", "")
            if router_method is not None:
                route_label = router_method(current_result)
                for trigger, listener_method in listeners:
                    if trigger == route_label:
                        current_result = listener_method()
                        current_name = getattr(listener_method, "__name__", "")
                        break
                else:
                    return None
            while True:
                next_listener = None
                for trigger, listener_method in listeners:
                    trigger_name = getattr(trigger, "__name__", None)
                    if trigger_name == current_name:
                        next_listener = listener_method
                        break
                if next_listener is None:
                    return current_result
                current_result = next_listener(current_result)
                current_name = getattr(next_listener, "__name__", "")

    _set_module_attrs(flow_module, Flow=FakeFlow, start=start, listen=listen, router=router)
    monkeypatch.setitem(sys.modules, "crewai.flow.flow", flow_module)


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
    events = cast(Any, events_module)
    bus = events.crewai_event_bus

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
        bus.emit(events.CrewKickoffStartedEvent(crew=crew))
        bus.emit(events.TaskStartedEvent(task=task))
        bus.emit(events.ToolUsageStartedEvent(tool=SimpleNamespace(name="read_current_plan_context")))

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
    events = cast(Any, events_module)
    bus = events.crewai_event_bus

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
        bus.emit(events.CrewKickoffStartedEvent(crew=crew))
        bus.emit(events.TaskStartedEvent(task=task, agent=agent))

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
    module = types.ModuleType("rps.agents.crewai_task_execution")
    _set_module_attrs(module, run_agent_multi_output_crewai=_fake_backend)
    monkeypatch.setitem(sys.modules, "rps.agents.crewai_task_execution", module)

    result = agent_runtime.run_agent_multi_output()
    assert result["ok"] is True
    assert marker["called"] is True

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

def test_run_season_flow_uses_typed_flow_state(monkeypatch) -> None:
    _install_strict_state_flow_module(monkeypatch)

    monkeypatch.setattr(
        "rps.crewai_runtime.flows.run_agent_multi_output",
        lambda *args, **kwargs: {"ok": True, "produced": {}},
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

    result = run_season_flow(
        runtime_for=lambda _name: runtime,
        agent_name="season_planner",
        athlete_id="i150546",
        task=AgentTask.CREATE_SEASON_SCENARIOS,
        user_input="Create season scenarios.",
        run_id="season-flow-state-run",
    )

    assert result["ok"] is True

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

def test_run_phase_flow_uses_typed_flow_state(monkeypatch) -> None:
    _install_strict_state_flow_module(monkeypatch)

    monkeypatch.setattr(
        "rps.crewai_runtime.flows.run_phase_bundle_crewai",
        lambda *args, **kwargs: {"ok": True, "produced": {}},
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

    result = run_phase_flow(
        runtime,
        agent_name="phase_architect",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_PHASE_GUARDRAILS],
        user_input="Create phase bundle.",
        run_id="phase-flow-state-run",
    )

    assert result["ok"] is True

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

def test_run_week_flow_uses_typed_flow_state(monkeypatch) -> None:
    _install_strict_state_flow_module(monkeypatch)

    monkeypatch.setattr(
        "rps.crewai_runtime.flows.execute_week_engine",
        lambda **kwargs: {"ok": True, "produced": {"store_week_plan": {"run_id": kwargs["run_id"]}}},
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

    result = run_week_flow(
        runtime_for=lambda _name: runtime,
        agent_name="week_planner",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_WEEK_PLAN],
        user_input="Target ISO week: year=2026, week=21. Message: ",
        run_id="week-flow-state-run",
    )

    assert result["ok"] is True

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

def test_run_report_flow_uses_typed_flow_state(monkeypatch) -> None:
    _install_strict_state_flow_module(monkeypatch)

    result = run_report_flow(lambda: {"ok": True})

    assert result["ok"] is True

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

def test_run_feed_forward_flow_uses_typed_flow_state(monkeypatch) -> None:
    _install_strict_state_flow_module(monkeypatch)

    result = run_feed_forward_flow(
        report_runner=lambda: {"ok": True},
        season_phase_runner=lambda: {"ok": True},
        phase_runner=lambda: {"ok": True},
    )

    assert result["report_result"]["ok"] is True
    assert result["season_phase_result"]["ok"] is True
    assert result["phase_result"]["ok"] is True
