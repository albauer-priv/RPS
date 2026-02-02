from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import streamlit as st

from rps.orchestrator.week_revision import revise_week_plan
from rps.ui.intervals_post import delete_posted_workouts, post_to_intervals_commit
from rps.ui.shared import (
    CAPTURE_LOGGERS,
    SETTINGS,
    announce_log_file,
    append_system_log,
    capture_output,
    duration_minutes_from_workout_text,
    format_duration_hhmm,
    get_athlete_id,
    get_iso_year_week,
    iso_week_date_range,
    init_ui_state,
    make_ui_run_id,
    multi_runtime_for,
    parse_duration_minutes,
    render_global_sidebar,
    render_status_panel,
    set_status,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType
from rps.workspace.iso_helpers import parse_iso_week


state = init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")
week_start, week_end = iso_week_date_range(year, week)
st.title(f"Workouts · {week_start} to {week_end}")

# CHECKLIST (Workouts page)
# - Current week actions: Post to Intervals, Delete posted, Revise via Week Planner message.
# - Current week workouts list (from workouts_yyyy-ww.json) with description details.
# - History view: month -> week -> workouts (newest months first).
# - Show status + errors when no exports are found.

store = LocalArtifactStore(root=SETTINGS.workspace_root)
version_key = f"{year:04d}-{week:02d}"

st.subheader(f"Workouts · {version_key}")

with st.expander("Actions", expanded=False):
    with st.form("workouts_actions"):
        post_submit = st.form_submit_button("Post to Intervals")
        delete_submit = st.form_submit_button("Delete posted workouts")
        delete_removed = st.checkbox("Delete removed workouts", value=False)

    with st.form("workouts_revise"):
        message = st.text_area("Message to coach (Week Planner)")
        revise_submit = st.form_submit_button("Revise week plan")

if post_submit:
    result = post_to_intervals_commit(
        store,
        athlete_id,
        year=year,
        week=week,
        run_id=f"post_intervals_{version_key}",
        allow_delete=delete_removed,
    )
    if result.ok:
        st.success(
            f"Posted {result.posted} workouts (skipped {result.skipped}, deleted {result.deleted})."
        )
    else:
        st.error(result.error or "Intervals posting failed.")

if delete_submit:
    result = delete_posted_workouts(
        store,
        athlete_id,
        year=year,
        week=week,
        run_id=f"delete_intervals_{version_key}",
    )
    if result.ok:
        st.success(f"Deleted {result.deleted} posted workouts.")
    else:
        st.error(result.error or "Intervals delete failed.")

if revise_submit:
    if not message.strip():
        st.warning("Please provide a message for the Week Planner.")
    else:
        run_id = make_ui_run_id(f"workouts_revise_{year}_{week:02d}")
        append_system_log("workouts", f"Revise Week Plan started for {version_key}.")
        set_status(
            status_state="running",
            title="Workouts",
            message=f"Revising week {version_key}...",
            last_action="Revise Week Plan",
            last_run_id=run_id,
        )
        result, output = capture_output(
            lambda: revise_week_plan(
                lambda name: multi_runtime_for(name),
                athlete_id=athlete_id,
                year=year,
                week=week,
                message=message,
                run_id=run_id,
                model_resolver=SETTINGS.model_for_agent,
                temperature_resolver=SETTINGS.temperature_for_agent,
                force_file_search=True,
                max_num_results=SETTINGS.file_search_max_results,
            ),
            loggers=CAPTURE_LOGGERS,
        )
        status = "done" if isinstance(result, dict) or getattr(result, "ok", False) else "error"
        set_status(
            status_state=status,
            title="Workouts",
            message=f"Revise complete for {version_key}.",
            last_action="Revise Week Plan",
            last_run_id=run_id,
        )
        if output:
            with st.expander("Revise output", expanded=False):
                st.code(output)

render_status_panel()

intervals_payload = None
try:
    intervals_payload = store.load_version(athlete_id, ArtifactType.INTERVALS_WORKOUTS, version_key)
except FileNotFoundError:
    try:
        intervals_payload = store.load_latest(athlete_id, ArtifactType.INTERVALS_WORKOUTS)
    except FileNotFoundError:
        intervals_payload = None

if not intervals_payload:
    st.info("No Intervals workouts found for this week.")
else:
    week_plan_payload = None
    try:
        week_plan_payload = store.load_version(athlete_id, ArtifactType.WEEK_PLAN, version_key)
    except FileNotFoundError:
        week_plan_payload = None
    day_lookup: dict[str, list[dict[str, str]]] = {}
    if isinstance(week_plan_payload, dict):
        agenda_rows = (week_plan_payload.get("data") or {}).get("agenda") or []
        workout_rows = (week_plan_payload.get("data") or {}).get("workouts") or []
        workout_map = {
            workout.get("workout_id"): workout
            for workout in workout_rows
            if workout.get("workout_id")
        }
        for row in agenda_rows:
            workout_id = row.get("workout_id")
            workout = workout_map.get(workout_id, {})
            name = workout.get("title") or workout_id or "Workout"
            date = row.get("date") or ""
            duration = row.get("planned_duration") or workout.get("duration") or ""
            load_kj = str(row.get("planned_kj") or "")
            day = str(row.get("day") or "")
            if date:
                day_lookup.setdefault(date, []).append(
                    {
                        "name": str(name),
                        "duration": str(duration),
                        "load_kj": load_kj,
                        "day": day,
                    }
                )

    st.subheader("Current Week Workouts")
    for item in intervals_payload:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or "Workout"
        start = item.get("start_date_local") or ""
        description = item.get("description") or ""
        date_str = start.split("T")[0] if "T" in start else start
        time_str = start.split("T")[1][:5] if "T" in start else ""
        duration_source = ""
        load_kj = ""
        day = ""
        if date_str and date_str in day_lookup:
            candidates = day_lookup[date_str]
            if len(candidates) == 1:
                match = candidates[0]
            else:
                match = None
                name_lower = name.lower()
                for candidate in candidates:
                    if candidate["name"].lower() in name_lower:
                        match = candidate
                        break
                if match is None:
                    match = candidates[0]
            duration_source = match.get("duration", "")
            load_kj = match.get("load_kj", "")
            day = match.get("day", "")
        duration_minutes = parse_duration_minutes(duration_source) if duration_source else 0
        if not duration_minutes:
            duration_minutes = duration_minutes_from_workout_text(description)
        duration_label = format_duration_hhmm(duration_minutes)
        header = name
        if day:
            focus = name.split(" - ")[-1] if " - " in name else name
            if isinstance(focus, str) and focus.lower().startswith(day.lower()):
                focus = focus[len(day) :].lstrip()
            header = f"{day}: {focus}"
            if duration_label:
                header = f"{header} - {duration_label} Duration"
            if load_kj:
                header = f"{header} - {load_kj} kJ Load"
        else:
            if date_str:
                header = f"{header} · {date_str}"
            if time_str:
                header = f"{header} {time_str}"
            if duration_label:
                header = f"{header} · {duration_label}"
        with st.expander(header, expanded=False):
            st.code(description)


st.subheader("Workouts History")
exports_dir = store.root / athlete_id / "data" / "exports"
workout_files = sorted(exports_dir.glob("workouts_*.json"), reverse=True)

if not workout_files:
    st.info("No exported workouts found yet.")
else:
    month_map: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for path in workout_files:
        week_label = path.stem.replace("workouts_", "")
        iso_week = parse_iso_week(week_label)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            continue
        for item in payload:
            if not isinstance(item, dict):
                continue
            start = item.get("start_date_local") or ""
            date_str = start.split("T")[0] if "T" in start else ""
            if date_str:
                try:
                    month_key = datetime.fromisoformat(date_str).strftime("%Y-%m")
                except ValueError:
                    month_key = week_label
            elif iso_week:
                month_key = datetime.fromisocalendar(iso_week.year, iso_week.week, 1).strftime("%Y-%m")
            else:
                month_key = "unknown"
            month_map[month_key][week_label].append(
                {
                    "name": item.get("name") or "Workout",
                    "start": start or "—",
                    "description": item.get("description") or "",
                }
            )

    for month_key in sorted(month_map.keys(), reverse=True):
        with st.expander(month_key, expanded=False):
            weeks = month_map[month_key]
            for week_label in sorted(weeks.keys(), reverse=True):
                with st.expander(f"Week {week_label}", expanded=False):
                    for workout in weeks[week_label]:
                        st.markdown(f"**{workout['name']}** · {workout['start']}")
                        if workout["description"]:
                            st.code(workout["description"])
