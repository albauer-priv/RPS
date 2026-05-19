"""CrewAI execution backend for planner and advisory artefact tasks."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import Any

from rps.agents.output_normalization import (
    extract_planning_events_document,
    normalize_phase_guardrails_document,
    normalize_season_scenarios_document,
    normalize_workout_percent_ranges,
)
from rps.agents.tasks import OUTPUT_SPECS, AgentTask
from rps.crewai_runtime.bindings import (
    build_agent_blueprints,
    build_task_blueprints,
    collect_native_agent_kwargs,
    collect_native_crew_kwargs,
    output_model_for_kind,
)
from rps.crewai_runtime.config import CrewAIConfigBundle, load_crewai_config_bundle
from rps.crewai_runtime.generated_artifact_models import (
    artifact_model_for_schema_file,
    artifact_model_for_task_name,
)
from rps.crewai_runtime.guardrails import (
    build_task_guardrail_kwargs,
    current_guardrail_runtime_context,
    guardrail_runtime_context,
)
from rps.crewai_runtime.knowledge import (
    build_crewai_knowledge_kwargs,
    resolve_agent_knowledge_profile,
)
from rps.crewai_runtime.memory import (
    build_agent_memory_value,
    build_crew_memory_kwargs,
    resolve_agent_memory_profile,
    resolve_crew_memory_profile,
)
from rps.crewai_runtime.provider import (
    build_crewai_llm_kwargs,
    build_crewai_planning_llm_kwargs,
    resolve_crewai_planning_enabled,
)
from rps.crewai_runtime.skills import (
    build_crewai_skill_kwargs,
    resolve_agent_skill_profile,
)
from rps.crewai_runtime.telemetry import (
    build_step_callback,
    build_task_callback,
    emit_runtime_event,
    emit_runtime_exception_event,
    register_runtime_label,
    runtime_event_scope,
)
from rps.tools.workspace_read_tools import ReadToolContext, read_tool_defs, read_tool_handlers
from rps.workouts.week_plan_consistency import normalize_week_plan_consistency
from rps.workspace.artifact_metadata import CANONICAL_OWNER_BY_ARTIFACT
from rps.workspace.guarded_store import GuardedValidatedStore
from rps.workspace.schema_registry import SchemaValidationError
from rps.workspace.types import ArtifactType

from .runtime import AgentRuntime

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[3]

JsonMap = dict[str, Any]
ToolMap = dict[str, Any]

_TASK_BLUEPRINT_BY_AGENT_TASK = {
    AgentTask.CREATE_SEASON_SCENARIOS: "season_scenarios",
    AgentTask.CREATE_SEASON_SCENARIO_SELECTION: "season_scenario_selection",
    AgentTask.CREATE_SEASON_PLAN: "season_plan",
    AgentTask.CREATE_SEASON_PHASE_FEED_FORWARD: "season_phase_feed_forward",
    AgentTask.CREATE_PHASE_GUARDRAILS: "phase_guardrails",
    AgentTask.CREATE_PHASE_STRUCTURE: "phase_structure",
    AgentTask.CREATE_PHASE_PREVIEW: "phase_preview",
    AgentTask.CREATE_PHASE_FEED_FORWARD: "phase_feed_forward",
    AgentTask.CREATE_WEEK_PLAN: "week_plan",
    AgentTask.CREATE_DES_ANALYSIS_REPORT: "des_analysis_report",
}

_SEASON_PLANNING_TASKS: tuple[str, ...] = (
    "season_context_read",
    "season_scenario_interpretation",
    "season_event_priority_review",
    "season_peak_window_review",
    "season_macrocycle_draft",
    "season_constraint_review",
    "season_historical_context_review",
    "season_kpi_guidance_review",
    "season_load_corridor_draft",
    "season_progression_review",
    "season_plan_finalize",
)

_SEASON_REVIEW_TASKS: tuple[str, ...] = (
    "season_governance_review",
    "season_constraints_review",
    "season_plan_audit",
    "season_contract_review",
    "season_review",
)

_PHASE_PLANNING_TASKS: tuple[str, ...] = (
    "phase_context_read",
    "phase_guardrail_band_draft",
    "phase_execution_rules_draft",
    "phase_structure_draft",
    "phase_cadence_recovery_draft",
    "phase_intensity_distribution_draft",
    "phase_event_integration_draft",
    "phase_preview_draft",
    "phase_bundle_finalize",
)

_PHASE_REVIEW_TASKS: tuple[str, ...] = (
    "phase_constraint_audit",
    "phase_governance_review",
    "phase_structure_review",
    "phase_preview_review",
    "phase_contract_review",
    "phase_review",
)

_WEEK_PLANNING_TASKS: tuple[str, ...] = (
    "week_context_read",
    "week_constraint_review",
    "week_load_target_draft",
    "week_revision_draft",
    "week_workout_text_draft",
    "week_plan_finalize",
)

_WEEK_REVIEW_TASKS: tuple[str, ...] = (
    "week_consistency_review",
    "week_load_governance_review",
    "week_workout_syntax_review",
    "week_contract_review",
    "week_review",
)


def _resolve_agent_runtime_profile(bundle: CrewAIConfigBundle, agent_name: str) -> JsonMap:
    """Return the runtime-model/reasoning profile for one agent."""

    profiles = bundle.runtime_profiles.get("agents") or {}
    profile = profiles.get(agent_name) or {}
    if not isinstance(profile, dict):
        return {}
    return profile


def _resolve_crew_runtime_profile(bundle: CrewAIConfigBundle, crew_name: str) -> JsonMap:
    """Return the runtime planning profile for one crew."""

    profiles = bundle.runtime_profiles.get("crews") or {}
    profile = profiles.get(crew_name) or {}
    if not isinstance(profile, dict):
        return {}
    return profile


def _build_crewai_crew_kwargs(
    *,
    runtime: AgentRuntime,
    bundle: CrewAIConfigBundle,
    crew_name: str,
    athlete_id: str | None,
    run_id: str | None,
    persisted_artifact_flow: bool = True,
) -> JsonMap:
    """Return CrewAI-native kwargs and callbacks for one crew execution."""

    crew_profile = _resolve_crew_runtime_profile(bundle, crew_name)
    kwargs = collect_native_crew_kwargs(
        crew_profile,
        persisted_artifact_flow=persisted_artifact_flow,
    )
    root = runtime.workspace_root if athlete_id and run_id else None
    kwargs["task_callback"] = build_task_callback(
        root=root,
        athlete_id=athlete_id,
        run_id=run_id,
        crew_name=crew_name,
    )
    step_cfg = crew_profile.get("step_callback")
    step_enabled = bool(step_cfg.get("enabled", False)) if isinstance(step_cfg, dict) else False
    step_callback = build_step_callback(
        root=root,
        athlete_id=athlete_id,
        run_id=run_id,
        crew_name=crew_name,
        enabled=step_enabled,
    )
    if step_callback is not None:
        kwargs["step_callback"] = step_callback
    return kwargs


def _build_task_callback_kwargs(
    *,
    runtime: AgentRuntime,
    crew_name: str,
    task_name: str,
    athlete_id: str | None,
    run_id: str | None,
) -> JsonMap:
    """Return CrewAI Task callback kwargs for compact task-level telemetry."""

    root = runtime.workspace_root if athlete_id and run_id else None
    return {
        "callback": build_task_callback(
            root=root,
            athlete_id=athlete_id,
            run_id=run_id,
            crew_name=crew_name,
            task_name=task_name,
            event_type="CREW_TASK_CALLBACK_COMPLETED",
        )
    }


def _emit_crew_task_prepared_events(
    *,
    runtime: AgentRuntime,
    crew_name: str,
    tasks: list[tuple[str, str]],
    athlete_id: str | None,
    run_id: str | None,
    component: str,
) -> None:
    """Emit one compact log/event row per task before CrewAI kickoff begins."""

    if not athlete_id or not run_id:
        return
    for index, (task_name, agent_name) in enumerate(tasks, start=1):
        emit_runtime_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            event_type="CREW_TASK_PREPARED",
            crew=crew_name,
            task=task_name,
            agent=agent_name,
            status=f"{index}/{len(tasks)}",
            component=component,
        )


def _tool_map_from_runtime_tools(tools: list[Any] | ToolMap) -> ToolMap:
    """Normalize runtime tools to a lookup by CrewAI tool name."""

    if isinstance(tools, dict):
        return tools
    result: ToolMap = {}
    for tool_obj in tools:
        for attr in ("name", "tool_name", "__name__"):
            value = getattr(tool_obj, attr, None)
            if isinstance(value, str) and value:
                result[value] = tool_obj
                break
    return result


def _tool_names_for_task(task_blueprint: Any, tools_by_name: ToolMap) -> tuple[str, ...]:
    """Resolve the CrewAI task-level tool names from task config."""

    configured = (getattr(task_blueprint, "config", {}) or {}).get("tools")
    if configured is None:
        return ()
    if configured == "read_only_workspace":
        return tuple(tools_by_name)
    if configured in (False, "none"):
        return ()
    if isinstance(configured, str):
        return (configured,)
    if isinstance(configured, list | tuple):
        return tuple(str(item) for item in configured if str(item).strip())
    raise ValueError(f"Task '{task_blueprint.name}' tools must be a string or list of tool names.")


def _task_tools_for_blueprint(task_blueprint: Any, tools: list[Any] | ToolMap) -> list[Any]:
    """Return the task-scoped CrewAI tools configured for a task blueprint."""

    tools_by_name = _tool_map_from_runtime_tools(tools)
    names = _tool_names_for_task(task_blueprint, tools_by_name)
    missing = [name for name in names if name not in tools_by_name]
    if missing:
        raise ValueError(
            f"Task '{task_blueprint.name}' references unknown tools: {', '.join(missing)}"
        )
    return [tools_by_name[name] for name in names]


def _build_crewai_planning_llm(
    crewai_llm_cls: Any,
    *,
    bundle: CrewAIConfigBundle,
    crew_name: str,
) -> object | None:
    """Instantiate the dedicated crew-planning LLM when configured."""

    crew_profile = _resolve_crew_runtime_profile(bundle, crew_name)
    planning_profile = crew_profile.get("planning") or {}
    if not isinstance(planning_profile, dict):
        return None
    enabled = resolve_crewai_planning_enabled(
        crew_name,
        default_enabled=bool(planning_profile.get("enabled", False)),
    )
    if not enabled:
        return None
    kwargs = build_crewai_planning_llm_kwargs(
        crew_name,
        default_model=planning_profile.get("model") if isinstance(planning_profile.get("model"), str) else None,
    )
    if not kwargs:
        return None
    return crewai_llm_cls(**kwargs)

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


def _normalize_artifact_meta(document: JsonMap, artifact_type: ArtifactType) -> JsonMap:
    """Apply canonical meta ownership for persisted artifact envelopes."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta")
    if not isinstance(meta, dict):
        return document
    meta.setdefault("authority", "Binding")
    owner = CANONICAL_OWNER_BY_ARTIFACT.get(artifact_type)
    if owner:
        meta["owner_agent"] = owner
    document["meta"] = meta
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
    meta["owner_agent"] = "Week-Artifact-Writer"
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
        meta["owner_agent"] = CANONICAL_OWNER_BY_ARTIFACT[ArtifactType.DES_ANALYSIS_REPORT]
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


def _render_json_block(label: str, payload: object) -> str:
    """Render structured intermediate results as compact JSON context."""

    if hasattr(payload, "model_dump"):
        payload = payload.model_dump()
    try:
        rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    except TypeError:
        rendered = json.dumps(str(payload), ensure_ascii=False)
    return f"{label}:\n```json\n{rendered}\n```"


def _augment_user_input(user_input: str, *context_blocks: str) -> str:
    """Append structured runtime context blocks to the base user request."""

    blocks = [block.strip() for block in context_blocks if isinstance(block, str) and block.strip()]
    if not blocks:
        return user_input
    return "\n\n".join([user_input, "Additional runtime context:", *blocks])


def _contract_context_blocks_for_task(*, crew_name: str, task_name: str) -> list[str]:
    """Return structured deterministic contract blocks relevant to one CrewAI task."""

    context = current_guardrail_runtime_context()
    blocks: list[str] = []
    if crew_name == "season_planning":
        phase_slot_context = context.get("phase_slot_context")
        if phase_slot_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Season Phase Slot Contract",
                    phase_slot_context,
                )
            )
        season_phase_load_context = context.get("season_phase_load_context")
        if season_phase_load_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Season Phase Load Contract",
                    season_phase_load_context,
                )
            )
        if task_name == "season_plan_finalize" and blocks:
            blocks.append(
                "Season finalization rule: consume these deterministic contracts directly. "
                "Do not search the workspace for non-persisted phase-load recommendation artifacts."
            )
    elif crew_name == "phase_planning":
        phase_execution_context = context.get("phase_execution_context")
        if phase_execution_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Phase Execution Contract",
                    phase_execution_context,
                )
            )
        phase_slot_context = context.get("phase_slot_context")
        if phase_slot_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Season Phase Slot Contract",
                    phase_slot_context,
                )
            )
        if task_name == "phase_bundle_finalize" and blocks:
            blocks.append(
                "Phase finalization rule: consume these deterministic contracts directly. "
                "Do not delegate or rediscover week roles, S5 bands, or phase-range authority from prose."
            )
    elif crew_name == "week_planning":
        week_calendar_context = context.get("week_calendar_context")
        if week_calendar_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Week Calendar Contract",
                    week_calendar_context,
                )
            )
        phase_execution_context = context.get("phase_execution_context")
        if phase_execution_context:
            blocks.append(
                _render_json_block(
                    "Deterministic Phase Execution Contract",
                    phase_execution_context,
                )
            )
        if task_name == "week_plan_finalize" and blocks:
            blocks.append(
                "Week finalization rule: consume these deterministic contracts directly. "
                "Do not delegate or rediscover active week role, active weekly band, availability caps, or fixed rest rules from prose."
            )
    return blocks


def _resolve_prompt_agent_name(agent_name: str, blueprint: Any) -> str:
    """Resolve which top-level prompt should back a CrewAI specialist agent."""

    config = getattr(blueprint, "config", {}) or {}
    prompt_agent = config.get("prompt_agent")
    if isinstance(prompt_agent, str) and prompt_agent:
        return prompt_agent
    return agent_name


def _build_crewai_llm(
    crewai_llm_cls: Any,
    runtime: AgentRuntime,
    *,
    agent_name: str,
    model_override: str | None,
    temperature_override: float | None,
    reasoning_effort_override: str | None = None,
    reasoning_summary_override: str | None = None,
    max_completion_tokens_override: int | None = None,
) -> object:
    """Instantiate the CrewAI LLM wrapper for the given agent."""

    return crewai_llm_cls(
        **build_crewai_llm_kwargs(
            agent_name,
            model_override=model_override or runtime.model,
            temperature_override=(
                temperature_override if temperature_override is not None else runtime.temperature
            ),
            reasoning_effort_override=(
                reasoning_effort_override
                if reasoning_effort_override is not None
                else runtime.reasoning_effort
            ),
            reasoning_summary_override=(
                reasoning_summary_override
                if reasoning_summary_override is not None
                else runtime.reasoning_summary
            ),
            max_completion_tokens_override=(
                max_completion_tokens_override
                if max_completion_tokens_override is not None
                else runtime.max_completion_tokens
            ),
        )
    )


def _build_crewai_agent(
    agent_cls: Any,
    *,
    crewai_llm_cls: Any,
    runtime: AgentRuntime,
    bundle: Any,
    blueprint: Any,
    tools: list[Any],
    athlete_id: str,
    crew_name: str,
    surface: str = "default",
    shared_memory: Any | None = None,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> object:
    """Instantiate one CrewAI agent from a blueprint."""

    config = getattr(blueprint, "config", {}) or {}
    runtime_profile = _resolve_agent_runtime_profile(bundle, blueprint.name)
    reasoning_profile = runtime_profile.get("reasoning") or {}
    llm = _build_crewai_llm(
        crewai_llm_cls,
        runtime,
        agent_name=blueprint.name,
        model_override=runtime_profile.get("model") or model_override,
        temperature_override=temperature_override,
        reasoning_effort_override=runtime_profile.get("reasoning_effort"),
        reasoning_summary_override=runtime_profile.get("reasoning_summary"),
        max_completion_tokens_override=runtime_profile.get("max_completion_tokens"),
    )
    kwargs: dict[str, Any] = {
        "role": blueprint.role,
        "goal": blueprint.goal,
        "backstory": blueprint.backstory,
        "llm": llm,
        "tools": tools,
        "verbose": bool(config.get("verbose", False)),
    }
    kwargs.update(collect_native_agent_kwargs(blueprint.name, config))
    if bool(reasoning_profile.get("enabled", False)):
        kwargs["reasoning"] = True
        max_attempts = reasoning_profile.get("max_attempts")
        if isinstance(max_attempts, int) and max_attempts > 0:
            kwargs["max_reasoning_attempts"] = max_attempts
    knowledge_kwargs = build_crewai_knowledge_kwargs(
        root=ROOT,
        profile=resolve_agent_knowledge_profile(bundle, agent_name=blueprint.name),
    )
    kwargs.update(knowledge_kwargs)
    skill_profile = resolve_agent_skill_profile(bundle, agent_name=blueprint.name, crew_name=crew_name)
    kwargs.update(build_crewai_skill_kwargs(root=ROOT, profile=skill_profile))
    agent_memory = build_agent_memory_value(
        shared_memory=shared_memory,
        profile=resolve_agent_memory_profile(
            bundle,
            agent_name=blueprint.name,
            athlete_id=athlete_id,
            surface=surface,
        ),
    )
    if agent_memory is not None:
        kwargs["memory"] = agent_memory
    for field in ("system_template", "prompt_template", "response_template"):
        value = config.get(field)
        if isinstance(value, str) and value:
            kwargs[field] = value
    agent = agent_cls(**kwargs)
    register_runtime_label(agent, kind="agent", label=blueprint.name)
    return agent




def _extract_raw_output_text(result: object, task_obj: object) -> str | None:
    """Return raw text output from a CrewAI task result when available."""

    task_output = getattr(task_obj, "output", None)
    for candidate in (
        getattr(task_output, "raw", None),
        getattr(result, "raw", None),
        result if isinstance(result, str) else None,
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _parse_json_document(raw_text: str) -> JsonMap:
    """Parse a JSON object from raw task output, tolerating fenced JSON blocks."""

    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise RuntimeError("CrewAI task output did not decode to an artifact envelope object.")
    return parsed


def _coerce_artifact_envelope(candidate: object) -> JsonMap | None:
    """Extract a `{meta, data}` envelope from direct or wrapped CrewAI results."""

    if hasattr(candidate, "model_dump"):
        try:
            candidate = candidate.model_dump()
        except Exception:
            return None

    if isinstance(candidate, dict):
        if isinstance(candidate.get("meta"), dict) and "data" in candidate:
            return candidate

        nested_json = candidate.get("json_dict")
        if nested_json is not None:
            coerced = _coerce_artifact_envelope(nested_json)
            if coerced is not None:
                return coerced

        nested_pydantic = candidate.get("pydantic")
        if nested_pydantic is not None:
            coerced = _coerce_artifact_envelope(nested_pydantic)
            if coerced is not None:
                return coerced

        raw = candidate.get("raw")
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = _parse_json_document(raw)
            except Exception:
                parsed = None
            if parsed is not None and isinstance(parsed.get("meta"), dict) and "data" in parsed:
                return parsed

        task_outputs = candidate.get("tasks_output")
        if isinstance(task_outputs, list):
            for item in task_outputs:
                coerced = _coerce_artifact_envelope(item)
                if coerced is not None:
                    return coerced
    return None


def _extract_typed_output(result: object, task_obj: object) -> Any:
    """Extract the typed Pydantic output from a CrewAI task result."""

    task_output = getattr(task_obj, "output", None)
    pydantic_output = getattr(task_output, "pydantic", None) if task_output is not None else None
    if pydantic_output is None:
        pydantic_output = getattr(result, "pydantic", None)
    if pydantic_output is None and hasattr(result, "model_dump"):
        pydantic_output = result
    return pydantic_output


def _extract_json_output(result: object, task_obj: object) -> JsonMap | None:
    """Extract JSON task output from a CrewAI task result when configured via output_json."""

    task_output = getattr(task_obj, "output", None)
    for candidate in (
        getattr(task_output, "json_dict", None),
        getattr(result, "json_dict", None),
    ):
        if isinstance(candidate, dict):
            return candidate
    return None


def _output_model_for_task(task_blueprint: Any, *, schema_file: str | None = None) -> type[Any]:
    """Resolve the strongest structured-output model for a CrewAI task."""

    if task_blueprint.output_kind == "artifact_envelope":
        if schema_file:
            return artifact_model_for_schema_file(schema_file)
        return artifact_model_for_task_name(task_blueprint.name)
    return output_model_for_kind(task_blueprint.output_kind)


def _execute_crewai_task(
    *,
    agent_cls: Any,
    crewai_llm_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    runtime: AgentRuntime,
    bundle: Any,
    agent_blueprint: Any,
    task_blueprint: Any,
    tools: list[Any] | ToolMap,
    description: str,
    crew_name: str,
    athlete_id: str | None = None,
    run_id: str | None = None,
    model_override: str | None = None,
    temperature_override: float | None = None,
    artifact_schema_file: str | None = None,
) -> Any:
    """Execute one CrewAI task and return its typed output."""

    crew_memory_kwargs = build_crew_memory_kwargs(
        import_module("crewai"),
        profile=resolve_crew_memory_profile(
            bundle,
            crew_name=crew_name,
            athlete_id=athlete_id or "unknown",
            surface="default",
        ),
    )
    shared_memory = crew_memory_kwargs.get("memory")
    agent = _build_crewai_agent(
        agent_cls,
        crewai_llm_cls=crewai_llm_cls,
        runtime=runtime,
        bundle=bundle,
        blueprint=agent_blueprint,
        tools=[],
        athlete_id=athlete_id or "unknown",
        crew_name=crew_name,
        shared_memory=shared_memory,
        model_override=model_override,
        temperature_override=temperature_override,
    )
    crew_task_kwargs: dict[str, Any] = {
        "name": task_blueprint.name,
        "description": description,
        "expected_output": task_blueprint.expected_output,
        "agent": agent,
    }
    crew_task_kwargs.update(
        _build_task_callback_kwargs(
            runtime=runtime,
            crew_name=crew_name,
            task_name=task_blueprint.name,
            athlete_id=athlete_id,
            run_id=run_id,
        )
    )
    guardrail_kwargs = build_task_guardrail_kwargs(task_blueprint, bundle.task_policies)
    output_mode = str(guardrail_kwargs.pop("_resolved_output_mode", "pydantic"))
    output_model = _output_model_for_task(task_blueprint, schema_file=artifact_schema_file)
    if output_mode == "json":
        crew_task_kwargs["output_json"] = output_model
    elif output_mode == "pydantic":
        crew_task_kwargs["output_pydantic"] = output_model
    crew_task_kwargs.update(guardrail_kwargs)
    task_tools = _task_tools_for_blueprint(task_blueprint, tools)
    if task_tools:
        crew_task_kwargs["tools"] = task_tools
    crew_task = task_cls(**crew_task_kwargs)
    register_runtime_label(crew_task, kind="task", label=task_blueprint.name)
    process = getattr(process_cls, "sequential")
    planning_llm = _build_crewai_planning_llm(crewai_llm_cls, bundle=bundle, crew_name=crew_name)
    crew_kwargs: dict[str, Any] = {
        "agents": [agent],
        "tasks": [crew_task],
        "process": process,
        "verbose": bool(task_blueprint.config.get("verbose", False)),
    }
    crew_kwargs.update(
        _build_crewai_crew_kwargs(
            runtime=runtime,
            bundle=bundle,
            crew_name=crew_name,
            athlete_id=athlete_id,
            run_id=run_id,
            persisted_artifact_flow=task_blueprint.output_kind == "artifact_envelope",
        )
    )
    if planning_llm is not None:
        crew_kwargs["planning"] = True
        crew_kwargs["planning_llm"] = planning_llm
    crew_kwargs.update(crew_memory_kwargs)
    crew = crew_cls(**crew_kwargs)
    register_runtime_label(crew, kind="crew", label=crew_name)
    _emit_crew_task_prepared_events(
        runtime=runtime,
        crew_name=crew_name,
        tasks=[(task_blueprint.name, agent_blueprint.role)],
        athlete_id=athlete_id,
        run_id=run_id,
        component=f"crew:{task_blueprint.name}",
    )
    if athlete_id and run_id:
        with runtime_event_scope(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            component=f"crew:{task_blueprint.name}",
        ), guardrail_runtime_context(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            component=f"crew:{task_blueprint.name}",
        ):
            result = crew.kickoff()
    else:
        result = crew.kickoff()
    if task_blueprint.output_kind == "artifact_envelope":
        json_output = _coerce_artifact_envelope(_extract_json_output(result, crew_task))
        if json_output is not None:
            return json_output
        pydantic_output = _coerce_artifact_envelope(_extract_typed_output(result, crew_task))
        if pydantic_output is not None:
            return pydantic_output
        wrapped_output = _coerce_artifact_envelope(result)
        if wrapped_output is not None:
            return wrapped_output
        raw = _extract_raw_output_text(result, crew_task)
        if not raw:
            raise RuntimeError(f"CrewAI task '{task_blueprint.name}' produced no raw artifact output.")
        return _parse_json_document(raw)
    pydantic_output = _extract_typed_output(result, crew_task)
    if pydantic_output is None:
        raw = _extract_raw_output_text(result, crew_task)
        raise RuntimeError(
            f"CrewAI task '{task_blueprint.name}' did not produce a typed pydantic output."
            + (f" Raw output: {raw}" if raw else "")
        )
    return pydantic_output


def _build_crewai_task(
    *,
    task_cls: Any,
    bundle: Any,
    task_blueprint: Any,
    agent: object,
    description: str,
    runtime: AgentRuntime,
    crew_name: str,
    athlete_id: str | None = None,
    run_id: str | None = None,
    tools: list[Any] | ToolMap | None = None,
    context_tasks: list[object] | None = None,
) -> object:
    """Instantiate one CrewAI task object with optional explicit context."""

    kwargs: dict[str, Any] = {
        "name": task_blueprint.name,
        "description": description,
        "expected_output": task_blueprint.expected_output,
        "agent": agent,
    }
    kwargs.update(
        _build_task_callback_kwargs(
            runtime=runtime,
            crew_name=crew_name,
            task_name=task_blueprint.name,
            athlete_id=athlete_id,
            run_id=run_id,
        )
    )
    guardrail_kwargs = build_task_guardrail_kwargs(task_blueprint, bundle.task_policies)
    output_mode = str(guardrail_kwargs.pop("_resolved_output_mode", "pydantic"))
    output_model = _output_model_for_task(task_blueprint)
    if output_mode == "json":
        kwargs["output_json"] = output_model
    elif output_mode == "pydantic":
        kwargs["output_pydantic"] = output_model
    kwargs.update(guardrail_kwargs)
    task_tools = _task_tools_for_blueprint(task_blueprint, tools or {})
    if task_tools:
        kwargs["tools"] = task_tools
    if context_tasks:
        kwargs["context"] = context_tasks
    task = task_cls(**kwargs)
    register_runtime_label(task, kind="task", label=task_blueprint.name)
    return task


def _execute_crewai_hierarchical_crew(
    *,
    agent_cls: Any,
    crewai_llm_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    runtime: AgentRuntime,
    bundle: Any,
    manager_agent_name: str,
    crew_name: str,
    crew_task_names: tuple[str, ...],
    final_task_name: str,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    tools: list[Any] | ToolMap,
    user_input: str,
    final_public_task: AgentTask | None = None,
    athlete_id: str | None = None,
    run_id: str | None = None,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> Any:
    """Execute one real multi-agent hierarchical crew and return the final typed output."""

    crew_memory_kwargs = build_crew_memory_kwargs(
        import_module("crewai"),
        profile=resolve_crew_memory_profile(
            bundle,
            crew_name=crew_name,
            athlete_id=athlete_id or "unknown",
            surface="default",
        ),
    )
    shared_memory = crew_memory_kwargs.get("memory")
    agents_by_name: dict[str, object] = {}
    for task_name in crew_task_names:
        task_blueprint = task_blueprints[task_name]
        agent_name = task_blueprint.agent
        if agent_name in agents_by_name:
            continue
        agent_blueprint = agent_blueprints[agent_name]
        agents_by_name[agent_name] = _build_crewai_agent(
            agent_cls,
            crewai_llm_cls=crewai_llm_cls,
            runtime=runtime,
            bundle=bundle,
            blueprint=agent_blueprint,
            tools=[],
            athlete_id=athlete_id or "unknown",
            crew_name=crew_name,
            shared_memory=shared_memory,
            model_override=model_override,
            temperature_override=temperature_override,
        )

    if manager_agent_name not in agents_by_name:
        manager_blueprint = agent_blueprints[manager_agent_name]
        agents_by_name[manager_agent_name] = _build_crewai_agent(
            agent_cls,
            crewai_llm_cls=crewai_llm_cls,
            runtime=runtime,
            bundle=bundle,
            blueprint=manager_blueprint,
            tools=[],
            athlete_id=athlete_id or "unknown",
            crew_name=crew_name,
            shared_memory=shared_memory,
            model_override=model_override,
            temperature_override=temperature_override,
        )

    manager_agent = agents_by_name[manager_agent_name]
    manager_llm = getattr(manager_agent, "llm", None)
    crew_tasks: list[object] = []
    prior_tasks: list[object] = []
    tasks_by_name: dict[str, object] = {}
    final_task_obj: object | None = None
    for task_name in crew_task_names:
        task_blueprint = task_blueprints[task_name]
        agent_name = task_blueprint.agent
        prompt_agent = _resolve_prompt_agent_name(agent_name, agent_blueprints[agent_name])
        if task_name == final_task_name and final_public_task is not None:
            contract_blocks = _contract_context_blocks_for_task(
                crew_name=crew_name,
                task_name=task_name,
            )
            description = _build_task_description(
                runtime,
                bundle=bundle,
                crew_name=crew_name,
                agent_name=manager_agent_name,
                task=final_public_task,
                user_input=_augment_user_input(user_input, *contract_blocks),
            )
            if prior_tasks:
                description = "\n".join(
                    [
                        description,
                        "",
                        "Use the prior specialist and audit task outputs as context for the final manager decision.",
                    ]
                )
        else:
            contract_blocks = _contract_context_blocks_for_task(
                crew_name=crew_name,
                task_name=task_name,
            )
            description = _build_internal_task_description(
                runtime,
                agent_name=agent_name,
                prompt_agent=prompt_agent,
                bundle=bundle,
                crew_name=crew_name,
                task_blueprint=task_blueprint,
                user_input=_augment_user_input(user_input, *contract_blocks),
            )
        context_tasks: list[object] | None
        if getattr(task_blueprint, "context_names", ()):
            missing = [item for item in task_blueprint.context_names if item not in tasks_by_name]
            if missing:
                raise ValueError(
                    f"Task '{task_name}' references unknown or later context tasks: {', '.join(missing)}"
                )
            context_tasks = [tasks_by_name[item] for item in task_blueprint.context_names]
        else:
            context_tasks = prior_tasks[:] if prior_tasks else None
        crew_task = _build_crewai_task(
            task_cls=task_cls,
            bundle=bundle,
            task_blueprint=task_blueprint,
            agent=agents_by_name[agent_name],
            description=description,
            runtime=runtime,
            crew_name=crew_name,
            athlete_id=athlete_id,
            run_id=run_id,
            tools=tools,
            context_tasks=context_tasks,
        )
        crew_tasks.append(crew_task)
        prior_tasks.append(crew_task)
        tasks_by_name[task_name] = crew_task
        if task_name == final_task_name:
            final_task_obj = crew_task

    if final_task_obj is None:
        raise RuntimeError(f"Final crew task '{final_task_name}' was not created.")

    hierarchical = getattr(process_cls, "hierarchical", None)
    process = hierarchical or getattr(process_cls, "sequential")
    crew_kwargs: dict[str, Any] = {
        "agents": [agent for name, agent in agents_by_name.items() if name != manager_agent_name],
        "tasks": crew_tasks,
        "process": process,
        "verbose": False,
    }
    crew_kwargs.update(
        _build_crewai_crew_kwargs(
            runtime=runtime,
            bundle=bundle,
            crew_name=crew_name,
            athlete_id=athlete_id,
            run_id=run_id,
            persisted_artifact_flow=True,
        )
    )
    if crew_memory_kwargs:
        crew_kwargs.update(crew_memory_kwargs)
    if hierarchical is not None:
        crew_kwargs["manager_agent"] = manager_agent
        if manager_llm is not None:
            crew_kwargs["manager_llm"] = manager_llm
    planning_llm = _build_crewai_planning_llm(crewai_llm_cls, bundle=bundle, crew_name=crew_name)
    if planning_llm is not None:
        crew_kwargs["planning"] = True
        crew_kwargs["planning_llm"] = planning_llm
    crew = crew_cls(**crew_kwargs)
    register_runtime_label(crew, kind="crew", label=crew_name)
    _emit_crew_task_prepared_events(
        runtime=runtime,
        crew_name=crew_name,
        tasks=[
            (
                task_name,
                agent_blueprints[task_blueprints[task_name].agent].role,
            )
            for task_name in crew_task_names
        ],
        athlete_id=athlete_id,
        run_id=run_id,
        component=f"crew:{final_task_name}",
    )
    if athlete_id and run_id:
        with runtime_event_scope(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            component=f"crew:{final_task_name}",
        ), guardrail_runtime_context(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            component=f"crew:{final_task_name}",
        ):
            result = crew.kickoff()
    else:
        result = crew.kickoff()
    final_output_kind = str(task_blueprints[final_task_name].output_kind)
    if final_output_kind == "artifact_envelope":
        json_output = _coerce_artifact_envelope(_extract_json_output(result, final_task_obj))
        if json_output is not None:
            return json_output
        pydantic_output = _coerce_artifact_envelope(_extract_typed_output(result, final_task_obj))
        if pydantic_output is not None:
            return pydantic_output
        wrapped_output = _coerce_artifact_envelope(result)
        if wrapped_output is not None:
            return wrapped_output
        raw = _extract_raw_output_text(result, final_task_obj)
        if not raw:
            raise RuntimeError(f"CrewAI crew final task '{final_task_name}' produced no raw artifact output.")
        return _parse_json_document(raw)
    pydantic_output = _extract_typed_output(result, final_task_obj)
    if pydantic_output is None:
        raw = _extract_raw_output_text(result, final_task_obj)
        raise RuntimeError(
            f"CrewAI crew final task '{final_task_name}' did not produce a typed pydantic output."
            + (f" Raw output: {raw}" if raw else "")
        )
    return pydantic_output


def _build_internal_task_description(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    prompt_agent: str,
    bundle: Any,
    crew_name: str,
    task_blueprint: Any,
    user_input: str,
    context_blocks: list[str] | None = None,
) -> str:
    """Build a specialist-task description with top-level prompt context."""

    prompt = runtime.prompt_loader.combined_system_prompt(prompt_agent)
    parts = [
        "System and agent instructions:",
        prompt,
    ]
    parts.extend(
        [
            "",
            f"Internal specialist task: {task_blueprint.description}",
            "",
            "User request:",
            user_input,
        ]
    )
    if context_blocks:
        parts.extend(["", "Internal context from prior specialist tasks:"])
        parts.extend(context_blocks)
    parts.extend(
        [
            "",
            "Return only the typed output required for this specialist task.",
        ]
    )
    return "\n".join(parts)


def _phase_document_from_bundle(bundle_document: JsonMap, artifact_type: ArtifactType) -> JsonMap:
    """Select the correct nested phase artifact document from a PhaseBundle."""

    if artifact_type == ArtifactType.PHASE_GUARDRAILS:
        candidate = bundle_document.get("guardrails_document") or bundle_document.get("guardrails")
    elif artifact_type == ArtifactType.PHASE_STRUCTURE:
        candidate = bundle_document.get("structure_document") or bundle_document.get("structure")
    elif artifact_type == ArtifactType.PHASE_PREVIEW:
        candidate = bundle_document.get("preview_document") or bundle_document.get("preview")
    else:
        raise ValueError(f"Unsupported PhaseBundle split target: {artifact_type.value}")
    if not isinstance(candidate, dict):
        raise RuntimeError(f"PhaseBundle missing nested document for {artifact_type.value}.")
    return candidate


def _run_season_plan_document(
    *,
    runtime: AgentRuntime,
    bundle: Any,
    user_input: str,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    agent_cls: Any,
    crewai_llm_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    tools: list[Any] | ToolMap,
    athlete_id: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> JsonMap:
    """Execute the hierarchical season planning crew and return the internal bundle."""
    pydantic_output = _execute_crewai_hierarchical_crew(
        agent_cls=agent_cls,
        crewai_llm_cls=crewai_llm_cls,
        crew_cls=crew_cls,
        task_cls=task_cls,
        process_cls=process_cls,
        runtime=runtime,
        bundle=bundle,
        manager_agent_name="season_plan_manager",
        crew_name="season_planning",
        crew_task_names=_SEASON_PLANNING_TASKS,
        final_task_name="season_plan_finalize",
        task_blueprints=task_blueprints,
        agent_blueprints=agent_blueprints,
        tools=tools,
        user_input=user_input,
        final_public_task=None,
        athlete_id=athlete_id,
        run_id=run_id,
        model_override=model_override,
        temperature_override=temperature_override,
    )
    document = pydantic_output.model_dump() if hasattr(pydantic_output, "model_dump") else pydantic_output
    if not isinstance(document, dict):
        raise RuntimeError("Season manager output did not decode to an artifact envelope object.")
    return document


def _run_phase_bundle_document(
    *,
    runtime: AgentRuntime,
    bundle: Any,
    user_input: str,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    agent_cls: Any,
    crewai_llm_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    tools: list[Any] | ToolMap,
    athlete_id: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> JsonMap:
    """Execute the hierarchical phase planning crew and return the internal PhaseBundle."""
    final_task_name = _PHASE_PLANNING_TASKS[-1]
    pydantic_output = _execute_crewai_hierarchical_crew(
        agent_cls=agent_cls,
        crewai_llm_cls=crewai_llm_cls,
        crew_cls=crew_cls,
        task_cls=task_cls,
        process_cls=process_cls,
        runtime=runtime,
        bundle=bundle,
        manager_agent_name=task_blueprints[final_task_name].agent,
        crew_name="phase_planning",
        crew_task_names=_PHASE_PLANNING_TASKS,
        final_task_name=final_task_name,
        task_blueprints=task_blueprints,
        agent_blueprints=agent_blueprints,
        tools=tools,
        user_input=user_input,
        final_public_task=None,
        athlete_id=athlete_id,
        run_id=run_id,
        model_override=model_override,
        temperature_override=temperature_override,
    )
    bundle_document = (
        pydantic_output.model_dump() if hasattr(pydantic_output, "model_dump") else pydantic_output
    )
    if not isinstance(bundle_document, dict):
        raise RuntimeError("Phase bundle output did not decode to an object.")
    return bundle_document


def _run_review_decision_document(
    *,
    runtime: AgentRuntime,
    bundle: Any,
    review_task_names: tuple[str, ...],
    final_task_name: str,
    manager_agent_name: str,
    crew_name: str,
    user_input: str,
    planning_bundle: JsonMap,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    agent_cls: Any,
    crewai_llm_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    tools: list[Any] | ToolMap,
    athlete_id: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> JsonMap:
    """Execute a review crew against a planning bundle and return its decision."""

    review_input = _augment_user_input(
        user_input,
        _render_json_block("Planning bundle", planning_bundle),
    )
    pydantic_output = _execute_crewai_hierarchical_crew(
        agent_cls=agent_cls,
        crewai_llm_cls=crewai_llm_cls,
        crew_cls=crew_cls,
        task_cls=task_cls,
        process_cls=process_cls,
        runtime=runtime,
        bundle=bundle,
        manager_agent_name=manager_agent_name,
        crew_name=crew_name,
        crew_task_names=review_task_names,
        final_task_name=final_task_name,
        task_blueprints=task_blueprints,
        agent_blueprints=agent_blueprints,
        tools=tools,
        user_input=review_input,
        final_public_task=None,
        athlete_id=athlete_id,
        run_id=run_id,
        model_override=model_override,
        temperature_override=temperature_override,
    )
    decision = pydantic_output.model_dump() if hasattr(pydantic_output, "model_dump") else pydantic_output
    if not isinstance(decision, dict):
        raise RuntimeError(f"Review crew '{crew_name}' did not return an object.")
    return decision


def _run_single_internal_document(
    *,
    runtime: AgentRuntime,
    bundle: Any,
    crew_name: str,
    task_name: str,
    user_input: str,
    context_payloads: list[tuple[str, object]] | None,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    agent_cls: Any,
    crewai_llm_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    tools: list[Any] | ToolMap,
    athlete_id: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> JsonMap:
    """Execute a single internal typed CrewAI task and return its document payload."""

    task_blueprint = task_blueprints[task_name]
    agent_blueprint = agent_blueprints[task_blueprint.agent]
    context_blocks = [
        _render_json_block(label, payload)
        for label, payload in (context_payloads or [])
        if payload is not None
    ]
    description = _build_internal_task_description(
        runtime,
        agent_name=task_blueprint.agent,
        prompt_agent=_resolve_prompt_agent_name(task_blueprint.agent, agent_blueprint),
        bundle=bundle,
        crew_name=crew_name,
        task_blueprint=task_blueprint,
        user_input=_augment_user_input(user_input, *context_blocks),
    )
    pydantic_output = _execute_crewai_task(
        agent_cls=agent_cls,
        crewai_llm_cls=crewai_llm_cls,
        crew_cls=crew_cls,
        task_cls=task_cls,
        process_cls=process_cls,
        runtime=runtime,
        bundle=bundle,
        agent_blueprint=agent_blueprint,
        task_blueprint=task_blueprint,
        tools=tools,
        description=description,
        crew_name=crew_name,
        athlete_id=athlete_id,
        run_id=run_id,
        model_override=model_override,
        temperature_override=temperature_override,
    )
    document = pydantic_output.model_dump() if hasattr(pydantic_output, "model_dump") else pydantic_output
    if not isinstance(document, dict):
        raise RuntimeError(f"Internal task '{task_name}' did not return an object.")
    return document


def _run_writer_document(
    *,
    runtime: AgentRuntime,
    bundle: Any,
    crew_name: str,
    public_task: AgentTask,
    user_input: str,
    planning_bundle: JsonMap,
    review_decision: JsonMap,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    agent_cls: Any,
    crewai_llm_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    tools: list[Any] | ToolMap,
    athlete_id: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> JsonMap:
    """Execute a writer task from approved bundle + review context and return the final document."""

    blueprint_name = _TASK_BLUEPRINT_BY_AGENT_TASK[public_task]
    task_blueprint = task_blueprints[blueprint_name]
    agent_blueprint = agent_blueprints[task_blueprint.agent]
    description = _build_task_description(
        runtime,
        bundle=bundle,
        crew_name=crew_name,
        agent_name=task_blueprint.agent,
        task=public_task,
        user_input=_augment_user_input(
            user_input,
            _render_json_block("Approved planning bundle", planning_bundle),
            _render_json_block("Review decision", review_decision),
        ),
    )
    document = _execute_crewai_task(
        agent_cls=agent_cls,
        crewai_llm_cls=crewai_llm_cls,
        crew_cls=crew_cls,
        task_cls=task_cls,
        process_cls=process_cls,
        runtime=runtime,
        bundle=bundle,
        agent_blueprint=agent_blueprint,
        task_blueprint=task_blueprint,
        tools=tools,
        description=description,
        crew_name=crew_name,
        athlete_id=athlete_id,
        run_id=run_id,
        model_override=model_override,
        temperature_override=temperature_override,
    )
    if not isinstance(document, dict):
        raise RuntimeError(f"Writer task '{blueprint_name}' did not return an artifact object.")
    return document


def _run_multicrew_cycle(
    *,
    runtime: AgentRuntime,
    bundle: Any,
    user_input: str,
    planning_runner: Callable[[str], JsonMap],
    review_runner: Callable[[str, JsonMap], JsonMap],
    max_replan_rounds: int,
) -> tuple[JsonMap, JsonMap]:
    """Run planning -> review with bounded replans and return the approved pair."""

    attempt = 0
    planning_input = user_input
    latest_decision: JsonMap | None = None
    while True:
        planning_bundle = planning_runner(planning_input)
        latest_decision = review_runner(planning_input, planning_bundle)
        status = str(latest_decision.get("status") or "").lower()
        if status == "approved":
            return planning_bundle, latest_decision
        if status == "rejected":
            raise RuntimeError(
                "; ".join(latest_decision.get("blocking_issues") or [])
                or "Review crew rejected the planning bundle."
            )
        if status != "replan_required":
            raise RuntimeError(f"Unsupported review decision status: {status or '<empty>'}")
        if attempt >= max_replan_rounds:
            raise RuntimeError(
                "Review requested another replan after exhausting the allowed replan rounds."
            )
        attempt += 1
        planning_input = _augment_user_input(
            user_input,
            _render_json_block("Replan instructions", latest_decision),
        )


def _persist_artifact_document(
    *,
    runtime: AgentRuntime,
    athlete_id: str,
    run_id: str,
    output_spec: Any,
    document: JsonMap,
    producer_agent: str,
) -> JsonMap:
    """Validate and persist one final artifact envelope."""

    guarded = GuardedValidatedStore(
        athlete_id=athlete_id,
        schema_dir=runtime.schema_dir,
        workspace_root=runtime.workspace_root,
    )
    saved = guarded.guard_put_validated(
        output_spec=output_spec,
        document=document,
        run_id=run_id,
        producer_agent=producer_agent,
        update_latest=True,
    )
    emit_runtime_event(
        root=runtime.workspace_root,
        athlete_id=athlete_id,
        run_id=run_id,
        event_type="ARTEFACT_WRITTEN",
        artifact_type=output_spec.artifact_type.value,
        outputs=[saved],
    )
    return saved


def _normalize_document(spec: Any, document: JsonMap, loaded_inputs: dict[str, object]) -> JsonMap:
    """Apply the same deterministic normalization rules as the legacy runner."""

    normalized = normalize_season_scenarios_document(
        document,
        planning_events_document=extract_planning_events_document(
            loaded_inputs.get("planning_events")
        ),
    )
    normalized = _normalize_artifact_meta(normalized, spec.artifact_type)
    normalized = _fill_season_plan(normalized)
    normalized = normalize_phase_guardrails_document(normalized)
    if spec.artifact_type == ArtifactType.WEEK_PLAN:
        normalized = _normalize_week_plan_meta(normalized)
        normalized = normalize_week_plan_consistency(normalized)
    if spec.artifact_type == ArtifactType.DES_ANALYSIS_REPORT:
        normalized = _normalize_des_analysis_report(normalized)
    return normalized


def run_phase_bundle_crewai(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    athlete_id: str,
    tasks: list[AgentTask],
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> JsonMap:
    """Execute planning -> review -> writer for the requested phase artefacts."""

    allowed_tasks = {
        AgentTask.CREATE_PHASE_GUARDRAILS,
        AgentTask.CREATE_PHASE_STRUCTURE,
        AgentTask.CREATE_PHASE_PREVIEW,
    }
    requested_tasks = [task for task in tasks if task in allowed_tasks]
    if not requested_tasks:
        return {
            "ok": False,
            "error": "Phase bundle execution requires one or more phase artefact tasks.",
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
    tools, loaded_inputs = _build_crewai_tooling(athlete_id, runtime.workspace_root)

    try:
        def _planning_runner(loop_input: str) -> JsonMap:
            return _run_phase_bundle_document(
                runtime=runtime,
                bundle=bundle,
                user_input=loop_input,
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                agent_cls=Agent,
                crewai_llm_cls=LLM,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                tools=tools,
                athlete_id=athlete_id,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
            )

        def _review_runner(loop_input: str, planning_bundle: JsonMap) -> JsonMap:
            return _run_review_decision_document(
                runtime=runtime,
                bundle=bundle,
                review_task_names=_PHASE_REVIEW_TASKS,
                final_task_name="phase_review",
                manager_agent_name="phase_review_manager",
                crew_name="phase_review",
                user_input=loop_input,
                planning_bundle=planning_bundle,
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                agent_cls=Agent,
                crewai_llm_cls=LLM,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                tools=tools,
                athlete_id=athlete_id,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
            )

        planning_bundle, review_decision = _run_multicrew_cycle(
            runtime=runtime,
            bundle=bundle,
            user_input=user_input,
            planning_runner=_planning_runner,
            review_runner=_review_runner,
            max_replan_rounds=2,
        )
    except Exception as exc:
        emit_runtime_exception_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            exc=exc,
            crew="phase_planning",
            task="phase_bundle_cycle",
            agent=agent_name,
            component="crew:phase_bundle_cycle",
        )
        return {"ok": False, "error": str(exc), "produced": {}}

    produced: dict[str, Any] = {}
    warnings = list(planning_bundle.get("warnings") or []) + list(review_decision.get("warnings") or [])
    for task in requested_tasks:
        output_spec = OUTPUT_SPECS[task]
        try:
            document = _run_writer_document(
                runtime=runtime,
                bundle=bundle,
                crew_name="phase_writer",
                public_task=task,
                user_input=user_input,
                planning_bundle=planning_bundle,
                review_decision=review_decision,
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                agent_cls=Agent,
                crewai_llm_cls=LLM,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                tools=tools,
                athlete_id=athlete_id,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
            )
            document = _normalize_document(output_spec, document, loaded_inputs)
            saved = _persist_artifact_document(
                runtime=runtime,
                athlete_id=athlete_id,
                run_id=run_id,
                output_spec=output_spec,
                document=document,
                producer_agent="phase_artifact_writer",
            )
        except SchemaValidationError as exc:
            return {
                "ok": False,
                "error": "Schema validation failed",
                "details": list(exc.errors or []),
                "warnings": warnings,
                "produced": produced,
            }
        except Exception as exc:
            logger.warning("CrewAI phase multi-crew store failed for %s: %s", output_spec.artifact_type.value, exc)
            return {"ok": False, "error": str(exc), "warnings": warnings, "produced": produced}
        produced[output_spec.tool_name] = saved

    return {"ok": True, "produced": produced, "warnings": warnings}


def _build_crewai_tooling(
    athlete_id: str,
    workspace_root: Any,
) -> tuple[ToolMap, dict[str, object]]:
    """Create CrewAI tools backed by the existing workspace read handlers."""

    crewai_tools = import_module("crewai.tools")
    tool_decorator = getattr(crewai_tools, "tool")

    ctx = ReadToolContext(athlete_id=athlete_id, workspace_root=workspace_root)
    handlers = read_tool_handlers(ctx)
    tool_defs = read_tool_defs()
    loaded_inputs: dict[str, object] = {}
    tools: ToolMap = {}

    def _capture_loaded_input(tool_name: str, args: JsonMap, result: object) -> None:
        if tool_name != "workspace_get_input":
            return
        if not isinstance(result, dict) or result.get("ok") is not True:
            return
        key = args.get("input_type") or args.get("artifact_type") or args.get("input_name")
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

        tools[name] = _factory()

    return tools, loaded_inputs


def _build_task_description(
    runtime: AgentRuntime,
    *,
    bundle: Any,
    crew_name: str,
    agent_name: str,
    task: AgentTask,
    user_input: str,
) -> str:
    """Compose the final CrewAI task description from prompts, injections, and user input."""

    prompt = runtime.prompt_loader.combined_system_prompt(agent_name)
    parts = [
        "System and agent instructions:",
        prompt,
    ]
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


def _run_single_task_document_crewai(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    athlete_id: str,
    task: AgentTask,
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> tuple[Any, JsonMap]:
    """Execute one CrewAI task and return its normalized document without storing it."""

    output_spec = OUTPUT_SPECS[task]
    blueprint_name = _TASK_BLUEPRINT_BY_AGENT_TASK.get(task)
    if blueprint_name is None:
        raise ValueError(f"No CrewAI task blueprint mapping for {task.value}.")

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

    tools, loaded_inputs = _build_crewai_tooling(athlete_id, runtime.workspace_root)

    if task == AgentTask.CREATE_SEASON_PLAN:
        def _planning_runner(loop_input: str) -> JsonMap:
            return _run_season_plan_document(
                runtime=runtime,
                bundle=bundle,
                user_input=loop_input,
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                agent_cls=Agent,
                crewai_llm_cls=LLM,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                tools=tools,
                athlete_id=athlete_id,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
            )

        def _review_runner(loop_input: str, planning_bundle: JsonMap) -> JsonMap:
            return _run_review_decision_document(
                runtime=runtime,
                bundle=bundle,
                review_task_names=_SEASON_REVIEW_TASKS,
                final_task_name="season_review",
                manager_agent_name="season_review_manager",
                crew_name="season_review",
                user_input=loop_input,
                planning_bundle=planning_bundle,
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                agent_cls=Agent,
                crewai_llm_cls=LLM,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                tools=tools,
                athlete_id=athlete_id,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
            )

        planning_bundle, review_decision = _run_multicrew_cycle(
            runtime=runtime,
            bundle=bundle,
            user_input=user_input,
            planning_runner=_planning_runner,
            review_runner=_review_runner,
            max_replan_rounds=2,
        )
        document = _run_writer_document(
            runtime=runtime,
            bundle=bundle,
            crew_name="season_writer",
            public_task=task,
            user_input=user_input,
            planning_bundle=planning_bundle,
            review_decision=review_decision,
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=Agent,
            crewai_llm_cls=LLM,
            crew_cls=Crew,
            task_cls=Task,
            process_cls=Process,
            tools=tools,
            athlete_id=athlete_id,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )
    elif task == AgentTask.CREATE_WEEK_PLAN:
        def _planning_runner(loop_input: str) -> JsonMap:
            return _execute_crewai_hierarchical_crew(
            agent_cls=Agent,
            crewai_llm_cls=LLM,
            crew_cls=Crew,
            task_cls=Task,
            process_cls=Process,
            runtime=runtime,
            bundle=bundle,
                manager_agent_name="week_plan_manager",
                crew_name="week_planning",
                crew_task_names=_WEEK_PLANNING_TASKS,
                final_task_name="week_plan_finalize",
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                tools=tools,
                user_input=loop_input,
                final_public_task=None,
                athlete_id=athlete_id,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
            ).model_dump()

        def _review_runner(loop_input: str, planning_bundle: JsonMap) -> JsonMap:
            return _run_review_decision_document(
                runtime=runtime,
                bundle=bundle,
                review_task_names=_WEEK_REVIEW_TASKS,
                final_task_name="week_review",
                manager_agent_name="week_review_manager",
                crew_name="week_review",
                user_input=loop_input,
                planning_bundle=planning_bundle,
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                agent_cls=Agent,
                crewai_llm_cls=LLM,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                tools=tools,
                athlete_id=athlete_id,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
            )

        planning_bundle, review_decision = _run_multicrew_cycle(
            runtime=runtime,
            bundle=bundle,
            user_input=user_input,
            planning_runner=_planning_runner,
            review_runner=_review_runner,
            max_replan_rounds=1,
        )
        document = _run_writer_document(
            runtime=runtime,
            bundle=bundle,
            crew_name="week_writer",
            public_task=task,
            user_input=user_input,
            planning_bundle=planning_bundle,
            review_decision=review_decision,
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=Agent,
            crewai_llm_cls=LLM,
            crew_cls=Crew,
            task_cls=Task,
            process_cls=Process,
            tools=tools,
            athlete_id=athlete_id,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )
    elif task == AgentTask.CREATE_DES_ANALYSIS_REPORT:
        planning_bundle = _run_single_internal_document(
            runtime=runtime,
            bundle=bundle,
            crew_name="report_planning",
            task_name="des_diagnostic_draft",
            user_input=user_input,
            context_payloads=None,
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=Agent,
            crewai_llm_cls=LLM,
            crew_cls=Crew,
            task_cls=Task,
            process_cls=Process,
            tools=tools,
            athlete_id=athlete_id,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )
        review_decision = _run_single_internal_document(
            runtime=runtime,
            bundle=bundle,
            crew_name="report_review",
            task_name="report_review",
            user_input=user_input,
            context_payloads=[("Planning bundle", planning_bundle)],
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=Agent,
            crewai_llm_cls=LLM,
            crew_cls=Crew,
            task_cls=Task,
            process_cls=Process,
            tools=tools,
            athlete_id=athlete_id,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )
        status = str(review_decision.get("status") or "").lower()
        if status != "approved":
            raise RuntimeError(
                "; ".join(review_decision.get("blocking_issues") or [])
                or f"Report review returned status '{status or 'unknown'}'."
            )
        document = _run_writer_document(
            runtime=runtime,
            bundle=bundle,
            crew_name="report_writer",
            public_task=task,
            user_input=user_input,
            planning_bundle=planning_bundle,
            review_decision=review_decision,
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=Agent,
            crewai_llm_cls=LLM,
            crew_cls=Crew,
            task_cls=Task,
            process_cls=Process,
            tools=tools,
            athlete_id=athlete_id,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )
    else:
        description = _build_task_description(
            runtime,
            bundle=bundle,
            crew_name=(
                "week_planning"
                if task == AgentTask.CREATE_WEEK_PLAN
                else "report_advisory"
                if task == AgentTask.CREATE_DES_ANALYSIS_REPORT
                else "season_planning"
            ),
            agent_name=agent_name,
            task=task,
            user_input=user_input,
        )
        pydantic_output = _execute_crewai_task(
            agent_cls=Agent,
            crewai_llm_cls=LLM,
            crew_cls=Crew,
            task_cls=Task,
            process_cls=Process,
            runtime=runtime,
            bundle=bundle,
            agent_blueprint=agent_blueprint,
            task_blueprint=task_blueprint,
            tools=tools,
            description=description,
            crew_name=(
                "week_planning"
                if task == AgentTask.CREATE_WEEK_PLAN
                else "report_advisory"
                if task == AgentTask.CREATE_DES_ANALYSIS_REPORT
                else "season_planning"
            ),
            athlete_id=athlete_id,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )
        document = pydantic_output.model_dump() if hasattr(pydantic_output, "model_dump") else pydantic_output

    if not isinstance(document, dict):
        raise RuntimeError("CrewAI typed output did not decode to an artifact envelope object.")

    return output_spec, _normalize_document(output_spec, document, loaded_inputs)


def run_agent_multi_output_crewai(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    athlete_id: str,
    tasks: list[AgentTask],
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
    stream_handlers: dict[str, object] | None = None,
) -> JsonMap:
    """Execute a single persisted task through CrewAI and persist the typed result."""

    del stream_handlers

    if len(tasks) != 1:
        return {
            "ok": False,
            "error": "CrewAI backend currently supports exactly one task per run.",
            "produced": {},
        }

    task = tasks[0]
    if task in {
        AgentTask.CREATE_PHASE_GUARDRAILS,
        AgentTask.CREATE_PHASE_STRUCTURE,
        AgentTask.CREATE_PHASE_PREVIEW,
    }:
        return run_phase_bundle_crewai(
            runtime,
            agent_name=agent_name,
            athlete_id=athlete_id,
            tasks=[task],
            user_input=user_input,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )

    try:
        output_spec, document = _run_single_task_document_crewai(
            runtime,
            agent_name=agent_name,
            athlete_id=athlete_id,
            task=task,
            user_input=user_input,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )
    except Exception as exc:
        emit_runtime_exception_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            exc=exc,
            crew="single_task",
            task=task.value,
            agent=agent_name,
        )
        return {
            "ok": False,
            "error": str(exc),
            "produced": {},
        }

    try:
        saved = _persist_artifact_document(
            runtime=runtime,
            athlete_id=athlete_id,
            run_id=run_id,
            output_spec=output_spec,
            document=document,
            producer_agent=agent_name,
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


def run_agent_multi_output_preview_crewai(
    runtime: AgentRuntime,
    *,
    agent_name: str,
    athlete_id: str,
    tasks: list[AgentTask],
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
    stream_handlers: dict[str, object] | None = None,
) -> JsonMap:
    """Execute a single CrewAI task and return the normalized document without storing it."""

    del stream_handlers

    if len(tasks) != 1:
        return {
            "ok": False,
            "error": "CrewAI preview backend currently supports exactly one task per run.",
            "document": {},
        }

    task = tasks[0]
    if task in {
        AgentTask.CREATE_PHASE_GUARDRAILS,
        AgentTask.CREATE_PHASE_STRUCTURE,
        AgentTask.CREATE_PHASE_PREVIEW,
    }:
        return {
            "ok": False,
            "error": "Preview-only CrewAI backend does not support phase bundle tasks.",
            "document": {},
        }

    try:
        output_spec, document = _run_single_task_document_crewai(
            runtime,
            agent_name=agent_name,
            athlete_id=athlete_id,
            task=task,
            user_input=user_input,
            run_id=run_id,
            model_override=model_override,
            temperature_override=temperature_override,
        )
    except Exception as exc:
        emit_runtime_exception_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            exc=exc,
            crew="single_task_preview",
            task=task.value,
            agent=agent_name,
        )
        return {"ok": False, "error": str(exc), "document": {}}

    return {
        "ok": True,
        "artifact_type": output_spec.artifact_type.value,
        "document": document,
    }
