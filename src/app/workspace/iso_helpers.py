"""ISO week helper structures and utilities."""

from __future__ import annotations

from dataclasses import dataclass


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


def envelope_week(envelope: dict) -> IsoWeek | None:
    """Extract iso_week from an artifact envelope."""
    meta = envelope.get("meta", {})
    iso_week = meta.get("iso_week")
    if not iso_week:
        return None
    return IsoWeek(int(iso_week["year"]), int(iso_week["week"]))


def envelope_week_range(envelope: dict) -> IsoWeekRange | None:
    """Extract iso_week_range from an artifact envelope."""
    meta = envelope.get("meta", {})
    range_spec = meta.get("iso_week_range")
    if not range_spec:
        return None
    start = range_spec["start"]
    end = range_spec["end"]
    return IsoWeekRange(
        start=IsoWeek(int(start["year"]), int(start["week"])),
        end=IsoWeek(int(end["year"]), int(end["week"])),
    )
