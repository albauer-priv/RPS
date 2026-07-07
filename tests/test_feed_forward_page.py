from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("ATHLETE_ID", "test_athlete")
    monkeypatch.setenv("ATHLETE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RPS_DISABLE_INTERVALS_REFRESH", "1")


def test_feed_forward_page_renders():
    at = AppTest.from_file("src/rps/ui/pages/performance/feed_forward.py")
    at.run(timeout=10)
    assert len(at.error) == 0



def test_feed_forward_requires_selected_week_report():
    at = AppTest.from_file("src/rps/ui/pages/performance/feed_forward.py")
    at.run(timeout=10)
    assert len(at.error) == 0
    button = next(
        button for button in at.button if "Run Feed Forward" in button.label
    )
    assert button.disabled is True



def test_feed_forward_page_delegates_to_orchestrator_chain():
    """Feed Forward page must not call agents directly (ADR-001 / .clinerules Sec.7)."""
    source = Path("src/rps/ui/pages/performance/feed_forward.py").read_text(encoding="utf-8")
    assert "run_feed_forward_chain" in source
    assert "run_agent_multi_output" not in source
    assert "from rps.agents" not in source



def test_advisory_actions_source_uses_selected_week_report_versions():
    source = Path("src/rps/orchestrator/advisory_actions.py").read_text(encoding="utf-8")
    assert 'workspace_get_version({{"artifact_type":"DES_ANALYSIS_REPORT","version_key":"{selected_week_key}"}})' in source
    assert 'store.load_latest(athlete_id, ArtifactType.DES_ANALYSIS_REPORT)' not in source



def test_advisory_actions_source_injects_resolved_selected_week_context():
    source = Path("src/rps/orchestrator/advisory_actions.py").read_text(encoding="utf-8")
    assert "build_resolved_des_evaluation_context" in source
    assert "build_resolved_season_phase_feed_forward_context" in source
    assert "save_athlete_state_snapshot" in source
    assert "save_planning_context_snapshot" in source
    assert "save_advisory_memory" in source
    assert 'workspace_get_version({{"artifact_type":"DES_ANALYSIS_REPORT","version_key":"{selected_week_key}"}})' in source
    assert 'workspace_get_version({{"artifact_type":"SEASON_PHASE_FEED_FORWARD","version_key":"{selected_week_key}"}})' in source



def test_coach_source_preloads_week_scoped_activity_versions():
    source = Path("src/rps/ui/pages/coach.py").read_text(encoding="utf-8")
    assert "_coach_memory_blocks" in source
    assert "Workspace memory (auto-loaded, preferred)." in source
    assert "ArtifactType.ADVISORY_MEMORY" in source
    assert '"workspace_get_version", {"artifact_type": "ACTIVITIES_TREND", "version_key": week_key}' in source
    assert '"workspace_get_version", {"artifact_type": "ACTIVITIES_ACTUAL", "version_key": week_key}' in source



def test_week_planner_prompt_requires_percent_on_both_sides_of_ranges():
    source = Path("prompts/agents/week_planner.md").read_text(encoding="utf-8")
    assert "valid: `68%-72%`, `80%-82%`" in source
    assert "invalid: `68-72%`, `80-82%`" in source


