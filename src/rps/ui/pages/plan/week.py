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
    render_global_sidebar,
    render_status_panel,
    season_plan_covers_week,
    set_status,
    system_log_panel,
)


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

with st.expander("Actions", expanded=False):
    with st.form("plan_week_actions"):
        plan_submit = st.form_submit_button("Plan Week", disabled=not allowed)
        report_submit = st.form_submit_button("Create Report")

if report_submit:
    st.info("Report creation requested. Following the plan-week run, this will queue the DES analysis report.")
    set_status(
        status_state="running",
        title="Week",
        message="Report creation requested.",
        last_action="Create Report",
    )

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

plan_output = st.session_state.get("plan_week_output")
if plan_output:
    with st.expander("Plan Week Output", expanded=True):
        st.code(plan_output)

system_log_panel(expanded=False)
