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
from rps.crewai_runtime.telemetry import emit_runtime_event, runtime_event_scope
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

_CANONICAL_OWNER_BY_ARTIFACT: dict[ArtifactType, str] = {
    ArtifactType.SEASON_SCENARIOS: "Season-Scenario-Agent",
    ArtifactType.SEASON_SCENARIO_SELECTION: "Season-Scenario-Agent",
    ArtifactType.SEASON_PLAN: "Season-Planner",
    ArtifactType.SEASON_PHASE_FEED_FORWARD: "Season-Planner",
    ArtifactType.PHASE_GUARDRAILS: "Phase-Architect",
    ArtifactType.PHASE_STRUCTURE: "Phase-Architect",
    ArtifactType.PHASE_PREVIEW: "Phase-Architect",
    ArtifactType.PHASE_FEED_FORWARD: "Phase-Architect",
    ArtifactType.WEEK_PLAN: "Week-Planner",
    ArtifactType.DES_ANALYSIS_REPORT: "Performance-Analyst",
}

_SEASON_INTERNAL_TASKS: tuple[str, ...] = (
    "season_scenario_interpretation",
    "season_event_anchor_review",
    "season_macrocycle_draft",
    "season_constraint_review",
    "season_historical_context_review",
    "season_kpi_guidance_review",
    "season_load_governance_review",
    "season_plan_audit",
)

_PHASE_INTERNAL_TASKS: tuple[str, ...] = (
    "phase_guardrails_draft",
    "phase_structure_draft",
    "phase_cadence_recovery_integration",
    "phase_intensity_distribution_review",
    "phase_preview_draft",
    "phase_constraint_audit",
    "phase_load_governance_audit",
    "phase_bundle_finalize",
)


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


def _normalize_artifact_meta(document: JsonMap, artifact_type: ArtifactType) -> JsonMap:
    """Apply canonical meta ownership for persisted artifact envelopes."""

    if not isinstance(document, dict):
        return document
    meta = document.get("meta")
    if not isinstance(meta, dict):
        return document
    meta.setdefault("authority", "Binding")
    owner = _CANONICAL_OWNER_BY_ARTIFACT.get(artifact_type)
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
        meta["owner_agent"] = _CANONICAL_OWNER_BY_ARTIFACT[ArtifactType.DES_ANALYSIS_REPORT]
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
) -> object:
    """Instantiate the CrewAI LLM wrapper for the given agent."""

    return crewai_llm_cls(
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


def _build_crewai_agent(
    agent_cls: Any,
    *,
    blueprint: Any,
    llm: object,
    tools: list[Any],
) -> object:
    """Instantiate one CrewAI agent from a blueprint."""

    config = getattr(blueprint, "config", {}) or {}
    return agent_cls(
        role=blueprint.role,
        goal=blueprint.goal,
        backstory=blueprint.backstory,
        llm=llm,
        tools=tools,
        allow_delegation=bool(config.get("allow_delegation", False)),
        verbose=bool(config.get("verbose", False)),
    )


def _extract_typed_output(result: object, task_obj: object) -> Any:
    """Extract the typed Pydantic output from a CrewAI task result."""

    task_output = getattr(task_obj, "output", None)
    pydantic_output = getattr(task_output, "pydantic", None) if task_output is not None else None
    if pydantic_output is None:
        pydantic_output = getattr(result, "pydantic", None)
    if pydantic_output is None and hasattr(result, "model_dump"):
        pydantic_output = result
    return pydantic_output


def _execute_crewai_task(
    *,
    agent_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    runtime: AgentRuntime,
    agent_name: str,
    agent_blueprint: Any,
    task_blueprint: Any,
    llm: object,
    tools: list[Any],
    description: str,
    athlete_id: str | None = None,
    run_id: str | None = None,
) -> Any:
    """Execute one CrewAI task and return its typed output."""

    agent = _build_crewai_agent(
        agent_cls,
        blueprint=agent_blueprint,
        llm=llm,
        tools=tools,
    )
    crew_task = task_cls(
        description=description,
        expected_output=task_blueprint.expected_output,
        agent=agent,
        output_pydantic=output_model_for_kind(task_blueprint.output_kind),
    )
    process = getattr(process_cls, "sequential")
    crew = crew_cls(
        agents=[agent],
        tasks=[crew_task],
        process=process,
        verbose=bool(task_blueprint.config.get("verbose", False)),
    )
    if athlete_id and run_id:
        with runtime_event_scope(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            component=f"crew:{task_blueprint.name}",
        ):
            result = crew.kickoff()
    else:
        result = crew.kickoff()
    pydantic_output = _extract_typed_output(result, crew_task)
    if pydantic_output is None:
        raw = getattr(getattr(crew_task, "output", None), "raw", None)
        raise RuntimeError(
            f"CrewAI task '{task_blueprint.name}' did not produce a typed pydantic output."
            + (f" Raw output: {raw}" if raw else "")
        )
    return pydantic_output


def _build_crewai_task(
    *,
    task_cls: Any,
    task_blueprint: Any,
    agent: object,
    description: str,
    context_tasks: list[object] | None = None,
) -> object:
    """Instantiate one CrewAI task object with optional explicit context."""

    kwargs: dict[str, Any] = {
        "description": description,
        "expected_output": task_blueprint.expected_output,
        "agent": agent,
        "output_pydantic": output_model_for_kind(task_blueprint.output_kind),
    }
    if context_tasks:
        kwargs["context"] = context_tasks
    return task_cls(**kwargs)


def _execute_crewai_hierarchical_crew(
    *,
    agent_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    runtime: AgentRuntime,
    manager_agent_name: str,
    crew_task_names: tuple[str, ...],
    final_task_name: str,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    llm: object,
    tools: list[Any],
    user_input: str,
    final_public_task: AgentTask | None = None,
    athlete_id: str | None = None,
    run_id: str | None = None,
) -> Any:
    """Execute one real multi-agent hierarchical crew and return the final typed output."""

    agents_by_name: dict[str, object] = {}
    for task_name in crew_task_names:
        task_blueprint = task_blueprints[task_name]
        agent_name = task_blueprint.agent
        if agent_name in agents_by_name:
            continue
        agent_blueprint = agent_blueprints[agent_name]
        agents_by_name[agent_name] = _build_crewai_agent(
            agent_cls,
            blueprint=agent_blueprint,
            llm=llm,
            tools=tools,
        )

    manager_agent = agents_by_name[manager_agent_name]
    crew_tasks: list[object] = []
    prior_tasks: list[object] = []
    final_task_obj: object | None = None
    for task_name in crew_task_names:
        task_blueprint = task_blueprints[task_name]
        agent_name = task_blueprint.agent
        prompt_agent = _resolve_prompt_agent_name(agent_name, agent_blueprints[agent_name])
        if task_name == final_task_name and final_public_task is not None:
            description = _build_task_description(
                runtime,
                agent_name=manager_agent_name,
                task=final_public_task,
                user_input=user_input,
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
            description = _build_internal_task_description(
                runtime,
                prompt_agent=prompt_agent,
                task_blueprint=task_blueprint,
                user_input=user_input,
            )
        crew_task = _build_crewai_task(
            task_cls=task_cls,
            task_blueprint=task_blueprint,
            agent=agents_by_name[agent_name],
            description=description,
            context_tasks=prior_tasks[:] if prior_tasks else None,
        )
        crew_tasks.append(crew_task)
        prior_tasks.append(crew_task)
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
    if hierarchical is not None:
        crew_kwargs["manager_agent"] = manager_agent
        crew_kwargs["manager_llm"] = llm
    crew = crew_cls(**crew_kwargs)
    if athlete_id and run_id:
        with runtime_event_scope(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            component=f"crew:{final_task_name}",
        ):
            result = crew.kickoff()
    else:
        result = crew.kickoff()
    pydantic_output = _extract_typed_output(result, final_task_obj)
    if pydantic_output is None:
        raw = getattr(getattr(final_task_obj, "output", None), "raw", None)
        raise RuntimeError(
            f"CrewAI crew final task '{final_task_name}' did not produce a typed pydantic output."
            + (f" Raw output: {raw}" if raw else "")
        )
    return pydantic_output


def _build_internal_task_description(
    runtime: AgentRuntime,
    *,
    prompt_agent: str,
    task_blueprint: Any,
    user_input: str,
    context_blocks: list[str] | None = None,
) -> str:
    """Build a specialist-task description with top-level prompt context."""

    prompt = runtime.prompt_loader.combined_system_prompt(prompt_agent)
    parts = [
        "System and agent instructions:",
        prompt,
        "",
        f"Internal specialist task: {task_blueprint.description}",
        "",
        "User request:",
        user_input,
    ]
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
    user_input: str,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    agent_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    llm: object,
    tools: list[Any],
    task_blueprint: Any,
    athlete_id: str,
    run_id: str,
) -> JsonMap:
    """Execute the hierarchical season crew and return the final manager document."""
    pydantic_output = _execute_crewai_hierarchical_crew(
        agent_cls=agent_cls,
        crew_cls=crew_cls,
        task_cls=task_cls,
        process_cls=process_cls,
        runtime=runtime,
        manager_agent_name=task_blueprint.agent,
        crew_task_names=(*_SEASON_INTERNAL_TASKS, task_blueprint.name),
        final_task_name=task_blueprint.name,
        task_blueprints=task_blueprints,
        agent_blueprints=agent_blueprints,
        llm=llm,
        tools=tools,
        user_input=user_input,
        final_public_task=AgentTask.CREATE_SEASON_PLAN,
        athlete_id=athlete_id,
        run_id=run_id,
    )
    document = pydantic_output.model_dump() if hasattr(pydantic_output, "model_dump") else pydantic_output
    if not isinstance(document, dict):
        raise RuntimeError("Season manager output did not decode to an artifact envelope object.")
    return document


def _run_phase_bundle_document(
    *,
    runtime: AgentRuntime,
    user_input: str,
    task_blueprints: dict[str, Any],
    agent_blueprints: dict[str, Any],
    agent_cls: Any,
    crew_cls: Any,
    task_cls: Any,
    process_cls: Any,
    llm: object,
    tools: list[Any],
    athlete_id: str,
    run_id: str,
) -> JsonMap:
    """Execute the hierarchical phase crew once and return the final PhaseBundle document."""
    final_task_name = _PHASE_INTERNAL_TASKS[-1]
    pydantic_output = _execute_crewai_hierarchical_crew(
        agent_cls=agent_cls,
        crew_cls=crew_cls,
        task_cls=task_cls,
        process_cls=process_cls,
        runtime=runtime,
        manager_agent_name=task_blueprints[final_task_name].agent,
        crew_task_names=_PHASE_INTERNAL_TASKS,
        final_task_name=final_task_name,
        task_blueprints=task_blueprints,
        agent_blueprints=agent_blueprints,
        llm=llm,
        tools=tools,
        user_input=user_input,
        final_public_task=None,
        athlete_id=athlete_id,
        run_id=run_id,
    )
    bundle_document = (
        pydantic_output.model_dump() if hasattr(pydantic_output, "model_dump") else pydantic_output
    )
    if not isinstance(bundle_document, dict):
        raise RuntimeError("Phase bundle output did not decode to an object.")
    return bundle_document


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
    """Execute the hierarchical phase crew once and persist the requested phase artefacts."""

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
    manager_task_blueprint = task_blueprints["phase_bundle_finalize"]

    llm = _build_crewai_llm(
        LLM,
        runtime,
        agent_name=agent_name,
        model_override=model_override,
        temperature_override=temperature_override,
    )
    tools, loaded_inputs = _build_crewai_tooling(athlete_id, runtime.workspace_root)

    try:
        bundle_document = _run_phase_bundle_document(
            runtime=runtime,
            user_input=user_input,
            task_blueprints=task_blueprints,
            agent_blueprints=agent_blueprints,
            agent_cls=Agent,
            crew_cls=Crew,
            task_cls=Task,
            process_cls=Process,
            llm=llm,
            tools=tools,
            athlete_id=athlete_id,
            run_id=run_id,
        )
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "produced": {},
        }

    if bundle_document.get("blocking_issues"):
        return {
            "ok": False,
            "error": "Phase bundle blocked by internal audits.",
            "details": list(bundle_document.get("blocking_issues") or []),
            "warnings": list(bundle_document.get("warnings") or []),
            "produced": {},
        }

    guarded = GuardedValidatedStore(
        athlete_id=athlete_id,
        schema_dir=runtime.schema_dir,
        workspace_root=runtime.workspace_root,
    )
    produced: dict[str, Any] = {}
    warnings = list(bundle_document.get("warnings") or [])
    for task in requested_tasks:
        output_spec = OUTPUT_SPECS[task]
        document = _phase_document_from_bundle(bundle_document, output_spec.artifact_type)
        document = _normalize_document(output_spec, document, loaded_inputs)
        try:
            saved = guarded.guard_put_validated(
                output_spec=output_spec,
                document=document,
                run_id=run_id,
                producer_agent=manager_task_blueprint.agent,
                update_latest=True,
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
            logger.warning("CrewAI phase bundle store failed for %s: %s", output_spec.artifact_type.value, exc)
            return {"ok": False, "error": str(exc), "warnings": warnings, "produced": produced}
        produced[output_spec.tool_name] = saved
        emit_runtime_event(
            root=runtime.workspace_root,
            athlete_id=athlete_id,
            run_id=run_id,
            event_type="ARTEFACT_WRITTEN",
            artifact_type=output_spec.artifact_type.value,
            outputs=[saved],
        )

    return {"ok": True, "produced": produced, "warnings": warnings}


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

    llm = _build_crewai_llm(
        LLM,
        runtime,
        agent_name=agent_name,
        model_override=model_override,
        temperature_override=temperature_override,
    )

    tools, loaded_inputs = _build_crewai_tooling(athlete_id, runtime.workspace_root)

    try:
        if task == AgentTask.CREATE_SEASON_PLAN:
            document = _run_season_plan_document(
                runtime=runtime,
                user_input=user_input,
                task_blueprints=task_blueprints,
                agent_blueprints=agent_blueprints,
                agent_cls=Agent,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                llm=llm,
                tools=tools,
                task_blueprint=task_blueprint,
                athlete_id=athlete_id,
                run_id=run_id,
            )
        else:
            description = _build_task_description(
                runtime,
                agent_name=agent_name,
                task=task,
                user_input=user_input,
            )
            pydantic_output = _execute_crewai_task(
                agent_cls=Agent,
                crew_cls=Crew,
                task_cls=Task,
                process_cls=Process,
                runtime=runtime,
                agent_name=agent_name,
                agent_blueprint=agent_blueprint,
                task_blueprint=task_blueprint,
                llm=llm,
                tools=tools,
                description=description,
                athlete_id=athlete_id,
                run_id=run_id,
            )
            document = pydantic_output.model_dump() if hasattr(pydantic_output, "model_dump") else pydantic_output
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "produced": {},
        }

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

    emit_runtime_event(
        root=runtime.workspace_root,
        athlete_id=athlete_id,
        run_id=run_id,
        event_type="ARTEFACT_WRITTEN",
        artifact_type=output_spec.artifact_type.value,
        outputs=[saved],
    )
    return {"ok": True, "produced": {output_spec.tool_name: saved}}
