"""Orchestrator flow for weekly planning runs."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from rps.agents.multi_output_runner import AgentRuntime, run_agent_multi_output
from rps.agents.registry import AGENTS
from rps.agents.tasks import AgentTask
from rps.data_pipeline.season_brief_availability import load_season_brief
from rps.workspace.index_exact import IndexExactQuery
from rps.workspace.iso_helpers import (
    IsoWeek,
    envelope_week,
    envelope_week_range,
    parse_iso_week_range,
    previous_iso_week,
    range_contains,
)
from rps.workspace.season_plan_service import resolve_season_plan_phase_info
from rps.orchestrator.workout_export import create_intervals_workouts_export
from rps.workspace.api import Workspace
from rps.workspace.local_store import LocalArtifactStore
from rps.core.logging import log_and_print
from rps.workspace.types import ArtifactType

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[3]
INJECTION_CONFIG = ROOT / "config" / "agent_knowledge_injection.yaml"


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


def _extract_season_brief_user_data(season_text: str) -> dict[str, object]:
    """Extract optional Season Brief inputs for prompt injection."""
    anchor_match = re.search(
        r"^\s*endurance-anchor-w\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*w\s*$",
        season_text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    range_match = re.search(
        r"^\s*ambition-if-range\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*-\s*([0-9]+(?:\.[0-9]+)?)\s*$",
        season_text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    anchor = float(anchor_match.group(1)) if anchor_match else None
    ambition = None
    if range_match:
        ambition = (float(range_match.group(1)), float(range_match.group(2)))
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
    if isinstance(ambition, tuple) and len(ambition) == 2:
        lines.append(f"ambition_if_range: [{ambition[0]}, {ambition[1]}]")
    else:
        lines.append("ambition_if_range: n/a")
    lines.append("kpi_profile: xxx")
    return "\n".join(lines) + "\n"


def _build_user_data_block(runtime_for: Callable[[str], AgentRuntime], athlete_id: str, year: int) -> str:
    """Load Season Brief and format user data for prompt injection."""
    try:
        athlete_root = runtime_for("season_planner").workspace_root / athlete_id
        _season_path, season_text = load_season_brief(athlete_root, year, None)
        user_data = _extract_season_brief_user_data(season_text)
        return _format_user_data_block(user_data)
    except Exception:
        return _format_user_data_block({})


def _build_kpi_selection_block(runtime_for: Callable[[str], AgentRuntime], athlete_id: str) -> str:
    """Format selected KPI guidance (segment + bounds) for prompt injection."""
    try:
        store = LocalArtifactStore(root=runtime_for("season_planner").workspace_root)
        selection = store.load_latest(athlete_id, ArtifactType.SEASON_SCENARIO_SELECTION)
        kpi_sel = (selection.get("data") or {}).get("kpi_moving_time_rate_guidance_selection")
        if isinstance(kpi_sel, dict):
            segment = kpi_sel.get("segment")
            w_per_kg = kpi_sel.get("w_per_kg") or {}
            kj_per_kg = kpi_sel.get("kj_per_kg_per_hour") or {}
            if segment and w_per_kg and kj_per_kg:
                return (
                    "Selected KPI guidance: "
                    f"kpi_rate_band_selector {segment} "
                    f"(w_per_kg {w_per_kg.get('min')} - {w_per_kg.get('max')}, "
                    f"kj_per_kg_per_hour {kj_per_kg.get('min')} - {kj_per_kg.get('max')}). "
                )
    except Exception:
        return ""
    return ""


def _extract_general_and_phase(spec_text: str) -> str:
    """Return General + Phase sections, skipping Season section when present."""
    lines = spec_text.splitlines()
    season_idx = None
    phase_idx = None
    for idx, line in enumerate(lines):
        if line.startswith("## "):
            if season_idx is None and line.startswith("## Season"):
                season_idx = idx
            if phase_idx is None and line.startswith("## Phase"):
                phase_idx = idx
        if season_idx is not None and phase_idx is not None:
            break

    if phase_idx is None:
        return spec_text
    if season_idx is None or phase_idx < season_idx:
        return spec_text
    head = "\n".join(lines[:season_idx]).rstrip()
    tail = "\n".join(lines[phase_idx:]).lstrip()
    return f"{head}\n\n{tail}".strip()


def _load_load_estimation_spec_phase() -> tuple[str, str]:
    """Load LoadEstimationSpec and keep General + Phase sections only."""
    path = ROOT / "knowledge" / "_shared" / "sources" / "specs" / "load_estimation_spec.md"
    content = path.read_text(encoding="utf-8")
    return str(path), _extract_general_and_phase(content)


def _extract_load_estimation_section(spec_text: str, section: str | None) -> str:
    if not section:
        return spec_text
    section_key = section.strip().lower()
    if section_key == "general":
        lines = spec_text.splitlines()
        season_idx = None
        for idx, line in enumerate(lines):
            if line.startswith("## Season"):
                season_idx = idx
                break
        if season_idx is None:
            return spec_text
        return "\n".join(lines[:season_idx]).rstrip()
    if section_key == "general+phase":
        return _extract_general_and_phase(spec_text)
    return spec_text


def _load_agent_injection_config() -> dict:
    if not INJECTION_CONFIG.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    return yaml.safe_load(INJECTION_CONFIG.read_text(encoding="utf-8")) or {}


def _mode_for_task(task: AgentTask) -> str | None:
    """Return an injection mode label for a given task."""
    mapping = {
        AgentTask.CREATE_PHASE_GUARDRAILS: "phase_guardrails",
        AgentTask.CREATE_PHASE_STRUCTURE: "phase_structure",
        AgentTask.CREATE_PHASE_PREVIEW: "phase_preview",
        AgentTask.CREATE_PHASE_FEED_FORWARD: "phase_feed_forward",
        AgentTask.CREATE_WEEK_PLAN: "week_plan",
        AgentTask.CREATE_INTERVALS_WORKOUTS_EXPORT: "intervals_workouts",
        AgentTask.CREATE_DES_ANALYSIS_REPORT: "des_analysis_report",
    }
    return mapping.get(task)


def create_performance_report(
    runtime_for: Callable[[str], AgentRuntime],
    *,
    athlete_id: str,
    report_week: IsoWeek,
    run_id_prefix: str = "performance_report",
    force_file_search: bool = True,
    max_num_results: int = 20,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    reasoning_effort_resolver: Callable[[str], str | None] | None = None,
    reasoning_summary_resolver: Callable[[str], str | None] | None = None,
    reasoning_stream_handler: Callable[[str], None] | None = None,
) -> dict:
    """Create a DES analysis report for the requested ISO week."""
    agent_logger = logging.getLogger("rps.agents.multi_output_runner")
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
        season_range = envelope_week_range(season_plan)
    report_label = f"{report_week.year:04d}-{report_week.week:02d}"
    if not season_range or not range_contains(season_range, report_week):
        message = (
            "Performance analysis running despite report week "
            f"{report_label} being outside season plan range {season_range.range_key if season_range else 'missing'}."
        )
        _log(message, logging.WARNING)

    required = [
        ArtifactType.ACTIVITIES_ACTUAL,
        ArtifactType.ACTIVITIES_TREND,
        ArtifactType.KPI_PROFILE,
        ArtifactType.SEASON_PLAN,
        ArtifactType.PHASE_GUARDRAILS,
        ArtifactType.PHASE_STRUCTURE,
    ]
    missing_required = [item for item in required if not workspace.latest_exists(item)]
    if missing_required:
        message = "Performance analysis skipped: required inputs missing."
        _log(message)
        return {"ok": False, "message": message, "step": None}

    analysis_tasks: list[AgentTask] = []
    if workspace.latest_exists(ArtifactType.DES_ANALYSIS_REPORT):
        report = workspace.get_latest(ArtifactType.DES_ANALYSIS_REPORT)
        week = envelope_week(report)
        if week and week.year == report_week.year and week.week == report_week.week:
            message = f"Found DES_ANALYSIS_REPORT for ISO week {report_label}."
            _log(message)
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
        mode = _mode_for_task(AgentTask.CREATE_DES_ANALYSIS_REPORT)
        injected_block = _build_injection_block("performance_analysis", mode=mode)
        stream_chunks: list[str] = []
        def _on_reasoning_chunk(delta: str) -> None:
            stream_chunks.append(delta)
            if reasoning_stream_handler:
                reasoning_stream_handler(delta)

        out = run_agent_multi_output(
            runtime_for_agent(spec.name),
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=analysis_tasks,
            user_input=(
                f"Create des_analysis_report for ISO week {report_label} "
                f"(planning week reference). "
                "Read activities_actual, activities_trend, KPI profile, season plan, phase artefacts from workspace. "
                f"{injected_block}"
            ),
            run_id=f"{run_id_prefix}_{report_label}",
            model_override=model_resolver(spec.name) if model_resolver else None,
            temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
            force_file_search=force_file_search,
            max_num_results=max_num_results,
            stream_handlers={"on_reasoning": _on_reasoning_chunk},
        )
        step = {
            "agent": "performance_analysis",
            "tasks": [t.value for t in analysis_tasks],
            "result": out,
        }
        if out.get("ok") and out.get("produced"):
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


def _build_injection_block(agent_name: str, mode: str | None = None) -> str:
    config = _load_agent_injection_config()
    agent_cfg = (config.get("agents") or {}).get(agent_name) or {}
    base_items = agent_cfg.get("inject") or []
    items = list(base_items)
    if mode:
        modes = agent_cfg.get("modes") or {}
        mode_cfg = modes.get(mode) or {}
        bundle_id = mode_cfg.get("bundle_id")
        bundle_items: list = []
        if bundle_id:
            bundles = agent_cfg.get("bundles") or []
            bundle_cfg = next((b for b in bundles if b.get("id") == bundle_id), {})
            bundle_items = bundle_cfg.get("inject") or []
        mode_items = mode_cfg.get("inject") or []
        combined: list = []
        combined.extend(base_items)
        combined.extend(bundle_items)
        combined.extend(mode_items)

        # Deduplicate while preserving order (dicts keyed by stable JSON).
        seen: set[str] = set()
        deduped: list = []
        for item in combined:
            if isinstance(item, dict):
                key = json.dumps(item, sort_keys=True, ensure_ascii=True)
            else:
                key = str(item)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        items = deduped
    if not items:
        return ""
    chunks: list[str] = [
        (
            "Injected mandatory knowledge "
            f"(mode={mode}; read in full; do NOT file_search these files):"
            if mode
            else "Injected mandatory knowledge (read in full; do NOT file_search these files):"
        )
    ]
    for item in items:
        path_str = None
        label = None
        section = None
        if isinstance(item, dict):
            path_str = item.get("path")
            label = item.get("label")
            section = item.get("section")
        elif isinstance(item, str):
            path_str = item
        if not path_str:
            continue
        path = (ROOT / path_str).resolve()
        header = label or str(path)
        try:
            content = path.read_text(encoding="utf-8")
            if path.name == "load_estimation_spec.md":
                content = _extract_load_estimation_section(content, section)
            chunks.append(f"{header}:\n\"\"\"\n{content}\n\"\"\"\n")
        except FileNotFoundError:
            chunks.append(f"{header}: MISSING\n")
    return "\n".join(chunks)


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
    override_text: str | None = None,
    model_resolver: Callable[[str], str] | None = None,
    temperature_resolver: Callable[[str], float | None] | None = None,
    reasoning_effort_resolver: Callable[[str], str | None] | None = None,
    reasoning_summary_resolver: Callable[[str], str | None] | None = None,
    force_file_search: bool = True,
    max_num_results: int = 20,
) -> PlanWeekResult:
    """Run the Season -> Phase -> Week -> Builder flow if needed.

    Purpose:
        Generate missing/stale phase, week, and workouts artifacts for a target ISO week.
    Inputs:
        override_text: optional override to apply at the selected scope, passed into agent prompts.
    Outputs:
        PlanWeekResult with ok flag and step summaries.
    Side effects:
        Writes phase/ week/ workouts artifacts to the workspace.
    """
    workspace = Workspace.for_athlete(athlete_id, root=runtime.workspace_root)
    store = LocalArtifactStore(root=runtime.workspace_root)
    target = IsoWeek(year=year, week=week)

    steps: list[dict] = []
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

    user_data_block = _build_user_data_block(runtime_for, athlete_id, year)
    kpi_block = _build_kpi_selection_block(runtime_for, athlete_id)

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
    phase_type = phase_raw.get("cycle") or phase_info.phase_type
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

    needs_phase_guardrails = phase_guardrails_path is None
    if season_plan_mtime and phase_guardrails_mtime and season_plan_mtime > phase_guardrails_mtime:
        needs_phase_guardrails = True

    needs_phase_structure = phase_structure_path is None
    if season_plan_mtime and phase_structure_mtime and season_plan_mtime > phase_structure_mtime:
        needs_phase_structure = True
    if phase_guardrails_mtime and phase_structure_mtime and phase_guardrails_mtime > phase_structure_mtime:
        needs_phase_structure = True

    needs_phase_preview = phase_preview_path is None
    if phase_structure_mtime and phase_preview_mtime and phase_structure_mtime > phase_preview_mtime:
        needs_phase_preview = True

    if needs_phase_guardrails:
        needs_phase_structure = True
        needs_phase_preview = True
    if needs_phase_structure:
        needs_phase_preview = True

    phase_tasks: list[AgentTask] = []
    if not needs_phase_guardrails:
        message = f"Found PHASE_GUARDRAILS for phase range {phase_range_label}."
        _log(message)
    else:
        message = f"PHASE_GUARDRAILS missing/stale for phase range {phase_range_label}. Will create."
        _log(message)
        phase_tasks.append(AgentTask.CREATE_PHASE_GUARDRAILS)

    if not needs_phase_structure:
        message = f"Found PHASE_STRUCTURE for phase range {phase_range_label}."
        _log(message)
    else:
        message = f"PHASE_STRUCTURE missing/stale for phase range {phase_range_label}. Will create."
        _log(message)
        phase_tasks.append(AgentTask.CREATE_PHASE_STRUCTURE)

    if not needs_phase_preview:
        message = f"Found PHASE_PREVIEW for phase range {phase_range_label}."
        _log(message)
    else:
        message = f"PHASE_PREVIEW missing/stale for phase range {phase_range_label}. Will create."
        _log(message)
        phase_tasks.append(AgentTask.CREATE_PHASE_PREVIEW)

    if phase_tasks:
        spec = AGENTS["phase_architect"]
        for task in phase_tasks:
            mode = _mode_for_task(task)
            injected_block = _build_injection_block("phase_architect", mode=mode)
            message = f"Running Phase-Architect task {task.value} for phase range {phase_range_label}."
            _log(message)
            out = run_agent_multi_output(
                runtime_for(spec.name),
                agent_name=spec.name,
                agent_vs_name=spec.vector_store_name,
                athlete_id=athlete_id,
                tasks=[task],
                user_input=(
                    f"Create phase artefact {task.value} for phase range {phase_range_label} "
                    f"(phase {phase_info.phase_id} {phase_name} {phase_type}) covering ISO week {target_label}. "
                    "Use this phase range as the iso_week_range for the artefact. "
                    "Read season_plan and use workspace_get_latest to pull required inputs. "
                    f"{user_data_block}"
                    f"{kpi_block}"
                    f"{override_line}"
                    f"{injected_block}"
                ),
                run_id=f"{run_id}_phase_{task.value.lower()}",
                model_override=model_resolver(spec.name) if model_resolver else None,
                temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
                force_file_search=force_file_search,
                max_num_results=max_num_results,
            )
            steps.append({"agent": "phase_architect", "tasks": [task.value], "result": out})
            if out.get("ok") and out.get("produced"):
                _log("Done.")
            elif not out.get("ok"):
                _log(f"Phase-Architect failed for {task.value}. Aborting remaining phase tasks.", logging.ERROR)
                return PlanWeekResult(ok=False, steps=steps)

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
    needs_week_plan = not version_exists
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
            week = envelope_week(plan)
            if week and (week.year == target.year and week.week == target.week):
                message = (
                    f"WEEK_PLAN matches ISO week {target_label} but is stale. Will create."
                )
                _log(message)
            else:
                message = f"WEEK_PLAN does not match ISO week {target_label}. Will create."
                _log(message)
        else:
            message = f"WEEK_PLAN NOT FOUND. Will create for ISO week {target_label}."
            _log(message)
        week_tasks.append(AgentTask.CREATE_WEEK_PLAN)

    if week_tasks:
        spec = AGENTS["week_planner"]
        message = f"Running Week-Planner for ISO week {target_label}."
        _log(message)
        mode = _mode_for_task(AgentTask.CREATE_WEEK_PLAN)
        injected_block = _build_injection_block("week_planner", mode=mode)
        out = run_agent_multi_output(
            runtime_for(spec.name),
            agent_name=spec.name,
            agent_vs_name=spec.vector_store_name,
            athlete_id=athlete_id,
            tasks=week_tasks,
            user_input=(
                f"Create week_plan for ISO week {target_label} only (Mon–Sun of that week). "
                "Do NOT output multiple weeks even if the phase range spans multiple weeks. "
                "Read phase_guardrails and phase_structure from workspace. "
                f"{user_data_block}"
                f"{kpi_block}"
                f"{override_line}"
                f"{injected_block}"
            ),
            run_id=f"{run_id}_week",
            model_override=model_resolver(spec.name) if model_resolver else None,
            temperature_override=temperature_resolver(spec.name) if temperature_resolver else None,
            force_file_search=force_file_search,
            max_num_results=max_num_results,
        )
        steps.append({"agent": "week_planner", "tasks": [t.value for t in week_tasks], "result": out})
        if out.get("ok") and out.get("produced"):
            _log("Done.")

    injected_block = _build_injection_block(
        "workout_builder",
        mode=_mode_for_task(AgentTask.CREATE_INTERVALS_WORKOUTS_EXPORT),
    )
    export_result = create_intervals_workouts_export(
        runtime_for,
        store=store,
        athlete_id=athlete_id,
        year=year,
        week=week,
        run_id=run_id,
        injected_block=injected_block,
        plan_mtime=plan_mtime,
        needs_week_plan=needs_week_plan,
        override_text=override_text,
        force_file_search=force_file_search,
        max_num_results=max_num_results,
        model_resolver=model_resolver,
        temperature_resolver=temperature_resolver,
        log_fn=_log,
    )
    if export_result.get("ran"):
        out = export_result.get("result") or {}
        steps.append(
            {
                "agent": "workout_builder",
                "tasks": [AgentTask.CREATE_INTERVALS_WORKOUTS_EXPORT.value],
                "result": out,
            }
        )
        if out.get("ok") and out.get("produced"):
            _log("Done.")


    ok = all(step["result"].get("ok") for step in steps) if steps else True
    message = f"Plan-week completed for ISO week {target_label} (ok={ok})."
    _log(message)
    return PlanWeekResult(ok=ok, steps=steps)
