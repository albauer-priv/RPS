"""CrewAI Flow wrappers for outer season and phase orchestration."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Any

from pydantic import BaseModel, Field

from rps.agents.crewai_backend import run_phase_bundle_crewai
from rps.agents.runtime import AgentRuntime, run_agent_multi_output
from rps.agents.tasks import AgentTask

JsonMap = dict[str, Any]


class SeasonFlowState(BaseModel):
    """Structured state for season outer orchestration."""

    action: str = ""
    result: JsonMap = Field(default_factory=dict)


class PhaseFlowState(BaseModel):
    """Structured state for phase outer orchestration."""

    requested_tasks: list[str] = Field(default_factory=list)
    result: JsonMap = Field(default_factory=dict)


def _load_flow_symbols() -> tuple[Any, Any, Any, Any]:
    """Load CrewAI Flow primitives lazily for runtime-safe imports."""

    flow_module = import_module("crewai.flow.flow")
    Flow = getattr(flow_module, "Flow")
    start = getattr(flow_module, "start")
    listen = getattr(flow_module, "listen")
    router = getattr(flow_module, "router")
    return Flow, start, listen, router


def run_season_flow(
    *,
    runtime_for: Callable[[str], AgentRuntime],
    agent_name: str,
    athlete_id: str,
    task: AgentTask,
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
    force_file_search: bool = True,
    max_num_results: int = 20,
) -> JsonMap:
    """Execute one season outer step through a CrewAI Flow wrapper."""

    action_by_task = {
        AgentTask.CREATE_SEASON_SCENARIOS: "season_scenarios",
        AgentTask.CREATE_SEASON_SCENARIO_SELECTION: "season_scenario_selection",
        AgentTask.CREATE_SEASON_PLAN: "season_plan",
    }
    action = action_by_task.get(task)
    if action is None:
        raise ValueError(f"Unsupported season flow task: {task.value}")

    Flow, start, listen, router = _load_flow_symbols()

    class SeasonOuterFlow(Flow[SeasonFlowState]):
        @start()
        def bootstrap(self) -> str:
            return self.state.action

        @router(bootstrap)
        def route(self, selected_action: str) -> str:
            return selected_action

        @listen("season_scenarios")
        def run_scenarios(self) -> JsonMap:
            self.state.result = run_agent_multi_output(
                runtime_for(agent_name),
                agent_name=agent_name,
                agent_vs_name="vs_rps_all_agents",
                athlete_id=athlete_id,
                tasks=[AgentTask.CREATE_SEASON_SCENARIOS],
                user_input=user_input,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
                force_file_search=force_file_search,
                max_num_results=max_num_results,
            )
            return self.state.result

        @listen("season_scenario_selection")
        def run_selection(self) -> JsonMap:
            self.state.result = run_agent_multi_output(
                runtime_for(agent_name),
                agent_name=agent_name,
                agent_vs_name="vs_rps_all_agents",
                athlete_id=athlete_id,
                tasks=[AgentTask.CREATE_SEASON_SCENARIO_SELECTION],
                user_input=user_input,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
                force_file_search=force_file_search,
                max_num_results=max_num_results,
            )
            return self.state.result

        @listen("season_plan")
        def run_plan(self) -> JsonMap:
            self.state.result = run_agent_multi_output(
                runtime_for(agent_name),
                agent_name=agent_name,
                agent_vs_name="vs_rps_all_agents",
                athlete_id=athlete_id,
                tasks=[AgentTask.CREATE_SEASON_PLAN],
                user_input=user_input,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
                force_file_search=force_file_search,
                max_num_results=max_num_results,
            )
            return self.state.result

    flow = SeasonOuterFlow()
    flow.state.action = action
    flow.kickoff()
    return dict(flow.state.result)


def run_phase_flow(
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
    """Execute the outer Phase chain through one CrewAI Flow-backed bundle run."""

    if not tasks:
        return {"ok": True, "produced": {}}

    Flow, start, listen, _router = _load_flow_symbols()

    class PhaseOuterFlow(Flow[PhaseFlowState]):
        @start()
        def bootstrap(self) -> list[str]:
            return list(self.state.requested_tasks)

        @listen(bootstrap)
        def run_bundle(self, _requested_tasks: list[str]) -> JsonMap:
            self.state.result = run_phase_bundle_crewai(
                runtime,
                agent_name=agent_name,
                athlete_id=athlete_id,
                tasks=tasks,
                user_input=user_input,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
            )
            return self.state.result

    flow = PhaseOuterFlow()
    flow.state.requested_tasks = [task.value for task in tasks]
    flow.kickoff()
    return dict(flow.state.result)
