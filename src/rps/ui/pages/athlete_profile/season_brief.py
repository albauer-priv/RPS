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

st.title("Season Brief (Deprecated)")
st.caption(f"Athlete: {athlete_id}")
st.info(
    "Season Brief has been replaced by modular inputs. "
    "Use About You & Goals, Availability, Events, and Logistics instead."
)
set_status(
    status_state="warning",
    title="Season Brief",
    message="Deprecated. Use About You & Goals, Availability, Events, and Logistics.",
)

render_status_panel()
