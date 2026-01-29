from __future__ import annotations

import streamlit as st

from rps.ui.shared import (
    announce_log_file,
    athlete_phase_card,
    get_athlete_id,
    get_iso_year_week,
    init_ui_state,
    system_log_panel,
)

st.title("RPS - Randonneur Performance System")
st.caption("Chat-style control surface for preflight, season-plan, and plan-week flows.")

init_ui_state()
athlete_id = get_athlete_id()
year, week = get_iso_year_week()
announce_log_file(athlete_id)

athlete_phase_card(athlete_id, year, week)
system_log_panel(expanded=True)
