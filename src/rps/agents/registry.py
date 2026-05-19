"""Agent registry."""

from rps.agents.spec import AgentSpec

AGENTS: dict[str, AgentSpec] = {
    "season_scenario": AgentSpec(
        name="season_scenario",
        display_name="Season-Scenario-Agent",
        prompt_file_stem="season_scenario",
    ),
    "season_planner": AgentSpec(
        name="season_planner",
        display_name="Season-Planner",
        prompt_file_stem="season_planner",
    ),
    "phase_architect": AgentSpec(
        name="phase_architect",
        display_name="Phase-Architect",
        prompt_file_stem="phase_architect",
    ),
    "week_planner": AgentSpec(
        name="week_planner",
        display_name="Week-Planner",
        prompt_file_stem="week_planner",
    ),
    "performance_analysis": AgentSpec(
        name="performance_analysis",
        display_name="Performance-Analyst",
        prompt_file_stem="performance_analysis",
    ),
    "coach": AgentSpec(
        name="coach",
        display_name="Coach",
        prompt_file_stem="coach",
    ),
}


def list_agents() -> list[str]:
    """Return the list of registered agent names."""
    return list(AGENTS.keys())


def get_agent(name: str) -> AgentSpec:
    """Return the AgentSpec for a given agent name."""
    return AGENTS[name]
