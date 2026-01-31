import pytest
from streamlit.testing.v1 import AppTest


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
