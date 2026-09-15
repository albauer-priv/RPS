"""Unit tests for preview_swap_workouts bounded edit."""

from __future__ import annotations

import pytest

from rps.orchestrator.week_plan_edits import preview_swap_workouts


def _minimal_week_plan(workouts_agenda: list[dict]) -> dict:
    """Build a minimal WEEK_PLAN envelope for testing."""
    agenda = []
    workouts = []
    for entry in workouts_agenda:
        wid = entry.get("workout_id")
        agenda.append(
            {
                "day": entry["day"],
                "date": entry.get("date", ""),
                "day_role": entry.get("day_role", "ENDURANCE"),
                "planned_duration": entry.get("planned_duration", "01:00"),
                "planned_kj": entry.get("planned_kj", 500),
                "workout_id": wid,
            }
        )
        if wid:
            workouts.append(
                {
                    "workout_id": wid,
                    "title": entry.get("title", wid),
                    "date": entry.get("date", ""),
                    "start": entry.get("start", "07:00"),
                }
            )
    return {"meta": {"artifact_type": "WEEK_PLAN"}, "data": {"agenda": agenda, "workouts": workouts}}


def test_swap_workouts_exchanges_workout_ids_and_dates() -> None:
    plan = _minimal_week_plan(
        [
            {"day": "Tue", "date": "2026-09-15", "workout_id": "w001", "title": "Threshold", "day_role": "QUALITY"},
            {"day": "Thu", "date": "2026-09-17", "workout_id": "w002", "title": "Endurance", "day_role": "ENDURANCE"},
        ]
    )

    preview = preview_swap_workouts(plan, year=2026, week=38, source_day="Tue", target_day="Thu")

    workouts_by_day = {w["day"]: w for w in preview.workouts}
    assert workouts_by_day["Tue"]["workout_id"] == "w002"
    assert workouts_by_day["Thu"]["workout_id"] == "w001"
    # Agenda row dates stay on their calendar slot; workout records get the new day's date
    assert workouts_by_day["Tue"]["date"] == "2026-09-15"
    assert workouts_by_day["Thu"]["date"] == "2026-09-17"
    # Workout records' dates updated to their new day
    doc_workouts = {w["workout_id"]: w for w in preview.document["data"]["workouts"]}  # type: ignore[index]
    assert doc_workouts["w001"]["date"] == "2026-09-17"   # w001 moved to Thu
    assert doc_workouts["w002"]["date"] == "2026-09-15"   # w002 moved to Tue
    assert "w001" in preview.summary
    assert "w002" in preview.summary


def test_swap_workouts_carries_agenda_metadata_with_workout() -> None:
    plan = _minimal_week_plan(
        [
            {"day": "Mon", "workout_id": "w001", "day_role": "QUALITY", "planned_kj": 800, "planned_duration": "01:30"},
            {"day": "Wed", "workout_id": "w002", "day_role": "ENDURANCE", "planned_kj": 400, "planned_duration": "02:00"},
        ]
    )

    preview = preview_swap_workouts(plan, year=2026, week=38, source_day="Mon", target_day="Wed")

    doc_agenda = {row["day"]: row for row in preview.document["data"]["agenda"]}  # type: ignore[index]
    assert doc_agenda["Mon"]["workout_id"] == "w002"
    assert doc_agenda["Mon"]["day_role"] == "ENDURANCE"
    assert doc_agenda["Mon"]["planned_kj"] == 400
    assert doc_agenda["Wed"]["workout_id"] == "w001"
    assert doc_agenda["Wed"]["day_role"] == "QUALITY"
    assert doc_agenda["Wed"]["planned_kj"] == 800


def test_swap_workouts_rejects_empty_source_day() -> None:
    plan = _minimal_week_plan(
        [
            {"day": "Mon", "workout_id": None},
            {"day": "Wed", "workout_id": "w002"},
        ]
    )

    with pytest.raises(ValueError, match="source day Mon has no workout"):
        preview_swap_workouts(plan, year=2026, week=38, source_day="Mon", target_day="Wed")


def test_swap_workouts_rejects_empty_target_day() -> None:
    plan = _minimal_week_plan(
        [
            {"day": "Tue", "workout_id": "w001"},
            {"day": "Thu", "workout_id": None},
        ]
    )

    with pytest.raises(ValueError, match="target day Thu has no workout"):
        preview_swap_workouts(plan, year=2026, week=38, source_day="Tue", target_day="Thu")


def test_swap_workouts_rejects_same_day() -> None:
    plan = _minimal_week_plan([{"day": "Tue", "workout_id": "w001"}])

    with pytest.raises(ValueError, match="source and target day are the same"):
        preview_swap_workouts(plan, year=2026, week=38, source_day="Tue", target_day="Tuesday")
