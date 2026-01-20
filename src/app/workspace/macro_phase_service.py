"""Utilities for macro phase lookup and block derivation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.workspace.block_from_macro import (
    parse_iso_week_range,
    resolve_current_block_from_macro,
    resolve_current_phase,
)
from app.workspace.iso_helpers import IsoWeek, IsoWeekRange


@dataclass(frozen=True)
class MacroPhaseInfo:
    """Normalized view of a macro phase entry."""
    phase_id: str
    phase_name: str
    phase_type: str
    phase_range: IsoWeekRange
    raw: dict[str, Any]


def resolve_macro_phase_info(
    macro_overview_envelope: dict[str, Any],
    target: IsoWeek,
) -> Optional[MacroPhaseInfo]:
    """Return macro phase info for the target week if available."""
    phase = resolve_current_phase(macro_overview_envelope, target)
    if not phase:
        return None

    phase_range = parse_iso_week_range(phase["iso_week_range"])
    return MacroPhaseInfo(
        phase_id=str(phase.get("phase_id", "")),
        phase_name=str(phase.get("phase_name", "")),
        phase_type=str(phase.get("phase_type", "")),
        phase_range=phase_range,
        raw=phase,
    )


def resolve_block_range_from_macro(
    macro_overview_envelope: dict[str, Any],
    target: IsoWeek,
    block_len: int = 4,
) -> IsoWeekRange:
    """Resolve a block range aligned to the macro phase."""
    return resolve_current_block_from_macro(macro_overview_envelope, target, block_len=block_len)
