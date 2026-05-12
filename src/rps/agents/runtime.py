"""Unified agent runtime gateway for legacy and CrewAI execution backends."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from rps.crewai_runtime.compat import CrewAIRuntimeStatus, crewai_runtime_status

from .multi_output_runner import AgentRuntime as LegacyAgentRuntime
from .multi_output_runner import run_agent_multi_output as run_agent_multi_output_legacy

logger = logging.getLogger(__name__)

AgentRuntime = LegacyAgentRuntime
JsonMap = dict[str, Any]
_SUPPORTED_BACKENDS = {"auto", "legacy", "crewai"}


@dataclass(frozen=True)
class AgentRuntimeSelection:
    """Describe the currently selected agent execution backend."""

    requested_backend: str
    effective_backend: str
    can_execute: bool
    is_fallback: bool
    reason: str
    crewai_status: CrewAIRuntimeStatus


def _crewai_execution_implemented() -> bool:
    """Return whether the repo contains a production CrewAI execution bridge."""

    return False


def configured_agent_backend() -> str:
    """Return the configured agent backend mode.

    Supported values:
    - ``auto``: prefer CrewAI only when fully executable; otherwise use legacy.
    - ``legacy``: always use the current LiteLLM/multi-output runner backend.
    - ``crewai``: require CrewAI and fail fast when it cannot execute.
    """

    raw = os.getenv("RPS_AGENT_RUNTIME", "auto").strip().lower() or "auto"
    if raw in _SUPPORTED_BACKENDS:
        return raw
    logger.warning("Unknown RPS_AGENT_RUNTIME=%s; falling back to auto.", raw)
    return "auto"


def resolve_agent_runtime_selection(
    requested_backend: str | None = None,
) -> AgentRuntimeSelection:
    """Resolve the effective backend and fallback reason for agent execution."""

    requested = (requested_backend or configured_agent_backend()).strip().lower() or "auto"
    if requested not in _SUPPORTED_BACKENDS:
        requested = "auto"
    status = crewai_runtime_status()
    crewai_ready = status.ok and _crewai_execution_implemented()
    crewai_reason = (
        status.message
        if not status.ok
        else "CrewAI package is available, but the runtime execution bridge is not implemented yet."
    )

    if requested == "legacy":
        return AgentRuntimeSelection(
            requested_backend=requested,
            effective_backend="legacy",
            can_execute=True,
            is_fallback=False,
            reason="Legacy multi-output runner selected explicitly.",
            crewai_status=status,
        )

    if requested == "crewai":
        return AgentRuntimeSelection(
            requested_backend=requested,
            effective_backend="crewai",
            can_execute=crewai_ready,
            is_fallback=False,
            reason=(
                "CrewAI runtime selected explicitly."
                if crewai_ready
                else f"CrewAI runtime requested but unavailable: {crewai_reason}"
            ),
            crewai_status=status,
        )

    if crewai_ready:
        return AgentRuntimeSelection(
            requested_backend=requested,
            effective_backend="crewai",
            can_execute=True,
            is_fallback=False,
            reason="CrewAI runtime selected automatically.",
            crewai_status=status,
        )

    return AgentRuntimeSelection(
        requested_backend=requested,
        effective_backend="legacy",
        can_execute=True,
        is_fallback=True,
        reason=f"Auto mode falling back to legacy backend: {crewai_reason}",
        crewai_status=status,
    )


def _run_agent_multi_output_crewai(*args: Any, **kwargs: Any) -> JsonMap:
    """Execute a run through the CrewAI backend.

    The repo is not yet on a CrewAI-supported Python baseline and does not ship
    a production execution bridge, so this path is intentionally blocked.
    """

    raise RuntimeError(
        "CrewAI backend execution is not implemented yet. "
        "Use RPS_AGENT_RUNTIME=legacy or keep the default auto mode."
    )


def run_agent_multi_output(*args: Any, **kwargs: Any) -> JsonMap:
    """Run an agent task through the selected runtime backend."""

    selection = resolve_agent_runtime_selection()
    if selection.effective_backend == "legacy":
        return run_agent_multi_output_legacy(*args, **kwargs)
    if not selection.can_execute:
        raise RuntimeError(selection.reason)
    return _run_agent_multi_output_crewai(*args, **kwargs)

