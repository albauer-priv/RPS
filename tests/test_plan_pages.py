import json
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("ATHLETE_ID", "test_athlete")
    monkeypatch.setenv("ATHLETE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RPS_DISABLE_INTERVALS_REFRESH", "1")


def test_season_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/plan/season.py")
    at.run()
    assert len(at.error) == 0
    assert len(at.text_input) >= 1
    assert all(button.label != "Create Scenarios" for button in at.button)


def test_season_page_handles_selection_error_state():
    at = AppTest.from_file("src/rps/ui/pages/plan/season.py")
    at.session_state["rps_state"] = {"season_selection_error_output": "error output"}
    at.run()
    assert len(at.error) == 0


def test_plan_hub_season_actions_expander(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    plan_path = store.latest_path("test_athlete", ArtifactType.SEASON_PLAN)
    plan_path.write_text(json.dumps({"meta": {"version_key": "test"}, "data": {"phases": []}}), encoding="utf-8")

    at = AppTest.from_file("src/rps/ui/pages/plan/hub.py")
    at.run(timeout=10)
    assert len(at.error) == 0
    labels = [expander.label for expander in at.expander]
    assert "Season Plan: Delete or Reset" in labels
    assert any("Build Workouts" in label for label in labels)
    assert all("Was wird alles erstellt:" not in info.value for info in at.info)
    # Run planning UI is hidden when readiness has blockers.
    info_text = "\n".join(info.value for info in at.info)
    assert "Resolve missing inputs/artifacts above" in info_text
    assert "Inputs missing" in info_text


def test_plan_hub_reset_delete_latest(tmp_path):
    from rps.ui.pages.plan import hub as plan_hub

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    for artifact_type in plan_hub.DELETE_LATEST_TYPES:
        path = store.latest_path("test_athlete", artifact_type)
        path.write_text("{}", encoding="utf-8")

    removed_delete = plan_hub._clear_latest_artifacts(store, "test_athlete", plan_hub.DELETE_LATEST_TYPES)
    assert removed_delete
    for artifact_type in plan_hub.DELETE_LATEST_TYPES:
        assert not store.latest_path("test_athlete", artifact_type).exists()

    for artifact_type in plan_hub.DELETE_LATEST_TYPES:
        path = store.latest_path("test_athlete", artifact_type)
        path.write_text("{}", encoding="utf-8")

    removed_reset = plan_hub._clear_latest_artifacts(store, "test_athlete", plan_hub.RESET_LATEST_TYPES)
    assert removed_reset
    for artifact_type in plan_hub.RESET_LATEST_TYPES:
        assert not store.latest_path("test_athlete", artifact_type).exists()
    assert store.latest_path("test_athlete", ArtifactType.SEASON_SCENARIOS).exists()
    assert store.latest_path("test_athlete", ArtifactType.SEASON_SCENARIO_SELECTION).exists()


def test_plan_hub_readiness_requires_latest_files(tmp_path):
    from rps.ui.pages.plan import hub as plan_hub
    from rps.workspace.index_manager import WorkspaceIndexManager

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")

    inputs_dir = tmp_path / "test_athlete" / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    (inputs_dir / "season_brief_2026.md").write_text("test", encoding="utf-8")
    (inputs_dir / "events_2026.md").write_text("test", encoding="utf-8")

    for artifact_type in (
        ArtifactType.KPI_PROFILE,
        ArtifactType.AVAILABILITY,
        ArtifactType.ZONE_MODEL,
        ArtifactType.WELLNESS,
        ArtifactType.SEASON_SCENARIOS,
        ArtifactType.SEASON_SCENARIO_SELECTION,
    ):
        path = store.latest_path("test_athlete", artifact_type)
        path.write_text("{}", encoding="utf-8")

    scenarios_key = "2026-05"
    scenarios_path = store.versioned_path("test_athlete", ArtifactType.SEASON_SCENARIOS, scenarios_key)
    scenarios_path.write_text("{}", encoding="utf-8")
    selection_key = "2026-05"
    selection_path = store.versioned_path("test_athlete", ArtifactType.SEASON_SCENARIO_SELECTION, selection_key)
    selection_path.write_text("{}", encoding="utf-8")

    version_key = "2026-05"
    version_path = store.versioned_path("test_athlete", ArtifactType.SEASON_PLAN, version_key)
    version_path.write_text("{}", encoding="utf-8")

    manager = WorkspaceIndexManager(root=tmp_path, athlete_id="test_athlete")
    index = {
        "athlete_id": "test_athlete",
        "updated_at": "2026-02-01T00:00:00Z",
        "artefacts": {
            ArtifactType.SEASON_SCENARIOS.value: {
                "latest": {
                    "version_key": scenarios_key,
                    "path": str(scenarios_path.relative_to(tmp_path / "test_athlete")),
                    "created_at": "2026-02-01T00:00:00Z",
                },
                "versions": {
                    scenarios_key: {
                        "version_key": scenarios_key,
                        "path": str(scenarios_path.relative_to(tmp_path / "test_athlete")),
                        "created_at": "2026-02-01T00:00:00Z",
                    }
                },
            },
            ArtifactType.SEASON_SCENARIO_SELECTION.value: {
                "latest": {
                    "version_key": selection_key,
                    "path": str(selection_path.relative_to(tmp_path / "test_athlete")),
                    "created_at": "2026-02-01T00:00:00Z",
                },
                "versions": {
                    selection_key: {
                        "version_key": selection_key,
                        "path": str(selection_path.relative_to(tmp_path / "test_athlete")),
                        "created_at": "2026-02-01T00:00:00Z",
                    }
                },
            },
            ArtifactType.SEASON_PLAN.value: {
                "latest": {
                    "version_key": version_key,
                    "path": str(version_path.relative_to(tmp_path / "test_athlete")),
                    "created_at": "2026-02-01T00:00:00Z",
                },
                "versions": {
                    version_key: {
                        "version_key": version_key,
                        "path": str(version_path.relative_to(tmp_path / "test_athlete")),
                        "created_at": "2026-02-01T00:00:00Z",
                    }
                },
            }
        },
    }
    manager.save(index)

    readiness = plan_hub._compute_readiness("test_athlete", 2026, 5)
    readiness_map = {step.key: step for step in readiness}
    assert readiness_map["season_plan"].status in {"missing", "blocked"}


def test_week_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/plan/week.py")
    at.run()
    assert len(at.error) == 0
    assert len(at.number_input) >= 2


def test_workouts_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/plan/workouts.py")
    at.run()
    assert len(at.error) == 0
    assert len(at.info) >= 1


def test_system_pages_render():
    status = AppTest.from_file("src/rps/ui/pages/system/status.py")
    status.run()
    assert len(status.error) == 0

    history = AppTest.from_file("src/rps/ui/pages/system/history.py")
    history.run()
    assert len(history.error) == 0

    log_page = AppTest.from_file("src/rps/ui/pages/system/log.py")
    log_page.run()
    assert len(log_page.error) == 0


def test_kpi_profile_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/athlete_profile/kpi_profile.py")
    at.run()
    assert len(at.error) == 0


def test_data_operations_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/athlete_profile/data_operations.py")
    at.run()
    assert len(at.error) == 0


def test_feed_forward_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/performance/feed_forward.py")
    at.run()
    assert len(at.error) == 0


def test_performance_report_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/performance/report.py")
    at.run()
    assert len(at.error) == 0


def test_data_metrics_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/performance/data_metrics.py")
    at.run(timeout=10)
    assert len(at.error) == 0
    labels = [button.label for button in at.button]
    assert "Refresh Intervals Data" in labels
    slider_labels = [slider.label for slider in at.slider]
    assert "Show last N weeks (including current)" in slider_labels


def test_availability_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/athlete_profile/availability.py")
    at.run()
    assert len(at.error) == 0
    labels = [button.label for button in at.button]
    assert "Parse Availability from Season Brief" in labels
