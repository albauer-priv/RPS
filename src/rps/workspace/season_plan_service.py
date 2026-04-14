"""Utilities for season plan phase lookup and phase window derivation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rps.workspace.iso_helpers import IsoWeek, IsoWeekRange, week_index
from rps.workspace.phase_from_season_plan import (
    parse_iso_week_range,
    resolve_current_phase,
    resolve_current_phase_window_from_season_plan,
)


@dataclass(frozen=True)
class SeasonPlanPhaseInfo:
    """Normalized view of a season plan phase entry."""
    phase_id: str
    phase_name: str
    phase_type: str
    phase_range: IsoWeekRange
    raw: dict[str, Any]


def phase_context_summary(
    season_plan_envelope: dict[str, Any],
    target: IsoWeek,
) -> dict[str, Any] | None:
    """Return a compact phase context payload for a target ISO week."""
    info = resolve_season_plan_phase_info(season_plan_envelope, target)
    if not info:
        return None

    phase_name = info.phase_name or str(info.raw.get("name", ""))
    phase_type = info.phase_type or str(info.raw.get("phase_type", ""))
    phase_focus = phase_name or phase_type or info.phase_id or "Unknown"
    phase_week = max(1, week_index(target) - week_index(info.phase_range.start) + 1)

    return {
        "phase_id": info.phase_id,
        "phase_name": phase_name,
        "phase_type": phase_type,
        "phase_focus": phase_focus,
        "phase_week": phase_week,
        "iso_week_range": {
            "start": {"year": info.phase_range.start.year, "week": info.phase_range.start.week},
            "end": {"year": info.phase_range.end.year, "week": info.phase_range.end.week},
        },
        "range_key": info.phase_range.key,
    }


def resolve_season_plan_phase_info(
    season_plan_envelope: dict[str, Any],
    target: IsoWeek,
) -> SeasonPlanPhaseInfo | None:
    """Return season plan phase info for the target week if available."""
    phase = resolve_current_phase(season_plan_envelope, target)
    if not phase:
        return None

    phase_range = parse_iso_week_range(phase["iso_week_range"])
    return SeasonPlanPhaseInfo(
        phase_id=str(phase.get("phase_id", "")),
        phase_name=str(phase.get("phase_name", "")),
        phase_type=str(phase.get("phase_type", "")),
        phase_range=phase_range,
        raw=phase,
    )


def resolve_phase_range_from_season_plan(
    season_plan_envelope: dict[str, Any],
    target: IsoWeek,
    phase_len: int = 4,
) -> IsoWeekRange:
    """Resolve a phase range aligned to the season plan phase."""
    return resolve_current_phase_window_from_season_plan(
        season_plan_envelope,
        target,
        phase_len=phase_len,
    )
