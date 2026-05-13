"""Helpers for revising week plans via the Week Planner."""

from __future__ import annotations

import logging
from collections.abc import Callable

from rps.agents.knowledge_injection import build_injection_block
from rps.agents.registry import AGENTS
from rps.agents.runtime import AgentRuntime
from rps.agents.tasks import AgentTask
from rps.crewai_runtime.flows import run_week_flow
from rps.orchestrator.plan_week import _mode_for_task

logger = logging.getLogger(__name__)

OrchestratorResult = dict[str, object]


def _build_revision_user_input(*, year: int, week: int, message: str) -> str:
    """Build the common user-input payload for week revision and preview runs."""

    injected_block = build_injection_block("week_planner", mode=_mode_for_task(AgentTask.CREATE_WEEK_PLAN))
    return (
        f"Target ISO week: year={year}, week={week} (ISO {year:04d}-{week:02d}). "
        "Revise the week plan based on the following coach message. "
        f"Message: {message}\n"
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for WEEK_PLAN."
    )


def revise_week_plan(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    message: str,
    run_id: str,
    force_file_search: bool = True,
    max_num_results: int = 20,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
) -> OrchestratorResult:
    """Revise a week plan based on a coach message.

    Purpose:
        Allow manual adjustments to week plans (e.g., swapping days or intensity tweaks).
    Inputs:
        runtime_for: runtime factory for agent execution.
        athlete_id: athlete identifier.
        year/week: ISO week to revise.
        message: coach message describing changes.
        run_id: run identifier.
    Outputs:
        Agent result dict from the Week Planner.
    Side effects:
        Writes a revised WEEK_PLAN artifact to the workspace.
    """
    spec = AGENTS["week_planner"]
    user_input = _build_revision_user_input(year=year, week=week, message=message)
    logger.info("Revising week plan athlete=%s iso_week=%04d-W%02d", athlete_id, year, week)
    return run_week_flow(
        runtime_for=runtime_for,
        agent_name=spec.name,
        athlete_id=athlete_id,
        tasks=[AgentTask.CREATE_WEEK_PLAN],
        user_input=user_input,
        run_id=run_id,
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
        workspace_root=runtime_for(spec.name).workspace_root,
    )


def preview_week_plan_revision(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    message: str,
    run_id: str,
    force_file_search: bool = True,
    max_num_results: int = 20,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
) -> OrchestratorResult:
    """Run the Week Planner in preview-only mode and return the candidate WEEK_PLAN."""

    spec = AGENTS["week_planner"]
    user_input = _build_revision_user_input(year=year, week=week, message=message)
    logger.info("Previewing week plan revision athlete=%s iso_week=%04d-W%02d", athlete_id, year, week)
    return run_week_flow(
        runtime_for=runtime_for,
        agent_name=spec.name,
        athlete_id=athlete_id,
        tasks=[AgentTask.CREATE_WEEK_PLAN],
        user_input=user_input,
        run_id=run_id,
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
        workspace_root=runtime_for(spec.name).workspace_root,
        preview_only=True,
    )
