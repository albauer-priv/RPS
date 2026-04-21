"""Helpers for generating Intervals workouts exports."""

from __future__ import annotations

import logging
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path

from rps.agents.multi_output_runner import AgentRuntime
from rps.workouts.exporter import build_intervals_workouts_export
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.schema_registry import SchemaRegistry, validate_or_raise
from rps.workspace.types import ArtifactType
from rps.workspace.validated_api import ValidatedWorkspace

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
    try:
        _ = runtime_for  # retained for interface compatibility with caller
        _ = injected_block
        _ = override_text
        _ = force_file_search
        _ = max_num_results
        _ = model_resolver
        _ = temperature_resolver

        week_plan = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, version_key)
        if not isinstance(week_plan, dict):
            raise ValueError("WEEK_PLAN payload is not an object")

        schema_dir = Path("specs/schemas")
        schemas = SchemaRegistry(schema_dir=schema_dir)
        week_plan_validator = schemas.validator_for("week_plan.schema.json")
        week_plan_for_validation = deepcopy(week_plan)
        meta = week_plan_for_validation.get("meta")
        if isinstance(meta, dict):
            meta.pop("version_key", None)
        validate_or_raise(week_plan_validator, week_plan_for_validation)

        export_payload = build_intervals_workouts_export(week_plan)

        workspace = ValidatedWorkspace.for_athlete(
            athlete_id,
            schema_dir=schema_dir,
            root=store.root,
        )
        path = workspace.put_validated(
            ArtifactType.INTERVALS_WORKOUTS,
            version_key,
            export_payload,
            payload_meta=None,
            producer_agent="workout_builder",
            run_id=f"{run_id}_builder",
            update_latest=True,
        )
        out = {
            "ok": True,
            "produced": [ArtifactType.INTERVALS_WORKOUTS.value],
            "artifact_type": ArtifactType.INTERVALS_WORKOUTS.value,
            "version_key": version_key,
            "path": path,
            "run_id": f"{run_id}_builder",
            "producer_agent": "workout_builder",
        }
    except Exception as exc:
        _log(f"Workout-Builder failed for ISO week {year:04d}-{week:02d}: {exc}", logging.ERROR)
        out = {
            "ok": False,
            "produced": [],
            "error": str(exc),
            "artifact_type": ArtifactType.INTERVALS_WORKOUTS.value,
            "run_id": f"{run_id}_builder",
            "producer_agent": "workout_builder",
        }
    return {
        "ran": True,
        "ok": out.get("ok", False),
        "produced": out.get("produced", False),
        "result": out,
        "message": message,
    }
