"""YAML configuration loader for CrewAI runtime definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

JsonMap = dict[str, Any]

OPERATIONAL_CREW_SKILLS: tuple[str, ...] = (
    "skills/shared/runtime-boundaries",
    "skills/shared/resolved-context-consumption",
    "skills/shared/snapshot-memory-consumption",
    "skills/shared/contract-context-consumption",
    "skills/shared/blueprint-contract-validation",
    "skills/shared/blueprint-bound-writing",
    "skills/shared/traceability-and-naming",
    "skills/shared/replan-instruction-authoring",
)


@dataclass(frozen=True)
class CrewAIConfigBundle:
    """Loaded CrewAI configuration bundle."""

    agents: JsonMap
    tasks: JsonMap
    skills: JsonMap
    knowledge_sources: JsonMap
    memory_policy: JsonMap
    task_policies: JsonMap
    flow_persistence: JsonMap
    runtime_profiles: JsonMap


def _load_yaml(path: Path) -> JsonMap:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a top-level mapping.")
    return data


def load_crewai_config_bundle(
    *,
    root: Path | None = None,
) -> CrewAIConfigBundle:
    """Load and minimally validate CrewAI YAML config files."""

    base = (root or Path.cwd()) / "config" / "crewai"
    agents = _load_yaml(base / "agents.yaml")
    tasks = _load_yaml(base / "tasks.yaml")
    skills = _load_yaml(base / "skills.yaml")
    knowledge_sources = _load_yaml(base / "knowledge_sources.yaml")
    memory_policy = _load_yaml(base / "memory_policy.yaml")
    task_policies = _load_yaml(base / "task_policies.yaml")
    flow_persistence = _load_yaml(base / "flow_persistence.yaml")
    runtime_profiles = _load_yaml(base / "runtime_profiles.yaml")

    agent_defs = agents.get("agents")
    task_defs = tasks.get("tasks")
    skill_agent_defs = skills.get("agents") or {}
    skill_crew_defs = skills.get("crews") or {}
    if not isinstance(agent_defs, dict):
        raise ValueError("config/crewai/agents.yaml must contain an 'agents' mapping.")
    if not isinstance(task_defs, dict):
        raise ValueError("config/crewai/tasks.yaml must contain a 'tasks' mapping.")
    if not isinstance(skill_agent_defs, dict):
        raise ValueError("config/crewai/skills.yaml must contain an 'agents' mapping.")
    if not isinstance(skill_crew_defs, dict):
        raise ValueError("config/crewai/skills.yaml must contain a 'crews' mapping.")
    if not isinstance(knowledge_sources.get("agents") or {}, dict):
        raise ValueError("config/crewai/knowledge_sources.yaml must contain an 'agents' mapping.")
    if not isinstance(memory_policy.get("crews") or {}, dict):
        raise ValueError("config/crewai/memory_policy.yaml must contain a 'crews' mapping.")
    if not isinstance(task_policies.get("tasks") or {}, dict):
        raise ValueError("config/crewai/task_policies.yaml must contain a 'tasks' mapping.")
    if not isinstance(flow_persistence.get("flows") or {}, dict):
        raise ValueError("config/crewai/flow_persistence.yaml must contain a 'flows' mapping.")
    if not isinstance(runtime_profiles.get("crews") or {}, dict):
        raise ValueError("config/crewai/runtime_profiles.yaml must contain a 'crews' mapping.")
    if not isinstance(runtime_profiles.get("agents") or {}, dict):
        raise ValueError("config/crewai/runtime_profiles.yaml must contain an 'agents' mapping.")

    allowed_models = runtime_profiles.get("allowed_models") or []
    if not isinstance(allowed_models, list) or not all(isinstance(item, str) for item in allowed_models):
        raise ValueError("config/crewai/runtime_profiles.yaml must contain an 'allowed_models' string list.")

    unknown_agents: list[str] = []
    for task_name, task_def in task_defs.items():
        if not isinstance(task_def, dict):
            raise ValueError(f"Task '{task_name}' must be a mapping.")
        agent_name = task_def.get("agent")
        if isinstance(agent_name, str) and agent_name not in agent_defs:
            unknown_agents.append(agent_name)
    if unknown_agents:
        unique = ", ".join(sorted(set(unknown_agents)))
        raise ValueError(f"Unknown agent references in tasks.yaml: {unique}")

    unknown_knowledge_agents = sorted(
        set((knowledge_sources.get("agents") or {}).keys()) - set(agent_defs.keys())
    )
    if unknown_knowledge_agents:
        unique = ", ".join(unknown_knowledge_agents)
        raise ValueError(f"Unknown agent references in knowledge_sources.yaml: {unique}")

    unknown_skill_agents = sorted(set(skill_agent_defs.keys()) - set(agent_defs.keys()))
    if unknown_skill_agents:
        unique = ", ".join(unknown_skill_agents)
        raise ValueError(f"Unknown agent references in skills.yaml: {unique}")

    runtime_agent_defs = runtime_profiles.get("agents") or {}
    unknown_runtime_agents = sorted(set(runtime_agent_defs.keys()) - set(agent_defs.keys()))
    if unknown_runtime_agents:
        unique = ", ".join(unknown_runtime_agents)
        raise ValueError(f"Unknown agent references in runtime_profiles.yaml: {unique}")

    known_crews = set(skill_crew_defs.keys()) | set((memory_policy.get("crews") or {}).keys())
    runtime_crew_defs = runtime_profiles.get("crews") or {}
    unknown_runtime_crews = sorted(set(runtime_crew_defs.keys()) - known_crews)
    if unknown_runtime_crews:
        unique = ", ".join(unknown_runtime_crews)
        raise ValueError(f"Unknown crew references in runtime_profiles.yaml: {unique}")

    configured_runtime_models: set[str] = set()
    for agent_def in runtime_agent_defs.values():
        if isinstance(agent_def, dict):
            model_name = agent_def.get("model")
            if isinstance(model_name, str) and model_name:
                configured_runtime_models.add(model_name)
    for crew_def in runtime_crew_defs.values():
        if not isinstance(crew_def, dict):
            continue
        planning = crew_def.get("planning") or {}
        if not isinstance(planning, dict):
            raise ValueError("Crew planning profiles in runtime_profiles.yaml must be mappings.")
        model_name = planning.get("model")
        enabled = planning.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            raise ValueError("Crew planning.enabled values in runtime_profiles.yaml must be booleans.")
        if isinstance(model_name, str) and model_name:
            configured_runtime_models.add(model_name)
    unknown_models = sorted(configured_runtime_models - set(allowed_models))
    if unknown_models:
        unique = ", ".join(unknown_models)
        raise ValueError(f"Unknown model references in runtime_profiles.yaml: {unique}")

    for agent_name, agent_def in runtime_agent_defs.items():
        if not isinstance(agent_def, dict):
            raise ValueError(f"Runtime profile for agent '{agent_name}' must be a mapping.")
        reasoning = agent_def.get("reasoning") or {}
        if reasoning and not isinstance(reasoning, dict):
            raise ValueError(f"Runtime reasoning profile for agent '{agent_name}' must be a mapping.")
        if isinstance(reasoning, dict):
            enabled = reasoning.get("enabled")
            if enabled is not None and not isinstance(enabled, bool):
                raise ValueError(
                    f"Runtime reasoning.enabled for agent '{agent_name}' must be a boolean."
                )
            max_attempts = reasoning.get("max_attempts")
            if max_attempts is not None and (not isinstance(max_attempts, int) or max_attempts < 1):
                raise ValueError(
                    f"Runtime reasoning.max_attempts for agent '{agent_name}' must be a positive integer."
                )

    base_root = root or Path.cwd()
    configured_skill_paths: set[str] = set()
    for crew_name, crew_def in skill_crew_defs.items():
        if not isinstance(crew_def, dict):
            raise ValueError(f"Crew skill profile for '{crew_name}' must be a mapping.")
        crew_skills = crew_def.get("skills") or []
        if not isinstance(crew_skills, list) or not all(isinstance(item, str) for item in crew_skills):
            raise ValueError(f"Crew skill profile for '{crew_name}' must contain a string list in 'skills'.")
        invalid = sorted(set(crew_skills) - set(OPERATIONAL_CREW_SKILLS))
        if invalid:
            unique = ", ".join(invalid)
            raise ValueError(f"Crew '{crew_name}' attaches non-operational skills: {unique}")
        configured_skill_paths.update(crew_skills)

    for agent_name, agent_def in skill_agent_defs.items():
        if not isinstance(agent_def, dict):
            raise ValueError(f"Agent skill profile for '{agent_name}' must be a mapping.")
        skill_value = agent_def.get("skill")
        if not isinstance(skill_value, str) or not skill_value:
            raise ValueError(f"Agent '{agent_name}' must declare exactly one non-empty 'skill' string.")
        extra_skills = agent_def.get("skills")
        if extra_skills is not None:
            raise ValueError(f"Agent '{agent_name}' must not declare 'skills'; use exactly one 'skill'.")
        extra_bundles = agent_def.get("bundles")
        if extra_bundles is not None:
            raise ValueError(f"Agent '{agent_name}' must not declare 'bundles'; use exactly one 'skill'.")
        configured_skill_paths.add(skill_value)

    missing_skill_agents = sorted(set(agent_defs.keys()) - set(skill_agent_defs.keys()))
    if missing_skill_agents:
        unique = ", ".join(missing_skill_agents)
        raise ValueError(f"Missing skill assignments in skills.yaml for agents: {unique}")

    missing_skills = sorted(
        skill_path for skill_path in configured_skill_paths if not ((base_root / skill_path) / "SKILL.md").exists()
    )
    if missing_skills:
        unique = ", ".join(missing_skills)
        raise ValueError(f"Configured CrewAI skills are missing SKILL.md: {unique}")

    task_policy_defs = task_policies.get("tasks") or {}
    unknown_policy_tasks = sorted(set(task_policy_defs.keys()) - set(task_defs.keys()))
    if unknown_policy_tasks:
        unique = ", ".join(unknown_policy_tasks)
        raise ValueError(f"Unknown task references in task_policies.yaml: {unique}")

    return CrewAIConfigBundle(
        agents=agents,
        tasks=tasks,
        skills=skills,
        knowledge_sources=knowledge_sources,
        memory_policy=memory_policy,
        task_policies=task_policies,
        flow_persistence=flow_persistence,
        runtime_profiles=runtime_profiles,
    )
