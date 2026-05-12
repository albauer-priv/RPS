from __future__ import annotations

from rps.agents.output_normalization import (
    extract_planning_events_document,
    injection_mode_for_tasks,
    normalize_phase_guardrails_document,
    normalize_season_scenarios_document,
    normalize_workout_percent_ranges,
)
from rps.agents.tasks import AgentTask


def test_normalize_phase_guardrails_recovery_rules_and_band_order() -> None:
    document = {
        "meta": {"artifact_type": "PHASE_GUARDRAILS"},
        "data": {
            "execution_non_negotiables": {"recovery_protection_rules": ["rest day", "sleep"]},
            "load_guardrails": {"weekly_kj_bands": [{"band": {"min": 8000, "max": 6200}}]},
        },
    }

    normalized = normalize_phase_guardrails_document(document)

    assert normalized["data"]["execution_non_negotiables"]["recovery_protection_rules"] == "rest day | sleep"
    assert normalized["data"]["load_guardrails"]["weekly_kj_bands"][0]["band"] == {"min": 6200.0, "max": 8000.0}


def test_extract_planning_events_document_parses_workspace_payload() -> None:
    payload = {"ok": True, "content": '{"data":{"events":[{"type":"A","date":"2026-05-10"}]}}'}
    parsed = extract_planning_events_document(payload)
    assert parsed == {"data": {"events": [{"type": "A", "date": "2026-05-10"}]}}


def test_normalize_season_scenarios_derives_horizon_from_events() -> None:
    document = {
        "meta": {"artifact_type": "SEASON_SCENARIOS", "iso_week": "2026-19", "trace_events": [], "trace_data": []},
        "data": {
            "planning_horizon_weeks": 1,
            "scenarios": [
                {
                    "scenario_id": "S1",
                    "scenario_guidance": {"deload_cadence": "3:1", "intensity_guidance": {"allowed_domains": ["ENDURANCE_LOW"], "avoid_domains": ["NONE", "THRESHOLD"]}},
                }
            ],
        },
    }
    events = {"data": {"events": [{"type": "A", "date": "2026-06-14"}]}}

    normalized = normalize_season_scenarios_document(document, planning_events_document=events)

    assert normalized["meta"]["iso_week_range"] == "2026-19--2026-24"
    assert normalized["data"]["planning_horizon_weeks"] == 6
    guidance = normalized["data"]["scenarios"][0]["scenario_guidance"]
    assert guidance["intensity_guidance"]["allowed_domains"] == ["ENDURANCE_LOW"]
    assert guidance["intensity_guidance"]["avoid_domains"] == ["THRESHOLD"]


def test_injection_mode_for_tasks_is_single_mode_only() -> None:
    assert injection_mode_for_tasks([AgentTask.CREATE_PHASE_GUARDRAILS]) == "phase_guardrails"
    assert injection_mode_for_tasks([AgentTask.CREATE_PHASE_GUARDRAILS, AgentTask.CREATE_WEEK_PLAN]) is None


def test_normalize_workout_percent_ranges_repairs_missing_middle_percent() -> None:
    assert normalize_workout_percent_ranges("- 3h44m 68-72% 85-90rpm") == "- 3h44m 68%-72% 85-90rpm"
