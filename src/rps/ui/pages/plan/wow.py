from __future__ import annotations

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

rendered = load_rendered_markdown(athlete_id, ArtifactType.WEEK_PLAN, version_key=version_key)
if rendered:
    st.markdown(rendered)
else:
    st.json(payload)
