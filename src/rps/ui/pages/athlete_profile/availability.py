from __future__ import annotations

import json
import logging

import streamlit as st

from rps.data_pipeline.season_brief_availability import parse_and_store_availability
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

st.subheader("Actions")
if st.button("Parse Availability from Season Brief", width="content"):
    logger = logging.getLogger("rps.ui.availability")
    with st.spinner("Parsing availability from Season Brief..."):
        try:
            result = parse_and_store_availability(
                athlete_id=athlete_id,
                workspace_root=SETTINGS.workspace_root,
                schema_dir=SETTINGS.schema_dir,
            )
        except Exception as exc:  # pragma: no cover - UI error path
            logger.exception("Availability parse failed.")
            st.error(f"Availability parse failed: {exc}")
            set_status(status_state="error", title="Availability", message="Parse failed.")
        else:
            st.success(f"Wrote {result.output_path.name} to latest/ and versioned storage.")
            set_status(status_state="done", title="Availability", message="Parsed from Season Brief.")
            st.rerun()

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
