"""Orchestrator flow for weekly planning runs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import Callable

from app.agents.multi_output_runner import AgentRuntime, run_agent_multi_output
from app.agents.registry import AGENTS
from app.agents.tasks import AgentTask
from app.workspace.index_exact import IndexExactQuery
from app.workspace.iso_helpers import (
    IsoWeek,
    envelope_week,
    envelope_week_range,
    previous_iso_week,
    range_contains,
)
from app.workspace.macro_phase_service import resolve_macro_phase_info
from app.workspace.api import Workspace
from app.workspace.local_store import LocalArtifactStore
from app.core.logging import log_and_print
from app.workspace.types import ArtifactType

logger = logging.getLogger(__name__)


@dataclass
class PlanWeekResult:
    """Result summary for a plan-week orchestration."""
    ok: bool
    steps: list[dict]


def plan_week(
    runtime: AgentRuntime,
    *,
    athlete_id: str,
    year: int,
    week: int,
    run_id: str,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    reasoning_effort_resolver: Callable[[str], str | None] | None = None,
    reasoning_summary_resolver: Callable[[str], str | None] | None = None,
    force_file_search: bool = True,
) -> PlanWeekResult:
    """Run the Macro -> Meso -> Micro -> Builder -> Analysis flow if needed."""
    workspace = Workspace.for_athlete(athlete_id, root=runtime.workspace_root)
    store = LocalArtifactStore(root=runtime.workspace_root)
    target = IsoWeek(year=year, week=week)

    steps: list[dict] = []
    target_label = f"{year:04d}-{week:02d}"

    message = f"Plan-week start for ISO week {target_label} (athlete={athlete_id})."
    log_and_print(logger, message)

    def runtime_for(agent_name: str) -> AgentRuntime:
        if not reasoning_effort_resolver and not reasoning_summary_resolver:
            return runtime
        return replace(
            runtime,
            reasoning_effort=reasoning_effort_resolver(agent_name) if reasoning_effort_resolver else runtime.reasoning_effort,
            reasoning_summary=reasoning_summary_resolver(agent_name) if reasoning_summary_resolver else runtime.reasoning_summary,
        )

    if not workspace.latest_exists(ArtifactType.MACRO_OVERVIEW):
        message = "Macro Overview NOT FOUND. Run macro planning first."
        log_and_print(logger, message, logging.ERROR)
        steps.append(
            {
                "agent": "macro_planner",
                "tasks": [],
                "result": {"ok": False, "error": "MACRO_OVERVIEW not found"},
            }
        )
        return PlanWeekResult(ok=False, steps=steps)

    macro = workspace.get_latest(ArtifactType.MACRO_OVERVIEW)
    macro_range = envelope_week_range(macro)
    if not macro_range or not range_contains(macro_range, target):
        range_label = macro_range.range_key if macro_range else "missing"
        message = (
            "Macro Overview NOT FOUND for target week "
            f"{target_label} (macro iso_week_range={range_label})."
        )
        log_and_print(logger, message, logging.ERROR)
        steps.append(
            {
                "agent": "macro_planner",
                "tasks": [],
                "result": {
                    "ok": False,
                    "error": "MACRO_OVERVIEW does not cover target week",
                    "macro_range": range_label,
                },
            }
        )
        return PlanWeekResult(ok=False, steps=steps)

    phase_info = resolve_macro_phase_info(macro, target)
    if not phase_info:
        message = f"Matching Phase NOT FOUND in Macro Overview for {target_label}."
        log_and_print(logger, message, logging.ERROR)
        steps.append(
            {
                "agent": "macro_planner",
                "tasks": [],
                "result": {"ok": False, "error": "Macro phase not found"},
            }
        )
        return PlanWeekResult(ok=False, steps=steps)

    phase_raw = phase_info.raw
    phase_name = phase_raw.get("name") or phase_info.phase_name or phase_info.phase_id
    phase_type = phase_raw.get("cycle") or phase_info.phase_type
    message = (
        "Matching Phase found in Macro Overview: "
        f"Phase {phase_info.phase_id} ({phase_name or phase_type or 'unknown'}) "
        f"iso_week_range: {phase_info.phase_range.range_key}"
    )
    log_and_print(logger, message)

    block_range = phase_info.phase_range
    block_range_label = block_range.range_key

    index_query = IndexExactQuery(
        root=workspace.store.root,
        athlete_id=athlete_id,
    )

    meso_tasks: list[AgentTask] = []
    if index_query.has_exact_range(ArtifactType.BLOCK_GOVERNANCE.value, block_range):
        message = f"Found BLOCK_GOVERNANCE for block range {block_range_label}."
        log_and_print(logger, message)
    else:
        message = f"BLOCK_GOVERNANCE NOT FOUND for block range {block_range_label}. Will create."
        log_and_print(logger, message)
        meso_tasks.append(AgentTask.CREATE_BLOCK_GOVERNANCE)

    if index_query.has_exact_range(ArtifactType.BLOCK_EXECUTION_ARCH.value, block_range):
        message = f"Found BLOCK_EXECUTION_ARCH for block range {block_range_label}."
        log_and_print(logger, message)
    else:
        message = f"BLOCK_EXECUTION_ARCH NOT FOUND for block range {block_range_label}. Will create."
        log_and_print(logger, message)
        meso_tasks.append(AgentTask.CREATE_BLOCK_EXECUTION_ARCH)

    if index_query.has_exact_range(ArtifactType.BLOCK_EXECUTION_PREVIEW.value, block_range):
        message = f"Found BLOCK_EXECUTION_PREVIEW for block range {block_range_label}."
        log_and_print(logger, message)
    else:
        message = f"BLOCK_EXECUTION_PREVIEW NOT FOUND for block range {block_range_label}. Will create."
        log_and_print(logger, message)
        meso_tasks.append(AgentTask.CREATE_BLOCK_EXECUTION_PREVIEW)

    if meso_tasks:
        spec = AGENTS["meso_architect"]
        for task in meso_tasks:
            message = f"Running Meso-Architect task {task.value} for block range {block_range_label}."
            log_and_print(logger, message)
            out = run_agent_multi_output(
                runtime_for(spec.name),
                agent_name=spec.name,
                agent_vs_name=spec.vector_store_name,
                athlete_id=athlete_id,
                tasks=[task],
                user_input=(
                    f"Create meso artefact {task.value} for block range {block_range_label} "
                    f"(phase {phase_info.phase_id} {phase_name} {phase_type}) covering ISO week {target_label}. "
                    "Use this block range as the iso_week_range for the artefact. "
                    "Read macro_overview and use workspace_get_latest to pull required inputs."
                ),
                run_id=f"{run_id}_meso_{task.value.lower()}",
                model_override=model_resolver(spec.name) if model_resolver else None,
                temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
                force_file_search=force_file_search,
            )
            steps.append({"agent": "meso_architect", "tasks": [task.value], "result": out})
            if out.get("ok") and out.get("produced"):
                log_and_print(logger, "Done.")

    if not index_query.has_exact_range(ArtifactType.BLOCK_GOVERNANCE.value, block_range) or not index_query.has_exact_range(
        ArtifactType.BLOCK_EXECUTION_ARCH.value, block_range
    ):
        message = (
            f"Required block artefacts missing for range {block_range_label}. "
            "Cannot proceed to Micro-Planner."
        )
        log_and_print(logger, message, logging.ERROR)
        steps.append(
            {
                "agent": "micro_planner",
                "tasks": [],
                "result": {"ok": False, "error": "Missing block artefacts"},
            }
        )
        return PlanWeekResult(ok=False, steps=steps)

    micro_tasks: list[AgentTask] = []
    version_key = target_label
    version_exists = store.exists(athlete_id, ArtifactType.WORKOUTS_PLAN, version_key)
    if version_exists:
        message = f"Found WORKOUTS_PLAN for ISO week {target_label}."
        log_and_print(logger, message)
    else:
        if workspace.latest_exists(ArtifactType.WORKOUTS_PLAN):
            plan = workspace.get_latest(ArtifactType.WORKOUTS_PLAN)
            week = envelope_week(plan)
            if week and (week.year == target.year and week.week == target.week):
                message = (
                    f"WORKOUTS_PLAN latest matches ISO week {target_label} but "
                    "versioned file is missing. Will create."
                )
                log_and_print(logger, message)
            else:
                message = f"WORKOUTS_PLAN does not match ISO week {target_label}. Will create."
                log_and_print(logger, message)
        else:
            message = f"WORKOUTS_PLAN NOT FOUND. Will create for ISO week {target_label}."
            log_and_print(logger, message)
        micro_tasks.append(AgentTask.CREATE_WORKOUTS_PLAN)

    if micro_tasks:
        spec = AGENTS["micro_planner"]
        message = f"Running Micro-Planner for ISO week {target_label}."
        log_and_print(logger, message)
        out = run_agent_multi_output(
            runtime_for(spec.name),
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=micro_tasks,
            user_input=(
                f"Create workouts_plan for ISO week {target_label} only (Mon–Sun of that week). "
                "Do NOT output multiple weeks even if the block range spans multiple weeks. "
                "Read block_governance and block_execution_arch from workspace."
            ),
            run_id=f"{run_id}_micro",
            model_override=model_resolver(spec.name) if model_resolver else None,
            temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
            force_file_search=force_file_search,
        )
        steps.append({"agent": "micro_planner", "tasks": [t.value for t in micro_tasks], "result": out})
        if out.get("ok") and out.get("produced"):
            log_and_print(logger, "Done.")

    builder_tasks: list[AgentTask] = []
    if store.exists(athlete_id, ArtifactType.WORKOUTS_PLAN, version_key):
        builder_tasks.append(AgentTask.CREATE_INTERVALS_WORKOUTS_EXPORT)
        message = f"Running Workout-Builder for ISO week {target_label}."
        log_and_print(logger, message)
        spec = AGENTS["workout_builder"]
        out = run_agent_multi_output(
            runtime_for(spec.name),
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=builder_tasks,
            user_input=(
                f"Convert workouts_plan into Intervals.icu workouts JSON for ISO week {target_label}. "
                "Read workouts_plan from workspace."
            ),
            run_id=f"{run_id}_builder",
            model_override=model_resolver(spec.name) if model_resolver else None,
            temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
            force_file_search=force_file_search,
        )
        steps.append({"agent": "workout_builder", "tasks": [t.value for t in builder_tasks], "result": out})
        if out.get("ok") and out.get("produced"):
            log_and_print(logger, "Done.")
    else:
        message = f"Workout-Builder skipped: WORKOUTS_PLAN {target_label} not found."
        log_and_print(logger, message)

    analysis_tasks: list[AgentTask] = []
    report_week = previous_iso_week(target)
    report_label = f"{report_week.year:04d}-{report_week.week:02d}"
    if macro_range and not range_contains(macro_range, report_week):
        message = (
            "Performance analysis skipped: report week "
            f"{report_label} is outside macro range {macro_range.range_key}."
        )
        log_and_print(logger, message)
    else:
        required = [
            ArtifactType.ACTIVITIES_ACTUAL,
            ArtifactType.ACTIVITIES_TREND,
            ArtifactType.KPI_PROFILE,
            ArtifactType.MACRO_OVERVIEW,
            ArtifactType.BLOCK_GOVERNANCE,
            ArtifactType.BLOCK_EXECUTION_ARCH,
        ]
        if all(workspace.latest_exists(item) for item in required):
            if workspace.latest_exists(ArtifactType.DES_ANALYSIS_REPORT):
                report = workspace.get_latest(ArtifactType.DES_ANALYSIS_REPORT)
                week = envelope_week(report)
                if week and (week.year == report_week.year and week.week == report_week.week):
                    message = f"Found DES_ANALYSIS_REPORT for ISO week {report_label}."
                    log_and_print(logger, message)
                else:
                    message = f"DES_ANALYSIS_REPORT missing for ISO week {report_label}. Will create."
                    log_and_print(logger, message)
                    analysis_tasks.append(AgentTask.CREATE_DES_ANALYSIS_REPORT)
            else:
                message = f"DES_ANALYSIS_REPORT NOT FOUND. Will create for ISO week {report_label}."
                log_and_print(logger, message)
                analysis_tasks.append(AgentTask.CREATE_DES_ANALYSIS_REPORT)
        else:
            message = "Performance analysis skipped: required inputs missing."
            log_and_print(logger, message)

        if analysis_tasks:
            spec = AGENTS["performance_analysis"]
            message = f"Running Performance-Analyst for ISO week {report_label}."
            log_and_print(logger, message)
            out = run_agent_multi_output(
                runtime_for(spec.name),
                agent_name=spec.name,
                agent_vs_name=spec.vector_store_name,
                athlete_id=athlete_id,
                tasks=analysis_tasks,
                user_input=(
                    f"Create des_analysis_report for ISO week {report_label} "
                    f"(planning week {target_label} minus one). "
                    "Read activities_actual, activities_trend, KPI profile, macro overview, meso artefacts from workspace."
                ),
                run_id=f"{run_id}_analysis",
                model_override=model_resolver(spec.name) if model_resolver else None,
                temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
                force_file_search=force_file_search,
            )
            steps.append({"agent": "performance_analysis", "tasks": [t.value for t in analysis_tasks], "result": out})
            if out.get("ok") and out.get("produced"):
                log_and_print(logger, "Done.")

    ok = all(step["result"].get("ok") for step in steps) if steps else True
    message = f"Plan-week completed for ISO week {target_label} (ok={ok})."
    log_and_print(logger, message)
    return PlanWeekResult(ok=ok, steps=steps)
