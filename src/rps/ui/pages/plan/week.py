from __future__ import annotations

from datetime import date as calendar_date
from typing import Any

import streamlit as st

from rps.ui.shared import (
    SETTINGS,
    announce_log_file,
    duration_minutes_from_workout_text,
    format_duration_hhmm,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    iso_week_date_range,
    parse_duration_minutes,
    render_global_sidebar,
    render_status_panel,
    season_plan_covers_week,
    set_status,
)
from rps.workspace.iso_helpers import IsoWeek, next_iso_week
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType

AgendaRow = dict[str, Any]
WorkoutRow = dict[str, Any]


def _agenda_table(agenda: list[AgendaRow]) -> str:
    header = (
        "| Day | Date (YYYY-MM-DD) | Day-Role | Planned Duration | Planned Load (kJ) | Workout-ID |\n"
        "| --- | --- | --- | --- | ---: | --- |\n"
    )
    rows = []
    for row in agenda:
        rows.append(
            "| {day} | {date} | {role} | {duration} | {load} | {workout} |".format(
                day=row.get("day", "N/A"),
                date=row.get("date", "N/A"),
                role=row.get("day_role", "N/A"),
                duration=row.get("planned_duration", "N/A"),
                load=row.get("planned_kj", "N/A"),
                workout=row.get("workout_id", "N/A"),
            )
        )
    if not rows:
        rows.append("| N/A | N/A | N/A | N/A | N/A | N/A |")
    return header + "\n".join(rows)


def _parse_float(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _intensity_buckets(workout_text: str) -> dict[str, int]:
    import re

    buckets = [
        ("Z1", 0, 59),
        ("Z2", 60, 75),
        ("Z3", 76, 87),
        ("Z4", 88, 95),
        ("Z5", 96, 105),
        ("Z6", 106, 1000),
    ]
    counts = {label: 0 for label, _, _ in buckets}
    for match in re.findall(r"(\\d{2,3})%", workout_text or ""):
        val = int(match)
        for label, low, high in buckets:
            if low <= val <= high:
                counts[label] += 1
                break
    return counts


state = init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
announce_log_file(athlete_id)

week_start, week_end = iso_week_date_range(year, week)
st.title(f"Week · {week_start} to {week_end}")
st.caption(f"Athlete: {athlete_id}")
state["iso_year"] = year
state["iso_week"] = week
st.session_state["iso_year"] = year
st.session_state["iso_week"] = week

allowed, reason = season_plan_covers_week(athlete_id, year, week)
current_week = IsoWeek(*calendar_date.today().isocalendar()[:2])
allowed_scope = IsoWeek(year=year, week=week) in {current_week, next_iso_week(current_week)}
if not allowed_scope:
    allowed = False
    reason = "Planning is limited to the current or next ISO week."

if not allowed and reason:
    st.caption(reason)

if not allowed:
    set_status(status_state="running", title="Week", message=reason or "Planning not allowed.")
else:
    set_status(status_state="done", title="Week", message="Ready.")
render_status_panel()

store = LocalArtifactStore(root=SETTINGS.workspace_root)
agenda_payload = None
try:
    agenda_payload = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, f"{year:04d}-{week:02d}")
except FileNotFoundError:
    agenda_payload = None

agenda_rows: list[AgendaRow] = []
workout_rows: list[WorkoutRow] = []
if isinstance(agenda_payload, dict):
    data = agenda_payload.get("data")
    if isinstance(data, dict):
        raw_agenda = data.get("agenda")
        if isinstance(raw_agenda, list):
            agenda_rows = [row for row in raw_agenda if isinstance(row, dict)]
        raw_workouts = data.get("workouts")
        if isinstance(raw_workouts, list):
            workout_rows = [row for row in raw_workouts if isinstance(row, dict)]

workout_map = {workout.get("workout_id"): workout for workout in workout_rows if workout.get("workout_id")}

total_activities = sum(bool(row.get("workout_id")) for row in agenda_rows)
total_minutes = 0
total_kj = 0.0
for row in agenda_rows:
    total_minutes += parse_duration_minutes(str(row.get("planned_duration", "")))
    try:
        total_kj += float(row.get("planned_kj", 0) or 0)
    except (TypeError, ValueError):
        continue

agenda_title = (
    "Weekly Agenda: "
    f"{total_activities} Act. - "
    f"{format_duration_hhmm(total_minutes)} Duration - "
    f"{int(round(total_kj))} kJ Load"
)

with st.expander(agenda_title, expanded=False):
    st.markdown(_agenda_table(agenda_rows), unsafe_allow_html=True)

day_order = {
    "Mon": 1,
    "Monday": 1,
    "Tue": 2,
    "Tuesday": 2,
    "Wed": 3,
    "Wednesday": 3,
    "Thu": 4,
    "Thursday": 4,
    "Fri": 5,
    "Friday": 5,
    "Sat": 6,
    "Saturday": 6,
    "Sun": 7,
    "Sunday": 7,
}
sorted_agenda = sorted(
    agenda_rows,
    key=lambda row: (
        day_order.get(str(row.get("day", "")), 99),
        str(row.get("date", "")),
    ),
)

st.subheader("Workouts")
for row in sorted_agenda:
    workout_id = row.get("workout_id")
    if not workout_id:
        continue
    workout = workout_map.get(workout_id, {})
    title = workout.get("title") or workout_id
    notes = workout.get("notes") or "N/A"
    duration = row.get("planned_duration") or workout.get("duration") or "N/A"
    load_kj = row.get("planned_kj") or "N/A"
    day = row.get("day") or "N/A"
    workout_date = row.get("date") or "N/A"

    focus = title.split(" - ")[-1] if " - " in title else title
    if isinstance(focus, str) and focus.lower().startswith(f"{day}".lower()):
        focus = focus[len(day) :].lstrip()
    duration_minutes = parse_duration_minutes(str(duration))
    if not duration_minutes:
        duration_minutes = duration_minutes_from_workout_text(str(workout.get("workout_text") or ""))
    duration_label = format_duration_hhmm(duration_minutes) or str(duration)
    expander_title = f"{day}: {focus} - {duration_label} Duration - {load_kj} kJ Load"
    with st.expander(expander_title, expanded=False):
        st.markdown(f"**{day} · {title}**")
        cols = st.columns([2, 1])
        with cols[0]:
            st.markdown(f"**Notes:** {notes}")
            st.markdown(f"**Date:** {workout_date}")
        with cols[1]:
            st.markdown(f"**Duration:** {duration_label}")
            st.markdown(f"**Load:** {load_kj} kJ")
        workout_text = workout.get("workout_text")
        if workout_text:
            st.code(workout_text)
