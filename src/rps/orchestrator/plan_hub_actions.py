"""Plan Hub orchestration helpers (UI delegates here)."""

from __future__ import annotations

import logging
from typing import Callable, Any

from rps.agents.multi_output_runner import AgentRuntime
from rps.orchestrator.plan_week import plan_week
from rps.orchestrator.season_flow import (
    create_season_plan,
    create_season_scenarios,
)
from rps.ui.intervals_post import post_to_intervals_commit
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.iso_helpers import IsoWeek
from rps.orchestrator.plan_week import create_performance_report

logger = logging.getLogger(__name__)


def execute_season_scenarios(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    override_text: str | None = None,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    force_file_search: bool = True,
    max_num_results: int = 20,
) -> dict[str, Any]:
    """Run Season Scenarios agent."""
    return create_season_scenarios(
        runtime_for,
        athlete_id=athlete_id,
        year=year,
        week=week,
        run_id=run_id,
        override_text=override_text,
        model_resolver=model_resolver,
        temperature_resolver=temperature_resolver,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
    )


def execute_scenario_selection(*_args, **_kwargs) -> dict[str, Any]:
    """Scenario selection is manual (performed on Season page)."""
    return {"ok": False, "error": "Scenario selection is manual. Use the Season page."}


def execute_season_plan(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    override_text: str | None = None,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    force_file_search: bool = True,
    max_num_results: int = 20,
) -> dict[str, Any]:
    """Run Season Plan agent."""
    return create_season_plan(
        runtime_for,
        athlete_id=athlete_id,
        year=year,
        week=week,
        run_id=run_id,
        selected=None,
        override_text=override_text,
        model_resolver=model_resolver,
        temperature_resolver=temperature_resolver,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
    )


def execute_plan_week(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    force_steps: list[str] | None = None,
    override_text: str | None = None,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    reasoning_effort_resolver: Callable[[str], str | None] | None = None,
    reasoning_summary_resolver: Callable[[str], str | None] | None = None,
    force_file_search: bool = True,
    max_num_results: int = 20,
) -> dict[str, Any]:
    """Run the plan-week orchestrator (phase + week + export)."""
    result = plan_week(
        runtime_for("season_planner"),
        athlete_id=athlete_id,
        year=year,
        week=week,
        run_id=run_id,
        force_steps=force_steps,
        override_text=override_text,
        model_resolver=model_resolver,
        temperature_resolver=temperature_resolver,
        reasoning_effort_resolver=reasoning_effort_resolver,
        reasoning_summary_resolver=reasoning_summary_resolver,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
    )
    return {"ok": result.ok}


def execute_performance_report(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
) -> dict[str, Any]:
    """Run the performance report generation."""
    result = create_performance_report(
        runtime_for,
        athlete_id=athlete_id,
        report_week=IsoWeek(year=year, week=week),
        run_id_prefix=run_id,
        reasoning_stream_handler=lambda _delta: None,
    )
    return result if isinstance(result, dict) else {"ok": False, "error": "Unknown report error"}


def execute_post_intervals(
    *,
    store: LocalArtifactStore,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    allow_delete: bool,
) -> dict[str, Any]:
    """Create idempotent posting receipts for Intervals workouts."""
    result = post_to_intervals_commit(
        store,
        athlete_id,
        year=year,
        week=week,
        run_id=run_id,
        allow_delete=allow_delete,
    )
    return {
        "ok": result.ok,
        "posted": result.posted,
        "skipped": result.skipped,
        "deleted": result.deleted,
        "error": result.error,
    }
