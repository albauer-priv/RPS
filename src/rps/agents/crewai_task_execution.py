"""CrewAI execution backend for planner and advisory artefact tasks."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import Any

from rps.agents.crewai_builders import (
    _build_crewai_agent,
    _build_crewai_crew_kwargs,
    _build_crewai_planning_llm,
    _build_task_callback_kwargs,
    _emit_crew_task_prepared_events,
    _llm_model_label,
    _resolve_prompt_agent_name,
    _review_subject_metadata,
    _task_tools_for_blueprint,
    _tool_map_from_runtime_tools,
)
from rps.agents.crewai_bundle_normalization import (
    _fill_season_plan,
    _normalize_final_season_plan_semantics,
    normalize_phase_draft_bundle,
    normalize_season_plan_draft_bundle,
)
from rps.agents.crewai_context_blocks import (
    _contract_context_blocks_for_task,
    _phase_bundle_finalize_has_bound_contracts,
    _phase_writer_authority_context_block,
)
from rps.agents.crewai_output_extraction import (
    _coerce_artifact_envelope,
    _extract_json_output,
    _extract_raw_output_text,
    _extract_structured_output,
    _extract_typed_output,
    _freeze_season_bundle_audit_slots,
    _output_model_for_task,
    _parse_json_document,
    coerce_season_plan_draft_bundle_slots,
)
from rps.agents.crewai_validation import (
    _normalize_artifact_meta,
    _normalize_des_analysis_report,
    _normalize_week_plan_meta,
    _validate_normalized_phase_bundle,
    _validate_normalized_season_bundle,
    _validate_normalized_week_bundle,
)
from rps.agents.output_normalization import (
    extract_loaded_document,
    extract_planning_events_document,
    normalize_phase_guardrails_document,
    normalize_season_scenarios_document,
)
from rps.agents.tasks import OUTPUT_SPECS, AgentTask
from rps.crewai_runtime.bindings import (
    build_agent_blueprints,
    build_task_blueprints,
    should_bind_crewai_output_model,
)
from rps.crewai_runtime.config import load_crewai_config_bundle
from rps.crewai_runtime.guardrails import (
    build_task_guardrail_kwargs,
    week_bundle_domain_legality_messages,
)
from rps.crewai_runtime.guardrails_context import (
    current_guardrail_runtime_context,
    guardrail_runtime_context,
)
from rps.crewai_runtime.memory import (
    build_crew_memory_kwargs,
    resolve_crew_memory_profile,
)
from rps.crewai_runtime.models import SeasonPlanDraftBundleModel
from rps.crewai_runtime.telemetry import (
    emit_runtime_event,
    emit_runtime_exception_event,
    register_runtime_label,
    register_runtime_metadata,
    runtime_event_scope,
)
from rps.planning.week_engine import (
    execute_week_engine,
    extract_message_from_user_input,
    parse_target_week_from_user_input,
)
from rps.tools.workspace_read_tools import ReadToolContext, read_tool_defs, read_tool_handlers
from rps.workouts.generator import build_week_plan_document_from_bundle
from rps.workouts.week_plan_consistency import normalize_week_plan_consistency
from rps.workspace.guarded_store import GuardedValidatedStore
from rps.workspace.schema_registry import SchemaValidationError
from rps.workspace.types import ArtifactType

from .runtime import AgentRuntime

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[3]

_INTERNAL_PROMPT_CHAR_LIMIT = 2800
_INTERNAL_PROMPT_WORD_LIMIT = 450
_INTERNAL_PROMPT_SEGMENT_CHAR_LIMIT = 420
_INTERNAL_PROMPT_PRIORITY_MARKERS: tuple[str, ...] = (
    "Current Task:",
    "Current Step",
    "Context from previous steps:",
    "Athlete State Snapshot",
    "Use the latest",
    "Target ISO week:",
    "Internal specialist task:",
    "User request:",
)

_AUTHORITATIVE_RUNTIME_BLOCK_PREFIXES: tuple[str, ...] = (
    "**Athlete State Snapshot**",
    "**Planning Context Snapshot**",
    "**Current Week Status Snapshot**",
    "**Advisory Memory**",
    "**Resolved ",
    "**Deterministic ",
)

_INTERNAL_TOOL_FIRST_RULES = """Shared binding rules for this internal planning step:
- Use prior specialist context and the provided workspace tools before claiming any input is missing.
- An input is missing only after the relevant workspace tool fails, returns not found, or prior specialist context truly does not contain it.
- If a required input is tool-loadable, do not ask the user to paste or re-provide it.
- If the task has workspace tools, use them first and keep the number of retrieval attempts tight and relevant.
- If still blocked, return one compact blocked result only once. Include: missing_inputs, attempted_tools, and reason.
- No repeated paragraphs. No duplicate missing-input lists. No generic apology text.
"""

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
    "season_constraint_review",
    "season_historical_context_review",
    "season_evidence_alignment",
    "season_macrocycle_draft",
    "season_kpi_guidance_review",
    "season_load_corridor_draft",
    "season_progression_review",
    "season_phase_blueprint_draft",
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
    "phase_evidence_alignment",
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
    "week_evidence_alignment",
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


def _sanitize_replan_decision_context(decision: JsonMap) -> JsonMap:
    """Return only the active replan delta that should survive into the next round."""

    return {
        "status": str(decision.get("status") or "").lower(),
        "replan_instructions": list(decision.get("replan_instructions") or []),
        "writer_ready_summary": str(decision.get("writer_ready_summary") or "").strip(),
    }


def _compact_internal_user_input(user_input: str) -> str:
    """Reduce oversized specialist-task input while preserving the most relevant markers."""

    text = " ".join(str(user_input).split()).strip()
    if not text:
        return ""
    if len(text) <= _INTERNAL_PROMPT_CHAR_LIMIT and len(text.split()) <= _INTERNAL_PROMPT_WORD_LIMIT:
        return text

    chosen_segments: list[str] = []
    lower_text = text.lower()
    for marker in _INTERNAL_PROMPT_PRIORITY_MARKERS:
        lower_marker = marker.lower()
        index = lower_text.find(lower_marker)
        if index < 0:
            continue
        next_index = len(text)
        for candidate in _INTERNAL_PROMPT_PRIORITY_MARKERS:
            if candidate == marker:
                continue
            candidate_index = lower_text.find(candidate.lower(), index + len(lower_marker))
            if candidate_index >= 0:
                next_index = min(next_index, candidate_index)
        segment = text[index:next_index].strip(" -")
        if len(segment) > _INTERNAL_PROMPT_SEGMENT_CHAR_LIMIT:
            segment = segment[:_INTERNAL_PROMPT_SEGMENT_CHAR_LIMIT].rstrip()
        if segment and segment not in chosen_segments:
            chosen_segments.append(segment)

    if not chosen_segments:
        chosen_segments.append(text)

    compacted = " ".join(chosen_segments)
    words = compacted.split()
    if len(words) > _INTERNAL_PROMPT_WORD_LIMIT:
        compacted = " ".join(words[:_INTERNAL_PROMPT_WORD_LIMIT]).strip()
    if len(compacted) > _INTERNAL_PROMPT_CHAR_LIMIT:
        compacted = compacted[: _INTERNAL_PROMPT_CHAR_LIMIT].rstrip()
    return compacted


def _extract_authoritative_runtime_blocks(user_input: str) -> list[str]:
    """Preserve authoritative markdown context blocks that specialists must see in full."""

    if not isinstance(user_input, str) or not user_input.strip():
        return []

    blocks: list[str] = []
    current: list[str] = []
    current_title: str | None = None

    def _flush() -> None:
        nonlocal current, current_title
        if current_title and current:
            block = "\n".join(line.rstrip() for line in current).strip()
            if block and block not in blocks:
                blocks.append(block)
        current = []
        current_title = None

    for raw_line in user_input.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in _AUTHORITATIVE_RUNTIME_BLOCK_PREFIXES):
            _flush()
            current_title = stripped
            current = [line]
            continue
        if current_title is not None:
            if stripped.startswith("**") and stripped.endswith("**"):
                _flush()
                continue
            current.append(line)
    _flush()
    return blocks


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
    if output_mode == "json" and should_bind_crewai_output_model(task_blueprint, output_mode=output_mode):
        crew_task_kwargs["output_json"] = output_model
    elif output_mode == "pydantic" and should_bind_crewai_output_model(task_blueprint, output_mode=output_mode):
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
        tasks=[(task_blueprint.name, task_blueprint.agent, _llm_model_label(getattr(agent, "llm", None)))],
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
            task_name=task_blueprint.name,
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
    return _extract_structured_output(
        result,
        crew_task,
        task_name=task_blueprint.name,
        output_mode=output_mode,
    )


def execute_structured_internal_task_crewai(
    runtime: AgentRuntime,
    *,
    crew_name: str,
    task_name: str,
    description: str,
    athlete_id: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> Any:
    """Execute one configured internal CrewAI task and return its typed output."""

    crewai = import_module("crewai")
    Agent = getattr(crewai, "Agent")
    Task = getattr(crewai, "Task")
    Crew = getattr(crewai, "Crew")
    Process = getattr(crewai, "Process")
    LLM = getattr(crewai, "LLM")

    bundle = load_crewai_config_bundle(root=ROOT)
    agent_blueprints = build_agent_blueprints(bundle)
    task_blueprints = build_task_blueprints(bundle)
    task_blueprint = task_blueprints[task_name]
    agent_blueprint = agent_blueprints[task_blueprint.agent]

    return _execute_crewai_task(
        agent_cls=Agent,
        crewai_llm_cls=LLM,
        crew_cls=Crew,
        task_cls=Task,
        process_cls=Process,
        runtime=runtime,
        bundle=bundle,
        agent_blueprint=agent_blueprint,
        task_blueprint=task_blueprint,
        tools=[],
        description=description,
        crew_name=crew_name,
        athlete_id=athlete_id,
        run_id=run_id,
        model_override=model_override,
        temperature_override=temperature_override,
    )


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
    tools_override: list[Any] | ToolMap | None = None,
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
    if output_mode == "json" and should_bind_crewai_output_model(task_blueprint, output_mode=output_mode):
        kwargs["output_json"] = output_model
    elif output_mode == "pydantic" and should_bind_crewai_output_model(task_blueprint, output_mode=output_mode):
        kwargs["output_pydantic"] = output_model
    kwargs.update(guardrail_kwargs)
    if tools_override is not None and len(_tool_map_from_runtime_tools(tools_override)) == 0:
        task_tools: list[Any] = []
    else:
        task_tools = _task_tools_for_blueprint(
            task_blueprint,
            tools_override if tools_override is not None else (tools or {}),
        )
    if task_tools:
        kwargs["tools"] = task_tools
    if context_tasks:
        kwargs["context"] = context_tasks
    task = task_cls(**kwargs)
    register_runtime_label(task, kind="task", label=task_blueprint.name)
    register_runtime_metadata(
        task,
        assigned_agent=str(task_blueprint.agent),
        assigned_model=_llm_model_label(getattr(agent, "llm", None)),
    )
    return task


def _execute_crewai_multiagent_crew(
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
    tools_override_by_task: dict[str, list[Any] | ToolMap] | None = None,
    user_input: str,
    final_public_task: AgentTask | None = None,
    athlete_id: str | None = None,
    run_id: str | None = None,
    model_override: str | None = None,
    temperature_override: float | None = None,
    execution_mode: str = "hierarchical",
) -> Any:
    """Execute one multi-agent crew and return the final typed output."""

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
            tools_override=(tools_override_by_task or {}).get(task_name),
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
    sequential = getattr(process_cls, "sequential")
    use_hierarchical = execution_mode == "hierarchical" and hierarchical is not None
    process = hierarchical if use_hierarchical else sequential
    crew_kwargs: dict[str, Any] = {
        "agents": (
            [agent for name, agent in agents_by_name.items() if name != manager_agent_name]
            if use_hierarchical
            else list(agents_by_name.values())
        ),
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
    if use_hierarchical:
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
                task_blueprints[task_name].agent,
                _llm_model_label(getattr(agents_by_name[task_blueprints[task_name].agent], "llm", None)),
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
            task_name=final_task_name,
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
    policy = build_task_guardrail_kwargs(task_blueprints[final_task_name], bundle.task_policies)
    output_mode = str(policy.get("_resolved_output_mode", "pydantic"))
    structured_output = _extract_structured_output(
        result,
        final_task_obj,
        task_name=final_task_name,
        output_mode=output_mode,
    )
    if final_task_name == "season_plan_finalize":
        structured_output = _freeze_season_bundle_audit_slots(
            structured_output,
            result=result,
            tasks_by_name=tasks_by_name,
            task_blueprints=task_blueprints,
        )
    return structured_output


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

    prompt = runtime.prompt_loader.agent_prompt(prompt_agent)
    compact_user_input = _compact_internal_user_input(user_input)
    authoritative_runtime_blocks = _extract_authoritative_runtime_blocks(user_input)
    parts = [
        "Agent instructions:",
        prompt,
        "",
        _INTERNAL_TOOL_FIRST_RULES.strip(),
        "",
        "Tool contract:",
        "- All available workspace tools accept exactly one string parameter named `payload_json`.",
        "- `payload_json` must be a JSON object string that matches the tool's expected arguments.",
        "- If a needed input is available through `workspace_get_input`, `workspace_get_latest`, or `workspace_get_version`, call the tool instead of asking the user for it.",
    ]
    parts.extend(
        [
            "",
            f"Internal specialist task: {task_blueprint.description}",
            "",
            "User request:",
            compact_user_input,
        ]
    )
    if authoritative_runtime_blocks:
        parts.extend(["", "Authoritative runtime context:"])
        parts.extend(authoritative_runtime_blocks)
    if context_blocks:
        parts.extend(["", "Internal context from prior specialist tasks:"])
        parts.extend(context_blocks)
    parts.extend(
        [
            "",
            "This is an internal reasoning task. Do not create, write, or verify workspace files unless the active task explicitly exposes a write-capable tool and requires persisted artefact creation.",
            "If prior specialist context already contains the needed facts, use it directly and do not ask for original workspace artefacts again.",
            "If you are blocked after relevant tool attempts, return one compact blocked result only once.",
            "",
            "Return only the typed output required for this specialist task.",
        ]
    )
    return "\n".join(parts)


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
    final_output = _execute_crewai_multiagent_crew(
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
        execution_mode="sequential",
    )
    document = final_output.model_dump() if hasattr(final_output, "model_dump") else final_output
    if not isinstance(document, dict):
        raise RuntimeError("Season manager output did not decode to an artifact envelope object.")
    try:
        coerced = coerce_season_plan_draft_bundle_slots(document)
        return SeasonPlanDraftBundleModel.model_validate(coerced).model_dump()
    except Exception as exc:
        emit_runtime_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            event_type="SEASON_BUNDLE_RAW_VALIDATION_FAILED",
            crew="season_planning",
            task="season_plan_finalize",
            component="crew:season_plan_finalize",
            reason=str(exc),
        )
        raise RuntimeError(f"season_plan_finalize raw bundle failure: {exc}") from exc


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
    tools_override_by_task: dict[str, list[Any] | ToolMap] | None = None
    if _phase_bundle_finalize_has_bound_contracts():
        tools_override_by_task = {final_task_name: []}
    pydantic_output = _execute_crewai_multiagent_crew(
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
        tools_override_by_task=tools_override_by_task,
        user_input=user_input,
        final_public_task=None,
        athlete_id=athlete_id,
        run_id=run_id,
        model_override=model_override,
        temperature_override=temperature_override,
        execution_mode="sequential",
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

    review_context = current_guardrail_runtime_context()
    week_calendar_context = review_context.get("week_calendar_context")
    legality_issues = week_bundle_domain_legality_messages(
        planning_bundle,
        week_calendar_context=week_calendar_context if isinstance(week_calendar_context, dict) else None,
    )
    if legality_issues:
        return {
            "status": "replan_required",
            "blocking_issues": legality_issues,
            "warnings": [
                "Candidate week bundle violates binding phase workout-domain legality and must be corrected before review approval."
            ],
            "replan_instructions": [
                {
                    "target_specialists": ["Week Planner", "Workout Authoring"],
                    "issues_to_fix": legality_issues,
                    "must_preserve": [
                        "Preserve fixed rest days and active week structure.",
                        "Preserve allowed phase intensity domains only.",
                        "Represent recovery-like low-load work as legal low-end ENDURANCE when RECOVERY is forbidden.",
                    ],
                    "priority_order": [
                        "Replace illegal workout families/domains first.",
                        "Then realign workout text to the corrected canonical family/domain.",
                        "Then recheck export-safe syntax and load coherence.",
                    ],
                    "max_scope_of_change": (
                        "Adjust workout domain/family assignments, dependent workout text, and only the minimum day-role intent needed to remove illegal domains."
                    ),
                }
            ],
            "writer_ready_summary": "",
        }

    candidate_block_title, candidate_bundle_label, candidate_artifact_name = _review_subject_metadata(crew_name)
    review_input = _augment_user_input(
        user_input,
        _render_json_block(candidate_block_title, planning_bundle),
        (
            f"Review subject rule: treat the injected {candidate_block_title} as the authoritative {candidate_bundle_label} under review. "
            f"Do not call workspace tools to reload a synthetic `{candidate_artifact_name}` artefact."
        ),
    )
    pydantic_output = _execute_crewai_multiagent_crew(
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
        execution_mode="sequential",
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
    loaded_inputs: dict[str, object] | None = None,
    model_override: str | None = None,
    temperature_override: float | None = None,
) -> JsonMap:
    """Execute a writer task from approved bundle + review context and return the final document."""

    if public_task == AgentTask.CREATE_WEEK_PLAN:
        week_calendar_result = {}
        if isinstance(loaded_inputs, dict):
            maybe_result = loaded_inputs.get("workspace_get_week_calendar_context")
            if isinstance(maybe_result, dict):
                week_calendar_result = dict(maybe_result.get("contract") or {})
        return build_week_plan_document_from_bundle(
            planning_bundle=planning_bundle,
            week_calendar_context=week_calendar_result,
            review_decision=review_decision,
        )

    blueprint_name = _TASK_BLUEPRINT_BY_AGENT_TASK[public_task]
    task_blueprint = task_blueprints[blueprint_name]
    agent_blueprint = agent_blueprints[task_blueprint.agent]
    exact_authority_block = _phase_writer_authority_context_block(public_task, loaded_inputs)
    description = _build_task_description(
        runtime,
        bundle=bundle,
        crew_name=crew_name,
        agent_name=task_blueprint.agent,
        task=public_task,
        user_input=_augment_user_input(
            user_input,
            exact_authority_block,
            _render_json_block("Approved planning bundle", planning_bundle),
            _render_json_block("Review decision", review_decision),
        ),
    )
    with guardrail_runtime_context(
        approved_planning_bundle=planning_bundle,
        artifact_type=OUTPUT_SPECS[public_task].artifact_type.value,
        loaded_inputs=loaded_inputs or {},
    ):
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
        replan_context = _sanitize_replan_decision_context(latest_decision)
        planning_input = _augment_user_input(
            user_input,
            _render_json_block("Active replan instructions", replan_context),
            (
                "Replan handoff rule: treat the injected Active replan instructions as the only active delta from the previous review. "
                "Do not copy prior blocking issues or warnings forward unless they still apply after the new draft."
            ),
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
    normalized = _normalize_final_season_plan_semantics(normalized)
    normalized = normalize_phase_guardrails_document(
        normalized,
        season_plan_document=extract_loaded_document(loaded_inputs.get("season_plan")),
        season_scenario_selection_document=extract_loaded_document(loaded_inputs.get("season_scenario_selection")),
        season_scenarios_document=extract_loaded_document(loaded_inputs.get("season_scenarios")),
    )
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
            planning_bundle = _run_phase_bundle_document(
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
            try:
                normalized = normalize_phase_draft_bundle(planning_bundle)
            except Exception as exc:
                emit_runtime_event(
                    root=runtime.workspace_root,
                    athlete_id=athlete_id,
                    run_id=run_id,
                    event_type="PHASE_BUNDLE_NORMALIZATION_FAILED",
                    crew="phase_planning",
                    task="phase_bundle_finalize",
                    component="crew:phase_bundle_finalize",
                    reason=str(exc),
                )
                raise
            return _validate_normalized_phase_bundle(
                normalized,
                runtime=runtime,
                athlete_id=athlete_id,
                run_id=run_id,
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
                loaded_inputs=loaded_inputs,
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
        loaded_inputs[output_spec.artifact_type.value.lower()] = {
            "ok": True,
            "document": document,
            "version_key": saved.get("version_key"),
        }
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
        if not isinstance(result, dict) or result.get("ok") is not True:
            return
        loaded_inputs[tool_name] = result
        if tool_name != "workspace_get_input":
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
            planning_bundle = _run_season_plan_document(
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
            try:
                normalized = normalize_season_plan_draft_bundle(planning_bundle)
            except Exception as exc:
                emit_runtime_event(
                    root=runtime.workspace_root,
                    athlete_id=athlete_id,
                    run_id=run_id,
                    event_type="SEASON_BUNDLE_NORMALIZATION_FAILED",
                    crew="season_planning",
                    task="season_plan_finalize",
                    component="crew:season_plan_finalize",
                    reason=str(exc),
                )
                raise
            return _validate_normalized_season_bundle(
                normalized,
                runtime=runtime,
                athlete_id=athlete_id,
                run_id=run_id,
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
            loaded_inputs=loaded_inputs,
            model_override=model_override,
            temperature_override=temperature_override,
        )
    elif task == AgentTask.CREATE_WEEK_PLAN:
        def _planning_runner(loop_input: str) -> JsonMap:
            planning_bundle = _execute_crewai_multiagent_crew(
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
                execution_mode="sequential",
            ).model_dump()
            return _validate_normalized_week_bundle(
                planning_bundle,
                runtime=runtime,
                athlete_id=athlete_id,
                run_id=run_id,
            )

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
            loaded_inputs=loaded_inputs,
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
            loaded_inputs=loaded_inputs,
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
    if task == AgentTask.CREATE_WEEK_PLAN:
        try:
            target_year, target_week = parse_target_week_from_user_input(user_input)
            return execute_week_engine(
                repo_root=ROOT,
                schema_dir=runtime.schema_dir,
                workspace_root=runtime.workspace_root,
                athlete_id=athlete_id,
                run_id=run_id,
                target_year=target_year,
                target_week=target_week,
                user_message=extract_message_from_user_input(user_input),
                preview_only=False,
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
    if task == AgentTask.CREATE_WEEK_PLAN:
        try:
            target_year, target_week = parse_target_week_from_user_input(user_input)
            return execute_week_engine(
                repo_root=ROOT,
                schema_dir=runtime.schema_dir,
                workspace_root=runtime.workspace_root,
                athlete_id=athlete_id,
                run_id=run_id,
                target_year=target_year,
                target_week=target_week,
                user_message=extract_message_from_user_input(user_input),
                preview_only=True,
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
