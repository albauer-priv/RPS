"""Orchestrator flow for weekly planning runs."""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from rps.agents.registry import AGENTS
from rps.agents.runtime import AgentRuntime
from rps.agents.runtime import run_agent_multi_output as run_agent_multi_output_direct
from rps.agents.tasks import AgentTask
from rps.core.logging import log_and_print
from rps.crewai_runtime.flows import run_phase_flow, run_report_flow, run_week_flow
from rps.crewai_runtime.guardrails import guardrail_runtime_context
from rps.crewai_runtime.runtime_status import crewai_runtime_status
from rps.data_pipeline.intervals_data import run_pipeline as run_intervals_pipeline
from rps.orchestrator.context_snapshots import (
    build_athlete_state_snapshot_prompt_block,
    build_planning_context_snapshot_prompt_block,
    save_advisory_memory,
    save_athlete_state_snapshot,
    save_planning_context_snapshot,
)
from rps.orchestrator.resolved_context import (
    build_resolved_athlete_context_block,
    build_resolved_kpi_context_block,
)
from rps.orchestrator.workout_export import run_workout_export
from rps.planning.contracts import blocking_messages, validate_snapshot_freshness
from rps.planning.deterministic_context import (
    build_load_capacity_block,
    build_phase_execution_context,
    build_report_evidence_context,
    build_season_phase_slot_block,
    build_selected_scenario_contract_block,
    build_selected_scenario_structure_block,
    build_week_calendar_context,
    build_workout_load_method_block,
    render_context_blocks,
    render_phase_execution_context_block,
    render_report_evidence_context_block,
    render_week_calendar_context_block,
)
from rps.planning.load_bands import selected_kpi_rate_band_from_selection
from rps.workspace.api import Workspace
from rps.workspace.index_exact import IndexExactQuery
from rps.workspace.iso_helpers import (
    IsoWeek,
    envelope_week,
    envelope_week_range,
    parse_iso_week,
    parse_iso_week_range,
    range_contains,
    week_index,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.season_plan_service import resolve_season_plan_phase_info
from rps.workspace.types import ArtifactType

logger = logging.getLogger(__name__)
AMBITION_IF_RANGE_LENGTH = 2

JsonMap = dict[str, object]
OrchestratorResult = dict[str, object]
StepRecord = dict[str, object]


def run_agent_multi_output(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    athlete_id: str,
    tasks: list[AgentTask],
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
    stream_handlers=None,
) -> dict[str, object]:
    """Compatibility dispatcher used by plan-week orchestration and tests."""

    if tasks and all(
        task
        in {
            AgentTask.CREATE_PHASE_GUARDRAILS,
            AgentTask.CREATE_PHASE_STRUCTURE,
            AgentTask.CREATE_PHASE_PREVIEW,
            AgentTask.CREATE_PHASE_FEED_FORWARD,
        }
        for task in tasks
    ):
        return run_phase_flow(
            runtime,
            agent_name=agent_name,
            athlete_id=athlete_id,
            tasks=tasks,
            user_input=user_input,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
            workspace_root=runtime.workspace_root,
        )
    if tasks and all(task == AgentTask.CREATE_WEEK_PLAN for task in tasks):
        return run_week_flow(
            runtime_for=lambda _agent_name: runtime,
            agent_name=agent_name,
            athlete_id=athlete_id,
            tasks=tasks,
            user_input=user_input,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
            workspace_root=runtime.workspace_root,
        )
    return run_agent_multi_output_direct(
        runtime,
        agent_name=agent_name,
        athlete_id=athlete_id,
        tasks=tasks,
        user_input=user_input,
        run_id=run_id,
        model_override=model_override,
        temperature_override=temperature_override,
        stream_handlers=stream_handlers,
    )


def _format_screen_text(text: str) -> str:
    """Insert a blank line before markdown-style headings for readability."""
    lines = text.splitlines()
    formatted: list[str] = []
    for line in lines:
        is_heading = line.startswith("**") or line.startswith("#")
        if is_heading and formatted and formatted[-1] != "":
            formatted.append("")
        formatted.append(line)
    return "\n".join(formatted)


def _log(message: str, level: int = logging.INFO) -> None:
    log_and_print(logger, _format_screen_text(message), level)


def _extract_profile_user_data(profile_payload: JsonMap | None) -> JsonMap:
    """Extract optional Athlete Profile inputs for prompt injection."""
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


def _build_user_data_block(runtime_for: Callable[[str], AgentRuntime], athlete_id: str) -> str:
    """Load Athlete Profile and format user data for prompt injection."""
    try:
        store = LocalArtifactStore(root=runtime_for("season_planner").workspace_root)
        athlete_block = build_resolved_athlete_context_block(store, athlete_id)
        profile_payload = store.load_latest(athlete_id, ArtifactType.ATHLETE_PROFILE)
        user_data = _extract_profile_user_data(profile_payload if isinstance(profile_payload, dict) else None)
        return athlete_block + _format_user_data_block(user_data)
    except Exception:
        return _format_user_data_block({})


def _build_kpi_selection_block(runtime_for: Callable[[str], AgentRuntime], athlete_id: str) -> str:
    """Format resolved KPI guidance for prompt injection."""
    try:
        store = LocalArtifactStore(root=runtime_for("season_planner").workspace_root)
        return build_resolved_kpi_context_block(store, athlete_id)
    except Exception:
        return ""


def _selected_kpi_rate_band(runtime_for: Callable[[str], AgentRuntime], athlete_id: str) -> JsonMap | None:
    """Load selected KPI moving-time-rate guidance for deterministic load-band mapping."""

    try:
        store = LocalArtifactStore(root=runtime_for("season_planner").workspace_root)
        selection = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
        return selected_kpi_rate_band_from_selection(selection if isinstance(selection, dict) else None)
    except Exception:
        return None


def _required_workspace_input_exists(root: Path, athlete_id: str, input_type: str) -> bool:
    """Return whether a required shared input exists in inputs/ or latest/."""
    athlete_root = root / athlete_id
    patterns: dict[str, tuple[str, ...]] = {
        "planning_events": ("planning_events*.json",),
        "logistics": ("logistics*.json",),
    }
    wanted = patterns.get(input_type)
    if not wanted:
        return False
    for folder_name in ("inputs", "latest"):
        folder = athlete_root / folder_name
        if not folder.exists():
            continue
        for pattern in wanted:
            if any(folder.glob(pattern)):
                return True
    return False


def _resolve_required_week_versions(
    store: LocalArtifactStore,
    athlete_id: str,
    week_key: str,
) -> dict[ArtifactType, str]:
    """Resolve the newest stored week-scoped versions for required analysis artefacts."""
    resolved: dict[ArtifactType, str] = {}
    for artifact_type in (ArtifactType.ACTIVITIES_ACTUAL, ArtifactType.ACTIVITIES_TREND):
        version_key = store.resolve_week_version_key(athlete_id, artifact_type, week_key)
        if version_key:
            resolved[artifact_type] = version_key
    return resolved


def _resolve_latest_historical_week_versions(
    store: LocalArtifactStore,
    athlete_id: str,
    target_week: IsoWeek,
) -> dict[ArtifactType, str]:
    """Resolve the newest stored activity artefacts strictly before the target week."""
    resolved: dict[ArtifactType, str] = {}
    target_index = week_index(target_week)
    for artifact_type in (ArtifactType.ACTIVITIES_ACTUAL, ArtifactType.ACTIVITIES_TREND):
        candidates: list[tuple[int, str]] = []
        for version_key in store.list_versions(athlete_id, artifact_type):
            version_week = parse_iso_week(version_key)
            if not version_week:
                continue
            version_index = week_index(version_week)
            if version_index >= target_index:
                continue
            candidates.append((version_index, version_key))
        if candidates:
            candidates.sort()
            resolved[artifact_type] = candidates[-1][1]
    return resolved


def _refresh_required_week_versions(
    athlete_id: str,
    report_week: IsoWeek,
) -> None:
    """Run the Intervals pipeline for the target ISO week to backfill missing activity artefacts."""
    historical_years = int(os.getenv("RPS_HISTORICAL_YEARS", "3"))
    args = argparse.Namespace(
        year=report_week.year,
        week=report_week.week,
        from_date=None,
        to_date=None,
        athlete=athlete_id,
        skip_validate=False,
        historical_years=historical_years,
    )
    pipeline_logger = logging.getLogger("rps.ui.performance")
    run_intervals_pipeline(args, logger=pipeline_logger)


def _mode_for_task(task: AgentTask) -> str | None:
    """Return an injection mode label for a given task."""
    mapping = {
        AgentTask.CREATE_PHASE_GUARDRAILS: "phase_guardrails",
        AgentTask.CREATE_PHASE_STRUCTURE: "phase_structure",
        AgentTask.CREATE_PHASE_PREVIEW: "phase_preview",
        AgentTask.CREATE_PHASE_FEED_FORWARD: "phase_feed_forward",
        AgentTask.CREATE_WEEK_PLAN: "week_plan",
        AgentTask.CREATE_DES_ANALYSIS_REPORT: "des_analysis_report",
    }
    return mapping.get(task)


def create_performance_report(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    report_week: IsoWeek,
    run_id_prefix: str = "performance_report",
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    reasoning_effort_resolver: Callable[[str], str | None] | None = None,
    reasoning_summary_resolver: Callable[[str], str | None] | None = None,
    reasoning_stream_handler: Callable[[str], None] | None = None,
    _flow_wrapped: bool = False,
) -> OrchestratorResult:
    """Create a DES analysis report for the requested ISO week."""
    if not _flow_wrapped and crewai_runtime_status().ok:
        spec = AGENTS["performance_analysis"]
        return run_report_flow(
            lambda: create_performance_report(
                runtime_for,
                athlete_id=athlete_id,
                report_week=report_week,
                run_id_prefix=run_id_prefix,
                model_resolver=model_resolver,
                temperature_resolver=temperature_resolver,
                reasoning_effort_resolver=reasoning_effort_resolver,
                reasoning_summary_resolver=reasoning_summary_resolver,
                reasoning_stream_handler=reasoning_stream_handler,
                _flow_wrapped=True,
            ),
            workspace_root=runtime_for(spec.name).workspace_root,
            athlete_id=athlete_id,
            run_id=run_id_prefix,
        )

    agent_logger = logging.getLogger("rps.agents.crewai_backend")
    summaries: list[str] = []
    log_messages: list[str] = []

    class _ReasoningCaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            message = record.getMessage()
            log_messages.append(message)
            marker = "Reasoning summary:"
            if marker in message:
                summary = message.split(marker, 1)[1].strip()
                if summary and summary not in summaries:
                    summaries.append(summary)

    handler = _ReasoningCaptureHandler()
    agent_logger.addHandler(handler)
    handler.setLevel(logging.INFO)
    runtime = runtime_for("performance_analysis")
    workspace = Workspace.for_athlete(athlete_id, root=runtime.workspace_root)
    season_range = None
    if workspace.latest_exists(ArtifactType.SEASON_PLAN):
        season_plan = workspace.get_latest(ArtifactType.SEASON_PLAN)
        if isinstance(season_plan, dict):
            season_range = envelope_week_range(season_plan)
    report_label = f"{report_week.year:04d}-{report_week.week:02d}"
    if not season_range or not range_contains(season_range, report_week):
        message = (
            "Performance analysis running despite report week "
            f"{report_label} being outside season plan range {season_range.range_key if season_range else 'missing'}."
        )
        _log(message, logging.WARNING)

    report_week_key = report_label
    resolved_week_versions = _resolve_required_week_versions(
        workspace.store,
        athlete_id,
        report_week_key,
    )
    missing_week_versions = [
        artifact_type
        for artifact_type in (ArtifactType.ACTIVITIES_ACTUAL, ArtifactType.ACTIVITIES_TREND)
        if artifact_type not in resolved_week_versions
    ]
    if missing_week_versions:
        _log(
            "Performance analysis target-week activity data missing for "
            f"{report_label}; refreshing Intervals data first."
        )
        try:
            _refresh_required_week_versions(athlete_id, report_week)
        except Exception as exc:
            _log(
                "Intervals refresh before performance analysis failed for "
                f"{report_label}: {exc}",
                logging.WARNING,
            )
        resolved_week_versions = _resolve_required_week_versions(
            workspace.store,
            athlete_id,
            report_week_key,
        )
    required_latest = [
        ArtifactType.KPI_PROFILE,
        ArtifactType.SEASON_PLAN,
    ]
    missing_required = [item for item in required_latest if not workspace.latest_exists(item)]
    for artifact_type in (ArtifactType.ACTIVITIES_ACTUAL, ArtifactType.ACTIVITIES_TREND):
        if artifact_type not in resolved_week_versions:
            missing_required.append(artifact_type)
    missing_context_inputs = [
        input_name
        for input_name in ("planning_events", "logistics")
        if not _required_workspace_input_exists(runtime.workspace_root, athlete_id, input_name)
    ]
    if missing_required or missing_context_inputs:
        missing_labels = [item.value for item in missing_required] + missing_context_inputs
        message = f"Performance analysis skipped: required inputs missing ({', '.join(missing_labels)})."
        _log(message)
        return {"ok": False, "message": message, "step": None}

    analysis_tasks: list[AgentTask] = []
    if workspace.latest_exists(ArtifactType.DES_ANALYSIS_REPORT):
        report = workspace.get_latest(ArtifactType.DES_ANALYSIS_REPORT)
        if isinstance(report, dict):
            week = envelope_week(report)
            if week and week.year == report_week.year and week.week == report_week.week:
                message = f"Found DES_ANALYSIS_REPORT for ISO week {report_label}."
                _log(message)
            else:
                message = f"DES_ANALYSIS_REPORT missing for ISO week {report_label}. Will create."
                _log(message)
                analysis_tasks.append(AgentTask.CREATE_DES_ANALYSIS_REPORT)
        else:
            message = f"DES_ANALYSIS_REPORT missing for ISO week {report_label}. Will create."
            _log(message)
            analysis_tasks.append(AgentTask.CREATE_DES_ANALYSIS_REPORT)
    else:
        message = f"DES_ANALYSIS_REPORT NOT FOUND. Will create for ISO week {report_label}."
        _log(message)
        analysis_tasks.append(AgentTask.CREATE_DES_ANALYSIS_REPORT)

    if not analysis_tasks:
        return {"ok": True, "message": message, "step": None}

    def runtime_for_agent(agent_name: str) -> AgentRuntime:
        if not reasoning_effort_resolver and not reasoning_summary_resolver:
            return runtime_for(agent_name)
        runtime_base = runtime_for(agent_name)
        return replace(
            runtime_base,
            reasoning_effort=reasoning_effort_resolver(agent_name) if reasoning_effort_resolver else runtime_base.reasoning_effort,
            reasoning_summary=reasoning_summary_resolver(agent_name) if reasoning_summary_resolver else runtime_base.reasoning_summary,
        )
    try:
        spec = AGENTS["performance_analysis"]
        message = f"Running Performance-Analyst for ISO week {report_label}."
        _log(message)
        injected_block = render_report_evidence_context_block(
            build_report_evidence_context(
                report_week=report_week,
                resolved_week_versions=resolved_week_versions,
                missing_required=[],
                missing_context_inputs=[],
            )
        )
        stream_chunks: list[str] = []
        def _on_reasoning_chunk(delta: str) -> None:
            stream_chunks.append(delta)
            if reasoning_stream_handler:
                reasoning_stream_handler(delta)

        out = run_agent_multi_output(
            runtime_for_agent(spec.name),
            agent_name=spec.name,
            athlete_id=athlete_id,
            tasks=analysis_tasks,
            user_input=(
                f"Create des_analysis_report for ISO week {report_label} "
                f"(planning week reference). "
                "Use workspace_get_version for target-week activity artefacts before any latest fallback. "
                f"Load ACTIVITIES_ACTUAL version_key {resolved_week_versions[ArtifactType.ACTIVITIES_ACTUAL]} "
                f"and ACTIVITIES_TREND version_key {resolved_week_versions[ArtifactType.ACTIVITIES_TREND]} "
                f"for ISO week {report_label}. "
                "Read KPI profile, season plan, and phase context from workspace. "
                f"{injected_block}"
            ),
            run_id=f"{run_id_prefix}_{report_label}",
            model_override=model_resolver(spec.name) if model_resolver else None,
            temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
            stream_handlers={"on_reasoning": _on_reasoning_chunk},
        )
        step = {
            "agent": "performance_analysis",
            "tasks": [t.value for t in analysis_tasks],
            "result": out,
        }
        if out.get("ok") and out.get("produced"):
            try:
                season_plan_payload = workspace.get_latest(ArtifactType.SEASON_PLAN)
                report_payload = workspace.get_latest(ArtifactType.DES_ANALYSIS_REPORT)
                save_advisory_memory(
                    workspace.store,
                    athlete_id,
                    target_week=report_week,
                    run_id=f"{run_id_prefix}_{report_label}",
                    season_plan_payload=season_plan_payload if isinstance(season_plan_payload, dict) else {},
                    des_analysis_payload=report_payload if isinstance(report_payload, dict) else {},
                )
            except Exception:
                logger.debug("Advisory memory refresh after DES analysis failed.", exc_info=True)
            _log("Done.")
        return {
            "ok": out.get("ok", False),
            "message": message,
            "step": step,
            "reasoning_summaries": summaries,
            "reasoning_log": log_messages.copy(),
            "reasoning_stream": "".join(stream_chunks),
        }
    finally:
        agent_logger.removeHandler(handler)

@dataclass
class PlanWeekResult:
    """Result summary for a plan-week orchestration."""
    ok: bool
    steps: list[StepRecord]


def _normalize_force_steps(force_steps: Iterable[str] | None) -> set[str]:
    """Normalize optional forced step ids to uppercase identifiers."""
    if not force_steps:
        return set()
    return {str(step).strip().upper() for step in force_steps if str(step).strip()}


def _required_phase_artefacts_for_forced_steps(forced_steps: set[str]) -> list[ArtifactType]:
    """Return exact-range phase artefacts required for an isolated forced phase run."""
    if forced_steps == {"PHASE_GUARDRAILS"}:
        return [ArtifactType.PHASE_GUARDRAILS]
    if "PHASE_PREVIEW" in forced_steps or "PHASE_STRUCTURE" in forced_steps:
        return [ArtifactType.PHASE_GUARDRAILS, ArtifactType.PHASE_STRUCTURE, ArtifactType.PHASE_PREVIEW]
    return []


def plan_week(
    runtime: AgentRuntime,
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    force_steps: Iterable[str] | None = None,
    override_text: str | None = None,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    reasoning_effort_resolver: Callable[[str], str | None] | None = None,
    reasoning_summary_resolver: Callable[[str], str | None] | None = None,
) -> PlanWeekResult:
    """Run the Season -> Phase -> Week -> Builder flow if needed.

    Purpose:
        Generate missing/stale phase, week, and workouts artifacts for a target ISO week.
    Inputs:
        force_steps: optional step ids that should rerun even if artifacts already exist.
        override_text: optional override to apply at the selected scope, passed into agent prompts.
    Outputs:
        PlanWeekResult with ok flag and step summaries.
    Side effects:
        Writes phase/ week/ workouts artifacts to the workspace.
    """
    workspace = Workspace.for_athlete(athlete_id, root=runtime.workspace_root)
    store = LocalArtifactStore(root=runtime.workspace_root)
    target = IsoWeek(year=year, week=week)
    forced_steps = _normalize_force_steps(force_steps)
    isolated_phase_force = bool(_required_phase_artefacts_for_forced_steps(forced_steps))

    steps: list[StepRecord] = []
    target_label = f"{year:04d}-{week:02d}"

    message = f"Plan-week start for ISO week {target_label} (athlete={athlete_id})."
    _log(message)
    override_line = f"Override: {override_text.strip()}. " if override_text else ""

    def runtime_for(agent_name: str) -> AgentRuntime:
        if not reasoning_effort_resolver and not reasoning_summary_resolver:
            return runtime
        return replace(
            runtime,
            reasoning_effort=reasoning_effort_resolver(agent_name) if reasoning_effort_resolver else runtime.reasoning_effort,
            reasoning_summary=reasoning_summary_resolver(agent_name) if reasoning_summary_resolver else runtime.reasoning_summary,
        )

    user_data_block = _build_user_data_block(runtime_for, athlete_id)
    kpi_block = _build_kpi_selection_block(runtime_for, athlete_id)
    selected_kpi_rate_band = _selected_kpi_rate_band(runtime_for, athlete_id)

    if not workspace.latest_exists(ArtifactType.SEASON_PLAN):
        message = "Season Plan NOT FOUND. Run season planning first."
        _log(message, logging.ERROR)
        steps.append(
            {
                "agent": "season_planner",
                "tasks": [],
                "result": {"ok": False, "error": "SEASON_PLAN not found"},
            }
        )
        return PlanWeekResult(ok=False, steps=steps)

    season_plan = workspace.get_latest(ArtifactType.SEASON_PLAN)
    if not isinstance(season_plan, dict):
        steps.append(
            {
                "agent": "season_planner",
                "tasks": [],
                "result": {"ok": False, "error": "SEASON_PLAN has invalid payload shape"},
            }
        )
        return PlanWeekResult(ok=False, steps=steps)
    season_range = envelope_week_range(season_plan)
    if not season_range or not range_contains(season_range, target):
        range_label = season_range.range_key if season_range else "missing"
        message = (
            "Season Plan NOT FOUND for target week "
            f"{target_label} (season_plan iso_week_range={range_label})."
        )
        _log(message, logging.ERROR)
        steps.append(
            {
                "agent": "season_planner",
                "tasks": [],
                "result": {
                    "ok": False,
                    "error": "SEASON_PLAN does not cover target week",
                    "season_plan_range": range_label,
                },
            }
        )
        return PlanWeekResult(ok=False, steps=steps)

    phase_info = resolve_season_plan_phase_info(season_plan, target)
    if not phase_info:
        message = f"Matching Phase NOT FOUND in Season Plan for {target_label}."
        _log(message, logging.ERROR)
        steps.append(
            {
                "agent": "season_planner",
                "tasks": [],
                "result": {"ok": False, "error": "Season plan phase not found"},
            }
        )
        return PlanWeekResult(ok=False, steps=steps)

    phase_raw = phase_info.raw
    phase_name = phase_raw.get("name") or phase_info.phase_name or phase_info.phase_id
    phase_type = phase_raw.get("phase_type") or phase_raw.get("cycle") or phase_info.phase_type
    message = (
        "Matching Phase found in Season Plan: "
        f"Phase {phase_info.phase_id} ({phase_name or phase_type or 'unknown'}) "
        f"iso_week_range: {phase_info.phase_range.range_key}"
    )
    _log(message)

    phase_range = phase_info.phase_range
    phase_range_label = phase_range.range_key

    index_query = IndexExactQuery(
        root=workspace.store.root,
        athlete_id=athlete_id,
    )

    def _mtime(path) -> float | None:
        if not path or not path.exists():
            return None
        return path.stat().st_mtime

    def _load_exact_range_payload(artifact_type: ArtifactType):
        version_key = index_query.best_exact_range_version(artifact_type.value, phase_range)
        if not version_key:
            return None
        try:
            payload = store.load_version(athlete_id, artifact_type, version_key)
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None

    def _latest_range_record(artifact_type: ArtifactType):
        index = index_query._index_manager.load()
        artefacts = index.get("artefacts", {})
        if not isinstance(artefacts, dict):
            return None, None, None
        entry = artefacts.get(artifact_type.value)
        if not isinstance(entry, dict):
            return None, None, None
        versions = entry.get("versions", {})
        if not isinstance(versions, dict):
            versions = {}
        candidates: list[tuple[str, dict]] = []
        for record in versions.values():
            if not isinstance(record, dict):
                continue
            path = record.get("path") or record.get("relative_path")
            if not path:
                continue
            full_path = (workspace.store.root / athlete_id / path).resolve()
            if not full_path.exists():
                continue
            range_obj = parse_iso_week_range(record.get("iso_week_range"))
            if not range_obj or range_obj.key != phase_range.key:
                continue
            candidates.append((record.get("created_at", ""), {"record": record, "path": full_path}))
        if not candidates:
            return None, None, None
        candidates.sort()
        chosen = candidates[-1][1]
        return chosen["record"], chosen["path"], _mtime(chosen["path"])

    season_plan_path = store.latest_path(athlete_id, ArtifactType.SEASON_PLAN)
    season_plan_mtime = _mtime(season_plan_path)

    phase_guardrails_record, phase_guardrails_path, phase_guardrails_mtime = _latest_range_record(ArtifactType.PHASE_GUARDRAILS)
    phase_structure_record, phase_structure_path, phase_structure_mtime = _latest_range_record(ArtifactType.PHASE_STRUCTURE)
    phase_preview_record, phase_preview_path, phase_preview_mtime = _latest_range_record(ArtifactType.PHASE_PREVIEW)

    needs_phase_guardrails = phase_guardrails_path is None or "PHASE_GUARDRAILS" in forced_steps
    if season_plan_mtime and phase_guardrails_mtime and season_plan_mtime > phase_guardrails_mtime:
        needs_phase_guardrails = True

    needs_phase_structure = phase_structure_path is None or "PHASE_STRUCTURE" in forced_steps
    if season_plan_mtime and phase_structure_mtime and season_plan_mtime > phase_structure_mtime:
        needs_phase_structure = True
    if phase_guardrails_mtime and phase_structure_mtime and phase_guardrails_mtime > phase_structure_mtime:
        needs_phase_structure = True

    needs_phase_preview = phase_preview_path is None or "PHASE_PREVIEW" in forced_steps
    if phase_structure_mtime and phase_preview_mtime and phase_structure_mtime > phase_preview_mtime:
        needs_phase_preview = True

    if forced_steps == {"PHASE_GUARDRAILS"}:
        needs_phase_structure = False
        needs_phase_preview = False
    elif "PHASE_GUARDRAILS" in forced_steps or "PHASE_STRUCTURE" in forced_steps:
        needs_phase_preview = True

    if needs_phase_guardrails and not isolated_phase_force:
        needs_phase_structure = True
        needs_phase_preview = True
    if needs_phase_structure and not isolated_phase_force:
        needs_phase_preview = True

    if isolated_phase_force and forced_steps == {"PHASE_GUARDRAILS"}:
        _log(
            f"Scoped phase guardrails run requested for range {phase_range_label}; "
            "PHASE_STRUCTURE and PHASE_PREVIEW will be reused if present and will not be rerun."
        )
    elif isolated_phase_force and forced_steps == {"PHASE_STRUCTURE"}:
        _log(
            f"Scoped phase structure run requested for range {phase_range_label}; "
            "PHASE_PREVIEW is included in this scoped run and will be rerun after PHASE_STRUCTURE."
        )
    elif isolated_phase_force and forced_steps == {"PHASE_PREVIEW"}:
        _log(
            f"Scoped phase preview run requested for range {phase_range_label}; "
            "only PHASE_PREVIEW will be rerun."
        )
    elif isolated_phase_force and forced_steps:
        _log(
            f"Scoped phase run requested for range {phase_range_label}; "
            f"bundled phase artefacts: {', '.join(sorted(forced_steps))}."
        )

    phase_tasks: list[AgentTask] = []
    if not needs_phase_guardrails:
        message = f"Found PHASE_GUARDRAILS for phase range {phase_range_label}."
        _log(message)
    else:
        message = f"PHASE_GUARDRAILS missing/stale for phase range {phase_range_label}. Will create."
        _log(message)
        phase_tasks.append(AgentTask.CREATE_PHASE_GUARDRAILS)

    if not needs_phase_structure:
        if forced_steps == {"PHASE_GUARDRAILS"}:
            message = (
                f"Reusing existing PHASE_STRUCTURE for phase range {phase_range_label}; "
                "not queued for this scoped run."
            )
        else:
            message = f"Found PHASE_STRUCTURE for phase range {phase_range_label}."
        _log(message)
    else:
        message = f"PHASE_STRUCTURE missing/stale for phase range {phase_range_label}. Will create."
        _log(message)
        phase_tasks.append(AgentTask.CREATE_PHASE_STRUCTURE)

    if not needs_phase_preview:
        if forced_steps == {"PHASE_GUARDRAILS"}:
            message = (
                f"Reusing existing PHASE_PREVIEW for phase range {phase_range_label}; "
                "not queued for this scoped run."
            )
        else:
            message = f"Found PHASE_PREVIEW for phase range {phase_range_label}."
        _log(message)
    else:
        message = f"PHASE_PREVIEW missing/stale for phase range {phase_range_label}. Will create."
        _log(message)
        phase_tasks.append(AgentTask.CREATE_PHASE_PREVIEW)

    if phase_tasks:
        availability_payload = None
        try:
            loaded_availability = store.load_latest(athlete_id, ArtifactType.AVAILABILITY)
            availability_payload = loaded_availability if isinstance(loaded_availability, dict) else None
        except Exception:
            availability_payload = None
        planning_events_payload = None
        try:
            loaded_events = store.load_latest(athlete_id, ArtifactType.PLANNING_EVENTS)
            planning_events_payload = loaded_events if isinstance(loaded_events, dict) else None
        except Exception:
            planning_events_payload = None
        athlete_profile_payload = None
        try:
            loaded_profile = store.load_latest(athlete_id, ArtifactType.ATHLETE_PROFILE)
            athlete_profile_payload = loaded_profile if isinstance(loaded_profile, dict) else None
        except Exception:
            athlete_profile_payload = None
        kpi_profile_payload = None
        try:
            loaded_kpi = store.load_latest(athlete_id, ArtifactType.KPI_PROFILE)
            kpi_profile_payload = loaded_kpi if isinstance(loaded_kpi, dict) else None
        except Exception:
            kpi_profile_payload = None
        logistics_payload = None
        try:
            loaded_logistics = store.load_latest(athlete_id, ArtifactType.LOGISTICS)
            logistics_payload = loaded_logistics if isinstance(loaded_logistics, dict) else None
        except Exception:
            logistics_payload = None
        zone_model_payload = None
        try:
            loaded_zone_model = store.load_latest(athlete_id, ArtifactType.ZONE_MODEL)
            zone_model_payload = loaded_zone_model if isinstance(loaded_zone_model, dict) else None
        except Exception:
            zone_model_payload = None
        wellness_payload = None
        try:
            loaded_wellness = store.load_latest(athlete_id, ArtifactType.WELLNESS)
            wellness_payload = loaded_wellness if isinstance(loaded_wellness, dict) else None
        except Exception:
            wellness_payload = None
        selection_payload = None
        try:
            loaded_selection = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
            selection_payload = loaded_selection if isinstance(loaded_selection, dict) else None
        except Exception:
            selection_payload = None
        season_scenarios_payload = None
        try:
            loaded_scenarios = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIOS)
            season_scenarios_payload = loaded_scenarios if isinstance(loaded_scenarios, dict) else None
        except Exception:
            season_scenarios_payload = None
        selection_payload = None
        try:
            loaded_selection = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
            selection_payload = loaded_selection if isinstance(loaded_selection, dict) else None
        except Exception:
            selection_payload = None
        season_phase_feed_forward_payload = None
        try:
            ff_version = store.resolve_week_version_key(athlete_id, ArtifactType.SEASON_PHASE_FEED_FORWARD, target_label)
            if ff_version:
                loaded = store.load_version(athlete_id, ArtifactType.SEASON_PHASE_FEED_FORWARD, ff_version)
                season_phase_feed_forward_payload = loaded if isinstance(loaded, dict) else None
        except Exception:
            season_phase_feed_forward_payload = None
        historical_activity_versions = _resolve_latest_historical_week_versions(store, athlete_id, target)
        actual_version = historical_activity_versions.get(ArtifactType.ACTIVITIES_ACTUAL)
        trend_version = historical_activity_versions.get(ArtifactType.ACTIVITIES_TREND)
        athlete_state_snapshot = save_athlete_state_snapshot(
            store,
            athlete_id,
            target_week=target,
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
        planning_context_snapshot = save_planning_context_snapshot(
            store,
            athlete_id,
            target_week=target,
            phase_info=phase_info,
            season_plan_payload=season_plan,
            phase_range=phase_range,
            run_id=run_id,
            availability_payload=availability_payload or {},
            planning_events_payload=planning_events_payload or {},
            season_phase_feed_forward_payload=season_phase_feed_forward_payload or {},
            activities_actual_version=actual_version,
            activities_trend_version=trend_version,
        )
        athlete_snapshot_blockers = blocking_messages(
            validate_snapshot_freshness(
                snapshot_payload=athlete_state_snapshot if isinstance(athlete_state_snapshot, dict) else {},
                expected_source_versions=_expected_source_versions(
                    [
                        ("athlete_profile", athlete_profile_payload),
                        ("kpi_profile", kpi_profile_payload),
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
        )
        if athlete_snapshot_blockers:
            message = "Phase athlete snapshot freshness failed: " + "; ".join(athlete_snapshot_blockers[:5])
            _log(message, logging.ERROR)
            steps.append({"agent": "phase_architect", "tasks": [], "result": {"ok": False, "error": message}})
            return PlanWeekResult(ok=False, steps=steps)
        planning_snapshot_blockers = blocking_messages(
            validate_snapshot_freshness(
                snapshot_payload=planning_context_snapshot if isinstance(planning_context_snapshot, dict) else {},
                expected_source_versions=_expected_source_versions(
                    [
                        ("season_plan", season_plan if isinstance(season_plan, dict) else None),
                        ("availability", availability_payload),
                        ("planning_events", planning_events_payload),
                        ("season_phase_feed_forward", season_phase_feed_forward_payload),
                    ]
                )
                | {
                    key: value
                    for key, value in {
                        "activities_actual": actual_version,
                        "activities_trend": trend_version,
                    }.items()
                    if value
                },
                authoritative=True,
                snapshot_label="PLANNING_CONTEXT_SNAPSHOT",
            )
        )
        if planning_snapshot_blockers:
            message = "Phase planning snapshot freshness failed: " + "; ".join(planning_snapshot_blockers[:5])
            _log(message, logging.ERROR)
            steps.append({"agent": "phase_architect", "tasks": [], "result": {"ok": False, "error": message}})
            return PlanWeekResult(ok=False, steps=steps)
        athlete_state_snapshot_block = build_athlete_state_snapshot_prompt_block(
            athlete_state_snapshot if isinstance(athlete_state_snapshot, dict) else {}
        )
        planning_context_snapshot_block = build_planning_context_snapshot_prompt_block(
            planning_context_snapshot if isinstance(planning_context_snapshot, dict) else {}
        )
        historical_context_line = ""
        if actual_version and trend_version:
            historical_context_line = (
                f"Load historical ACTIVITIES_ACTUAL version_key {actual_version} and "
                f"ACTIVITIES_TREND version_key {trend_version} "
                "with workspace_get_version before any STOP about missing activity context; "
                "never use workspace_get_latest for these activity artefacts. "
            )
        spec = AGENTS["phase_architect"]
        phase_task_labels = ", ".join(task.value for task in phase_tasks)
        selected_structure_context = build_selected_scenario_structure_block(
            season_scenarios_payload=season_scenarios_payload or {},
            selection_payload=selection_payload or {},
            selected_scenario_id=None,
        )
        selected_scenario_contract = build_selected_scenario_contract_block(
            season_scenarios_payload=season_scenarios_payload or {},
            selection_payload=selection_payload or {},
            selected_scenario_id=None,
        )
        phase_slot_context = build_season_phase_slot_block(
            selected_structure_context=selected_structure_context.payload,
            target_week=phase_range.start,
        )
        phase_execution_seed = build_phase_execution_context(
            target_week=target,
            phase_info=phase_info,
            phase_range=phase_range,
            season_plan_payload=season_plan if isinstance(season_plan, dict) else {},
            phase_slot_context=phase_slot_context.payload,
            availability_payload=availability_payload or {},
            logistics_payload=logistics_payload or {},
            planning_events_payload=planning_events_payload or {},
            load_capacity_context={},
        )
        phase_execution_issues = [
            str(item)
            for item in phase_execution_seed.get("blocking_issues") or []
            if str(item).strip()
        ]
        if phase_execution_issues:
            message = "Phase execution context is incomplete: " + "; ".join(phase_execution_issues)
            _log(message, logging.ERROR)
            steps.append({"agent": "phase_architect", "tasks": [], "result": {"ok": False, "error": message}})
            return PlanWeekResult(ok=False, steps=steps)
        week_role_raw = phase_execution_seed.get("week_role_by_iso_week")
        week_role_by_week = {
            str(key): str(value)
            for key, value in week_role_raw.items()
        } if isinstance(week_role_raw, dict) else {}
        phase_role_by_week = {
            str(week_key): str(phase_execution_seed.get("phase_role") or "")
            for week_key in week_role_by_week
        }
        load_capacity_context = build_load_capacity_block(
            target_week=target,
            phase_range=phase_range,
            athlete_profile_payload=athlete_profile_payload or {},
            availability_payload=availability_payload or {},
            logistics_payload=logistics_payload or {},
            zone_model_payload=zone_model_payload or {},
            season_plan_payload=season_plan if isinstance(season_plan, dict) else {},
            wellness_payload=wellness_payload or {},
            kpi_profile_payload=kpi_profile_payload or {},
            kpi_rate_band=selected_kpi_rate_band,
            week_role_by_week=week_role_by_week,
            phase_role_by_week=phase_role_by_week,
            scenario_cadence=phase_execution_seed.get("scenario_cadence"),
        )
        phase_execution_block = render_phase_execution_context_block(
            build_phase_execution_context(
                target_week=target,
                phase_info=phase_info,
                phase_range=phase_range,
                season_plan_payload=season_plan if isinstance(season_plan, dict) else {},
                phase_slot_context=phase_slot_context.payload,
                availability_payload=availability_payload or {},
                logistics_payload=logistics_payload or {},
                planning_events_payload=planning_events_payload or {},
                load_capacity_context=load_capacity_context.payload,
            )
        )
        injected_block = render_context_blocks(
            [selected_structure_context, selected_scenario_contract, phase_slot_context, load_capacity_context]
        ) + phase_execution_block
        message = (
            f"Running Phase-Architect Flow for phase range {phase_range_label} "
            f"covering tasks: {phase_task_labels}."
        )
        _log(message)
        with guardrail_runtime_context(
            phase_execution_context=build_phase_execution_context(
                target_week=target,
                phase_info=phase_info,
                phase_range=phase_range,
                season_plan_payload=season_plan if isinstance(season_plan, dict) else {},
                phase_slot_context=phase_slot_context.payload,
                availability_payload=availability_payload or {},
                logistics_payload=logistics_payload or {},
                planning_events_payload=planning_events_payload or {},
                load_capacity_context=load_capacity_context.payload,
            )
        ):
            out = run_agent_multi_output(
                runtime_for(spec.name),
                agent_name=spec.name,
                athlete_id=athlete_id,
                tasks=phase_tasks,
                user_input=(
                    f"Create phase artefacts {phase_task_labels} for phase range {phase_range_label} "
                    f"(phase {phase_info.phase_id} {phase_name} {phase_type}) covering ISO week {target_label}. "
                    "Use this phase range as the iso_week_range for the artefacts. "
                    "Read season_plan first and use explicit week/range-scoped workspace tools for any "
                    "week-sensitive or exact-range dependencies. "
                    f"{athlete_state_snapshot_block}"
                    f"{planning_context_snapshot_block}"
                    f"{historical_context_line}"
                    f"{user_data_block}"
                    f"{override_line}"
                    f"{injected_block}"
                ),
                run_id=f"{run_id}_phase_bundle",
                model_override=model_resolver(spec.name) if model_resolver else None,
                temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
            )
        steps.append({"agent": "phase_architect", "tasks": [task.value for task in phase_tasks], "result": out})
        if out.get("ok") and out.get("produced"):
            _log("Done.")

    required_phase_artefacts = _required_phase_artefacts_for_forced_steps(forced_steps)
    if required_phase_artefacts:
        phase_steps_ok = all(
            isinstance((result := step.get("result")), dict) and bool(result.get("ok"))
            for step in steps
            if step.get("agent") == "phase_architect"
        )
        if not phase_steps_ok:
            message = f"Scoped phase run failed for range {phase_range_label}."
            _log(message, logging.ERROR)
            return PlanWeekResult(ok=False, steps=steps)
        missing_required = [
            artifact_type
            for artifact_type in required_phase_artefacts
            if not index_query.has_exact_range(artifact_type.value, phase_range)
        ]
        if missing_required:
            missing_labels = ", ".join(artifact_type.value for artifact_type in missing_required)
            message = (
                f"Required isolated phase artefacts missing for range {phase_range_label}: "
                f"{missing_labels}."
            )
            _log(message, logging.ERROR)
            steps.append(
                {
                    "agent": "phase_architect",
                    "tasks": [],
                    "result": {"ok": False, "error": f"Missing isolated phase artefacts: {missing_labels}"},
                }
            )
            return PlanWeekResult(ok=False, steps=steps)
        completed_phase_steps = [task.value.removeprefix("CREATE_") for task in phase_tasks] or sorted(forced_steps)
        label = "Scoped phase run" if len(completed_phase_steps) > 1 else "Isolated phase run"
        _log(
            f"{label} completed for range {phase_range_label} "
            f"(forced_steps={completed_phase_steps})."
        )
        return PlanWeekResult(ok=True, steps=steps)

    if not index_query.has_exact_range(ArtifactType.PHASE_GUARDRAILS.value, phase_range) or not index_query.has_exact_range(
        ArtifactType.PHASE_STRUCTURE.value, phase_range
    ):
        message = (
            f"Required phase artefacts missing for range {phase_range_label}. "
            "Cannot proceed to Week-Planner."
        )
        _log(message, logging.ERROR)
        steps.append(
            {
                "agent": "week_planner",
                "tasks": [],
                "result": {"ok": False, "error": "Missing phase artefacts"},
            }
        )
        return PlanWeekResult(ok=False, steps=steps)

    week_tasks: list[AgentTask] = []
    version_key = target_label
    resolved_key = store.resolve_week_version_key(athlete_id, ArtifactType.WEEK_PLAN, version_key)
    version_exists = resolved_key is not None
    plan_path = store.versioned_path(athlete_id, ArtifactType.WEEK_PLAN, resolved_key) if resolved_key else None
    plan_mtime = _mtime(plan_path)
    needs_week_plan = (not version_exists) or ("WEEK_PLAN" in forced_steps)
    if season_plan_mtime and plan_mtime and season_plan_mtime > plan_mtime:
        needs_week_plan = True
    if phase_guardrails_mtime and plan_mtime and phase_guardrails_mtime > plan_mtime:
        needs_week_plan = True
    if phase_structure_mtime and plan_mtime and phase_structure_mtime > plan_mtime:
        needs_week_plan = True
    if needs_phase_guardrails or needs_phase_structure:
        needs_week_plan = True

    if not needs_week_plan:
        message = f"Found WEEK_PLAN for ISO week {target_label}."
        _log(message)
    else:
        if workspace.latest_exists(ArtifactType.WEEK_PLAN):
            plan = workspace.get_latest(ArtifactType.WEEK_PLAN)
            if isinstance(plan, dict):
                plan_week = envelope_week(plan)
                if plan_week and (plan_week.year == target.year and plan_week.week == target.week):
                    message = (
                        f"WEEK_PLAN matches ISO week {target_label} but is stale. Will create."
                    )
                    _log(message)
                else:
                    message = f"WEEK_PLAN does not match ISO week {target_label}. Will create."
                    _log(message)
            else:
                message = f"WEEK_PLAN does not match ISO week {target_label}. Will create."
                _log(message)
        else:
            message = f"WEEK_PLAN NOT FOUND. Will create for ISO week {target_label}."
            _log(message)
        week_tasks.append(AgentTask.CREATE_WEEK_PLAN)

    week_run_ok: bool | None = None
    if week_tasks:
        availability_payload = None
        try:
            loaded_availability = store.load_latest(athlete_id, ArtifactType.AVAILABILITY)
            availability_payload = loaded_availability if isinstance(loaded_availability, dict) else None
        except Exception:
            availability_payload = None
        planning_events_payload = None
        try:
            loaded_events = store.load_latest(athlete_id, ArtifactType.PLANNING_EVENTS)
            planning_events_payload = loaded_events if isinstance(loaded_events, dict) else None
        except Exception:
            planning_events_payload = None
        athlete_profile_payload = None
        try:
            loaded_profile = store.load_latest(athlete_id, ArtifactType.ATHLETE_PROFILE)
            athlete_profile_payload = loaded_profile if isinstance(loaded_profile, dict) else None
        except Exception:
            athlete_profile_payload = None
        kpi_profile_payload = None
        try:
            loaded_kpi = store.load_latest(athlete_id, ArtifactType.KPI_PROFILE)
            kpi_profile_payload = loaded_kpi if isinstance(loaded_kpi, dict) else None
        except Exception:
            kpi_profile_payload = None
        logistics_payload = None
        try:
            loaded_logistics = store.load_latest(athlete_id, ArtifactType.LOGISTICS)
            logistics_payload = loaded_logistics if isinstance(loaded_logistics, dict) else None
        except Exception:
            logistics_payload = None
        zone_model_payload = None
        try:
            loaded_zone_model = store.load_latest(athlete_id, ArtifactType.ZONE_MODEL)
            zone_model_payload = loaded_zone_model if isinstance(loaded_zone_model, dict) else None
        except Exception:
            zone_model_payload = None
        wellness_payload = None
        try:
            loaded_wellness = store.load_latest(athlete_id, ArtifactType.WELLNESS)
            wellness_payload = loaded_wellness if isinstance(loaded_wellness, dict) else None
        except Exception:
            wellness_payload = None
        selection_payload = None
        try:
            loaded_selection = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
            selection_payload = loaded_selection if isinstance(loaded_selection, dict) else None
        except Exception:
            selection_payload = None
        phase_guardrails_payload = _load_exact_range_payload(ArtifactType.PHASE_GUARDRAILS)
        phase_structure_payload = _load_exact_range_payload(ArtifactType.PHASE_STRUCTURE)
        phase_feed_forward_payload = None
        try:
            ff_version = store.resolve_week_version_key(athlete_id, ArtifactType.PHASE_FEED_FORWARD, target_label)
            if ff_version:
                loaded = store.load_version(athlete_id, ArtifactType.PHASE_FEED_FORWARD, ff_version)
                phase_feed_forward_payload = loaded if isinstance(loaded, dict) else None
        except Exception:
            phase_feed_forward_payload = None
        historical_activity_versions = _resolve_latest_historical_week_versions(
            store,
            athlete_id,
            target,
        )
        actual_version = historical_activity_versions.get(ArtifactType.ACTIVITIES_ACTUAL)
        trend_version = historical_activity_versions.get(ArtifactType.ACTIVITIES_TREND)
        historical_context_line = ""
        if actual_version and trend_version:
            historical_context_line = (
                f"Load historical ACTIVITIES_ACTUAL version_key {actual_version} and "
                f"ACTIVITIES_TREND version_key {trend_version} "
                "with workspace_get_version before any STOP about missing activity context; "
                "never use workspace_get_latest for these activity artefacts. "
            )
        athlete_state_snapshot = save_athlete_state_snapshot(
            store,
            athlete_id,
            target_week=target,
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
        planning_context_snapshot = save_planning_context_snapshot(
            store,
            athlete_id,
            target_week=target,
            phase_info=phase_info,
            season_plan_payload=season_plan,
            phase_range=phase_range,
            run_id=run_id,
            phase_guardrails_payload=phase_guardrails_payload or {},
            phase_structure_payload=phase_structure_payload or {},
            availability_payload=availability_payload or {},
            planning_events_payload=planning_events_payload or {},
            phase_feed_forward_payload=phase_feed_forward_payload or {},
            activities_actual_version=actual_version,
            activities_trend_version=trend_version,
        )
        athlete_snapshot_blockers = blocking_messages(
            validate_snapshot_freshness(
                snapshot_payload=athlete_state_snapshot if isinstance(athlete_state_snapshot, dict) else {},
                expected_source_versions=_expected_source_versions(
                    [
                        ("athlete_profile", athlete_profile_payload),
                        ("kpi_profile", kpi_profile_payload),
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
        )
        if athlete_snapshot_blockers:
            message = "Week athlete snapshot freshness failed: " + "; ".join(athlete_snapshot_blockers[:5])
            _log(message, logging.ERROR)
            steps.append({"agent": "week_planner", "tasks": [], "result": {"ok": False, "error": message}})
            return PlanWeekResult(ok=False, steps=steps)
        planning_snapshot_blockers = blocking_messages(
            validate_snapshot_freshness(
                snapshot_payload=planning_context_snapshot if isinstance(planning_context_snapshot, dict) else {},
                expected_source_versions=_expected_source_versions(
                    [
                        ("season_plan", season_plan if isinstance(season_plan, dict) else None),
                        ("phase_guardrails", phase_guardrails_payload),
                        ("phase_structure", phase_structure_payload),
                        ("availability", availability_payload),
                        ("planning_events", planning_events_payload),
                        ("phase_feed_forward", phase_feed_forward_payload),
                    ]
                )
                | {
                    key: value
                    for key, value in {
                        "activities_actual": actual_version,
                        "activities_trend": trend_version,
                    }.items()
                    if value
                },
                authoritative=True,
                snapshot_label="PLANNING_CONTEXT_SNAPSHOT",
            )
        )
        if planning_snapshot_blockers:
            message = "Week planning snapshot freshness failed: " + "; ".join(planning_snapshot_blockers[:5])
            _log(message, logging.ERROR)
            steps.append({"agent": "week_planner", "tasks": [], "result": {"ok": False, "error": message}})
            return PlanWeekResult(ok=False, steps=steps)
        athlete_state_snapshot_block = build_athlete_state_snapshot_prompt_block(
            athlete_state_snapshot if isinstance(athlete_state_snapshot, dict) else {}
        )
        planning_context_snapshot_block = build_planning_context_snapshot_prompt_block(
            planning_context_snapshot if isinstance(planning_context_snapshot, dict) else {}
        )
        spec = AGENTS["week_planner"]
        message = f"Running Week-Planner for ISO week {target_label}."
        _log(message)
        load_capacity_context = build_load_capacity_block(
            target_week=target,
            phase_range=phase_range,
            athlete_profile_payload=athlete_profile_payload or {},
            availability_payload=availability_payload or {},
            logistics_payload=logistics_payload or {},
            zone_model_payload=zone_model_payload or {},
            season_plan_payload=season_plan if isinstance(season_plan, dict) else {},
            phase_guardrails_payload=phase_guardrails_payload or {},
            wellness_payload=wellness_payload or {},
            kpi_profile_payload=kpi_profile_payload or {},
            kpi_rate_band=selected_kpi_rate_band,
        )
        workout_load_method_block = build_workout_load_method_block(
            athlete_profile_payload=athlete_profile_payload or {},
            zone_model_payload=zone_model_payload or {},
            allowed_intensity_domains=load_capacity_context.payload.get("allowed_intensity_domains") or [],
        )
        week_calendar_context = build_week_calendar_context(
            target_week=target,
            phase_info=phase_info,
            phase_range=phase_range,
            availability_payload=availability_payload or {},
            logistics_payload=logistics_payload or {},
            planning_events_payload=planning_events_payload or {},
            phase_guardrails_payload=phase_guardrails_payload or {},
            phase_structure_payload=phase_structure_payload or {},
            load_capacity_context=load_capacity_context.payload,
        )
        active_weekly_band = week_calendar_context.get("active_weekly_kj_band")
        if not isinstance(active_weekly_band, dict) or not active_weekly_band:
            message = "Week calendar context is incomplete: active weekly load band is missing."
            _log(message, logging.ERROR)
            steps.append({"agent": "week_planner", "tasks": [], "result": {"ok": False, "error": message}})
            return PlanWeekResult(ok=False, steps=steps)
        week_calendar_block = render_week_calendar_context_block(week_calendar_context)
        injected_block = render_context_blocks([load_capacity_context, workout_load_method_block]) + week_calendar_block
        with guardrail_runtime_context(
            availability_payload=availability_payload or {},
            target_week=target,
            week_calendar_context=week_calendar_context,
        ):
            out = run_agent_multi_output(
                runtime_for(spec.name),
                agent_name=spec.name,
                athlete_id=athlete_id,
                tasks=week_tasks,
                user_input=(
                    f"Create week_plan for ISO week {target_label} only (Mon-Sun of that week). "
                    "Do NOT output multiple weeks even if the phase range spans multiple weeks. "
                    "Read phase_guardrails and phase_structure from workspace. "
                    f"For exact-range predecessor reads, use workspace_get_version with version_key {phase_range_label} "
                    "for both PHASE_GUARDRAILS and PHASE_STRUCTURE; never use the single-week key for these range-scoped artefacts. "
                    f"{athlete_state_snapshot_block}"
                    f"{planning_context_snapshot_block}"
                    f"{historical_context_line}"
                    f"{user_data_block}"
                    f"{kpi_block}"
                    f"{override_line}"
                    f"{injected_block}"
                ),
                run_id=f"{run_id}_week",
                model_override=model_resolver(spec.name) if model_resolver else None,
                temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
            )
        steps.append({"agent": "week_planner", "tasks": [t.value for t in week_tasks], "result": out})
        week_run_ok = bool(out.get("ok") and out.get("produced"))
        if out.get("ok") and out.get("produced"):
            _log("Done.")

    if needs_week_plan and week_tasks and week_run_ok is False:
        _log(
            f"Skipping local workout export for ISO week {target_label} because WEEK_PLAN creation failed.",
            logging.WARNING,
        )
    else:
        export_result = run_workout_export(
            store=store,
            athlete_id=athlete_id,
            year=year,
            week=week,
            run_id=run_id,
            plan_mtime=plan_mtime,
            needs_week_plan=needs_week_plan,
            force_export="WORKOUT_EXPORT" in forced_steps,
            log_fn=_log,
        )
        if export_result.get("ran"):
            out = export_result.get("result") or {}
            steps.append(
                {
                    "agent": "workout_export",
                    "tasks": [AgentTask.BUILD_WORKOUT_EXPORT.value],
                    "result": out,
                }
            )
            if out.get("ok") and out.get("produced"):
                _log("Done.")

    ok = (
        all(isinstance((result := step.get("result")), dict) and bool(result.get("ok")) for step in steps)
        if steps
        else True
    )
    if ok:
        try:
            week_plan_payload = (
                store.load_version(athlete_id, ArtifactType.WEEK_PLAN, target_label)
                if store.exists(athlete_id, ArtifactType.WEEK_PLAN, target_label)
                else None
            )
            save_advisory_memory(
                store,
                athlete_id,
                target_week=target,
                run_id=run_id,
                season_plan_payload=season_plan if isinstance(season_plan, dict) else {},
                week_plan_payload=week_plan_payload if isinstance(week_plan_payload, dict) else {},
            )
        except Exception:
            logger.debug("Advisory memory refresh after plan_week failed.", exc_info=True)
    message = f"Plan-week completed for ISO week {target_label} (ok={ok})."
    _log(message)
    return PlanWeekResult(ok=ok, steps=steps)
