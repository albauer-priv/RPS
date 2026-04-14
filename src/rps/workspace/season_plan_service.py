"""Utilities for season plan phase lookup and phase window derivation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rps.workspace.iso_helpers import IsoWeek, IsoWeekRange
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
