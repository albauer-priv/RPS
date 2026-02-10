from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from rps.ui.shared import (
    ROOT,
    SETTINGS,
    announce_log_file,
    get_athlete_id,
    init_ui_state,
    render_global_sidebar,
    render_status_panel,
    set_status,
)
from rps.workspace.local_store import LocalArtifactStore
from rps.workspace.types import ArtifactType


st.title("KPI Profile")

# CHECKLIST (Athlete Profile -> KPI Profile)
# - Show all available KPI profiles (expandable list).
# - Provide dropdown selection and core profile metadata summary.
# - Apply selection to workspace (inputs + latest) on confirm.

init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")

profiles_dir = ROOT / "specs" / "kpi_profiles"
profile_paths = sorted(profiles_dir.glob("kpi_profile_*.json"))

if not profile_paths:
    set_status(status_state="idle", title="KPI Profile", message="No KPI profiles found.")
    render_status_panel()
    st.stop()

set_status(status_state="done", title="KPI Profile", message="Ready.")
render_status_panel()

profile_map = {path.stem: path for path in profile_paths}
profile_keys = list(profile_map.keys())
selected_key = st.selectbox("Select KPI Profile", options=profile_keys)

selected_payload = json.loads(profile_map[selected_key].read_text(encoding="utf-8"))
meta = selected_payload.get("meta", {}) if isinstance(selected_payload, dict) else {}
data = selected_payload.get("data", {}) if isinstance(selected_payload, dict) else {}
profile_meta = data.get("profile_metadata", {}) if isinstance(data, dict) else {}

with st.expander("Available KPI Profiles", expanded=False):
    for key, path in profile_map.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        data_block = payload.get("data", {}) if isinstance(payload, dict) else {}
        meta_block = data_block.get("profile_metadata", {}) if isinstance(data_block, dict) else {}
        summary = " · ".join(
            str(meta_block.get(field) or "").strip()
            for field in ("profile_id", "event_type", "distance_range", "athlete_class")
            if meta_block.get(field)
        )
        st.markdown(f"**{key}**\n\n{summary or 'No metadata available.'}")

st.subheader("Profile Summary")
if profile_meta:
    st.table(
        {
            "Profile ID": [profile_meta.get("profile_id", "—")],
            "Event Type": [profile_meta.get("event_type", "—")],
            "Distance Range": [profile_meta.get("distance_range", "—")],
            "Athlete Class": [profile_meta.get("athlete_class", "—")],
            "Primary Objective": [profile_meta.get("primary_objective", "—")],
        }
    )
else:
    st.info("No profile metadata found.")

with st.expander("Profile Details", expanded=False):
    st.json(data)

if st.button("Use this KPI Profile"):
    store = LocalArtifactStore(root=SETTINGS.workspace_root)
    version_key = selected_key.replace("kpi_profile_", "")
    store.save_document(
        athlete_id,
        ArtifactType.KPI_PROFILE,
        version_key,
        selected_payload,
        producer_agent="user",
        run_id=f"kpi_profile_select_{version_key}",
        update_latest=True,
    )
    # Ensure a canonical inputs copy exists (kpi_profile.json) alongside versioned input.
    inputs_path = store.type_dir(athlete_id, ArtifactType.KPI_PROFILE) / "kpi_profile.json"
    inputs_path.write_text(json.dumps(selected_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    set_status(
        status_state="done",
        title="KPI Profile",
        message=f"Selected {selected_key}.",
        last_action="Select KPI Profile",
    )
    st.success("KPI Profile updated.")
