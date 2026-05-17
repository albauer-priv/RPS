from __future__ import annotations

from rps.planning.week_availability import validate_week_plan_daily_availability
from rps.workspace.iso_helpers import IsoWeek


def _week_plan(*, day: str = "Tue", duration: str = "01:00", workout_id: str | None = "W1") -> dict:
    return {
        "data": {
            "agenda": [
                {
                    "day": day,
                    "date": "2026-05-12",
                    "day_role": "ENDURANCE",
                    "planned_duration": duration,
                    "planned_kj": 500 if workout_id else 0,
                    "workout_id": workout_id,
                }
            ]
        }
    }


def test_daily_availability_blocks_duration_above_hours_max() -> None:
    issues = validate_week_plan_daily_availability(
        week_plan_payload=_week_plan(duration="02:00"),
        availability_payload={
            "data": {
                "availability_table": [
                    {"weekday": "Tue", "hours_min": 1.0, "hours_typical": 1.0, "hours_max": 1.5}
                ]
            }
        },
        target_week=IsoWeek(2026, 20),
    )

    assert len(issues) == 1
    assert "exceeds availability hours_max" in issues[0].format()


def test_daily_availability_allows_duration_above_typical_but_within_max() -> None:
    issues = validate_week_plan_daily_availability(
        week_plan_payload=_week_plan(duration="01:20"),
        availability_payload={
            "data": {
                "availability_table": [
                    {"weekday": "Tue", "hours_min": 1.0, "hours_typical": 1.0, "hours_max": 1.5}
                ]
            }
        },
        target_week=IsoWeek(2026, 20),
    )

    assert issues == []


def test_daily_availability_blocks_fixed_rest_day_load() -> None:
    issues = validate_week_plan_daily_availability(
        week_plan_payload=_week_plan(duration="01:00"),
        availability_payload={"data": {"fixed_rest_days": ["Tue"]}},
        target_week=IsoWeek(2026, 20),
    )

    assert len(issues) == 1
    assert "fixed rest day" in issues[0].format()


def test_daily_availability_ignores_missing_table_rows() -> None:
    issues = validate_week_plan_daily_availability(
        week_plan_payload=_week_plan(duration="03:00"),
        availability_payload={"data": {"availability_table": []}},
        target_week=IsoWeek(2026, 20),
    )

    assert issues == []
