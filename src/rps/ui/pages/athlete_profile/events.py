from __future__ import annotations

import json
from datetime import datetime, timezone

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
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType, Authority


init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.title("Events")
st.caption(f"Athlete: {athlete_id}")

store = LocalArtifactStore(root=SETTINGS.workspace_root)
store.ensure_workspace(athlete_id)
events_path = store.latest_path(athlete_id, ArtifactType.PLANNING_EVENTS)

payload: dict[str, object] = {}
if events_path.exists():
    payload = json.loads(events_path.read_text(encoding="utf-8"))
    set_status(status_state="done", title="Events", message="Ready.")
else:
    st.info("No planning events found yet. Add A/B/C events below.")
    set_status(status_state="running", title="Events", message="Missing planning events input.")

render_status_panel()

data = payload.get("data", {}) if isinstance(payload, dict) else {}
events = data.get("events") or []

st.subheader("Planning Events (A/B/C)")
events = st.data_editor(events, num_rows="dynamic", width="stretch", key="planning_events_editor")

if st.button("Save Events", width="content"):
    run_ts = datetime.now(timezone.utc)
    version_key = run_ts.strftime("%Y%m%d_%H%M%S")
    payload = {"events": events}
    store.save_version(
        athlete_id,
        ArtifactType.PLANNING_EVENTS,
        version_key,
        payload,
        payload_meta={
            "schema_id": "PlanningEventsInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": Authority.BINDING.value,
            "owner_agent": "User",
            "scope": "Shared",
            "data_confidence": "USER",
            "created_at": run_ts.isoformat(),
            "notes": "",
        },
        authority=Authority.BINDING,
        producer_agent="ui_planning_events",
        run_id=f"ui_planning_events_{run_ts.strftime('%Y%m%dT%H%M%SZ')}",
        update_latest=True,
    )
    st.success("Planning events saved.")
    set_status(status_state="done", title="Events", message="Saved planning events input.")
