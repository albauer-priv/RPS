"""Registry and renderers for code-owned planning context injection.

The helpers in this module keep deterministic derivations out of agent prompts:
dates, ISO ranges, phase slots, active S5 bands, daily availability, and
operation boundaries are computed in code and rendered as prompt context.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from rps.planning.load_bands import (
    build_load_capacity_context,
    build_season_phase_load_context,
    render_load_capacity_context_block,
    render_season_phase_load_context_block,
)
from rps.planning.season_structure import (
    build_cadence_options_context,
    build_phase_slot_context,
    build_planning_horizon_context,
    build_selected_scenario_structure_context,
    render_cadence_options_block,
    render_phase_slot_context_block,
    render_planning_horizon_context_block,
    render_selected_scenario_structure_block,
)
from rps.planning.workout_load import (
    build_workout_load_method_context,
    render_workout_load_method_context_block,
)
from rps.workspace.iso_helpers import IsoWeek, IsoWeekRange, range_contains, week_index
from rps.workspace.phase_resolution import date_to_iso_week

JsonMap = dict[str, Any]
CADENCE_WEEK_ROLE_PATTERNS = {
    "2:1": ["LOAD_1", "LOAD_2", "DELOAD"],
    "3:1": ["LOAD_1", "LOAD_2", "LOAD_3", "DELOAD"],
    "2:1:1": ["LOAD_1", "LOAD_2", "MINI_RESET", "RELOAD"],
}
SHORTENED_WEEK_ROLE_PATTERN = [
    "SHORTENED_RE_ENTRY",
    "SHORTENED_CONSOLIDATION",
    "SHORTENED_MINI_RESET",
    "SHORTENED_RELOAD",
]


@dataclass(frozen=True)
class DeterministicContextBlock:
    """Structured deterministic context plus its markdown prompt block."""

    name: str
    title: str
    payload: JsonMap
    markdown: str


def render_context_blocks(blocks: list[DeterministicContextBlock]) -> str:
    """Concatenate non-empty deterministic context markdown blocks."""

    return "".join(block.markdown for block in blocks if block.markdown.strip())


def build_season_scenario_horizon_block(
    *,
    planning_events_payload: JsonMap | None,
    target_week: IsoWeek,
) -> DeterministicContextBlock:
    """Build deterministic event horizon context for scenario generation."""

    payload = build_planning_horizon_context(
        planning_events_payload=planning_events_payload or {},
        target_week=target_week,
    )
    return DeterministicContextBlock(
        name="season_scenario_horizon",
        title="Deterministic Season Scenario Horizon Context",
        payload=payload,
        markdown=render_planning_horizon_context_block(payload),
    )


def build_cadence_options_block(*, horizon_context: JsonMap) -> DeterministicContextBlock:
    """Build deterministic cadence options from a season horizon."""

    payload = build_cadence_options_context(planning_horizon_context=horizon_context)
    return DeterministicContextBlock(
        name="cadence_options",
        title="Deterministic Cadence Options Context",
        payload=payload,
        markdown=render_cadence_options_block(payload),
    )


def build_selected_scenario_structure_block(
    *,
    season_scenarios_payload: JsonMap | None,
    selection_payload: JsonMap | None,
    selected_scenario_id: str | None,
) -> DeterministicContextBlock:
    """Build deterministic selected-scenario structure context."""

    payload = build_selected_scenario_structure_context(
        season_scenarios_payload=season_scenarios_payload or {},
        selection_payload=selection_payload or {},
        selected_scenario_id=selected_scenario_id,
    )
    return DeterministicContextBlock(
        name="selected_scenario_structure",
        title="Deterministic Selected Scenario Structure Context",
        payload=payload,
        markdown=render_selected_scenario_structure_block(payload),
    )


def build_season_phase_slot_block(
    *,
    selected_structure_context: JsonMap,
    target_week: IsoWeek,
) -> DeterministicContextBlock:
    """Build deterministic phase-slot skeleton from selected scenario math."""

    payload = build_phase_slot_context(
        selected_structure_context=selected_structure_context,
        target_week=target_week,
    )
    return DeterministicContextBlock(
        name="season_phase_slots",
        title="Deterministic Season Phase Slot Context",
        payload=payload,
        markdown=render_phase_slot_context_block(payload),
    )


def build_load_capacity_block(**kwargs: Any) -> DeterministicContextBlock:
    """Build deterministic load capacity and S5 context."""

    payload = build_load_capacity_context(**kwargs)
    return DeterministicContextBlock(
        name="load_capacity",
        title="Deterministic Load Capacity Context",
        payload=payload,
        markdown=render_load_capacity_context_block(payload),
    )


def build_season_phase_load_block(**kwargs: Any) -> DeterministicContextBlock:
    """Build deterministic season phase load context."""

    payload = build_season_phase_load_context(**kwargs)
    return DeterministicContextBlock(
        name="season_phase_load",
        title="Deterministic Season Phase Load Context",
        payload=payload,
        markdown=render_season_phase_load_context_block(payload),
    )


def build_workout_load_method_block(**kwargs: Any) -> DeterministicContextBlock:
    """Build deterministic workout-load estimation context."""

    payload = build_workout_load_method_context(**kwargs)
    return DeterministicContextBlock(
        name="workout_load_method",
        title="Deterministic Workout Load Estimation Context",
        payload=payload,
        markdown=render_workout_load_method_context_block(payload),
    )


def build_phase_execution_context(
    *,
    target_week: IsoWeek,
    phase_info: Any,
    phase_range: IsoWeekRange,
    season_plan_payload: JsonMap | None = None,
    phase_slot_context: JsonMap | None = None,
    availability_payload: JsonMap | None = None,
    logistics_payload: JsonMap | None = None,
    planning_events_payload: JsonMap | None = None,
    load_capacity_context: JsonMap | None = None,
) -> JsonMap:
    """Return exact-range phase execution context for Phase prompts."""

    weeks = _weeks_in_range(phase_range)
    target_key = _week_key(target_week)
    phase_raw = _as_map(getattr(phase_info, "raw", {}))
    phase_index = _phase_index(season_plan_payload or {}, str(getattr(phase_info, "phase_id", "")))
    active_s5 = _active_s5_band(load_capacity_context or {}, target_key)
    active_slot = _phase_slot_for_context(
        phase_slot_context=phase_slot_context or {},
        phase_id=str(getattr(phase_info, "phase_id", "")),
        phase_range=phase_range,
    )
    scenario_cadence = str(active_slot.get("scenario_cadence") or "").strip() or None
    cadence_week_roles = [
        str(item)
        for item in _as_list(active_slot.get("cadence_week_roles"))
        if str(item).strip()
    ]
    week_role_by_iso_week = {
        _week_key(week): cadence_week_roles[idx]
        for idx, week in enumerate(weeks)
        if idx < len(cadence_week_roles)
    }
    return {
        "target_iso_week": target_key,
        "phase_id": getattr(phase_info, "phase_id", ""),
        "phase_index": phase_index,
        "phase_iso_week_range": phase_range.range_key,
        "phase_length_weeks": len(weeks),
        "week_keys": [_week_key(week) for week in weeks],
        "week_index_within_phase": max(1, week_index(target_week) - week_index(phase_range.start) + 1),
        "cycle": phase_raw.get("cycle") or getattr(phase_info, "phase_type", ""),
        "phase_role": phase_raw.get("cycle") or getattr(phase_info, "phase_type", ""),
        "phase_intent": phase_raw.get("phase_intent") or "",
        "scenario_cadence": scenario_cadence,
        "phase_cadence_week_roles": cadence_week_roles,
        "week_role_by_iso_week": week_role_by_iso_week,
        "season_phase_slot_source": "Deterministic Season Phase Slot Context",
        "season_phase_slot": active_slot,
        "is_shortened_phase": any(str(role).startswith("SHORTENED_") for role in cadence_week_roles),
        "deload_intent": phase_raw.get("deload"),
        "deload_rationale": phase_raw.get("deload_rationale"),
        "target_week_s5_band": active_s5.get("band"),
        "target_week_s5_trace": active_s5.get("trace"),
        "phase_s5_bands": _s5_bands_for_weeks(load_capacity_context or {}, weeks),
        "fixed_rest_days": _fixed_rest_days(availability_payload or {}),
        "logistics_in_phase": _dated_items_in_range(logistics_payload or {}, phase_range, field="events"),
        "events_in_phase": _dated_items_in_range(planning_events_payload or {}, phase_range, field="events"),
        "blocking_issues": _phase_execution_blocking_issues(
            weeks=weeks,
            cadence_week_roles=cadence_week_roles,
            scenario_cadence=scenario_cadence,
        ),
    }


def render_phase_execution_context_block(context: JsonMap) -> str:
    """Render exact-range phase execution context for Phase prompts."""

    if not context:
        return ""
    lines = [
        "**Deterministic Phase Execution Context**",
        "These values define the exact phase runtime frame. Emit only the listed ISO weeks and use S5 bands as binding code-owned values.",
        f"target_iso_week: {context.get('target_iso_week')}",
        f"phase_id: {context.get('phase_id')}",
        f"phase_index: {context.get('phase_index')}",
        f"phase_iso_week_range: {context.get('phase_iso_week_range')}",
        f"phase_length_weeks: {context.get('phase_length_weeks')}",
        f"week_index_within_phase: {context.get('week_index_within_phase')}",
        f"cycle: {context.get('cycle')}",
        f"phase_role: {context.get('phase_role')}",
        f"phase_intent: {context.get('phase_intent')}",
        f"scenario_cadence: {context.get('scenario_cadence')}",
        "phase_cadence_week_roles: "
        + ", ".join(str(item) for item in _as_list(context.get("phase_cadence_week_roles"))),
        f"deload_intent: {context.get('deload_intent')}",
        f"deload_rationale: {context.get('deload_rationale')}",
        "required_phase_weeks: " + ", ".join(str(item) for item in _as_list(context.get("week_keys"))),
    ]
    role_map = _as_map(context.get("week_role_by_iso_week"))
    if role_map:
        lines.append("week_role_by_iso_week:")
        for week in _as_list(context.get("week_keys")):
            lines.append(f"- {week}: {role_map.get(str(week))}")
    target_band = _as_map(context.get("target_week_s5_band"))
    if target_band:
        lines.append(f"target_week_s5_band: min {target_band.get('min')}, max {target_band.get('max')}")
    phase_bands = _as_list(context.get("phase_s5_bands"))
    if phase_bands:
        lines.append("phase_s5_bands:")
        for entry in phase_bands:
            entry_map = _as_map(entry)
            band = _as_map(entry_map.get("band"))
            if band:
                lines.append(f"- {entry_map.get('week')}: min {band.get('min')}, max {band.get('max')}")
            elif entry_map.get("error"):
                lines.append(f"- {entry_map.get('week')}: ERROR {entry_map.get('error')}")
    _append_list(lines, "fixed_rest_days", context.get("fixed_rest_days"))
    _append_event_list(lines, "logistics_in_phase", context.get("logistics_in_phase"))
    _append_event_list(lines, "events_in_phase", context.get("events_in_phase"))
    _append_list(lines, "blocking_issues", context.get("blocking_issues"))
    return "\n".join(lines) + "\n"


def build_week_calendar_context(
    *,
    target_week: IsoWeek,
    phase_info: Any,
    phase_range: IsoWeekRange,
    availability_payload: JsonMap | None = None,
    logistics_payload: JsonMap | None = None,
    planning_events_payload: JsonMap | None = None,
    phase_guardrails_payload: JsonMap | None = None,
    phase_structure_payload: JsonMap | None = None,
    load_capacity_context: JsonMap | None = None,
) -> JsonMap:
    """Return target-week calendar, availability, and active-band context."""

    target_key = _week_key(target_week)
    week_start = date.fromisocalendar(target_week.year, target_week.week, 1)
    fixed_rest = _fixed_rest_days(availability_payload or {})
    table = _availability_table(availability_payload or {})
    active_s5 = _active_s5_band(load_capacity_context or {}, target_key)
    phase_band = _phase_guardrail_band(phase_guardrails_payload or {}, target_key)
    phase_role = _phase_role_from_structure(phase_structure_payload or {}, phase_info)
    phase_intent = _phase_intent_from_structure(phase_structure_payload or {}, phase_info)
    phase_week_role = _phase_week_role_from_structure(phase_structure_payload or {}, target_key)
    week_role_source = "PHASE_STRUCTURE.week_skeleton_logic.week_roles" if phase_week_role else "phase_position_fallback"
    if not phase_week_role:
        phase_week_role = _phase_role_for_week(phase_info, target_week, phase_range)
    return {
        "target_iso_week": target_key,
        "week_start_date": week_start.isoformat(),
        "week_end_date": (week_start + timedelta(days=6)).isoformat(),
        "phase_id": getattr(phase_info, "phase_id", ""),
        "phase_iso_week_range": phase_range.range_key,
        "phase_cycle": phase_role,
        "phase_role": phase_role,
        "phase_intent": phase_intent,
        "phase_week_role": phase_week_role,
        "phase_role_for_week": phase_week_role,
        "phase_week_role_source": week_role_source,
        "day_matrix": [
            _day_context_row(week_start + timedelta(days=offset), table, fixed_rest, logistics_payload or {}, planning_events_payload or {})
            for offset in range(7)
        ],
        "fixed_rest_days": fixed_rest,
        "active_s5_band": active_s5.get("band"),
        "active_s5_trace": active_s5.get("trace"),
        "phase_weekly_kj_band": phase_band,
        "active_weekly_kj_band": phase_band or active_s5.get("band"),
        "allowed_day_roles": _allowed_day_roles(phase_guardrails_payload or {}),
        "forbidden_day_roles": _forbidden_day_roles(phase_guardrails_payload or {}),
        "allowed_intensity_domains": _allowed_intensity_domains(phase_guardrails_payload or {}),
        "forbidden_intensity_domains": _forbidden_intensity_domains(phase_guardrails_payload or {}),
        "allowed_load_modalities": _allowed_load_modalities(phase_guardrails_payload or {}),
        "quality_day_cap": _quality_day_cap(phase_guardrails_payload or {}),
        "week_skeleton_mandatory_elements": _week_skeleton_mandatory_elements(phase_structure_payload or {}),
        "event_proximity": build_event_proximity_context(
            target_week=target_week,
            planning_events_payload=planning_events_payload or {},
        ),
    }


def render_week_calendar_context_block(context: JsonMap) -> str:
    """Render target-week deterministic calendar and availability context."""

    if not context:
        return ""
    lines = [
        "**Deterministic Week Calendar and Availability Context**",
        "Use this Mon-Sun day matrix and active S5 band directly. Do not move load onto fixed rest days or recompute load bounds.",
        f"target_iso_week: {context.get('target_iso_week')}",
        f"week_start_date: {context.get('week_start_date')}",
        f"week_end_date: {context.get('week_end_date')}",
        f"phase_id: {context.get('phase_id')}",
        f"phase_iso_week_range: {context.get('phase_iso_week_range')}",
        f"phase_cycle: {context.get('phase_cycle')}",
        f"phase_role: {context.get('phase_role')}",
        f"phase_intent: {context.get('phase_intent')}",
        f"phase_week_role: {context.get('phase_week_role')}",
        f"phase_week_role_source: {context.get('phase_week_role_source')}",
        f"phase_role_for_week: {context.get('phase_role_for_week')}",
        "allowed_day_roles: " + ", ".join(str(item) for item in _as_list(context.get("allowed_day_roles"))),
        "forbidden_day_roles: " + ", ".join(str(item) for item in _as_list(context.get("forbidden_day_roles"))),
        "allowed_intensity_domains: " + ", ".join(str(item) for item in _as_list(context.get("allowed_intensity_domains"))),
        "forbidden_intensity_domains: " + ", ".join(str(item) for item in _as_list(context.get("forbidden_intensity_domains"))),
        "allowed_load_modalities: " + ", ".join(str(item) for item in _as_list(context.get("allowed_load_modalities"))),
        f"quality_day_cap: {context.get('quality_day_cap')}",
    ]
    s5 = _as_map(context.get("active_s5_band"))
    if s5:
        lines.append(f"active_s5_band: min {s5.get('min')}, max {s5.get('max')}")
    phase_band = _as_map(context.get("phase_weekly_kj_band"))
    if phase_band:
        lines.append(f"phase_weekly_kj_band: min {phase_band.get('min')}, max {phase_band.get('max')}")
    active_band = _as_map(context.get("active_weekly_kj_band"))
    if active_band:
        lines.append(f"active_weekly_kj_band: min {active_band.get('min')}, max {active_band.get('max')}")
    mandatory = _as_map(context.get("week_skeleton_mandatory_elements"))
    if mandatory:
        lines.append(
            "week_skeleton_mandatory_elements: "
            f"recovery_opportunities_min {mandatory.get('recovery_opportunities_min')}, "
            f"endurance_anchor_required {mandatory.get('endurance_anchor_required')}"
        )
    _append_list(lines, "fixed_rest_days", context.get("fixed_rest_days"))
    lines.append("day_matrix:")
    for row in _as_list(context.get("day_matrix")):
        row_map = _as_map(row)
        availability = _as_map(row_map.get("availability_hours"))
        lines.append(
            "- "
            f"{row_map.get('day')} {row_map.get('date')}: "
            f"fixed_rest {row_map.get('fixed_rest_day')}, "
            f"hours min {availability.get('min')}, typical {availability.get('typical')}, max {availability.get('max')}, "
            f"logistics {row_map.get('logistics') or 'none'}, events {row_map.get('events') or 'none'}"
        )
    proximity = _as_map(context.get("event_proximity"))
    if proximity:
        lines.append(
            "event_proximity: "
            f"nearest {proximity.get('nearest_event_name')} "
            f"({proximity.get('nearest_event_type')}) "
            f"relation {proximity.get('relation_to_target_week')} "
            f"weeks_delta {proximity.get('weeks_delta')}"
        )
    return "\n".join(lines) + "\n"


def build_event_proximity_context(*, target_week: IsoWeek, planning_events_payload: JsonMap | None) -> JsonMap:
    """Return deterministic proximity of the selected week to the nearest planning event."""

    target_start = date.fromisocalendar(target_week.year, target_week.week, 1)
    nearest: JsonMap | None = None
    nearest_delta: int | None = None
    for event in _as_list(_as_map((planning_events_payload or {}).get("data")).get("events")):
        event_map = _as_map(event)
        raw_date = event_map.get("date")
        if not isinstance(raw_date, str):
            continue
        try:
            event_date = date.fromisoformat(raw_date)
        except ValueError:
            continue
        delta_weeks = (event_date - target_start).days // 7
        if nearest_delta is None or abs(delta_weeks) < abs(nearest_delta):
            nearest = event_map
            nearest_delta = delta_weeks
    if nearest is None or nearest_delta is None:
        return {"nearest_event_name": None, "nearest_event_type": None, "weeks_delta": None, "relation_to_target_week": "none"}
    relation = "during"
    if nearest_delta < 0:
        relation = "after_event_week"
    elif nearest_delta > 0:
        relation = "before_event_week"
    return {
        "nearest_event_name": nearest.get("event_name"),
        "nearest_event_type": nearest.get("type"),
        "nearest_event_date": nearest.get("date"),
        "weeks_delta": nearest_delta,
        "relation_to_target_week": relation,
    }


def build_report_evidence_context(
    *,
    report_week: IsoWeek,
    resolved_week_versions: dict[Any, str],
    missing_required: list[Any] | None = None,
    missing_context_inputs: list[str] | None = None,
) -> JsonMap:
    """Return deterministic evidence and boundary context for DES reports."""

    return {
        "report_iso_week": _week_key(report_week),
        "activity_versions": {str(getattr(key, "value", key)): value for key, value in resolved_week_versions.items()},
        "missing_required": [str(getattr(item, "value", item)) for item in missing_required or []],
        "missing_context_inputs": list(missing_context_inputs or []),
        "diagnostic_only": True,
        "forbidden_actions": ["direct_phase_change", "weekly_intervention", "artifact_persistence"],
    }


def render_report_evidence_context_block(context: JsonMap) -> str:
    """Render DES report evidence context."""

    if not context:
        return ""
    lines = [
        "**Deterministic Report Evidence Context**",
        "Use exact completed-week evidence versions. This report is diagnostic-only and must not directly change planning artefacts.",
        f"report_iso_week: {context.get('report_iso_week')}",
        f"diagnostic_only: {context.get('diagnostic_only')}",
        "activity_versions:",
    ]
    versions = _as_map(context.get("activity_versions"))
    if versions:
        lines.extend(f"- {key}: {value}" for key, value in sorted(versions.items()))
    else:
        lines.append("- none")
    _append_list(lines, "missing_required", context.get("missing_required"))
    _append_list(lines, "missing_context_inputs", context.get("missing_context_inputs"))
    _append_list(lines, "forbidden_actions", context.get("forbidden_actions"))
    return "\n".join(lines) + "\n"


def build_coach_operation_context(
    *,
    athlete_id: str,
    target_week: IsoWeek,
    pending_operation: JsonMap | None = None,
    allowed_operations: list[str] | None = None,
) -> JsonMap:
    """Return deterministic Coach operation boundaries for the selected week."""

    pending = pending_operation or {}
    return {
        "athlete_id": athlete_id,
        "target_iso_week": _week_key(target_week),
        "allowed_operations": allowed_operations
        or [
            "read_context",
            "preview_week_plan",
            "preview_scoped_week_replan",
            "preview_report",
            "preview_feed_forward",
            "apply_confirmed_pending_operation",
        ],
        "pending_operation_type": pending.get("type") or pending.get("operation_type"),
        "pending_operation_status": pending.get("status") or ("present" if pending else "none"),
        "preview_first": True,
        "persistence_requires_confirmation": True,
    }


def render_coach_operation_context_block(context: JsonMap) -> str:
    """Render Coach operation boundary context."""

    if not context:
        return ""
    lines = [
        "**Deterministic Coach Operation Context**",
        "Coach is preview-first. It may explain and preview allowed operations, but persistence requires an existing confirmed pending operation.",
        f"athlete_id: {context.get('athlete_id')}",
        f"target_iso_week: {context.get('target_iso_week')}",
        f"pending_operation_type: {context.get('pending_operation_type')}",
        f"pending_operation_status: {context.get('pending_operation_status')}",
        f"preview_first: {context.get('preview_first')}",
        f"persistence_requires_confirmation: {context.get('persistence_requires_confirmation')}",
        "allowed_operations:",
    ]
    lines.extend(f"- {item}" for item in _as_list(context.get("allowed_operations")))
    return "\n".join(lines) + "\n"


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _week_key(week: IsoWeek) -> str:
    return f"{week.year:04d}-{week.week:02d}"


def _weeks_in_range(phase_range: IsoWeekRange) -> list[IsoWeek]:
    cursor = date.fromisocalendar(phase_range.start.year, phase_range.start.week, 1)
    end = date.fromisocalendar(phase_range.end.year, phase_range.end.week, 1)
    weeks: list[IsoWeek] = []
    while cursor <= end:
        iso_year, iso_week, _ = cursor.isocalendar()
        weeks.append(IsoWeek(iso_year, iso_week))
        cursor += timedelta(days=7)
    return weeks


def _phase_index(season_plan_payload: JsonMap, phase_id: str) -> int | None:
    phases = _as_list(_as_map(season_plan_payload.get("data")).get("phases"))
    for idx, phase in enumerate(phases, start=1):
        if str(_as_map(phase).get("phase_id") or "") == phase_id:
            return idx
    return None


def _active_s5_band(load_context: JsonMap, week_key: str) -> JsonMap:
    for entry in _as_list(load_context.get("s5_bands")):
        entry_map = _as_map(entry)
        if entry_map.get("week") == week_key:
            return entry_map
    return {}


def _s5_bands_for_weeks(load_context: JsonMap, weeks: list[IsoWeek]) -> list[JsonMap]:
    wanted = {_week_key(week) for week in weeks}
    return [_as_map(entry) for entry in _as_list(load_context.get("s5_bands")) if _as_map(entry).get("week") in wanted]


def _scenario_cadence_from_phase(phase_raw: JsonMap) -> str | None:
    return None


def _cadence_week_roles_for_phase(*, phase_raw: JsonMap, cadence: str | None, length_weeks: int) -> list[str]:
    return []


def _phase_slot_for_context(*, phase_slot_context: JsonMap, phase_id: str, phase_range: IsoWeekRange) -> JsonMap:
    """Return the deterministic season phase slot matching the active phase."""

    range_key = phase_range.range_key
    for slot in _as_list(phase_slot_context.get("phase_slots")):
        slot_map = _as_map(slot)
        if phase_id and str(slot_map.get("phase_id") or "") == phase_id:
            return slot_map
        if str(slot_map.get("iso_week_range") or "") == range_key:
            return slot_map
    return {}


def _phase_execution_blocking_issues(
    *,
    weeks: list[IsoWeek],
    cadence_week_roles: list[str],
    scenario_cadence: str | None,
) -> list[str]:
    issues: list[str] = []
    if len(cadence_week_roles) != len(weeks):
        issues.append("phase cadence week roles do not cover every phase week.")
    if not scenario_cadence:
        issues.append("phase scenario cadence missing from deterministic phase slot context.")
    if scenario_cadence and scenario_cadence not in CADENCE_WEEK_ROLE_PATTERNS:
        issues.append("scenario cadence is unsupported for deterministic phase roles.")
    return issues


def _fixed_rest_days(availability_payload: JsonMap) -> list[str]:
    return [str(item) for item in _as_list(_as_map(availability_payload.get("data")).get("fixed_rest_days"))]


def _availability_table(availability_payload: JsonMap) -> dict[str, JsonMap]:
    table: dict[str, JsonMap] = {}
    for row in _as_list(_as_map(availability_payload.get("data")).get("availability_table")):
        row_map = _as_map(row)
        day = str(row_map.get("day") or row_map.get("weekday") or "").strip()
        if day:
            table[day[:3].title()] = row_map
    return table


def _day_context_row(
    day_date: date,
    availability_table: dict[str, JsonMap],
    fixed_rest_days: list[str],
    logistics_payload: JsonMap,
    planning_events_payload: JsonMap,
) -> JsonMap:
    day_label = day_date.strftime("%a")
    row = availability_table.get(day_label, {})
    return {
        "day": day_label,
        "date": day_date.isoformat(),
        "fixed_rest_day": day_label in fixed_rest_days or day_date.isoformat() in fixed_rest_days,
        "availability_hours": {
            "min": row.get("hours_min") or row.get("min_hours") or row.get("min"),
            "typical": row.get("hours_typical") or row.get("typical_hours") or row.get("typical"),
            "max": row.get("hours_max") or row.get("max_hours") or row.get("max"),
        },
        "logistics": _dated_items_on_date(logistics_payload, day_date, field="events"),
        "events": _dated_items_on_date(planning_events_payload, day_date, field="events"),
    }


def _dated_items_on_date(payload: JsonMap, target_date: date, *, field: str) -> list[JsonMap]:
    out: list[JsonMap] = []
    for item in _as_list(_as_map(payload.get("data")).get(field)):
        item_map = _as_map(item)
        if item_map.get("date") == target_date.isoformat():
            out.append(_event_summary(item_map))
    return out


def _dated_items_in_range(payload: JsonMap, phase_range: IsoWeekRange, *, field: str) -> list[JsonMap]:
    out: list[JsonMap] = []
    for item in _as_list(_as_map(payload.get("data")).get(field)):
        item_map = _as_map(item)
        raw_date = item_map.get("date")
        if not isinstance(raw_date, str):
            continue
        try:
            item_week = date_to_iso_week(date.fromisoformat(raw_date))
        except ValueError:
            continue
        if range_contains(phase_range, item_week):
            out.append(_event_summary(item_map))
    return out


def _event_summary(item: JsonMap) -> JsonMap:
    return {
        "date": item.get("date"),
        "type": item.get("type") or item.get("event_type"),
        "name": item.get("event_name") or item.get("name"),
        "impact": item.get("impact"),
        "description": item.get("description"),
    }


def _phase_role_for_week(phase_info: Any, target_week: IsoWeek, phase_range: IsoWeekRange) -> str:
    if target_week == phase_range.end:
        return "phase_final_week"
    if target_week == phase_range.start:
        return "phase_entry_week"
    raw = _as_map(getattr(phase_info, "raw", {}))
    if raw.get("deload") is True:
        return "deload_phase_week"
    return "phase_middle_week"


def _phase_role_from_structure(phase_structure_payload: JsonMap, phase_info: Any) -> str:
    data = _as_map(phase_structure_payload.get("data"))
    execution = _as_map(data.get("execution_principles"))
    role = execution.get("phase_role") or data.get("phase_role")
    if isinstance(role, str) and role.strip():
        return role.strip()
    raw = _as_map(getattr(phase_info, "raw", {}))
    fallback = raw.get("cycle") or getattr(phase_info, "phase_type", "")
    return str(fallback or "").strip()


def _phase_intent_from_structure(phase_structure_payload: JsonMap, phase_info: Any) -> str:
    data = _as_map(phase_structure_payload.get("data"))
    upstream_intent = _as_map(data.get("upstream_intent"))
    intent = upstream_intent.get("phase_intent") or data.get("phase_intent")
    if isinstance(intent, str) and intent.strip():
        return intent.strip()
    raw = _as_map(getattr(phase_info, "raw", {}))
    fallback = raw.get("phase_intent")
    return str(fallback or "").strip()


def _phase_week_role_from_structure(phase_structure_payload: JsonMap, week_key: str) -> str | None:
    data = _as_map(phase_structure_payload.get("data"))
    skeleton = _as_map(data.get("week_skeleton_logic"))
    roles_wrapper = _as_map(skeleton.get("week_roles"))
    for entry in _as_list(roles_wrapper.get("week_roles")):
        entry_map = _as_map(entry)
        if entry_map.get("week") == week_key and isinstance(entry_map.get("role"), str):
            return str(entry_map.get("role")).strip()
    return None


def _phase_guardrail_band(phase_guardrails_payload: JsonMap, week_key: str) -> JsonMap:
    data = _as_map(phase_guardrails_payload.get("data"))
    guardrails = _as_map(data.get("load_guardrails"))
    for entry in _as_list(guardrails.get("weekly_kj_bands")):
        entry_map = _as_map(entry)
        if entry_map.get("week") == week_key:
            return _as_map(entry_map.get("band"))
    return {}


def _allowed_day_roles(phase_guardrails_payload: JsonMap) -> list[str]:
    data = _as_map(phase_guardrails_payload.get("data"))
    semantics = _as_map(data.get("allowed_forbidden_semantics"))
    return [str(item) for item in _as_list(semantics.get("allowed_day_roles"))]


def _forbidden_day_roles(phase_guardrails_payload: JsonMap) -> list[str]:
    data = _as_map(phase_guardrails_payload.get("data"))
    semantics = _as_map(data.get("allowed_forbidden_semantics"))
    return [str(item) for item in _as_list(semantics.get("forbidden_day_roles"))]


def _allowed_intensity_domains(phase_guardrails_payload: JsonMap) -> list[str]:
    data = _as_map(phase_guardrails_payload.get("data"))
    semantics = _as_map(data.get("allowed_forbidden_semantics"))
    return [str(item) for item in _as_list(semantics.get("allowed_intensity_domains"))]


def _forbidden_intensity_domains(phase_guardrails_payload: JsonMap) -> list[str]:
    data = _as_map(phase_guardrails_payload.get("data"))
    semantics = _as_map(data.get("allowed_forbidden_semantics"))
    return [str(item) for item in _as_list(semantics.get("forbidden_intensity_domains"))]


def _allowed_load_modalities(phase_guardrails_payload: JsonMap) -> list[str]:
    data = _as_map(phase_guardrails_payload.get("data"))
    semantics = _as_map(data.get("allowed_forbidden_semantics"))
    return [str(item) for item in _as_list(semantics.get("allowed_load_modalities"))]


def _quality_day_cap(phase_guardrails_payload: JsonMap) -> Any:
    data = _as_map(phase_guardrails_payload.get("data"))
    semantics = _as_map(data.get("allowed_forbidden_semantics"))
    quality_density = _as_map(semantics.get("quality_density"))
    caps = _as_map(data.get("density_caps") or data.get("load_guardrails"))
    return (
        quality_density.get("max_quality_days_per_week")
        or caps.get("quality_day_cap")
        or caps.get("max_quality_days_per_week")
    )


def _week_skeleton_mandatory_elements(phase_structure_payload: JsonMap) -> JsonMap:
    data = _as_map(phase_structure_payload.get("data"))
    skeleton = _as_map(data.get("week_skeleton_logic"))
    return _as_map(skeleton.get("mandatory_elements"))


def _append_list(lines: list[str], label: str, values: object) -> None:
    items = [str(item) for item in _as_list(values) if str(item).strip()]
    if not items:
        return
    lines.append(f"{label}:")
    lines.extend(f"- {item}" for item in items)


def _append_event_list(lines: list[str], label: str, values: object) -> None:
    items = [_as_map(item) for item in _as_list(values)]
    if not items:
        return
    lines.append(f"{label}:")
    for item in items:
        lines.append(
            f"- {item.get('date')}: {item.get('type') or ''} {item.get('name') or ''} "
            f"impact {item.get('impact') or '-'} {item.get('description') or ''}".strip()
        )
