"""YAML configuration loader for CrewAI runtime definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

JsonMap = dict[str, Any]


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

    agent_defs = agents.get("agents")
    task_defs = tasks.get("tasks")
    if not isinstance(agent_defs, dict):
        raise ValueError("config/crewai/agents.yaml must contain an 'agents' mapping.")
    if not isinstance(task_defs, dict):
        raise ValueError("config/crewai/tasks.yaml must contain a 'tasks' mapping.")
    if not isinstance(skills.get("agents") or {}, dict):
        raise ValueError("config/crewai/skills.yaml must contain an 'agents' mapping.")
    if not isinstance(knowledge_sources.get("agents") or {}, dict):
        raise ValueError("config/crewai/knowledge_sources.yaml must contain an 'agents' mapping.")
    if not isinstance(memory_policy.get("crews") or {}, dict):
        raise ValueError("config/crewai/memory_policy.yaml must contain a 'crews' mapping.")
    if not isinstance(task_policies.get("tasks") or {}, dict):
        raise ValueError("config/crewai/task_policies.yaml must contain a 'tasks' mapping.")
    if not isinstance(flow_persistence.get("flows") or {}, dict):
        raise ValueError("config/crewai/flow_persistence.yaml must contain a 'flows' mapping.")

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
    unknown_skill_agents = sorted(set((skills.get("agents") or {}).keys()) - set(agent_defs.keys()))
    if unknown_skill_agents:
        unique = ", ".join(unknown_skill_agents)
        raise ValueError(f"Unknown agent references in skills.yaml: {unique}")
    skill_bundle_defs = skills.get("bundles") or {}
    configured_skill_paths: list[str] = []
    for bundle_def in skill_bundle_defs.values():
        if isinstance(bundle_def, dict):
            configured_skill_paths.extend(
                str(item) for item in (bundle_def.get("skills") or []) if isinstance(item, str)
            )
    base_root = root or Path.cwd()
    missing_skills = sorted(
        {
            skill_path
            for skill_path in configured_skill_paths
            if not ((base_root / skill_path) / "SKILL.md").exists()
        }
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
    )
