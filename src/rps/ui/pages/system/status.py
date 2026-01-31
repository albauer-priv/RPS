from __future__ import annotations

from datetime import datetime

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
from rps.ui.run_store import load_runs
from rps.workspace.index_manager import WorkspaceIndexManager
from rps.workspace.types import ArtifactType


st.title("Status")

# CHECKLIST (System -> Status)
# - Show running processes with filters (status, athlete).
# - Provide a live list of latest artifacts (one per type).
# - Keep output compact and scannable.

init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")

runs = load_runs(SETTINGS.workspace_root, athlete_id, limit=100)
status_filter = st.selectbox(
    "Process status",
    options=["All", "QUEUED", "RUNNING", "DONE", "FAILED", "CANCELLED", "SUPERSEDED"],
    index=1,
)
type_values = sorted({run.get("process_type") or "Unspecified" for run in runs})
type_filter = st.selectbox(
    "Process type",
    options=["All", *type_values],
    index=0,
)
subtype_values = sorted({run.get("process_subtype") or "Unspecified" for run in runs})
subtype_filter = st.selectbox(
    "Process subtype",
    options=["All", *subtype_values],
    index=0,
)

def _matches_filter(run: dict) -> bool:
    if status_filter != "All" and run.get("status") != status_filter:
        return False
    process_type = run.get("process_type") or "Unspecified"
    if type_filter != "All" and process_type != type_filter:
        return False
    process_subtype = run.get("process_subtype") or "Unspecified"
    if subtype_filter != "All" and process_subtype != subtype_filter:
        return False
    return True


filtered_runs = [run for run in runs if _matches_filter(run)]

set_status(
    status_state="done" if filtered_runs else "idle",
    title="System",
    message=f"{len(filtered_runs)} runs" if filtered_runs else "No runs found.",
    last_action="View Status",
)
render_status_panel()

if filtered_runs:
    st.subheader("Running Processes")
    rows = []
    for run in filtered_runs:
        rows.append(
            {
                "Run ID": run.get("run_id"),
                "Status": run.get("status"),
                "Type": run.get("process_type") or "Unspecified",
                "Subtype": run.get("process_subtype") or "Unspecified",
                "Mode": run.get("mode"),
                "Scope": run.get("scope") or "—",
                "Created": run.get("created_at") or "—",
                "Current Step": run.get("current_step") or "—",
            }
        )
    st.dataframe(rows, use_container_width=True)
else:
    st.info("No matching runs.")

st.subheader("Latest Artefacts")
index = WorkspaceIndexManager(root=SETTINGS.workspace_root, athlete_id=athlete_id).load()
latest_rows = []
for artifact_type in ArtifactType:
    entry = (index.get("artefacts") or {}).get(artifact_type.value)
    if not entry or not isinstance(entry, dict):
        continue
    latest = entry.get("latest")
    if not isinstance(latest, dict):
        continue
    created_at = latest.get("created_at")
    latest_rows.append(
        {
            "Artefact": artifact_type.value,
            "Version": latest.get("version_key") or "—",
            "Run": latest.get("run_id") or "—",
            "Updated": created_at or "—",
        }
    )

latest_rows.sort(key=lambda row: row.get("Updated") or "", reverse=True)
if latest_rows:
    st.dataframe(latest_rows, use_container_width=True)
else:
    st.info("No artefacts found.")
