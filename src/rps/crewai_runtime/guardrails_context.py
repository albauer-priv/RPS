"""Runtime-context threading for CrewAI guardrail evaluation."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

JsonMap = dict[str, Any]
GuardrailResult = tuple[bool, Any]
GuardrailFn = Callable[[Any], GuardrailResult]
_GUARDRAIL_CONTEXT: ContextVar[JsonMap] = ContextVar("rps_guardrail_context", default={})


@contextmanager
def guardrail_runtime_context(**context: Any):
    """Bind runtime-only guardrail context for the current CrewAI task run."""

    current = dict(_GUARDRAIL_CONTEXT.get({}))
    current.update({key: value for key, value in context.items() if value is not None})
    token = _GUARDRAIL_CONTEXT.set(current)
    try:
        yield
    finally:
        _GUARDRAIL_CONTEXT.reset(token)


def current_guardrail_runtime_context() -> JsonMap:
    """Return the currently bound runtime guardrail context."""

    return dict(_GUARDRAIL_CONTEXT.get({}))
