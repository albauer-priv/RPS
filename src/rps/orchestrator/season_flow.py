"""Season-level orchestration helpers for scenario + plan actions."""

from __future__ import annotations

import logging
from collections.abc import Callable

from rps.agents.knowledge_injection import build_injection_block
from rps.agents.multi_output_runner import AgentRuntime, run_agent_multi_output
from rps.agents.registry import AGENTS
from rps.agents.tasks import AgentTask
from rps.orchestrator.resolved_context import (
    build_resolved_activity_context_block,
    build_resolved_athlete_context_block,
    build_resolved_availability_context_block,
    build_resolved_kpi_context_block,
    build_resolved_logistics_context_block,
    build_resolved_planning_events_context_block,
    build_resolved_zone_model_context_block,
)
from rps.workspace.iso_helpers import IsoWeek, parse_iso_week, week_index
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

logger = logging.getLogger(__name__)
AMBITION_IF_RANGE_LENGTH = 2

JsonMap = dict[str, object]
OrchestratorResult = dict[str, object]


def _extract_profile_user_data(profile_payload: JsonMap | None) -> JsonMap:
    """Extract optional user-provided planning fields from Athlete Profile."""
    if not isinstance(profile_payload, dict):
        return {"endurance_anchor_w": None, "ambition_if_range": None}
    data = profile_payload.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    profile = data.get("profile") or {}
    if not isinstance(profile, dict):
        profile = {}
    anchor = profile.get("endurance_anchor_w")
    ambition = profile.get("ambition_if_range")
    return {"endurance_anchor_w": anchor, "ambition_if_range": ambition}


def _format_user_data_block(user_data: dict[str, object]) -> str:
    """Format user-provided data for prompt injection."""
    anchor = user_data.get("endurance_anchor_w")
    ambition = user_data.get("ambition_if_range")
    lines = ["**User Provided Data**"]
    if isinstance(anchor, (int, float)):
        lines.append(f"endurance_anchor_w: {anchor} W")
    else:
        lines.append("endurance_anchor_w: n/a")
    if isinstance(ambition, tuple) and len(ambition) == AMBITION_IF_RANGE_LENGTH:
        lines.append(f"ambition_if_range: [{ambition[0]}, {ambition[1]}]")
    else:
        lines.append("ambition_if_range: n/a")
    lines.append("kpi_profile: xxx")
    return "\n".join(lines) + "\n"


def _resolve_latest_historical_week_versions(
    store: LocalArtifactStore,
    athlete_id: str,
    target_week: IsoWeek,
) -> dict[ArtifactType, str]:
    """Return the latest available week-scoped activity versions before the target week."""
    resolved: dict[ArtifactType, str] = {}
    for artifact_type in (ArtifactType.ACTIVITIES_ACTUAL, ArtifactType.ACTIVITIES_TREND):
        latest_version: str | None = None
        latest_week_index: int | None = None
        for version_key in store.list_versions(athlete_id, artifact_type):
            version_week = parse_iso_week(version_key)
            if version_week is None:
                continue
            version_index = week_index(version_week)
            if version_index >= week_index(target_week):
                continue
            if latest_week_index is None or version_index > latest_week_index:
                latest_version = version_key
                latest_week_index = version_index
        if latest_version:
            resolved[artifact_type] = latest_version
    return resolved


def create_season_scenarios(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    override_text: str | None = None,
    force_file_search: bool = True,
    max_num_results: int = 20,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
) -> OrchestratorResult:
    """Create season scenarios for the target ISO week."""
    spec = AGENTS["season_scenario"]
    injected_block = build_injection_block("season_scenario", mode="scenario")
    override_line = f"Override: {override_text.strip()}. " if override_text else ""
    athlete_block = ""
    kpi_block = ""
    availability_block = ""
    logistics_block = ""
    planning_events_block = ""
    try:
        store = LocalArtifactStore(root=runtime_for(spec.name).workspace_root)
        athlete_block = build_resolved_athlete_context_block(store, athlete_id)
        kpi_block = build_resolved_kpi_context_block(store, athlete_id)
        availability_block = build_resolved_availability_context_block(store, athlete_id)
        logistics_block = build_resolved_logistics_context_block(
            store,
            athlete_id,
            IsoWeek(year=year, week=week),
        )
        planning_events_block = build_resolved_planning_events_context_block(
            store,
            athlete_id,
            IsoWeek(year=year, week=week),
        )
    except Exception:
        athlete_block = ""
        kpi_block = ""
        availability_block = ""
        logistics_block = ""
        planning_events_block = ""
    user_input = (
        "Mode A. Generate the pre-decision scenarios. "
        f"Target ISO week: {year}-{week:02d}. "
        "Use workspace_get_input for Athlete Profile, Planning Events, and Logistics. "
        "Use workspace_get_latest only for shared latest inputs Availability, KPI Profile, and Wellness. "
        "Focus on qualitative scenario differences; runtime will canonicalize horizon and phase math from planning events. "
        f"{athlete_block}"
        f"{kpi_block}"
        f"{availability_block}"
        f"{logistics_block}"
        f"{planning_events_block}"
        f"{override_line}"
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_SCENARIOS."
    )
    logger.info("Creating season scenarios athlete=%s iso_week=%04d-W%02d", athlete_id, year, week)
    return run_agent_multi_output(
        runtime_for(spec.name),
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=athlete_id,
        tasks=[AgentTask.CREATE_SEASON_SCENARIOS],
        user_input=user_input,
        run_id=run_id,
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
    )


def select_season_scenario(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    selected: str,
    rationale: str | None,
    kpi_selection: JsonMap | None = None,
    force_file_search: bool = True,
    max_num_results: int = 20,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
) -> OrchestratorResult:
    """Select a season scenario for the target ISO week."""
    spec = AGENTS["season_scenario"]
    injected_block = build_injection_block("season_scenario", mode="scenario")
    rationale_line = f"Rationale: {rationale.strip()}. " if rationale else ""
    kpi_line = ""
    if isinstance(kpi_selection, dict):
        segment = kpi_selection.get("segment")
        w_per_kg = kpi_selection.get("w_per_kg") or {}
        kj_per_kg = kpi_selection.get("kj_per_kg_per_hour") or {}
        if (
            segment
            and isinstance(w_per_kg, dict)
            and isinstance(kj_per_kg, dict)
            and w_per_kg
            and kj_per_kg
        ):
            w_bounds: JsonMap = w_per_kg
            kj_bounds: JsonMap = kj_per_kg
            kpi_line = (
                "KPI moving_time_rate_guidance selection: "
                f"{segment} "
                f"(w_per_kg {w_bounds.get('min')} - {w_bounds.get('max')}, "
                f"kj_per_kg_per_hour {kj_bounds.get('min')} - {kj_bounds.get('max')}). "
            )
    user_input = (
        f"Select Scenario {selected.upper()} for ISO week {year}-{week:02d}. "
        "Use the latest season-level SEASON_SCENARIOS as context. "
        f"{rationale_line}"
        f"{kpi_line}"
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_SCENARIO_SELECTION. "
        "Always include kpi_moving_time_rate_guidance_selection (set to null if not provided)."
    )
    logger.info(
        "Selecting season scenario athlete=%s iso_week=%04d-W%02d scenario=%s",
        athlete_id,
        year,
        week,
        selected,
    )
    return run_agent_multi_output(
        runtime_for(spec.name),
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=athlete_id,
        tasks=[AgentTask.CREATE_SEASON_SCENARIO_SELECTION],
        user_input=user_input,
        run_id=run_id,
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
    )


def create_season_plan(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    selected: str | None,
    override_text: str | None = None,
    force_file_search: bool = True,
    max_num_results: int = 20,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
) -> OrchestratorResult:
    """Create the season plan for the selected scenario."""
    spec = AGENTS["season_planner"]
    injected_block = build_injection_block("season_planner", mode="season_plan")
    scenario_line = f"Scenario {selected.upper()}. " if selected else ""
    override_line = f"Override: {override_text.strip()}. " if override_text else ""
    user_data_block = ""
    try:
        store = LocalArtifactStore(root=runtime_for(spec.name).workspace_root)
        profile_payload = store.load_latest(athlete_id, ArtifactType.ATHLETE_PROFILE)
        user_data = _extract_profile_user_data(profile_payload if isinstance(profile_payload, dict) else None)
        user_data_block = _format_user_data_block(user_data)
    except Exception:
        user_data_block = _format_user_data_block({})
    athlete_block = ""
    kpi_block = ""
    availability_block = ""
    logistics_block = ""
    planning_events_block = ""
    zone_model_block = ""
    resolved_activity_block = ""
    historical_context_line = ""
    try:
        store = LocalArtifactStore(root=runtime_for(spec.name).workspace_root)
        target_week = IsoWeek(year=year, week=week)
        athlete_block = build_resolved_athlete_context_block(store, athlete_id)
        kpi_block = build_resolved_kpi_context_block(store, athlete_id)
        availability_block = build_resolved_availability_context_block(store, athlete_id)
        logistics_block = build_resolved_logistics_context_block(
            store,
            athlete_id,
            target_week,
        )
        planning_events_block = build_resolved_planning_events_context_block(
            store,
            athlete_id,
            target_week,
        )
        zone_model_block = build_resolved_zone_model_context_block(store, athlete_id)
        historical_activity_versions = _resolve_latest_historical_week_versions(
            store,
            athlete_id,
            target_week,
        )
        if (
            ArtifactType.ACTIVITIES_ACTUAL in historical_activity_versions
            and ArtifactType.ACTIVITIES_TREND in historical_activity_versions
        ):
            actual_version = historical_activity_versions[ArtifactType.ACTIVITIES_ACTUAL]
            trend_version = historical_activity_versions[ArtifactType.ACTIVITIES_TREND]
            resolved_activity_block = build_resolved_activity_context_block(
                store,
                athlete_id,
                target_week=target_week,
                activities_actual_version=actual_version,
                activities_trend_version=trend_version,
            )
            historical_context_line = (
                f"If activity context is needed, use workspace_get_version for ACTIVITIES_ACTUAL and "
                f"ACTIVITIES_TREND with the latest historical version_key before target week {year}-{week:02d}: "
                f"{actual_version} and {trend_version}; never use workspace_get_latest for week-sensitive "
                "activity artefacts. "
            )
    except Exception:
        athlete_block = ""
        kpi_block = ""
        availability_block = ""
        logistics_block = ""
        planning_events_block = ""
        zone_model_block = ""
        resolved_activity_block = ""
        historical_context_line = ""
    user_input = (
        f"{scenario_line}Mode A. Create the SEASON_PLAN. "
        f"Target ISO week: {year}-{week:02d}. "
        "Use the latest season-level SEASON_SCENARIO_SELECTION and SEASON_SCENARIOS as context. "
        f"{historical_context_line}"
        f"{athlete_block}"
        f"{user_data_block}"
        f"{kpi_block}"
        f"{availability_block}"
        f"{logistics_block}"
        f"{planning_events_block}"
        f"{zone_model_block}"
        f"{resolved_activity_block}"
        f"{override_line}"
        f"{injected_block}"
        "Follow the Mandatory Output Chapter for SEASON_PLAN."
    )
    logger.info(
        "Creating season plan athlete=%s iso_week=%04d-W%02d scenario=%s",
        athlete_id,
        year,
        week,
        selected or "latest",
    )
    return run_agent_multi_output(
        runtime_for(spec.name),
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=athlete_id,
        tasks=[AgentTask.CREATE_SEASON_PLAN],
        user_input=user_input,
        run_id=run_id,
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
    )
