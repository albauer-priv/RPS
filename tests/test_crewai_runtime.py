from __future__ import annotations

import sys
from pathlib import Path

from rps.agents import runtime as agent_runtime
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
        assert "Python 3.14" in status.message
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
