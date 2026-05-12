"""CrewAI event-listener adapter for the local run-store telemetry."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from rps.ui.run_store import append_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CrewAIRunContext:
    """Per-execution run context used to route CrewAI events into our run-store."""

    root: Path
    athlete_id: str
    run_id: str
    component: str | None = None


_RUN_CONTEXT: ContextVar[CrewAIRunContext | None] = ContextVar("rps_crewai_run_context", default=None)
_LISTENER_READY = False
_LISTENER_INIT_FAILED = False


def _append_with_context(event_type: str, **payload: object) -> None:
    """Append an event when a run context is currently active."""

    ctx = _RUN_CONTEXT.get()
    if ctx is None:
        return
    event_payload = {"type": event_type, **payload}
    if ctx.component and "component" not in event_payload:
        event_payload["component"] = ctx.component
    try:
        append_event(ctx.root, ctx.athlete_id, ctx.run_id, event_payload)
    except Exception as exc:  # pragma: no cover - telemetry must remain best-effort
        logger.warning("Failed to append CrewAI runtime event %s for run %s: %s", event_type, ctx.run_id, exc)


def emit_runtime_event(
    *,
    root: Path | None,
    athlete_id: str | None,
    run_id: str | None,
    event_type: str,
    **payload: object,
) -> None:
    """Append one explicit RPS-owned runtime event when context is available."""

    if root is None or not athlete_id or not run_id:
        return
    try:
        append_event(
            root,
            athlete_id,
            run_id,
            {
                "type": event_type,
                **payload,
            },
        )
    except Exception as exc:  # pragma: no cover - telemetry must stay best-effort
        logger.warning("Failed to append runtime event %s for run %s: %s", event_type, run_id, exc)


def _event_attr(event: object, *names: str) -> object | None:
    """Return the first matching attribute on an event object."""

    for name in names:
        if hasattr(event, name):
            return getattr(event, name)
    return None


def _safe_str(value: object, default: str = "—") -> str:
    """Return a readable string for telemetry payloads."""

    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _tool_name(event: object) -> str:
    """Resolve a tool name from the CrewAI event payload."""

    direct = _event_attr(event, "tool_name", "tool")
    if isinstance(direct, str):
        return direct
    if hasattr(direct, "__name__"):
        return _safe_str(getattr(direct, "__name__"))
    return "—"


def ensure_crewai_event_listener() -> None:
    """Register the singleton CrewAI event listener once."""

    global _LISTENER_READY, _LISTENER_INIT_FAILED
    if _LISTENER_READY or _LISTENER_INIT_FAILED:
        return
    try:
        crewai_events = import_module("crewai.events")
        BaseEventListener = getattr(crewai_events, "BaseEventListener")
        CrewKickoffStartedEvent = getattr(crewai_events, "CrewKickoffStartedEvent")
        CrewKickoffCompletedEvent = getattr(crewai_events, "CrewKickoffCompletedEvent")
        CrewKickoffFailedEvent = getattr(crewai_events, "CrewKickoffFailedEvent")
        TaskStartedEvent = getattr(crewai_events, "TaskStartedEvent")
        TaskCompletedEvent = getattr(crewai_events, "TaskCompletedEvent")
        TaskFailedEvent = getattr(crewai_events, "TaskFailedEvent")
        ToolUsageStartedEvent = getattr(crewai_events, "ToolUsageStartedEvent")
        ToolUsageFinishedEvent = getattr(crewai_events, "ToolUsageFinishedEvent")
        ToolUsageErrorEvent = getattr(crewai_events, "ToolUsageErrorEvent")
        FlowStartedEvent = getattr(crewai_events, "FlowStartedEvent")
        FlowFinishedEvent = getattr(crewai_events, "FlowFinishedEvent")
        MethodExecutionStartedEvent = getattr(crewai_events, "MethodExecutionStartedEvent")
        MethodExecutionFinishedEvent = getattr(crewai_events, "MethodExecutionFinishedEvent")
        MethodExecutionFailedEvent = getattr(crewai_events, "MethodExecutionFailedEvent")
    except Exception as exc:  # pragma: no cover - depends on installed CrewAI runtime
        _LISTENER_INIT_FAILED = True
        logger.warning("CrewAI event listener setup unavailable: %s", exc)
        return

    class RPSCrewAIEventListener(BaseEventListener):
        """Translate CrewAI lifecycle events into run-store rows."""

        def setup_listeners(self, crewai_event_bus: Any) -> None:  # pragma: no cover - integration behavior
            @crewai_event_bus.on(CrewKickoffStartedEvent)
            def _on_crew_started(_source: object, event: object) -> None:
                _append_with_context(
                    "CREW_STARTED",
                    crew=_safe_str(_event_attr(event, "crew_name", "crew_id", "crew")),
                )

            @crewai_event_bus.on(CrewKickoffCompletedEvent)
            def _on_crew_finished(_source: object, event: object) -> None:
                _append_with_context(
                    "CREW_FINISHED",
                    crew=_safe_str(_event_attr(event, "crew_name", "crew_id", "crew")),
                )

            @crewai_event_bus.on(CrewKickoffFailedEvent)
            def _on_crew_failed(_source: object, event: object) -> None:
                _append_with_context(
                    "CREW_FAILED",
                    crew=_safe_str(_event_attr(event, "crew_name", "crew_id", "crew")),
                    reason=_safe_str(_event_attr(event, "error", "error_message", "message")),
                )

            @crewai_event_bus.on(TaskStartedEvent)
            def _on_task_started(_source: object, event: object) -> None:
                _append_with_context(
                    "CREW_TASK_STARTED",
                    task=_safe_str(_event_attr(event, "task_name", "task_id", "task")),
                )

            @crewai_event_bus.on(TaskCompletedEvent)
            def _on_task_completed(_source: object, event: object) -> None:
                _append_with_context(
                    "CREW_TASK_FINISHED",
                    task=_safe_str(_event_attr(event, "task_name", "task_id", "task")),
                )

            @crewai_event_bus.on(TaskFailedEvent)
            def _on_task_failed(_source: object, event: object) -> None:
                _append_with_context(
                    "CREW_TASK_FAILED",
                    task=_safe_str(_event_attr(event, "task_name", "task_id", "task")),
                    reason=_safe_str(_event_attr(event, "error", "error_message", "message")),
                )

            @crewai_event_bus.on(ToolUsageStartedEvent)
            def _on_tool_started(_source: object, event: object) -> None:
                _append_with_context("TOOL_STARTED", tool=_tool_name(event))

            @crewai_event_bus.on(ToolUsageFinishedEvent)
            def _on_tool_finished(_source: object, event: object) -> None:
                _append_with_context("TOOL_FINISHED", tool=_tool_name(event))

            @crewai_event_bus.on(ToolUsageErrorEvent)
            def _on_tool_failed(_source: object, event: object) -> None:
                _append_with_context(
                    "TOOL_FAILED",
                    tool=_tool_name(event),
                    reason=_safe_str(_event_attr(event, "error", "error_message", "message")),
                )

            @crewai_event_bus.on(FlowStartedEvent)
            def _on_flow_started(_source: object, event: object) -> None:
                _append_with_context(
                    "FLOW_STARTED",
                    flow=_safe_str(_event_attr(event, "flow_name", "flow_id", "flow")),
                )

            @crewai_event_bus.on(FlowFinishedEvent)
            def _on_flow_finished(_source: object, event: object) -> None:
                _append_with_context(
                    "FLOW_FINISHED",
                    flow=_safe_str(_event_attr(event, "flow_name", "flow_id", "flow")),
                )

            @crewai_event_bus.on(MethodExecutionStartedEvent)
            def _on_method_started(_source: object, event: object) -> None:
                _append_with_context(
                    "FLOW_STEP_STARTED",
                    flow=_safe_str(_event_attr(event, "flow_name", "flow")),
                    step=_safe_str(_event_attr(event, "method_name", "method")),
                )

            @crewai_event_bus.on(MethodExecutionFinishedEvent)
            def _on_method_finished(_source: object, event: object) -> None:
                _append_with_context(
                    "FLOW_STEP_FINISHED",
                    flow=_safe_str(_event_attr(event, "flow_name", "flow")),
                    step=_safe_str(_event_attr(event, "method_name", "method")),
                )

            @crewai_event_bus.on(MethodExecutionFailedEvent)
            def _on_method_failed(_source: object, event: object) -> None:
                _append_with_context(
                    "FLOW_STEP_FAILED",
                    flow=_safe_str(_event_attr(event, "flow_name", "flow")),
                    step=_safe_str(_event_attr(event, "method_name", "method")),
                    reason=_safe_str(_event_attr(event, "error", "error_message", "message")),
                )

    try:
        RPSCrewAIEventListener()
    except Exception as exc:  # pragma: no cover - depends on CrewAI runtime details
        _LISTENER_INIT_FAILED = True
        logger.warning("Failed to initialize CrewAI event listener: %s", exc)
        return

    _LISTENER_READY = True


@contextmanager
def runtime_event_scope(
    *,
    root: Path,
    athlete_id: str,
    run_id: str,
    component: str | None = None,
) -> Any:
    """Bind the current run context for CrewAI listener events."""

    ensure_crewai_event_listener()
    token: Token[CrewAIRunContext | None] = _RUN_CONTEXT.set(
        CrewAIRunContext(root=root, athlete_id=athlete_id, run_id=run_id, component=component)
    )
    try:
        yield
    finally:
        _RUN_CONTEXT.reset(token)
