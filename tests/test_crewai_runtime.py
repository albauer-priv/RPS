from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

from rps.agents import runtime as agent_runtime
from rps.agents.crewai_backend import run_agent_multi_output_crewai
from rps.agents.runtime import AgentRuntime
from rps.agents.tasks import AgentTask
from rps.crewai_runtime import crewai_runtime_status, load_crewai_config_bundle
from rps.crewai_runtime.bindings import (
    build_agent_blueprints,
    build_task_blueprints,
    output_model_for_kind,
)
from rps.crewai_runtime.flows import run_phase_flow, run_season_flow
from rps.crewai_runtime.models import (
    ArtifactEnvelopeModel,
    CoachOperationApplyResultModel,
    CoachOperationPreviewModel,
    ConstraintAuditModel,
    LoadGovernanceAuditModel,
    PhaseBundleModel,
    SeasonEventAnchorModel,
    SeasonMacrocycleDraftModel,
    SeasonPlanAuditModel,
)
from rps.crewai_runtime.provider import build_crewai_llm_kwargs, resolve_crewai_provider_config
from rps.orchestrator.coach_operations import (
    preview_feed_forward_operation,
    preview_report_operation,
    preview_scoped_week_replan_operation,
)
from rps.prompts.loader import PromptLoader


def _install_fake_flow_module(monkeypatch) -> None:
    """Install a minimal CrewAI Flow module for unit tests."""

    flow_module = types.ModuleType("crewai.flow.flow")

    def start(*_args, **_kwargs):
        def _decorate(func):
            func._flow_start = True
            return func

        return _decorate

    def router(trigger):
        def _decorate(func):
            func._flow_router = trigger
            return func

        return _decorate

    def listen(trigger):
        def _decorate(func):
            func._flow_listen = trigger
            return func

        return _decorate

    class FakeFlow:
        @classmethod
        def __class_getitem__(cls, _item):
            return cls

        def __init__(self):
            self.state = SimpleNamespace(action="", result={}, requested_tasks=[])

        def kickoff(self):
            start_method = None
            router_method = None
            listeners: list[tuple[object, object]] = []
            for name in dir(self):
                candidate = getattr(self, name)
                func = getattr(type(self), name, None)
                if callable(candidate) and getattr(func, "_flow_start", False):
                    start_method = candidate
                if callable(candidate) and hasattr(func, "_flow_router"):
                    router_method = candidate
                if callable(candidate) and hasattr(func, "_flow_listen"):
                    listeners.append((getattr(func, "_flow_listen"), candidate))
            if start_method is None:
                raise AssertionError("FakeFlow requires a @start method")
            start_result = start_method()
            if router_method is not None:
                route_label = router_method(start_result)
                for trigger, listener_method in listeners:
                    if trigger == route_label:
                        return listener_method()
                return None
            for trigger, listener_method in listeners:
                trigger_name = getattr(trigger, "__name__", None)
                if trigger_name == getattr(start_method, "__name__", None):
                    return listener_method(start_result)
            return None

    flow_module.Flow = FakeFlow
    flow_module.start = start
    flow_module.listen = listen
    flow_module.router = router
    monkeypatch.setitem(sys.modules, "crewai.flow.flow", flow_module)


def test_crewai_config_bundle_loads_known_agents_and_tasks() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))

    agent_defs = bundle.agents["agents"]
    task_defs = bundle.tasks["tasks"]
    assert "coach" in agent_defs
    assert "week_planner" in agent_defs
    assert "season_planner_manager" in agent_defs
    assert "phase_architect_manager" in agent_defs
    assert task_defs["coach_apply_scoped_replan"]["agent"] == "coach"
    assert task_defs["week_plan"]["agent"] == "week_planner"
    assert task_defs["season_plan"]["agent"] == "season_planner_manager"
    assert task_defs["phase_guardrails"]["agent"] == "phase_architect_manager"


def test_crewai_blueprints_build_from_yaml() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    agents = build_agent_blueprints(bundle)
    tasks = build_task_blueprints(bundle)

    assert agents["coach"].goal
    assert agents["season_plan_auditor"].goal
    assert agents["season_plan_auditor"].config["prompt_agent"] == "season_plan_auditor"
    assert agents["guardrails_specialist"].config["prompt_agent"] == "guardrails_specialist"
    assert tasks["coach_preview_artifact_edit"].output_kind == "coach_preview"
    assert tasks["week_plan"].output_kind == "artifact_envelope"
    assert tasks["phase_bundle_finalize"].output_kind == "phase_bundle"


def test_output_model_registry_resolves_known_output_kinds() -> None:
    assert output_model_for_kind("artifact_envelope") is ArtifactEnvelopeModel
    assert output_model_for_kind("coach_preview") is CoachOperationPreviewModel
    assert output_model_for_kind("coach_apply") is CoachOperationApplyResultModel
    assert output_model_for_kind("season_event_anchor") is SeasonEventAnchorModel
    assert output_model_for_kind("season_macrocycle_draft") is SeasonMacrocycleDraftModel
    assert output_model_for_kind("season_plan_audit") is SeasonPlanAuditModel
    assert output_model_for_kind("constraint_audit") is ConstraintAuditModel
    assert output_model_for_kind("load_governance_audit") is LoadGovernanceAuditModel
    assert output_model_for_kind("phase_bundle") is PhaseBundleModel


def test_crewai_runtime_status_reports_python_compatibility() -> None:
    status = crewai_runtime_status()

    if sys.version_info >= (3, 14):
        assert status.python_supported is False
        assert status.ok is False
        assert "unsupported" in status.message.lower()
    else:
        assert status.python_supported is True


def test_preview_scoped_week_replan_requires_message() -> None:
    preview = preview_scoped_week_replan_operation(year=2026, week=19, message="")
    assert preview.ok is False
    assert preview.requires_confirmation is True
    assert preview.issues


def test_preview_report_and_feed_forward_operations_are_typed() -> None:
    report_preview = preview_report_operation(year=2026, week=19)
    feed_forward_preview = preview_feed_forward_operation(year=2026, week=19)

    assert report_preview.operation == "preview_report"
    assert report_preview.requires_confirmation is True
    assert "DES_ANALYSIS_REPORT" in report_preview.affected_artifacts

    assert feed_forward_preview.operation == "preview_feed_forward"
    assert feed_forward_preview.requires_confirmation is True
    assert "PHASE_FEED_FORWARD" in feed_forward_preview.affected_artifacts


def test_runtime_gateway_defaults_to_crewai(monkeypatch) -> None:
    monkeypatch.delenv("RPS_AGENT_RUNTIME", raising=False)
    selection = agent_runtime.resolve_agent_runtime_selection()

    assert selection.requested_backend == "crewai"
    assert selection.effective_backend == "crewai"
    assert selection.is_fallback is False


def test_runtime_gateway_rejects_unknown_backend(monkeypatch) -> None:
    monkeypatch.setenv("RPS_AGENT_RUNTIME", "legacy")
    selection = agent_runtime.resolve_agent_runtime_selection()

    assert selection.requested_backend == "crewai"
    assert selection.effective_backend == "crewai"


def test_runtime_gateway_dispatches_to_crewai_backend(monkeypatch) -> None:
    marker = {"called": False}

    def _fake_selection():
        return agent_runtime.AgentRuntimeSelection(
            requested_backend="crewai",
            effective_backend="crewai",
            can_execute=True,
            is_fallback=False,
            reason="ok",
            crewai_status=crewai_runtime_status(),
        )

    def _fake_backend(*args, **kwargs):
        marker["called"] = True
        return {"ok": True, "produced": {}}

    monkeypatch.setattr(agent_runtime, "resolve_agent_runtime_selection", _fake_selection)
    module = types.ModuleType("rps.agents.crewai_backend")
    module.run_agent_multi_output_crewai = _fake_backend
    monkeypatch.setitem(sys.modules, "rps.agents.crewai_backend", module)

    result = agent_runtime.run_agent_multi_output()
    assert result["ok"] is True
    assert marker["called"] is True


def test_run_agent_multi_output_crewai_persists_typed_output(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "openai/gpt-5-mini")
    fake_crewai = types.ModuleType("crewai")
    fake_tools = types.ModuleType("crewai.tools")

    class FakeLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.output_pydantic = kwargs["output_pydantic"]
            self.output = None

    class FakeCrew:
        def __init__(self, *, tasks, **kwargs):
            self.tasks = tasks
            self.kwargs = kwargs

        def kickoff(self):
            task = self.tasks[0]
            model_cls = task.output_pydantic
            if model_cls is ArtifactEnvelopeModel:
                model = model_cls(
                    meta={
                        "artifact_type": "SEASON_PLAN",
                        "schema_id": "SeasonPlanInterface",
                        "schema_version": "1.0",
                    },
                    data={},
                )
            else:
                model = model_cls()
            task.output = SimpleNamespace(pydantic=model, raw=model.model_dump_json())
            return task.output

    class FakeProcess:
        sequential = "sequential"

    def _tool(name: str):
        def _decorate(func):
            func.tool_name = name
            return func

        return _decorate

    fake_crewai.LLM = FakeLLM
    fake_crewai.Agent = FakeAgent
    fake_crewai.Task = FakeTask
    fake_crewai.Crew = FakeCrew
    fake_crewai.Process = FakeProcess
    fake_tools.tool = _tool

    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    monkeypatch.setitem(sys.modules, "crewai.tools", fake_tools)

    saved = {"ok": True, "path": "/tmp/out.json", "version_key": "2026-19__x", "run_id": "run-1"}

    def _fake_guard_put_validated(self, **kwargs):
        return saved

    monkeypatch.setattr(
        "rps.agents.crewai_backend.GuardedValidatedStore.guard_put_validated",
        _fake_guard_put_validated,
    )

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        vs_resolver=SimpleNamespace(id_for_store_name=lambda name: name),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_agent_multi_output_crewai(
        runtime,
        agent_name="season_planner",
        agent_vs_name="vs_rps_all_agents",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_SEASON_PLAN],
        user_input="Create the season plan.",
        run_id="run-1",
    )

    assert result["ok"] is True
    assert result["produced"]["store_season_plan"] == saved


def test_run_agent_multi_output_crewai_phase_bundle_split(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "openai/gpt-5-mini")
    fake_crewai = types.ModuleType("crewai")
    fake_tools = types.ModuleType("crewai.tools")

    class FakeLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.output_pydantic = kwargs["output_pydantic"]
            self.description = kwargs["description"]
            self.output = None

    class FakeCrew:
        def __init__(self, *, tasks, **kwargs):
            self.tasks = tasks
            self.kwargs = kwargs

        def kickoff(self):
            task = self.tasks[0]
            model_cls = task.output_pydantic
            if model_cls is PhaseBundleModel:
                model = model_cls(
                    phase_range="2026-17--2026-19",
                    phase_id="P01",
                    phase_type="Base",
                    cadence_source="season_plan",
                    guardrails={},
                    structure={},
                    preview={},
                    guardrails_document={
                        "meta": {
                            "artifact_type": "PHASE_GUARDRAILS",
                            "schema_id": "PhaseGuardrailsInterface",
                            "schema_version": "1.0",
                            "owner_agent": "Phase-Architect",
                        },
                        "data": {},
                    },
                    structure_document={
                        "meta": {
                            "artifact_type": "PHASE_STRUCTURE",
                            "schema_id": "PhaseStructureInterface",
                            "schema_version": "1.0",
                            "owner_agent": "Phase-Architect",
                        },
                        "data": {},
                    },
                    preview_document={
                        "meta": {
                            "artifact_type": "PHASE_PREVIEW",
                            "schema_id": "PhasePreviewInterface",
                            "schema_version": "1.0",
                            "owner_agent": "Phase-Architect",
                        },
                        "data": {},
                    },
                    constraint_audit={},
                    load_governance_audit={},
                    decision_summary={},
                )
            else:
                model = model_cls()
            task.output = SimpleNamespace(pydantic=model, raw=model.model_dump_json())
            return task.output

    class FakeProcess:
        sequential = "sequential"

    def _tool(name: str):
        def _decorate(func):
            func.tool_name = name
            return func

        return _decorate

    fake_crewai.LLM = FakeLLM
    fake_crewai.Agent = FakeAgent
    fake_crewai.Task = FakeTask
    fake_crewai.Crew = FakeCrew
    fake_crewai.Process = FakeProcess
    fake_tools.tool = _tool

    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    monkeypatch.setitem(sys.modules, "crewai.tools", fake_tools)

    captured: dict[str, object] = {}

    def _fake_guard_put_validated(self, **kwargs):
        captured.update(kwargs)
        return {"ok": True, "path": "/tmp/phase.json", "version_key": "2026-17__x", "run_id": "run-phase"}

    monkeypatch.setattr(
        "rps.agents.crewai_backend.GuardedValidatedStore.guard_put_validated",
        _fake_guard_put_validated,
    )

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        vs_resolver=SimpleNamespace(id_for_store_name=lambda name: name),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_agent_multi_output_crewai(
        runtime,
        agent_name="phase_architect",
        agent_vs_name="vs_rps_all_agents",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_PHASE_GUARDRAILS],
        user_input="Create phase guardrails.",
        run_id="run-phase",
    )

    assert result["ok"] is True
    document = captured["document"]
    assert isinstance(document, dict)
    meta = document["meta"]
    assert meta["artifact_type"] == "PHASE_GUARDRAILS"
    assert meta["owner_agent"] == "Phase-Architect"


def test_run_agent_multi_output_crewai_normalizes_feed_forward_owner(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "openai/gpt-5-mini")
    fake_crewai = types.ModuleType("crewai")
    fake_tools = types.ModuleType("crewai.tools")

    class FakeLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeAgent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeTask:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.output_pydantic = kwargs["output_pydantic"]
            self.output = None

    class FakeCrew:
        def __init__(self, *, tasks, **kwargs):
            self.tasks = tasks
            self.kwargs = kwargs

        def kickoff(self):
            task = self.tasks[0]
            model_cls = task.output_pydantic
            envelope = model_cls(
                meta={
                    "artifact_type": "SEASON_PHASE_FEED_FORWARD",
                    "schema_id": "SeasonPhaseFeedForwardInterface",
                    "schema_version": "1.0",
                    "owner_agent": "Performance-Analyst",
                },
                data={},
            )
            task.output = SimpleNamespace(pydantic=envelope, raw=envelope.model_dump_json())
            return task.output

    class FakeProcess:
        sequential = "sequential"

    def _tool(name: str):
        def _decorate(func):
            func.tool_name = name
            return func

        return _decorate

    fake_crewai.LLM = FakeLLM
    fake_crewai.Agent = FakeAgent
    fake_crewai.Task = FakeTask
    fake_crewai.Crew = FakeCrew
    fake_crewai.Process = FakeProcess
    fake_tools.tool = _tool

    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    monkeypatch.setitem(sys.modules, "crewai.tools", fake_tools)

    captured: dict[str, object] = {}

    def _fake_guard_put_validated(self, **kwargs):
        captured.update(kwargs)
        return {"ok": True, "path": "/tmp/out.json", "version_key": "2026-19__x", "run_id": "run-ff"}

    monkeypatch.setattr(
        "rps.agents.crewai_backend.GuardedValidatedStore.guard_put_validated",
        _fake_guard_put_validated,
    )

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        vs_resolver=SimpleNamespace(id_for_store_name=lambda name: name),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_agent_multi_output_crewai(
        runtime,
        agent_name="season_planner",
        agent_vs_name="vs_rps_all_agents",
        athlete_id="i150546",
        tasks=[AgentTask.CREATE_SEASON_PHASE_FEED_FORWARD],
        user_input="Create season-phase feed-forward.",
        run_id="run-ff",
    )

    assert result["ok"] is True
    document = captured["document"]
    assert isinstance(document, dict)
    meta = document["meta"]
    assert meta["owner_agent"] == "Season-Planner"


def test_run_season_flow_routes_to_requested_task(monkeypatch) -> None:
    _install_fake_flow_module(monkeypatch)

    captured: dict[str, object] = {}

    def _fake_run_agent_multi_output(*args, **kwargs):
        captured["task"] = kwargs["tasks"][0]
        return {"ok": True, "produced": {"store": {"run_id": kwargs["run_id"]}}}

    monkeypatch.setattr("rps.crewai_runtime.flows.run_agent_multi_output", _fake_run_agent_multi_output)

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        vs_resolver=SimpleNamespace(id_for_store_name=lambda name: name),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_season_flow(
        runtime_for=lambda _name: runtime,
        agent_name="season_planner",
        athlete_id="i150546",
        task=AgentTask.CREATE_SEASON_PLAN,
        user_input="Create season plan.",
        run_id="season-flow-run",
    )

    assert result["ok"] is True
    assert captured["task"] == AgentTask.CREATE_SEASON_PLAN


def test_run_phase_flow_executes_bundle_once(monkeypatch) -> None:
    _install_fake_flow_module(monkeypatch)
    marker = {"calls": 0}

    def _fake_run_phase_bundle_crewai(*args, **kwargs):
        marker["calls"] += 1
        return {"ok": True, "produced": {"store_phase_guardrails": {"run_id": kwargs["run_id"]}}}

    monkeypatch.setattr("rps.crewai_runtime.flows.run_phase_bundle_crewai", _fake_run_phase_bundle_crewai)

    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        vs_resolver=SimpleNamespace(id_for_store_name=lambda name: name),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )

    result = run_phase_flow(
        runtime,
        agent_name="phase_architect",
        athlete_id="i150546",
        tasks=[
            AgentTask.CREATE_PHASE_GUARDRAILS,
            AgentTask.CREATE_PHASE_STRUCTURE,
            AgentTask.CREATE_PHASE_PREVIEW,
        ],
        user_input="Create phase bundle.",
        run_id="phase-flow-run",
    )

    assert result["ok"] is True
    assert marker["calls"] == 1


def test_direct_crewai_provider_config_uses_env_without_litellm(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "global-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "openai/gpt-5-mini")
    monkeypatch.setenv("RPS_LLM_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("RPS_LLM_API_KEY_COACH", "coach-key")
    monkeypatch.setenv("RPS_LLM_MODEL_COACH", "openai/gpt-5-nano")

    config = resolve_crewai_provider_config("coach")
    kwargs = build_crewai_llm_kwargs("coach")

    assert config.api_key == "coach-key"
    assert config.model == "openai/gpt-5-nano"
    assert kwargs["api_key"] == "coach-key"
    assert kwargs["model"] == "openai/gpt-5-nano"
