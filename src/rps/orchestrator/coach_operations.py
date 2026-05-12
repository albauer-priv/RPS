"""Active coach operations built on top of existing bounded planners and exports."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from rps.agents.multi_output_runner import AgentRuntime
from rps.crewai_runtime.models import (
    ArtifactWriteModel,
    CoachOperationApplyResultModel,
    CoachOperationPreviewModel,
)
from rps.orchestrator.advisory_actions import run_feed_forward_chain
from rps.orchestrator.plan_week import create_performance_report
from rps.orchestrator.week_plan_edits import (
    apply_week_plan_edit,
    list_week_plan_workouts,
    load_week_plan_for_edit,
    preview_change_start_time,
    preview_move_workout,
    preview_update_workout_text,
)
from rps.orchestrator.week_revision import revise_week_plan
from rps.orchestrator.workout_export import run_workout_export
from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

JsonMap = dict[str, Any]


class _HasToJson(Protocol):
    """Preview payload protocol produced by bounded week-plan edit helpers."""

    def to_json(self) -> str: ...


def _preview_from_week_plan(operation: str, preview_payload: _HasToJson) -> CoachOperationPreviewModel:
    payload = json.loads(preview_payload.to_json())
    return CoachOperationPreviewModel(
        operation=operation,
        ok=bool(payload.get("ok")),
        requires_confirmation=True,
        summary=str(payload.get("summary") or ""),
        warnings=[str(item) for item in payload.get("warnings") or []],
        issues=[str(item) for item in payload.get("issues") or []],
        affected_artifacts=["WEEK_PLAN", "INTERVALS_WORKOUTS"],
        downstream_recomputations=["Rebuild INTERVALS_WORKOUTS"],
        document=payload.get("document") if isinstance(payload.get("document"), dict) else None,
        metadata={"workouts": payload.get("workouts") or []},
    )


def preview_read_context(
    *,
    store: LocalArtifactStore,
    athlete_id: str,
    year: int,
    week: int,
) -> CoachOperationPreviewModel:
    """Summarize selected-week context for the active coach."""

    version_key = f"{year:04d}-{week:02d}"
    week_plan = None
    try:
        week_plan = load_week_plan_for_edit(store, athlete_id, year, week)
    except FileNotFoundError:
        week_plan = None
    activity_trend_key = store.resolve_week_version_key(athlete_id, ArtifactType.ACTIVITIES_TREND, version_key)
    actual_key = store.resolve_week_version_key(athlete_id, ArtifactType.ACTIVITIES_ACTUAL, version_key)
    return CoachOperationPreviewModel(
        operation="read_context",
        ok=True,
        requires_confirmation=False,
        summary=f"Loaded selected-week context for {version_key}.",
        affected_artifacts=["WEEK_PLAN", "ACTIVITIES_TREND", "ACTIVITIES_ACTUAL", "SEASON_PLAN", "PHASE_PREVIEW"],
        metadata={
            "iso_week": version_key,
            "week_plan_present": bool(week_plan),
            "workouts": list_week_plan_workouts(week_plan) if isinstance(week_plan, dict) else [],
            "activities_trend_version": activity_trend_key,
            "activities_actual_version": actual_key,
        },
    )


def preview_move_workout_operation(
    week_plan: JsonMap,
    *,
    year: int,
    week: int,
    workout_id: str,
    target_day: str,
    target_start: str | None = None,
) -> CoachOperationPreviewModel:
    """Preview moving one workout within the selected week."""

    preview = preview_move_workout(
        week_plan,
        year=year,
        week=week,
        workout_id=workout_id,
        target_day=target_day,
        target_start=target_start,
    )
    return _preview_from_week_plan("preview_artifact_edit", preview)


def preview_change_start_time_operation(
    week_plan: JsonMap,
    *,
    workout_id: str,
    start: str,
) -> CoachOperationPreviewModel:
    """Preview changing one workout start time."""

    preview = preview_change_start_time(week_plan, workout_id=workout_id, start=start)
    return _preview_from_week_plan("preview_artifact_edit", preview)


def preview_update_workout_text_operation(
    week_plan: JsonMap,
    *,
    workout_id: str,
    workout_text: str,
    title: str | None = None,
    notes: str | None = None,
    start: str | None = None,
) -> CoachOperationPreviewModel:
    """Preview replacing workout text and optional metadata."""

    preview = preview_update_workout_text(
        week_plan,
        workout_id=workout_id,
        workout_text=workout_text,
        title=title,
        notes=notes,
        start=start,
    )
    return _preview_from_week_plan("preview_artifact_edit", preview)


def preview_scoped_week_replan_operation(
    *,
    year: int,
    week: int,
    message: str,
) -> CoachOperationPreviewModel:
    """Preview a scoped week replan without mutating artifacts."""

    version_key = f"{year:04d}-{week:02d}"
    return CoachOperationPreviewModel(
        operation="preview_scoped_replan",
        ok=bool(message.strip()),
        requires_confirmation=True,
        summary=f"Scoped replan prepared for {version_key}.",
        issues=[] if message.strip() else ["Replan message must not be empty."],
        affected_artifacts=["WEEK_PLAN", "INTERVALS_WORKOUTS"],
        downstream_recomputations=["Rebuild INTERVALS_WORKOUTS"],
        metadata={"message": message.strip(), "iso_week": version_key},
    )


def preview_report_operation(*, year: int, week: int) -> CoachOperationPreviewModel:
    """Preview performance-report generation for the selected week."""

    version_key = f"{year:04d}-{week:02d}"
    return CoachOperationPreviewModel(
        operation="preview_report",
        ok=True,
        requires_confirmation=True,
        summary=f"Performance report generation prepared for {version_key}.",
        affected_artifacts=["DES_ANALYSIS_REPORT"],
        metadata={"iso_week": version_key},
    )


def preview_feed_forward_operation(*, year: int, week: int) -> CoachOperationPreviewModel:
    """Preview report + feed-forward chain for the selected week."""

    version_key = f"{year:04d}-{week:02d}"
    return CoachOperationPreviewModel(
        operation="preview_feed_forward",
        ok=True,
        requires_confirmation=True,
        summary=f"Feed-forward chain prepared for {version_key}.",
        affected_artifacts=["DES_ANALYSIS_REPORT", "SEASON_PHASE_FEED_FORWARD", "PHASE_FEED_FORWARD"],
        metadata={"iso_week": version_key},
    )


def apply_week_plan_preview(
    *,
    workspace_root: Path,
    athlete_id: str,
    document: JsonMap,
    run_id: str,
) -> CoachOperationApplyResultModel:
    """Persist a previewed week-plan edit and rebuild workouts export."""

    result = apply_week_plan_edit(
        workspace_root=workspace_root,
        schema_dir=Path("specs/schemas"),
        athlete_id=athlete_id,
        document=document,
        run_id=run_id,
    )
    writes: list[ArtifactWriteModel] = []
    if result.week_plan_version_key or result.week_plan_path:
        writes.append(
            ArtifactWriteModel(
                artifact_type="WEEK_PLAN",
                version_key=result.week_plan_version_key,
                path=result.week_plan_path,
                run_id=run_id,
            )
        )
    if result.export_version_key or result.export_path:
        writes.append(
            ArtifactWriteModel(
                artifact_type="INTERVALS_WORKOUTS",
                version_key=result.export_version_key,
                path=result.export_path,
                run_id=run_id,
            )
        )
    return CoachOperationApplyResultModel(
        operation="apply_artifact_edit",
        ok=result.ok,
        summary=result.summary,
        artifact_writes=writes,
        error=result.error,
    )


def apply_scoped_week_replan_operation(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    workspace_root: Path,
    athlete_id: str,
    year: int,
    week: int,
    message: str,
    run_id: str,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    max_num_results: int = 20,
) -> CoachOperationApplyResultModel:
    """Run Week Planner revision and rebuild workouts export."""

    revise_result = revise_week_plan(
        runtime_for,
        athlete_id=athlete_id,
        year=year,
        week=week,
        message=message,
        run_id=run_id,
        model_resolver=model_resolver,
        temperature_resolver=temperature_resolver,
        force_file_search=True,
        max_num_results=max_num_results,
    )
    if not (isinstance(revise_result, dict) and revise_result.get("ok")):
        return CoachOperationApplyResultModel(
            operation="apply_scoped_replan",
            ok=False,
            summary=f"Scoped week replan failed for {year:04d}-{week:02d}.",
            error=str(revise_result.get("error") or revise_result.get("final_text") or "Week Planner revision failed."),
        )

    store = LocalArtifactStore(root=workspace_root)
    export_result = run_workout_export(
        store=store,
        athlete_id=athlete_id,
        year=year,
        week=week,
        run_id=f"{run_id}_export",
        plan_mtime=None,
        needs_week_plan=False,
    )
    version_key = f"{year:04d}-{week:02d}"
    writes = [
        ArtifactWriteModel(
            artifact_type="WEEK_PLAN",
            version_key=store.resolve_week_version_key(athlete_id, ArtifactType.WEEK_PLAN, version_key),
            path=None,
            run_id=run_id,
        )
    ]
    export_version = store.resolve_week_version_key(athlete_id, ArtifactType.INTERVALS_WORKOUTS, version_key)
    if export_version:
        writes.append(
            ArtifactWriteModel(
                artifact_type="INTERVALS_WORKOUTS",
                version_key=export_version,
                path=None,
                run_id=f"{run_id}_export",
            )
        )
    return CoachOperationApplyResultModel(
        operation="apply_scoped_replan",
        ok=bool(export_result.get("ok")),
        summary=f"Scoped week replan applied for {version_key}.",
        artifact_writes=writes,
        error=None if export_result.get("ok") else str(export_result.get("error") or "Workout export rebuild failed."),
    )


def apply_report_operation(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    max_num_results: int = 20,
) -> CoachOperationApplyResultModel:
    """Run DES analysis report generation for the selected week."""

    result = create_performance_report(
        runtime_for,
        athlete_id=athlete_id,
        report_week=IsoWeek(year=year, week=week),
        run_id_prefix=run_id,
        force_file_search=True,
        max_num_results=max_num_results,
        model_resolver=model_resolver,
        temperature_resolver=temperature_resolver,
    )
    if not (isinstance(result, dict) and result.get("ok")):
        return CoachOperationApplyResultModel(
            operation="apply_report",
            ok=False,
            summary=f"Performance report failed for {year:04d}-{week:02d}.",
            error=str(result.get("message") if isinstance(result, dict) else "Performance report failed."),
        )
    writes = [
        ArtifactWriteModel(
            artifact_type="DES_ANALYSIS_REPORT",
            version_key=f"{year:04d}-{week:02d}",
            path=None,
            run_id=run_id,
        )
    ]
    return CoachOperationApplyResultModel(
        operation="apply_report",
        ok=True,
        summary=f"Performance report created for {year:04d}-{week:02d}.",
        artifact_writes=writes,
    )


def apply_feed_forward_operation(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    workspace_root: Path,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    max_num_results: int = 20,
) -> CoachOperationApplyResultModel:
    """Run the report + feed-forward chain for the selected week."""

    result = run_feed_forward_chain(
        runtime_for,
        workspace_root=workspace_root,
        athlete_id=athlete_id,
        target_week=IsoWeek(year=year, week=week),
        run_id_prefix=run_id,
        model_resolver=model_resolver,
        temperature_resolver=temperature_resolver,
        max_num_results=max_num_results,
    )
    writes: list[ArtifactWriteModel] = []
    if result.report_version_key:
        writes.append(
            ArtifactWriteModel(
                artifact_type="DES_ANALYSIS_REPORT",
                version_key=result.report_version_key,
                path=None,
                run_id=f"{run_id}_report",
            )
        )
    if result.season_phase_version_key:
        writes.append(
            ArtifactWriteModel(
                artifact_type="SEASON_PHASE_FEED_FORWARD",
                version_key=result.season_phase_version_key,
                path=None,
                run_id=f"{run_id}_season_phase",
            )
        )
    if result.phase_version_key:
        writes.append(
            ArtifactWriteModel(
                artifact_type="PHASE_FEED_FORWARD",
                version_key=result.phase_version_key,
                path=None,
                run_id=f"{run_id}_phase",
            )
        )
    return CoachOperationApplyResultModel(
        operation="apply_feed_forward",
        ok=result.ok,
        summary=f"Feed-forward chain {'completed' if result.ok else 'failed'} for {year:04d}-{week:02d}.",
        artifact_writes=writes,
        error=result.error,
    )
