"""Agent registry."""

from rps.agents.spec import AgentSpec


AGENTS: dict[str, AgentSpec] = {
    "season_scenario": AgentSpec(
        name="season_scenario",
        display_name="Season-Scenario-Agent",
        vector_store_name="vs_rps_all_agents",
        prompt_file_stem="season_scenario",
    ),
    "macro_planner": AgentSpec(
        name="macro_planner",
        display_name="Macro-Planner",
        vector_store_name="vs_rps_all_agents",
        prompt_file_stem="macro_planner",
    ),
    "meso_architect": AgentSpec(
        name="meso_architect",
        display_name="Meso-Architect",
        vector_store_name="vs_rps_all_agents",
        prompt_file_stem="meso_architect",
    ),
    "micro_planner": AgentSpec(
        name="micro_planner",
        display_name="Micro-Planner",
        vector_store_name="vs_rps_all_agents",
        prompt_file_stem="micro_planner",
    ),
    "workout_builder": AgentSpec(
        name="workout_builder",
        display_name="Workout-Builder",
        vector_store_name="vs_rps_all_agents",
        prompt_file_stem="workout_builder",
    ),
    "performance_analysis": AgentSpec(
        name="performance_analysis",
        display_name="Performance-Analyst",
        vector_store_name="vs_rps_all_agents",
        prompt_file_stem="performance_analysis",
    ),
}


def list_agents() -> list[str]:
    """Return the list of registered agent names."""
    return list(AGENTS.keys())


def get_agent(name: str) -> AgentSpec:
    """Return the AgentSpec for a given agent name."""
    return AGENTS[name]
