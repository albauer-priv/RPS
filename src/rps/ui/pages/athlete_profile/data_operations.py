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

st.title("Data Operations")
st.caption(f"Athlete: {athlete_id}")
st.write("Backup and restore athlete data for portability and recovery.")

set_status(status_state="ready", title="Data Operations", message="Backup/restore tools are available.")
render_status_panel()

with st.expander("Backup (Export)", expanded=False):
    st.write("Create a portable archive of this athlete’s data.")
    st.button("Create Backup (coming soon)", disabled=True, width="content")
    st.info("Backups exclude logs and run history; see the backup/restore doc for scope.")

with st.expander("Restore (Import)", expanded=False):
    st.write("Restore an archive into this athlete’s workspace.")
    st.file_uploader("Backup archive (.zip or .tar.gz)", type=["zip", "tar", "gz"])
    st.button("Restore Backup (coming soon)", disabled=True, width="content")
    st.warning("Restores are destructive; target workspace should be empty unless using a partial restore.")
