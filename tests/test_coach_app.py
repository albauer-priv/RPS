from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch):
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")


def test_coach_summary_above_input():
    at = AppTest.from_file("src/rps/ui/pages/coach.py")
    at.run()

    assert len(at.error) == 0
    assert len(at.chat_input) == 1
    assert len(at.info) >= 1

    summary_info = None
    for info in at.info:
        if info.value.startswith("Summary:"):
            summary_info = info
            break
    assert summary_info is not None

    info_index = next(idx for idx, node in enumerate(list(at)) if node is summary_info)
    chat_index = next(idx for idx, node in enumerate(list(at)) if node.type == "chat_input")
    assert info_index < chat_index


def test_coach_source_exposes_active_operation_tools():
    source = Path("src/rps/ui/pages/coach.py").read_text(encoding="utf-8")
    assert "preview_scoped_week_replan" in source
    assert "apply_pending_coach_operation" in source
    assert "preview_run_performance_report" in source
    assert "preview_run_feed_forward" in source


def test_coach_source_no_longer_depends_on_rps_chatbot():
    source = Path("src/rps/ui/pages/coach.py").read_text(encoding="utf-8")
    assert "rps_chatbot" not in source
    assert "run_coach_flow(" in source


def test_workouts_editor_source_no_longer_depends_on_rps_chatbot():
    source = Path("src/rps/ui/pages/plan/workouts.py").read_text(encoding="utf-8")
    assert "rps_chatbot" not in source
