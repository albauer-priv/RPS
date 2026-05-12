"""Reusable advisory/report/feed-forward actions for UI and coach surfaces."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rps.agents.knowledge_injection import build_injection_block
from rps.agents.multi_output_runner import AgentRuntime, run_agent_multi_output
from rps.agents.registry import AGENTS
from rps.agents.tasks import AgentTask
from rps.orchestrator.context_snapshots import (
    build_athlete_state_snapshot_prompt_block,
    build_planning_context_snapshot_prompt_block,
    save_advisory_memory,
    save_athlete_state_snapshot,
    save_planning_context_snapshot,
)
from rps.orchestrator.plan_week import _mode_for_task, create_performance_report
from rps.ui.feed_forward_context import (
    build_resolved_des_evaluation_context,
    build_resolved_season_phase_feed_forward_context,
)
from rps.workspace.iso_helpers import IsoWeek
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.season_plan_service import resolve_season_plan_phase_info
from rps.workspace.types import ArtifactType

logger = logging.getLogger(__name__)

JsonMap = dict[str, Any]
ActionResult = dict[str, Any]


def _as_map(value: object) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _load_selected_week_artifact(
    store: LocalArtifactStore,
    athlete_id: str,
    artifact_type: ArtifactType,
    week_key: str,
) -> JsonMap | None:
    version_key = store.resolve_week_version_key(athlete_id, artifact_type, week_key)
    if not version_key:
        return None
    try:
        payload = store.load_version(athlete_id, artifact_type, version_key)
    except FileNotFoundError:
        return None
    return _as_map(payload)


def _load_latest_payload(
    store: LocalArtifactStore,
    athlete_id: str,
    artifact_type: ArtifactType,
) -> JsonMap | None:
    try:
        payload = store.load_latest(athlete_id, artifact_type)
    except Exception:
        return None
    return _as_map(payload)


@dataclass(frozen=True)
class FeedForwardChainResult:
    """Structured result for report + feed-forward execution."""

    ok: bool
    report_ok: bool
    season_phase_ok: bool
    phase_ok: bool
    report_version_key: str | None
    season_phase_version_key: str | None
    phase_version_key: str | None
    error: str | None = None


def run_feed_forward_chain(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    workspace_root: Path,
    athlete_id: str,
    target_week: IsoWeek,
    run_id_prefix: str,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    max_num_results: int = 20,
) -> FeedForwardChainResult:
    """Run DES report and both feed-forward artefacts for the selected week."""

    store = LocalArtifactStore(root=workspace_root)
    selected_week_key = f"{target_week.year:04d}-{target_week.week:02d}"
    report_result = create_performance_report(
        runtime_for,
        athlete_id=athlete_id,
        report_week=target_week,
        run_id_prefix=f"{run_id_prefix}_report",
        force_file_search=True,
        max_num_results=max_num_results,
        model_resolver=model_resolver,
        temperature_resolver=temperature_resolver,
    )
    if not (isinstance(report_result, dict) and report_result.get("ok")):
        message = report_result.get("message") if isinstance(report_result, dict) else "DES analysis report failed."
        return FeedForwardChainResult(
            ok=False,
            report_ok=False,
            season_phase_ok=False,
            phase_ok=False,
            report_version_key=None,
            season_phase_version_key=None,
            phase_version_key=None,
            error=str(message),
        )

    season_plan_payload = _load_selected_week_artifact(store, athlete_id, ArtifactType.SEASON_PLAN, selected_week_key)
    if not season_plan_payload and store.latest_exists(athlete_id, ArtifactType.SEASON_PLAN):
        season_plan_payload = _as_map(store.load_latest(athlete_id, ArtifactType.SEASON_PLAN))
    phase_info = resolve_season_plan_phase_info(season_plan_payload or {}, target_week)
    if not season_plan_payload or phase_info is None:
        return FeedForwardChainResult(
            ok=False,
            report_ok=True,
            season_phase_ok=False,
            phase_ok=False,
            report_version_key=store.resolve_week_version_key(athlete_id, ArtifactType.DES_ANALYSIS_REPORT, selected_week_key),
            season_phase_version_key=None,
            phase_version_key=None,
            error="Season plan or covering phase context missing for feed forward.",
        )

    athlete_profile_payload = _load_latest_payload(store, athlete_id, ArtifactType.ATHLETE_PROFILE)
    kpi_profile_payload = _load_latest_payload(store, athlete_id, ArtifactType.KPI_PROFILE)
    availability_payload = _load_latest_payload(store, athlete_id, ArtifactType.AVAILABILITY)
    planning_events_payload = _load_latest_payload(store, athlete_id, ArtifactType.PLANNING_EVENTS)
    logistics_payload = _load_latest_payload(store, athlete_id, ArtifactType.LOGISTICS)
    selection_payload = _load_latest_payload(store, athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
    zone_model_payload = _load_latest_payload(store, athlete_id, ArtifactType.ZONE_MODEL)
    wellness_payload = _load_latest_payload(store, athlete_id, ArtifactType.WELLNESS)

    selected_report_payload = _load_selected_week_artifact(store, athlete_id, ArtifactType.DES_ANALYSIS_REPORT, selected_week_key)
    report_version = store.resolve_week_version_key(athlete_id, ArtifactType.DES_ANALYSIS_REPORT, selected_week_key)
    report_ref = f"des_analysis_report_{report_version}.json" if report_version else ""
    season_plan_ref = ""
    try:
        season_plan_ref = f"season_plan_{store.get_latest_version_key(athlete_id, ArtifactType.SEASON_PLAN)}.json"
    except Exception:
        season_plan_ref = ""

    athlete_state_snapshot = save_athlete_state_snapshot(
        store,
        athlete_id,
        target_week=target_week,
        run_id=f"{run_id_prefix}_report",
        athlete_profile_payload=athlete_profile_payload or {},
        kpi_profile_payload=kpi_profile_payload or {},
        selection_payload=selection_payload or {},
        availability_payload=availability_payload or {},
        planning_events_payload=planning_events_payload or {},
        logistics_payload=logistics_payload or {},
        zone_model_payload=zone_model_payload or {},
        wellness_payload=wellness_payload or {},
    )
    athlete_state_snapshot_block = build_athlete_state_snapshot_prompt_block(athlete_state_snapshot)
    planning_context_snapshot = save_planning_context_snapshot(
        store,
        athlete_id,
        target_week=target_week,
        phase_info=phase_info,
        season_plan_payload=_as_map(season_plan_payload),
        phase_range=phase_info.phase_range,
        run_id=f"{run_id_prefix}_report",
        availability_payload=availability_payload or {},
        planning_events_payload=planning_events_payload or {},
    )
    planning_context_snapshot_block = build_planning_context_snapshot_prompt_block(planning_context_snapshot)
    save_advisory_memory(
        store,
        athlete_id,
        target_week=target_week,
        run_id=f"{run_id_prefix}_report",
        season_plan_payload=_as_map(season_plan_payload),
        des_analysis_payload=selected_report_payload or {},
    )
    des_context_block = build_resolved_des_evaluation_context(
        selected_week=target_week,
        report_payload=selected_report_payload,
        report_ref=report_ref,
        season_plan_ref=season_plan_ref,
        affected_phase_id=phase_info.phase_id,
        phase_range_key=phase_info.phase_range.key,
    )

    runtime = runtime_for("season_planner")
    spec = AGENTS["season_planner"]
    injected_block = build_injection_block("season_planner", mode=_mode_for_task(AgentTask.CREATE_SEASON_PHASE_FEED_FORWARD))
    season_ff_run_id = f"{run_id_prefix}_season_phase"
    season_ff_result = run_agent_multi_output(
        runtime,
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=athlete_id,
        tasks=[AgentTask.CREATE_SEASON_PHASE_FEED_FORWARD],
        user_input=(
            f"Target ISO week: {target_week.year}-{target_week.week:02d}. "
            f'Use workspace_get_version({{"artifact_type":"DES_ANALYSIS_REPORT","version_key":"{selected_week_key}"}}) '
            "for the selected week if further report detail is needed. "
            "Use the selected-week DES analysis report to produce SEASON_PHASE_FEED_FORWARD. "
            f"{athlete_state_snapshot_block}\n"
            f"{planning_context_snapshot_block}\n"
            f"{des_context_block}\n\n"
            f"{injected_block}"
        ),
        run_id=season_ff_run_id,
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        force_file_search=True,
        max_num_results=max_num_results,
    )
    if not (isinstance(season_ff_result, dict) and season_ff_result.get("ok")):
        return FeedForwardChainResult(
            ok=False,
            report_ok=True,
            season_phase_ok=False,
            phase_ok=False,
            report_version_key=report_version,
            season_phase_version_key=None,
            phase_version_key=None,
            error="Season → Phase feed forward failed.",
        )

    selected_season_phase_ff_payload = _load_selected_week_artifact(
        store,
        athlete_id,
        ArtifactType.SEASON_PHASE_FEED_FORWARD,
        selected_week_key,
    )
    season_ff_version = store.resolve_week_version_key(
        athlete_id,
        ArtifactType.SEASON_PHASE_FEED_FORWARD,
        selected_week_key,
    )
    season_phase_ref = f"season_phase_feed_forward_{season_ff_version}.json" if season_ff_version else ""
    planning_context_snapshot = save_planning_context_snapshot(
        store,
        athlete_id,
        target_week=target_week,
        phase_info=phase_info,
        season_plan_payload=_as_map(season_plan_payload),
        phase_range=phase_info.phase_range,
        run_id=season_ff_run_id,
        availability_payload=availability_payload or {},
        planning_events_payload=planning_events_payload or {},
        season_phase_feed_forward_payload=selected_season_phase_ff_payload or {},
    )
    planning_context_snapshot_block = build_planning_context_snapshot_prompt_block(planning_context_snapshot)
    save_advisory_memory(
        store,
        athlete_id,
        target_week=target_week,
        run_id=season_ff_run_id,
        season_plan_payload=_as_map(season_plan_payload),
        des_analysis_payload=selected_report_payload or {},
        season_phase_feed_forward_payload=selected_season_phase_ff_payload or {},
    )
    season_phase_context_block = build_resolved_season_phase_feed_forward_context(
        selected_week=target_week,
        feed_forward_payload=selected_season_phase_ff_payload,
        feed_forward_ref=season_phase_ref,
    )

    runtime = runtime_for("phase_architect")
    spec = AGENTS["phase_architect"]
    injected_block = build_injection_block("phase_architect", mode=_mode_for_task(AgentTask.CREATE_PHASE_FEED_FORWARD))
    phase_ff_run_id = f"{run_id_prefix}_phase"
    phase_ff_result = run_agent_multi_output(
        runtime,
        agent_name=spec.name,
        agent_vs_name=spec.vector_store_name,
        athlete_id=athlete_id,
        tasks=[AgentTask.CREATE_PHASE_FEED_FORWARD],
        user_input=(
            f"Target ISO week: {target_week.year}-{target_week.week:02d}. "
            f'Use workspace_get_version({{"artifact_type":"DES_ANALYSIS_REPORT","version_key":"{selected_week_key}"}}) '
            "and "
            f'workspace_get_version({{"artifact_type":"SEASON_PHASE_FEED_FORWARD","version_key":"{selected_week_key}"}}) '
            "for the selected week if further detail is needed. "
            "Use the selected-week DES analysis report and the selected-week "
            "SEASON_PHASE_FEED_FORWARD context to produce PHASE_FEED_FORWARD. "
            f"{athlete_state_snapshot_block}\n"
            f"{planning_context_snapshot_block}\n"
            f"{des_context_block}\n\n"
            f"{season_phase_context_block}\n\n"
            f"{injected_block}"
        ),
        run_id=phase_ff_run_id,
        model_override=model_resolver(spec.name) if model_resolver else None,
        temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
        force_file_search=True,
        max_num_results=max_num_results,
    )
    if not (isinstance(phase_ff_result, dict) and phase_ff_result.get("ok")):
        return FeedForwardChainResult(
            ok=False,
            report_ok=True,
            season_phase_ok=True,
            phase_ok=False,
            report_version_key=report_version,
            season_phase_version_key=season_ff_version,
            phase_version_key=None,
            error="Phase → Week feed forward failed.",
        )

    phase_ff_version = store.resolve_week_version_key(
        athlete_id,
        ArtifactType.PHASE_FEED_FORWARD,
        selected_week_key,
    )
    selected_phase_ff_payload = _load_selected_week_artifact(
        store,
        athlete_id,
        ArtifactType.PHASE_FEED_FORWARD,
        selected_week_key,
    )
    save_advisory_memory(
        store,
        athlete_id,
        target_week=target_week,
        run_id=phase_ff_run_id,
        season_plan_payload=_as_map(season_plan_payload),
        des_analysis_payload=selected_report_payload or {},
        season_phase_feed_forward_payload=selected_season_phase_ff_payload or {},
        phase_feed_forward_payload=selected_phase_ff_payload or {},
    )
    return FeedForwardChainResult(
        ok=True,
        report_ok=True,
        season_phase_ok=True,
        phase_ok=True,
        report_version_key=report_version,
        season_phase_version_key=season_ff_version,
        phase_version_key=phase_ff_version,
    )
