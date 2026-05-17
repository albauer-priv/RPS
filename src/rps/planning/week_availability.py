"""Deterministic daily-availability validation for WEEK_PLAN artefacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from rps.workspace.iso_helpers import IsoWeek

JsonMap = dict[str, Any]


@dataclass(frozen=True)
class WeekAvailabilityIssue:
    """A deterministic daily-availability violation."""

    day: str
    date: str
    message: str

    def format(self) -> str:
        """Return a stable, agent-actionable validation message."""

        return f"{self.day} {self.date}: {self.message}"


def validate_week_plan_daily_availability(
    *,
    week_plan_payload: JsonMap,
    availability_payload: JsonMap,
    target_week: IsoWeek | None = None,
) -> list[WeekAvailabilityIssue]:
    """Validate a WEEK_PLAN agenda against concrete daily availability.

    The validator only hard-blocks deterministic violations. Missing
    availability rows are ignored, while explicit fixed-rest days, locked
    zero-availability days, and `hours_max` overflows are returned as issues.
    """

    availability_index = _availability_index(availability_payload)
    fixed_rest = _fixed_rest_days(availability_payload)
    issues: list[WeekAvailabilityIssue] = []
    data = _as_map(week_plan_payload.get("data"))
    for entry in _as_list(data.get("agenda")):
        row = _as_map(entry)
        row_day = str(row.get("day") or "").strip()[:3].title()
        row_date = str(row.get("date") or "").strip()
        if target_week is not None and row_date and not _date_in_iso_week(row_date, target_week):
            continue
        planned_seconds = _hhmm_to_seconds(str(row.get("planned_duration") or ""))
        planned_kj = _to_float(row.get("planned_kj"))
        workout_id = row.get("workout_id")
        has_workout = workout_id not in (None, "")
        rest_key_match = row_day in fixed_rest or row_date in fixed_rest
        issue_day = row_day or "UNKNOWN"
        issue_date = row_date or "-"
        if rest_key_match and (planned_seconds > 0 or planned_kj > 0 or has_workout):
            issues.append(
                WeekAvailabilityIssue(
                    issue_day,
                    issue_date,
                    "fixed rest day must have planned_duration 00:00, planned_kj 0, and workout_id null.",
                )
            )
            continue
        availability_row = availability_index.get(row_day) or availability_index.get(row_date)
        if not availability_row:
            continue
        max_hours = _availability_hours_max(availability_row)
        if max_hours is not None and planned_seconds > int(round(max_hours * 3600)):
            issues.append(
                WeekAvailabilityIssue(
                    issue_day,
                    issue_date,
                    f"planned_duration {_seconds_to_hhmm(planned_seconds)} exceeds availability hours_max {_hours_to_hhmm(max_hours)}.",
                )
            )
            continue
        if _is_locked_zero_availability(availability_row) and (planned_seconds > 0 or planned_kj > 0 or has_workout):
            issues.append(
                WeekAvailabilityIssue(
                    issue_day,
                    issue_date,
                    "locked zero-availability day must not carry planned load or a workout.",
                )
            )
    return issues


def _availability_index(availability_payload: JsonMap) -> dict[str, JsonMap]:
    index: dict[str, JsonMap] = {}
    data = _as_map(availability_payload.get("data"))
    for row in _as_list(data.get("availability_table")):
        row_map = _as_map(row)
        day = str(row_map.get("day") or row_map.get("weekday") or "").strip()[:3].title()
        row_date = str(row_map.get("date") or "").strip()
        if day:
            index[day] = row_map
        if row_date:
            index[row_date] = row_map
    return index


def _fixed_rest_days(availability_payload: JsonMap) -> set[str]:
    data = _as_map(availability_payload.get("data"))
    out: set[str] = set()
    for item in _as_list(data.get("fixed_rest_days")):
        text = str(item).strip()
        if not text:
            continue
        out.add(text)
        out.add(text[:3].title())
    return out


def _availability_hours_max(row: JsonMap) -> float | None:
    return _to_optional_float(row.get("hours_max") or row.get("max_hours") or row.get("max"))


def _is_locked_zero_availability(row: JsonMap) -> bool:
    if row.get("locked") is not True:
        return False
    values = [
        _to_optional_float(row.get("hours_min") or row.get("min_hours") or row.get("min")),
        _to_optional_float(row.get("hours_typical") or row.get("typical_hours") or row.get("typical")),
        _to_optional_float(row.get("hours_max") or row.get("max_hours") or row.get("max")),
    ]
    numeric = [value for value in values if value is not None]
    return bool(numeric) and all(value <= 0 for value in numeric)


def _date_in_iso_week(raw_date: str, target_week: IsoWeek) -> bool:
    try:
        parsed = date.fromisoformat(raw_date)
    except ValueError:
        return True
    iso_year, iso_week, _weekday = parsed.isocalendar()
    return iso_year == target_week.year and iso_week == target_week.week


def _hhmm_to_seconds(value: str) -> int:
    parts = value.split(":")
    if len(parts) != 2:
        return 0
    try:
        hours, minutes = [int(part) for part in parts]
    except ValueError:
        return 0
    return max(0, (hours * 60 + minutes) * 60)


def _seconds_to_hhmm(seconds: int) -> str:
    minutes = int(round(seconds / 60))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _hours_to_hhmm(hours: float) -> str:
    return _seconds_to_hhmm(int(round(hours * 3600)))


def _to_float(value: object) -> float:
    parsed = _to_optional_float(value)
    return parsed if parsed is not None else 0.0


def _to_optional_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []
