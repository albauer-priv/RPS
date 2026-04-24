"""Helpers for resolving deterministic planner context before agent calls."""

from __future__ import annotations

from datetime import date

from rps.workspace.iso_helpers import IsoWeek, IsoWeekRange, parse_iso_week, week_index
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.phase_resolution import date_to_iso_week
from rps.workspace.season_plan_service import SeasonPlanPhaseInfo
from rps.workspace.types import ArtifactType


def _format_activity_session_line(activity: dict[str, object]) -> str | None:
    """Return a compact line for a key activity session."""
    day = activity.get("day")
    activity_type = activity.get("type")
    moving_time = activity.get("moving_time")
    work_kj = activity.get("work_kj")
    load_tss = activity.get("load_tss")
    intensity_factor = activity.get("intensity_factor")
    if not isinstance(day, str) or not day:
        return None
    if not isinstance(activity_type, str) or not activity_type:
        activity_type = "activity"
    parts = [f"- {day} {activity_type}"]
    if isinstance(moving_time, str) and moving_time:
        parts.append(f"moving_time {moving_time}")
    if isinstance(work_kj, (int, float)):
        parts.append(f"work_kj {work_kj}")
    if isinstance(load_tss, (int, float)):
        parts.append(f"load_tss {load_tss}")
    if isinstance(intensity_factor, (int, float)):
        parts.append(f"if {intensity_factor}")
    return ", ".join(parts)


def build_resolved_activity_context_block(
    store: LocalArtifactStore,
    athlete_id: str,
    *,
    target_week: IsoWeek,
    activities_actual_version: str | None = None,
    activities_trend_version: str | None = None,
) -> str:
    """Build a compact historical activity context block for planners."""
    if not activities_actual_version or not activities_trend_version:
        return ""
    try:
        trend_payload = store.load_version(athlete_id, ArtifactType.ACTIVITIES_TREND, activities_trend_version)
        actual_payload = store.load_version(athlete_id, ArtifactType.ACTIVITIES_ACTUAL, activities_actual_version)
    except Exception:
        return ""
    if not isinstance(trend_payload, dict) or not isinstance(actual_payload, dict):
        return ""

    trend_data = trend_payload.get("data")
    weekly_trends = trend_data.get("weekly_trends") if isinstance(trend_data, dict) else None
    trend_week = parse_iso_week(activities_trend_version)
    trend_entry = None
    if isinstance(weekly_trends, list) and trend_week is not None:
        for item in weekly_trends:
            if not isinstance(item, dict):
                continue
            if item.get("year") == trend_week.year and item.get("iso_week") == trend_week.week:
                trend_entry = item
                break
        if trend_entry is None and weekly_trends:
            trend_entry = weekly_trends[-1] if isinstance(weekly_trends[-1], dict) else None

    actual_data = actual_payload.get("data")
    activities = actual_data.get("activities") if isinstance(actual_data, dict) else None
    if not isinstance(activities, list):
        activities = []

    lines = [
        "**Resolved Activity Context**",
        "Use these historical activity facts directly; do not reload raw activity artefacts just to rediscover the same recent load, durability, or long-ride signals when they are provided here.",
        f"target_iso_week: {target_week.year:04d}-{target_week.week:02d}",
        f"historical_reference_week: {activities_trend_version}",
        f"activities_actual_version: {activities_actual_version}",
        f"activities_trend_version: {activities_trend_version}",
    ]

    if isinstance(trend_entry, dict):
        weekly_aggregates = trend_entry.get("weekly_aggregates")
        if isinstance(weekly_aggregates, dict):
            for key in ("activity_count", "moving_time", "distance_km", "work_kj", "load_tss"):
                value = weekly_aggregates.get(key)
                if value is not None:
                    lines.append(f"weekly_aggregates.{key}: {value}")
        intensity = trend_entry.get("intensity_load_metrics")
        if isinstance(intensity, dict):
            for key in (
                "intensity_factor",
                "decoupling_percent",
                "durability_index",
                "efficiency_factor",
                "ftp_estimated_w",
            ):
                value = intensity.get(key)
                if value is not None:
                    lines.append(f"intensity_load_metrics.{key}: {value}")
        distribution = trend_entry.get("distribution_metrics")
        if isinstance(distribution, dict):
            for key in (
                "z1_z2_time_percent",
                "z5_time_percent",
                "z2_share_power_percent",
                "back_to_back_z2_days_count",
            ):
                value = distribution.get(key)
                if value is not None:
                    lines.append(f"distribution_metrics.{key}: {value}")
        metrics = trend_entry.get("metrics")
        if isinstance(metrics, dict):
            for key in (
                "weekly_moving_time_total_min",
                "weekly_z2_time_total_min",
                "weekly_moving_time_max_min",
                "weekly_z2_time_max_min",
                "weekly_moving_time_180min_sum_min",
                "weekly_moving_time_240min_sum_min",
                "weekly_z2_time_180min_sum_min",
                "weekly_z2_time_240min_sum_min",
                "weekly_moving_time_des_base_sum_min",
                "weekly_moving_time_des_build_sum_min",
                "weekly_z2_time_des_base_sum_min",
                "weekly_z2_time_des_build_sum_min",
            ):
                value = metrics.get(key)
                if value is not None:
                    lines.append(f"metrics.{key}: {value}")
        flag_any = trend_entry.get("flag_any")
        if isinstance(flag_any, dict):
            for key in (
                "flag_long_ride_180min_bool",
                "flag_long_ride_240min_bool",
                "flag_des_long_base_candidate_bool",
                "flag_des_long_build_candidate_bool",
                "flag_brevet_long_candidate_bool",
            ):
                value = flag_any.get(key)
                if value is not None:
                    lines.append(f"flag_any.{key}: {value}")

    key_activities: list[tuple[float, dict[str, object]]] = []
    for activity in activities:
        if not isinstance(activity, dict):
            continue
        flags = activity.get("flags")
        if not isinstance(flags, dict):
            flags = {}
        score = 0.0
        if flags.get("flag_long_ride_240min_bool") is True:
            score += 5
        if flags.get("flag_long_ride_180min_bool") is True:
            score += 4
        if flags.get("flag_des_long_build_candidate_bool") is True:
            score += 3
        if flags.get("flag_des_long_base_candidate_bool") is True:
            score += 2
        if flags.get("flag_brevet_long_candidate_bool") is True:
            score += 2
        work_kj = activity.get("work_kj")
        if isinstance(work_kj, (int, float)):
            score += float(work_kj) / 10000.0
        key_activities.append((score, activity))
    key_activities.sort(key=lambda item: item[0], reverse=True)
    rendered = []
    for _, activity in key_activities[:3]:
        line = _format_activity_session_line(activity)
        if line:
            rendered.append(line)
    if rendered:
        lines.append("key_actual_sessions:")
        lines.extend(rendered)

    return "\n".join(lines) + "\n"


def build_resolved_athlete_context_block(store: LocalArtifactStore, athlete_id: str) -> str:
    """Build a deterministic athlete-profile summary from the latest athlete profile."""
    try:
        athlete_profile = store.load_latest(athlete_id, ArtifactType.ATHLETE_PROFILE)
    except Exception:
        return ""
    data = athlete_profile.get("data") if isinstance(athlete_profile, dict) else None
    profile_data = data if isinstance(data, dict) else {}
    profile = profile_data.get("profile") or {}
    objectives = profile_data.get("objectives") or {}
    if not isinstance(profile, dict):
        profile = {}
    if not isinstance(objectives, dict):
        objectives = {}

    lines: list[str] = []
    identity_lines: list[str] = []
    for key in ("athlete_id", "athlete_name", "location_time_zone", "sex", "age_group"):
        value = profile.get(key)
        if isinstance(value, str) and value:
            identity_lines.append(f"{key}: {value}")
    age = profile.get("age")
    if isinstance(age, (int, float)):
        identity_lines.append(f"age: {age}")
    body_mass = profile.get("body_mass_kg")
    if isinstance(body_mass, (int, float)):
        identity_lines.append(f"body_mass_kg: {body_mass}")
    training_age = profile.get("training_age_years")
    if isinstance(training_age, (int, float)):
        identity_lines.append(f"training_age_years: {training_age}")
    disciplines = profile.get("primary_disciplines")
    if isinstance(disciplines, list) and disciplines:
        identity_lines.append(
            "primary_disciplines: " + ", ".join(str(item) for item in disciplines if str(item).strip())
        )
    anchor = profile.get("endurance_anchor_w")
    if isinstance(anchor, (int, float)):
        identity_lines.append(f"endurance_anchor_w: {anchor}")
    ambition = profile.get("ambition_if_range")
    if isinstance(ambition, list | tuple) and len(ambition) == 2:
        identity_lines.append(f"ambition_if_range: [{ambition[0]}, {ambition[1]}]")
    primary_objective = objectives.get("primary")
    if isinstance(primary_objective, str) and primary_objective:
        identity_lines.append(f"primary_objective: {primary_objective}")

    if identity_lines:
        lines.append("**Resolved Athlete Context**")
        lines.append(
            "Use these athlete facts directly; do not search or reinterpret the same profile fields again when they are provided here."
        )
        lines.extend(identity_lines)

    return "\n".join(lines) + ("\n" if lines else "")


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


def _as_map(value: object) -> dict[str, object]:
    """Return a dict-like value or an empty mapping."""
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    """Return a list-like value or an empty list."""
    return value if isinstance(value, list) else []


def _find_week_band(entries: object, target_week: IsoWeek) -> dict[str, object] | None:
    """Return the weekly band entry matching the target week."""
    target_key = f"{target_week.year:04d}-{target_week.week:02d}"
    for entry in _as_list(entries):
        if not isinstance(entry, dict):
            continue
        if entry.get("week") == target_key:
            return entry
    return None


def build_resolved_recovery_context_block(
    *,
    availability_payload: dict[str, object] | None = None,
    season_plan_payload: dict[str, object] | None = None,
    phase_guardrails_payload: dict[str, object] | None = None,
    phase_structure_payload: dict[str, object] | None = None,
) -> str:
    """Build a compact recovery and recovery-protection summary."""
    availability_data = _as_map((availability_payload or {}).get("data"))
    season_data = _as_map((season_plan_payload or {}).get("data"))
    season_global = _as_map(season_data.get("global_constraints"))
    season_recovery = _as_map(season_global.get("recovery_protection"))
    guardrails_data = _as_map((phase_guardrails_payload or {}).get("data"))
    execution_non_negotiables = _as_map(guardrails_data.get("execution_non_negotiables"))
    structure_data = _as_map((phase_structure_payload or {}).get("data"))
    execution_principles = _as_map(structure_data.get("execution_principles"))
    structure_recovery = _as_map(execution_principles.get("recovery_protection"))

    fixed_rest_days = [str(x) for x in _as_list(availability_data.get("fixed_rest_days")) if str(x).strip()]
    season_fixed_rest_days = [str(x) for x in _as_list(season_recovery.get("fixed_rest_days")) if str(x).strip()]
    season_notes = [str(x) for x in _as_list(season_recovery.get("notes")) if str(x).strip()]
    structure_fixed_days = [str(x) for x in _as_list(structure_recovery.get("fixed_non_training_days")) if str(x).strip()]
    spacing_rules = [str(x) for x in _as_list(structure_recovery.get("mandatory_recovery_spacing_rules")) if str(x).strip()]
    forbidden_sequences = [str(x) for x in _as_list(structure_recovery.get("forbidden_sequences")) if str(x).strip()]

    lines: list[str] = []
    if any((fixed_rest_days, season_fixed_rest_days, season_notes, structure_fixed_days, spacing_rules, forbidden_sequences)):
        lines.extend([
            "**Resolved Recovery Context**",
            "Use these recovery-protection facts directly; do not reconstruct recovery anchors or spacing rules from raw season/phase text when they are provided here.",
        ])
    if fixed_rest_days:
        lines.append("availability.fixed_rest_days: " + ", ".join(fixed_rest_days))
    if season_fixed_rest_days:
        lines.append("season.recovery_protection.fixed_rest_days: " + ", ".join(season_fixed_rest_days))
    if season_notes:
        lines.append("season.recovery_protection.notes:")
        lines.extend(f"- {note}" for note in season_notes)
    minimum_recovery = execution_non_negotiables.get("minimum_recovery_opportunities")
    if isinstance(minimum_recovery, str) and minimum_recovery.strip():
        lines.append(f"phase.minimum_recovery_opportunities: {minimum_recovery}")
    no_catch_up = execution_non_negotiables.get("no_catch_up_rule")
    if isinstance(no_catch_up, str) and no_catch_up.strip():
        lines.append(f"phase.no_catch_up_rule: {no_catch_up}")
    if structure_fixed_days:
        lines.append("structure.fixed_non_training_days: " + ", ".join(structure_fixed_days))
    if spacing_rules:
        lines.append("structure.mandatory_recovery_spacing_rules:")
        lines.extend(f"- {rule}" for rule in spacing_rules)
    if forbidden_sequences:
        lines.append("structure.forbidden_sequences:")
        lines.extend(f"- {rule}" for rule in forbidden_sequences)
    return "\n".join(lines) + ("\n" if lines else "")


def build_resolved_load_governance_context_block(
    *,
    target_week: IsoWeek,
    season_plan_payload: dict[str, object] | None = None,
    phase_guardrails_payload: dict[str, object] | None = None,
    phase_structure_payload: dict[str, object] | None = None,
) -> str:
    """Build a compact active load-governance summary for the target week."""
    season_data = _as_map((season_plan_payload or {}).get("data"))
    season_phases = _as_list(season_data.get("phases"))
    season_band = None
    target_key = f"{target_week.year:04d}-{target_week.week:02d}"
    for phase in season_phases:
        phase_map = _as_map(phase)
        if phase_map.get("iso_week_range") and isinstance(phase_map.get("weekly_load_corridor"), dict):
            weekly_kj = _as_map(phase_map.get("weekly_load_corridor")).get("weekly_kj")
            if isinstance(weekly_kj, dict) and target_key in str(phase_map.get("iso_week_range")):
                season_band = weekly_kj
                break

    guardrails_data = _as_map((phase_guardrails_payload or {}).get("data"))
    load_guardrails = _as_map(guardrails_data.get("load_guardrails"))
    active_band_entry = _find_week_band(load_guardrails.get("weekly_kj_bands"), target_week)
    active_band = _as_map(active_band_entry.get("band")) if isinstance(active_band_entry, dict) else {}
    semantics = _as_map(guardrails_data.get("allowed_forbidden_semantics"))
    structure_data = _as_map((phase_structure_payload or {}).get("data"))
    execution_principles = _as_map(structure_data.get("execution_principles"))
    load_intensity = _as_map(execution_principles.get("load_intensity_handling"))

    lines: list[str] = []
    if season_band or active_band or semantics or load_intensity:
        lines.extend([
            "**Resolved Load Governance Context**",
            "Use these active governance facts directly; do not reconstruct corridor, quality-density, or allowed-domain semantics from raw artefact prose when they are provided here.",
        ])
    if isinstance(season_band, dict) and season_band:
        lines.append(
            f"season_phase.weekly_load_corridor.weekly_kj: min {season_band.get('min')}, max {season_band.get('max')}, notes {season_band.get('notes')}"
        )
    if active_band:
        lines.append(
            f"phase_guardrails.active_weekly_kj_band ({target_key}): min {active_band.get('min')}, max {active_band.get('max')}, notes {active_band.get('notes')}"
        )
    allowed_domains = [str(x) for x in _as_list(semantics.get("allowed_intensity_domains")) if str(x).strip()]
    allowed_modalities = [str(x) for x in _as_list(semantics.get("allowed_load_modalities")) if str(x).strip()]
    quality_density = _as_map(semantics.get("quality_density"))
    if allowed_domains:
        lines.append("phase_guardrails.allowed_intensity_domains: " + ", ".join(allowed_domains))
    if allowed_modalities:
        lines.append("phase_guardrails.allowed_load_modalities: " + ", ".join(allowed_modalities))
    if quality_density:
        lines.append(
            f"phase_guardrails.quality_density: max_quality_days_per_week {quality_density.get('max_quality_days_per_week')}, quality_intent {quality_density.get('quality_intent')}"
        )
    forbidden_patterns = [str(x) for x in _as_list(quality_density.get("forbidden_patterns")) if str(x).strip()]
    if forbidden_patterns:
        lines.append("phase_guardrails.quality_density.forbidden_patterns:")
        lines.extend(f"- {item}" for item in forbidden_patterns)
    if load_intensity:
        lines.append(
            f"phase_structure.load_intensity_handling: max_quality_days_per_week {load_intensity.get('max_quality_days_per_week')}, quality_intent {load_intensity.get('quality_intent')}"
        )
    return "\n".join(lines) + ("\n" if lines else "")


def build_resolved_event_priority_context_block(
    *,
    target_week: IsoWeek,
    season_plan_payload: dict[str, object] | None = None,
    phase_guardrails_payload: dict[str, object] | None = None,
    planning_events_payload: dict[str, object] | None = None,
) -> str:
    """Build a compact event-priority summary for the target week."""
    season_data = _as_map((season_plan_payload or {}).get("data"))
    global_constraints = _as_map(season_data.get("global_constraints"))
    planned_windows = [str(x) for x in _as_list(global_constraints.get("planned_event_windows")) if str(x).strip()]
    guardrails_data = _as_map((phase_guardrails_payload or {}).get("data"))
    guardrail_events = _as_list(_as_map(guardrails_data.get("events_constraints")).get("events"))
    planning_events_data = _as_map((planning_events_payload or {}).get("data"))
    planning_events = _as_list(planning_events_data.get("events"))
    target_key = f"{target_week.year:04d}-{target_week.week:02d}"

    target_planning_lines: list[str] = []
    upcoming_a = None
    for event in planning_events:
        event_map = _as_map(event)
        raw_date = event_map.get("date")
        event_type = event_map.get("type")
        if not isinstance(raw_date, str) or not isinstance(event_type, str):
            continue
        try:
            event_week = date_to_iso_week(date.fromisoformat(raw_date))
        except ValueError:
            continue
        event_key = f"{event_week.year:04d}-{event_week.week:02d}"
        if event_key == target_key:
            target_planning_lines.append(f"- {raw_date} {event_type} {event_map.get('event_name') or ''}".rstrip())
        if event_type == 'A' and week_index(event_week) >= week_index(target_week):
            if upcoming_a is None or week_index(event_week) < week_index(upcoming_a[0]):
                upcoming_a = (event_week, event_map)

    guardrail_lines = []
    for event in guardrail_events:
        event_map = _as_map(event)
        raw_date = event_map.get('date')
        event_type = event_map.get('type')
        constraint = event_map.get('constraint')
        if isinstance(raw_date, str) and isinstance(event_type, str):
            guardrail_lines.append(f"- {raw_date} {event_type}: {constraint}")

    lines: list[str] = []
    if planned_windows or target_planning_lines or upcoming_a or guardrail_lines:
        lines.extend([
            "**Resolved Event Priority Context**",
            "Use these event-priority facts directly; do not reconstruct protected event semantics or target-week event roles from scattered raw event text when they are provided here.",
        ])
    if planned_windows:
        lines.append("season.planned_event_windows:")
        lines.extend(f"- {item}" for item in planned_windows)
    if target_planning_lines:
        lines.append(f"target_week_priority_events ({target_key}):")
        lines.extend(target_planning_lines)
    else:
        lines.append(f"target_week_priority_events ({target_key}): none") if lines else None
    if upcoming_a is not None:
        week_obj, event_map = upcoming_a
        lines.append(
            f"next_protected_a_event: {event_map.get('date')} ({week_obj.year:04d}-{week_obj.week:02d}) {event_map.get('event_name') or ''}".rstrip()
        )
    if guardrail_lines:
        lines.append("phase_guardrails.events_constraints:")
        lines.extend(guardrail_lines)
    return "\n".join(lines) + ("\n" if lines else "")


def build_resolved_feed_forward_applicability_context_block(
    *,
    label: str,
    feed_forward_payload: dict[str, object] | None,
    target_week: IsoWeek,
) -> str:
    """Build a compact applicability summary for an optional feed-forward artefact."""
    target_key = f"{target_week.year:04d}-{target_week.week:02d}"
    if not isinstance(feed_forward_payload, dict):
        return (
            "**Resolved Feed-Forward Applicability Context**\n"
            "Use this applicability result directly; do not spend tool calls deciding whether an optional feed-forward artefact exists when that has already been resolved here.\n"
            f"{label}.status: none_for_target_week {target_key}\n"
        )
    meta = _as_map(feed_forward_payload.get("meta"))
    data = _as_map(feed_forward_payload.get("data"))
    body_metadata = _as_map(data.get("body_metadata"))
    applies = [str(x) for x in _as_list(body_metadata.get("applies_to_weeks")) if str(x).strip()]
    valid_until = body_metadata.get("valid_until")
    change_type = body_metadata.get("change_type")
    lines = [
        "**Resolved Feed-Forward Applicability Context**",
        "Use this applicability result directly; do not spend tool calls deciding whether an optional feed-forward artefact exists when that has already been resolved here.",
        f"{label}.status: applicable_for_target_week {target_key}",
    ]
    version_key = meta.get("version_key")
    if isinstance(version_key, str) and version_key:
        lines.append(f"{label}.version_key: {version_key}")
    if applies:
        lines.append(f"{label}.applies_to_weeks: {', '.join(applies)}")
    if isinstance(valid_until, str) and valid_until:
        lines.append(f"{label}.valid_until: {valid_until}")
    if isinstance(change_type, str) and change_type:
        lines.append(f"{label}.change_type: {change_type}")
    semantic_overrides = _as_map(data.get("temporary_semantic_overrides"))
    quality_override = _as_map(semantic_overrides.get("quality_density_override"))
    if quality_override:
        lines.append(
            f"{label}.quality_density_override: max_quality_days_per_week {quality_override.get('max_quality_days_per_week')}"
        )
    non_negotiables = _as_map(data.get("temporary_non_negotiables"))
    recovery_changes = non_negotiables.get("recovery_protection_changes")
    if isinstance(recovery_changes, str) and recovery_changes.strip():
        lines.append(f"{label}.recovery_protection_changes: {recovery_changes}")
    return "\n".join(lines) + "\n"


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


def build_resolved_zone_model_context_block(store: LocalArtifactStore, athlete_id: str) -> str:
    """Build a deterministic zone-model summary from the latest zone model artefact."""
    try:
        zone_model = store.load_latest(athlete_id, ArtifactType.ZONE_MODEL)
    except Exception:
        return ""
    data = zone_model.get("data") if isinstance(zone_model, dict) else None
    zone_data = data if isinstance(data, dict) else {}
    metadata = zone_data.get("model_metadata") or {}
    zones = zone_data.get("zones") or []
    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(zones, list):
        zones = []

    lines: list[str] = []
    ftp_watts = metadata.get("ftp_watts")
    if isinstance(ftp_watts, (int, float)):
        lines.extend(
            [
                "**Resolved Zone Model Context**",
                "Use these zone-model facts directly; do not search the raw zone table to rediscover FTP or load anchors when they are provided here.",
                f"ftp_watts: {ftp_watts}",
            ]
        )
    valid_from = metadata.get("valid_from")
    if isinstance(valid_from, str) and valid_from:
        if not lines:
            lines.extend(
                [
                    "**Resolved Zone Model Context**",
                    "Use these zone-model facts directly; do not search the raw zone table to rediscover FTP or load anchors when they are provided here.",
                ]
            )
        lines.append(f"valid_from: {valid_from}")
    filename = metadata.get("filename")
    if isinstance(filename, str) and filename:
        if not lines:
            lines.extend(
                [
                    "**Resolved Zone Model Context**",
                    "Use these zone-model facts directly; do not search the raw zone table to rediscover FTP or load anchors when they are provided here.",
                ]
            )
        lines.append(f"filename: {filename}")

    zone_lines: list[str] = []
    for zone in zones:
        if not isinstance(zone, dict):
            continue
        zone_id = zone.get("zone_id")
        if zone_id not in {"Z2", "Z3", "SS", "Z4"}:
            continue
        zone_lines.append(
            f"- {zone_id}: typical_if {zone.get('typical_if')}, training_intent {zone.get('training_intent')}"
        )
    if zone_lines:
        if not lines:
            lines.extend(
                [
                    "**Resolved Zone Model Context**",
                    "Use these zone-model facts directly; do not search the raw zone table to rediscover FTP or load anchors when they are provided here.",
                ]
            )
        lines.append("key_zone_defaults:")
        lines.extend(zone_lines)

    return "\n".join(lines) + ("\n" if lines else "")


def build_resolved_logistics_context_block(
    store: LocalArtifactStore,
    athlete_id: str,
    target_week: IsoWeek,
    *,
    phase_range: IsoWeekRange | None = None,
) -> str:
    """Build a deterministic logistics summary for the target week and optional phase range."""
    try:
        logistics = store.load_latest(athlete_id, ArtifactType.LOGISTICS)
    except Exception:
        return ""
    data = logistics.get("data") if isinstance(logistics, dict) else None
    logistics_data = data if isinstance(data, dict) else {}
    events = logistics_data.get("events") or []
    if not isinstance(events, list):
        return ""

    def _event_week(event: dict[str, object]) -> IsoWeek | None:
        raw_date = event.get("date")
        if not isinstance(raw_date, str):
            return None
        try:
            return date_to_iso_week(date.fromisoformat(raw_date))
        except ValueError:
            return None

    def _event_line(event: dict[str, object]) -> str | None:
        raw_date = event.get("date")
        event_week = _event_week(event)
        if not isinstance(raw_date, str) or event_week is None:
            return None
        return (
            f"- {raw_date} ({event_week.year:04d}-{event_week.week:02d}) "
            f"{event.get('event_type')}, status {event.get('status')}, "
            f"impact {event.get('impact')}, description {event.get('description')}"
        )

    target_key = f"{target_week.year:04d}-{target_week.week:02d}"
    target_lines: list[str] = []
    phase_lines: list[str] = []
    all_lines: list[str] = []
    for raw in events:
        if not isinstance(raw, dict):
            continue
        line = _event_line(raw)
        event_week = _event_week(raw)
        if not line or event_week is None:
            continue
        all_lines.append(line)
        event_key = f"{event_week.year:04d}-{event_week.week:02d}"
        if event_key == target_key:
            target_lines.append(line)
        if phase_range and week_index(phase_range.start) <= week_index(event_week) <= week_index(phase_range.end):
            phase_lines.append(line)

    if not all_lines:
        return ""

    lines = [
        "**Resolved Logistics Context**",
        "Use these logistics facts directly; do not recompute target-week or phase-range logistics membership when they are provided here.",
    ]
    if target_lines:
        lines.append(f"target_week_logistics ({target_key}):")
        lines.extend(target_lines)
    else:
        lines.append(f"target_week_logistics ({target_key}): none")
    if phase_range:
        if phase_lines:
            lines.append(f"phase_range_logistics ({phase_range.key}):")
            lines.extend(phase_lines)
        else:
            lines.append(f"phase_range_logistics ({phase_range.key}): none")
    lines.append("all_logistics_events:")
    lines.extend(all_lines)
    return "\n".join(lines) + "\n"
