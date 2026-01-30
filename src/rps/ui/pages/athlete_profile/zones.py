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

st.title("Zones")
st.caption(f"Athlete: {athlete_id}")

zone_path = SETTINGS.workspace_root / athlete_id / "latest" / "zone_model.json"

if not zone_path.exists():
    st.error("No zone_model.json artifact found for this athlete.")
    set_status(status_state="error", title="Zones", message="No zone_model.json found.")
    render_status_panel()
    st.stop()

set_status(status_state="done", title="Zones", message="Ready.")
render_status_panel()

payload = json.loads(zone_path.read_text(encoding="utf-8"))
data = payload.get("data", {}) or {}
zones = data.get("zones", [])

if zones:
    st.subheader("Zone Table")
    zone_rows = []
    for zone in zones:
        ftp = zone.get("ftp_percent_range", {})
        watt = zone.get("watt_range", {})
        zone_rows.append(
            {
                "Zone": zone.get("zone_id"),
                "Name": zone.get("name"),
                "FTP % (min-max)": f"{ftp.get('min', 'N/A')}–{ftp.get('max', 'N/A')}",
                "Watt (min-max)": f"{watt.get('min', 'N/A')}–{watt.get('max', 'N/A')}",
                "Typical IF": zone.get("typical_if", "N/A"),
                "Training intent": zone.get("training_intent"),
            }
        )
    st.data_editor(zone_rows, num_rows="dynamic", width="stretch")
else:
    st.info("No zones were found in the latest zone model artifact.")
