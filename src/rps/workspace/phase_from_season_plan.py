"""Resolve phase ranges from season plan phase definitions."""

from __future__ import annotations

from typing import Any

from rps.workspace.iso_helpers import (
    IsoWeek,
    IsoWeekRange,
    range_contains,
    week_index,
)
from rps.workspace.iso_helpers import (
    parse_iso_week_range as _parse_iso_week_range,
)
from rps.workspace.phase_resolution import add_weeks, iso_week_monday


def parse_iso_week_range(obj: Any) -> IsoWeekRange:
    """Parse a schema-style iso_week_range into an IsoWeekRange."""
    parsed = _parse_iso_week_range(obj)
    if not parsed:
        raise ValueError("Invalid iso_week_range format")
    return parsed


def resolve_current_phase(
    season_plan_envelope: dict[str, Any],
    target: IsoWeek,
) -> dict[str, Any] | None:
    """Return the phase entry that covers the target week, if any."""
    phases = season_plan_envelope.get("data", {}).get("phases", [])
    for phase in phases:
        range_obj = phase.get("iso_week_range")
        if not range_obj:
            continue
        phase_range = parse_iso_week_range(range_obj)
        if range_contains(phase_range, target):
            return phase
    return None


def resolve_phase_window_from_phase(
    phase_range: IsoWeekRange,
    target: IsoWeek,
    phase_len: int = 4,
) -> IsoWeekRange:
    """Resolve a phase range anchored to the phase start and clamped to its end."""
    if phase_len < 1:
        raise ValueError("phase_len must be >= 1")

    phase_start = iso_week_monday(phase_range.start.year, phase_range.start.week)
    target_start = iso_week_monday(target.year, target.week)
    delta_weeks = (target_start - phase_start).days // 7
    if delta_weeks < 0:
        delta_weeks = 0

    phase_index = delta_weeks // phase_len
    start = add_weeks(phase_range.start, phase_index * phase_len)
    end = add_weeks(start, phase_len - 1)

    if week_index(end) > week_index(phase_range.end):
        end = phase_range.end

    return IsoWeekRange(start=start, end=end)


def resolve_current_phase_window_from_season_plan(
    season_plan_envelope: dict[str, Any],
    target: IsoWeek,
    phase_len: int = 4,
) -> IsoWeekRange:
    """Resolve a phase-aligned window for a target week using season plan data."""
    phase = resolve_current_phase(season_plan_envelope, target)
    if not phase:
        raise ValueError(
            f"No season plan phase covers target week {target.year:04d}-{target.week:02d}"
        )
    phase_range = parse_iso_week_range(phase["iso_week_range"])
    return resolve_phase_window_from_phase(phase_range, target, phase_len=phase_len)
