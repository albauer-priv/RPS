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
from rps.crewai_runtime.models import (
    ArtifactEnvelopeModel,
    CoachOperationApplyResultModel,
    CoachOperationPreviewModel,
)
from rps.orchestrator.coach_operations import (
    preview_feed_forward_operation,
    preview_report_operation,
    preview_scoped_week_replan_operation,
)
from rps.prompts.loader import PromptLoader


def test_crewai_config_bundle_loads_known_agents_and_tasks() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))

    agent_defs = bundle.agents["agents"]
    task_defs = bundle.tasks["tasks"]
    assert "coach" in agent_defs
    assert "week_planner" in agent_defs
    assert task_defs["coach_apply_scoped_replan"]["agent"] == "coach"
    assert task_defs["week_plan"]["agent"] == "week_planner"


def test_crewai_blueprints_build_from_yaml() -> None:
    bundle = load_crewai_config_bundle(root=Path("."))
    agents = build_agent_blueprints(bundle)
    tasks = build_task_blueprints(bundle)

    assert agents["coach"].goal
    assert tasks["coach_preview_artifact_edit"].output_kind == "coach_preview"
    assert tasks["week_plan"].output_kind == "artifact_envelope"


def test_output_model_registry_resolves_known_output_kinds() -> None:
    assert output_model_for_kind("artifact_envelope") is ArtifactEnvelopeModel
    assert output_model_for_kind("coach_preview") is CoachOperationPreviewModel
    assert output_model_for_kind("coach_apply") is CoachOperationApplyResultModel


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


def test_runtime_gateway_auto_falls_back_to_legacy_under_python_314(monkeypatch) -> None:
    monkeypatch.delenv("RPS_AGENT_RUNTIME", raising=False)
    selection = agent_runtime.resolve_agent_runtime_selection()

    assert selection.requested_backend == "auto"
    assert selection.effective_backend == "legacy"
    assert selection.can_execute is True
    assert selection.is_fallback is True


def test_runtime_gateway_respects_explicit_legacy_mode(monkeypatch) -> None:
    monkeypatch.setenv("RPS_AGENT_RUNTIME", "legacy")
    selection = agent_runtime.resolve_agent_runtime_selection()

    assert selection.requested_backend == "legacy"
    assert selection.effective_backend == "legacy"
    assert selection.can_execute is True
    assert selection.is_fallback is False


def test_runtime_gateway_blocks_explicit_crewai_when_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("RPS_AGENT_RUNTIME", "crewai")
    selection = agent_runtime.resolve_agent_runtime_selection()

    assert selection.requested_backend == "crewai"
    assert selection.effective_backend == "crewai"
    assert selection.can_execute is False
    assert "unavailable" in selection.reason.lower()


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
    monkeypatch.setattr(agent_runtime, "_run_agent_multi_output_crewai", _fake_backend)

    result = agent_runtime.run_agent_multi_output()
    assert result["ok"] is True
    assert marker["called"] is True


def test_run_agent_multi_output_crewai_persists_typed_output(monkeypatch) -> None:
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
                    "artifact_type": "SEASON_PLAN",
                    "schema_id": "SeasonPlanInterface",
                    "schema_version": "1.0",
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

    saved = {"ok": True, "path": "/tmp/out.json", "version_key": "2026-19__x", "run_id": "run-1"}

    def _fake_guard_put_validated(self, **kwargs):
        return saved

    monkeypatch.setattr(
        "rps.agents.crewai_backend.GuardedValidatedStore.guard_put_validated",
        _fake_guard_put_validated,
    )

    runtime = AgentRuntime(
        client=SimpleNamespace(
            config=SimpleNamespace(
                api_key="test-key",
                base_url="https://api.openai.com/v1",
                org_id=None,
                project_id=None,
            )
        ),
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
