from __future__ import annotations

import json

import streamlit as st

from rps.ui.shared import SETTINGS, announce_log_file, get_athlete_id, init_ui_state


st.set_page_config(
    page_title="RPS - Randonneur Performance System",
    layout="wide",
)

init_ui_state()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.title("Availability")
st.caption(f"Athlete: {athlete_id}")

availability_path = SETTINGS.workspace_root / athlete_id / "latest" / "availability.json"

if not availability_path.exists():
    st.error("No availability.json found for this athlete.")
    raise SystemExit()

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
