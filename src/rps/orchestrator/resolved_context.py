"""Helpers for resolving deterministic planner context before agent calls."""

from __future__ import annotations

from datetime import date

from rps.workspace.iso_helpers import IsoWeek, IsoWeekRange, week_index
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.phase_resolution import date_to_iso_week
from rps.workspace.season_plan_service import SeasonPlanPhaseInfo
from rps.workspace.types import ArtifactType


def build_resolved_kpi_context_block(store: LocalArtifactStore, athlete_id: str) -> str:
    """Build a deterministic KPI context block from latest KPI profile + selection."""
    try:
        selection = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
    except Exception:
        selection = None
    try:
        profile = store.load_latest(athlete_id, ArtifactType.KPI_PROFILE)
    except Exception:
        profile = None

    selection_data = selection.get("data") if isinstance(selection, dict) else None
    selection_map = selection_data if isinstance(selection_data, dict) else {}
    selected = selection_map.get("kpi_moving_time_rate_guidance_selection")

    profile_data = profile.get("data") if isinstance(profile, dict) else None
    durability = (profile_data or {}).get("durability") if isinstance(profile_data, dict) else {}
    if not isinstance(durability, dict):
        durability = {}
    mt_guidance = durability.get("moving_time_rate_guidance") or {}
    if not isinstance(mt_guidance, dict):
        mt_guidance = {}
    bands = mt_guidance.get("bands") or []
    if not isinstance(bands, list):
        bands = []

    lines: list[str] = []
    if isinstance(selected, dict):
        segment = selected.get("segment")
        w_per_kg = selected.get("w_per_kg") or {}
        kj_per_kg = selected.get("kj_per_kg_per_hour") or {}
        if (
            segment
            and isinstance(w_per_kg, dict)
            and isinstance(kj_per_kg, dict)
            and "min" in w_per_kg
            and "max" in w_per_kg
            and "min" in kj_per_kg
            and "max" in kj_per_kg
        ):
            lines.extend(
                [
                    "**Resolved KPI Context**",
                    "Use these resolved KPI values directly; do not search, infer, or reinterpret KPI ranges when they are provided here.",
                    (
                        f"selected_kpi_rate_band_selector: {segment} "
                        f"(w_per_kg {w_per_kg.get('min')} - {w_per_kg.get('max')}, "
                        f"kj_per_kg_per_hour {kj_per_kg.get('min')} - {kj_per_kg.get('max')})"
                    ),
                ]
            )

    derived_from = mt_guidance.get("derived_from")
    notes = mt_guidance.get("notes")
    available_lines: list[str] = []
    for band in bands:
        if not isinstance(band, dict):
            continue
        segment = band.get("segment")
        w_per_kg = band.get("w_per_kg") or {}
        kj_per_kg = band.get("kj_per_kg_per_hour") or {}
        basis = band.get("basis")
        if (
            not segment
            or not isinstance(w_per_kg, dict)
            or not isinstance(kj_per_kg, dict)
            or "min" not in w_per_kg
            or "max" not in w_per_kg
            or "min" not in kj_per_kg
            or "max" not in kj_per_kg
        ):
            continue
        basis_text = f", basis {basis}" if isinstance(basis, str) and basis else ""
        available_lines.append(
            f"- {segment}: w_per_kg {w_per_kg.get('min')} - {w_per_kg.get('max')}, "
            f"kj_per_kg_per_hour {kj_per_kg.get('min')} - {kj_per_kg.get('max')}{basis_text}"
        )

    if available_lines:
        if not lines:
            lines.append("**Resolved KPI Context**")
            lines.append(
                "Use these resolved KPI values directly; do not search, infer, or reinterpret KPI ranges when they are provided here."
            )
        if isinstance(derived_from, str) and derived_from:
            lines.append(f"kpi_profile_moving_time_rate_guidance.derived_from: {derived_from}")
        if isinstance(notes, str) and notes:
            lines.append(f"kpi_profile_moving_time_rate_guidance.notes: {notes}")
        lines.append("kpi_profile_moving_time_rate_guidance.available_bands:")
        lines.extend(available_lines)

    return "\n".join(lines) + ("\n" if lines else "")


def build_resolved_availability_context_block(store: LocalArtifactStore, athlete_id: str) -> str:
    """Build a deterministic availability summary block from the latest availability artefact."""
    try:
        availability = store.load_latest(athlete_id, ArtifactType.AVAILABILITY)
    except Exception:
        return ""
    data = availability.get("data") if isinstance(availability, dict) else None
    availability_data = data if isinstance(data, dict) else {}
    weekly_hours = availability_data.get("weekly_hours") or {}
    table = availability_data.get("availability_table") or []
    fixed_rest_days = availability_data.get("fixed_rest_days") or []

    if not isinstance(weekly_hours, dict):
        weekly_hours = {}
    if not isinstance(table, list):
        table = []
    if not isinstance(fixed_rest_days, list):
        fixed_rest_days = []

    lines: list[str] = []
    if all(key in weekly_hours for key in ("min", "typical", "max")):
        lines.extend(
            [
                "**Resolved Availability Context**",
                "Use these resolved availability facts directly; do not infer weekly totals or fixed rest days from raw rows when they are provided here.",
                (
                    f"weekly_hours: min {weekly_hours.get('min')}, "
                    f"typical {weekly_hours.get('typical')}, max {weekly_hours.get('max')}"
                ),
            ]
        )
    if fixed_rest_days:
        if not lines:
            lines.extend(
                [
                    "**Resolved Availability Context**",
                    "Use these resolved availability facts directly; do not infer weekly totals or fixed rest days from raw rows when they are provided here.",
                ]
            )
        lines.append("fixed_rest_days: " + ", ".join(str(day) for day in fixed_rest_days))

    day_lines: list[str] = []
    for row in table:
        if not isinstance(row, dict):
            continue
        weekday = row.get("weekday")
        if not isinstance(weekday, str) or not weekday:
            continue
        hours_typical = row.get("hours_typical")
        locked = bool(row.get("locked"))
        indoor_possible = row.get("indoor_possible")
        travel_risk = row.get("travel_risk")
        if not locked and not isinstance(hours_typical, (int, float)):
            continue
        hours_typical_value = float(hours_typical) if isinstance(hours_typical, (int, float)) else 0.0
        if not locked and hours_typical_value == 0 and travel_risk == "LOW" and indoor_possible is not False:
            continue
        day_lines.append(
            f"- {weekday}: hours_typical {row.get('hours_typical')}, "
            f"hours_min {row.get('hours_min')}, hours_max {row.get('hours_max')}, "
            f"indoor_possible {row.get('indoor_possible')}, travel_risk {row.get('travel_risk')}, "
            f"locked {row.get('locked')}"
        )

    if day_lines:
        if not lines:
            lines.extend(
                [
                    "**Resolved Availability Context**",
                    "Use these resolved availability facts directly; do not infer weekly totals or fixed rest days from raw rows when they are provided here.",
                ]
            )
        lines.append("availability_table_summary:")
        lines.extend(day_lines)

    return "\n".join(lines) + ("\n" if lines else "")


def build_resolved_phase_context_block(
    target_week: IsoWeek,
    phase_info: SeasonPlanPhaseInfo | None,
    *,
    phase_name_override: str | None = None,
    phase_type_override: str | None = None,
) -> str:
    """Build a deterministic phase summary block for target-week planning."""
    if phase_info is None:
        return ""
    phase_name = phase_name_override or phase_info.phase_name or str(phase_info.raw.get("name", ""))
    phase_type = phase_type_override or phase_info.phase_type or str(phase_info.raw.get("cycle", ""))
    phase_week = max(1, week_index(target_week) - week_index(phase_info.phase_range.start) + 1)
    return (
        "**Resolved Phase Context**\n"
        "Use these phase facts directly; do not reinterpret phase identity or range from raw season-plan text when they are provided here.\n"
        f"target_iso_week: {target_week.year:04d}-{target_week.week:02d}\n"
        f"phase_id: {phase_info.phase_id}\n"
        f"phase_name: {phase_name}\n"
        f"phase_type: {phase_type}\n"
        f"phase_iso_week_range: {phase_info.phase_range.key}\n"
        f"phase_week_index: {phase_week}\n"
    )


def build_resolved_planning_events_context_block(
    store: LocalArtifactStore,
    athlete_id: str,
    target_week: IsoWeek,
    *,
    phase_range: IsoWeekRange | None = None,
) -> str:
    """Build a deterministic planning-event summary for the target week and optional phase range."""
    try:
        planning_events = store.load_latest(athlete_id, ArtifactType.PLANNING_EVENTS)
    except Exception:
        return ""
    data = planning_events.get("data") if isinstance(planning_events, dict) else None
    event_data = data if isinstance(data, dict) else {}
    events = event_data.get("events") or []
    if not isinstance(events, list):
        return ""

    def _event_week_key(event: dict[str, object]) -> str | None:
        raw_date = event.get("date")
        if not isinstance(raw_date, str):
            return None
        try:
            event_week = date_to_iso_week(date.fromisoformat(raw_date))
        except ValueError:
            return None
        return f"{event_week.year:04d}-{event_week.week:02d}"

    def _event_line(event: dict[str, object]) -> str | None:
        raw_date = event.get("date")
        event_type = event.get("type")
        event_name = event.get("event_name")
        goal = event.get("goal")
        week_key = _event_week_key(event)
        if not isinstance(raw_date, str) or not isinstance(event_type, str) or not week_key:
            return None
        name_part = f" {event_name}" if isinstance(event_name, str) and event_name else ""
        goal_part = f", goal {goal}" if isinstance(goal, str) and goal else ""
        return f"- {raw_date} ({week_key}) {event_type}{name_part}{goal_part}"

    target_key = f"{target_week.year:04d}-{target_week.week:02d}"
    target_lines: list[str] = []
    phase_lines: list[str] = []
    all_lines: list[str] = []
    for raw in events:
        if not isinstance(raw, dict):
            continue
        line = _event_line(raw)
        week_key = _event_week_key(raw)
        if not line or not week_key:
            continue
        all_lines.append(line)
        if week_key == target_key:
            target_lines.append(line)
        if phase_range:
            event_week = date_to_iso_week(date.fromisoformat(str(raw.get("date"))))
            if week_index(phase_range.start) <= week_index(event_week) <= week_index(phase_range.end):
                phase_lines.append(line)

    if not all_lines:
        return ""

    lines = [
        "**Resolved Planning Event Context**",
        "Use these event facts directly; do not recompute target-week or phase-range event membership when they are provided here.",
    ]
    if target_lines:
        lines.append(f"target_week_events ({target_key}):")
        lines.extend(target_lines)
    else:
        lines.append(f"target_week_events ({target_key}): none")
    if phase_range:
        if phase_lines:
            lines.append(f"phase_range_events ({phase_range.key}):")
            lines.extend(phase_lines)
        else:
            lines.append(f"phase_range_events ({phase_range.key}): none")
    lines.append("all_planned_events:")
    lines.extend(all_lines)
    return "\n".join(lines) + "\n"
