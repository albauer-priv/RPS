"""Orchestrator flow for weekly planning runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.agents.multi_output_runner import AgentRuntime, run_agent_multi_output
from app.agents.registry import AGENTS
from app.agents.task_router import AgentTaskRouter, RouterContext
from app.workspace.iso_helpers import IsoWeek
from app.workspace.api import Workspace


@dataclass
class PlanWeekResult:
    """Result summary for a plan-week orchestration."""
    ok: bool
    steps: list[dict]


def plan_week(
    runtime: AgentRuntime,
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    force_file_search: bool = True,
) -> PlanWeekResult:
    """Run the Macro -> Meso -> Micro -> Builder -> Analysis flow if needed."""
    workspace = Workspace.for_athlete(athlete_id, root=runtime.workspace_root)
    router = AgentTaskRouter(RouterContext(workspace=workspace))
    target = IsoWeek(year=year, week=week)

    steps: list[dict] = []

    macro_tasks = router.route_macro(target)
    if macro_tasks:
        spec = AGENTS["macro_planner"]
        out = run_agent_multi_output(
            runtime,
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=macro_tasks,
            user_input=(
                f"Create macro artefacts needed for planning. Target ISO week: {year}-{week:02d}."
            ),
            run_id=f"{run_id}_macro",
            model_override=model_resolver(spec.name) if model_resolver else None,
            temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
            force_file_search=force_file_search,
        )
        steps.append({"agent": "macro_planner", "tasks": [t.value for t in macro_tasks], "result": out})

    meso_tasks = router.route_meso(target)
    if meso_tasks:
        spec = AGENTS["meso_architect"]
        out = run_agent_multi_output(
            runtime,
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=meso_tasks,
            user_input=(
                f"Create meso artefacts for the current 4-week block covering ISO week {year}-{week:02d}. "
                f"Read macro_overview and use workspace_get_latest to pull required inputs."
            ),
            run_id=f"{run_id}_meso",
            model_override=model_resolver(spec.name) if model_resolver else None,
            temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
            force_file_search=force_file_search,
        )
        steps.append({"agent": "meso_architect", "tasks": [t.value for t in meso_tasks], "result": out})

    micro_tasks = router.route_micro(target)
    if micro_tasks:
        spec = AGENTS["micro_planner"]
        out = run_agent_multi_output(
            runtime,
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=micro_tasks,
            user_input=(
                f"Create workouts_plan for ISO week {year}-{week:02d}. "
                f"Read block_governance and block_execution_arch from workspace."
            ),
            run_id=f"{run_id}_micro",
            model_override=model_resolver(spec.name) if model_resolver else None,
            temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
            force_file_search=force_file_search,
        )
        steps.append({"agent": "micro_planner", "tasks": [t.value for t in micro_tasks], "result": out})

    builder_tasks = router.route_builder(target)
    if builder_tasks:
        spec = AGENTS["workout_builder"]
        out = run_agent_multi_output(
            runtime,
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=builder_tasks,
            user_input=(
                f"Convert workouts_plan into Intervals.icu workouts JSON for ISO week {year}-{week:02d}. "
                f"Read workouts_plan from workspace."
            ),
            run_id=f"{run_id}_builder",
            model_override=model_resolver(spec.name) if model_resolver else None,
            temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
            force_file_search=force_file_search,
        )
        steps.append({"agent": "workout_builder", "tasks": [t.value for t in builder_tasks], "result": out})

    analysis_tasks = router.route_analysis(target)
    if analysis_tasks:
        spec = AGENTS["performance_analysis"]
        out = run_agent_multi_output(
            runtime,
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=analysis_tasks,
            user_input=(
                f"Create des_analysis_report for ISO week {year}-{week:02d}. "
                f"Read activities_actual, activities_trend, KPI profile, macro overview, meso artefacts from workspace."
            ),
            run_id=f"{run_id}_analysis",
            model_override=model_resolver(spec.name) if model_resolver else None,
            temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
            force_file_search=force_file_search,
        )
        steps.append({"agent": "performance_analysis", "tasks": [t.value for t in analysis_tasks], "result": out})

    ok = all(step["result"].get("ok") for step in steps) if steps else True
    return PlanWeekResult(ok=ok, steps=steps)
