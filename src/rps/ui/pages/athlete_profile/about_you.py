from __future__ import annotations

import streamlit as st

from rps.ui.shared import announce_log_file, get_athlete_id, init_ui_state


st.set_page_config(
    page_title="RPS - Randonneur Performance System",
    layout="wide",
)

init_ui_state()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.title("About You")
st.caption(f"Athlete: {athlete_id}")
st.info("Athlete profile page placeholder.")
