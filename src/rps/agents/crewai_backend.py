"""CrewAI execution backend for planner and advisory artefact tasks."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import Any

from rps.agents.knowledge_injection import build_injection_block
from rps.agents.output_normalization import (
    extract_planning_events_document,
    injection_mode_for_tasks,
    load_shared_knowledge_source,
    normalize_phase_guardrails_document,
    normalize_season_scenarios_document,
    normalize_workout_percent_ranges,
)
from rps.agents.tasks import OUTPUT_SPECS, AgentTask
from rps.crewai_runtime.bindings import (
    build_agent_blueprints,
    build_task_blueprints,
    output_model_for_kind,
)
from rps.crewai_runtime.config import load_crewai_config_bundle
from rps.crewai_runtime.provider import build_crewai_llm_kwargs
from rps.tools.workspace_read_tools import ReadToolContext, read_tool_defs, read_tool_handlers
from rps.workouts.week_plan_consistency import normalize_week_plan_consistency
from rps.workspace.guarded_store import GuardedValidatedStore
from rps.workspace.schema_registry import SchemaValidationError
from rps.workspace.types import ArtifactType

from .runtime import AgentRuntime

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[3]

JsonMap = dict[str, Any]

_TASK_BLUEPRINT_BY_AGENT_TASK = {
    AgentTask.CREATE_SEASON_SCENARIOS: "season_scenarios",
    AgentTask.CREATE_SEASON_SCENARIO_SELECTION: "season_scenarios",
    AgentTask.CREATE_SEASON_PLAN: "season_plan",
    AgentTask.CREATE_SEASON_PHASE_FEED_FORWARD: "season_phase_feed_forward",
    AgentTask.CREATE_PHASE_GUARDRAILS: "phase_guardrails",
    AgentTask.CREATE_PHASE_STRUCTURE: "phase_structure",
    AgentTask.CREATE_PHASE_PREVIEW: "phase_preview",
    AgentTask.CREATE_PHASE_FEED_FORWARD: "phase_feed_forward",
    AgentTask.CREATE_WEEK_PLAN: "week_plan",
    AgentTask.CREATE_DES_ANALYSIS_REPORT: "des_analysis_report",
}


def _mandatory_output_doc_for_schema(schema_file: str) -> str | None:
    mandatory_by_schema = {
        "season_scenarios.schema.json": "mandatory_output_season_scenarios.md",
        "season_scenario_selection.schema.json": "mandatory_output_season_scenario_selection.md",
        "season_plan.schema.json": "mandatory_output_season_plan.md",
        "season_phase_feed_forward.schema.json": "mandatory_output_season_phase_feed_forward.md",
        "phase_guardrails.schema.json": "mandatory_output_phase_guardrails.md",
        "phase_structure.schema.json": "mandatory_output_phase_structure.md",
        "phase_preview.schema.json": "mandatory_output_phase_preview.md",
        "phase_feed_forward.schema.json": "mandatory_output_phase_feed_forward.md",
        "week_plan.schema.json": "mandatory_output_week_plan.md",
        "des_analysis_report.schema.json": "mandatory_output_des_analysis_report.md",
    }
    return mandatory_by_schema.get(schema_file)


def _fill_season_plan(document: JsonMap) -> JsonMap:
    """Normalize common SEASON_PLAN placement issues."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta") or {}
    if str(meta.get("artifact_type", "")).upper() != "SEASON_PLAN":
        return document
    if not meta.get("data_confidence"):
        meta["data_confidence"] = "UNKNOWN"
    document["meta"] = meta
    data = document.get("data") or {}
    if not isinstance(data, dict):
        return document
    if "explicit_forbidden_content" not in data or not isinstance(
        data.get("explicit_forbidden_content"), list
    ):
        data["explicit_forbidden_content"] = [
            "phase definitions (phase plans)",
            "weekly schedules",
            "day-by-day structure",
            "workouts or interval prescriptions",
            "numeric progression rules",
            "daily or session-level kJ targets",
        ]
    if "self_check" not in data or not isinstance(data.get("self_check"), dict):
        data["self_check"] = {
            "planning_horizon_is_at_least_8_weeks": True,
            "every_phase_defines_weekly_kj_corridor": True,
            "every_phase_includes_kj_per_kg_guardrails_and_reference_mass": True,
            "every_phase_maps_to_cycle_and_deload_intent": True,
            "every_phase_includes_narrative_and_metabolic_focus": True,
            "every_phase_includes_evaluation_focus_and_exit_assumptions": True,
            "season_load_envelope_and_assumptions_documented": True,
            "principles_and_scientific_foundation_documented": True,
            "allowed_forbidden_domains_listed": True,
            "no_phase_or_week_planning_content": True,
            "header_includes_implements_iso_week_range_trace": True,
        }
    document["data"] = data
    return document


def _normalize_week_plan_meta(document: JsonMap) -> JsonMap:
    """Coerce WEEK_PLAN header constants to the canonical schema values."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta")
    if not isinstance(meta, dict):
        return document
    meta["artifact_type"] = "WEEK_PLAN"
    meta["schema_id"] = "WeekPlanInterface"
    meta["schema_version"] = "1.2"
    meta["authority"] = "Binding"
    meta["owner_agent"] = "Week-Planner"
    if "notes" not in meta or meta.get("notes") is None:
        meta["notes"] = ""
    document["meta"] = meta
    data = document.get("data")
    if isinstance(data, dict):
        workouts = data.get("workouts")
        if isinstance(workouts, list):
            for workout in workouts:
                if not isinstance(workout, dict):
                    continue
                workout_text = workout.get("workout_text")
                if isinstance(workout_text, str):
                    workout["workout_text"] = normalize_workout_percent_ranges(workout_text)
            data["workouts"] = workouts
        document["data"] = data
    return document


def _normalize_des_analysis_report(document: JsonMap) -> JsonMap:
    """Coerce DES analysis report constants to the canonical schema values."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta")
    if isinstance(meta, dict):
        meta["artifact_type"] = "DES_ANALYSIS_REPORT"
        meta["schema_id"] = "DESAnalysisInterface"
        meta["schema_version"] = "1.1"
        meta["authority"] = "Binding"
        meta["owner_agent"] = "Performance-Analyst"
        if "notes" not in meta or meta.get("notes") is None:
            meta["notes"] = ""
        document["meta"] = meta
    data = document.get("data")
    if isinstance(data, dict):
        rec = data.get("recommendation")
        if isinstance(rec, dict):
            rec["type"] = "advisory"
            rec["scope"] = "Season-Planner"
            data["recommendation"] = rec
        document["data"] = data
    return document


def _normalize_document(spec: Any, document: JsonMap, loaded_inputs: dict[str, object]) -> JsonMap:
    """Apply the same deterministic normalization rules as the legacy runner."""

    normalized = normalize_season_scenarios_document(
        document,
        planning_events_document=extract_planning_events_document(
            loaded_inputs.get("planning_events")
        ),
    )
    normalized = _fill_season_plan(normalized)
    normalized = normalize_phase_guardrails_document(normalized)
    if spec.artifact_type == ArtifactType.WEEK_PLAN:
        normalized = _normalize_week_plan_meta(normalized)
        normalized = normalize_week_plan_consistency(normalized)
    if spec.artifact_type == ArtifactType.DES_ANALYSIS_REPORT:
        normalized = _normalize_des_analysis_report(normalized)
    return normalized


def _build_crewai_tooling(
    athlete_id: str,
    workspace_root: Any,
) -> tuple[list[Any], dict[str, object]]:
    """Create CrewAI tools backed by the existing workspace read handlers."""

    crewai_tools = import_module("crewai.tools")
    tool_decorator = getattr(crewai_tools, "tool")

    ctx = ReadToolContext(athlete_id=athlete_id, workspace_root=workspace_root)
    handlers = read_tool_handlers(ctx)
    tool_defs = read_tool_defs()
    loaded_inputs: dict[str, object] = {}
    tools: list[Any] = []

    def _capture_loaded_input(tool_name: str, args: JsonMap, result: object) -> None:
        if tool_name != "workspace_get_input":
            return
        if not isinstance(result, dict) or result.get("ok") is not True:
            return
        key = args.get("input_type") or args.get("input_name")
        if isinstance(key, str):
            loaded_inputs[key] = result

    for tool_def in tool_defs:
        name = tool_def.get("name")
        description = tool_def.get("description")
        if not isinstance(name, str) or not isinstance(description, str):
            continue
        handler = handlers.get(name)
        if handler is None:
            continue

        def _factory(
            tool_name: str = str(name),
            tool_description: str = str(description),
            tool_handler: Callable[[dict[str, Any]], object] | None = handler,
        ) -> Any:
            def _run(payload_json: str = "{}") -> str:
                """Execute the wrapped legacy workspace tool."""

                try:
                    args = json.loads(payload_json) if payload_json else {}
                except json.JSONDecodeError as exc:
                    return json.dumps({"ok": False, "error": f"Invalid payload_json: {exc}"})
                if not isinstance(args, dict):
                    return json.dumps({"ok": False, "error": "payload_json must decode to an object"})
                if tool_handler is None:
                    return json.dumps({"ok": False, "error": f"Tool handler missing for {tool_name}"})
                try:
                    result = tool_handler(args)
                except Exception as exc:  # pragma: no cover - backend parity with legacy handler exceptions
                    result = {"ok": False, "error": str(exc)}
                _capture_loaded_input(tool_name, args, result)
                return json.dumps(result, ensure_ascii=False)

            _run.__name__ = f"{tool_name}_tool"
            _run.__doc__ = (
                f"{tool_description} "
                "Pass arguments as a JSON string in the single `payload_json` parameter."
            )
            return tool_decorator(tool_name)(_run)

        tools.append(_factory())

    return tools, loaded_inputs


def _build_task_description(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    task: AgentTask,
    user_input: str,
) -> str:
    """Compose the final CrewAI task description from prompts, injections, and user input."""

    prompt = runtime.prompt_loader.combined_system_prompt(agent_name)
    mode = injection_mode_for_tasks([task])
    injected_block = build_injection_block(agent_name, mode=mode)
    spec = OUTPUT_SPECS[task]
    mandatory_doc_name = _mandatory_output_doc_for_schema(spec.schema_file)
    mandatory_doc = (
        load_shared_knowledge_source("specs", mandatory_doc_name)
        if mandatory_doc_name
        else None
    )
    parts = [
        "System and agent instructions:",
        prompt,
    ]
    if injected_block and injected_block not in prompt:
        parts.extend(["", "Injected runtime context:", injected_block])
    if mandatory_doc:
        parts.extend(
            [
                "",
                f"Mandatory JSON output rules for {spec.artifact_type.value}:",
                mandatory_doc,
            ]
        )
    parts.extend(
        [
            "",
            "Tool contract:",
            "- All available tools accept a single string parameter named `payload_json`.",
            "- `payload_json` must be a JSON object string matching the legacy tool arguments.",
            "",
            "User request:",
            user_input,
            "",
            "Return only the final full artifact envelope with top-level `meta` and `data`.",
        ]
    )
    return "\n".join(parts)


def run_agent_multi_output_crewai(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    agent_vs_name: str,
    athlete_id: str,
    tasks: list[AgentTask],
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
    include_debug_file_search: bool = False,
    force_file_search: bool = True,
    max_num_results: int | None = None,
    stream_handlers: dict[str, object] | None = None,
) -> JsonMap:
    """Execute a single persisted task through CrewAI and persist the typed result."""

    del agent_vs_name, include_debug_file_search, force_file_search, max_num_results, stream_handlers

    if len(tasks) != 1:
        return {
            "ok": False,
            "error": "CrewAI backend currently supports exactly one task per run.",
            "produced": {},
        }

    task = tasks[0]
    output_spec = OUTPUT_SPECS[task]
    blueprint_name = _TASK_BLUEPRINT_BY_AGENT_TASK.get(task)
    if blueprint_name is None:
        return {
            "ok": False,
            "error": f"No CrewAI task blueprint mapping for {task.value}.",
            "produced": {},
        }

    crewai = import_module("crewai")
    Agent = getattr(crewai, "Agent")
    Task = getattr(crewai, "Task")
    Crew = getattr(crewai, "Crew")
    Process = getattr(crewai, "Process")
    LLM = getattr(crewai, "LLM")

    bundle = load_crewai_config_bundle(root=ROOT)
    agent_blueprints = build_agent_blueprints(bundle)
    task_blueprints = build_task_blueprints(bundle)
    task_blueprint = task_blueprints[blueprint_name]
    agent_blueprint = agent_blueprints[task_blueprint.agent]

    llm = LLM(
        **build_crewai_llm_kwargs(
            agent_name,
            model_override=model_override or runtime.model,
            temperature_override=(
                temperature_override if temperature_override is not None else runtime.temperature
            ),
            reasoning_effort_override=runtime.reasoning_effort,
            reasoning_summary_override=runtime.reasoning_summary,
            max_completion_tokens_override=runtime.max_completion_tokens,
        )
    )

    tools, loaded_inputs = _build_crewai_tooling(athlete_id, runtime.workspace_root)
    agent = Agent(
        role=agent_blueprint.role,
        goal=agent_blueprint.goal,
        backstory=agent_blueprint.backstory,
        llm=llm,
        tools=tools,
        allow_delegation=False,
        verbose=bool(agent_blueprint.config.get("verbose", False)),
    )
    crew_task = Task(
        description=_build_task_description(
            runtime,
            agent_name=agent_name,
            task=task,
            user_input=user_input,
        ),
        expected_output=task_blueprint.expected_output,
        agent=agent,
        output_pydantic=output_model_for_kind(task_blueprint.output_kind),
    )
    crew = Crew(
        agents=[agent],
        tasks=[crew_task],
        process=Process.sequential,
        verbose=bool(task_blueprint.config.get("verbose", False)),
    )
    result = crew.kickoff()

    task_output = getattr(crew_task, "output", None)
    pydantic_output = getattr(task_output, "pydantic", None) if task_output is not None else None
    if pydantic_output is None:
        pydantic_output = getattr(result, "pydantic", None)
    if pydantic_output is None and hasattr(result, "model_dump"):
        pydantic_output = result
    if pydantic_output is None:
        raw = getattr(task_output, "raw", None)
        return {
            "ok": False,
            "error": "CrewAI task did not produce a typed pydantic output.",
            "final_text": raw,
            "produced": {},
        }

    document = pydantic_output.model_dump() if hasattr(pydantic_output, "model_dump") else pydantic_output
    if not isinstance(document, dict):
        return {
            "ok": False,
            "error": "CrewAI typed output did not decode to an artifact envelope object.",
            "produced": {},
        }

    document = _normalize_document(output_spec, document, loaded_inputs)

    guarded = GuardedValidatedStore(
        athlete_id=athlete_id,
        schema_dir=runtime.schema_dir,
        workspace_root=runtime.workspace_root,
    )
    try:
        saved = guarded.guard_put_validated(
            output_spec=output_spec,
            document=document,
            run_id=run_id,
            producer_agent=agent_name,
            update_latest=True,
        )
    except SchemaValidationError as exc:
        return {
            "ok": False,
            "error": "Schema validation failed",
            "details": list(exc.errors or []),
            "produced": {},
        }
    except Exception as exc:
        logger.warning("CrewAI store failed for %s: %s", output_spec.artifact_type.value, exc)
        return {"ok": False, "error": str(exc), "produced": {}}

    return {"ok": True, "produced": {output_spec.tool_name: saved}}
