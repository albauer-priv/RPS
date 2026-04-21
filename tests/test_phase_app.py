import json

import pytest
from streamlit.testing.v1 import AppTest

from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

MIN_PHASE_PAGE_NUMBER_INPUTS = 2


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch):
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("ATHLETE_ID", "test_athlete")


def _write_season_plan(root, athlete_id: str) -> None:
    store = LocalArtifactStore(root=root)
    store.ensure_workspace(athlete_id)
    payload = {
        "meta": {"version_key": "latest"},
        "data": {
            "phases": [
                {
                    "phase_id": "P1",
                    "name": "Base",
                    "iso_week_range": "2026-W01..2026-W04",
                    "overview": {
                        "phase_goals": {
                            "primary": "Endurance",
                            "secondary": "Strength",
                        }
                    },
                    "weekly_load_corridor": {"weekly_kj": {"min": 1000, "max": 2000}},
                    "allowed_forbidden_semantics": {
                        "allowed_intensity_domains": ["ENDURANCE_LOW"],
                        "allowed_load_modalities": ["NONE"],
                        "forbidden_intensity_domains": [],
                    },
                }
            ]
        },
    }
    path = store.latest_path(athlete_id, ArtifactType.SEASON_PLAN)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_phase_page_renders(tmp_path, monkeypatch):
    monkeypatch.setenv("ATHLETE_WORKSPACE_ROOT", str(tmp_path))
    athlete_id = "test_athlete"
    _write_season_plan(tmp_path, athlete_id)

    at = AppTest.from_file("src/rps/ui/pages/plan/phase.py")
    at.run()

    assert len(at.error) == 0
    assert len(at.selectbox) >= 1
    assert len(at.text_input) >= 1
    assert len(at.number_input) >= MIN_PHASE_PAGE_NUMBER_INPUTS
