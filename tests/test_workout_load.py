from __future__ import annotations

import pytest

from rps.planning.workout_load import (
    build_workout_load_method_context,
    estimate_week_plan_load,
    estimate_workout_load,
)


def _zone_model() -> dict:
    return {"data": {"model_metadata": {"ftp_watts": 300}, "zones": [{"zone_id": "Z2", "typical_if": 0.66}]}}


def test_estimate_workout_load_parses_segments_and_loops() -> None:
    workout = {
        "workout_id": "W1",
        "workout_text": (
            "Warmup\n- 10m ramp 50%-70% 85-90rpm\n\n"
            "Main Set\n2x\n- 20m 80% 88-92rpm\n- 5m 60% 85rpm\n\n"
            "Cooldown\n- 8m ramp 60%-45% 80-85rpm"
        ),
    }

    estimate = estimate_workout_load(workout=workout, zone_model_payload=_zone_model())

    assert estimate.segment_parse_status == "OK"
    assert estimate.used_fallback_if_direct is False
    assert estimate.duration_seconds == 4080
    assert estimate.planned_if == pytest.approx(0.733, abs=0.001)
    assert estimate.planned_kj > 0
    assert estimate.planned_load_kj > 0


def test_estimate_workout_load_uses_if_direct_fallback_for_intent_only_text() -> None:
    workout = {"workout_id": "W1", "duration": "01:00:00", "notes": "ENDURANCE", "workout_text": "Main Set\nEndurance ride"}
    agenda = {"day_role": "ENDURANCE", "planned_duration": "01:00"}

    estimate = estimate_workout_load(workout=workout, agenda_entry=agenda, zone_model_payload=_zone_model())

    assert estimate.segment_parse_status == "FAIL"
    assert estimate.used_fallback_if_direct is True
    assert estimate.duration_seconds == 3600
    assert estimate.planned_if == pytest.approx(0.66)


def test_estimate_week_plan_load_sums_workouts_against_declared_week_load() -> None:
    week_plan = {
        "data": {
            "week_summary": {"planned_weekly_load_kj": 1500},
            "agenda": [{"workout_id": "W1", "day_role": "ENDURANCE", "planned_duration": "01:00"}],
            "workouts": [
                {
                    "workout_id": "W1",
                    "duration": "01:00:00",
                    "notes": "ENDURANCE",
                    "workout_text": "Warmup\n- 10m 55% 85rpm\n\nMain Set\n- 40m 68%-72% 85-90rpm\n\nCooldown\n- 10m 55% 80rpm",
                }
            ],
        }
    }

    audit = estimate_week_plan_load(week_plan_payload=week_plan, zone_model_payload=_zone_model())

    assert audit["mechanical_total_kj"] > 0
    assert audit["estimated_planned_weekly_load_kj"] > 0
    assert isinstance(audit["delta_to_declared_planned_weekly_load_kj"], int)


def test_build_workout_load_method_context_provides_hourly_domain_calibration() -> None:
    context = build_workout_load_method_context(
        zone_model_payload=_zone_model(),
        allowed_intensity_domains=["RECOVERY", "ENDURANCE_LOW", "TEMPO"],
    )

    assert context["ftp_watts"] == 300
    assert context["IF_ref_load"] == pytest.approx(0.66)
    assert [row["domain"] for row in context["domain_hourly_estimates"]] == ["RECOVERY", "ENDURANCE_LOW", "TEMPO"]
    assert all(row["governance_load_kj_per_hour"] > 0 for row in context["domain_hourly_estimates"])
