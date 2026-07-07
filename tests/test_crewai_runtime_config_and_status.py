from __future__ import annotations

import sys
from pathlib import Path

from rps.agents.runtime import AgentRuntime
from rps.core.config import load_app_settings
from rps.crewai_runtime import crewai_runtime_status
from rps.crewai_runtime.bindings import (
    output_model_for_kind,
)
from rps.crewai_runtime.compat import crewai_runtime_status as compat_crewai_runtime_status
from rps.crewai_runtime.guardrails import (
    des_diagnostic_only,
)
from rps.crewai_runtime.models import (
    AdjustmentIntentModel,
    ArtifactEnvelopeModel,
    CoachingRecommendationModel,
    CoachOperationApplyResultModel,
    CoachOperationPreviewModel,
    ConstraintAuditModel,
    EvidenceCurationModel,
    LoadGovernanceAuditModel,
    PendingResolutionResultModel,
    PhaseBundleModel,
    PhaseDraftBundleModel,
    SeasonEventAnchorModel,
    SeasonMacrocycleDraftModel,
    SeasonPhaseBlueprintDraftOutputModel,
    SeasonPlanAuditModel,
    SeasonPlanDraftBundleModel,
    TurnModeModel,
    WeekContextAssessmentModel,
)
from rps.crewai_runtime.provider import (
    build_crewai_llm_kwargs,
    build_crewai_planning_llm_kwargs,
    resolve_crewai_planning_enabled,
    resolve_crewai_provider_config,
)
from rps.orchestrator.coach_operations import (
    preview_feed_forward_operation,
    preview_report_operation,
    preview_scoped_week_replan_operation,
)
from rps.prompts.loader import PromptLoader
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


def test_des_guardrail_rejects_non_diagnostic_recommendation() -> None:
    failed, message = des_diagnostic_only(
        {
            "meta": {"artifact_type": "DES_ANALYSIS_REPORT", "schema_id": "DESAnalysisReportInterface"},
            "data": {"recommendation": {"type": "intervention", "scope": "Week-Planner"}},
        }
    )

    assert failed is False
    assert "must remain advisory" in message

def test_output_model_registry_resolves_known_output_kinds() -> None:
    assert output_model_for_kind("turn_mode") is TurnModeModel
    assert output_model_for_kind("week_context_assessment") is WeekContextAssessmentModel
    assert output_model_for_kind("coaching_recommendation") is CoachingRecommendationModel
    assert output_model_for_kind("adjustment_intent") is AdjustmentIntentModel
    assert output_model_for_kind("pending_resolution_result") is PendingResolutionResultModel
    assert output_model_for_kind("artifact_envelope") is ArtifactEnvelopeModel
    assert output_model_for_kind("coach_preview") is CoachOperationPreviewModel
    assert output_model_for_kind("coach_apply") is CoachOperationApplyResultModel
    assert output_model_for_kind("season_event_anchor") is SeasonEventAnchorModel
    assert output_model_for_kind("season_macrocycle_draft") is SeasonMacrocycleDraftModel
    assert output_model_for_kind("season_phase_blueprint_draft") is SeasonPhaseBlueprintDraftOutputModel
    assert output_model_for_kind("season_plan_audit") is SeasonPlanAuditModel
    assert output_model_for_kind("season_plan_draft_bundle") is SeasonPlanDraftBundleModel
    assert output_model_for_kind("constraint_audit") is ConstraintAuditModel
    assert output_model_for_kind("load_governance_audit") is LoadGovernanceAuditModel
    assert output_model_for_kind("phase_bundle_draft") is PhaseDraftBundleModel
    assert output_model_for_kind("phase_bundle") is PhaseBundleModel
    assert output_model_for_kind("evidence_curation") is EvidenceCurationModel

def test_crewai_runtime_status_reports_python_compatibility() -> None:
    status = crewai_runtime_status()

    if sys.version_info >= (3, 14):
        assert status.python_supported is False
        assert status.ok is False
        assert "unsupported" in status.message.lower()
    else:
        assert status.python_supported is True

def test_crewai_runtime_status_compat_shim_matches_runtime_status_module() -> None:
    active = crewai_runtime_status()
    compat = compat_crewai_runtime_status()

    assert compat == active

def test_preview_scoped_week_replan_requires_message() -> None:
    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=Path("runtime/athletes"),
    )
    preview = preview_scoped_week_replan_operation(
        lambda _name: runtime,
        store=LocalArtifactStore(root=Path("runtime/athletes")),
        athlete_id="i150546",
        year=2026,
        week=19,
        message="",
        run_id="preview-run",
    )
    assert preview.ok is False
    assert preview.requires_confirmation is True
    assert preview.issues

def test_preview_scoped_week_replan_returns_true_preview_metadata(monkeypatch, tmp_path: Path) -> None:
    athlete_id = "i150546"
    store = LocalArtifactStore(root=tmp_path)
    runtime = AgentRuntime(
        model="openai/gpt-5-mini",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_summary="auto",
        max_completion_tokens=8000,
        prompt_loader=PromptLoader(Path("prompts")),
        schema_dir=Path("specs/schemas"),
        workspace_root=tmp_path,
    )
    base_document = {
        "meta": {
            "artifact_type": "WEEK_PLAN",
            "schema_id": "WeekPlanInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "test",
            "run_id": "base-run",
            "created_at": "2026-05-13T06:00:00Z",
            "scope": "Shared",
            "iso_week": "2026-19",
            "iso_week_range": "2026-19--2026-19",
            "temporal_scope": {"from": "2026-05-04", "to": "2026-05-10"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "HIGH",
            "notes": "test",
        },
        "data": {
            "agenda": [
                {
                    "day": "Tue",
                    "date": "2026-05-05",
                    "day_role": "ENDURANCE",
                    "planned_duration": "01:30",
                    "planned_kj": 900,
                    "workout_id": "w1",
                }
            ],
            "workouts": [
                {
                    "workout_id": "w1",
                    "title": "Aerobic Endurance",
                    "date": "2026-05-05",
                    "start": "18:00",
                    "duration": "01:30:00",
                }
            ],
        },
    }
    preview_document = {
        **base_document,
        "data": {
            "agenda": [
                {
                    "day": "Tue",
                    "date": "2026-05-05",
                    "day_role": "ENDURANCE",
                    "planned_duration": "01:10",
                    "planned_kj": 780,
                    "workout_id": "w1",
                }
            ],
            "workouts": [
                {
                    "workout_id": "w1",
                    "title": "Aerobic Endurance",
                    "date": "2026-05-05",
                    "start": "18:00",
                    "duration": "01:10:00",
                }
            ],
        },
    }
    store.save_document(
        athlete_id,
        ArtifactType.WEEK_PLAN,
        "2026-19",
        base_document,
        producer_agent="test",
        run_id="base-run",
        update_latest=True,
    )
    monkeypatch.setattr(
        "rps.orchestrator.coach_operations.preview_week_plan_revision",
        lambda *args, **kwargs: {"ok": True, "document": preview_document},
    )
    monkeypatch.setattr("rps.orchestrator.coach_operations.validate_document", lambda *args, **kwargs: None)

    preview = preview_scoped_week_replan_operation(
        lambda _name: runtime,
        store=store,
        athlete_id=athlete_id,
        year=2026,
        week=19,
        message="Reduce Tuesday slightly.",
        run_id="preview-run",
    )

    assert preview.ok is True
    assert preview.document == preview_document
    metadata = preview.metadata
    assert metadata["change_rows"]
    assert "| Date | Day | Workout | Before | After |" in metadata["change_table_markdown"]
    first_change = metadata["change_rows"][0]
    assert first_change["workout"] == "Aerobic Endurance"
    assert "Workout: Aerobic Endurance;" in first_change["before"]
    assert "Duration: 01:10:00;" in first_change["after"]
    assert "before.json" in metadata["diff_text"]

def test_preview_report_and_feed_forward_operations_are_typed() -> None:
    report_preview = preview_report_operation(year=2026, week=19)
    feed_forward_preview = preview_feed_forward_operation(year=2026, week=19)

    assert report_preview.operation == "preview_report"
    assert report_preview.requires_confirmation is True
    assert "DES_ANALYSIS_REPORT" in report_preview.affected_artifacts

    assert feed_forward_preview.operation == "preview_feed_forward"
    assert feed_forward_preview.requires_confirmation is True
    assert "PHASE_FEED_FORWARD" in feed_forward_preview.affected_artifacts

def test_direct_crewai_provider_config_uses_env_without_litellm(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "global-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "openai/gpt-5-mini")
    monkeypatch.setenv("RPS_LLM_BASE_URL", "https://api.openai.com/v1")

    config = resolve_crewai_provider_config("coach")
    kwargs = build_crewai_llm_kwargs("coach")

    assert config.api_key == "global-key"
    assert config.model == "openai/gpt-5-mini"
    assert kwargs["api_key"] == "global-key"
    assert kwargs["model"] == "openai/gpt-5-mini"

def test_app_settings_default_model_uses_gpt54_family(monkeypatch) -> None:
    monkeypatch.delenv("RPS_LLM_MODEL", raising=False)
    monkeypatch.delenv("RPS_LLM_BASE_URL", raising=False)

    settings = load_app_settings()

    assert settings.openai_model == "gpt-5.4-mini"

def test_planning_provider_overrides_and_app_settings(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "global-key")
    monkeypatch.setenv("RPS_LLM_BASE_URL", "https://api.openai.com/v1")

    assert resolve_crewai_planning_enabled("season_planning", default_enabled=True) is True
    planning_kwargs = build_crewai_planning_llm_kwargs(
        "season_planning",
        default_model="gpt-5.4",
    )
    assert planning_kwargs is not None
    assert planning_kwargs["model"] == "gpt-5.4"
    assert planning_kwargs["api_key"] == "global-key"

    settings = load_app_settings()
    assert settings.planning_enabled_for_crew("season_planning", True) is True
    assert settings.planning_model_for_crew("season_planning", "gpt-5.4") == "gpt-5.4"

def test_app_settings_ignore_agent_and_crew_scoped_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("RPS_LLM_API_KEY", "global-key")
    monkeypatch.setenv("RPS_LLM_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("RPS_LLM_MODEL_COACH", "gpt-5.4")
    monkeypatch.setenv("RPS_LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("RPS_LLM_TEMPERATURE_COACH", "0.9")
    monkeypatch.setenv("RPS_CREW_PLANNING_SEASON_PLANNING", "false")
    monkeypatch.setenv("RPS_CREW_PLANNING_LLM_SEASON_PLANNING", "gpt-5.4-nano")

    settings = load_app_settings()

    assert settings.model_for_agent("coach") == "gpt-5.4-mini"
    assert settings.temperature_for_agent("coach") == 0.2
    assert settings.planning_enabled_for_crew("season_planning", True) is True
    assert settings.planning_model_for_crew("season_planning", "gpt-5.4") == "gpt-5.4"
    provider = resolve_crewai_provider_config("coach")
    assert provider.model == "gpt-5.4-mini"
    assert provider.temperature == 0.2
