from __future__ import annotations

from collections import defaultdict
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
from rps.workspace.index_manager import WorkspaceIndexManager
from rps.workspace.types import ArtifactType


st.title("History")

# CHECKLIST (System -> History)
# - Show historical artefacts grouped by time (month -> week -> items).
# - Provide focus sections for Season/Phase/Week when available.
# - Keep newest months first.

init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.caption(f"Athlete: {athlete_id}")

index = WorkspaceIndexManager(root=SETTINGS.workspace_root, athlete_id=athlete_id).load()
artefacts = index.get("artefacts") or {}

rows = []
for artifact_type, entry in artefacts.items():
    if not isinstance(entry, dict):
        continue
    versions = entry.get("versions") or {}
    for version_key, record in versions.items():
        if not isinstance(record, dict):
            continue
        created_at = record.get("created_at") or ""
        rows.append(
            {
                "Artefact": artifact_type,
                "Version": str(version_key),
                "Run": record.get("run_id") or "—",
                "Created": created_at or "—",
                "Validity": record.get("iso_week_range") or record.get("iso_week") or "—",
            }
        )

if not rows:
    set_status(status_state="idle", title="System", message="No artefacts found.")
    render_status_panel()
    st.stop()

set_status(status_state="done", title="System", message="History loaded.")
render_status_panel()

month_map: dict[str, list[dict[str, str]]] = defaultdict(list)
for row in rows:
    created = row.get("Created") or ""
    month_key = "unknown"
    if created:
        try:
            month_key = datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%Y-%m")
        except ValueError:
            month_key = created[:7] if len(created) >= 7 else "unknown"
    month_map[month_key].append(row)

for month_key in sorted(month_map.keys(), reverse=True):
    with st.expander(month_key, expanded=False):
        month_rows = month_map[month_key]
        season_rows = [row for row in month_rows if row["Artefact"] == ArtifactType.SEASON_PLAN.value]
        phase_rows = [
            row
            for row in month_rows
            if row["Artefact"] in {ArtifactType.PHASE_GUARDRAILS.value, ArtifactType.PHASE_STRUCTURE.value}
        ]
        week_rows = [row for row in month_rows if row["Artefact"] == ArtifactType.WEEK_PLAN.value]
        other_rows = [
            row
            for row in month_rows
            if row not in season_rows + phase_rows + week_rows
        ]
        if season_rows:
            st.subheader("Season Plan")
            st.dataframe(season_rows, use_container_width=True)
        if phase_rows:
            st.subheader("Phase")
            st.dataframe(phase_rows, use_container_width=True)
        if week_rows:
            st.subheader("Week")
            st.dataframe(week_rows, use_container_width=True)
        if other_rows:
            st.subheader("Other")
            st.dataframe(other_rows, use_container_width=True)
