import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("ATHLETE_ID", "test_athlete")
    monkeypatch.setenv("ATHLETE_WORKSPACE_ROOT", str(tmp_path))


def test_home_page_renders_marketing_and_table():
    at = AppTest.from_file("src/rps/ui/pages/home.py")
    at.run()
    assert len(at.error) == 0
    assert len(at.markdown) >= 1
    assert len(at.table) >= 1
