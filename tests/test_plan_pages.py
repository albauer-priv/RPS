import json

import pytest
from streamlit.testing.v1 import AppTest

from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("ATHLETE_ID", "test_athlete")
    monkeypatch.setenv("ATHLETE_WORKSPACE_ROOT", str(tmp_path))


def test_season_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/plan/season.py")
    at.run()
    assert len(at.error) == 0
    assert len(at.text_input) >= 1


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
    assert all("Was wird alles erstellt:" not in info.value for info in at.info)


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


def test_week_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/plan/week.py")
    at.run()
    assert len(at.error) == 0
    assert len(at.number_input) >= 2
    labels = [button.label for button in at.button]
    assert "Post to Intervals" in labels


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


def test_feed_forward_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/performance/feed_forward.py")
    at.run()
    assert len(at.error) == 0


def test_performance_report_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/performance/report.py")
    at.run()
    assert len(at.error) == 0
