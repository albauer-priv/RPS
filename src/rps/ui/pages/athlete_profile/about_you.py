from __future__ import annotations

import streamlit as st

from rps.ui.shared import (
    announce_log_file,
    get_athlete_id,
    init_ui_state,
    render_global_sidebar,
    render_status_panel,
    set_status,
)


init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.title("About You")
st.caption(f"Athlete: {athlete_id}")
set_status(status_state="done", title="About You", message="Ready.")
render_status_panel()
st.write("Athlete profile page placeholder.")
