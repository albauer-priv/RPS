from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
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



def test_season_page_renders_scenario_ux_fields(tmp_path):
    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.save_document(
        "test_athlete",
        ArtifactType.SEASON_SCENARIOS,
        "2026-21",
        {
            "meta": {
                "artifact_type": "SEASON_SCENARIOS",
                "schema_id": "SeasonScenariosInterface",
                "schema_version": "1.0",
                "version": "1.0",
                "authority": "Informational",
                "owner_agent": "Season-Scenario-Agent",
                "run_id": "season_scenarios_test",
                "created_at": "2026-05-19T21:00:00Z",
                "scope": "Season",
                "iso_week": "2026-21",
                "iso_week_range": "2026-21--2026-37",
                "temporal_scope": {"from": "2026-05-18", "to": "2026-09-13"},
                "trace_upstream": [],
                "trace_data": [],
                "trace_events": [],
                "data_confidence": "HIGH",
                "notes": "",
            },
            "data": {
                "kpi_profile_ref": "kpi",
                "athlete_profile_ref": "test_athlete",
                "planning_horizon_weeks": 17,
                "notes": [],
                "scenarios": [
                    {
                        "scenario_id": "A",
                        "name": "Scenario A",
                        "core_idea": "Core.",
                        "load_philosophy": "Load.",
                        "risk_profile": "Risk.",
                        "key_differences": "Diff.",
                        "best_suited_if": "Best.",
                        "typical_week_feel": "Calm and repeatable.",
                        "main_payoff": "High executability.",
                        "main_cost": "Less upside.",
                        "what_gets_prioritized": "Consistency.",
                        "what_gets_de_emphasized": "Aggressive sharpening.",
                        "scenario_guidance": {
                            "deload_cadence": "2:1",
                            "phase_length_weeks": 3,
                            "phase_count_expected": 6,
                            "max_shortened_phases": 1,
                            "shortening_budget_weeks": 1,
                            "phase_plan_summary": {"full_phases": 5, "shortened_phases": [{"len": 2, "count": 1}]},
                            "event_alignment_notes": ["Note."],
                            "risk_flags": ["Risk."],
                            "fixed_rest_days": ["Mon", "Fri"],
                            "constraint_summary": ["Constraint."],
                            "kpi_guardrail_notes": ["Guardrail."],
                            "decision_notes": ["Decision."],
                            "intensity_guidance": {"allowed_domains": ["ENDURANCE"], "avoid_domains": ["THRESHOLD"]},
                            "assumptions": ["Assumption."],
                            "unknowns": ["Unknown."],
                        },
                    },
                    {
                        "scenario_id": "B",
                        "name": "Scenario B",
                        "core_idea": "Core.",
                        "load_philosophy": "Load.",
                        "risk_profile": "Risk.",
                        "key_differences": "Diff.",
                        "best_suited_if": "Best.",
                        "typical_week_feel": "Structured and productive.",
                        "main_payoff": "Balanced progress.",
                        "main_cost": "Needs steadier recovery.",
                        "what_gets_prioritized": "Durability under load.",
                        "what_gets_de_emphasized": "Maximal intensity.",
                        "scenario_guidance": {
                            "deload_cadence": "2:1:1",
                            "phase_length_weeks": 4,
                            "phase_count_expected": 5,
                            "max_shortened_phases": 2,
                            "shortening_budget_weeks": 3,
                            "phase_plan_summary": {"full_phases": 3, "shortened_phases": [{"len": 3, "count": 1}]},
                            "event_alignment_notes": ["Note."],
                            "risk_flags": ["Risk."],
                            "fixed_rest_days": ["Mon", "Fri"],
                            "constraint_summary": ["Constraint."],
                            "kpi_guardrail_notes": ["Guardrail."],
                            "decision_notes": ["Decision."],
                            "intensity_guidance": {"allowed_domains": ["ENDURANCE", "TEMPO"], "avoid_domains": ["VO2MAX"]},
                            "assumptions": ["Assumption."],
                            "unknowns": ["Unknown."],
                        },
                    },
                    {
                        "scenario_id": "C",
                        "name": "Scenario C",
                        "core_idea": "Core.",
                        "load_philosophy": "Load.",
                        "risk_profile": "Risk.",
                        "key_differences": "Diff.",
                        "best_suited_if": "Best.",
                        "typical_week_feel": "Dense and demanding.",
                        "main_payoff": "Highest specificity.",
                        "main_cost": "Lower recovery margin.",
                        "what_gets_prioritized": "Fatigue-context specificity.",
                        "what_gets_de_emphasized": "Comfort and slack.",
                        "scenario_guidance": {
                            "deload_cadence": "3:1",
                            "phase_length_weeks": 4,
                            "phase_count_expected": 5,
                            "max_shortened_phases": 2,
                            "shortening_budget_weeks": 3,
                            "phase_plan_summary": {"full_phases": 3, "shortened_phases": [{"len": 3, "count": 1}]},
                            "event_alignment_notes": ["Note."],
                            "risk_flags": ["Risk."],
                            "fixed_rest_days": ["Mon", "Fri"],
                            "constraint_summary": ["Constraint."],
                            "kpi_guardrail_notes": ["Guardrail."],
                            "decision_notes": ["Decision."],
                            "intensity_guidance": {"allowed_domains": ["ENDURANCE", "TEMPO", "SWEET_SPOT"], "avoid_domains": []},
                            "assumptions": ["Assumption."],
                            "unknowns": ["Unknown."],
                        },
                    },
                ],
            },
        },
        producer_agent="season_scenario",
        run_id="season_scenarios_test",
        update_latest=True,
    )

    at = AppTest.from_file("src/rps/ui/pages/plan/season.py")
    at.run(timeout=10)

    assert len(at.error) == 0
    source = Path("src/rps/ui/pages/plan/season.py").read_text(encoding="utf-8")
    assert "Typical week feel:" in source
    assert "Main payoff:" in source
    assert "Main cost:" in source
    assert "What gets prioritized:" in source
    assert "What gets de-emphasized:" in source


