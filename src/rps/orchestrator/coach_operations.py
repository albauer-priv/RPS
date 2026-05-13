"""Active coach operations built on top of existing bounded planners and exports."""

from __future__ import annotations

import json
from collections.abc import Callable
from difflib import unified_diff
from pathlib import Path
from typing import Any, Protocol

from rps.agents.runtime import AgentRuntime
from rps.crewai_runtime.models import (
    ArtifactWriteModel,
    CoachOperationApplyResultModel,
    CoachOperationPreviewModel,
)
from rps.orchestrator.advisory_actions import run_feed_forward_chain
from rps.orchestrator.context_snapshots import save_advisory_memory
from rps.orchestrator.plan_week import create_performance_report
from rps.orchestrator.week_plan_edits import (
    apply_week_plan_edit,
    list_week_plan_workouts,
    load_week_plan_for_edit,
    preview_change_start_time,
    preview_move_workout,
    preview_update_workout_text,
)
from rps.orchestrator.week_revision import preview_week_plan_revision, revise_week_plan
from rps.orchestrator.workout_export import run_workout_export
from rps.rendering.renderer import validate_document
from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.schema_registry import SchemaValidationError
from rps.workspace.types import ArtifactType

JsonMap = dict[str, Any]


def _refresh_week_advisory_memory(
    *,
    store: LocalArtifactStore,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    week_plan_payload: JsonMap | None,
) -> None:
    """Best-effort refresh of advisory memory after a successful week-plan change."""

    try:
        season_plan_payload = store.load_latest(athlete_id, ArtifactType.SEASON_PLAN)
    except Exception:
        season_plan_payload = None
    try:
        save_advisory_memory(
            store,
            athlete_id,
            target_week=IsoWeek(year=year, week=week),
            run_id=run_id,
            season_plan_payload=season_plan_payload if isinstance(season_plan_payload, dict) else {},
            week_plan_payload=week_plan_payload if isinstance(week_plan_payload, dict) else {},
        )
    except Exception:
        return


class _HasToJson(Protocol):
    """Preview payload protocol produced by bounded week-plan edit helpers."""

    def to_json(self) -> str: ...


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _json_diff(before: object, after: object) -> str:
    before_text = json.dumps(before, ensure_ascii=False, indent=2, sort_keys=True)
    after_text = json.dumps(after, ensure_ascii=False, indent=2, sort_keys=True)
    return "\n".join(
        unified_diff(
            before_text.splitlines(),
            after_text.splitlines(),
            fromfile="before.json",
            tofile="after.json",
            lineterm="",
        )
    )


def _week_plan_rows(document: JsonMap) -> list[dict[str, str]]:
    data = _as_map(document.get("data"))
    agenda = _as_list(data.get("agenda"))
    workouts = {
        str(_as_map(item).get("workout_id") or ""): _as_map(item)
        for item in _as_list(data.get("workouts"))
        if str(_as_map(item).get("workout_id") or "")
    }
    rows: list[dict[str, str]] = []
    for entry in agenda:
        agenda_row = _as_map(entry)
        workout_id = str(agenda_row.get("workout_id") or "")
        workout = workouts.get(workout_id, {})
        title = str(workout.get("title") or ("Rest" if not workout_id else workout_id))
        start = str(workout.get("start") or "")
        duration = str(workout.get("duration") or "")
        planned_duration = str(agenda_row.get("planned_duration") or "")
        planned_kj = str(agenda_row.get("planned_kj") or "")
        day_role = str(agenda_row.get("day_role") or "")
        rows.append(
            {
                "date": str(agenda_row.get("date") or ""),
                "day": str(agenda_row.get("day") or ""),
                "title": title,
                "start": start,
                "duration": duration,
                "planned_duration": planned_duration,
                "planned_kj": planned_kj,
                "day_role": day_role,
            }
        )
    return rows


def _row_summary(row: dict[str, str] | None) -> str:
    if not row:
        return "-"
    title = row.get("title") or "-"
    day_role = row.get("day_role") or "-"
    start = row.get("start") or "-"
    duration = row.get("duration") or row.get("planned_duration") or "-"
    planned_kj = row.get("planned_kj") or "-"
    return (
        f"Workout: {title}; "
        f"Role: {day_role}; "
        f"Start: {start}; "
        f"Duration: {duration}; "
        f"Load: {planned_kj} kJ"
    )


def _change_rows(before: list[dict[str, str]], after: list[dict[str, str]]) -> list[dict[str, str]]:
    def _index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
        return {
            f"{row.get('date') or ''}|{row.get('day') or ''}": row
            for row in rows
        }

    before_idx = _index(before)
    after_idx = _index(after)
    keys = sorted(set(before_idx) | set(after_idx))
    changes: list[dict[str, str]] = []
    for key in keys:
        before_row = before_idx.get(key)
        after_row = after_idx.get(key)
        before_text = _row_summary(before_row)
        after_text = _row_summary(after_row)
        if before_text == after_text:
            continue
        row = after_row or before_row or {}
        changes.append(
            {
                "date": str(row.get("date") or ""),
                "day": str(row.get("day") or ""),
                "workout": str((after_row or before_row or {}).get("title") or "-"),
                "before": before_text,
                "after": after_text,
                "title_before": str((before_row or {}).get("title") or "-"),
                "title_after": str((after_row or {}).get("title") or "-"),
                "day_role_before": str((before_row or {}).get("day_role") or "-"),
                "day_role_after": str((after_row or {}).get("day_role") or "-"),
                "start_before": str((before_row or {}).get("start") or "-"),
                "start_after": str((after_row or {}).get("start") or "-"),
                "duration_before": str(((before_row or {}).get("duration") or (before_row or {}).get("planned_duration") or "-")),
                "duration_after": str(((after_row or {}).get("duration") or (after_row or {}).get("planned_duration") or "-")),
                "planned_kj_before": str((before_row or {}).get("planned_kj") or "-"),
                "planned_kj_after": str((after_row or {}).get("planned_kj") or "-"),
            }
        )
    return changes


def _md_cell(value: str) -> str:
    return str(value or "-").replace("|", "\\|").replace("\n", "<br>")


def _change_table_markdown(changes: list[dict[str, str]]) -> str:
    if not changes:
        return (
            "| Date | Day | Workout | Before | After |\n"
            "|---|---|---|---|---|\n"
            "| - | - | - | No visible changes | No visible changes |"
        )
    lines = ["| Date | Day | Workout | Before | After |", "|---|---|---|---|---|"]
    for row in changes:
        before = _md_cell(str(row.get("before") or "-"))
        after = _md_cell(str(row.get("after") or "-"))
        workout = _md_cell(str(row.get("workout") or "-"))
        lines.append(
            f"| {_md_cell(str(row.get('date') or '-'))} | {_md_cell(str(row.get('day') or '-'))} | {workout} | {before} | {after} |"
        )
    return "\n".join(lines)


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
    runtime_for: Callable[[str], AgentRuntime],
    *,
    store: LocalArtifactStore,
    athlete_id: str,
    year: int,
    week: int,
    message: str,
    run_id: str,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    max_num_results: int = 20,
) -> CoachOperationPreviewModel:
    """Preview a scoped week replan with a real candidate WEEK_PLAN document."""

    version_key = f"{year:04d}-{week:02d}"
    cleaned_message = message.strip()
    if not cleaned_message:
        return CoachOperationPreviewModel(
            operation="preview_scoped_replan",
            ok=False,
            requires_confirmation=True,
            summary=f"Scoped replan prepared for {version_key}.",
            issues=["Replan message must not be empty."],
            affected_artifacts=["WEEK_PLAN", "INTERVALS_WORKOUTS"],
            downstream_recomputations=["Rebuild INTERVALS_WORKOUTS"],
            metadata={"message": cleaned_message, "iso_week": version_key},
        )

    try:
        before_document = load_week_plan_for_edit(store, athlete_id, year, week)
    except FileNotFoundError:
        return CoachOperationPreviewModel(
            operation="preview_scoped_replan",
            ok=False,
            requires_confirmation=True,
            summary=f"Scoped replan preview failed for {version_key}.",
            issues=[f"No WEEK_PLAN found for {version_key}."],
            affected_artifacts=["WEEK_PLAN", "INTERVALS_WORKOUTS"],
            downstream_recomputations=["Rebuild INTERVALS_WORKOUTS"],
            metadata={"message": cleaned_message, "iso_week": version_key},
        )

    preview_result = preview_week_plan_revision(
        runtime_for,
        athlete_id=athlete_id,
        year=year,
        week=week,
        message=cleaned_message,
        run_id=run_id,
        model_resolver=model_resolver,
        temperature_resolver=temperature_resolver,
        force_file_search=True,
        max_num_results=max_num_results,
    )
    if not (isinstance(preview_result, dict) and preview_result.get("ok")):
        return CoachOperationPreviewModel(
            operation="preview_scoped_replan",
            ok=False,
            requires_confirmation=True,
            summary=f"Scoped replan preview failed for {version_key}.",
            issues=[str(preview_result.get("error") or "Week Planner preview failed.")],
            affected_artifacts=["WEEK_PLAN", "INTERVALS_WORKOUTS"],
            downstream_recomputations=["Rebuild INTERVALS_WORKOUTS"],
            metadata={"message": cleaned_message, "iso_week": version_key},
        )

    preview_document = preview_result.get("document")
    if not isinstance(preview_document, dict):
        return CoachOperationPreviewModel(
            operation="preview_scoped_replan",
            ok=False,
            requires_confirmation=True,
            summary=f"Scoped replan preview failed for {version_key}.",
            issues=["Preview run did not return a candidate WEEK_PLAN document."],
            affected_artifacts=["WEEK_PLAN", "INTERVALS_WORKOUTS"],
            downstream_recomputations=["Rebuild INTERVALS_WORKOUTS"],
            metadata={"message": cleaned_message, "iso_week": version_key},
        )

    issues: list[str] = []
    try:
        validate_document(preview_document, "WEEK_PLAN", Path("specs/schemas"))
    except SchemaValidationError as exc:
        issues.extend(list(exc.errors or []))
    except Exception as exc:
        issues.append(str(exc))

    before_rows = _week_plan_rows(before_document)
    after_rows = _week_plan_rows(preview_document)
    change_rows = _change_rows(before_rows, after_rows)
    warnings = [] if change_rows else ["Preview produced no visible workout-level changes."]
    change_table_markdown = _change_table_markdown(change_rows)
    diff_text = _json_diff(before_document, preview_document)
    return CoachOperationPreviewModel(
        operation="preview_scoped_replan",
        ok=not issues,
        requires_confirmation=True,
        summary=f"Scoped replan preview prepared for {version_key}.",
        warnings=warnings,
        issues=issues,
        affected_artifacts=["WEEK_PLAN", "INTERVALS_WORKOUTS"],
        downstream_recomputations=["Rebuild INTERVALS_WORKOUTS"],
        document=preview_document,
        metadata={
            "message": cleaned_message,
            "iso_week": version_key,
            "base_workouts": before_rows,
            "preview_workouts": after_rows,
            "change_rows": change_rows,
            "change_table_markdown": change_table_markdown,
            "diff_text": diff_text,
        },
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
    if result.ok:
        meta = document.get("meta") if isinstance(document, dict) else None
        iso_week = meta.get("iso_week") if isinstance(meta, dict) else None
        if isinstance(iso_week, str) and "-" in iso_week:
            year_text, week_text = iso_week.split("-", 1)
            if year_text.isdigit() and week_text.isdigit():
                _refresh_week_advisory_memory(
                    store=LocalArtifactStore(root=workspace_root),
                    athlete_id=athlete_id,
                    year=int(year_text),
                    week=int(week_text),
                    run_id=run_id,
                    week_plan_payload=document if isinstance(document, dict) else None,
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
    if export_result.get("ok"):
        week_plan_payload = (
            store.load_version(athlete_id, ArtifactType.WEEK_PLAN, version_key)
            if store.exists(athlete_id, ArtifactType.WEEK_PLAN, version_key)
            else None
        )
        _refresh_week_advisory_memory(
            store=store,
            athlete_id=athlete_id,
            year=year,
            week=week,
            run_id=run_id,
            week_plan_payload=week_plan_payload if isinstance(week_plan_payload, dict) else None,
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
