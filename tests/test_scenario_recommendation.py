from __future__ import annotations

from rps.planning.scenario_recommendation import (
    build_scenario_recommendation_context,
    filter_future_planning_events_payload,
)


def _scenario_payload() -> dict:
    return {
        "meta": {"temporal_scope": {"from": "2026-05-18", "to": "2026-09-13"}},
        "data": {
            "scenarios": [
                {
                    "scenario_id": "A",
                    "name": "Stable 2:1",
                    "scenario_guidance": {"deload_cadence": "2:1"},
                },
                {
                    "scenario_id": "B",
                    "name": "Classic 3:1",
                    "scenario_guidance": {"deload_cadence": "3:1"},
                },
                {
                    "scenario_id": "C",
                    "name": "Flexible 2:1:1",
                    "scenario_guidance": {"deload_cadence": "2:1:1"},
                },
            ]
        },
    }


def _availability_payload() -> dict:
    return {
        "data": {
            "weekly_hours": {"min": 10.5, "typical": 14.0, "max": 17.5},
            "fixed_rest_days": ["Mon", "Fri"],
            "availability_table": [{"weekday": "Tue", "travel_risk": "MED"}],
        }
    }


def _athlete_payload() -> dict:
    return {
        "data": {
            "profile": {"age": 56, "training_age_years": 3},
            "objectives": {"primary": "Top 20 competitive brevet performance"},
            "limitations": ["Training interruptions due to travel"],
        }
    }


def _historical_payload() -> dict:
    return {"data": {"metrics": {"kj_per_year": 203000, "kj_per_hour": 615}, "yearly_summary": [{}, {}, {}]}}


def _events_payload() -> dict:
    return {
        "data": {
            "events": [
                {"type": "A", "date": "2026-09-12", "event_name": "A"},
                {"type": "B", "date": "2026-08-02", "event_name": "B"},
                {"type": "B", "date": "2026-04-11", "event_name": "Past B"},
            ]
        }
    }


def _trend_payload(kj_values: list[int], *, durability: float = 0.95, decoupling: float = 4.5) -> dict:
    return {
        "data": {
            "weekly_trends": [
                {
                    "year": 2026,
                    "iso_week": index,
                    "weekly_aggregates": {"work_kj": kj},
                    "intensity_load_metrics": {
                        "durability_index": durability,
                        "decoupling_percent": decoupling,
                    },
                    "metrics": {
                        "weekly_moving_time_total_min": 600,
                        "tsb_today": -10,
                    },
                }
                for index, kj in enumerate(kj_values, start=13)
            ]
        }
    }


def test_recommends_flexible_cadence_for_robust_but_volatile_athlete() -> None:
    context = build_scenario_recommendation_context(
        season_scenarios_payload=_scenario_payload(),
        athlete_profile_payload=_athlete_payload(),
        availability_payload=_availability_payload(),
        planning_events_payload=_events_payload(),
        historical_baseline_payload=_historical_payload(),
        activities_trend_payload=_trend_payload([1148, 3731, 9752, 8000, 11824, 7559, 7103, 1550]),
    )

    assert context["recommended_scenario_id"] == "C"
    assert context["recommended_cadence"] == "2:1:1"
    assert context["confidence"] == "HIGH"
    assert context["features"]["load_volatility_high"] is True
    assert context["features"]["recent_load_gap"] is True


def test_stable_robust_trend_can_recommend_classic_build() -> None:
    context = build_scenario_recommendation_context(
        season_scenarios_payload=_scenario_payload(),
        athlete_profile_payload={
            "data": {
                "profile": {"age": 38, "training_age_years": 8},
                "objectives": {"primary": "Top 20 competitive brevet performance"},
                "limitations": [],
            }
        },
        availability_payload={
            "data": {
                "weekly_hours": {"min": 12.0, "typical": 16.0, "max": 20.0},
                "fixed_rest_days": [],
                "availability_table": [],
            }
        },
        planning_events_payload=_events_payload(),
        historical_baseline_payload=_historical_payload(),
        activities_trend_payload=_trend_payload([8200, 8500, 8700, 8900, 9100, 9300, 9500, 9300], durability=1.0, decoupling=2.0),
    )

    assert context["recommended_scenario_id"] == "B"
    assert context["recommended_cadence"] == "3:1"
    assert context["features"]["load_volatility_high"] is False
    assert context["features"]["recent_load_gap"] is False


def test_filter_future_planning_events_payload_excludes_pre_horizon_events() -> None:
    filtered = filter_future_planning_events_payload(
        _events_payload(),
        as_of_date="2026-05-18",
        until_date="2026-09-13",
    )

    events = filtered["data"]["events"]
    assert [event["event_name"] for event in events] == ["A", "B"]


def test_recommendation_context_counts_future_events_only() -> None:
    context = build_scenario_recommendation_context(
        season_scenarios_payload=_scenario_payload(),
        athlete_profile_payload=_athlete_payload(),
        availability_payload=_availability_payload(),
        planning_events_payload=filter_future_planning_events_payload(
            _events_payload(),
            as_of_date="2026-05-18",
            until_date="2026-09-13",
        ),
        historical_baseline_payload=_historical_payload(),
        activities_trend_payload=_trend_payload([1148, 3731, 9752, 8000, 11824, 7559, 7103, 1550]),
    )

    assert context["evidence"]["future_a_events"] == 1
    assert context["evidence"]["future_b_events"] == 1
