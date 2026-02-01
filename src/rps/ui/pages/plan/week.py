from __future__ import annotations

from datetime import date

import streamlit as st

from rps.orchestrator.plan_week import plan_week
from rps.ui.shared import (
    CAPTURE_LOGGERS,
    SETTINGS,
    announce_log_file,
    append_system_log,
    capture_output,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    load_rendered_markdown,
    make_ui_run_id,
    multi_runtime_for,
    render_global_sidebar,
    render_status_panel,
    season_plan_covers_week,
    set_status,
    system_log_panel,
)
from rps.workspace.iso_helpers import IsoWeek, next_iso_week
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


def _parse_minutes(duration: str) -> int:
    parts = duration.split(":")
    if len(parts) == 3:
        hours, minutes, _seconds = parts
        return int(hours) * 60 + int(minutes)
    if len(parts) == 2:
        hours, minutes = parts
        return int(hours) * 60 + int(minutes)
    if len(parts) == 1 and parts[0].isdigit():
        return int(parts[0]) * 60
    return 0


def _format_hhmm(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def _agenda_table(agenda: list[dict]) -> str:
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
    try:
        return float(value)
    except (TypeError, ValueError):
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


st.title("Week")

state = init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")
state["iso_year"] = year
state["iso_week"] = week
st.session_state["iso_year"] = year
st.session_state["iso_week"] = week

allowed, reason = season_plan_covers_week(athlete_id, year, week)
current_week = IsoWeek(*date.today().isocalendar()[:2])
allowed_scope = IsoWeek(year=year, week=week) in {current_week, next_iso_week(current_week)}
if not allowed_scope:
    allowed = False
    reason = "Planning is limited to the current or next ISO week."

with st.expander("Actions", expanded=False):
    with st.form("plan_week_actions"):
        plan_submit = st.form_submit_button("Plan Week", disabled=not allowed)

if plan_submit:
    run_id = make_ui_run_id(f"plan_week_{year}_{week:02d}")
    append_system_log("plan_week", f"Plan Week started for {year}-W{week:02d}.")
    set_status(
        status_state="running",
        title="Week",
        message=f"Planning week {year}-W{week:02d}...",
        last_action="Plan Week",
        last_run_id=run_id,
    )

    runtime = multi_runtime_for("season_planner")

    def _run():
        return plan_week(
            runtime,
            athlete_id=athlete_id,
            year=year,
            week=week,
            run_id=run_id,
            model_resolver=SETTINGS.model_for_agent,
            temperature_resolver=SETTINGS.temperature_for_agent,
            reasoning_effort_resolver=SETTINGS.reasoning_effort_for_agent,
            reasoning_summary_resolver=SETTINGS.reasoning_summary_for_agent,
            force_file_search=True,
            max_num_results=SETTINGS.file_search_max_results,
        )

    result, output = capture_output(_run, loggers=CAPTURE_LOGGERS)
    status = "ok" if getattr(result, "ok", False) else "error"
    summary = f"plan-week finished: {status}"
    if output:
        summary = f"{output}\n\n{summary}"
    st.session_state["plan_week_output"] = summary
    append_system_log("plan_week", summary)
    set_status(
        status_state="done",
        title="Week",
        message=f"Plan week finished ({status}).",
        last_action="Plan Week",
        last_run_id=run_id,
    )

if not allowed and reason:
    st.caption(reason)

render_status_panel()

store = LocalArtifactStore(root=SETTINGS.workspace_root)
agenda_payload = None
try:
    agenda_payload = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, f"{year:04d}-{week:02d}")
except FileNotFoundError:
    agenda_payload = None

agenda_rows = []
workout_rows = []
if isinstance(agenda_payload, dict):
    agenda_rows = (agenda_payload.get("data") or {}).get("agenda") or []
    workout_rows = (agenda_payload.get("data") or {}).get("workouts") or []

workout_map = {workout.get("workout_id"): workout for workout in workout_rows if workout.get("workout_id")}

total_activities = sum(1 for row in agenda_rows if row.get("workout_id"))
total_minutes = 0
total_kj = 0.0
for row in agenda_rows:
    total_minutes += _parse_minutes(str(row.get("planned_duration", "")))
    try:
        total_kj += float(row.get("planned_kj", 0) or 0)
    except (TypeError, ValueError):
        continue

agenda_title = (
    "Weekly Agenda: "
    f"{total_activities} Act. - "
    f"{_format_hhmm(total_minutes)} Duration - "
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

plan_output = st.session_state.get("plan_week_output")
if plan_output:
    with st.expander("Plan Week Output", expanded=True):
        st.code(plan_output)

system_log_panel(expanded=False)
