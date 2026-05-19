"""CrewAI event-listener adapter for the local run-store telemetry."""

from __future__ import annotations

import ast
import logging
import re
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
_RUNTIME_LABELS: dict[int, dict[str, str]] = {}


def register_runtime_label(value: object | None, *, kind: str, label: str | None) -> None:
    """Register a stable RPS label for a CrewAI runtime object."""

    if value is None or not label:
        return
    rendered = _compact_text(str(label))
    if not rendered:
        return
    labels = _RUNTIME_LABELS.setdefault(id(value), {})
    labels[kind] = rendered


def _registered_label(value: object | None, *kinds: str) -> str | None:
    """Return a previously registered label for an object id."""

    if value is None:
        return None
    labels = _RUNTIME_LABELS.get(id(value))
    if not labels:
        return None
    for kind in kinds:
        label = labels.get(kind)
        if label:
            return label
    return None


def _append_with_context(event_type: str, **payload: object) -> None:
    """Append an event when a run context is currently active."""

    ctx = _RUN_CONTEXT.get()
    if ctx is None:
        return
    event_payload = {"type": event_type, **payload}
    if ctx.component and "component" not in event_payload:
        event_payload["component"] = ctx.component
    _log_runtime_event(ctx, event_type, event_payload)
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
    _log_runtime_event(
        CrewAIRunContext(root=root, athlete_id=athlete_id, run_id=run_id, component=None),
        event_type,
        payload,
    )
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


def _log_runtime_event(ctx: CrewAIRunContext, event_type: str, payload: dict[str, object]) -> None:
    """Write compact CrewAI runtime progress into the normal application log."""

    keys = (
        "flow",
        "crew",
        "task",
        "agent",
        "tool",
        "step",
        "status",
        "output_format",
        "component",
        "reason",
        "error_type",
        "error_code",
        "status_code",
        "model",
        "provider",
    )
    fields: list[str] = [
        f"type={event_type}",
        f"run_id={ctx.run_id}",
        f"athlete={ctx.athlete_id}",
    ]
    for key in keys:
        value = payload.get(key)
        text = _safe_str(value, default="")
        if text:
            fields.append(f"{key}={_compact_text(text, max_len=140)}")
    level = logging.INFO
    if event_type in {
        "CREW_TASK_CALLBACK_COMPLETED",
        "CREW_TASK_COMPLETED",
        "TOOL_STARTED",
        "TOOL_FINISHED",
        "CREW_AGENT_STEP",
    }:
        level = logging.DEBUG
    if "FAILED" in event_type or "ERROR" in event_type:
        level = logging.WARNING
    logger.log(level, "CrewAI runtime %s", " ".join(fields))


def _output_format_label(value: object) -> str:
    """Return a compact structured-output label for a CrewAI task output."""

    if value is None:
        return "none"
    if getattr(value, "pydantic", None) is not None:
        return "pydantic"
    if getattr(value, "json_dict", None) is not None:
        return "json"
    if getattr(value, "raw", None) is not None:
        return "raw"
    return type(value).__name__


def _callback_task_name(task_output: object) -> str:
    """Resolve a compact task label from a CrewAI task callback payload."""

    for candidate in (
        _object_attr(task_output, "name", "task_name", "task_id"),
        _object_attr(_object_attr(task_output, "task"), "name", "key"),
    ):
        text = _safe_str(candidate, default="")
        if text:
            return _compact_text(text)
    return type(task_output).__name__ if task_output is not None else "TaskOutput"


def _callback_agent_name(task_output: object) -> str:
    """Resolve a compact agent label from a CrewAI task callback payload."""

    agent = _object_attr(task_output, "agent")
    text = _safe_str(_object_attr(agent, "role", "name", "key"), default="")
    if text:
        return _compact_text(text)
    text = _safe_str(agent, default="")
    return _compact_text(text) if text else "unknown"


def _agent_label(event: object, source: object) -> str:
    """Resolve a compact agent label from task events."""

    for candidate in (
        _event_attr(event, "agent_name", "agent_role", "agent"),
        _object_attr(_event_attr(event, "task"), "agent"),
        _object_attr(source, "agent"),
    ):
        if candidate is None:
            continue
        registered = _registered_label(candidate, "agent")
        if registered:
            return registered
        text = _safe_str(_object_attr(candidate, "role", "name", "key"), default="")
        if not text:
            text = _safe_str(candidate, default="")
        if text:
            return _compact_text(text)
    return "unknown"


def build_task_callback(
    *,
    root: Path | None,
    athlete_id: str | None,
    run_id: str | None,
    crew_name: str,
    task_name: str | None = None,
    event_type: str = "CREW_TASK_COMPLETED",
) -> Any:
    """Build a safe CrewAI task callback that records compact runtime metadata."""

    def _callback(task_output: object) -> None:
        emit_runtime_event(
            root=root,
            athlete_id=athlete_id,
            run_id=run_id,
            event_type=event_type,
            crew=crew_name,
            task=task_name or _callback_task_name(task_output),
            agent=_callback_agent_name(task_output),
            output_format=_output_format_label(task_output),
        )

    return _callback


def build_step_callback(
    *,
    root: Path | None,
    athlete_id: str | None,
    run_id: str | None,
    crew_name: str,
    enabled: bool = False,
) -> Any | None:
    """Build an optional debug step callback without logging prompt/output bodies."""

    if not enabled:
        return None

    def _callback(step: object) -> None:
        emit_runtime_event(
            root=root,
            athlete_id=athlete_id,
            run_id=run_id,
            event_type="CREW_AGENT_STEP",
            crew=crew_name,
            step=_compact_text(type(step).__name__),
            tool=_safe_str(_object_attr(step, "tool_name", "tool"), default=""),
            status=_safe_str(_object_attr(step, "status"), default=""),
        )

    return _callback


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
    if not isinstance(value, (str, int, float, bool)):
        return default
    text = str(value).strip()
    return text or default


def _compact_text(text: str, *, max_len: int = 96) -> str:
    """Collapse whitespace and cap telemetry labels to a compact single line."""

    compact = " ".join(text.split())
    if len(compact) <= max_len:
        return compact
    return f"{compact[: max_len - 3].rstrip()}..."


def _extract_error_mapping(text: str) -> dict[str, object]:
    """Best-effort parse a provider error mapping embedded in an exception string."""

    if "{" not in text or "}" not in text:
        return {}
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return {}
    raw = text[start : end + 1]
    try:
        parsed = ast.literal_eval(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _exception_chain(exc: BaseException) -> list[BaseException]:
    """Return the exception chain from outermost to deepest cause/context."""

    chain: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(current)
        next_exc = current.__cause__ or current.__context__
        current = next_exc if isinstance(next_exc, BaseException) else None
    return chain


def summarize_exception(exc: BaseException) -> dict[str, object]:
    """Return a compact structured failure summary for telemetry and run-store details."""

    chain = _exception_chain(exc)
    root = chain[-1] if chain else exc
    root_message = str(root).strip() or type(root).__name__
    top_message = str(exc).strip() or type(exc).__name__

    payload: dict[str, object] = {
        "reason": _compact_text(root_message, max_len=220),
        "exception_class": type(root).__name__,
    }
    if top_message != root_message:
        payload["top_level_reason"] = _compact_text(top_message, max_len=220)

    for source in (root, exc):
        for attr_name, key in (
            ("status_code", "status_code"),
            ("code", "error_code"),
            ("type", "error_type"),
            ("model", "model"),
            ("provider", "provider"),
        ):
            value = getattr(source, attr_name, None)
            text = _safe_str(value, default="")
            if text and key not in payload:
                payload[key] = text

        body = getattr(source, "body", None)
        body_map = body if isinstance(body, dict) else {}
        error_map = body_map.get("error") if isinstance(body_map.get("error"), dict) else {}
        for mapping in (body_map, error_map):
            for source_key, key in (
                ("message", "reason"),
                ("type", "error_type"),
                ("code", "error_code"),
                ("param", "error_param"),
            ):
                value = mapping.get(source_key)
                text = _safe_str(value, default="")
                if text:
                    payload[key] = _compact_text(text, max_len=220) if key == "reason" else text

    parsed = _extract_error_mapping(root_message)
    error_map = parsed.get("error") if isinstance(parsed.get("error"), dict) else {}
    if error_map:
        for source_key, key in (
            ("message", "reason"),
            ("type", "error_type"),
            ("code", "error_code"),
        ):
            value = error_map.get(source_key)
            text = _safe_str(value, default="")
            if text:
                payload[key] = _compact_text(text, max_len=220) if key == "reason" else text

    status_match = re.search(r"Error code:\s*(\d+)", top_message)
    if status_match and "status_code" not in payload:
        payload["status_code"] = status_match.group(1)

    provider_hint = "openai" if "openai" in top_message.lower() or "chat/completions" in top_message.lower() else ""
    if provider_hint and "provider" not in payload:
        payload["provider"] = provider_hint

    if (
        payload.get("error_code") in {"insufficient_quota", "rate_limit_exceeded"}
        or payload.get("error_type") in {"insufficient_quota", "tokens"}
        or payload.get("provider") == "openai"
    ):
        payload["event_type"] = "LLM_REQUEST_FAILED"
    else:
        payload["event_type"] = "CREW_EXECUTION_FAILED"

    return payload


def emit_runtime_exception_event(
    *,
    root: Path | None,
    athlete_id: str | None,
    run_id: str | None,
    exc: BaseException,
    event_type: str | None = None,
    **payload: object,
) -> None:
    """Emit one structured runtime failure event derived from an exception."""

    summary = summarize_exception(exc)
    resolved_event_type = event_type or str(summary.pop("event_type", "CREW_EXECUTION_FAILED"))
    emit_runtime_event(
        root=root,
        athlete_id=athlete_id,
        run_id=run_id,
        event_type=resolved_event_type,
        **summary,
        **payload,
    )


def _append_exception_with_context(
    event_type: str,
    *,
    exc: object,
    **payload: object,
) -> None:
    """Append one telemetry event enriched from an exception-like object."""

    if isinstance(exc, BaseException):
        summary = summarize_exception(exc)
        resolved_type = str(summary.pop("event_type", event_type))
        _append_with_context(resolved_type if event_type == "LLM_REQUEST_FAILED" else event_type, **summary, **payload)
        return
    _append_with_context(event_type, reason=_safe_str(exc), **payload)


def _looks_like_prompt_text(text: str) -> bool:
    """Return true when a CrewAI label is actually injected prompt text."""

    compact = " ".join(text.split()).lower()
    prompt_markers = (
        "system and agent instructions:",
        "system instructions:",
        "based on these tasks summary:",
        "# system prompt",
        "shared system instructions",
    )
    return any(marker in compact for marker in prompt_markers)


def _object_attr(value: object, *names: str) -> object | None:
    """Return the first matching attribute on an object without stringifying it."""

    if value is None:
        return None
    for name in names:
        if hasattr(value, name):
            return getattr(value, name)
    return None


def _object_identifier(value: object, *, generic_names: set[str] | None = None) -> str | None:
    """Extract a compact, stable identifier from a runtime object."""

    registered = _registered_label(value, "task", "crew", "agent", "tool")
    if registered:
        return registered
    generic = {name.lower() for name in (generic_names or set())}
    for candidate in (
        _object_attr(value, "name", "key", "role", "tool_name", "method_name", "flow_name"),
        _object_attr(value, "id", "task_id", "crew_id", "flow_id"),
    ):
        text = _safe_str(candidate, default="")
        if text and text.lower() not in generic:
            return _compact_text(text)
    return None


def _task_label(event: object, source: object) -> str:
    """Resolve a compact task label without leaking full prompt text."""

    direct = _safe_str(_event_attr(event, "task_name", "task_id"), default="")
    if direct and direct.lower() != "task" and not _looks_like_prompt_text(direct):
        return _compact_text(direct)
    task_obj = _event_attr(event, "task") or source
    registered = _registered_label(task_obj, "task")
    if registered:
        return registered
    named = _safe_str(_object_attr(task_obj, "name", "key", "role"), default="")
    if named and not _looks_like_prompt_text(named):
        return _compact_text(named)
    task_id = _safe_str(_object_attr(task_obj, "id", "task_id"), default="")
    if task_id:
        return f"{type(task_obj).__name__}#{task_id[:8]}"
    return type(task_obj).__name__ if task_obj is not None else "Task"


def _crew_label(event: object, source: object) -> str:
    """Resolve a meaningful crew label and avoid generic `crew` payloads."""

    direct = _safe_str(_event_attr(event, "crew_name", "crew_id"), default="")
    if direct and direct.lower() != "crew":
        return _compact_text(direct)
    for candidate in (_event_attr(event, "crew"), source):
        named = _object_identifier(candidate, generic_names={"crew"})
        if named:
            return named
    ctx = _RUN_CONTEXT.get()
    if ctx and ctx.component:
        return ctx.component
    if source is not None:
        return type(source).__name__
    return "crew"


def _tool_name(event: object, source: object) -> str:
    """Resolve a tool name from the CrewAI event payload."""

    direct = _event_attr(event, "tool_name", "tool")
    if isinstance(direct, str):
        return _compact_text(direct)
    if hasattr(direct, "__name__"):
        return _safe_str(getattr(direct, "__name__"))
    for candidate in (direct, source):
        named = _object_identifier(candidate, generic_names={"tool"})
        if named:
            return named
    return "Tool"


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
            def _on_crew_started(source: object, event: object) -> None:
                _append_with_context(
                    "CREW_STARTED",
                    crew=_crew_label(event, source),
                )

            @crewai_event_bus.on(CrewKickoffCompletedEvent)
            def _on_crew_finished(source: object, event: object) -> None:
                _append_with_context(
                    "CREW_FINISHED",
                    crew=_crew_label(event, source),
                )

            @crewai_event_bus.on(CrewKickoffFailedEvent)
            def _on_crew_failed(source: object, event: object) -> None:
                _append_exception_with_context(
                    "CREW_FAILED",
                    exc=_event_attr(event, "error", "error_message", "message"),
                    crew=_crew_label(event, source),
                )

            @crewai_event_bus.on(TaskStartedEvent)
            def _on_task_started(source: object, event: object) -> None:
                _append_with_context(
                    "CREW_TASK_STARTED",
                    task=_task_label(event, source),
                    agent=_agent_label(event, source),
                )

            @crewai_event_bus.on(TaskCompletedEvent)
            def _on_task_completed(source: object, event: object) -> None:
                _append_with_context(
                    "CREW_TASK_FINISHED",
                    task=_task_label(event, source),
                    agent=_agent_label(event, source),
                )

            @crewai_event_bus.on(TaskFailedEvent)
            def _on_task_failed(source: object, event: object) -> None:
                _append_exception_with_context(
                    "CREW_TASK_FAILED",
                    exc=_event_attr(event, "error", "error_message", "message"),
                    task=_task_label(event, source),
                    agent=_agent_label(event, source),
                )

            @crewai_event_bus.on(ToolUsageStartedEvent)
            def _on_tool_started(source: object, event: object) -> None:
                _append_with_context("TOOL_STARTED", tool=_tool_name(event, source))

            @crewai_event_bus.on(ToolUsageFinishedEvent)
            def _on_tool_finished(source: object, event: object) -> None:
                _append_with_context("TOOL_FINISHED", tool=_tool_name(event, source))

            @crewai_event_bus.on(ToolUsageErrorEvent)
            def _on_tool_failed(source: object, event: object) -> None:
                _append_exception_with_context(
                    "TOOL_FAILED",
                    exc=_event_attr(event, "error", "error_message", "message"),
                    tool=_tool_name(event, source),
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
                _append_exception_with_context(
                    "FLOW_STEP_FAILED",
                    exc=_event_attr(event, "error", "error_message", "message"),
                    flow=_safe_str(_event_attr(event, "flow_name", "flow")),
                    step=_safe_str(_event_attr(event, "method_name", "method")),
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
