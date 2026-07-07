import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rps.orchestrator import season_flow
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType
from tests.planning_context_helpers import (
    seed_previous_week_planning_evidence as _seed_previous_week_planning_evidence,
)
from tests.planning_context_helpers import (
    write_minimal_availability as _write_minimal_availability,
)
from tests.planning_context_helpers import (
    write_minimal_scenario_chain as _write_minimal_scenario_chain,
)

EXPECTED_SCOPED_ACTION_CALLS = 2


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("RPS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("ATHLETE_ID", "test_athlete")
    monkeypatch.setenv("ATHLETE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RPS_DISABLE_INTERVALS_REFRESH", "1")


def test_season_flow_scoped_actions_do_not_short_circuit(monkeypatch, tmp_path):
    calls = []

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*args, **kwargs):
        calls.append(kwargs)
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text("{}", encoding="utf-8")
    store.latest_path("test_athlete", ArtifactType.AVAILABILITY).write_text(
        json.dumps(
            {
                "data": {
                    "weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5},
                    "fixed_rest_days": ["Mon", "Fri"],
                    "availability_table": [
                        {
                            "weekday": "Tue",
                            "hours_min": 1.5,
                            "hours_typical": 2.0,
                            "hours_max": 2.5,
                            "indoor_possible": True,
                            "travel_risk": "LOW",
                            "locked": False,
                        }
                    ],
                    "source_type": "manual",
                    "source_ref": "ui",
                    "notes": "",
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps(
            {
                "data": {
                    "events": [
                        {
                            "type": "B",
                            "priority_rank": 2,
                            "event_name": "Spring 200",
                            "date": "2026-03-18",
                            "event_type": "Brevet",
                            "goal": "rehearsal",
                            "distance_km": 200,
                            "elevation_m": 1800,
                            "expected_duration": "08:00",
                            "time_limit": "13:30",
                        },
                        {
                            "type": "A",
                            "priority_rank": 1,
                            "event_name": "Main 400",
                            "date": "2026-05-10",
                            "event_type": "Brevet",
                            "goal": "finish strong",
                            "distance_km": 400,
                            "elevation_m": 3600,
                            "expected_duration": "18:00",
                            "time_limit": "27:00",
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.SEASON_SCENARIO_SELECTION).write_text(
        json.dumps({"data": {"kpi_moving_time_rate_guidance_selection": None}}),
        encoding="utf-8",
    )
    _seed_previous_week_planning_evidence(store, "test_athlete", target_year=2026, target_week=12)
    _write_minimal_scenario_chain(store, "test_athlete", horizon_weeks=8)

    season_flow.create_season_scenarios(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=12,
        run_id="run_scenarios",
        override_text="rerun scenarios",
    )
    season_flow.create_season_plan(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=12,
        run_id="run_plan",
        selected=None,
        override_text="rerun season",
    )

    assert len(calls) == EXPECTED_SCOPED_ACTION_CALLS



def test_create_season_plan_includes_selected_kpi_guidance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_inputs: list[str] = []

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text("{}", encoding="utf-8")
    store.latest_path("test_athlete", ArtifactType.AVAILABILITY).write_text(
        json.dumps(
            {
                "data": {
                    "weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5},
                    "fixed_rest_days": ["Mon", "Fri"],
                    "availability_table": [
                        {
                            "weekday": "Tue",
                            "hours_min": 1.5,
                            "hours_typical": 2.0,
                            "hours_max": 2.5,
                            "indoor_possible": True,
                            "travel_risk": "LOW",
                            "locked": False,
                        }
                    ],
                    "source_type": "manual",
                    "source_ref": "ui",
                    "notes": "",
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps(
            {
                "data": {
                    "events": [
                        {
                            "type": "B",
                            "priority_rank": 2,
                            "event_name": "Spring 200",
                            "date": "2026-03-18",
                            "event_type": "Brevet",
                            "goal": "rehearsal",
                            "distance_km": 200,
                            "elevation_m": 1800,
                            "expected_duration": "08:00",
                            "time_limit": "13:30",
                        },
                        {
                            "type": "A",
                            "priority_rank": 1,
                            "event_name": "Main 400",
                            "date": "2026-05-10",
                            "event_type": "Brevet",
                            "goal": "finish strong",
                            "distance_km": 400,
                            "elevation_m": 3600,
                            "expected_duration": "18:00",
                            "time_limit": "27:00",
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    store.save_document(
        "test_athlete",
        ArtifactType.SEASON_SCENARIO_SELECTION,
        "2026-12",
        {
            "data": {
                "kpi_moving_time_rate_guidance_selection": {
                    "segment": "fast_competitive",
                    "w_per_kg": {"min": 2.5, "max": 3.0},
                    "kj_per_kg_per_hour": {"min": 20, "max": 24},
                }
            }
        },
        producer_agent="user",
        run_id="test_selection",
        update_latest=True,
    )
    store.save_document(
        "test_athlete",
        ArtifactType.KPI_PROFILE,
        "sample_profile",
        {
            "data": {
                "durability": {
                    "moving_time_rate_guidance": {
                        "derived_from": "kpi_profile_v1",
                        "notes": "Use selected segment directly.",
                        "bands": [
                            {
                                "segment": "fast_competitive",
                                "w_per_kg": {"min": 2.5, "max": 3.0},
                                "kj_per_kg_per_hour": {"min": 20, "max": 24},
                                "basis": "validated",
                            },
                            {
                                "segment": "steady_endurance",
                                "w_per_kg": {"min": 2.0, "max": 2.4},
                                "kj_per_kg_per_hour": {"min": 16, "max": 19},
                                "basis": "validated",
                            },
                        ],
                    }
                }
            }
        },
        producer_agent="user",
        run_id="test_kpi_profile",
        update_latest=True,
    )
    _seed_previous_week_planning_evidence(store, "test_athlete", target_year=2026, target_week=12)
    _write_minimal_scenario_chain(store, "test_athlete", horizon_weeks=8)

    season_flow.create_season_plan(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=12,
        run_id="run_plan",
        selected=None,
        override_text="rerun season",
    )

    assert captured_inputs
    assert "**Athlete State Snapshot**" in captured_inputs[0]
    assert "**Resolved KPI Context**" in captured_inputs[0]
    assert "selected_kpi_rate_band_selector: fast_competitive" in captured_inputs[0]
    assert "kj_per_kg_per_hour 20 - 24" in captured_inputs[0]
    assert "kpi_profile_moving_time_rate_guidance.available_bands:" in captured_inputs[0]
    assert "**Resolved Availability Context**" in captured_inputs[0]
    assert "fixed_rest_days: Mon, Fri" in captured_inputs[0]
    assert "**Resolved Planning Event Context**" in captured_inputs[0]
    assert "Spring 200" in captured_inputs[0]
    assert "workspace_get_version for ACTIVITIES_ACTUAL and ACTIVITIES_TREND with version_key 2026-12" not in captured_inputs[0]
    assert store.latest_exists("test_athlete", ArtifactType.ATHLETE_STATE_SNAPSHOT)



def test_create_season_plan_injects_selected_scenario_phase_math(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_inputs: list[str] = []

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*_args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text("{}", encoding="utf-8")
    _write_minimal_availability(store, "test_athlete")
    store.save_document(
        "test_athlete",
        ArtifactType.SEASON_SCENARIOS,
        "2026-12",
        {
            "meta": {
                "artifact_type": "SEASON_SCENARIOS",
                "version_key": "2026-12",
                "run_id": "test_scenarios",
            },
            "data": {
                "planning_horizon_weeks": 17,
                "scenarios": [
                    {
                        "scenario_id": "B",
                        "name": "Compact resilient build",
                        "load_philosophy": "balanced_progressive",
                        "risk_profile": "medium",
                        "best_suited_if": "Compressed horizon with stable recovery.",
                        "key_differences": "Uses shorter phases with bounded compression.",
                        "main_payoff": "Preserves continuity in a compressed horizon.",
                        "main_cost": "Less room for recovery drift.",
                        "scenario_guidance": {
                            "deload_cadence": "2:1",
                            "phase_length_weeks": 3,
                            "phase_count_expected": 6,
                            "max_shortened_phases": 2,
                            "shortening_budget_weeks": 1,
                            "phase_plan_summary": {
                                "full_phases": 5,
                                "shortened_phases": [{"len": 2, "count": 1}],
                            },
                            "recovery_margin": "medium",
                            "fatigue_exposure": "moderate",
                            "specificity_density": "controlled",
                            "constraint_summary": ["Keep compression bounded and repeatable."],
                            "intensity_guidance": {
                                "allowed_domains": ["ENDURANCE", "TEMPO"],
                                "avoid_domains": ["VO2MAX"],
                            },
                            "event_alignment_notes": ["A-event backplanned."],
                            "risk_flags": ["Compressed horizon."],
                            "kpi_guardrail_notes": ["Do not over-compress early load."],
                            "decision_notes": ["Chosen for compact progression test."],
                        },
                    }
                ],
            }
        },
        producer_agent="test",
        run_id="test_scenarios",
        update_latest=True,
    )
    scenarios_doc = store.load_latest("test_athlete", ArtifactType.SEASON_SCENARIOS)
    scenarios_meta = scenarios_doc.get("meta", {}) if isinstance(scenarios_doc, dict) else {}
    scenarios_version_key = scenarios_meta.get("version_key", "2026-12")
    store.save_document(
        "test_athlete",
        ArtifactType.SEASON_SCENARIO_SELECTION,
        "2026-12",
        {
            "meta": {
                "artifact_type": "SEASON_SCENARIO_SELECTION",
                "version_key": "2026-12",
                "run_id": "test_selection",
                "trace_upstream": [
                    {
                        "artifact": "SEASON_SCENARIOS",
                        "version": scenarios_version_key,
                        "version_key": scenarios_version_key,
                        "run_id": "test_scenarios",
                    }
                ],
            },
            "data": {
                "selected_scenario_id": "B",
                "season_scenarios_ref": scenarios_version_key,
                "selection_source": "user",
                "selection_rationale": "Compact resilient build.",
                "notes": ["Test selection."],
                "kpi_moving_time_rate_guidance_selection": None,
            },
        },
        producer_agent="test",
        run_id="test_selection",
        update_latest=True,
    )
    _seed_previous_week_planning_evidence(store, "test_athlete", target_year=2026, target_week=12)

    season_flow.create_season_plan(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=12,
        run_id="run_plan",
        selected=None,
    )

    assert captured_inputs
    assert "**Deterministic Selected Scenario Structure Context**" in captured_inputs[0]
    assert "planning_horizon_weeks: 17" in captured_inputs[0]
    assert "deload_cadence: 2:1" in captured_inputs[0]
    assert "phase_length_weeks: 3" in captured_inputs[0]
    assert "phase_count_expected: 6" in captured_inputs[0]
    assert "full_phases: 5" in captured_inputs[0]
    assert "- len 2, count 1" in captured_inputs[0]
    assert "consistent_with_horizon: True" in captured_inputs[0]
    assert "**Deterministic Season Phase Slot Context**" in captured_inputs[0]
    assert "P01: 2026-12--2026-13" in captured_inputs[0]
    assert "scenario_cadence 2:1" in captured_inputs[0]
    assert "cadence_week_roles SHORTENED_RE_ENTRY, SHORTENED_CONSOLIDATION" in captured_inputs[0]
    assert "P06: 2026-26--2026-28" in captured_inputs[0]
    assert "**Deterministic Season Phase Load Context**" in captured_inputs[0]
    assert "season_phase_role" in captured_inputs[0]
    assert "role_week_load_bands" in captured_inputs[0]



def test_create_season_plan_injects_resolved_logistics_and_zone_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_inputs: list[str] = []

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*_args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text("{}", encoding="utf-8")
    store.latest_path("test_athlete", ArtifactType.LOGISTICS).write_text(
        json.dumps(
            {
                "data": {
                    "events": [
                        {
                            "date": "2026-03-19",
                            "event_id": "LOG-1",
                            "event_type": "TRAVEL",
                            "status": "PLANNED",
                            "impact": "AVAILABILITY",
                            "description": "Business trip",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps(
            {
                "data": {
                    "events": [
                        {
                            "type": "B",
                            "priority_rank": 2,
                            "event_name": "Spring 200",
                            "date": "2026-03-18",
                            "event_type": "Brevet",
                            "goal": "rehearsal",
                            "distance_km": 200,
                            "elevation_m": 1800,
                            "expected_duration": "08:00",
                            "time_limit": "13:30",
                        },
                        {
                            "type": "A",
                            "priority_rank": 1,
                            "event_name": "Main 400",
                            "date": "2026-05-10",
                            "event_type": "Brevet",
                            "goal": "finish strong",
                            "distance_km": 400,
                            "elevation_m": 3600,
                            "expected_duration": "18:00",
                            "time_limit": "27:00",
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.AVAILABILITY).write_text(
        json.dumps(
            {
                "data": {
                    "weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5},
                    "fixed_rest_days": ["Mon", "Fri"],
                    "availability_table": [],
                    "source_type": "manual",
                    "source_ref": "ui",
                    "notes": "",
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.ZONE_MODEL).write_text(
        json.dumps(
            {
                "data": {
                    "model_metadata": {
                        "valid_from": "2026-01-01",
                        "ftp_watts": 300,
                        "purpose": "planning",
                        "filename": "zone_model_power_300W.json",
                    },
                    "zones": [
                        {
                            "zone_id": "Z2",
                            "name": "Endurance",
                            "ftp_percent_range": {"min": 56, "max": 75},
                            "watt_range": {"min": 168, "max": 225},
                            "training_intent": "endurance",
                            "typical_if": 0.68,
                        }
                    ],
                    "examples": [],
                    "versioning_usage": [],
                }
            }
        ),
        encoding="utf-8",
    )
    _seed_previous_week_planning_evidence(store, "test_athlete", target_year=2026, target_week=12)
    _write_minimal_scenario_chain(store, "test_athlete", horizon_weeks=8)

    season_flow.create_season_plan(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=12,
        run_id="run_plan",
        selected=None,
        override_text=None,
    )

    assert captured_inputs
    assert "**Resolved Logistics Context**" in captured_inputs[0]
    assert "Business trip" in captured_inputs[0]
    assert "**Resolved Zone Model Context**" in captured_inputs[0]
    assert "ftp_watts: 300" in captured_inputs[0]



def test_create_season_plan_uses_historical_activity_versions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_inputs: list[str] = []

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*_args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text("{}", encoding="utf-8")
    store.latest_path("test_athlete", ArtifactType.AVAILABILITY).write_text(
        json.dumps({"data": {"weekly_hours": {"min": 10, "typical": 12, "max": 14}, "fixed_rest_days": ["Mon"], "availability_table": []}}),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps({"data": {"events": []}}),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.ZONE_MODEL).write_text(
        json.dumps({"data": {"model_metadata": {"ftp_watts": 300}, "zones": []}}),
        encoding="utf-8",
    )
    store.save_document(
        "test_athlete",
        ArtifactType.ACTIVITIES_ACTUAL,
        "2026-16",
        {"data": {"activities": []}},
        producer_agent="user",
        run_id="activities_actual_202616",
        update_latest=True,
    )
    store.save_document(
        "test_athlete",
        ArtifactType.ACTIVITIES_TREND,
        "2026-16",
        {
            "data": {
                "weekly_trends": [
                    {
                        "year": 2026,
                        "iso_week": 16,
                        "weekly_aggregates": {"activity_count": 5, "moving_time": "13:48", "work_kj": 7760},
                        "intensity_load_metrics": {"durability_index": 0.94},
                    }
                ]
            }
        },
        producer_agent="user",
        run_id="activities_trend_202616",
        update_latest=True,
    )
    store.save_document(
        "test_athlete",
        ArtifactType.HISTORICAL_BASELINE,
        "baseline",
        {
            "data": {
                "metrics": {"kj_per_year": 120000},
                "source": {"source_type": "test", "range": "3y"},
            }
        },
        producer_agent="user",
        run_id="historical-baseline",
        update_latest=True,
    )
    _write_minimal_scenario_chain(store, "test_athlete")

    season_flow.create_season_plan(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=17,
        run_id="run_plan",
        selected=None,
        override_text=None,
    )

    assert captured_inputs
    assert "previous-week ACTIVITIES_ACTUAL and ACTIVITIES_TREND at evidence week 2026-16: 2026-16 and 2026-16" in captured_inputs[0]
    assert "**Resolved Activity Context**" in captured_inputs[0]
    assert "historical_reference_week: 2026-16" in captured_inputs[0]
    assert "activities_actual_version: 2026-16" in captured_inputs[0]
    assert "activities_trend_version: 2026-16" in captured_inputs[0]



def test_create_season_scenarios_injects_resolved_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_inputs: list[str] = []

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*_args, **kwargs):
        captured_inputs.append(kwargs["user_input"])
        return {"ok": True, "produced": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text(
        json.dumps(
            {
                "data": {
                    "profile": {
                        "athlete_id": "test_athlete",
                        "year": 2026,
                        "athlete_name": "Test Rider",
                        "athlete_story": "Long-distance rider",
                        "location_time_zone": "Europe/Berlin",
                        "primary_disciplines": ["Randonneuring"],
                        "training_age_years": 8,
                        "age": 45,
                        "body_mass_kg": 82.4,
                        "sex": "M",
                        "age_group": "Masters",
                        "endurance_anchor_w": 210,
                        "ambition_if_range": [0.68, 0.75],
                    },
                    "objectives": {"primary": "Finish 400 km A event", "secondary": [], "priority_order": []},
                    "constraints": {},
                    "strengths": [],
                    "limitations": [],
                    "risk_flags": [],
                    "success_criteria": [],
                    "measurement_assumptions": {},
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.LOGISTICS).write_text(
        json.dumps(
            {"data": {"events": [{"date": "2026-03-19", "event_id": "LOG-1", "event_type": "TRAVEL", "status": "PLANNED", "impact": "AVAILABILITY", "description": "Business trip"}]}}
        ),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps(
            {
                "data": {
                    "events": [
                        {
                            "type": "B",
                            "priority_rank": 2,
                            "event_name": "Spring 200",
                            "date": "2026-03-18",
                            "event_type": "Brevet",
                            "goal": "rehearsal",
                            "distance_km": 200,
                            "elevation_m": 1800,
                            "expected_duration": "08:00",
                            "time_limit": "13:30",
                        },
                        {
                            "type": "A",
                            "priority_rank": 1,
                            "event_name": "Main 400",
                            "date": "2026-05-10",
                            "event_type": "Brevet",
                            "goal": "finish strong",
                            "distance_km": 400,
                            "elevation_m": 3600,
                            "expected_duration": "18:00",
                            "time_limit": "27:00",
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.AVAILABILITY).write_text(
        json.dumps({"data": {"weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5}, "fixed_rest_days": ["Mon", "Fri"], "availability_table": [], "source_type": "manual", "source_ref": "ui", "notes": ""}}),
        encoding="utf-8",
    )
    store.save_document(
        "test_athlete",
        ArtifactType.KPI_PROFILE,
        "sample_profile",
        {
            "data": {
                "durability": {
                    "moving_time_rate_guidance": {
                        "derived_from": "kpi_profile_v1",
                        "notes": "Use selected segment directly.",
                        "bands": [
                            {
                                "segment": "fast_competitive",
                                "w_per_kg": {"min": 2.5, "max": 3.0},
                                "kj_per_kg_per_hour": {"min": 20, "max": 24},
                                "basis": "validated",
                            }
                        ],
                    }
                }
            }
        },
        producer_agent="user",
        run_id="test_kpi_profile",
        update_latest=True,
    )
    _seed_previous_week_planning_evidence(store, "test_athlete", target_year=2026, target_week=12)

    season_flow.create_season_scenarios(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=12,
        run_id="run_scenarios",
        override_text=None,
    )

    assert captured_inputs
    assert "**Athlete State Snapshot**" in captured_inputs[0]
    assert "athlete_name: Test Rider" in captured_inputs[0]
    assert "endurance_anchor_w: 210" in captured_inputs[0]
    assert "kpi_profile" in captured_inputs[0]
    assert "availability" in captured_inputs[0]
    assert "Spring 200" in captured_inputs[0]
    assert "Main 400" in captured_inputs[0]
    assert "**Historical Baseline Evidence**" in captured_inputs[0]
    assert "**Resolved Activity Context**" in captured_inputs[0]
    assert "**Evidence Alignment**" in captured_inputs[0]
    assert "**Deterministic Season Scenario Horizon Context**" in captured_inputs[0]
    assert "target_week_start_date: 2026-03-16" in captured_inputs[0]
    assert "last_event_date: 2026-05-10" in captured_inputs[0]
    assert "last_event_iso_week: 2026-19" in captured_inputs[0]
    assert "weeks_until_last_event_from_target_week_start: 7" in captured_inputs[0]
    assert "inclusive_planning_horizon_weeks: 8" in captured_inputs[0]
    assert "season_iso_week_range: 2026-12--2026-19" in captured_inputs[0]
    assert "**Deterministic Cadence Options Context**" in captured_inputs[0]
    assert "cadence 2:1" in captured_inputs[0]
    assert "phase_count_expected 3" in captured_inputs[0]



def test_create_season_scenarios_fails_closed_when_activity_resolution_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    invoked = False

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*_args, **_kwargs):
        nonlocal invoked
        invoked = True
        return {"ok": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text(
        json.dumps({"data": {"profile": {"athlete_id": "test_athlete", "athlete_name": "Test Rider"}}}),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.AVAILABILITY).write_text(
        json.dumps({"data": {"weekly_hours": {"typical": 12.0}, "fixed_rest_days": ["Mon", "Fri"]}}),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps({"data": {"events": []}}),
        encoding="utf-8",
    )
    store.save_document(
        "test_athlete",
        ArtifactType.HISTORICAL_BASELINE,
        "baseline",
        {"data": {"metrics": {"kj_per_year": 120000}, "source": {"source_type": "test", "range": "3y"}}},
        producer_agent="test",
        run_id="historical-baseline",
        update_latest=True,
    )

    def _raise_resolution(*_args, **_kwargs):
        raise RuntimeError("resolution boom")

    monkeypatch.setattr("rps.orchestrator.season_flow.resolve_previous_week_activity_versions", _raise_resolution)

    result = season_flow.create_season_scenarios(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=12,
        run_id="run_scenarios",
        override_text=None,
    )

    assert result["ok"] is False
    assert "Season evidence alignment preparation failed: resolution boom" in str(result["error"])
    assert invoked is False



def test_create_season_scenarios_fails_closed_when_recommendation_context_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    invoked = False

    def _fake_runtime_for(_agent_name):
        return SimpleNamespace(workspace_root=tmp_path)

    def _fake_run_agent_multi_output(*_args, **_kwargs):
        nonlocal invoked
        invoked = True
        return {"ok": True}

    monkeypatch.setattr("rps.orchestrator.season_flow.run_agent_multi_output", _fake_run_agent_multi_output)

    store = LocalArtifactStore(root=tmp_path)
    store.ensure_workspace("test_athlete")
    store.latest_path("test_athlete", ArtifactType.ATHLETE_PROFILE).write_text(
        json.dumps({"data": {"profile": {"athlete_id": "test_athlete", "athlete_name": "Test Rider"}}}),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.AVAILABILITY).write_text(
        json.dumps({"data": {"weekly_hours": {"typical": 12.0}, "fixed_rest_days": ["Mon", "Fri"]}}),
        encoding="utf-8",
    )
    store.latest_path("test_athlete", ArtifactType.PLANNING_EVENTS).write_text(
        json.dumps({"data": {"events": []}}),
        encoding="utf-8",
    )
    _seed_previous_week_planning_evidence(store, "test_athlete", target_year=2026, target_week=12)

    def _raise_recommendation(*_args, **_kwargs):
        raise RuntimeError("recommendation boom")

    monkeypatch.setattr("rps.orchestrator.season_flow.build_scenario_recommendation_context", _raise_recommendation)

    result = season_flow.create_season_scenarios(
        _fake_runtime_for,
        athlete_id="test_athlete",
        year=2026,
        week=12,
        run_id="run_scenarios",
        override_text=None,
    )

    assert result["ok"] is False
    assert "Season evidence alignment preparation failed: recommendation boom" in str(result["error"])
    assert invoked is False


