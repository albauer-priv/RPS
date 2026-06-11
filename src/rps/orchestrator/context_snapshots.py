"""Derived snapshot artefacts for snapshot-based planner memory."""

from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime, timedelta

from rps.data_pipeline.intervals_data import fetch_current_week_activities_actual_payload
from rps.orchestrator.resolved_context import (
    build_resolved_activity_context_block,
    build_resolved_athlete_context_block,
    build_resolved_availability_context_block,
    build_resolved_event_priority_context_block,
    build_resolved_feed_forward_applicability_context_block,
    build_resolved_kpi_context_block,
    build_resolved_load_governance_context_block,
    build_resolved_logistics_context_block,
    build_resolved_phase_context_block,
    build_resolved_planning_events_context_block,
    build_resolved_recovery_context_block,
    build_resolved_zone_model_context_block,
)
from rps.orchestrator.week_plan_edits import list_week_plan_workouts
from rps.planning.season_selection_binding import resolve_bound_season_selection
from rps.workspace.iso_helpers import IsoWeek, IsoWeekRange
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.paths import ARTIFACT_PATHS
from rps.workspace.season_plan_service import SeasonPlanPhaseInfo
from rps.workspace.types import ArtifactType

JsonMap = dict[str, object]

SNAPSHOT_OWNER_AGENT = "Policy-Owner"
SNAPSHOT_PRODUCER_AGENT = "policy_owner"
SNAPSHOT_VERSION = "1.0"
SNAPSHOT_SCHEMA_VERSION = "1.0"


def _as_meta(payload: object) -> JsonMap:
    if not isinstance(payload, dict):
        return {}
    meta = payload.get("meta")
    return meta if isinstance(meta, dict) else {}


def _trace_ref(artifact_type: ArtifactType, payload: object) -> JsonMap | None:
    meta = _as_meta(payload)
    version_key = meta.get("version_key")
    run_id = meta.get("run_id")
    if not isinstance(version_key, str) or not isinstance(run_id, str):
        return None
    prefix = ARTIFACT_PATHS[artifact_type].filename_prefix
    return {
        "artifact": f"{prefix}_{version_key}.json",
        "version": SNAPSHOT_VERSION,
        "run_id": run_id,
    }


def _compact_source_version(artifact_type: ArtifactType, payload: object) -> str | None:
    meta = _as_meta(payload)
    version_key = meta.get("version_key")
    return version_key if isinstance(version_key, str) else None


def _temporal_scope_for_week(target_week: IsoWeek) -> JsonMap:
    week_start = date.fromisocalendar(target_week.year, target_week.week, 1)
    week_end = date.fromisocalendar(target_week.year, target_week.week, 7)
    return {"from": week_start.isoformat(), "to": week_end.isoformat()}


def _non_empty_prompt_blocks(blocks: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in blocks.items() if value.strip()}


def _source_versions_map(entries: list[tuple[str, ArtifactType, object]]) -> JsonMap:
    out: JsonMap = {}
    for label, artifact_type, payload in entries:
        version_key = _compact_source_version(artifact_type, payload)
        if version_key:
            out[label] = version_key
    return out


def _build_wellness_prompt_block(wellness_payload: JsonMap | None) -> str:
    """Return a compact wellness/body-mass block when authoritative body mass exists."""
    if not isinstance(wellness_payload, dict):
        return ""
    data = wellness_payload.get("data")
    if not isinstance(data, dict):
        return ""
    body_mass = data.get("body_mass_kg")
    if not isinstance(body_mass, (int, float)):
        return ""
    return (
        "**Resolved Wellness Context**\n"
        f"WELLNESS.data.body_mass_kg is present and authoritative for KPI gating: {float(body_mass):.1f} kg.\n"
        "Use WELLNESS.data.body_mass_kg for any kJ/kg/h or W/kg gating before any STOP about missing or "
        "semantically unusable body mass.\n"
    )


def _as_data(payload: JsonMap | None) -> JsonMap:
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _as_str(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_str_list(value: object) -> list[str]:
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []


def _build_advisory_season_block(season_plan_payload: JsonMap | None) -> str:
    data = _as_data(season_plan_payload)
    phases = data.get("phases")
    if not isinstance(phases, list) or not phases:
        return ""
    first = phases[0] if isinstance(phases[0], dict) else {}
    selected_contract = data.get("selected_scenario_contract")
    selected_map = selected_contract if isinstance(selected_contract, dict) else {}
    return (
        "**Season Advisory Summary**\n"
        f"season_objective: {_as_str(data.get('season_objective')) or 'n/a'}\n"
        f"current_phase_seed: {_as_str(first.get('phase_type')) or _as_str(first.get('label')) or 'n/a'}\n"
        f"selected_scenario_posture_summary: {_as_str(selected_map.get('load_posture')) or 'n/a'}; "
        f"recovery_margin {_as_str(selected_map.get('recovery_margin')) or 'n/a'}; "
        f"specificity_density {_as_str(selected_map.get('specificity_density')) or 'n/a'}\n"
    )


def _build_advisory_week_block(week_plan_payload: JsonMap | None) -> str:
    data = _as_data(week_plan_payload)
    summary = data.get("week_summary")
    summary_map = summary if isinstance(summary, dict) else {}
    objective = _as_str(summary_map.get("week_objective"))
    load = summary_map.get("planned_weekly_load_kj")
    if not objective and not isinstance(load, (int, float)):
        return ""
    lines = ["**Week Advisory Summary**"]
    if objective:
        lines.append(f"week_objective: {objective}")
    if isinstance(load, (int, float)):
        lines.append(f"planned_weekly_load_kj: {int(load)}")
    return "\n".join(lines) + "\n"


def _build_current_week_plan_block(week_plan_payload: JsonMap | None) -> str:
    """Return a compact selected-week workout summary for Coach memory."""

    if not isinstance(week_plan_payload, dict):
        return ""
    workouts = list_week_plan_workouts(week_plan_payload)
    if not workouts:
        return ""
    lines = [
        "**Current Week Plan Snapshot**",
        "Use this derived current-week plan summary directly before asking tools to rediscover the same workout list.",
    ]
    lines.append("planned_workouts_table:")
    for row in workouts:
        day = _as_str(row.get("day"))
        date_label = _as_str(row.get("date"))
        role = _as_str(row.get("day_role"))
        title = _as_str(row.get("title"))
        duration = _as_str(row.get("duration")) or _as_str(row.get("planned_duration"))
        planned_kj = _as_str(row.get("planned_kj"))
        lines.append(
            "- "
            + " | ".join(
                [
                    day or "-",
                    date_label or "-",
                    role or "-",
                    title or "-",
                    duration or "-",
                    (planned_kj + " kJ") if planned_kj else "-",
                ]
            )
        )
    return "\n".join(lines) + "\n"


def _duration_to_seconds(value: object) -> int:
    """Return whole seconds for a `HH:MM:SS` string or zero when unavailable."""

    if not isinstance(value, str):
        return 0
    parts = value.split(":")
    if len(parts) != 3:
        return 0
    try:
        hours, minutes, seconds = (int(part) for part in parts)
    except ValueError:
        return 0
    return max(0, hours * 3600 + minutes * 60 + seconds)


def _format_duration(seconds: int) -> str:
    """Return `HH:MM:SS` for a non-negative duration in seconds."""

    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _weekday_label(date_text: str) -> str:
    """Return Mon..Sun for an ISO date string, or '-' when unavailable."""

    if not date_text:
        return "-"
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").strftime("%a")
    except ValueError:
        return "-"


def _simple_key_value_map(block: str) -> dict[str, str]:
    """Parse simple `key: value` lines from a prompt block."""

    parsed: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key_clean = key.strip()
        value_clean = value.strip()
        if key_clean and value_clean and not key_clean.startswith("**"):
            parsed[key_clean] = value_clean
    return parsed


def _int_from_text(value: str | None) -> int:
    """Return an integer parsed from text, defaulting to zero."""

    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def _build_advisory_report_block(
    des_analysis_payload: JsonMap | None,
    report_version_key: str | None = None,
) -> str:
    data = _as_data(des_analysis_payload)
    recommendation = data.get("recommendation")
    recommendation_map = recommendation if isinstance(recommendation, dict) else {}
    considerations = _as_str_list(recommendation_map.get("suggested_considerations"))
    rationale = _as_str_list(recommendation_map.get("rationale"))
    if not considerations and not rationale and not report_version_key:
        return ""
    lines = ["**Performance Advisory Summary**"]
    if report_version_key:
        lines.append(f"des_analysis_report_version: {report_version_key}")
    if considerations:
        lines.append("suggested_considerations: " + " | ".join(considerations))
    if rationale:
        lines.append("rationale: " + " | ".join(rationale))
    return "\n".join(lines) + "\n"


def _build_json_context_block(label: str, payload: JsonMap | None) -> str:
    """Render a compact JSON context block for flexible snapshot memory."""

    if not isinstance(payload, dict) or not payload:
        return ""
    return f"**{label}**\n{json.dumps(payload, sort_keys=True)}\n"


def _build_advisory_season_ff_block(season_phase_feed_forward_payload: JsonMap | None) -> str:
    data = _as_data(season_phase_feed_forward_payload)
    decision = data.get("decision_summary")
    adjustment = data.get("phase_adjustment")
    decision_map = decision if isinstance(decision, dict) else {}
    adjustment_map = adjustment if isinstance(adjustment, dict) else {}
    adjustments = adjustment_map.get("adjustments")
    adjustments_map = adjustments if isinstance(adjustments, dict) else {}
    kj_corridor = adjustments_map.get("kj_corridor")
    quality_density = adjustments_map.get("quality_density")
    kj_map = kj_corridor if isinstance(kj_corridor, dict) else {}
    quality_map = quality_density if isinstance(quality_density, dict) else {}
    conclusion = _as_str(decision_map.get("conclusion"))
    if not conclusion and not kj_map and not quality_map:
        return ""
    lines = ["**Season Feed Forward Advisory**"]
    if conclusion:
        lines.append(f"conclusion: {conclusion}")
    direction = _as_str(kj_map.get("direction"))
    if direction:
        percent = kj_map.get("percent")
        suffix = f" ({percent}%)" if isinstance(percent, (int, float)) else ""
        lines.append(f"kj_corridor_adjustment: {direction}{suffix}")
    action = _as_str(quality_map.get("action"))
    if action:
        details = _as_str(quality_map.get("details"))
        lines.append(f"quality_density: {action}" + (f" | {details}" if details else ""))
    return "\n".join(lines) + "\n"


def _build_advisory_phase_ff_block(phase_feed_forward_payload: JsonMap | None) -> str:
    data = _as_data(phase_feed_forward_payload)
    reason = data.get("reason_context")
    reason_map = reason if isinstance(reason, dict) else {}
    intent = _as_str(reason_map.get("intent_of_adjustment"))
    if not intent:
        return ""
    return (
        "**Phase Feed Forward Advisory**\n"
        f"intent_of_adjustment: {intent}\n"
    )


def _build_advisory_inherited_posture_block(phase_feed_forward_payload: JsonMap | None) -> str:
    """Return a compact non-binding inherited posture summary."""

    data = _as_data(phase_feed_forward_payload)
    contract = data.get("inherited_scenario_contract")
    contract_map = contract if isinstance(contract, dict) else {}
    if not contract_map:
        return ""
    return (
        "**Inherited Posture Summary**\n"
        f"inherited_specificity_stance: {_as_str(contract_map.get('specificity_density'))}\n"
        f"inherited_recovery_margin_summary: {_as_str(contract_map.get('recovery_margin'))}\n"
    )


def _build_advisory_selected_contract_block(season_plan_payload: JsonMap | None) -> str:
    """Return a compact non-binding selected scenario posture summary."""

    contract_map = _as_map(_as_data(season_plan_payload).get("selected_scenario_contract"))
    if not contract_map:
        return ""
    return (
        "**Selected Scenario Posture Summary**\n"
        f"selected_scenario_posture_summary: {_as_str(contract_map.get('load_posture')) or 'n/a'}\n"
        f"inherited_specificity_stance: {_as_str(contract_map.get('specificity_density')) or 'n/a'}\n"
        f"inherited_recovery_margin_summary: {_as_str(contract_map.get('recovery_margin')) or 'n/a'}\n"
    )


def _load_latest_snapshot(
    store: LocalArtifactStore, athlete_id: str, artifact_type: ArtifactType
) -> JsonMap:
    payload = store.load_latest(athlete_id, artifact_type)
    if not isinstance(payload, dict):
        raise TypeError(f"Latest {artifact_type.value} payload is not a JSON object.")
    return payload


def _try_load_latest(
    store: LocalArtifactStore, athlete_id: str, artifact_type: ArtifactType
) -> JsonMap | None:
    """Return the latest payload for `artifact_type`, or `None` when unavailable."""

    try:
        payload = store.load_latest(athlete_id, artifact_type)
    except FileNotFoundError:
        return None
    return payload if isinstance(payload, dict) else None


def _completed_sessions(current_week_actual_payload: JsonMap | None, target_week: IsoWeek) -> list[dict[str, object]]:
    """Return normalized completed sessions for the target week from a live/current-week payload."""

    data = current_week_actual_payload.get("data") if isinstance(current_week_actual_payload, dict) else None
    activities = data.get("activities") if isinstance(data, dict) else None
    if not isinstance(activities, list):
        return []
    sessions: list[dict[str, object]] = []
    for activity in activities:
        if not isinstance(activity, dict):
            continue
        if activity.get("iso_year") not in (None, target_week.year):
            continue
        if activity.get("iso_week") not in (None, target_week.week):
            continue
        sessions.append(activity)
    sessions.sort(key=lambda item: str(item.get("start_time_local") or item.get("day") or ""))
    return sessions


def _build_current_week_actuals_block(current_week_actual_payload: JsonMap | None, target_week: IsoWeek) -> str:
    """Return the current-week completed-session block for Coach memory."""

    completed_sessions = _completed_sessions(current_week_actual_payload, target_week)
    total_seconds = 0
    total_work_kj = 0.0
    for activity in completed_sessions:
        total_seconds += _duration_to_seconds(activity.get("moving_time"))
        work_kj = activity.get("work_kj")
        if isinstance(work_kj, (int, float)):
            total_work_kj += float(work_kj)

    lines = [
        "**Current Week Actuals Snapshot**",
        "Use this code-owned snapshot for completed sessions in the current target week up to now. It is partial by design and must not replace the stable historical reference-week planning context.",
        f"target_iso_week: {target_week.year:04d}-{target_week.week:02d}",
    ]
    meta = _as_meta(current_week_actual_payload or {})
    version_key = meta.get("version_key")
    if isinstance(version_key, str):
        lines.append(f"activities_actual_version: {version_key}")
    lines.append(f"completed_sessions_count: {len(completed_sessions)}")
    lines.append(f"completed_moving_time: {_format_duration(total_seconds)}")
    lines.append(f"completed_work_kj: {int(round(total_work_kj))}")
    if completed_sessions:
        lines.append("completed_sessions_table:")
        for activity in completed_sessions:
            date_label = _as_str(activity.get("day"))[:10] or "-"
            day = _weekday_label(date_label)
            session_type = _as_str(activity.get("type")) or "activity"
            what_label = (
                _as_str(activity.get("name"))
                or _as_str(activity.get("title"))
                or session_type
            )
            moving_time = _as_str(activity.get("moving_time")) or "-"
            work_kj = activity.get("work_kj")
            work_label = f"{int(round(float(work_kj)))} kJ" if isinstance(work_kj, (int, float)) else "-"
            load_tss = activity.get("load_tss")
            load_label = (
                str(int(round(float(load_tss)))) if isinstance(load_tss, (int, float)) else "-"
            )
            intensity_factor = activity.get("if")
            if_label = f"{float(intensity_factor):.2f}" if isinstance(intensity_factor, (int, float)) else "-"
            lines.append(
                "- "
                + " | ".join(
                    [
                        day,
                        date_label,
                        session_type,
                        what_label,
                        moving_time,
                        work_label,
                        if_label,
                        load_label,
                    ]
                )
            )
    return "\n".join(lines) + "\n"


def _build_plan_vs_actual_block(
    week_plan_payload: JsonMap | None,
    current_week_actual_payload: JsonMap | None,
    target_week: IsoWeek,
) -> str:
    """Return a deterministic plan-vs-actual comparison for the current week."""

    workouts = list_week_plan_workouts(week_plan_payload or {}) if isinstance(week_plan_payload, dict) else []
    completed_sessions = _completed_sessions(current_week_actual_payload, target_week)
    if not workouts and not completed_sessions:
        return ""

    planned_dates: dict[str, str] = {}
    planned_rows_by_date: dict[str, dict[str, str]] = {}
    for row in workouts:
        if not isinstance(row, dict):
            continue
        date_label = _as_str(row.get("date"))
        title = _as_str(row.get("title")) or _as_str(row.get("day_role")) or "Planned workout"
        if date_label:
            planned_dates[date_label] = title
            planned_rows_by_date[date_label] = row

    completed_dates: dict[str, str] = {}
    for activity in completed_sessions:
        day = _as_str(activity.get("day"))[:10]
        label = _as_str(activity.get("type")) or "activity"
        if day:
            completed_dates[day] = label

    open_days = sorted(set(planned_dates) - set(completed_dates))
    unplanned_days = sorted(set(completed_dates) - set(planned_dates))
    matched_days = sorted(set(planned_dates) & set(completed_dates))

    week_summary = _as_data(week_plan_payload).get("week_summary") if isinstance(week_plan_payload, dict) else None
    week_summary_map = week_summary if isinstance(week_summary, dict) else {}
    planned_load = week_summary_map.get("planned_weekly_load_kj")
    completed_work_kj = 0
    for activity in completed_sessions:
        work_kj = activity.get("work_kj")
        if isinstance(work_kj, (int, float)):
            completed_work_kj += int(round(float(work_kj)))

    lines = [
        "**Plan vs Actual Snapshot**",
        f"planned_workouts_count: {len(planned_dates)}",
        f"completed_sessions_count: {len(completed_sessions)}",
        f"matched_planned_days_count: {len(matched_days)}",
        f"open_planned_days_count: {len(open_days)}",
        f"unplanned_completed_days_count: {len(unplanned_days)}",
        f"completed_work_kj_so_far: {completed_work_kj}",
    ]
    if isinstance(planned_load, (int, float)):
        lines.append(f"planned_weekly_load_kj: {int(planned_load)}")
    if open_days:
        lines.append("open_planned_days_table:")
        for day in open_days:
            row = planned_rows_by_date.get(day, {})
            lines.append(
                "- "
                + " | ".join(
                    [
                        day,
                        _as_str(row.get("title")) or planned_dates[day],
                        _as_str(row.get("day")) or "-",
                        _as_str(row.get("day_role")) or "-",
                        _as_str(row.get("duration")) or _as_str(row.get("planned_duration")) or "-",
                        ((_as_str(row.get("planned_kj")) + " kJ") if _as_str(row.get("planned_kj")) else "-"),
                    ]
                )
            )
    if unplanned_days:
        lines.append("unplanned_completed_days:")
        for day in unplanned_days:
            lines.append(f"- {day} | {completed_dates[day]}")
    return "\n".join(lines) + "\n"


def _snapshot_recent_enough(snapshot: JsonMap | None) -> bool:
    """Return true when a snapshot is younger than the configured current-week TTL."""

    meta = _as_meta(snapshot or {})
    created_at = meta.get("created_at")
    if not isinstance(created_at, str) or not created_at:
        return False
    try:
        normalized = created_at.replace("Z", "+00:00")
        created = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    if created.tzinfo is not None:
        created = created.astimezone(UTC)
    max_age_hours = float(os.getenv("RPS_CURRENT_WEEK_STATUS_MAX_AGE_HOURS", "2"))
    return created >= datetime.now(UTC) - timedelta(hours=max_age_hours)


def _join_prompt_blocks(title: str, snapshot_type: ArtifactType, snapshot: JsonMap) -> str:
    meta = _as_meta(snapshot)
    data = snapshot.get("data") if isinstance(snapshot, dict) else None
    data_map = data if isinstance(data, dict) else {}
    prompt_blocks = data_map.get("prompt_blocks")
    if not isinstance(prompt_blocks, dict):
        return ""
    lines = [
        f"**{title}**",
        (
            "Use this code-owned derived snapshot as authoritative runtime memory for already-resolved facts. "
            "Do not reload the same artefacts just to rediscover values already present here."
        ),
    ]
    version_key = meta.get("version_key")
    if isinstance(version_key, str):
        lines.append(f"snapshot_ref: {ARTIFACT_PATHS[snapshot_type].filename_prefix}_{version_key}.json")
    source_versions = data_map.get("source_versions")
    if isinstance(source_versions, dict) and source_versions:
        lines.append("source_versions:")
        for key in sorted(source_versions):
            value = source_versions[key]
            lines.append(f"- {key}: {value}")
    lines.append("")
    for key in prompt_blocks:
        value = prompt_blocks[key]
        if isinstance(value, str) and value.strip():
            lines.append(value.rstrip())
    return "\n".join(lines).rstrip() + "\n"


def build_athlete_state_snapshot_document(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    target_week: IsoWeek,
    availability_payload: JsonMap | None = None,
    planning_events_payload: JsonMap | None = None,
    logistics_payload: JsonMap | None = None,
    zone_model_payload: JsonMap | None = None,
    wellness_payload: JsonMap | None = None,
    athlete_profile_payload: JsonMap | None = None,
    kpi_profile_payload: JsonMap | None = None,
    selection_payload: JsonMap | None = None,
) -> JsonMap:
    """Build a persisted athlete/input/pipeline state snapshot for planners."""
    athlete_block = build_resolved_athlete_context_block(store, athlete_id)
    kpi_block = build_resolved_kpi_context_block(store, athlete_id)
    availability_block = build_resolved_availability_context_block(store, athlete_id)
    logistics_block = build_resolved_logistics_context_block(store, athlete_id, target_week)
    planning_events_block = build_resolved_planning_events_context_block(store, athlete_id, target_week)
    zone_model_block = build_resolved_zone_model_context_block(store, athlete_id)
    wellness_block = _build_wellness_prompt_block(wellness_payload)
    selected_scenarios_payload = _try_load_latest(store, athlete_id, ArtifactType.SEASON_SCENARIOS) or {}
    selection_binding = resolve_bound_season_selection(
        season_scenarios_payload=selected_scenarios_payload,
        selection_payload=selection_payload or {},
        selected_scenario_id=None,
    )
    selected_scenario_contract_block = (
        str(selection_binding.get("selected_scenario_contract_markdown") or "")
        if bool(selection_binding.get("ok"))
        else ""
    )
    selected_scenario_binding_status = ""
    if not bool(selection_binding.get("ok")):
        selected_scenario_binding_status = (
            "**Selected Scenario Binding Status**\n"
            f"binding_status: {selection_binding.get('reason_code') or 'unknown'}\n"
            f"binding_reason: {selection_binding.get('reason_message') or 'Selected scenario binding failed.'}\n"
        )

    prompt_blocks = _non_empty_prompt_blocks(
        {
            "athlete": athlete_block,
            "kpi": kpi_block,
            "availability": availability_block,
            "logistics": logistics_block,
            "planning_events": planning_events_block,
            "zone_model": zone_model_block,
            "wellness": wellness_block,
            "selected_scenario_binding_status": selected_scenario_binding_status,
            "selected_scenario_contract": selected_scenario_contract_block,
        }
    )

    source_versions = _source_versions_map(
        [
            ("athlete_profile", ArtifactType.ATHLETE_PROFILE, athlete_profile_payload or {}),
            ("kpi_profile", ArtifactType.KPI_PROFILE, kpi_profile_payload or {}),
            ("season_scenarios", ArtifactType.SEASON_SCENARIOS, selected_scenarios_payload or {}),
            ("season_scenario_selection", ArtifactType.SEASON_SCENARIO_SELECTION, selection_payload or {}),
            ("availability", ArtifactType.AVAILABILITY, availability_payload or {}),
            ("planning_events", ArtifactType.PLANNING_EVENTS, planning_events_payload or {}),
            ("logistics", ArtifactType.LOGISTICS, logistics_payload or {}),
            ("zone_model", ArtifactType.ZONE_MODEL, zone_model_payload or {}),
            ("wellness", ArtifactType.WELLNESS, wellness_payload or {}),
        ]
    )

    trace_data = [
        ref
        for ref in (
            _trace_ref(ArtifactType.ATHLETE_PROFILE, athlete_profile_payload or {}),
            _trace_ref(ArtifactType.KPI_PROFILE, kpi_profile_payload or {}),
            _trace_ref(ArtifactType.SEASON_SCENARIO_SELECTION, selection_payload or {}),
            _trace_ref(ArtifactType.AVAILABILITY, availability_payload or {}),
            _trace_ref(ArtifactType.ZONE_MODEL, zone_model_payload or {}),
            _trace_ref(ArtifactType.WELLNESS, wellness_payload or {}),
        )
        if ref is not None
    ]
    trace_events = [
        ref
        for ref in (
            _trace_ref(ArtifactType.PLANNING_EVENTS, planning_events_payload or {}),
            _trace_ref(ArtifactType.LOGISTICS, logistics_payload or {}),
        )
        if ref is not None
    ]

    target_label = f"{target_week.year:04d}-{target_week.week:02d}"
    return {
        "meta": {
            "artifact_type": ArtifactType.ATHLETE_STATE_SNAPSHOT.value,
            "schema_id": "AthleteStateSnapshotInterface",
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "version": SNAPSHOT_VERSION,
            "authority": "Derived",
            "owner_agent": SNAPSHOT_OWNER_AGENT,
            "run_id": "pending",
            "created_at": "1970-01-01T00:00:00Z",
            "scope": "Context",
            "iso_week": target_label,
            "iso_week_range": f"{target_label}--{target_label}",
            "temporal_scope": _temporal_scope_for_week(target_week),
            "trace_upstream": [],
            "trace_data": trace_data,
            "trace_events": trace_events,
            "data_confidence": "HIGH",
            "notes": "Code-owned derived athlete/input/pipeline memory snapshot for planner injection.",
        },
        "data": {
            "target_iso_week": target_label,
            "source_versions": source_versions,
            "prompt_blocks": prompt_blocks,
        },
    }


def build_planning_context_snapshot_document(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    target_week: IsoWeek,
    phase_info: SeasonPlanPhaseInfo,
    season_plan_payload: JsonMap,
    phase_range: IsoWeekRange,
    phase_guardrails_payload: JsonMap | None = None,
    phase_structure_payload: JsonMap | None = None,
    availability_payload: JsonMap | None = None,
    planning_events_payload: JsonMap | None = None,
    season_phase_feed_forward_payload: JsonMap | None = None,
    phase_feed_forward_payload: JsonMap | None = None,
    activities_actual_version: str | None = None,
    activities_trend_version: str | None = None,
    des_analysis_payload: JsonMap | None = None,
    des_analysis_version: str | None = None,
    evidence_alignment_payload: JsonMap | None = None,
) -> JsonMap:
    """Build a target-week planning snapshot for phase/week planners."""
    phase_block = build_resolved_phase_context_block(target_week=target_week, phase_info=phase_info)
    recovery_block = build_resolved_recovery_context_block(
        availability_payload=availability_payload,
        season_plan_payload=season_plan_payload,
        phase_guardrails_payload=phase_guardrails_payload,
        phase_structure_payload=phase_structure_payload,
    )
    event_priority_block = build_resolved_event_priority_context_block(
        target_week=target_week,
        season_plan_payload=season_plan_payload,
        phase_guardrails_payload=phase_guardrails_payload,
        planning_events_payload=planning_events_payload,
    )
    load_governance_block = build_resolved_load_governance_context_block(
        target_week=target_week,
        season_plan_payload=season_plan_payload,
        phase_guardrails_payload=phase_guardrails_payload,
        phase_structure_payload=phase_structure_payload,
    )
    season_ff_block = build_resolved_feed_forward_applicability_context_block(
        label="season_phase_feed_forward",
        feed_forward_payload=season_phase_feed_forward_payload,
        target_week=target_week,
    )
    phase_ff_block = build_resolved_feed_forward_applicability_context_block(
        label="phase_feed_forward",
        feed_forward_payload=phase_feed_forward_payload,
        target_week=target_week,
    )
    activity_block = ""
    if activities_actual_version and activities_trend_version:
        activity_block = build_resolved_activity_context_block(
            store,
            athlete_id,
            target_week=target_week,
            activities_actual_version=activities_actual_version,
            activities_trend_version=activities_trend_version,
        )
    des_report_block = _build_advisory_report_block(
        des_analysis_payload,
        report_version_key=des_analysis_version,
    )
    evidence_alignment_block = _build_json_context_block(
        "Evidence Alignment",
        evidence_alignment_payload,
    )
    season_contract = _as_map(_as_data(season_plan_payload).get("selected_scenario_contract"))
    phase_guardrails_data = _as_data(phase_guardrails_payload)
    phase_structure_data = _as_data(phase_structure_payload)
    phase_contract = _as_map(phase_guardrails_data.get("inherited_scenario_contract"))
    selected_contract_block = ""
    if season_contract:
        selected_contract_block = (
            "**Selected Scenario Contract**\n"
            f"selected_scenario_id: {_as_str(season_contract.get('selected_scenario_id'))}\n"
            f"load_posture: {_as_str(season_contract.get('load_posture'))}\n"
            f"recovery_margin: {_as_str(season_contract.get('recovery_margin'))}\n"
            f"fatigue_exposure: {_as_str(season_contract.get('fatigue_exposure'))}\n"
            f"specificity_density: {_as_str(season_contract.get('specificity_density'))}\n"
        )
    inherited_contract_block = ""
    inherited_planning_posture_block = ""
    if phase_contract:
        inherited_contract_block = (
            "**Inherited Scenario Contract (Posture Ceiling)**\n"
            f"selected_scenario_id: {_as_str(phase_contract.get('selected_scenario_id'))}\n"
            f"load_posture: {_as_str(phase_contract.get('load_posture'))}\n"
            f"recovery_margin: {_as_str(phase_contract.get('recovery_margin'))}\n"
            f"fatigue_exposure: {_as_str(phase_contract.get('fatigue_exposure'))}\n"
            f"specificity_density: {_as_str(phase_contract.get('specificity_density'))}\n"
        )
        inherited_planning_posture_block = (
            "**Inherited Planning Posture**\n"
            f"selected_scenario_id: {_as_str(phase_contract.get('selected_scenario_id'))}\n"
            f"load_posture: {_as_str(phase_contract.get('load_posture'))}\n"
            f"recovery_margin: {_as_str(phase_contract.get('recovery_margin'))}\n"
            f"fatigue_exposure: {_as_str(phase_contract.get('fatigue_exposure'))}\n"
            f"specificity_density: {_as_str(phase_contract.get('specificity_density'))}\n"
        )
    phase_authority_block = ""
    if phase_guardrails_data or phase_structure_data:
        semantics = _as_map(phase_guardrails_data.get("allowed_forbidden_semantics"))
        structure_elements = _as_map(phase_structure_data.get("structural_phase_elements"))
        load_guardrails = _as_map(phase_guardrails_data.get("load_guardrails"))
        upstream_intent = _as_map(phase_structure_data.get("upstream_intent"))
        phase_summary = _as_map(phase_guardrails_data.get("phase_summary"))
        target_week_key = f"{target_week.year:04d}-{target_week.week:02d}"
        exact_band_line = "target_week_band: N/A"
        for entry in _as_list(load_guardrails.get("weekly_kj_bands")):
            entry_map = _as_map(entry)
            if _as_str(entry_map.get("week")) != target_week_key:
                continue
            band = _as_map(entry_map.get("band"))
            exact_band_line = (
                f"target_week_band: {_as_str(entry_map.get('week'))} "
                f"{_as_str(band.get('min'))}-{_as_str(band.get('max'))}"
            )
            break
        allowed_domains = _as_list(structure_elements.get("allowed_intensity_domains")) or _as_list(
            semantics.get("allowed_intensity_domains")
        )
        allowed_modalities = _as_list(structure_elements.get("allowed_load_modalities")) or _as_list(
            semantics.get("allowed_load_modalities")
        )
        phase_authority_block = (
            "**Exact Phase Authority**\n"
            f"phase_intent: {_as_str(upstream_intent.get('phase_intent') or phase_summary.get('phase_intent'))}\n"
            f"phase_primary_objective: {_as_str(upstream_intent.get('primary_objective') or phase_summary.get('primary_objective'))}\n"
            f"allowed_intensity_domains: {', '.join(str(item) for item in allowed_domains)}\n"
            f"forbidden_intensity_domains: {', '.join(str(item) for item in _as_list(semantics.get('forbidden_intensity_domains')))}\n"
            f"allowed_load_modalities: {', '.join(str(item) for item in allowed_modalities)}\n"
            f"{exact_band_line}\n"
            "s5_authority: feasibility_only\n"
        )

    prompt_blocks = _non_empty_prompt_blocks(
        {
            "phase": phase_block,
            "recovery": recovery_block,
            "event_priority": event_priority_block,
            "load_governance": load_governance_block,
            "season_feed_forward": season_ff_block,
            "phase_feed_forward": phase_ff_block,
            "activity": activity_block,
            "des_report": des_report_block,
            "evidence_alignment": evidence_alignment_block,
            "selected_scenario_contract": selected_contract_block,
            "inherited_scenario_contract": inherited_contract_block,
            "inherited_planning_posture": inherited_planning_posture_block,
            "phase_authority": phase_authority_block,
        }
    )

    source_versions = _source_versions_map(
        [
            ("season_plan", ArtifactType.SEASON_PLAN, season_plan_payload),
            ("phase_guardrails", ArtifactType.PHASE_GUARDRAILS, phase_guardrails_payload or {}),
            ("phase_structure", ArtifactType.PHASE_STRUCTURE, phase_structure_payload or {}),
            ("availability", ArtifactType.AVAILABILITY, availability_payload or {}),
            ("planning_events", ArtifactType.PLANNING_EVENTS, planning_events_payload or {}),
            ("season_phase_feed_forward", ArtifactType.SEASON_PHASE_FEED_FORWARD, season_phase_feed_forward_payload or {}),
            ("phase_feed_forward", ArtifactType.PHASE_FEED_FORWARD, phase_feed_forward_payload or {}),
        ]
    )
    if activities_actual_version:
        source_versions["activities_actual"] = activities_actual_version
    if activities_trend_version:
        source_versions["activities_trend"] = activities_trend_version
    if des_analysis_version:
        source_versions["des_analysis_report"] = des_analysis_version

    trace_upstream = [
        ref
        for ref in (
            _trace_ref(ArtifactType.SEASON_PLAN, season_plan_payload),
            _trace_ref(ArtifactType.PHASE_GUARDRAILS, phase_guardrails_payload or {}),
            _trace_ref(ArtifactType.PHASE_STRUCTURE, phase_structure_payload or {}),
            _trace_ref(ArtifactType.DES_ANALYSIS_REPORT, des_analysis_payload or {}),
            _trace_ref(ArtifactType.SEASON_PHASE_FEED_FORWARD, season_phase_feed_forward_payload or {}),
            _trace_ref(ArtifactType.PHASE_FEED_FORWARD, phase_feed_forward_payload or {}),
        )
        if ref is not None
    ]
    trace_data = [
        ref
        for ref in (
            _trace_ref(ArtifactType.AVAILABILITY, availability_payload or {}),
        )
        if ref is not None
    ]
    trace_events = [
        ref
        for ref in (
            _trace_ref(ArtifactType.PLANNING_EVENTS, planning_events_payload or {}),
        )
        if ref is not None
    ]

    target_label = f"{target_week.year:04d}-{target_week.week:02d}"
    phase_range_label = f"{phase_range.start.year:04d}-{phase_range.start.week:02d}--{phase_range.end.year:04d}-{phase_range.end.week:02d}"
    return {
        "meta": {
            "artifact_type": ArtifactType.PLANNING_CONTEXT_SNAPSHOT.value,
            "schema_id": "PlanningContextSnapshotInterface",
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "version": SNAPSHOT_VERSION,
            "authority": "Derived",
            "owner_agent": SNAPSHOT_OWNER_AGENT,
            "run_id": "pending",
            "created_at": "1970-01-01T00:00:00Z",
            "scope": "Context",
            "iso_week": target_label,
            "iso_week_range": f"{target_label}--{target_label}",
            "temporal_scope": _temporal_scope_for_week(target_week),
            "trace_upstream": trace_upstream,
            "trace_data": trace_data,
            "trace_events": trace_events,
            "data_confidence": "HIGH",
            "notes": f"Code-owned derived planning memory snapshot for target week {target_label} within phase {phase_range_label}.",
        },
        "data": {
            "target_iso_week": target_label,
            "phase_iso_week_range": phase_range_label,
            "source_versions": source_versions,
            "prompt_blocks": prompt_blocks,
        },
    }


def save_athlete_state_snapshot(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    target_week: IsoWeek,
    run_id: str,
    athlete_profile_payload: JsonMap | None = None,
    kpi_profile_payload: JsonMap | None = None,
    selection_payload: JsonMap | None = None,
    availability_payload: JsonMap | None = None,
    planning_events_payload: JsonMap | None = None,
    logistics_payload: JsonMap | None = None,
    zone_model_payload: JsonMap | None = None,
    wellness_payload: JsonMap | None = None,
) -> JsonMap:
    snapshot = build_athlete_state_snapshot_document(
        store,
        athlete_id,
        target_week=target_week,
        athlete_profile_payload=athlete_profile_payload,
        kpi_profile_payload=kpi_profile_payload,
        selection_payload=selection_payload,
        availability_payload=availability_payload,
        planning_events_payload=planning_events_payload,
        logistics_payload=logistics_payload,
        zone_model_payload=zone_model_payload,
        wellness_payload=wellness_payload,
    )
    target_label = f"{target_week.year:04d}-{target_week.week:02d}"
    store.save_document(
        athlete_id,
        ArtifactType.ATHLETE_STATE_SNAPSHOT,
        target_label,
        snapshot,
        producer_agent=SNAPSHOT_PRODUCER_AGENT,
        run_id=run_id,
        update_latest=True,
    )
    return _load_latest_snapshot(store, athlete_id, ArtifactType.ATHLETE_STATE_SNAPSHOT)


def save_planning_context_snapshot(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    target_week: IsoWeek,
    phase_info: SeasonPlanPhaseInfo,
    season_plan_payload: JsonMap,
    phase_range: IsoWeekRange,
    run_id: str,
    phase_guardrails_payload: JsonMap | None = None,
    phase_structure_payload: JsonMap | None = None,
    availability_payload: JsonMap | None = None,
    planning_events_payload: JsonMap | None = None,
    season_phase_feed_forward_payload: JsonMap | None = None,
    phase_feed_forward_payload: JsonMap | None = None,
    activities_actual_version: str | None = None,
    activities_trend_version: str | None = None,
    des_analysis_payload: JsonMap | None = None,
    des_analysis_version: str | None = None,
    evidence_alignment_payload: JsonMap | None = None,
) -> JsonMap:
    snapshot = build_planning_context_snapshot_document(
        store,
        athlete_id,
        target_week=target_week,
        phase_info=phase_info,
        season_plan_payload=season_plan_payload,
        phase_range=phase_range,
        phase_guardrails_payload=phase_guardrails_payload,
        phase_structure_payload=phase_structure_payload,
        availability_payload=availability_payload,
        planning_events_payload=planning_events_payload,
        season_phase_feed_forward_payload=season_phase_feed_forward_payload,
        phase_feed_forward_payload=phase_feed_forward_payload,
        activities_actual_version=activities_actual_version,
        activities_trend_version=activities_trend_version,
        des_analysis_payload=des_analysis_payload,
        des_analysis_version=des_analysis_version,
        evidence_alignment_payload=evidence_alignment_payload,
    )
    target_label = f"{target_week.year:04d}-{target_week.week:02d}"
    store.save_document(
        athlete_id,
        ArtifactType.PLANNING_CONTEXT_SNAPSHOT,
        target_label,
        snapshot,
        producer_agent=SNAPSHOT_PRODUCER_AGENT,
        run_id=run_id,
        update_latest=True,
    )
    return _load_latest_snapshot(store, athlete_id, ArtifactType.PLANNING_CONTEXT_SNAPSHOT)


def build_current_week_status_snapshot_document(
    *,
    target_week: IsoWeek,
    week_plan_payload: JsonMap | None = None,
    current_week_actual_payload: JsonMap | None = None,
) -> JsonMap:
    """Build a persisted current-week status snapshot for Coach-only plan/actual context."""

    prompt_blocks = _non_empty_prompt_blocks(
        {
            "current_week_actuals": _build_current_week_actuals_block(current_week_actual_payload, target_week),
            "plan_vs_actual": _build_plan_vs_actual_block(week_plan_payload, current_week_actual_payload, target_week),
        }
    )
    target_label = f"{target_week.year:04d}-{target_week.week:02d}"
    source_versions = _source_versions_map([("week_plan", ArtifactType.WEEK_PLAN, week_plan_payload or {})])
    actual_meta = _as_meta(current_week_actual_payload or {})
    actual_version = actual_meta.get("version_key") or actual_meta.get("iso_week")
    if isinstance(actual_version, str) and actual_version:
        source_versions["current_week_activities_actual"] = actual_version
    trace_upstream = [ref for ref in (_trace_ref(ArtifactType.WEEK_PLAN, week_plan_payload or {}),) if ref is not None]
    return {
        "meta": {
            "artifact_type": ArtifactType.CURRENT_WEEK_STATUS_SNAPSHOT.value,
            "schema_id": "CurrentWeekStatusSnapshotInterface",
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "version": SNAPSHOT_VERSION,
            "authority": "Derived",
            "owner_agent": SNAPSHOT_OWNER_AGENT,
            "run_id": "pending",
            "created_at": "1970-01-01T00:00:00Z",
            "scope": "Context",
            "iso_week": target_label,
            "iso_week_range": f"{target_label}--{target_label}",
            "temporal_scope": _temporal_scope_for_week(target_week),
            "trace_upstream": trace_upstream,
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "MEDIUM",
            "notes": f"Code-owned derived current-week status snapshot for target week {target_label}.",
        },
        "data": {
            "target_iso_week": target_label,
            "source_versions": source_versions,
            "prompt_blocks": prompt_blocks,
        },
    }


def save_current_week_status_snapshot(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    target_week: IsoWeek,
    run_id: str,
    week_plan_payload: JsonMap | None = None,
    current_week_actual_payload: JsonMap | None = None,
) -> JsonMap:
    """Persist the current-week status snapshot for the selected week."""

    snapshot = build_current_week_status_snapshot_document(
        target_week=target_week,
        week_plan_payload=week_plan_payload,
        current_week_actual_payload=current_week_actual_payload,
    )
    target_label = f"{target_week.year:04d}-{target_week.week:02d}"
    store.save_document(
        athlete_id,
        ArtifactType.CURRENT_WEEK_STATUS_SNAPSHOT,
        target_label,
        snapshot,
        producer_agent=SNAPSHOT_PRODUCER_AGENT,
        run_id=run_id,
        update_latest=True,
    )
    return _load_latest_snapshot(store, athlete_id, ArtifactType.CURRENT_WEEK_STATUS_SNAPSHOT)


def _current_week_status_snapshot_has_required_tables(snapshot: JsonMap | None) -> bool:
    """Return whether a persisted current-week status snapshot includes required table sections."""

    if not isinstance(snapshot, dict):
        return False
    data = _as_data(snapshot)
    prompt_blocks = data.get("prompt_blocks")
    if not isinstance(prompt_blocks, dict):
        return False
    actuals_block = _as_str(prompt_blocks.get("current_week_actuals"))
    plan_vs_actual_block = _as_str(prompt_blocks.get("plan_vs_actual"))
    actuals_map = _simple_key_value_map(actuals_block)
    plan_map = _simple_key_value_map(plan_vs_actual_block)
    completed_count = _int_from_text(actuals_map.get("completed_sessions_count"))
    open_days_count = _int_from_text(plan_map.get("open_planned_days_count"))
    if completed_count > 0 and "completed_sessions_table:" not in actuals_block:
        return False
    return not (open_days_count > 0 and "open_planned_days_table:" not in plan_vs_actual_block)


def ensure_current_week_status_snapshot(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    target_week: IsoWeek,
    run_id: str,
    week_plan_payload: JsonMap | None = None,
) -> JsonMap:
    """Load or refresh the current-week status snapshot for Coach."""

    target_label = f"{target_week.year:04d}-{target_week.week:02d}"
    current_week = IsoWeek(*date.today().isocalendar()[:2])
    current_week_plan_version = _compact_source_version(ArtifactType.WEEK_PLAN, week_plan_payload or {})
    existing_version = store.resolve_week_version_key(athlete_id, ArtifactType.CURRENT_WEEK_STATUS_SNAPSHOT, target_label)
    existing: JsonMap | None = None
    if existing_version:
        try:
            payload = store.load_version(athlete_id, ArtifactType.CURRENT_WEEK_STATUS_SNAPSHOT, existing_version)
        except FileNotFoundError:
            payload = None
        existing = payload if isinstance(payload, dict) else None
    if isinstance(existing, dict) and target_week != current_week:
        return existing
    existing_source_versions = _as_data(existing).get("source_versions") if isinstance(existing, dict) else None
    existing_week_plan_version = (
        existing_source_versions.get("week_plan")
        if isinstance(existing_source_versions, dict)
        else None
    )
    if (
        isinstance(existing, dict)
        and _snapshot_recent_enough(existing)
        and existing_week_plan_version == current_week_plan_version
        and _current_week_status_snapshot_has_required_tables(existing)
    ):
        return existing

    if target_week != current_week:
        return existing if isinstance(existing, dict) else {}

    current_week_actual_payload = fetch_current_week_activities_actual_payload(
        athlete_id=athlete_id,
        year=target_week.year,
        week=target_week.week,
    )
    return save_current_week_status_snapshot(
        store,
        athlete_id,
        target_week=target_week,
        run_id=run_id,
        week_plan_payload=week_plan_payload,
        current_week_actual_payload=current_week_actual_payload,
    )


def build_advisory_memory_document(
    *,
    target_week: IsoWeek,
    season_plan_payload: JsonMap | None = None,
    week_plan_payload: JsonMap | None = None,
    des_analysis_payload: JsonMap | None = None,
    season_phase_feed_forward_payload: JsonMap | None = None,
    phase_feed_forward_payload: JsonMap | None = None,
) -> JsonMap:
    """Build a non-binding narrative memory snapshot from recent planning outputs."""
    prompt_blocks = _non_empty_prompt_blocks(
        {
            "season": _build_advisory_season_block(season_plan_payload),
            "selected_scenario_posture": _build_advisory_selected_contract_block(season_plan_payload),
            "week": _build_advisory_week_block(week_plan_payload),
            "current_week_plan": _build_current_week_plan_block(week_plan_payload),
            "des_report": _build_advisory_report_block(des_analysis_payload),
            "season_phase_feed_forward": _build_advisory_season_ff_block(season_phase_feed_forward_payload),
            "phase_feed_forward": _build_advisory_phase_ff_block(phase_feed_forward_payload),
            "inherited_posture": _build_advisory_inherited_posture_block(phase_feed_forward_payload),
        }
    )
    target_label = f"{target_week.year:04d}-{target_week.week:02d}"
    source_versions = _source_versions_map(
        [
            ("season_plan", ArtifactType.SEASON_PLAN, season_plan_payload or {}),
            ("week_plan", ArtifactType.WEEK_PLAN, week_plan_payload or {}),
            ("des_analysis_report", ArtifactType.DES_ANALYSIS_REPORT, des_analysis_payload or {}),
            (
                "season_phase_feed_forward",
                ArtifactType.SEASON_PHASE_FEED_FORWARD,
                season_phase_feed_forward_payload or {},
            ),
            ("phase_feed_forward", ArtifactType.PHASE_FEED_FORWARD, phase_feed_forward_payload or {}),
        ]
    )
    trace_upstream = [
        ref
        for ref in (
            _trace_ref(ArtifactType.SEASON_PLAN, season_plan_payload or {}),
            _trace_ref(ArtifactType.WEEK_PLAN, week_plan_payload or {}),
            _trace_ref(ArtifactType.DES_ANALYSIS_REPORT, des_analysis_payload or {}),
            _trace_ref(
                ArtifactType.SEASON_PHASE_FEED_FORWARD,
                season_phase_feed_forward_payload or {},
            ),
            _trace_ref(ArtifactType.PHASE_FEED_FORWARD, phase_feed_forward_payload or {}),
        )
        if ref is not None
    ]
    return {
        "meta": {
            "artifact_type": ArtifactType.ADVISORY_MEMORY.value,
            "schema_id": "AdvisoryMemoryInterface",
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "version": SNAPSHOT_VERSION,
            "authority": "Advisory",
            "owner_agent": SNAPSHOT_OWNER_AGENT,
            "run_id": "pending",
            "created_at": "1970-01-01T00:00:00Z",
            "scope": "Context",
            "iso_week": target_label,
            "iso_week_range": f"{target_label}--{target_label}",
            "temporal_scope": _temporal_scope_for_week(target_week),
            "trace_upstream": trace_upstream,
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "MEDIUM",
            "notes": f"Non-binding narrative memory derived from latest planning outputs for target week {target_label}.",
        },
        "data": {
            "target_iso_week": target_label,
            "source_versions": source_versions,
            "prompt_blocks": prompt_blocks,
        },
    }


def save_advisory_memory(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    target_week: IsoWeek,
    run_id: str,
    season_plan_payload: JsonMap | None = None,
    week_plan_payload: JsonMap | None = None,
    des_analysis_payload: JsonMap | None = None,
    season_phase_feed_forward_payload: JsonMap | None = None,
    phase_feed_forward_payload: JsonMap | None = None,
) -> JsonMap:
    snapshot = build_advisory_memory_document(
        target_week=target_week,
        season_plan_payload=season_plan_payload,
        week_plan_payload=week_plan_payload,
        des_analysis_payload=des_analysis_payload,
        season_phase_feed_forward_payload=season_phase_feed_forward_payload,
        phase_feed_forward_payload=phase_feed_forward_payload,
    )
    target_label = f"{target_week.year:04d}-{target_week.week:02d}"
    store.save_document(
        athlete_id,
        ArtifactType.ADVISORY_MEMORY,
        target_label,
        snapshot,
        producer_agent=SNAPSHOT_PRODUCER_AGENT,
        run_id=run_id,
        update_latest=True,
    )
    return _load_latest_snapshot(store, athlete_id, ArtifactType.ADVISORY_MEMORY)


def build_athlete_state_snapshot_prompt_block(snapshot: JsonMap) -> str:
    """Render snapshot content for planner injection."""
    return _join_prompt_blocks("Athlete State Snapshot", ArtifactType.ATHLETE_STATE_SNAPSHOT, snapshot)


def build_planning_context_snapshot_prompt_block(snapshot: JsonMap) -> str:
    """Render target-week planning snapshot content for planner injection."""
    return _join_prompt_blocks("Planning Context Snapshot", ArtifactType.PLANNING_CONTEXT_SNAPSHOT, snapshot)


def build_current_week_status_snapshot_prompt_block(snapshot: JsonMap) -> str:
    """Render current-week status snapshot content for Coach injection."""
    return _join_prompt_blocks("Current Week Status Snapshot", ArtifactType.CURRENT_WEEK_STATUS_SNAPSHOT, snapshot)


def build_advisory_memory_prompt_block(snapshot: JsonMap) -> str:
    """Render non-binding advisory memory for coach/conversational contexts."""
    meta = _as_meta(snapshot)
    data = snapshot.get("data") if isinstance(snapshot, dict) else None
    data_map = data if isinstance(data, dict) else {}
    prompt_blocks = data_map.get("prompt_blocks")
    if not isinstance(prompt_blocks, dict) or not prompt_blocks:
        return ""
    lines = [
        "**Advisory Memory**",
        (
            "Use this code-owned derived memory as non-binding narrative context. "
            "It may summarize recent plans and reports, but it never overrides authoritative artefacts or snapshots."
        ),
    ]
    version_key = meta.get("version_key")
    if isinstance(version_key, str):
        lines.append(f"snapshot_ref: {ARTIFACT_PATHS[ArtifactType.ADVISORY_MEMORY].filename_prefix}_{version_key}.json")
    lines.append("")
    for key in prompt_blocks:
        value = prompt_blocks[key]
        if isinstance(value, str) and value.strip():
            lines.append(value.rstrip())
    return "\n".join(lines).rstrip() + "\n"
