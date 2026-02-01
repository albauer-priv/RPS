"""ISO week helper structures and utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any


@dataclass(frozen=True)
class IsoWeek:
    """ISO week identifier."""

    year: int
    week: int


@dataclass(frozen=True)
class IsoWeekRange:
    """Inclusive ISO week range."""

    start: IsoWeek
    end: IsoWeek

    @property
    def range_key(self) -> str:
        """Return the canonical YYYY-WW--YYYY-WW range key."""
        return f"{self.start.year:04d}-{self.start.week:02d}--{self.end.year:04d}-{self.end.week:02d}"

    @property
    def key(self) -> str:
        """Alias for range_key."""
        return self.range_key


def week_index(week: IsoWeek) -> int:
    """Return a comparable index for ISO weeks."""
    return week.year * 60 + week.week


def range_contains(range_spec: IsoWeekRange, week: IsoWeek) -> bool:
    """Return True if a week is within a range (inclusive)."""
    return week_index(range_spec.start) <= week_index(week) <= week_index(range_spec.end)


def previous_iso_week(week: IsoWeek) -> IsoWeek:
    """Return the ISO week immediately before the given one."""
    monday = date.fromisocalendar(week.year, week.week, 1)
    prev_monday = monday - timedelta(days=7)
    iso_year, iso_week, _ = prev_monday.isocalendar()
    return IsoWeek(year=iso_year, week=iso_week)


def next_iso_week(week: IsoWeek) -> IsoWeek:
    """Return the ISO week immediately after the given one."""
    monday = date.fromisocalendar(week.year, week.week, 1)
    next_monday = monday + timedelta(days=7)
    iso_year, iso_week, _ = next_monday.isocalendar()
    return IsoWeek(year=iso_year, week=iso_week)


def parse_iso_week(value: Any) -> IsoWeek | None:
    """Parse a string or mapping into an IsoWeek."""
    if isinstance(value, dict) and "year" in value and "week" in value:
        return IsoWeek(int(value["year"]), int(value["week"]))
    if isinstance(value, str):
        key = value.strip().split("__", 1)[0]
        parts = key.split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return IsoWeek(int(parts[0]), int(parts[1]))
    return None


def parse_iso_week_range(value: Any) -> IsoWeekRange | None:
    """Parse a string or mapping into an IsoWeekRange."""
    if isinstance(value, dict):
        start = value.get("start") or value.get("from")
        end = value.get("end") or value.get("to")
        start_week = parse_iso_week(start)
        end_week = parse_iso_week(end)
        if start_week and end_week:
            return IsoWeekRange(start=start_week, end=end_week)
        return None

    if isinstance(value, str):
        value = value.strip().split("__", 1)[0]
        parts = value.split("--")
        if len(parts) != 2:
            return None
        start = parse_iso_week(parts[0])
        end_part = parts[1].split("+", 1)[0]
        end = parse_iso_week(end_part)
        if start and end:
            return IsoWeekRange(start=start, end=end)
    return None


def envelope_week(envelope: dict) -> IsoWeek | None:
    """Extract iso_week from an artifact envelope."""
    meta = envelope.get("meta", {})
    iso_week = meta.get("iso_week")
    if not iso_week:
        return None
    return parse_iso_week(iso_week)


def envelope_week_range(envelope: dict) -> IsoWeekRange | None:
    """Extract iso_week_range from an artifact envelope."""
    meta = envelope.get("meta", {})
    range_spec = meta.get("iso_week_range")
    if not range_spec:
        return None
    return parse_iso_week_range(range_spec)
