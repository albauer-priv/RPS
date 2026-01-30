from __future__ import annotations

import json

import streamlit as st

from rps.ui.shared import (
    SETTINGS,
    announce_log_file,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    load_rendered_markdown,
    render_global_sidebar,
    render_status_panel,
    set_status,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


st.title("WoW")

init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")

store = LocalArtifactStore(root=SETTINGS.workspace_root)
version_key = f"{year}-{week:02d}"

st.subheader(f"Workouts of the Week · {version_key}")

with st.expander("Actions", expanded=False):
    with st.form("wow_load_plan"):
        load_submit = st.form_submit_button("Load Week Plan")

if not load_submit and not st.session_state.get("wow_loaded"):
    set_status(
        status_state="idle",
        title="WoW",
        message="Select a week in the sidebar and click 'Load Week Plan'.",
        last_action="View WoW",
    )
    render_status_panel()
    st.stop()
st.session_state["wow_loaded"] = True

if not store.latest_exists(athlete_id, ArtifactType.WEEK_PLAN):
    set_status(
        status_state="idle",
        title="WoW",
        message="No Week Plan found yet.",
        last_action="View WoW",
    )
    render_status_panel()
    st.stop()

if store.latest_exists(athlete_id, ArtifactType.WEEK_PLAN):
    try:
        payload = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, version_key)
    except FileNotFoundError:
        payload = None

    if payload is None:
        set_status(
            status_state="idle",
            title="WoW",
            message=f"No Week Plan found for {version_key}.",
            last_action="View WoW",
        )
        render_status_panel()
        st.stop()

set_status(
    status_state="done",
    title="WoW",
    message=f"Viewing {version_key}.",
    last_action="View WoW",
)
render_status_panel()

intervals_payload = None
try:
    intervals_payload = store.load_version(athlete_id, ArtifactType.INTERVALS_WORKOUTS, version_key)
except FileNotFoundError:
    try:
        intervals_payload = store.load_latest(athlete_id, ArtifactType.INTERVALS_WORKOUTS)
    except FileNotFoundError:
        intervals_payload = None

agenda_rows = []
workout_rows = []
if isinstance(payload, dict):
    agenda_rows = (payload.get("data") or {}).get("agenda") or []
    workout_rows = (payload.get("data") or {}).get("workouts") or []

workout_map = {workout.get("workout_id"): workout for workout in workout_rows if workout.get("workout_id")}
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
    date = row.get("date") or "N/A"

    focus = title.split(" - ")[-1] if " - " in title else title
    if isinstance(focus, str) and focus.lower().startswith(f"{day}".lower()):
        focus = focus[len(day) :].lstrip()
    expander_title = f"{day}: {focus} - {duration} Duration - {load_kj} kJ Load"
    with st.expander(expander_title, expanded=False):
        st.markdown(f"**{day} · {title}**")
        cols = st.columns([2, 1])
        with cols[0]:
            st.markdown(f"**Notes:** {notes}")
            st.markdown(f"**Date:** {date}")
        with cols[1]:
            st.markdown(f"**Duration:** {duration}")
            st.markdown(f"**Load:** {load_kj} kJ")
        workout_text = workout.get("workout_text")
        if workout_text:
            st.code(workout_text)

if isinstance(intervals_payload, list) and intervals_payload:
    st.subheader("Intervals Workouts")
    for item in intervals_payload:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or "Workout"
        start = item.get("start_date_local") or ""
        date_str = start.split("T")[0] if "T" in start else start
        time_str = start.split("T")[1][:5] if "T" in start else ""
        weekday = date_str
        try:
            from datetime import datetime as _dt

            weekday = _dt.fromisoformat(date_str).strftime("%a")
        except Exception:
            pass
        focus = name.split(" - ")[-1] if " - " in name else name
        if isinstance(focus, str) and focus.lower().startswith(f"{weekday}".lower()):
            focus = focus[len(weekday) :].lstrip()
        header = f"{weekday}: {focus}"
        if date_str:
            header = f"{header} - {date_str}"
        if time_str:
            header = f"{header} {time_str}"
        with st.expander(header, expanded=False):
            st.code(item.get("description") or "")
