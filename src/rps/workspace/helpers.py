"""General helper utilities for week and block calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Tuple


def resolve_current_week(d: date | datetime) -> str:
    """Return ISO week key: YYYY-WW."""
    if isinstance(d, datetime):
        d = d.date()
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year:04d}-{iso_week:02d}"


def _parse_week_key(week_key: str) -> Tuple[int, int]:
    """Parse a YYYY-WW week key into (year, week)."""
    year_s, week_s = week_key.split("-")
    return int(year_s), int(week_s)


def _iso_week_monday(iso_year: int, iso_week: int) -> date:
    """Return the Monday date for an ISO week."""
    jan4 = date(iso_year, 1, 4)
    jan4_monday = jan4 - timedelta(days=jan4.isoweekday() - 1)
    return jan4_monday + timedelta(weeks=iso_week - 1)


def _week_key_add_weeks(week_key: str, weeks: int) -> str:
    """Return a week key shifted by a number of weeks."""
    year, week = _parse_week_key(week_key)
    monday = _iso_week_monday(year, week)
    target = monday + timedelta(weeks=weeks)
    return resolve_current_week(target)


@dataclass(frozen=True)
class BlockRange:
    """Simple block range container with a precomputed key."""
    start_week: str
    end_week: str
    range_key: str


def resolve_current_block(week_key: str, block_length_weeks: int = 4) -> BlockRange:
    """Return a block range starting at week_key."""
    if block_length_weeks < 1:
        raise ValueError("block_length_weeks must be >= 1")

    start_week = week_key
    end_week = _week_key_add_weeks(start_week, block_length_weeks - 1)
    return BlockRange(
        start_week=start_week,
        end_week=end_week,
        range_key=f"{start_week}--{end_week}",
    )


def upstream_ref(artifact_type: str, version_key: str) -> str:
    """Build a stable upstream reference token."""
    return f"{artifact_type}:{version_key}"
