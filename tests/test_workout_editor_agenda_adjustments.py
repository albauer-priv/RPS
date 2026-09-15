"""Unit tests for preview_update_agenda_day bounded edit."""

from __future__ import annotations

import pytest

from rps.orchestrator.week_plan_edits import preview_update_agenda_day


def _minimal_plan(days: list[dict]) -> dict:
    agenda = [
        {
            "day": d["day"],
            "date": d.get("date", ""),
            "day_role": d.get("day_role", "ENDURANCE"),
            "planned_duration": d.get("planned_duration", "01:00"),
            "planned_kj": d.get("planned_kj", 400),
            "workout_id": d.get("workout_id"),
        }
        for d in days
    ]
    return {"meta": {}, "data": {"agenda": agenda, "workouts": []}}


def _agenda_row(preview, day: str) -> dict:
    return next(row for row in preview.document["data"]["agenda"] if row["day"] == day)  # type: ignore[index]


def test_update_planned_kj() -> None:
    plan = _minimal_plan([{"day": "Tue", "planned_kj": 400}])
    preview = preview_update_agenda_day(plan, day="Tue", planned_kj=600)
    assert _agenda_row(preview, "Tue")["planned_kj"] == 600
    assert "planned_kj → 600" in preview.summary


def test_update_planned_duration() -> None:
    plan = _minimal_plan([{"day": "Wed", "planned_duration": "01:00"}])
    preview = preview_update_agenda_day(plan, day="Wed", planned_duration="01:30")
    assert _agenda_row(preview, "Wed")["planned_duration"] == "01:30"
    assert "planned_duration → 01:30" in preview.summary


def test_update_day_role_uppercased() -> None:
    plan = _minimal_plan([{"day": "Thu", "day_role": "ENDURANCE"}])
    preview = preview_update_agenda_day(plan, day="Thu", day_role="recovery")
    assert _agenda_row(preview, "Thu")["day_role"] == "RECOVERY"
    assert "day_role → RECOVERY" in preview.summary


def test_update_multiple_fields() -> None:
    plan = _minimal_plan([{"day": "Mon", "day_role": "QUALITY", "planned_kj": 500, "planned_duration": "01:30"}])
    preview = preview_update_agenda_day(
        plan, day="Mon", planned_kj=350, planned_duration="00:45", day_role="RECOVERY"
    )
    row = _agenda_row(preview, "Mon")
    assert row["planned_kj"] == 350
    assert row["planned_duration"] == "00:45"
    assert row["day_role"] == "RECOVERY"
    assert "day_role → RECOVERY" in preview.summary
    assert "planned_kj → 350" in preview.summary
    assert "planned_duration → 00:45" in preview.summary


def test_update_rejects_all_none() -> None:
    plan = _minimal_plan([{"day": "Fri"}])
    with pytest.raises(ValueError, match="at least one of"):
        preview_update_agenda_day(plan, day="Fri")


def test_update_rejects_unknown_day() -> None:
    plan = _minimal_plan([{"day": "Mon"}])
    with pytest.raises(ValueError, match="agenda day not found"):
        preview_update_agenda_day(plan, day="Tue", planned_kj=100)


def test_update_rejects_negative_kj() -> None:
    plan = _minimal_plan([{"day": "Sat"}])
    with pytest.raises(ValueError, match="non-negative"):
        preview_update_agenda_day(plan, day="Sat", planned_kj=-10)


def test_update_rejects_invalid_duration_format() -> None:
    plan = _minimal_plan([{"day": "Sun"}])
    with pytest.raises(ValueError, match="HH:MM"):
        preview_update_agenda_day(plan, day="Sun", planned_duration="90")
