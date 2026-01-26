"""Orchestrator flow for weekly planning runs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from app.agents.multi_output_runner import AgentRuntime, run_agent_multi_output
from app.agents.registry import AGENTS
from app.agents.tasks import AgentTask
from app.workspace.index_exact import IndexExactQuery
from app.workspace.iso_helpers import (
    IsoWeek,
    envelope_week,
    envelope_week_range,
    parse_iso_week_range,
    previous_iso_week,
    range_contains,
)
from app.workspace.macro_phase_service import resolve_macro_phase_info
from app.workspace.api import Workspace
from app.workspace.local_store import LocalArtifactStore
from app.core.logging import log_and_print
from app.workspace.types import ArtifactType

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[3]


def _extract_general_and_meso(spec_text: str) -> str:
    """Return General + Meso sections, skipping Macro section when present."""
    lines = spec_text.splitlines()
    macro_idx = None
    meso_idx = None
    for idx, line in enumerate(lines):
        if line.startswith("## "):
            if macro_idx is None and line.startswith("## Macro"):
                macro_idx = idx
            if meso_idx is None and line.startswith("## Meso"):
                meso_idx = idx
        if macro_idx is not None and meso_idx is not None:
            break

    if meso_idx is None:
        return spec_text
    if macro_idx is None or meso_idx < macro_idx:
        return spec_text
    head = "\n".join(lines[:macro_idx]).rstrip()
    tail = "\n".join(lines[meso_idx:]).lstrip()
    return f"{head}\n\n{tail}".strip()


def _load_load_estimation_spec_meso() -> tuple[str, str]:
    """Load LoadEstimationSpec and keep General + Meso sections only."""
    path = ROOT / "knowledge" / "_shared" / "sources" / "specs" / "load_estimation_spec.md"
    content = path.read_text(encoding="utf-8")
    return str(path), _extract_general_and_meso(content)


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
    max_num_results: int = 20,
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

    def _mtime(path) -> float | None:
        if not path or not path.exists():
            return None
        return path.stat().st_mtime

    def _latest_range_record(artifact_type: ArtifactType):
        index = index_query._index_manager.load()
        entry = index.get("artefacts", {}).get(artifact_type.value)
        if not entry:
            return None, None, None
        versions: dict = entry.get("versions", {})
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
            if not range_obj or range_obj.key != block_range.key:
                continue
            candidates.append((record.get("created_at", ""), {"record": record, "path": full_path}))
        if not candidates:
            return None, None, None
        candidates.sort()
        chosen = candidates[-1][1]
        return chosen["record"], chosen["path"], _mtime(chosen["path"])

    macro_path = store.latest_path(athlete_id, ArtifactType.MACRO_OVERVIEW)
    macro_mtime = _mtime(macro_path)

    block_gov_record, block_gov_path, block_gov_mtime = _latest_range_record(ArtifactType.BLOCK_GOVERNANCE)
    block_arch_record, block_arch_path, block_arch_mtime = _latest_range_record(ArtifactType.BLOCK_EXECUTION_ARCH)
    block_preview_record, block_preview_path, block_preview_mtime = _latest_range_record(ArtifactType.BLOCK_EXECUTION_PREVIEW)

    needs_block_gov = block_gov_path is None
    if macro_mtime and block_gov_mtime and macro_mtime > block_gov_mtime:
        needs_block_gov = True

    needs_block_arch = block_arch_path is None
    if macro_mtime and block_arch_mtime and macro_mtime > block_arch_mtime:
        needs_block_arch = True
    if block_gov_mtime and block_arch_mtime and block_gov_mtime > block_arch_mtime:
        needs_block_arch = True

    needs_block_preview = block_preview_path is None
    if block_arch_mtime and block_preview_mtime and block_arch_mtime > block_preview_mtime:
        needs_block_preview = True

    if needs_block_gov:
        needs_block_arch = True
        needs_block_preview = True
    if needs_block_arch:
        needs_block_preview = True

    meso_tasks: list[AgentTask] = []
    if not needs_block_gov:
        message = f"Found BLOCK_GOVERNANCE for block range {block_range_label}."
        log_and_print(logger, message)
    else:
        message = f"BLOCK_GOVERNANCE missing/stale for block range {block_range_label}. Will create."
        log_and_print(logger, message)
        meso_tasks.append(AgentTask.CREATE_BLOCK_GOVERNANCE)

    if not needs_block_arch:
        message = f"Found BLOCK_EXECUTION_ARCH for block range {block_range_label}."
        log_and_print(logger, message)
    else:
        message = f"BLOCK_EXECUTION_ARCH missing/stale for block range {block_range_label}. Will create."
        log_and_print(logger, message)
        meso_tasks.append(AgentTask.CREATE_BLOCK_EXECUTION_ARCH)

    if not needs_block_preview:
        message = f"Found BLOCK_EXECUTION_PREVIEW for block range {block_range_label}."
        log_and_print(logger, message)
    else:
        message = f"BLOCK_EXECUTION_PREVIEW missing/stale for block range {block_range_label}. Will create."
        log_and_print(logger, message)
        meso_tasks.append(AgentTask.CREATE_BLOCK_EXECUTION_PREVIEW)

    if meso_tasks:
        spec = AGENTS["meso_architect"]
        try:
            spec_path, spec_content = _load_load_estimation_spec_meso()
            spec_block = (
                "LoadEstimationSpec (General + Meso sections; loaded from "
                f"{spec_path}):\n\"\"\"\n{spec_content}\n\"\"\"\n"
            )
        except FileNotFoundError as exc:
            spec_block = f"LoadEstimationSpec missing: {exc}\n"
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
                    "Read macro_overview and use workspace_get_latest to pull required inputs. "
                    f"{spec_block}"
                ),
                run_id=f"{run_id}_meso_{task.value.lower()}",
                model_override=model_resolver(spec.name) if model_resolver else None,
                temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
                force_file_search=force_file_search,
                max_num_results=max_num_results,
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
    plan_path = store.versioned_path(athlete_id, ArtifactType.WORKOUTS_PLAN, version_key) if version_exists else None
    plan_mtime = _mtime(plan_path)
    needs_workouts_plan = not version_exists
    if macro_mtime and plan_mtime and macro_mtime > plan_mtime:
        needs_workouts_plan = True
    if block_gov_mtime and plan_mtime and block_gov_mtime > plan_mtime:
        needs_workouts_plan = True
    if block_arch_mtime and plan_mtime and block_arch_mtime > plan_mtime:
        needs_workouts_plan = True
    if needs_block_gov or needs_block_arch:
        needs_workouts_plan = True

    if not needs_workouts_plan:
        message = f"Found WORKOUTS_PLAN for ISO week {target_label}."
        log_and_print(logger, message)
    else:
        if workspace.latest_exists(ArtifactType.WORKOUTS_PLAN):
            plan = workspace.get_latest(ArtifactType.WORKOUTS_PLAN)
            week = envelope_week(plan)
            if week and (week.year == target.year and week.week == target.week):
                message = (
                    f"WORKOUTS_PLAN matches ISO week {target_label} but is stale. Will create."
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
            max_num_results=max_num_results,
        )
        steps.append({"agent": "micro_planner", "tasks": [t.value for t in micro_tasks], "result": out})
        if out.get("ok") and out.get("produced"):
            log_and_print(logger, "Done.")

    builder_tasks: list[AgentTask] = []
    if store.exists(athlete_id, ArtifactType.WORKOUTS_PLAN, version_key):
        intervals_version = "raw"
        intervals_path = (
            store.versioned_path(athlete_id, ArtifactType.INTERVALS_WORKOUTS, intervals_version)
            if store.exists(athlete_id, ArtifactType.INTERVALS_WORKOUTS, intervals_version)
            else None
        )
        intervals_mtime = _mtime(intervals_path)
        needs_intervals = intervals_path is None
        if plan_mtime and intervals_mtime and plan_mtime > intervals_mtime:
            needs_intervals = True
        if needs_workouts_plan:
            needs_intervals = True
        if not needs_intervals:
            message = f"Found INTERVALS_WORKOUTS for ISO week {target_label}."
            log_and_print(logger, message)
        else:
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
                max_num_results=max_num_results,
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
                max_num_results=max_num_results,
            )
            steps.append({"agent": "performance_analysis", "tasks": [t.value for t in analysis_tasks], "result": out})
            if out.get("ok") and out.get("produced"):
                log_and_print(logger, "Done.")

    ok = all(step["result"].get("ok") for step in steps) if steps else True
    message = f"Plan-week completed for ISO week {target_label} (ok={ok})."
    log_and_print(logger, message)
    return PlanWeekResult(ok=ok, steps=steps)
