from __future__ import annotations

import json

import streamlit as st

from rps.ui.shared import (
    SETTINGS,
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

st.title("Availability")
st.caption(f"Athlete: {athlete_id}")

availability_path = SETTINGS.workspace_root / athlete_id / "latest" / "availability.json"

if not availability_path.exists():
    st.info("No availability.json found for this athlete.")
    set_status(status_state="running", title="Availability", message="Missing availability.json; parse from Season Brief.")
    render_status_panel()
else:
    set_status(status_state="done", title="Availability", message="Ready.")
    render_status_panel()

    payload = json.loads(availability_path.read_text(encoding="utf-8"))
    availability_table = payload.get("data", {}).get("availability_table") or []

    st.subheader("Availability Table")
    if availability_table:
        st.data_editor(availability_table, num_rows="dynamic", width="stretch")
    else:
        st.info("No availability rows found.")

    notes = payload.get("data", {}).get("notes")
    if notes:
        st.subheader("Notes")
        st.write(notes)
