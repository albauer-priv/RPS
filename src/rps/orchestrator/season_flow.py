"""Season-level orchestration helpers for scenario + plan actions."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date

from rps.agents.registry import AGENTS
from rps.agents.runtime import AgentRuntime
from rps.agents.runtime import run_agent_multi_output as run_agent_multi_output_direct
from rps.agents.tasks import AgentTask
from rps.crewai_runtime.flows import run_season_flow
from rps.crewai_runtime.guardrails import guardrail_runtime_context
from rps.crewai_runtime.runtime_status import crewai_runtime_status
from rps.orchestrator.context_snapshots import (
    build_athlete_state_snapshot_prompt_block,
    save_advisory_memory,
    save_athlete_state_snapshot,
)
from rps.orchestrator.planning_evidence import (
    build_evidence_alignment_payload,
    load_evidence_payloads,
    render_evidence_alignment_block,
    render_historical_baseline_block,
    render_previous_week_activity_block,
    resolve_previous_week_activity_versions,
)
from rps.orchestrator.resolved_context import build_resolved_activity_context_block
from rps.planning.contracts import blocking_messages, validate_snapshot_freshness
from rps.planning.deterministic_context import (
    build_cadence_options_block,
    build_load_capacity_block,
    build_season_phase_load_block,
    build_season_phase_slot_block,
    build_season_scenario_horizon_block,
    render_context_blocks,
)
from rps.planning.load_bands import selected_kpi_rate_band_from_selection
from rps.planning.scenario_recommendation import (
    build_scenario_recommendation_context,
    filter_future_planning_events_payload,
    render_scenario_recommendation_block,
)
from rps.planning.season_selection_binding import resolve_bound_season_selection
from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

logger = logging.getLogger(__name__)
AMBITION_IF_RANGE_LENGTH = 2

JsonMap = dict[str, object]
OrchestratorResult = dict[str, object]


def run_agent_multi_output(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    agent_name: str,
    athlete_id: str,
    task: AgentTask,
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
    workspace_root=None,
) -> OrchestratorResult:
    """Compatibility dispatcher for season orchestration tests and wrappers."""

    if crewai_runtime_status().ok:
        return run_season_flow(
            runtime_for=runtime_for,
            agent_name=agent_name,
            athlete_id=athlete_id,
            task=task,
            user_input=user_input,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
            workspace_root=workspace_root,
        )

    return run_agent_multi_output_direct(
        runtime_for(agent_name),
        agent_name=agent_name,
        athlete_id=athlete_id,
        tasks=[task],
        user_input=user_input,
        run_id=run_id,
        model_override=model_override,
        temperature_override=temperature_override,
        workspace_root=workspace_root,
    )

def _payload_version(payload: JsonMap | None) -> str | None:
    meta = payload.get("meta") if isinstance(payload, dict) else None
    if not isinstance(meta, dict):
        return None
    version = meta.get("version_key")
    return version if isinstance(version, str) else None


def _expected_source_versions(entries: list[tuple[str, JsonMap | None]]) -> JsonMap:
    return {
        label: version
        for label, payload in entries
        if (version := _payload_version(payload)) is not None
    }


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _binding_failure_result(result: JsonMap) -> OrchestratorResult:
    """Return a consistent early-abort result for season selection binding failures."""

    reason_code = str(result.get("reason_code") or "selected_scenario_binding_failed")
    reason_message = str(result.get("reason_message") or "Selected scenario binding failed.")
    logger.warning(
        "selected_scenario_binding_failed reason_code=%s selection=%s scenarios=%s",
        reason_code,
        result.get("selection_version_key") or "missing",
        result.get("scenarios_version_key") or "missing",
    )
    return {
        "ok": False,
        "reason_code": reason_code,
        "error": reason_message,
        "selection_version_key": result.get("selection_version_key"),
        "scenarios_version_key": result.get("scenarios_version_key"),
    }


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
    """Return exact previous-week activity versions for season planning evidence."""
    resolution = resolve_previous_week_activity_versions(store, athlete_id, target_week)
    resolved: dict[ArtifactType, str] = {}
    if resolution.activities_actual_version:
        resolved[ArtifactType.ACTIVITIES_ACTUAL] = resolution.activities_actual_version
    if resolution.activities_trend_version:
        resolved[ArtifactType.ACTIVITIES_TREND] = resolution.activities_trend_version
    return resolved


def create_season_scenarios(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    override_text: str | None = None,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
) -> OrchestratorResult:
    """Create season scenarios for the target ISO week."""
    spec = AGENTS["season_scenario"]
    injected_block = ""
    override_line = f"Override: {override_text.strip()}. " if override_text else ""
    athlete_state_snapshot_block = ""
    planning_horizon_block = ""
    cadence_options_block = ""
    scenario_recommendation_block = ""
    season_evidence_block = ""
    season_evidence_alignment_block = ""
    recommendation_context: JsonMap | None = None
    try:
        store = LocalArtifactStore(root=runtime_for(spec.name).workspace_root)
        target_week = IsoWeek(year=year, week=week)
        athlete_profile_payload = store.load_latest_payload(athlete_id, ArtifactType.ATHLETE_PROFILE)
        kpi_profile_payload = store.load_latest_payload(athlete_id, ArtifactType.KPI_PROFILE)
        availability_payload = store.load_latest_payload(athlete_id, ArtifactType.AVAILABILITY)
        planning_events_payload = store.load_latest_payload(athlete_id, ArtifactType.PLANNING_EVENTS)
        logistics_payload = store.load_latest_payload(athlete_id, ArtifactType.LOGISTICS)
        selection_payload = store.load_latest_payload(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
        zone_model_payload = store.load_latest_payload(athlete_id, ArtifactType.ZONE_MODEL)
        wellness_payload = store.load_latest_payload(athlete_id, ArtifactType.WELLNESS)
        historical_baseline_payload = store.load_latest_payload(athlete_id, ArtifactType.HISTORICAL_BASELINE)
        evidence_resolution = resolve_previous_week_activity_versions(store, athlete_id, target_week)
        if not historical_baseline_payload:
            return {"ok": False, "error": "Season planning evidence missing: HISTORICAL_BASELINE not found."}
        if not evidence_resolution.activities_actual_version or not evidence_resolution.activities_trend_version:
            return {
                "ok": False,
                "error": (
                    "Season planning evidence missing for previous week "
                    f"{evidence_resolution.evidence_week.year:04d}-{evidence_resolution.evidence_week.week:02d}: "
                    "ACTIVITIES_ACTUAL and ACTIVITIES_TREND are required."
                ),
            }
        evidence_payloads = load_evidence_payloads(
            store,
            athlete_id,
            resolution=evidence_resolution,
            include_report=False,
        )
        activities_actual_payload = _as_map(evidence_payloads.get("activities_actual"))
        activities_trend_payload = _as_map(evidence_payloads.get("activities_trend"))
        athlete_state_snapshot = save_athlete_state_snapshot(
            store,
            athlete_id,
            target_week=target_week,
            run_id=run_id,
            athlete_profile_payload=athlete_profile_payload or {},
            kpi_profile_payload=kpi_profile_payload or {},
            selection_payload=selection_payload or {},
            availability_payload=availability_payload or {},
            planning_events_payload=planning_events_payload or {},
            logistics_payload=logistics_payload or {},
            zone_model_payload=zone_model_payload or {},
            wellness_payload=wellness_payload or {},
        )
        athlete_state_snapshot_block = build_athlete_state_snapshot_prompt_block(
            athlete_state_snapshot if isinstance(athlete_state_snapshot, dict) else {}
        )
        target_week_start = date.fromisocalendar(target_week.year, target_week.week, 1).isoformat()
        future_planning_events_payload = filter_future_planning_events_payload(
            planning_events_payload or {},
            as_of_date=target_week_start,
        )
        horizon_context = build_season_scenario_horizon_block(
            planning_events_payload=future_planning_events_payload,
            target_week=target_week,
        )
        cadence_context = build_cadence_options_block(horizon_context=horizon_context.payload)
        planning_horizon_block = render_context_blocks([horizon_context])
        cadence_options_block = render_context_blocks([cadence_context])
        season_evidence_block = (
            render_historical_baseline_block(historical_baseline_payload)
            + render_previous_week_activity_block(
                store,
                athlete_id,
                target_week=target_week,
                resolution=evidence_resolution,
            )
        )
        season_evidence_alignment_payload = build_evidence_alignment_payload(
            scope="season",
            target_week=target_week,
            evidence_week=evidence_resolution.evidence_week,
            historical_baseline_payload=historical_baseline_payload,
            activities_actual_payload=activities_actual_payload,
            activities_trend_payload=activities_trend_payload,
        )
        season_evidence_alignment_block = render_evidence_alignment_block(season_evidence_alignment_payload)
        pseudo_scenarios_payload = {
            "meta": {
                "temporal_scope": _as_map(horizon_context.payload.get("temporal_scope"))
                or {"from": target_week_start, "to": target_week_start}
            },
            "data": {
                "scenarios": [
                    {
                        "scenario_id": str(option.get("deload_cadence")),
                        "name": f"Cadence option {option.get('deload_cadence')}",
                        "scenario_guidance": {"deload_cadence": option.get("deload_cadence")},
                    }
                    for option in _as_list(cadence_context.payload.get("options"))
                    if isinstance(option, dict)
                ]
            }
        }
        recommendation_context = build_scenario_recommendation_context(
            season_scenarios_payload=pseudo_scenarios_payload,
            athlete_profile_payload=athlete_profile_payload,
            kpi_profile_payload=kpi_profile_payload,
            availability_payload=availability_payload,
            planning_events_payload=future_planning_events_payload,
            historical_baseline_payload=historical_baseline_payload,
            activities_trend_payload=activities_trend_payload,
            wellness_payload=wellness_payload,
        )
        scenario_recommendation_block = render_scenario_recommendation_block(recommendation_context)
    except Exception as exc:
        logger.exception("Season evidence alignment preparation failed.")
        return {"ok": False, "error": f"Season evidence alignment preparation failed: {exc}"}
    user_input = (
        "Mode A. Generate the pre-decision scenarios. "
        f"Target ISO week: {year}-{week:02d}. "
        "Use workspace_get_input for Athlete Profile, Planning Events, and Logistics. "
        "Use workspace_get_latest only for shared latest inputs Availability, KPI Profile, and Wellness. "
        "Focus on qualitative scenario differences; runtime will canonicalize horizon and phase math from planning events. "
        f"{athlete_state_snapshot_block}"
        f"{planning_horizon_block}"
        f"{cadence_options_block}"
        f"{season_evidence_block}"
        f"{season_evidence_alignment_block}"
        f"{scenario_recommendation_block}"
        f"{override_line}"
        f"{injected_block}"
        "Return only the final schema-compliant SEASON_SCENARIOS artifact envelope."
    )
    logger.info("Creating season scenarios athlete=%s iso_week=%04d-W%02d", athlete_id, year, week)
    with guardrail_runtime_context(
        season_scenario_recommendation_context=recommendation_context if isinstance(recommendation_context, dict) else {},
        season_scenario_event_context={
            "target_week_start_date": target_week_start if "target_week_start" in locals() else "",
            "future_events": _as_list(
                _as_map(_as_map(future_planning_events_payload if "future_planning_events_payload" in locals() else {}).get("data")).get(
                    "events"
                )
            ),
            "all_events": _as_list(
                _as_map(_as_map(planning_events_payload if "planning_events_payload" in locals() else {}).get("data")).get("events")
            ),
        },
    ):
        return run_agent_multi_output(
            runtime_for,
            agent_name=spec.name,
            athlete_id=athlete_id,
            task=AgentTask.CREATE_SEASON_SCENARIOS,
            user_input=user_input,
            run_id=run_id,
            model_override=model_resolver(spec.name) if model_resolver else None,
            temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
            workspace_root=runtime_for(spec.name).workspace_root,
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
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
) -> OrchestratorResult:
    """Select a season scenario for the target ISO week."""
    spec = AGENTS["season_scenario"]
    injected_block = ""
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
        "Return only the final schema-compliant SEASON_SCENARIO_SELECTION artifact envelope. "
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
        runtime_for,
        agent_name=spec.name,
        athlete_id=athlete_id,
        task=AgentTask.CREATE_SEASON_SCENARIO_SELECTION,
        user_input=user_input,
        run_id=run_id,
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        workspace_root=runtime_for(spec.name).workspace_root,
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
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
) -> OrchestratorResult:
    """Create the season plan for the selected scenario."""
    spec = AGENTS["season_planner"]
    injected_block = ""
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
    athlete_state_snapshot_block = ""
    resolved_activity_block = ""
    historical_baseline_block = ""
    season_evidence_alignment_block = ""
    load_capacity_block = ""
    selected_scenario_structure_block = ""
    phase_slot_block = ""
    season_phase_load_block = ""
    phase_slot_context_payload: JsonMap = {}
    season_phase_load_context_payload: JsonMap = {}
    historical_context_line = ""
    try:
        store = LocalArtifactStore(root=runtime_for(spec.name).workspace_root)
        target_week = IsoWeek(year=year, week=week)
        athlete_profile_payload = store.load_latest_payload(athlete_id, ArtifactType.ATHLETE_PROFILE)
        kpi_profile_payload = store.load_latest_payload(athlete_id, ArtifactType.KPI_PROFILE)
        availability_payload = store.load_latest_payload(athlete_id, ArtifactType.AVAILABILITY)
        planning_events_payload = store.load_latest_payload(athlete_id, ArtifactType.PLANNING_EVENTS)
        logistics_payload = store.load_latest_payload(athlete_id, ArtifactType.LOGISTICS)
        season_scenarios_payload = store.load_latest_payload(athlete_id, ArtifactType.SEASON_SCENARIOS)
        selection_payload = store.load_latest_payload(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
        zone_model_payload = store.load_latest_payload(athlete_id, ArtifactType.ZONE_MODEL)
        wellness_payload = store.load_latest_payload(athlete_id, ArtifactType.WELLNESS)
        historical_baseline_payload = store.load_latest_payload(athlete_id, ArtifactType.HISTORICAL_BASELINE)
        athlete_state_snapshot = save_athlete_state_snapshot(
            store,
            athlete_id,
            target_week=target_week,
            run_id=run_id,
            athlete_profile_payload=athlete_profile_payload or {},
            kpi_profile_payload=kpi_profile_payload or {},
            selection_payload=selection_payload or {},
            availability_payload=availability_payload or {},
            planning_events_payload=planning_events_payload or {},
            logistics_payload=logistics_payload or {},
            zone_model_payload=zone_model_payload or {},
            wellness_payload=wellness_payload or {},
        )
        athlete_state_snapshot_block = build_athlete_state_snapshot_prompt_block(
            athlete_state_snapshot if isinstance(athlete_state_snapshot, dict) else {}
        )
        snapshot_issues = validate_snapshot_freshness(
            snapshot_payload=athlete_state_snapshot if isinstance(athlete_state_snapshot, dict) else {},
            expected_source_versions=_expected_source_versions(
                [
                    ("athlete_profile", athlete_profile_payload),
                    ("kpi_profile", kpi_profile_payload),
                    ("season_scenarios", season_scenarios_payload),
                    ("season_scenario_selection", selection_payload),
                    ("availability", availability_payload),
                    ("planning_events", planning_events_payload),
                    ("logistics", logistics_payload),
                    ("zone_model", zone_model_payload),
                    ("wellness", wellness_payload),
                ]
            ),
            authoritative=True,
            snapshot_label="ATHLETE_STATE_SNAPSHOT",
        )
        snapshot_blockers = blocking_messages(snapshot_issues)
        if snapshot_blockers:
            return {"ok": False, "error": "Season snapshot freshness failed: " + "; ".join(snapshot_blockers[:5])}
        binding = resolve_bound_season_selection(
            season_scenarios_payload=season_scenarios_payload or {},
            selection_payload=selection_payload or {},
            selected_scenario_id=selected,
        )
        if not bool(binding.get("ok")):
            return _binding_failure_result(binding)
        evidence_resolution = resolve_previous_week_activity_versions(store, athlete_id, target_week)
        if not historical_baseline_payload:
            return {"ok": False, "error": "Season planning evidence missing: HISTORICAL_BASELINE not found."}
        if not evidence_resolution.activities_actual_version or not evidence_resolution.activities_trend_version:
            return {
                "ok": False,
                "error": (
                    "Season planning evidence missing for previous week "
                    f"{evidence_resolution.evidence_week.year:04d}-{evidence_resolution.evidence_week.week:02d}: "
                    "ACTIVITIES_ACTUAL and ACTIVITIES_TREND are required."
                ),
            }
        evidence_payloads = load_evidence_payloads(
            store,
            athlete_id,
            resolution=evidence_resolution,
            include_report=False,
        )
        activities_actual_payload = _as_map(evidence_payloads.get("activities_actual"))
        activities_trend_payload = _as_map(evidence_payloads.get("activities_trend"))
        actual_version = evidence_resolution.activities_actual_version
        trend_version = evidence_resolution.activities_trend_version
        resolved_activity_block = build_resolved_activity_context_block(
            store,
            athlete_id,
            target_week=target_week,
            activities_actual_version=actual_version,
            activities_trend_version=trend_version,
        )
        historical_baseline_block = render_historical_baseline_block(historical_baseline_payload)
        season_evidence_alignment_payload = build_evidence_alignment_payload(
            scope="season",
            target_week=target_week,
            evidence_week=evidence_resolution.evidence_week,
            historical_baseline_payload=historical_baseline_payload,
            activities_actual_payload=activities_actual_payload,
            activities_trend_payload=activities_trend_payload,
        )
        season_evidence_alignment_block = render_evidence_alignment_block(season_evidence_alignment_payload)
        historical_context_line = (
            f"If activity context is needed, use workspace_get_version for previous-week ACTIVITIES_ACTUAL and "
            f"ACTIVITIES_TREND at evidence week "
            f"{evidence_resolution.evidence_week.year:04d}-{evidence_resolution.evidence_week.week:02d}: "
            f"{actual_version} and {trend_version}; never use workspace_get_latest for week-sensitive "
            "activity artefacts. "
        )
        selected_structure_payload = _as_map(binding.get("selected_scenario_structure_context"))
        selected_scenario_contract_payload = _as_map(binding.get("selected_scenario_contract"))
        season_allowed_intensity_domains = [
            str(item)
            for item in _as_list(selected_structure_payload.get("allowed_intensity_domains"))
            if str(item).strip()
        ]
        load_capacity_block = render_context_blocks(
            [
                build_load_capacity_block(
                    target_week=target_week,
                    athlete_profile_payload=athlete_profile_payload or {},
                    availability_payload=availability_payload or {},
                    logistics_payload=logistics_payload or {},
                    zone_model_payload=zone_model_payload or {},
                    season_plan_payload={},
                    season_allowed_intensity_domains=season_allowed_intensity_domains,
                    wellness_payload=wellness_payload or {},
                    kpi_profile_payload=kpi_profile_payload or {},
                    kpi_rate_band=selected_kpi_rate_band_from_selection(selection_payload or {}),
                )
            ]
        )
        if "availability_load_capacity_kj:" not in load_capacity_block:
            return {
                "ok": False,
                "error": "Season deterministic load capacity context is missing availability_load_capacity_kj.",
            }
        phase_slot_context = build_season_phase_slot_block(
            selected_structure_context=selected_structure_payload,
            target_week=target_week,
        )
        phase_slot_context_payload = phase_slot_context.payload
        slot_issues = [
            str(item)
            for item in _as_list(phase_slot_context_payload.get("blocking_issues"))
            if str(item).strip()
        ]
        if not phase_slot_context_payload or slot_issues:
            return {
                "ok": False,
                "error": "Season deterministic phase slot context is invalid: " + "; ".join(slot_issues or ["missing"]),
            }
        season_phase_load_context = build_season_phase_load_block(
            phase_slot_context=phase_slot_context.payload,
            target_week=target_week,
            athlete_profile_payload=athlete_profile_payload or {},
            availability_payload=availability_payload or {},
            logistics_payload=logistics_payload or {},
            planning_events_payload=planning_events_payload or {},
            zone_model_payload=zone_model_payload or {},
            selected_structure_context=selected_structure_payload,
            selected_scenario_contract=selected_scenario_contract_payload,
            wellness_payload=wellness_payload or {},
            kpi_profile_payload=kpi_profile_payload or {},
            kpi_rate_band=selected_kpi_rate_band_from_selection(selection_payload or {}),
        )
        season_phase_load_context_payload = season_phase_load_context.payload
        load_issues = [
            str(item)
            for item in _as_list(season_phase_load_context_payload.get("blocking_issues"))
            if str(item).strip()
        ]
        if not season_phase_load_context_payload or load_issues:
            return {
                "ok": False,
                "error": "Season deterministic phase load context is invalid: " + "; ".join(load_issues or ["missing"]),
            }
        selected_scenario_structure_block = (
            str(binding.get("selected_scenario_structure_markdown") or "")
            + str(binding.get("selected_scenario_contract_markdown") or "")
        )
        phase_slot_block = render_context_blocks([phase_slot_context])
        season_phase_load_block = render_context_blocks([season_phase_load_context])
    except Exception as exc:
        logger.exception("Season deterministic context construction failed.")
        return {"ok": False, "error": f"Season deterministic context construction failed: {exc}"}
    user_input = (
        f"{scenario_line}Mode A. Create the SEASON_PLAN. "
        f"Target ISO week: {year}-{week:02d}. "
        "Use the latest season-level SEASON_SCENARIO_SELECTION and SEASON_SCENARIOS as context. "
        f"{historical_context_line}"
        f"{athlete_state_snapshot_block}"
        f"{user_data_block}"
        f"{historical_baseline_block}"
        f"{resolved_activity_block}"
        f"{season_evidence_alignment_block}"
        f"{load_capacity_block}"
        f"{selected_scenario_structure_block}"
        f"{phase_slot_block}"
        f"{season_phase_load_block}"
        f"{override_line}"
        f"{injected_block}"
        "Return only the final schema-compliant SEASON_PLAN artifact envelope."
    )
    logger.info(
        "Creating season plan athlete=%s iso_week=%04d-W%02d scenario=%s",
        athlete_id,
        year,
        week,
        selected or "latest",
    )
    with guardrail_runtime_context(
        phase_slot_context=phase_slot_context_payload,
        season_phase_load_context=season_phase_load_context_payload,
        selected_scenario_contract=selected_scenario_contract_payload,
        athlete_profile_payload=athlete_profile_payload or {},
        kpi_profile_payload=kpi_profile_payload or {},
        availability_payload=availability_payload or {},
        planning_events_payload=planning_events_payload or {},
        logistics_payload=logistics_payload or {},
        zone_model_payload=zone_model_payload or {},
    ):
        result = run_agent_multi_output(
            runtime_for,
            agent_name=spec.name,
            athlete_id=athlete_id,
            task=AgentTask.CREATE_SEASON_PLAN,
            user_input=user_input,
            run_id=run_id,
            model_override=model_resolver(spec.name) if model_resolver else None,
            temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
            workspace_root=runtime_for(spec.name).workspace_root,
        )
    try:
        if result.get("ok") and result.get("produced"):
            store = LocalArtifactStore(root=runtime_for(spec.name).workspace_root)
            season_plan_payload = store.load_latest_payload(athlete_id, ArtifactType.SEASON_PLAN)
            save_advisory_memory(
                store,
                athlete_id,
                target_week=IsoWeek(year=year, week=week),
                run_id=run_id,
                season_plan_payload=season_plan_payload or {},
            )
    except Exception:
        logger.debug("Advisory memory refresh after season plan failed.", exc_info=True)
    return result
