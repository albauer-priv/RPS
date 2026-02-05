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

st.title("Availability")
st.caption(f"Athlete: {athlete_id}")
st.info(
    "Describe typical weekly hours plus any fixed rest days. "
    "This is used to bound feasible weekly load corridors."
)

store = LocalArtifactStore(root=SETTINGS.workspace_root)
store.ensure_workspace(athlete_id)
availability_path = store.latest_path(athlete_id, ArtifactType.AVAILABILITY)

if not availability_path.exists():
    payload: dict[str, object] = {}
    st.info("No availability input found yet. Add your weekly availability below.")
    set_status(status_state="running", title="Availability", message="Missing availability input.")
else:
    payload = json.loads(availability_path.read_text(encoding="utf-8"))
    set_status(status_state="done", title="Availability", message="Ready.")

render_status_panel()

data = payload.get("data", {}) if isinstance(payload, dict) else {}
availability_table = data.get("availability_table") or []
weekly_hours = data.get("weekly_hours") or {"min": 0.0, "typical": 0.0, "max": 0.0}
fixed_rest_days = data.get("fixed_rest_days") or []
notes = data.get("notes") or ""

st.subheader("Weekly Hours")
col_min, col_typ, col_max = st.columns(3)
with col_min:
    weekly_min = st.number_input("Min hours", min_value=0.0, value=float(weekly_hours.get("min", 0.0)))
with col_typ:
    weekly_typ = st.number_input("Typical hours", min_value=0.0, value=float(weekly_hours.get("typical", 0.0)))
with col_max:
    weekly_max = st.number_input("Max hours", min_value=0.0, value=float(weekly_hours.get("max", 0.0)))

st.subheader("Availability Table")
if not availability_table:
    availability_table = [
        {"day": "Mon", "hours": 0.0, "notes": ""}
    ]
availability_table = st.data_editor(
    availability_table,
    num_rows="dynamic",
    width="stretch",
    key="availability_table_editor",
)

fixed_rest_days = st.multiselect(
    "Fixed rest days",
    ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    default=fixed_rest_days,
)

notes = st.text_area("Notes", value=notes, height=120)

if st.button("Save Availability", width="content"):
    run_ts = datetime.now(timezone.utc)
    version_key = run_ts.strftime("%Y%m%d_%H%M%S")
    payload = {
        "source_type": "manual",
        "source_ref": "ui_manual",
        "availability_table": availability_table,
        "weekly_hours": {
            "min": weekly_min,
            "typical": weekly_typ,
            "max": weekly_max,
        },
        "fixed_rest_days": fixed_rest_days,
        "notes": notes,
    }
    store.save_version(
        athlete_id,
        ArtifactType.AVAILABILITY,
        version_key,
        payload,
        payload_meta={
            "schema_id": "AvailabilityInterface",
            "schema_version": "1.0",
            "version": "1.0",
            "authority": Authority.BINDING.value,
            "owner_agent": "User",
            "scope": "Shared",
            "data_confidence": "USER",
            "created_at": run_ts.isoformat(),
        },
        authority=Authority.BINDING,
        producer_agent="ui_availability",
        run_id=f"ui_availability_{run_ts.strftime('%Y%m%dT%H%M%SZ')}",
        update_latest=True,
    )
    st.success("Availability saved.")
    set_status(status_state="done", title="Availability", message="Saved availability input.")
