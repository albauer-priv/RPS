"""CrewAI agent/crew/LLM construction and tool resolution for planning tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rps.agents.runtime import AgentRuntime
from rps.crewai_runtime.bindings import collect_native_agent_kwargs, collect_native_crew_kwargs
from rps.crewai_runtime.config import CrewAIConfigBundle
from rps.crewai_runtime.knowledge import (
    build_crewai_knowledge_kwargs,
    resolve_agent_knowledge_profile,
)
from rps.crewai_runtime.memory import build_agent_memory_value, resolve_agent_memory_profile
from rps.crewai_runtime.provider import (
    build_crewai_llm_kwargs,
    build_crewai_planning_llm_kwargs,
    resolve_crewai_planning_enabled,
)
from rps.crewai_runtime.skills import build_crewai_skill_kwargs, resolve_agent_skill_profile
from rps.crewai_runtime.telemetry import (
    build_step_callback,
    build_task_callback,
    emit_runtime_event,
    register_runtime_label,
    register_runtime_metadata,
)

ROOT = Path(__file__).resolve().parents[3]

JsonMap = dict[str, Any]
ToolMap = dict[str, Any]


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
    tasks: list[tuple[str, str, str | None]],
    athlete_id: str | None,
    run_id: str | None,
    component: str,
) -> None:
    """Emit one compact log/event row per task before CrewAI kickoff begins."""

    if not athlete_id or not run_id:
        return
    for index, (task_name, agent_name, model_name) in enumerate(tasks, start=1):
        emit_runtime_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            event_type="CREW_TASK_PREPARED",
            crew=crew_name,
            task=task_name,
            agent=agent_name,
            model=model_name,
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


def _resolve_prompt_agent_name(agent_name: str, blueprint: Any) -> str:
    """Resolve which top-level prompt should back a CrewAI specialist agent."""

    config = getattr(blueprint, "config", {}) or {}
    prompt_agent = config.get("prompt_agent")
    if isinstance(prompt_agent, str) and prompt_agent:
        return prompt_agent
    return agent_name


def _review_subject_metadata(crew_name: str) -> tuple[str, str, str]:
    """Return review-subject labels for season/phase/week review crews."""

    if crew_name == "season_review":
        return (
            "Candidate Season Bundle",
            "candidate season bundle",
            "candidate_season_bundle",
        )
    if crew_name == "phase_review":
        return (
            "Candidate Phase Bundle",
            "candidate phase bundle",
            "candidate_phase_bundle",
        )
    if crew_name == "week_review":
        return (
            "Candidate Week Bundle",
            "candidate week bundle",
            "candidate_week_bundle",
        )
    return ("Candidate Planning Bundle", "candidate planning bundle", "candidate_planning_bundle")


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


def _llm_model_label(llm: object | None) -> str | None:
    """Return the configured model name from a CrewAI LLM wrapper when available."""

    if llm is None:
        return None
    for value in (
        getattr(llm, "model", None),
        getattr(llm, "model_name", None),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    llm_kwargs = getattr(llm, "kwargs", None)
    if isinstance(llm_kwargs, dict):
        model = llm_kwargs.get("model")
        if isinstance(model, str) and model.strip():
            return model.strip()
    return None


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
    register_runtime_metadata(agent, model=_llm_model_label(llm))
    register_runtime_metadata(llm, model=_llm_model_label(llm))
    return agent
