"""Utilities for season plan phase lookup and block derivation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from rps.workspace.block_from_season_plan import (
    parse_iso_week_range,
    resolve_current_block_from_season_plan,
    resolve_current_phase,
)
from rps.workspace.iso_helpers import IsoWeek, IsoWeekRange


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
) -> Optional[SeasonPlanPhaseInfo]:
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


def resolve_block_range_from_season_plan(
    season_plan_envelope: dict[str, Any],
    target: IsoWeek,
    block_len: int = 4,
) -> IsoWeekRange:
    """Resolve a block range aligned to the season plan phase."""
    return resolve_current_block_from_season_plan(
        season_plan_envelope,
        target,
        block_len=block_len,
    )
