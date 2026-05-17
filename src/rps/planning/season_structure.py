"""Deterministic season-structure context derived from selected scenarios."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.phase_resolution import date_to_iso_week

JsonMap = dict[str, Any]
CADENCE_PHASE_LENGTHS = {"2:1": 3, "3:1": 4, "2:1:1": 4}
MIN_SHORTENED_PHASE_LENGTH = 2


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _week_key(week: IsoWeek) -> str:
    return f"{week.year:04d}-{week.week:02d}"


def _next_week(week: IsoWeek) -> IsoWeek:
    monday = date.fromisocalendar(week.year, week.week, 1)
    next_monday = monday + timedelta(days=7)
    iso_year, iso_week, _ = next_monday.isocalendar()
    return IsoWeek(iso_year, iso_week)


def _add_weeks(week: IsoWeek, offset: int) -> IsoWeek:
    cursor = week
    for _ in range(max(0, offset)):
        cursor = _next_week(cursor)
    return cursor


def _phase_plan_math(planning_horizon_weeks: int, phase_length_weeks: int) -> JsonMap:
    phase_length = max(1, phase_length_weeks)
    phase_count = (max(1, planning_horizon_weeks) + phase_length - 1) // phase_length
    shortening_budget = max(0, (phase_count * phase_length) - max(1, planning_horizon_weeks))
    if shortening_budget == 0:
        return {
            "phase_count_expected": phase_count,
            "full_phases": phase_count,
            "shortening_budget_weeks": 0,
            "max_shortened_phases": 0,
            "shortened_phases": [],
        }
    shortened_length = max(MIN_SHORTENED_PHASE_LENGTH, phase_length - shortening_budget)
    if shortened_length >= phase_length:
        shortened_length = phase_length
    return {
        "phase_count_expected": phase_count,
        "full_phases": max(0, phase_count - 1),
        "shortening_budget_weeks": phase_length - shortened_length,
        "max_shortened_phases": 1,
        "shortened_phases": [{"len": shortened_length, "count": 1}],
    }


def build_cadence_options_context(*, planning_horizon_context: JsonMap) -> JsonMap:
    """Return deterministic phase math for supported cadence patterns."""

    horizon = _as_int(planning_horizon_context.get("inclusive_planning_horizon_weeks"))
    if horizon is None or horizon <= 0:
        return {}
    options: list[JsonMap] = []
    for cadence, phase_length in CADENCE_PHASE_LENGTHS.items():
        math = _phase_plan_math(horizon, phase_length)
        options.append(
            {
                "deload_cadence": cadence,
                "phase_length_weeks": phase_length,
                **math,
            }
        )
    return {
        "planning_horizon_weeks": horizon,
        "season_iso_week_range": planning_horizon_context.get("season_iso_week_range"),
        "options": options,
    }


def render_cadence_options_block(context: JsonMap) -> str:
    """Render deterministic cadence options for Season Scenario prompts."""

    if not context:
        return ""
    lines = [
        "**Deterministic Cadence Options Context**",
        "These cadence options are code-derived from the planning horizon. Use them when filling scenario_guidance; do not invent alternate phase-count math.",
        f"planning_horizon_weeks: {context.get('planning_horizon_weeks')}",
        f"season_iso_week_range: {context.get('season_iso_week_range')}",
    ]
    for option in _as_list(context.get("options")):
        option_map = _as_map(option)
        lines.append(
            "- "
            f"cadence {option_map.get('deload_cadence')}: "
            f"phase_length_weeks {option_map.get('phase_length_weeks')}, "
            f"phase_count_expected {option_map.get('phase_count_expected')}, "
            f"full_phases {option_map.get('full_phases')}, "
            f"shortening_budget_weeks {option_map.get('shortening_budget_weeks')}, "
            f"shortened_phases {option_map.get('shortened_phases') or 'none'}"
        )
    return "\n".join(lines) + "\n"


def build_selected_scenario_structure_context(
    *,
    season_scenarios_payload: JsonMap | None,
    selection_payload: JsonMap | None = None,
    selected_scenario_id: str | None = None,
) -> JsonMap:
    """Return phase-count/cadence planning math for the selected scenario."""

    scenarios_data = _as_map((season_scenarios_payload or {}).get("data"))
    selection_data = _as_map((selection_payload or {}).get("data"))
    selected_id = str(selected_scenario_id or selection_data.get("selected_scenario_id") or "").strip().upper()
    if selected_id not in {"A", "B", "C"}:
        return {}

    selected_scenario: JsonMap | None = None
    for scenario in _as_list(scenarios_data.get("scenarios")):
        scenario_map = _as_map(scenario)
        if str(scenario_map.get("scenario_id") or "").strip().upper() == selected_id:
            selected_scenario = scenario_map
            break
    if not selected_scenario:
        return {}

    guidance = _as_map(selected_scenario.get("scenario_guidance"))
    phase_summary = _as_map(guidance.get("phase_plan_summary"))
    shortened = [_as_map(item) for item in _as_list(phase_summary.get("shortened_phases"))]
    phase_length = _as_int(guidance.get("phase_length_weeks"))
    full_phases = _as_int(phase_summary.get("full_phases"))
    shortened_week_count = sum(
        (_as_int(item.get("len")) or 0) * (_as_int(item.get("count")) or 0)
        for item in shortened
    )
    full_week_count = (full_phases or 0) * (phase_length or 0)
    reconstructed_weeks = full_week_count + shortened_week_count

    return {
        "selected_scenario_id": selected_id,
        "scenario_name": selected_scenario.get("name"),
        "planning_horizon_weeks": _as_int(scenarios_data.get("planning_horizon_weeks")),
        "deload_cadence": guidance.get("deload_cadence"),
        "phase_length_weeks": phase_length,
        "phase_count_expected": _as_int(guidance.get("phase_count_expected")),
        "full_phases": full_phases,
        "shortened_phases": shortened,
        "max_shortened_phases": _as_int(guidance.get("max_shortened_phases")),
        "shortening_budget_weeks": _as_int(guidance.get("shortening_budget_weeks")),
        "reconstructed_horizon_weeks": reconstructed_weeks if reconstructed_weeks > 0 else None,
        "consistent_with_horizon": (
            reconstructed_weeks == _as_int(scenarios_data.get("planning_horizon_weeks"))
            if reconstructed_weeks > 0 and _as_int(scenarios_data.get("planning_horizon_weeks")) is not None
            else None
        ),
        "event_alignment_notes": guidance.get("event_alignment_notes") or [],
        "risk_flags": guidance.get("risk_flags") or [],
    }


def render_selected_scenario_structure_block(context: JsonMap) -> str:
    """Render selected scenario phase math for Season planning prompts."""

    if not context:
        return ""
    lines = [
        "**Deterministic Selected Scenario Structure Context**",
        "These values are derived from the selected SEASON_SCENARIOS scenario. Use them as the planning-math reference for phase count, cadence, and shortened-phase handling; do not invent alternate phase-length math.",
        f"selected_scenario_id: {context.get('selected_scenario_id')}",
        f"scenario_name: {context.get('scenario_name')}",
        f"planning_horizon_weeks: {context.get('planning_horizon_weeks')}",
        f"deload_cadence: {context.get('deload_cadence')}",
        f"phase_length_weeks: {context.get('phase_length_weeks')}",
        f"phase_count_expected: {context.get('phase_count_expected')}",
        f"full_phases: {context.get('full_phases')}",
        f"shortening_budget_weeks: {context.get('shortening_budget_weeks')}",
        f"max_shortened_phases: {context.get('max_shortened_phases')}",
        f"reconstructed_horizon_weeks: {context.get('reconstructed_horizon_weeks')}",
        f"consistent_with_horizon: {context.get('consistent_with_horizon')}",
    ]
    shortened = [_as_map(item) for item in _as_list(context.get("shortened_phases"))]
    if shortened:
        lines.append("shortened_phases:")
        for item in shortened:
            lines.append(f"- len {item.get('len')}, count {item.get('count')}")
    else:
        lines.append("shortened_phases: none")
    for label in ("event_alignment_notes", "risk_flags"):
        values = [str(item) for item in _as_list(context.get(label)) if str(item).strip()]
        if values:
            lines.append(f"{label}:")
            lines.extend(f"- {value}" for value in values)
    return "\n".join(lines) + "\n"


def build_phase_slot_context(
    *,
    selected_structure_context: JsonMap,
    target_week: IsoWeek,
) -> JsonMap:
    """Build deterministic phase slots from selected scenario math."""

    phase_length = _as_int(selected_structure_context.get("phase_length_weeks"))
    full_phases = _as_int(selected_structure_context.get("full_phases")) or 0
    horizon = _as_int(selected_structure_context.get("planning_horizon_weeks"))
    if phase_length is None or phase_length <= 0 or horizon is None or horizon <= 0:
        return {}
    shortened_entries = [_as_map(item) for item in _as_list(selected_structure_context.get("shortened_phases"))]
    lengths: list[tuple[int, bool]] = []
    # Shorten the earliest low-authority slots first, preserving full final phases near the event.
    for item in shortened_entries:
        length = _as_int(item.get("len"))
        count = _as_int(item.get("count")) or 0
        if length is None or length <= 0:
            continue
        lengths.extend((length, True) for _ in range(count))
    lengths.extend((phase_length, False) for _ in range(full_phases))
    if not lengths:
        return {}

    slots: list[JsonMap] = []
    cursor = target_week
    covered_weeks = 0
    for idx, (length, is_shortened) in enumerate(lengths, start=1):
        start = cursor
        end = _add_weeks(start, max(0, length - 1))
        slots.append(
            {
                "phase_id": f"P{idx:02d}",
                "iso_week_range": f"{_week_key(start)}--{_week_key(end)}",
                "length_weeks": length,
                "is_shortened": is_shortened,
                "week_keys": [_week_key(_add_weeks(start, offset)) for offset in range(length)],
            }
        )
        covered_weeks += length
        cursor = _next_week(end)
    return {
        "selected_scenario_id": selected_structure_context.get("selected_scenario_id"),
        "planning_horizon_weeks": horizon,
        "deload_cadence": selected_structure_context.get("deload_cadence"),
        "phase_length_weeks": phase_length,
        "phase_count_expected": selected_structure_context.get("phase_count_expected"),
        "covered_weeks": covered_weeks,
        "coverage_matches_horizon": covered_weeks == horizon,
        "phase_slots": slots,
    }


def render_phase_slot_context_block(context: JsonMap) -> str:
    """Render deterministic Season phase slots for Season planning prompts."""

    if not context:
        return ""
    lines = [
        "**Deterministic Season Phase Slot Context**",
        "These slots define phase count, order, length, and ISO-week coverage. Assign schema-valid cycles and planning content to these slots; do not add, remove, or resize slots.",
        f"selected_scenario_id: {context.get('selected_scenario_id')}",
        f"planning_horizon_weeks: {context.get('planning_horizon_weeks')}",
        f"deload_cadence: {context.get('deload_cadence')}",
        f"phase_length_weeks: {context.get('phase_length_weeks')}",
        f"phase_count_expected: {context.get('phase_count_expected')}",
        f"covered_weeks: {context.get('covered_weeks')}",
        f"coverage_matches_horizon: {context.get('coverage_matches_horizon')}",
        "phase_slots:",
    ]
    for slot in _as_list(context.get("phase_slots")):
        slot_map = _as_map(slot)
        lines.append(
            "- "
            f"{slot_map.get('phase_id')}: "
            f"{slot_map.get('iso_week_range')}, "
            f"length_weeks {slot_map.get('length_weeks')}, "
            f"is_shortened {slot_map.get('is_shortened')}, "
            f"weeks {', '.join(str(item) for item in _as_list(slot_map.get('week_keys')))}"
        )
    return "\n".join(lines) + "\n"


def build_planning_horizon_context(
    *,
    planning_events_payload: JsonMap | None,
    target_week: IsoWeek,
) -> JsonMap:
    """Derive the planning horizon from the latest A/B/C event."""

    data = _as_map((planning_events_payload or {}).get("data"))
    last_event: JsonMap | None = None
    last_event_date: date | None = None
    for event in _as_list(data.get("events")):
        event_map = _as_map(event)
        event_type = str(event_map.get("type") or "").strip().upper()
        if event_type not in {"A", "B", "C"}:
            continue
        raw_date = event_map.get("date")
        if not isinstance(raw_date, str):
            continue
        try:
            parsed = date.fromisoformat(raw_date)
        except ValueError:
            continue
        if last_event_date is None or parsed > last_event_date:
            last_event = event_map
            last_event_date = parsed
    if last_event is None or last_event_date is None:
        return {}

    target_start = date.fromisocalendar(target_week.year, target_week.week, 1)
    event_week = date_to_iso_week(last_event_date)
    event_week_end = date.fromisocalendar(event_week.year, event_week.week, 7)
    if event_week_end < target_start:
        event_week_end = target_start
        event_week = target_week
    inclusive_horizon_weeks = ((event_week_end - target_start).days // 7) + 1
    weeks_until_event = max(0, (last_event_date - target_start).days // 7)

    return {
        "target_iso_week": f"{target_week.year:04d}-{target_week.week:02d}",
        "target_week_start_date": target_start.isoformat(),
        "last_event_date": last_event_date.isoformat(),
        "last_event_iso_week": f"{event_week.year:04d}-{event_week.week:02d}",
        "last_event_type": last_event.get("type"),
        "last_event_name": last_event.get("event_name"),
        "weeks_until_last_event_from_target_week_start": weeks_until_event,
        "inclusive_planning_horizon_weeks": inclusive_horizon_weeks,
        "season_iso_week_range": (
            f"{target_week.year:04d}-{target_week.week:02d}--"
            f"{event_week.year:04d}-{event_week.week:02d}"
        ),
        "temporal_scope": {"from": target_start.isoformat(), "to": event_week_end.isoformat()},
    }


def render_planning_horizon_context_block(context: JsonMap) -> str:
    """Render deterministic event-horizon math for Season Scenario prompts."""

    if not context:
        return ""
    lines = [
        "**Deterministic Season Scenario Horizon Context**",
        "These values are derived from PLANNING_EVENTS A/B/C dates. Use them for scenario horizon and phase-math setup; do not recompute the last-event horizon in the agent.",
        f"target_iso_week: {context.get('target_iso_week')}",
        f"target_week_start_date: {context.get('target_week_start_date')}",
        f"last_event_date: {context.get('last_event_date')}",
        f"last_event_iso_week: {context.get('last_event_iso_week')}",
        f"last_event_type: {context.get('last_event_type')}",
        f"last_event_name: {context.get('last_event_name')}",
        "weeks_until_last_event_from_target_week_start: "
        f"{context.get('weeks_until_last_event_from_target_week_start')}",
        f"inclusive_planning_horizon_weeks: {context.get('inclusive_planning_horizon_weeks')}",
        f"season_iso_week_range: {context.get('season_iso_week_range')}",
    ]
    temporal_scope = _as_map(context.get("temporal_scope"))
    if temporal_scope:
        lines.append(f"temporal_scope: {temporal_scope.get('from')} to {temporal_scope.get('to')}")
    return "\n".join(lines) + "\n"
