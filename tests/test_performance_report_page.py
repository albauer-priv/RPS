from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from rps.agents.tasks import AgentTask
from rps.orchestrator.plan_week import create_performance_report
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("ATHLETE_ID", "test_athlete")
    monkeypatch.setenv("ATHLETE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RPS_DISABLE_INTERVALS_REFRESH", "1")


def test_create_performance_report_does_not_require_phase_artefacts(monkeypatch, tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)

    season_plan = {
        "meta": {
            "artifact_type": "SEASON_PLAN",
            "schema_id": "SeasonPlanInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "Season-Planner",
            "run_id": "season_plan_test",
            "created_at": "2026-04-01T00:00:00Z",
            "scope": "Season",
            "iso_week": "2026-14",
            "iso_week_range": "2026-14--2026-20",
            "temporal_scope": {"from": "2026-03-30", "to": "2026-05-17"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {
            "phases": [
                {
                    "phase_id": "P02",
                    "phase_name": "Build 1",
                    "phase_type": "Build",
                    "iso_week_range": "2026-14--2026-16",
                }
            ]
        },
    }
    generic_input = {
        "meta": {
            "artifact_type": "TEST",
            "schema_id": "TestInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "User",
            "run_id": "input_test",
            "created_at": "2026-04-10T00:00:00Z",
            "scope": "Shared",
            "iso_week": "2026-15",
            "iso_week_range": "2026-15--2026-15",
            "temporal_scope": {"from": "2026-04-06", "to": "2026-04-12"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {},
    }

    for artifact_type, version_key, document in (
        (ArtifactType.SEASON_PLAN, "2026-14--2026-20", season_plan),
        (ArtifactType.ACTIVITIES_ACTUAL, "2026-15", generic_input),
        (ArtifactType.ACTIVITIES_TREND, "2026-15", generic_input),
        (ArtifactType.KPI_PROFILE, "sample_profile", generic_input),
        (ArtifactType.PLANNING_EVENTS, "2026-15", generic_input),
        (ArtifactType.LOGISTICS, "2026-15", generic_input),
    ):
        store.save_document(
            athlete_id,
            artifact_type,
            version_key,
            document,
            producer_agent="test",
            run_id=f"store_{artifact_type.value.lower()}",
            update_latest=True,
        )
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_ACTUAL,
        "2026-14",
        generic_input,
        producer_agent="test",
        run_id="store_activities_actual_202614",
        update_latest=False,
    )
    store.save_document(
        athlete_id,
        ArtifactType.ACTIVITIES_TREND,
        "2026-14",
        generic_input,
        producer_agent="test",
        run_id="store_activities_trend_202614",
        update_latest=False,
    )

    captured: dict[str, object] = {}

    def _fake_run_agent_multi_output(runtime, **kwargs):
        captured["runtime"] = runtime
        captured["kwargs"] = kwargs
        return {"ok": True, "produced": {"store_des_analysis_report": {"path": "dummy"}}}

    monkeypatch.setattr("rps.orchestrator.plan_week.run_agent_multi_output", _fake_run_agent_multi_output)

    runtime = SimpleNamespace(workspace_root=tmp_path)
    result = create_performance_report(
        lambda _agent_name: runtime,
        athlete_id=athlete_id,
        report_week=SimpleNamespace(year=2026, week=15),
        run_id_prefix="report_ui",
    )

    assert result["ok"] is True
    assert captured["kwargs"]["tasks"] == [AgentTask.CREATE_DES_ANALYSIS_REPORT]
    user_input = captured["kwargs"]["user_input"]
    assert "ACTIVITIES_ACTUAL version_key 2026-15" in user_input
    assert "ACTIVITIES_TREND version_key 2026-15" in user_input
    assert "**Deterministic Report Evidence Context**" in user_input
    assert "diagnostic_only: True" in user_input



def test_create_performance_report_skips_when_context_inputs_missing(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)

    season_plan = {
        "meta": {
            "artifact_type": "SEASON_PLAN",
            "schema_id": "SeasonPlanInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "Season-Planner",
            "run_id": "season_plan_test",
            "created_at": "2026-04-01T00:00:00Z",
            "scope": "Season",
            "iso_week": "2026-14",
            "iso_week_range": "2026-14--2026-20",
            "temporal_scope": {"from": "2026-03-30", "to": "2026-05-17"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {"phases": []},
    }
    generic_input = {
        "meta": {
            "artifact_type": "TEST",
            "schema_id": "TestInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "User",
            "run_id": "input_test",
            "created_at": "2026-04-10T00:00:00Z",
            "scope": "Shared",
            "iso_week": "2026-15",
            "iso_week_range": "2026-15--2026-15",
            "temporal_scope": {"from": "2026-04-06", "to": "2026-04-12"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {},
    }

    for artifact_type, version_key, document in (
        (ArtifactType.SEASON_PLAN, "2026-14--2026-20", season_plan),
        (ArtifactType.ACTIVITIES_ACTUAL, "2026-15", generic_input),
        (ArtifactType.ACTIVITIES_TREND, "2026-15", generic_input),
        (ArtifactType.KPI_PROFILE, "sample_profile", generic_input),
    ):
        store.save_document(
            athlete_id,
            artifact_type,
            version_key,
            document,
            producer_agent="test",
            run_id=f"store_{artifact_type.value.lower()}",
            update_latest=True,
        )

    runtime = SimpleNamespace(workspace_root=tmp_path)
    result = create_performance_report(
        lambda _agent_name: runtime,
        athlete_id=athlete_id,
        report_week=SimpleNamespace(year=2026, week=15),
        run_id_prefix="report_ui",
    )

    assert result["ok"] is False
    assert "planning_events" in result["message"]
    assert "logistics" in result["message"]



def test_create_performance_report_backfills_target_week_activity_versions(monkeypatch, tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)

    season_plan = {
        "meta": {
            "artifact_type": "SEASON_PLAN",
            "schema_id": "SeasonPlanInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "Season-Planner",
            "run_id": "season_plan_test",
            "created_at": "2026-04-01T00:00:00Z",
            "scope": "Season",
            "iso_week": "2026-14",
            "iso_week_range": "2026-14--2026-20",
            "temporal_scope": {"from": "2026-03-30", "to": "2026-05-17"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {"phases": []},
    }
    generic_input = {
        "meta": {
            "artifact_type": "TEST",
            "schema_id": "TestInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "User",
            "run_id": "input_test",
            "created_at": "2026-04-10T00:00:00Z",
            "scope": "Shared",
            "iso_week": "2026-15",
            "iso_week_range": "2026-15--2026-15",
            "temporal_scope": {"from": "2026-04-06", "to": "2026-04-12"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {},
    }

    for artifact_type, version_key, document in (
        (ArtifactType.SEASON_PLAN, "2026-14--2026-20", season_plan),
        (ArtifactType.ACTIVITIES_ACTUAL, "2026-15", generic_input),
        (ArtifactType.ACTIVITIES_TREND, "2026-15", generic_input),
        (ArtifactType.KPI_PROFILE, "sample_profile", generic_input),
        (ArtifactType.PLANNING_EVENTS, "2026-15", generic_input),
        (ArtifactType.LOGISTICS, "2026-15", generic_input),
    ):
        store.save_document(
            athlete_id,
            artifact_type,
            version_key,
            document,
            producer_agent="test",
            run_id=f"store_{artifact_type.value.lower()}",
            update_latest=True,
        )

    def _fake_refresh(args, logger=None):
        store.save_document(
            athlete_id,
            ArtifactType.ACTIVITIES_ACTUAL,
            "2026-14",
            generic_input,
            producer_agent="test",
            run_id="backfill_activities_actual_202614",
            update_latest=False,
        )
        store.save_document(
            athlete_id,
            ArtifactType.ACTIVITIES_TREND,
            "2026-14",
            generic_input,
            producer_agent="test",
            run_id="backfill_activities_trend_202614",
            update_latest=False,
        )
        return 0

    captured: dict[str, object] = {}

    def _fake_run_agent_multi_output(runtime, **kwargs):
        captured["kwargs"] = kwargs
        return {"ok": True, "produced": {"store_des_analysis_report": {"path": "dummy"}}}

    monkeypatch.setattr("rps.orchestrator.plan_week.run_intervals_pipeline", _fake_refresh)
    monkeypatch.setattr("rps.orchestrator.plan_week.run_agent_multi_output", _fake_run_agent_multi_output)

    runtime = SimpleNamespace(workspace_root=tmp_path)
    result = create_performance_report(
        lambda _agent_name: runtime,
        athlete_id=athlete_id,
        report_week=SimpleNamespace(year=2026, week=14),
        run_id_prefix="report_ui",
    )

    assert result["ok"] is True
    user_input = captured["kwargs"]["user_input"]
    assert "ACTIVITIES_ACTUAL version_key 2026-14" in user_input
    assert "ACTIVITIES_TREND version_key 2026-14" in user_input



def test_create_performance_report_skips_when_target_week_activity_versions_missing(monkeypatch, tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)

    season_plan = {
        "meta": {
            "artifact_type": "SEASON_PLAN",
            "schema_id": "SeasonPlanInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "Season-Planner",
            "run_id": "season_plan_test",
            "created_at": "2026-04-01T00:00:00Z",
            "scope": "Season",
            "iso_week": "2026-14",
            "iso_week_range": "2026-14--2026-20",
            "temporal_scope": {"from": "2026-03-30", "to": "2026-05-17"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {"phases": []},
    }
    generic_input = {
        "meta": {
            "artifact_type": "TEST",
            "schema_id": "TestInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": "Binding",
            "owner_agent": "User",
            "run_id": "input_test",
            "created_at": "2026-04-10T00:00:00Z",
            "scope": "Shared",
            "iso_week": "2026-15",
            "iso_week_range": "2026-15--2026-15",
            "temporal_scope": {"from": "2026-04-06", "to": "2026-04-12"},
            "trace_upstream": [],
            "trace_data": [],
            "trace_events": [],
            "data_confidence": "UNKNOWN",
            "notes": "",
        },
        "data": {},
    }

    for artifact_type, version_key, document in (
        (ArtifactType.SEASON_PLAN, "2026-14--2026-20", season_plan),
        (ArtifactType.ACTIVITIES_ACTUAL, "2026-15", generic_input),
        (ArtifactType.ACTIVITIES_TREND, "2026-15", generic_input),
        (ArtifactType.KPI_PROFILE, "sample_profile", generic_input),
        (ArtifactType.PLANNING_EVENTS, "2026-15", generic_input),
        (ArtifactType.LOGISTICS, "2026-15", generic_input),
    ):
        store.save_document(
            athlete_id,
            artifact_type,
            version_key,
            document,
            producer_agent="test",
            run_id=f"store_{artifact_type.value.lower()}",
            update_latest=True,
        )

    monkeypatch.setattr("rps.orchestrator.plan_week.run_intervals_pipeline", lambda *args, **kwargs: 0)

    runtime = SimpleNamespace(workspace_root=tmp_path)
    result = create_performance_report(
        lambda _agent_name: runtime,
        athlete_id=athlete_id,
        report_week=SimpleNamespace(year=2026, week=14),
        run_id_prefix="report_ui",
    )

    assert result["ok"] is False
    assert "ACTIVITIES_ACTUAL" in result["message"]
    assert "ACTIVITIES_TREND" in result["message"]



def test_performance_report_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/performance/report.py")
    at.run(timeout=10)
    assert len(at.error) == 0



def test_performance_report_page_shows_single_active_job_message():
    from rps.ui.shared import get_iso_year_week

    year, week = get_iso_year_week()
    at = AppTest.from_file("src/rps/ui/pages/performance/report.py")
    at.session_state[f"report_job_test_athlete_{year:04d}{week:02d}"] = {
        "thread": None,
        "status": "running",
        "message": "Creating performance report...",
        "reasonings": [],
        "logs": [],
        "result": None,
        "run_id": "test-report-run",
    }
    at.run(timeout=10)

    assert len(at.error) == 0
    creating_infos = [info for info in at.info if info.value == "Creating performance report..."]
    assert len(creating_infos) == 1



def test_data_metrics_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/performance/data_metrics.py")
    at.run(timeout=10)
    assert len(at.error) == 0
    labels = [button.label for button in at.button]
    assert "Refresh Intervals Data" in labels
    slider_labels = [slider.label for slider in at.slider]
    assert "Show last N weeks (including current)" in slider_labels


