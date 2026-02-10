from __future__ import annotations

import json

import streamlit as st

from rps.ui.intervals_refresh import request_intervals_refresh
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
from rps.workspace.types import ArtifactType


def _format_hh_mm(total_seconds: float) -> str:
    if total_seconds <= 0:
        return "00:00"
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f"{hours:02d}:{minutes:02d}"


init_ui_state()
render_global_sidebar()
athlete_id = get_athlete_id()
announce_log_file(athlete_id)

st.title("Historic Data")
st.caption(f"Athlete: {athlete_id}")

store = LocalArtifactStore(root=SETTINGS.workspace_root)
store.ensure_workspace(athlete_id)
baseline_path = store.latest_path(athlete_id, ArtifactType.HISTORICAL_BASELINE)

payload: dict[str, object] = {}
if baseline_path.exists():
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    set_status(status_state="done", title="Historic Data", message="Ready.")
else:
    set_status(status_state="running", title="Historic Data", message="Missing baseline.")

render_status_panel()
st.info(
    "Historic baseline metrics are computed from full-year Intervals data. "
    "Use Refresh to recompute after new activities are imported."
)

data = payload.get("data", {}) if isinstance(payload, dict) else {}
meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
created_at = meta.get("created_at") if isinstance(meta, dict) else None
if created_at:
    st.caption(f"Last refresh: {created_at}")
yearly_summary = data.get("yearly_summary") or []
yearly_summary = sorted(
    yearly_summary,
    key=lambda entry: entry.get("year") or 0,
    reverse=True,
)

st.subheader("Yearly Activity Summary")
if yearly_summary:
    summary_rows = []
    for item in yearly_summary:
        if not isinstance(item, dict):
            continue
        moving_time_seconds = float(item.get("moving_time_seconds") or 0.0)
        km = item.get("distance_km")
        kj_year = item.get("work_kj")
        kj_activity = item.get("kj_per_activity")
        kj_hour = item.get("kj_per_hour")
        summary_rows.append(
            {
                "year": item.get("year"),
                "activities": item.get("activities"),
                "moving_time": _format_hh_mm(moving_time_seconds),
                "km": int(round(km)) if km is not None else None,
                "kj_year": int(round(kj_year)) if kj_year is not None else None,
                "kj_activity": int(round(kj_activity)) if kj_activity is not None else None,
                "kj_hour": int(round(kj_hour)) if kj_hour is not None else None,
            }
        )
    st.dataframe(
        summary_rows,
        width="stretch",
        hide_index=True,
        column_config={
            "year": st.column_config.NumberColumn("Year", format="%d"),
            "activities": st.column_config.NumberColumn("Activities", format="%d"),
            "moving_time": st.column_config.TextColumn("Moving Time (hh:mm)"),
            "km": st.column_config.NumberColumn("km", format="%d"),
            "kj_year": st.column_config.NumberColumn("kJ / year", format="%d"),
            "kj_activity": st.column_config.NumberColumn("kJ / activity", format="%d"),
            "kj_hour": st.column_config.NumberColumn("kJ / hour", format="%d"),
        },
    )
else:
    st.info("No historical baseline summary found yet. Run the Intervals pipeline to generate it.")

if st.button("Refresh Historical Baseline", width="content"):
    status, message, run_id = request_intervals_refresh(athlete_id)
    if status == "running":
        st.info(message or "Intervals pipeline running.")
    elif status == "error":
        st.error(message or "Intervals pipeline failed.")
    else:
        st.success(message or "Intervals data refreshed.")
    if run_id:
        st.caption(f"Run ID: {run_id}")
