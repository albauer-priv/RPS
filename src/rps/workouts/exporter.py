"""Deterministic conversion from WEEK_PLAN to INTERVALS_WORKOUTS."""

from __future__ import annotations

from typing import TypeAlias

from rps.workouts.validator import validate_week_plan_exportability

JsonMap: TypeAlias = dict[str, object]
JsonList: TypeAlias = list[object]


def build_intervals_workouts_export(week_plan: JsonMap) -> list[JsonMap]:
    """Convert a validated week plan into the Intervals workouts export array."""
    validate_week_plan_exportability(week_plan)
    data = week_plan["data"]
    assert isinstance(data, dict)  # validated above
    agenda = data["agenda"]
    workouts = data["workouts"]
    assert isinstance(agenda, list)
    assert isinstance(workouts, list)

    workout_map = {
        str(item.get("workout_id")): item
        for item in workouts
        if isinstance(item, dict) and item.get("workout_id") is not None
    }
    export_items: list[JsonMap] = []
    for agenda_item in agenda:
        if not isinstance(agenda_item, dict):
            continue
        workout_id = agenda_item.get("workout_id")
        if workout_id is None:
            continue
        workout = workout_map[str(workout_id)]
        export_items.append(_map_workout_entry(agenda_item, workout))
    return export_items


def _map_workout_entry(agenda_item: JsonMap, workout: JsonMap) -> JsonMap:
    """Map one week-plan workout to one Intervals export record."""
    date_value = str(workout.get("date") or agenda_item.get("date") or "").strip()
    start_value = str(workout.get("start") or "00:00").strip()
    title_value = str(workout.get("title") or "").strip()
    text_value = str(workout.get("workout_text") or "").strip("\n")
    return {
        "start_date_local": f"{date_value}T{start_value}:00",
        "category": "WORKOUT",
        "type": "Ride",
        "name": title_value,
        "description": text_value,
    }
