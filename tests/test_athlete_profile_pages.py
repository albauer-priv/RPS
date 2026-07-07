import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from rps.ui.shared import SETTINGS
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("ATHLETE_ID", "test_athlete")
    monkeypatch.setenv("ATHLETE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RPS_DISABLE_INTERVALS_REFRESH", "1")


def test_athlete_profile_pages_render():
    pages = [
        "src/rps/ui/pages/athlete_profile/about_you.py",
        "src/rps/ui/pages/athlete_profile/availability.py",
        "src/rps/ui/pages/athlete_profile/events.py",
        "src/rps/ui/pages/athlete_profile/logistics.py",
        "src/rps/ui/pages/athlete_profile/historic_data.py",
    ]
    for page in pages:
        at = AppTest.from_file(page)
        at.run(timeout=10)
        assert len(at.error) == 0
        if page.endswith("about_you.py"):
            assert any(button.label == "Save Profile & Goals" for button in at.button)
        if page.endswith("events.py"):
            assert any(button.label == "Save Events" for button in at.button)
        if page.endswith("logistics.py"):
            assert any(button.label == "Save Logistics" for button in at.button)
        if page.endswith("historic_data.py"):
            assert any(button.label == "Refresh Historical Baseline" for button in at.button)


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


def test_kpi_profile_page_defaults_to_saved_profile():
    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)
    profile_key = "des_brevet_600_km_masters"

    selected_payload = json.loads(
        (Path("specs/kpi_profiles") / f"kpi_profile_{profile_key}.json").read_text(encoding="utf-8")
    )
    store.save_document(
        athlete_id,
        ArtifactType.KPI_PROFILE,
        profile_key,
        selected_payload,
        producer_agent="user",
        run_id="test_kpi_profile_select",
        update_latest=True,
    )

    at = AppTest.from_file("src/rps/ui/pages/athlete_profile/kpi_profile.py")
    at.session_state["athlete_id"] = athlete_id
    at.run()

    assert len(at.error) == 0
    assert any(select.label == "Select KPI Profile" for select in at.selectbox)
    assert store.get_latest_version_key(athlete_id, ArtifactType.KPI_PROFILE) == profile_key


def test_kpi_profile_page_saves_canonical_meta():
    from rps.ui.pages.athlete_profile.kpi_profile import _build_selected_kpi_profile_document

    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    athlete_id = "test_athlete"
    store.ensure_workspace(athlete_id)
    profile_key = "des_brevet_600_km_masters"
    selected_payload = json.loads(
        (Path("specs/kpi_profiles") / f"kpi_profile_{profile_key}.json").read_text(encoding="utf-8")
    )
    run_id = "ui_kpi_profile_test"
    document = _build_selected_kpi_profile_document(
        selected_payload,
        version_key=profile_key,
        run_id=run_id,
    )
    store.save_document(
        athlete_id,
        ArtifactType.KPI_PROFILE,
        profile_key,
        document,
        producer_agent="ui_kpi_profile",
        run_id=run_id,
        update_latest=True,
    )

    saved = store.load_latest(athlete_id, ArtifactType.KPI_PROFILE)
    assert isinstance(saved, dict)
    meta = saved["meta"]
    assert meta["artifact_type"] == "KPI_PROFILE"
    assert meta["schema_id"] == "KPIProfileInterface"
    assert meta["authority"] == "Binding"
    assert meta["owner_agent"] == "Policy-Owner"
    assert meta["scope"] == "Shared"
    assert meta["data_confidence"] == "UNKNOWN"
    assert meta["iso_week"]
    assert meta["iso_week_range"] == f"{meta['iso_week']}--{meta['iso_week']}"
    assert isinstance(meta["temporal_scope"], dict)
    assert meta["temporal_scope"]["from"]
    assert meta["temporal_scope"]["to"]
    assert isinstance(meta["trace_upstream"], list)
    assert meta["trace_upstream"]
    assert "run_id" in meta["trace_upstream"][0]
    assert meta["trace_data"] == []
    assert meta["trace_events"] == []


def test_data_operations_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/athlete_profile/data_operations.py")
    at.run()
    assert len(at.error) == 0
    labels = [button.label for button in at.button]
    assert "Create Backup" in labels


def test_availability_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/athlete_profile/availability.py")
    at.run()
    assert len(at.error) == 0
