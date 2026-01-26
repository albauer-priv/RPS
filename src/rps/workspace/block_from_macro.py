"""Resolve meso block ranges from macro phase definitions."""

from __future__ import annotations

from typing import Any, Optional

from rps.workspace.block_resolution import add_weeks, iso_week_monday
from rps.workspace.iso_helpers import (
    IsoWeek,
    IsoWeekRange,
    parse_iso_week_range as _parse_iso_week_range,
    range_contains,
    week_index,
)


def parse_iso_week_range(obj: Any) -> IsoWeekRange:
    """Parse a schema-style iso_week_range into an IsoWeekRange."""
    parsed = _parse_iso_week_range(obj)
    if not parsed:
        raise ValueError("Invalid iso_week_range format")
    return parsed


def resolve_current_phase(
    macro_overview_envelope: dict[str, Any],
    target: IsoWeek,
) -> Optional[dict[str, Any]]:
    """Return the phase entry that covers the target week, if any."""
    phases = macro_overview_envelope.get("data", {}).get("phases", [])
    for phase in phases:
        range_obj = phase.get("iso_week_range")
        if not range_obj:
            continue
        phase_range = parse_iso_week_range(range_obj)
        if range_contains(phase_range, target):
            return phase
    return None


def resolve_block_from_phase(
    phase_range: IsoWeekRange,
    target: IsoWeek,
    block_len: int = 4,
) -> IsoWeekRange:
    """Resolve a block range anchored to the phase start and clamped to its end."""
    if block_len < 1:
        raise ValueError("block_len must be >= 1")

    phase_start = iso_week_monday(phase_range.start.year, phase_range.start.week)
    target_start = iso_week_monday(target.year, target.week)
    delta_weeks = (target_start - phase_start).days // 7
    if delta_weeks < 0:
        delta_weeks = 0

    block_index = delta_weeks // block_len
    start = add_weeks(phase_range.start, block_index * block_len)
    end = add_weeks(start, block_len - 1)

    if week_index(end) > week_index(phase_range.end):
        end = phase_range.end

    return IsoWeekRange(start=start, end=end)


def resolve_current_block_from_macro(
    macro_overview_envelope: dict[str, Any],
    target: IsoWeek,
    block_len: int = 4,
) -> IsoWeekRange:
    """Resolve a phase-aligned block for a target week using macro overview data."""
    phase = resolve_current_phase(macro_overview_envelope, target)
    if not phase:
        raise ValueError(
            f"No macro phase covers target week {target.year:04d}-{target.week:02d}"
        )
    phase_range = parse_iso_week_range(phase["iso_week_range"])
    return resolve_block_from_phase(phase_range, target, block_len=block_len)
