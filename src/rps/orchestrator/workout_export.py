"""Helpers for generating Intervals workouts exports."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from rps.agents.multi_output_runner import AgentRuntime, run_agent_multi_output
from rps.agents.registry import AGENTS
from rps.agents.tasks import AgentTask
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

logger = logging.getLogger(__name__)


def _mtime(path: Path | None) -> float | None:
    if not path or not path.exists():
        return None
    return path.stat().st_mtime


def create_intervals_workouts_export(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    store: LocalArtifactStore,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    injected_block: str,
    plan_mtime: float | None,
    needs_week_plan: bool,
    force_export: bool = False,
    override_text: str | None = None,
    force_file_search: bool = True,
    max_num_results: int = 20,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    log_fn: Callable[[str, int], None] | None = None,
) -> dict:
    """Create Intervals workouts export when missing or stale.

    Purpose:
        Ensure Intervals export is generated when week plan changes.
    Inputs:
        runtime_for: runtime factory for agent execution.
        store: workspace artifact store.
        athlete_id: athlete identifier.
        year/week: ISO week to export.
        run_id: run identifier prefix.
        injected_block: mandatory knowledge injection block (already built).
        plan_mtime: week plan modified time.
        needs_week_plan: whether week plan was regenerated this run.
        force_export: whether this export was explicitly requested by the caller.
        override_text: optional override text appended to the export prompt.
        force_file_search/max_num_results: agent settings.
        model_resolver/temperature_resolver: optional model overrides.
        log_fn: optional logger callback (message, level).
    Outputs:
        dict with keys: ran, ok, produced, result, message.
    Side effects:
        Writes Intervals workouts export JSON under the workspace.
    """

    def _log(message: str, level: int = logging.INFO) -> None:
        if log_fn:
            log_fn(message, level)
        else:
            logger.log(level, message)

    version_key = f"{year:04d}-{week:02d}"
    if not store.exists(athlete_id, ArtifactType.WEEK_PLAN, version_key):
        message = f"Workout-Builder skipped: WEEK_PLAN {version_key} not found."
        _log(message)
        return {"ran": False, "ok": True, "produced": False, "result": None, "message": message}

    intervals_key = store.resolve_week_version_key(athlete_id, ArtifactType.INTERVALS_WORKOUTS, version_key)
    intervals_path = (
        store.versioned_path(athlete_id, ArtifactType.INTERVALS_WORKOUTS, intervals_key)
        if intervals_key
        else None
    )
    intervals_mtime = _mtime(intervals_path)
    needs_intervals = intervals_path is None
    if plan_mtime and intervals_mtime and plan_mtime > intervals_mtime:
        needs_intervals = True
    if needs_week_plan:
        needs_intervals = True
    if force_export:
        needs_intervals = True

    if not needs_intervals:
        message = f"Found INTERVALS_WORKOUTS for ISO week {year:04d}-{week:02d}."
        _log(message)
        return {"ran": False, "ok": True, "produced": False, "result": None, "message": message}

    message = f"Running Workout-Builder for ISO week {year:04d}-{week:02d}."
    _log(message)
    spec = AGENTS["workout_builder"]
    override_line = f"Override: {override_text.strip()}. " if override_text else ""
    out = run_agent_multi_output(
        runtime_for(spec.name),
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=athlete_id,
        tasks=[AgentTask.CREATE_INTERVALS_WORKOUTS_EXPORT],
        user_input=(
            f"Convert week_plan into Intervals.icu workouts JSON for ISO week {year:04d}-{week:02d}. "
            "Read week_plan from workspace. "
            f"{override_line}"
            f"{injected_block}"
        ),
        run_id=f"{run_id}_builder",
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
    )
    return {
        "ran": True,
        "ok": out.get("ok", False),
        "produced": out.get("produced", False),
        "result": out,
        "message": message,
    }
