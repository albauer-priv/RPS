"""CrewAI-only agent runtime gateway and shared runtime settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rps.crewai_runtime.compat import CrewAIRuntimeStatus, crewai_runtime_status
from rps.prompts.loader import PromptLoader

JsonMap = dict[str, Any]


@dataclass(frozen=True)
class AgentRuntime:
    """Shared runtime dependencies for CrewAI-backed agent runs."""

    model: str
    temperature: float | None
    reasoning_effort: str | None
    reasoning_summary: str | None
    max_completion_tokens: int | None
    prompt_loader: PromptLoader
    schema_dir: Path
    workspace_root: Path


@dataclass(frozen=True)
class AgentRuntimeSelection:
    """Describe the currently selected agent execution backend."""

    requested_backend: str
    effective_backend: str
    can_execute: bool
    is_fallback: bool
    reason: str
    crewai_status: CrewAIRuntimeStatus


def resolve_agent_runtime_selection(
    requested_backend: str | None = None,
) -> AgentRuntimeSelection:
    """Resolve the fixed CrewAI backend for agent execution."""

    requested = (requested_backend or "crewai").strip().lower() or "crewai"
    if requested != "crewai":
        requested = "crewai"
    status = crewai_runtime_status()
    can_execute = status.ok
    reason = (
        "CrewAI runtime selected explicitly."
        if can_execute
        else f"CrewAI runtime unavailable: {status.message}"
    )
    return AgentRuntimeSelection(
        requested_backend=requested,
        effective_backend="crewai",
        can_execute=can_execute,
        is_fallback=False,
        reason=reason,
        crewai_status=status,
    )


def run_agent_multi_output(*args: Any, **kwargs: Any) -> JsonMap:
    """Run an agent task through the CrewAI backend."""

    selection = resolve_agent_runtime_selection()
    if not selection.can_execute:
        raise RuntimeError(selection.reason)
    from rps.agents.crewai_backend import run_agent_multi_output_crewai

    return run_agent_multi_output_crewai(*args, **kwargs)


def run_agent_multi_output_preview(*args: Any, **kwargs: Any) -> JsonMap:
    """Run an agent task through the CrewAI backend without persisting outputs."""

    selection = resolve_agent_runtime_selection()
    if not selection.can_execute:
        raise RuntimeError(selection.reason)
    from rps.agents.crewai_backend import run_agent_multi_output_preview_crewai

    return run_agent_multi_output_preview_crewai(*args, **kwargs)
