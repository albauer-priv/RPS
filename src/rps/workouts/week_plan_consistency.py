"""Deterministic normalization and consistency checks for WEEK_PLAN payloads."""

from __future__ import annotations

import copy
import re
from typing import TypeAlias

from rps.workouts.issues import WorkoutValidationIssue

JsonMap: TypeAlias = dict[str, object]

_SECTION_HEADERS = {
    "Warmup",
    "#### Activation",
    "Main Set",
    "#### Add-On",
    "#### Z2 Add-On",
    "Cooldown",
}
_LOOP_RE = re.compile(r"^(?P<count>\d+)[xX]$")
_STEP_DURATION_RE = re.compile(
    r"^- (?P<duration>(?:\d+(?:\.\d+)?(?:s|m|h)|\d+m\d+|\d+h\d+m))(?:\s|$)"
)
_KJ_NOTES_RE = re.compile(r"\bplanned_kJ\s+(?P<value>\d+(?:\.\d+)?)\b", re.IGNORECASE)
_SUMMARY_TOTAL_RE = re.compile(
    r"(Weekly planned_kJ mechanical total across agenda\s*=\s*)(?P<value>\d+(?:\.\d+)?)(?P<tail>\.?)",
    re.IGNORECASE,
)


def normalize_week_plan_consistency(week_plan: JsonMap) -> JsonMap:
    """Normalize linked workout metadata from deterministic workout-local sources."""
    document = copy.deepcopy(week_plan)
    data = _as_map(document.get("data"))
    agenda = [_as_map(item) for item in _as_list(data.get("agenda"))]
    workouts = [_as_map(item) for item in _as_list(data.get("workouts"))]
    workout_map = {
        str(workout.get("workout_id") or ""): workout
        for workout in workouts
        if str(workout.get("workout_id") or "")
    }

    for row in agenda:
        workout_id = row.get("workout_id")
        if workout_id in (None, ""):
            continue
        workout = workout_map.get(str(workout_id))
        if workout is None:
            continue

        derived_seconds = derive_workout_duration_seconds(str(workout.get("workout_text") or ""))
        current_seconds = _hhmmss_to_seconds(str(workout.get("duration") or ""))
        effective_seconds = current_seconds
        if derived_seconds > 0:
            effective_seconds = derived_seconds
            workout["duration"] = _seconds_to_hhmmss(derived_seconds)
        elif current_seconds <= 1 and derived_seconds <= 0:
            effective_seconds = current_seconds

        if effective_seconds > 1:
            row["planned_duration"] = _seconds_to_hhmm(effective_seconds)

        note_kj = derive_workout_planned_kj(str(workout.get("notes") or ""))
        current_kj = _to_nonnegative_number(row.get("planned_kj"))
        if note_kj > 0 and current_kj <= 0:
            row["planned_kj"] = int(note_kj)

        if not workout.get("date") and row.get("date"):
            workout["date"] = row["date"]

    week_summary = _as_map(data.get("week_summary"))
    notes = str(week_summary.get("notes") or "")
    if notes:
        mechanical_total = _agenda_mechanical_total(agenda)
        week_summary["notes"] = _replace_summary_total(notes, mechanical_total)

    data["agenda"] = agenda
    data["workouts"] = workouts
    data["week_summary"] = week_summary
    document["data"] = data
    return document


def collect_week_plan_consistency_issues(week_plan: JsonMap) -> list[WorkoutValidationIssue]:
    """Collect cross-field consistency issues for agenda/workout alignment."""
    data = _as_map(week_plan.get("data"))
    agenda = _as_list(data.get("agenda"))
    workouts = _as_list(data.get("workouts"))
    workout_map = {
        str(_as_map(workout).get("workout_id") or ""): _as_map(workout)
        for workout in workouts
        if str(_as_map(workout).get("workout_id") or "")
    }
    issues: list[WorkoutValidationIssue] = []

    for entry in agenda:
        row = _as_map(entry)
        workout_id = row.get("workout_id")
        if workout_id in (None, ""):
            continue
        workout_id_text = str(workout_id)
        workout = workout_map.get(workout_id_text)
        if workout is None:
            continue

        agenda_duration = str(row.get("planned_duration") or "")
        workout_duration = str(workout.get("duration") or "")
        workout_seconds = _hhmmss_to_seconds(workout_duration)
        agenda_seconds = _hhmm_to_seconds(agenda_duration)
        note_kj = derive_workout_planned_kj(str(workout.get("notes") or ""))
        agenda_kj = _to_nonnegative_number(row.get("planned_kj"))

        if workout_seconds <= 1:
            issues.append(WorkoutValidationIssue(workout_id_text, "linked workout has invalid duration metadata"))
        if agenda_seconds <= 0:
            issues.append(WorkoutValidationIssue(workout_id_text, "agenda row with workout_id must have non-zero planned_duration"))
        if workout_seconds > 1 and agenda_seconds != workout_seconds:
            issues.append(WorkoutValidationIssue(workout_id_text, "agenda planned_duration does not match linked workout duration"))
        if agenda_kj <= 0:
            issues.append(WorkoutValidationIssue(workout_id_text, "agenda row with workout_id must have positive planned_kj"))
        if note_kj > 0 and abs(agenda_kj - note_kj) > 0.5:
            issues.append(WorkoutValidationIssue(workout_id_text, "agenda planned_kj does not match linked workout notes"))
        if row.get("date") and workout.get("date") and str(row.get("date")) != str(workout.get("date")):
            issues.append(WorkoutValidationIssue(workout_id_text, "agenda date does not match linked workout date"))

    week_summary = _as_map(data.get("week_summary"))
    notes = str(week_summary.get("notes") or "")
    stated_total = derive_summary_mechanical_total(notes)
    if stated_total is not None:
        actual_total = _agenda_mechanical_total([_as_map(item) for item in agenda])
        if abs(actual_total - stated_total) > 0.5:
            issues.append(WorkoutValidationIssue("WEEK_PLAN", "week_summary notes mechanical total does not match agenda sum"))

    return issues


def derive_workout_planned_kj(notes: str) -> float:
    """Extract mechanical planned_kJ from workout notes when present."""
    match = _KJ_NOTES_RE.search(notes or "")
    if not match:
        return 0.0
    try:
        return float(match.group("value"))
    except ValueError:
        return 0.0


def derive_summary_mechanical_total(notes: str) -> float | None:
    """Extract the stated weekly mechanical total from summary notes."""
    match = _SUMMARY_TOTAL_RE.search(notes or "")
    if not match:
        return None
    try:
        return float(match.group("value"))
    except ValueError:
        return None


def derive_workout_duration_seconds(text: str) -> int:
    """Derive total workout duration from workout_text, honoring simple loop blocks."""
    total_seconds = 0.0
    repeat = 1
    repeat_active = False
    for raw_line in (text or "").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            if repeat_active:
                repeat = 1
                repeat_active = False
            continue
        if stripped in _SECTION_HEADERS:
            repeat = 1
            repeat_active = False
            continue
        loop_match = _LOOP_RE.fullmatch(stripped)
        if loop_match:
            repeat = int(loop_match.group("count"))
            repeat_active = True
            continue
        step_match = _STEP_DURATION_RE.fullmatch(stripped) or _STEP_DURATION_RE.match(stripped)
        if not step_match:
            continue
        duration_token = step_match.group("duration")
        seconds = _duration_token_to_seconds(duration_token)
        total_seconds += seconds * max(repeat, 1)
    return int(round(total_seconds))


def derive_workout_duration_hhmmss(text: str) -> str:
    """Return derived workout duration in HH:MM:SS or empty string."""
    seconds = derive_workout_duration_seconds(text)
    if seconds <= 0:
        return ""
    return _seconds_to_hhmmss(seconds)


def derive_workout_duration_hhmm(text: str) -> str:
    """Return derived workout duration in HH:MM or empty string."""
    seconds = derive_workout_duration_seconds(text)
    if seconds <= 0:
        return ""
    return _seconds_to_hhmm(seconds)


def _replace_summary_total(notes: str, actual_total: float) -> str:
    if not notes:
        return notes
    rounded = str(int(round(actual_total)))
    return _SUMMARY_TOTAL_RE.sub(lambda m: f"{m.group(1)}{rounded}{m.group('tail')}", notes, count=1)


def _agenda_mechanical_total(agenda: list[JsonMap]) -> float:
    return sum(_to_nonnegative_number(row.get("planned_kj")) for row in agenda)


def _duration_token_to_seconds(token: str) -> float:
    total = 0.0
    remaining = token
    hours_match = re.search(r"(?P<hours>\d+(?:\.\d+)?)h", remaining)
    if hours_match:
        total += float(hours_match.group("hours")) * 3600
    minutes_match = re.search(r"(?P<minutes>\d+(?:\.\d+)?)m", remaining)
    if minutes_match:
        total += float(minutes_match.group("minutes")) * 60
    seconds_match = re.search(r"(?P<seconds>\d+(?:\.\d+)?)s", remaining)
    if seconds_match:
        total += float(seconds_match.group("seconds"))
    return total


def _seconds_to_hhmmss(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _seconds_to_hhmm(total_seconds: int) -> str:
    rounded_minutes = int(round(total_seconds / 60.0))
    hours = rounded_minutes // 60
    minutes = rounded_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def _hhmmss_to_seconds(value: str) -> int:
    parts = value.split(":")
    if len(parts) != 3:
        return 0
    try:
        hours, minutes, seconds = [int(part) for part in parts]
    except ValueError:
        return 0
    return max(0, hours * 3600 + minutes * 60 + seconds)


def _hhmm_to_seconds(value: str) -> int:
    parts = value.split(":")
    if len(parts) != 2:
        return 0
    try:
        hours, minutes = [int(part) for part in parts]
    except ValueError:
        return 0
    return max(0, (hours * 60 + minutes) * 60)


def _to_nonnegative_number(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return max(0.0, float(value))
    if isinstance(value, str):
        try:
            return max(0.0, float(value))
        except ValueError:
            return 0.0
    return 0.0


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []
