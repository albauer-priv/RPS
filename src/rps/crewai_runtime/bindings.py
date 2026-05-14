"""Optional CrewAI object binding from YAML config and typed outputs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from .compat import crewai_runtime_status
from .config import CrewAIConfigBundle, load_crewai_config_bundle
from .guardrails import build_task_guardrail_kwargs, resolve_task_policy
from .knowledge import build_crewai_knowledge_kwargs, resolve_agent_knowledge_profile
from .memory import build_agent_memory_value, build_crew_memory_kwargs, resolve_agent_memory_profile
from .models import (
    AdjustmentIntentModel,
    ArtifactEnvelopeModel,
    CoachingRecommendationModel,
    CoachOperationApplyResultModel,
    CoachOperationPreviewModel,
    CoachPreviewSummaryModel,
    ConstraintAuditModel,
    LoadGovernanceAuditModel,
    PendingResolutionResultModel,
    PhaseBundleModel,
    PhaseGuardrailsPayloadModel,
    PhasePreviewPayloadModel,
    PhaseStructurePayloadModel,
    SeasonEventAnchorModel,
    SeasonMacrocycleDraftModel,
    SeasonPlanAuditModel,
    TurnModeModel,
    WeekContextAssessmentModel,
)

JsonMap = dict[str, Any]


@dataclass(frozen=True)
class AgentBlueprint:
    """Config-derived agent definition before optional CrewAI instantiation."""

    name: str
    role: str
    goal: str
    backstory: str
    knowledge_profile: JsonMap
    memory_profile: JsonMap
    config: JsonMap


@dataclass(frozen=True)
class TaskBlueprint:
    """Config-derived task definition before optional CrewAI instantiation."""

    name: str
    agent: str
    description: str
    expected_output: str
    output_kind: str
    execution_policy: JsonMap
    config: JsonMap


@dataclass(frozen=True)
class CrewAIBindings:
    """Bound CrewAI runtime objects and their blueprints."""

    agents: dict[str, object]
    tasks: dict[str, object]
    agent_blueprints: dict[str, AgentBlueprint]
    task_blueprints: dict[str, TaskBlueprint]


def build_agent_blueprints(bundle: CrewAIConfigBundle) -> dict[str, AgentBlueprint]:
    """Convert YAML agent config into normalized blueprints."""

    raw_agents = bundle.agents["agents"]
    blueprints: dict[str, AgentBlueprint] = {}
    for name, raw in raw_agents.items():
        if not isinstance(raw, dict):
            raise ValueError(f"Agent '{name}' must be a mapping.")
        role = str(raw.get("role") or name)
        goal = str(raw.get("goal") or role)
        backstory = str(raw.get("backstory") or raw.get("display_name") or role)
        blueprints[name] = AgentBlueprint(
            name=name,
            role=role,
            goal=goal,
            backstory=backstory,
            knowledge_profile=resolve_agent_knowledge_profile(bundle, agent_name=name),
            memory_profile={},
            config=raw,
        )
    return blueprints


def build_task_blueprints(bundle: CrewAIConfigBundle) -> dict[str, TaskBlueprint]:
    """Convert YAML task config into normalized blueprints."""

    raw_tasks = bundle.tasks["tasks"]
    blueprints: dict[str, TaskBlueprint] = {}
    for name, raw in raw_tasks.items():
        if not isinstance(raw, dict):
            raise ValueError(f"Task '{name}' must be a mapping.")
        agent_name = str(raw.get("agent") or "")
        description = str(raw.get("description") or f"Execute task '{name}'.")
        expected_output = str(raw.get("expected_output") or f"Structured output for task '{name}'.")
        output_kind = str(raw.get("output") or "artifact_envelope")
        blueprints[name] = TaskBlueprint(
            name=name,
            agent=agent_name,
            description=description,
            expected_output=expected_output,
            output_kind=output_kind,
            execution_policy=resolve_task_policy(
                type("TaskProxy", (), {"name": name, "config": raw})(),
                bundle.task_policies,
            ).__dict__,
            config=raw,
        )
    return blueprints


def output_model_for_kind(output_kind: str) -> type[Any]:
    """Resolve the typed output model for a configured task output kind."""

    registry: dict[str, type[Any]] = {
        "turn_mode": TurnModeModel,
        "week_context_assessment": WeekContextAssessmentModel,
        "coaching_recommendation": CoachingRecommendationModel,
        "adjustment_intent": AdjustmentIntentModel,
        "pending_resolution_result": PendingResolutionResultModel,
        "coach_preview_summary": CoachPreviewSummaryModel,
        "artifact_envelope": ArtifactEnvelopeModel,
        "coach_preview": CoachOperationPreviewModel,
        "coach_apply": CoachOperationApplyResultModel,
        "season_event_anchor": SeasonEventAnchorModel,
        "season_macrocycle_draft": SeasonMacrocycleDraftModel,
        "season_plan_audit": SeasonPlanAuditModel,
        "phase_guardrails_payload": PhaseGuardrailsPayloadModel,
        "phase_structure_payload": PhaseStructurePayloadModel,
        "phase_preview_payload": PhasePreviewPayloadModel,
        "constraint_audit": ConstraintAuditModel,
        "load_governance_audit": LoadGovernanceAuditModel,
        "phase_bundle": PhaseBundleModel,
    }
    if output_kind not in registry:
        raise ValueError(f"Unsupported CrewAI output kind: {output_kind}")
    return registry[output_kind]


def build_crewai_bindings(
    *,
    root: Path | None = None,
    llm_factory: Callable[[str, AgentBlueprint], object] | None = None,
    tools_factory: Callable[[TaskBlueprint], list[object]] | None = None,
) -> CrewAIBindings:
    """Build actual CrewAI Agent/Task objects when the runtime is supported."""

    status = crewai_runtime_status()
    if not status.python_supported:
        raise RuntimeError(status.message)
    if not status.package_installed:
        raise RuntimeError(status.message)

    crewai = import_module("crewai")
    Agent = getattr(crewai, "Agent")
    Task = getattr(crewai, "Task")

    bundle = load_crewai_config_bundle(root=root)
    agent_blueprints = build_agent_blueprints(bundle)
    task_blueprints = build_task_blueprints(bundle)

    crew_memory_kwargs = build_crew_memory_kwargs(
        crewai,
        profile={
            "enabled": False,
            "scope": "",
            "storage": "",
            "embedder": {},
            "llm": None,
        },
    )
    shared_memory = crew_memory_kwargs.get("memory")

    agents: dict[str, object] = {}
    for name, blueprint in agent_blueprints.items():
        llm = llm_factory(name, blueprint) if llm_factory else None
        kwargs: JsonMap = {
            "role": blueprint.role,
            "goal": blueprint.goal,
            "backstory": blueprint.backstory,
            "verbose": bool(blueprint.config.get("verbose", False)),
        }
        knowledge_kwargs = build_crewai_knowledge_kwargs(
            root=(root or Path.cwd()),
            profile=blueprint.knowledge_profile,
        )
        kwargs.update(knowledge_kwargs)
        agent_memory_value = build_agent_memory_value(
            shared_memory=shared_memory,
            profile=resolve_agent_memory_profile(
                bundle,
                agent_name=name,
                athlete_id="global",
                surface="default",
            ),
        )
        if agent_memory_value is not None:
            kwargs["memory"] = agent_memory_value
        for field in ("system_template", "prompt_template", "response_template"):
            value = blueprint.config.get(field)
            if isinstance(value, str) and value:
                kwargs[field] = value
        if llm is not None:
            kwargs["llm"] = llm
        agents[name] = Agent(**kwargs)

    tasks: dict[str, object] = {}
    for name, blueprint in task_blueprints.items():
        task_kwargs: JsonMap = {
            "description": blueprint.description,
            "expected_output": blueprint.expected_output,
            "agent": agents[blueprint.agent],
        }
        guardrail_kwargs = build_task_guardrail_kwargs(blueprint, bundle.task_policies)
        output_mode = str(guardrail_kwargs.pop("_resolved_output_mode", "pydantic"))
        if output_mode == "json":
            task_kwargs["output_json"] = output_model_for_kind(blueprint.output_kind)
        elif output_mode == "pydantic":
            task_kwargs["output_pydantic"] = output_model_for_kind(blueprint.output_kind)
        task_kwargs.update(guardrail_kwargs)
        tools = tools_factory(blueprint) if tools_factory else []
        if tools:
            task_kwargs["tools"] = tools
        tasks[name] = Task(**task_kwargs)

    return CrewAIBindings(
        agents=agents,
        tasks=tasks,
        agent_blueprints=agent_blueprints,
        task_blueprints=task_blueprints,
    )
