"""Deterministic bounded edits for existing week plans."""

from __future__ import annotations

import copy
import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import TypeAlias

from rps.agents.tasks import OUTPUT_SPECS, AgentTask
from rps.orchestrator.workout_export import run_workout_export
from rps.workouts.validator import collect_week_plan_export_issues
from rps.workspace.guarded_store import GuardedValidatedStore
from rps.workspace.local_store import LocalArtifactStore, utc_iso_now
from rps.workspace.types import ArtifactType

LOGGER = logging.getLogger(__name__)

JsonMap: TypeAlias = dict[str, object]

_DAY_TO_ISO = {
    "mon": ("Mon", 1),
    "monday": ("Mon", 1),
    "tue": ("Tue", 2),
    "tues": ("Tue", 2),
    "tuesday": ("Tue", 2),
    "wed": ("Wed", 3),
    "wednesday": ("Wed", 3),
    "thu": ("Thu", 4),
    "thurs": ("Thu", 4),
    "thursday": ("Thu", 4),
    "fri": ("Fri", 5),
    "friday": ("Fri", 5),
    "sat": ("Sat", 6),
    "saturday": ("Sat", 6),
    "sun": ("Sun", 7),
    "sunday": ("Sun", 7),
}
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")
_DURATION_PATTERN = re.compile(r"(?P<hours>\d+)h(?P<minutes>\d+)?m?|(?P<mins_only>\d+)m")


@dataclass(frozen=True)
class WeekPlanEditPreview:
    """Structured preview information for one pending week-plan edit."""

    ok: bool
    operation: str
    summary: str
    warnings: list[str]
    issues: list[str]
    workouts: list[dict[str, str]]
    document: JsonMap

    def to_json(self) -> str:
        """Return a stable JSON representation for tool output."""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


@dataclass(frozen=True)
class WeekPlanApplyResult:
    """Result of applying and exporting a week-plan edit."""

    ok: bool
    summary: str
    week_plan_version_key: str | None
    week_plan_path: str | None
    export_version_key: str | None
    export_path: str | None
    error: str | None = None

    def to_json(self) -> str:
        """Return a stable JSON representation for tool output."""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _require_time(value: str) -> str:
    cleaned = value.strip()
    if not _TIME_RE.fullmatch(cleaned):
        raise ValueError("start time must be HH:MM")
    return cleaned


def _resolve_day(target_day: str) -> tuple[str, str]:
    key = target_day.strip().lower()
    resolved = _DAY_TO_ISO.get(key)
    if resolved is None:
        raise ValueError("target_day must be one of Mon..Sun")
    day_label, iso_day = resolved
    return day_label, str(iso_day)


def _date_for_day(year: int, week: int, iso_day: int) -> str:
    return date.fromisocalendar(year, week, iso_day).isoformat()


def _duration_hhmmss(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}:00"


def _format_duration_hhmm(total_minutes: int) -> str:
    if total_minutes <= 0:
        return ""
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def _duration_minutes_from_workout_text(text: str) -> int:
    if not text:
        return 0
    total = 0
    for match in _DURATION_PATTERN.finditer(text):
        if match.group("mins_only"):
            total += int(match.group("mins_only"))
            continue
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        total += hours * 60 + minutes
    return total


def load_week_plan_for_edit(
    store: LocalArtifactStore,
    athlete_id: str,
    year: int,
    week: int,
) -> JsonMap:
    """Load the current week plan envelope for deterministic editing."""
    version_key = f"{year:04d}-{week:02d}"
    payload = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, version_key)
    if not isinstance(payload, dict):
        raise ValueError("WEEK_PLAN payload is not an object")
    return copy.deepcopy(payload)


def list_week_plan_workouts(week_plan: JsonMap) -> list[dict[str, str]]:
    """Return a compact stable summary of agenda-linked workouts."""
    data = _as_map(week_plan.get("data"))
    agenda = _as_list(data.get("agenda"))
    workouts = _as_list(data.get("workouts"))
    workout_map = {
        str(_as_map(workout).get("workout_id") or ""): _as_map(workout)
        for workout in workouts
        if str(_as_map(workout).get("workout_id") or "")
    }
    rows: list[dict[str, str]] = []
    for entry in agenda:
        row = _as_map(entry)
        workout_id = row.get("workout_id")
        if workout_id in (None, ""):
            continue
        workout = workout_map.get(str(workout_id), {})
        rows.append(
            {
                "workout_id": str(workout_id),
                "day": str(row.get("day") or ""),
                "date": str(row.get("date") or ""),
                "day_role": str(row.get("day_role") or ""),
                "planned_duration": str(row.get("planned_duration") or ""),
                "planned_kj": str(row.get("planned_kj") or ""),
                "title": str(workout.get("title") or ""),
                "start": str(workout.get("start") or ""),
                "duration": str(workout.get("duration") or ""),
            }
        )
    return rows


def _lookup_rows(week_plan: JsonMap) -> tuple[list[JsonMap], dict[str, JsonMap], dict[str, JsonMap]]:
    data = _as_map(week_plan.get("data"))
    agenda_rows = [_as_map(item) for item in _as_list(data.get("agenda"))]
    workouts = {
        str(_as_map(item).get("workout_id") or ""): _as_map(item)
        for item in _as_list(data.get("workouts"))
        if str(_as_map(item).get("workout_id") or "")
    }
    agenda_by_workout = {
        str(row.get("workout_id") or ""): row
        for row in agenda_rows
        if row.get("workout_id") not in (None, "")
    }
    return agenda_rows, workouts, agenda_by_workout


def _preview(operation: str, summary: str, document: JsonMap, warnings: list[str] | None = None) -> WeekPlanEditPreview:
    warning_list = list(warnings or [])
    issues = [issue.format() for issue in collect_week_plan_export_issues(document)]
    return WeekPlanEditPreview(
        ok=not issues,
        operation=operation,
        summary=summary,
        warnings=warning_list,
        issues=issues,
        workouts=list_week_plan_workouts(document),
        document=document,
    )


def preview_move_workout(
    week_plan: JsonMap,
    *,
    year: int,
    week: int,
    workout_id: str,
    target_day: str,
    target_start: str | None = None,
) -> WeekPlanEditPreview:
    """Preview moving one workout onto an empty target day within the same week."""
    document = copy.deepcopy(week_plan)
    agenda_rows, workouts, agenda_by_workout = _lookup_rows(document)
    workout = workouts.get(workout_id)
    if workout is None:
        raise ValueError(f"unknown workout_id: {workout_id}")
    source_row = agenda_by_workout.get(workout_id)
    if source_row is None:
        raise ValueError(f"agenda row for workout_id {workout_id} not found")

    day_label, iso_day_text = _resolve_day(target_day)
    iso_day = int(iso_day_text)
    target_date = _date_for_day(year, week, iso_day)
    target_row = next((row for row in agenda_rows if str(row.get("day") or "") == day_label), None)
    if target_row is None:
        raise ValueError(f"target agenda day not found: {day_label}")
    existing_target = target_row.get("workout_id")
    if existing_target not in (None, "", workout_id):
        raise ValueError(f"target day {day_label} already contains workout_id {existing_target}")
    if target_row is source_row:
        raise ValueError("source and target day are identical; use change_start_time if only the start should change")

    source_payload = {
        "day_role": source_row.get("day_role", "ENDURANCE"),
        "planned_duration": source_row.get("planned_duration", "00:00"),
        "planned_kj": source_row.get("planned_kj", 0),
        "workout_id": source_row.get("workout_id"),
    }
    target_row["day"] = day_label
    target_row["date"] = target_date
    target_row["day_role"] = source_payload["day_role"]
    target_row["planned_duration"] = source_payload["planned_duration"]
    target_row["planned_kj"] = source_payload["planned_kj"]
    target_row["workout_id"] = source_payload["workout_id"]

    source_row["day_role"] = "REST"
    source_row["planned_duration"] = "00:00"
    source_row["planned_kj"] = 0
    source_row["workout_id"] = None

    workout["date"] = target_date
    if target_start is not None and target_start.strip():
        workout["start"] = _require_time(target_start)

    title = str(workout.get("title") or workout_id)
    return _preview(
        "move_workout",
        f"Move '{title}' ({workout_id}) to {day_label} {target_date}.",
        document,
    )


def preview_change_start_time(
    week_plan: JsonMap,
    *,
    workout_id: str,
    start: str,
) -> WeekPlanEditPreview:
    """Preview changing one workout start time."""
    document = copy.deepcopy(week_plan)
    _agenda_rows, workouts, _agenda_by_workout = _lookup_rows(document)
    workout = workouts.get(workout_id)
    if workout is None:
        raise ValueError(f"unknown workout_id: {workout_id}")
    workout["start"] = _require_time(start)
    title = str(workout.get("title") or workout_id)
    return _preview(
        "change_start_time",
        f"Change start time for '{title}' ({workout_id}) to {workout['start']}.",
        document,
    )


def preview_update_workout_text(
    week_plan: JsonMap,
    *,
    workout_id: str,
    workout_text: str,
    title: str | None = None,
    notes: str | None = None,
    start: str | None = None,
) -> WeekPlanEditPreview:
    """Preview replacing one workout text block and optional workout metadata."""
    document = copy.deepcopy(week_plan)
    _agenda_rows, workouts, agenda_by_workout = _lookup_rows(document)
    workout = workouts.get(workout_id)
    if workout is None:
        raise ValueError(f"unknown workout_id: {workout_id}")
    agenda_row = agenda_by_workout.get(workout_id)
    if agenda_row is None:
        raise ValueError(f"agenda row for workout_id {workout_id} not found")
    if not workout_text.strip():
        raise ValueError("workout_text must not be empty")

    warnings: list[str] = []
    workout["workout_text"] = workout_text.strip()
    if title is not None and title.strip():
        workout["title"] = title.strip()
    if notes is not None:
        workout["notes"] = notes.strip()
    if start is not None and start.strip():
        workout["start"] = _require_time(start)

    normalized_text = str(workout["workout_text"])
    total_minutes = _duration_minutes_from_workout_text(normalized_text)
    if total_minutes > 0:
        workout["duration"] = _duration_hhmmss(total_minutes)
        agenda_row["planned_duration"] = _format_duration_hhmm(total_minutes)
    else:
        warnings.append("Could not derive duration from workout_text; existing duration fields were kept.")

    title_text = str(workout.get("title") or workout_id)
    return _preview(
        "update_workout_text",
        f"Replace workout text for '{title_text}' ({workout_id}).",
        document,
        warnings=warnings,
    )


def apply_week_plan_edit(
    *,
    workspace_root: Path,
    schema_dir: Path,
    athlete_id: str,
    document: JsonMap,
    run_id: str,
) -> WeekPlanApplyResult:
    """Persist an edited week plan through the guarded store and rebuild the export."""
    working = copy.deepcopy(document)
    meta = _as_map(working.get("meta"))
    meta.pop("version_key", None)
    meta["created_at"] = utc_iso_now()
    meta["run_id"] = run_id
    existing_notes = str(meta.get("notes") or "").strip()
    edit_note = "Edited via Workout Editor chat."
    if edit_note not in existing_notes:
        meta["notes"] = f"{existing_notes} {edit_note}".strip()
    working["meta"] = meta

    guarded = GuardedValidatedStore(
        athlete_id=athlete_id,
        schema_dir=schema_dir,
        workspace_root=workspace_root,
    )
    LOGGER.info("Workout editor apply started athlete=%s run_id=%s", athlete_id, run_id)
    store_result = guarded.guard_put_validated(
        output_spec=OUTPUT_SPECS[AgentTask.CREATE_WEEK_PLAN],
        document=working,
        run_id=run_id,
        producer_agent="workout_editor",
        update_latest=True,
    )
    store = LocalArtifactStore(root=workspace_root)
    plan_path = Path(str(store_result["path"]))
    export_result = run_workout_export(
        store,
        athlete_id,
        int(str(meta.get("iso_week") or "0000-00").split("-")[0]),
        int(str(meta.get("iso_week") or "0000-00").split("-")[1]),
        run_id,
        plan_mtime=plan_path.stat().st_mtime if plan_path.exists() else None,
        needs_week_plan=True,
        force_export=True,
    )
    raw_export_payload = export_result.get("result")
    export_payload: JsonMap = raw_export_payload if isinstance(raw_export_payload, dict) else {}
    export_ok = bool(export_result.get("ok"))
    LOGGER.info("Workout editor apply completed athlete=%s run_id=%s", athlete_id, run_id)
    return WeekPlanApplyResult(
        ok=bool(store_result.get("ok")) and export_ok,
        summary=(
            "Stored edited WEEK_PLAN and rebuilt INTERVALS_WORKOUTS."
            if export_ok
            else "Stored edited WEEK_PLAN, but INTERVALS_WORKOUTS rebuild failed."
        ),
        week_plan_version_key=str(store_result.get("version_key") or "") or None,
        week_plan_path=str(store_result.get("path") or "") or None,
        export_version_key=str(export_payload.get("version_key") or "") or None,
        export_path=str(export_payload.get("path") or "") or None,
        error=(
            None
            if bool(export_result.get("ok"))
            else str(export_payload.get("error") or export_result.get("message") or "workout export failed")
        ),
    )
