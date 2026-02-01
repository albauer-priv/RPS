"""Season-level orchestration helpers for scenario + plan actions."""

from __future__ import annotations

import logging
from typing import Callable

from rps.agents.multi_output_runner import AgentRuntime, run_agent_multi_output
from rps.agents.registry import AGENTS
from rps.agents.tasks import AgentTask
from rps.orchestrator.plan_week import _build_injection_block

logger = logging.getLogger(__name__)


def create_season_scenarios(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    force_file_search: bool = True,
    max_num_results: int = 20,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
) -> dict:
    """Create season scenarios for the target ISO week."""
    spec = AGENTS["season_scenario"]
    injected_block = _build_injection_block("season_scenario", mode="scenario")
    user_input = (
        "Mode A. Generate the pre-decision scenarios. "
        f"Target ISO week: {year}-{week:02d}. "
        "Use workspace_get_input for Season Brief and Events. "
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_SCENARIOS."
    )
    logger.info("Creating season scenarios athlete=%s iso_week=%04d-W%02d", athlete_id, year, week)
    return run_agent_multi_output(
        runtime_for(spec.name),
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=athlete_id,
        tasks=[AgentTask.CREATE_SEASON_SCENARIOS],
        user_input=user_input,
        run_id=run_id,
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
    )


def select_season_scenario(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    selected: str,
    rationale: str | None,
    force_file_search: bool = True,
    max_num_results: int = 20,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
) -> dict:
    """Select a season scenario for the target ISO week."""
    spec = AGENTS["season_scenario"]
    injected_block = _build_injection_block("season_scenario", mode="scenario")
    rationale_line = f"Rationale: {rationale.strip()}. " if rationale else ""
    user_input = (
        f"Select Scenario {selected.upper()} for ISO week {year}-{week:02d}. "
        "Use the latest SEASON_SCENARIOS as context. "
        f"{rationale_line}"
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_SCENARIO_SELECTION."
    )
    logger.info(
        "Selecting season scenario athlete=%s iso_week=%04d-W%02d scenario=%s",
        athlete_id,
        year,
        week,
        selected,
    )
    return run_agent_multi_output(
        runtime_for(spec.name),
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=athlete_id,
        tasks=[AgentTask.CREATE_SEASON_SCENARIO_SELECTION],
        user_input=user_input,
        run_id=run_id,
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
    )


def create_season_plan(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    selected: str | None,
    force_file_search: bool = True,
    max_num_results: int = 20,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
) -> dict:
    """Create the season plan for the selected scenario."""
    spec = AGENTS["season_planner"]
    injected_block = _build_injection_block("season_planner", mode="season_plan")
    scenario_line = f"Scenario {selected.upper()}. " if selected else ""
    user_input = (
        f"{scenario_line}Mode A. Create the SEASON_PLAN. "
        f"Target ISO week: {year}-{week:02d}. "
        "Use the latest SEASON_SCENARIO_SELECTION and SEASON_SCENARIOS as context. "
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_PLAN."
    )
    logger.info(
        "Creating season plan athlete=%s iso_week=%04d-W%02d scenario=%s",
        athlete_id,
        year,
        week,
        selected or "latest",
    )
    return run_agent_multi_output(
        runtime_for(spec.name),
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=athlete_id,
        tasks=[AgentTask.CREATE_SEASON_PLAN],
        user_input=user_input,
        run_id=run_id,
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
    )
