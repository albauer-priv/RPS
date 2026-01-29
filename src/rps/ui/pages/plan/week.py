from __future__ import annotations

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
    make_ui_run_id,
    multi_runtime_for,
    season_plan_covers_week,
    system_log_panel,
)


st.title("Week")

state = init_ui_state()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")

col_year, col_week = st.columns(2)
year = int(
    col_year.number_input(
        "ISO Year",
        min_value=2000,
        max_value=2100,
        value=year,
        step=1,
    )
)
week = int(
    col_week.number_input(
        "ISO Week",
        min_value=1,
        max_value=53,
        value=week,
        step=1,
    )
)
state["iso_year"] = year
state["iso_week"] = week
st.session_state["iso_year"] = year
st.session_state["iso_week"] = week

allowed, reason = season_plan_covers_week(athlete_id, year, week)

if st.button("Plan Week", disabled=not allowed):
    run_id = make_ui_run_id(f"plan_week_{year}_{week:02d}")
    append_system_log("plan_week", f"Plan Week started for {year}-W{week:02d}.")

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

if not allowed and reason:
    st.caption(reason)

plan_output = st.session_state.get("plan_week_output")
if plan_output:
    with st.expander("Plan Week Output", expanded=True):
        st.code(plan_output)

system_log_panel(expanded=False)
