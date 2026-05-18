"""CrewAI Flow wrappers for outer orchestration and Coach routing."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from rps.agents.crewai_backend import run_phase_bundle_crewai
from rps.agents.runtime import AgentRuntime, run_agent_multi_output, run_agent_multi_output_preview
from rps.agents.tasks import AgentTask
from rps.crewai_runtime.telemetry import emit_runtime_event, runtime_event_scope

from .config import load_crewai_config_bundle

JsonMap = dict[str, Any]


class SeasonFlowState(BaseModel):
    """Structured state for season outer orchestration."""

    athlete_id: str = ""
    run_id: str = ""
    target_iso_week: str = ""
    action: str = ""
    loaded_input_refs: JsonMap = Field(default_factory=dict)
    deterministic_context_refs: JsonMap = Field(default_factory=dict)
    produced_artifact_refs: JsonMap = Field(default_factory=dict)
    review_decisions: JsonMap = Field(default_factory=dict)
    failure_reason: str = ""
    source_versions: JsonMap = Field(default_factory=dict)
    intermediate_summaries: list[str] = Field(default_factory=list)
    normalization_summary: JsonMap = Field(default_factory=dict)
    persistence_summary: JsonMap = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    result: JsonMap = Field(default_factory=dict)


class PhaseFlowState(BaseModel):
    """Structured state for phase outer orchestration."""

    athlete_id: str = ""
    run_id: str = ""
    target_iso_week: str = ""
    requested_tasks: list[str] = Field(default_factory=list)
    phase_range: str = ""
    loaded_input_refs: JsonMap = Field(default_factory=dict)
    deterministic_context_refs: JsonMap = Field(default_factory=dict)
    produced_artifact_refs: JsonMap = Field(default_factory=dict)
    review_decisions: JsonMap = Field(default_factory=dict)
    failure_reason: str = ""
    source_versions: JsonMap = Field(default_factory=dict)
    bundle_summary: JsonMap = Field(default_factory=dict)
    persistence_summary: JsonMap = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    result: JsonMap = Field(default_factory=dict)


class WeekFlowState(BaseModel):
    """Structured state for week outer orchestration."""

    athlete_id: str = ""
    run_id: str = ""
    target_iso_week: str = ""
    target_week: str = ""
    preview_only: bool = False
    loaded_input_refs: JsonMap = Field(default_factory=dict)
    deterministic_context_refs: JsonMap = Field(default_factory=dict)
    produced_artifact_refs: JsonMap = Field(default_factory=dict)
    review_decisions: JsonMap = Field(default_factory=dict)
    failure_reason: str = ""
    source_versions: JsonMap = Field(default_factory=dict)
    loaded_inputs_summary: JsonMap = Field(default_factory=dict)
    candidate_week_plan: JsonMap = Field(default_factory=dict)
    normalization_summary: JsonMap = Field(default_factory=dict)
    diff_summary: JsonMap = Field(default_factory=dict)
    persistence_summary: JsonMap = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    result: JsonMap = Field(default_factory=dict)


class ReportFlowState(BaseModel):
    """Structured state for report outer orchestration."""

    athlete_id: str = ""
    run_id: str = ""
    target_iso_week: str = ""
    target_week: str = ""
    loaded_input_refs: JsonMap = Field(default_factory=dict)
    deterministic_context_refs: JsonMap = Field(default_factory=dict)
    produced_artifact_refs: JsonMap = Field(default_factory=dict)
    review_decisions: JsonMap = Field(default_factory=dict)
    failure_reason: str = ""
    source_versions: JsonMap = Field(default_factory=dict)
    persistence_summary: JsonMap = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    result: JsonMap = Field(default_factory=dict)


class FeedForwardFlowState(BaseModel):
    """Structured state for advisory chain orchestration."""

    athlete_id: str = ""
    run_id: str = ""
    target_iso_week: str = ""
    target_week: str = ""
    loaded_input_refs: JsonMap = Field(default_factory=dict)
    deterministic_context_refs: JsonMap = Field(default_factory=dict)
    produced_artifact_refs: JsonMap = Field(default_factory=dict)
    review_decisions: JsonMap = Field(default_factory=dict)
    failure_reason: str = ""
    source_versions: JsonMap = Field(default_factory=dict)
    report_result: JsonMap = Field(default_factory=dict)
    season_phase_result: JsonMap = Field(default_factory=dict)
    phase_result: JsonMap = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class CoachFlowState(BaseModel):
    """Structured state for one coach turn."""

    athlete_id: str = ""
    run_id: str = ""
    target_iso_week: str = ""
    user_message: str = ""
    route: str = ""
    loaded_input_refs: JsonMap = Field(default_factory=dict)
    deterministic_context_refs: JsonMap = Field(default_factory=dict)
    produced_artifact_refs: JsonMap = Field(default_factory=dict)
    review_decisions: JsonMap = Field(default_factory=dict)
    failure_reason: str = ""
    pending_summary: JsonMap = Field(default_factory=dict)
    recalled_memory_summary: list[str] = Field(default_factory=list)
    stored_memory_summary: list[str] = Field(default_factory=list)
    response: str = ""


def _extract_stage_summary(result: JsonMap) -> JsonMap:
    """Build a compact flow-stage summary from a backend result payload."""

    summary: JsonMap = {"ok": bool(result.get("ok"))}
    for key in ("warnings", "details", "error"):
        value = result.get(key)
        if value:
            summary[key] = value
    produced = result.get("produced")
    if isinstance(produced, dict):
        summary["produced_keys"] = sorted(str(key) for key in produced)
    document = result.get("document")
    if isinstance(document, dict):
        meta = document.get("meta")
        if isinstance(meta, dict):
            summary["artifact_type"] = meta.get("artifact_type")
    return summary


def _ensure_state_list(state: Any, name: str) -> list[Any]:
    """Return a mutable list attribute on flow state, creating it when absent."""

    value = getattr(state, name, None)
    if not isinstance(value, list):
        value = []
        setattr(state, name, value)
    return value


def _ensure_state_dict(state: Any, name: str) -> JsonMap:
    """Return a mutable dict attribute on flow state, creating it when absent."""

    value = getattr(state, name, None)
    if not isinstance(value, dict):
        value = {}
        setattr(state, name, value)
    return value


def _load_flow_symbols() -> tuple[Any, Any, Any, Any, Any]:
    """Load CrewAI Flow primitives lazily for runtime-safe imports."""

    flow_module = import_module("crewai.flow.flow")
    Flow = getattr(flow_module, "Flow")
    start = getattr(flow_module, "start")
    listen = getattr(flow_module, "listen")
    router = getattr(flow_module, "router")
    try:
        persist_module = import_module("crewai.flow.persistence")
    except Exception:
        persist = None
    else:
        persist = getattr(persist_module, "persist", None)
    return Flow, start, listen, router, persist


def _flow_should_persist(flow_name: str) -> bool:
    bundle = load_crewai_config_bundle(root=Path.cwd())
    flow_cfg = (bundle.flow_persistence.get("flows") or {}).get(flow_name) or {}
    return bool(flow_cfg.get("persist", False))


def _decorate_persist(flow_cls: type[Any], flow_name: str, persist_decorator: Any | None) -> type[Any]:
    if not _flow_should_persist(flow_name) or persist_decorator is None:
        return flow_cls

    # CrewAI has documented both `@persist` and `@persist()` styles across
    # versions/examples. Try the decorator-factory form first because a direct
    # call can otherwise return the inner decorator function and break flow
    # instantiation at runtime.
    try:
        decorator = persist_decorator()
    except TypeError:
        decorator = None
    else:
        if callable(decorator):
            try:
                decorated = decorator(flow_cls)
            except TypeError:
                decorated = None
            else:
                if isinstance(decorated, type):
                    return decorated

    try:
        decorated = persist_decorator(flow_cls)
    except TypeError:
        return flow_cls
    return decorated if isinstance(decorated, type) else flow_cls


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
    workspace_root: Path | None = None,
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

    Flow, start, listen, router, persist = _load_flow_symbols()

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
            self.state.persistence_summary = {"task": AgentTask.CREATE_SEASON_SCENARIOS.value, "persisted": True}
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
            self.state.persistence_summary = {"task": AgentTask.CREATE_SEASON_SCENARIO_SELECTION.value, "persisted": True}
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
            _ensure_state_list(self.state, "intermediate_summaries").append(
                "season planning/review/writer cycle executed"
            )
            self.state.normalization_summary = _extract_stage_summary(self.state.result)
            self.state.persistence_summary = {
                "task": AgentTask.CREATE_SEASON_PLAN.value,
                "stages": ["planning", "review", "writer"],
                "persisted": bool(self.state.result.get("ok")),
            }
            if self.state.result.get("warnings"):
                _ensure_state_list(self.state, "warnings").extend(
                    str(item) for item in self.state.result.get("warnings") or []
                )
            if not self.state.result.get("ok") and self.state.result.get("error"):
                self.state.failure_reason = str(self.state.result.get("error"))
                _ensure_state_list(self.state, "errors").append(self.state.failure_reason)
            return self.state.result

    SeasonOuterFlow = _decorate_persist(SeasonOuterFlow, "season", persist)
    flow = SeasonOuterFlow()
    flow.state.athlete_id = athlete_id
    flow.state.run_id = run_id
    flow.state.action = action
    if workspace_root is not None:
        with runtime_event_scope(root=workspace_root, athlete_id=athlete_id, run_id=run_id, component="season_flow"):
            flow.kickoff()
    else:
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
    workspace_root: Path | None = None,
) -> JsonMap:
    """Execute the outer Phase chain through one CrewAI Flow-backed bundle run."""

    if not tasks:
        return {"ok": True, "produced": {}}

    Flow, start, listen, _router, persist = _load_flow_symbols()

    class PhaseOuterFlow(Flow[PhaseFlowState]):
        @start()
        def bootstrap(self) -> list[str]:
            return list(self.state.requested_tasks)

        @listen(bootstrap)
        def run_planning_cycle(self, _requested_tasks: list[str]) -> JsonMap:
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
            self.state.bundle_summary = _extract_stage_summary(self.state.result)
            return self.state.result

        @listen(run_planning_cycle)
        def record_review(self, _result: JsonMap) -> JsonMap:
            _ensure_state_dict(self.state, "source_versions")["review_stage"] = (
                "phase multi-crew backend review completed"
            )
            return self.state.result

        @listen(record_review)
        def record_writer(self, _result: JsonMap) -> JsonMap:
            self.state.persistence_summary = {
                "tasks": list(self.state.requested_tasks),
                "stages": ["planning", "review", "writer"],
                "persisted": bool(self.state.result.get("ok")),
            }
            if self.state.result.get("warnings"):
                _ensure_state_list(self.state, "warnings").extend(
                    str(item) for item in self.state.result.get("warnings") or []
                )
            if not self.state.result.get("ok") and self.state.result.get("error"):
                self.state.failure_reason = str(self.state.result.get("error"))
                _ensure_state_list(self.state, "errors").append(self.state.failure_reason)
            return self.state.result

    PhaseOuterFlow = _decorate_persist(PhaseOuterFlow, "phase", persist)
    flow = PhaseOuterFlow()
    flow.state.athlete_id = athlete_id
    flow.state.run_id = run_id
    flow.state.requested_tasks = [task.value for task in tasks]
    if workspace_root is not None:
        with runtime_event_scope(root=workspace_root, athlete_id=athlete_id, run_id=run_id, component="phase_flow"):
            flow.kickoff()
    else:
        flow.kickoff()
    return dict(flow.state.result)


def run_week_flow(
    *,
    runtime_for: Callable[[str], AgentRuntime],
    agent_name: str,
    athlete_id: str,
    tasks: list[AgentTask],
    user_input: str,
    run_id: str,
    model_override: str | None = None,
    temperature_override: float | None = None,
    force_file_search: bool = True,
    max_num_results: int = 20,
    workspace_root: Path | None = None,
    preview_only: bool = False,
) -> JsonMap:
    """Execute the outer Week chain through a CrewAI Flow wrapper."""

    Flow, start, listen, _router, persist = _load_flow_symbols()

    class WeekOuterFlow(Flow[WeekFlowState]):
        @start()
        def bootstrap(self) -> str:
            return "week_plan"

        @listen(bootstrap)
        def run_planning_cycle(self, _label: str) -> JsonMap:
            runner = run_agent_multi_output_preview if preview_only else run_agent_multi_output
            self.state.result = runner(
                runtime_for(agent_name),
                agent_name=agent_name,
                agent_vs_name="vs_rps_all_agents",
                athlete_id=athlete_id,
                tasks=tasks,
                user_input=user_input,
                run_id=run_id,
                model_override=model_override,
                temperature_override=temperature_override,
                force_file_search=force_file_search,
                max_num_results=max_num_results,
            )
            self.state.preview_only = preview_only
            self.state.candidate_week_plan = _extract_stage_summary(self.state.result)
            return self.state.result

        @listen(run_planning_cycle)
        def record_review(self, _result: JsonMap) -> JsonMap:
            self.state.diff_summary = {
                "stages": ["planning", "review"] if preview_only else ["planning", "review", "writer"],
                "preview_only": preview_only,
            }
            return self.state.result

        @listen(record_review)
        def record_writer(self, _result: JsonMap) -> JsonMap:
            self.state.persistence_summary = {
                "persisted": bool(self.state.result.get("ok")) and not preview_only,
                "preview_only": preview_only,
            }
            if self.state.result.get("warnings"):
                _ensure_state_list(self.state, "warnings").extend(
                    str(item) for item in self.state.result.get("warnings") or []
                )
            if not self.state.result.get("ok") and self.state.result.get("error"):
                self.state.failure_reason = str(self.state.result.get("error"))
                _ensure_state_list(self.state, "errors").append(self.state.failure_reason)
            return self.state.result

    WeekOuterFlow = _decorate_persist(WeekOuterFlow, "week", persist)
    flow = WeekOuterFlow()
    flow.state.athlete_id = athlete_id
    flow.state.run_id = run_id
    flow.state.preview_only = preview_only
    if workspace_root is not None:
        with runtime_event_scope(root=workspace_root, athlete_id=athlete_id, run_id=run_id, component="week_flow"):
            flow.kickoff()
    else:
        flow.kickoff()
    return dict(flow.state.result)


def run_report_flow(
    report_runner: Callable[[], JsonMap],
    *,
    workspace_root: Path | None = None,
    athlete_id: str | None = None,
    run_id: str | None = None,
) -> JsonMap:
    """Execute report generation through a CrewAI Flow wrapper."""

    Flow, start, listen, _router, persist = _load_flow_symbols()

    class ReportOuterFlow(Flow[ReportFlowState]):
        @start()
        def bootstrap(self) -> str:
            return "report"

        @listen(bootstrap)
        def run_planning_cycle(self, _label: str) -> JsonMap:
            self.state.result = report_runner()
            _ensure_state_dict(self.state, "source_versions")["planning_stage"] = "report planning executed"
            return self.state.result

        @listen(run_planning_cycle)
        def record_review(self, _result: JsonMap) -> JsonMap:
            _ensure_state_dict(self.state, "source_versions")["review_stage"] = "report review executed"
            return self.state.result

        @listen(record_review)
        def record_writer(self, _result: JsonMap) -> JsonMap:
            self.state.persistence_summary = {
                "stages": ["planning", "review", "writer"],
                "persisted": bool(self.state.result.get("ok")),
            }
            if self.state.result.get("warnings"):
                _ensure_state_list(self.state, "warnings").extend(
                    str(item) for item in self.state.result.get("warnings") or []
                )
            if not self.state.result.get("ok") and self.state.result.get("error"):
                self.state.failure_reason = str(self.state.result.get("error"))
                _ensure_state_list(self.state, "errors").append(self.state.failure_reason)
            return self.state.result

    ReportOuterFlow = _decorate_persist(ReportOuterFlow, "report", persist)
    flow = ReportOuterFlow()
    flow.state.athlete_id = athlete_id or ""
    flow.state.run_id = run_id or ""
    if workspace_root is not None and athlete_id and run_id:
        with runtime_event_scope(root=workspace_root, athlete_id=athlete_id, run_id=run_id, component="report_flow"):
            flow.kickoff()
    else:
        flow.kickoff()
    return dict(flow.state.result)


def run_feed_forward_flow(
    *,
    report_runner: Callable[[], JsonMap],
    season_phase_runner: Callable[[], JsonMap],
    phase_runner: Callable[[], JsonMap],
    workspace_root: Path | None = None,
    athlete_id: str | None = None,
    run_id: str | None = None,
) -> dict[str, JsonMap]:
    """Execute report -> season delta -> phase delta through a CrewAI Flow wrapper."""

    Flow, start, listen, _router, persist = _load_flow_symbols()

    class FeedForwardOuterFlow(Flow[FeedForwardFlowState]):
        @start()
        def bootstrap(self) -> str:
            return "report"

        @listen(bootstrap)
        def run_report(self, _label: str) -> JsonMap:
            self.state.report_result = report_runner()
            return self.state.report_result

        @listen(run_report)
        def run_season_phase(self, _report_result: JsonMap) -> JsonMap:
            if not self.state.report_result.get("ok"):
                self.state.season_phase_result = {"ok": False, "skipped": True}
                return self.state.season_phase_result
            self.state.season_phase_result = season_phase_runner()
            return self.state.season_phase_result

        @listen(run_season_phase)
        def run_phase(self, _season_phase_result: JsonMap) -> JsonMap:
            if not self.state.season_phase_result.get("ok"):
                self.state.phase_result = {"ok": False, "skipped": True}
                return self.state.phase_result
            self.state.phase_result = phase_runner()
            return self.state.phase_result

    FeedForwardOuterFlow = _decorate_persist(FeedForwardOuterFlow, "feed_forward", persist)
    flow = FeedForwardOuterFlow()
    flow.state.athlete_id = athlete_id or ""
    flow.state.run_id = run_id or ""
    if workspace_root is not None and athlete_id and run_id:
        with runtime_event_scope(root=workspace_root, athlete_id=athlete_id, run_id=run_id, component="feed_forward_flow"):
            flow.kickoff()
    else:
        flow.kickoff()
    return {
        "report_result": dict(flow.state.report_result),
        "season_phase_result": dict(flow.state.season_phase_result),
        "phase_result": dict(flow.state.phase_result),
    }


def run_coach_flow(
    *,
    workspace_root: Path,
    athlete_id: str,
    run_id: str,
    user_message: str,
    chat_runner: Callable[[], str],
) -> dict[str, str]:
    """Run one conversational coach turn through a simple Flow wrapper."""

    Flow, start, listen, router, _persist = _load_flow_symbols()

    class CoachOuterFlow(Flow[CoachFlowState]):
        @start()
        def bootstrap(self) -> str:
            self.state.user_message = user_message
            return self.state.user_message

        @router(bootstrap)
        def route_turn(self, _message: str) -> str:
            route_name = "conversational_turn"
            self.state.route = route_name
            emit_runtime_event(
                root=workspace_root,
                athlete_id=athlete_id,
                run_id=run_id,
                event_type="FLOW_ROUTED",
                flow="coach",
                route=route_name,
            )
            return route_name

        @listen("conversational_turn")
        def run_chat_turn(self) -> str:
            self.state.response = chat_runner()
            return self.state.response

    flow = CoachOuterFlow()
    flow.state.athlete_id = athlete_id
    flow.state.run_id = run_id
    with runtime_event_scope(root=workspace_root, athlete_id=athlete_id, run_id=run_id, component="coach_flow"):
        flow.kickoff()
    return {"route": flow.state.route, "response": flow.state.response}
