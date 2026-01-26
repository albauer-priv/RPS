"""Helpers for aligned ISO-week block ranges."""

from __future__ import annotations

from datetime import date, timedelta

from rps.workspace.iso_helpers import IsoWeek, IsoWeekRange


def iso_week_monday(year: int, week: int) -> date:
    """Return the Monday date for an ISO week."""
    jan4 = date(year, 1, 4)
    jan4_monday = jan4 - timedelta(days=jan4.isoweekday() - 1)
    return jan4_monday + timedelta(weeks=week - 1)


def date_to_iso_week(value: date) -> IsoWeek:
    """Convert a date to an ISO week structure."""
    year, week, _ = value.isocalendar()
    return IsoWeek(year=year, week=week)


def add_weeks(iso: IsoWeek, weeks: int) -> IsoWeek:
    """Add a number of weeks to an ISO week."""
    monday = iso_week_monday(iso.year, iso.week)
    target = monday + timedelta(weeks=weeks)
    return date_to_iso_week(target)


def resolve_block_for_target_week(
    target: IsoWeek,
    block_len: int = 4,
    anchor: IsoWeek | None = None,
) -> IsoWeekRange:
    """Resolve an aligned block range that contains the target week."""
    if block_len < 1:
        raise ValueError("block_len must be >= 1")

    if anchor:
        anchor_m = iso_week_monday(anchor.year, anchor.week)
        target_m = iso_week_monday(target.year, target.week)
        delta_weeks = (target_m - anchor_m).days // 7
        offset = delta_weeks % block_len
        start = add_weeks(target, -offset)
    else:
        start_week = target.week - ((target.week - 1) % block_len)
        start = IsoWeek(year=target.year, week=start_week)

    end = add_weeks(start, block_len - 1)
    return IsoWeekRange(start=start, end=end)


def contains(range_spec: IsoWeekRange, week: IsoWeek) -> bool:
    """Return True if the week is within the range (inclusive)."""
    def idx(value: IsoWeek) -> int:
        """Return a sortable index for ISO week comparisons."""
        return value.year * 60 + value.week

    return idx(range_spec.start) <= idx(week) <= idx(range_spec.end)
