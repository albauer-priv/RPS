"""YAML configuration loader for future CrewAI agent/task definitions."""

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

    agent_defs = agents.get("agents")
    task_defs = tasks.get("tasks")
    if not isinstance(agent_defs, dict):
        raise ValueError("config/crewai/agents.yaml must contain an 'agents' mapping.")
    if not isinstance(task_defs, dict):
        raise ValueError("config/crewai/tasks.yaml must contain a 'tasks' mapping.")

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

    return CrewAIConfigBundle(agents=agents, tasks=tasks)
